#!/usr/bin/env bash
# Bouwt het hele rev C-project opnieuw, tot en met de Gerbers, en controleert
# het resultaat.
# Stopt bij de eerste fout; een mislukte stap mag niet als succes doorgaan.
set -euo pipefail

cd "$(dirname "$0")"

# Geen gecompileerde Python-cache gebruiken. Python herkent een verouderde
# cache alleen aan bestandsgrootte en tijdstip op de seconde; op 23-09-2026 had
# een tijdelijke wijziging precies dezelfde grootte en hetzelfde tijdstip als
# het origineel, en draaide elke build daarna stilletjes op de oude code.
rm -rf __pycache__
export PYTHONDONTWRITEBYTECODE=1

# Pak de nieuwste KiCad die geinstalleerd staat, in plaats van een versie vast
# te leggen. Zet KICAD_DIR als je een andere wilt afdwingen.
if [ -z "${KICAD_DIR:-}" ]; then
    KICAD_DIR=$(ls -d "/c/Program Files/KiCad"/*/ 2>/dev/null \
                | sort -V | tail -1 | sed 's:/$::')
fi
[ -x "$KICAD_DIR/bin/kicad-cli.exe" ] || {
    echo "geen KiCad gevonden in $KICAD_DIR" >&2; exit 1; }
KICAD="$KICAD_DIR/bin/kicad-cli.exe"
KICAD_PY="$KICAD_DIR/bin/python.exe"
echo "KiCad: $("$KICAD" version 2>/dev/null | grep -viE 'fontconfig') uit $KICAD_DIR"

PROJ="esp32ct-revc"
SCH="$PROJ/$PROJ.kicad_sch"

# kicad-cli klaagt op Windows over fontconfig; dat zegt niets over het resultaat.
run() { "$KICAD" "$@" 2>&1 | grep -viE 'fontconfig' || true; }

echo "== footprint HW-178-voetje"
python3 hw178.py

echo "== schema genereren"
python3 sheets.py

echo "== netlist"
run sch export netlist --format kicadsexpr -o "$PROJ/$PROJ.net" "$SCH"

echo "== netlist controleren"
python3 check_net.py

echo "== opmaak controleren"
python3 check_layout.py "$PROJ"

echo "== ERC"
run sch erc --severity-error --severity-warning -o "$PROJ/erc.txt" "$SCH" \
    | grep -iE 'overtreding|violation' || true

if grep -qE '^\[' "$PROJ/erc.txt"; then
    echo "ERC is niet schoon - zie $PROJ/erc.txt" >&2
    exit 1
fi

echo "== PDF"
run sch export pdf -o "$PROJ/$PROJ.pdf" "$SCH"

PCB="$PROJ/$PROJ.kicad_pcb"

echo "== PCB plaatsen"
# pcb.py draait op de Python van KiCad, want die heeft de pcbnew-module.
# Het bord wordt elke build vanaf nul geplaatst en gerout: er zit geen
# handwerk in dat verloren kan gaan, en zo kan een schemawijziging geen oude
# plaatsing of vergeten baan achterlaten.
OPNIEUW_PLAATSEN=1 "$KICAD_PY" pcb.py 2>&1 | grep -viE 'fontconfig'

echo "== banen leggen (Freerouting)"
# De eigen router werkt ook nog: OPNIEUW_ROUTEN=1 "$KICAD_PY" route.py
"$KICAD_PY" freeroute.py "$PCB" 2>&1 | grep -viE 'fontconfig|memory leak'

echo "== DRC"
# Met de banen erin moet dit helemaal leeg zijn: geen overtredingen en geen
# onverbonden items. Anders stopt de build - een bord met een ontbrekende
# verbinding mag niet naar de fabriek.
run pcb drc --severity-error --severity-warning -o "$PROJ/drc.txt" "$PCB" \
    | grep -iE 'overtreding|violation|onverbonden|unconnected' || true
if grep -qE '^\[' "$PROJ/drc.txt"; then
    grep -oE '\[[a-z_]+\]' "$PROJ/drc.txt" | sort | uniq -c | sort -rn
    echo "DRC is niet schoon - zie $PROJ/drc.txt" >&2
    exit 1
fi

echo "== tekeningen"
run pcb export pdf --layers "F.Cu,F.Silkscreen,F.Courtyard,Edge.Cuts" \
    -o "$PROJ/plaatsing.pdf" "$PCB"
run pcb export pdf --layers "F.Cu,F.Silkscreen,Edge.Cuts" \
    -o "$PROJ/bovenkant.pdf" "$PCB"
run pcb export pdf --mirror --layers "B.Cu,B.Silkscreen,Edge.Cuts" \
    -o "$PROJ/onderkant.pdf" "$PCB"
for kant in top bottom; do
    run pcb render --side "$kant" --width 1800 --height 1350 \
        --background opaque -o "$PROJ/render_$kant.png" "$PCB" >/dev/null
done

echo "== stuklijst"
run sch export bom --fields "Reference,Value,Description,Footprint" \
    --group-by "Value,Description" -o "$PROJ/bom.csv" "$SCH"

echo "== productiebestanden"
# Gerbers en boorbestanden in een zip: dat upload je bij de printfabriek.
rm -rf "$PROJ/productie"
mkdir -p "$PROJ/productie"
run pcb export gerbers --layers "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts" \
    -o "$PROJ/productie/" "$PCB"
run pcb export drill --format excellon --excellon-separate-th \
    -o "$PROJ/productie/" "$PCB"
python3 -c "
import os, zipfile
d = '$PROJ/productie'
with zipfile.ZipFile('$PROJ/$PROJ-gerbers.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(d)):
        z.write(os.path.join(d, f), f)
        print('  ', f)
"

echo
echo "klaar."
