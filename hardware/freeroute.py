#!/usr/bin/env python3
"""
Legt de banen op een bord met Freerouting, zonder venster.

  1. het bord gaat als Specctra-ontwerp (.dsn) naar buiten; netklassen,
     regelgebieden en pads gaan mee
  2. Freerouting legt de banen en schrijft een sessie (.ses)
  3. die sessie gaat terug het bord in, de vlakken worden opnieuw gegoten

Freerouting staat NIET in dit project maar gebruikersbreed, zodat elk project
hem kan gebruiken: de nieuwste freerouting-*.jar in
%LOCALAPPDATA%\\Programs\\freerouting, of wat FREEROUTING_JAR zegt. Java moet
op het PATH staan (getest met Java 25 en Freerouting 2.4.1).

Of het resultaat deugt beslist deze stap niet: dat doen de DRC en de eigen
controles in build.sh daarna.

Draaien met de Python van KiCad:
  "/c/Program Files/KiCad/<versie>/bin/python.exe" freeroute.py <bord.kicad_pcb>
"""
import glob, os, re, shutil, subprocess, sys, time
import pcbnew

PASSES = 100            # maximaal aantal routeerrondes
POGINGEN = 3            # zoveel runs voordat het aan de plaatsing ligt


def jar():
    pad = os.environ.get("FREEROUTING_JAR")
    if pad:
        if not os.path.isfile(pad):
            raise SystemExit(f"FREEROUTING_JAR wijst naar {pad}, dat bestaat niet")
        return pad
    map_ = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                        "freerouting")
    jars = glob.glob(os.path.join(map_, "freerouting-*.jar"))
    if not jars:
        raise SystemExit(f"geen freerouting-*.jar in {map_}; zet hem daar "
                         "of zet FREEROUTING_JAR")

    def versie(p):
        return [int(x) for x in re.findall(r"\d+", os.path.basename(p))]
    return max(jars, key=versie)


def uitvoeren(java, j, dsn, ses, basis):
    """Een run van Freerouting. Geeft (open, overtredingen, open netten)."""
    if os.path.exists(ses):
        os.remove(ses)
    t0 = time.time()
    r = subprocess.run([java, "-jar", j, "-de", dsn, "-do", ses,
                        "-mp", str(PASSES), "-mt", "1",
                        "--gui.enabled=false"],
                       capture_output=True, text=True, errors="replace")
    log = r.stdout + r.stderr
    with open(basis + "-freerouting.log", "w", encoding="utf-8") as f:
        f.write(log)
    if r.returncode != 0 or not os.path.exists(ses):
        print(log[-3000:])
        raise SystemExit(f"Freerouting faalde (code {r.returncode})")
    # Alleen de eindstand, en welke verbindingen er eventueel open bleven.
    # Let op het enkelvoud: bij één overtreding schrijft hij "1 violation".
    open_, fout, open_netten = None, None, set()
    for regel in log.splitlines():
        m = re.search(r"final score: [\d.]+ \((\d+) unrouted and (\d+) violations?\b", regel)
        if m and "Auto-routing stage completed" in regel:
            open_, fout = int(m.group(1)), int(m.group(2))
            print(f"  open verbindingen: {open_}, eigen overtredingen "
                  f"volgens Freerouting: {fout}")
        elif re.match(r"\s+(Net '|- )", regel):
            print("  ", regel.strip())
            n = re.match(r"\s+Net '(.+)' \(", regel)
            if n:
                open_netten.add(n.group(1))
    if open_ is None:
        print(log[-3000:])
        raise SystemExit("eindstand van Freerouting niet gevonden in de log")
    print(f"  klaar in {time.time() - t0:.0f} s")
    return open_, fout, open_netten


def main():
    if len(sys.argv) != 2:
        raise SystemExit("gebruik: freeroute.py <bord.kicad_pcb>")
    pcb = os.path.abspath(sys.argv[1])
    basis = os.path.splitext(pcb)[0]
    dsn, ses = basis + ".dsn", basis + ".ses"
    java = shutil.which("java")
    if not java:
        raise SystemExit("java staat niet op het PATH")

    bord = pcbnew.LoadBoard(pcb)
    # Netten met een koperen vlak, vóór het weghalen van de banen: na
    # bord.Remove() geeft SWIG soms kale objecten terug.
    vlaknetten = {z.GetNetname() for z in bord.Zones() if not z.GetIsRuleArea()}
    # Altijd vanaf een leeg bord: met oude banen erin routeert Freerouting
    # eromheen en blijft hij hangen. Zo geeft elke run hetzelfde resultaat.
    oud = list(bord.GetTracks())
    for t in oud:
        bord.Remove(t)
    if oud:
        print(f"  {len(oud)} oude banen en via's eerst weggehaald")
    for f in (dsn, ses):
        if os.path.exists(f):
            os.remove(f)
    if not pcbnew.ExportSpecctraDSN(bord, dsn):
        raise SystemExit("export naar Specctra mislukt")
    # Koperen vlakken NIET als 'plane' aan Freerouting geven. Dan legt hij geen
    # enkele GND-baan en rekent hij erop dat het vlak alles verbindt; op dit
    # bord vielen daardoor steeds andere GND-pads op een eiland tussen de banen
    # (ESP pad 33, mux EN en GND), ook met een vlak op beide lagen. Zonder
    # plane-regels legt hij GND als gewoon net; de vlakken komen er daarna
    # alsnog overheen en zijn dan extra koper, geen voorwaarde.
    with open(dsn, encoding="utf-8") as f:
        regels = f.readlines()
    zonder = [r for r in regels if not r.lstrip().startswith("(plane ")]
    if len(zonder) != len(regels):
        print(f"  {len(regels) - len(zonder)} vlak(ken) als gewone netten gerout")
        with open(dsn, "w", encoding="utf-8") as f:
            f.writelines(zonder)

    j = jar()
    print(f"Freerouting: {os.path.basename(j)}, max {PASSES} rondes, "
          f"max {POGINGEN} pogingen")
    # Freerouting geeft niet elke run hetzelfde. Blijft er iets open of meldt
    # hij zelf een overtreding, dan is een nieuwe run vaak wel schoon; pas als
    # het POGINGEN keer niet lukt, ligt het echt aan de plaatsing.
    for poging in range(1, POGINGEN + 1):
        open_, fout, open_netten = uitvoeren(java, j, dsn, ses, basis)
        # Een open verbinding op een net met een koperen vlak (GND) kan
        # alsnog via dat vlak dicht zijn; dat beslist de DRC na het gieten.
        # Op elk ander net is open ook echt open.
        echt_open = open_netten - vlaknetten
        if not echt_open and not fout:
            break
        print(f"  poging {poging}: niet schoon"
              + (f", open op {', '.join(sorted(echt_open))}" if echt_open else "")
              + (f", {fout} overtreding(en) volgens Freerouting" if fout else ""))
    else:
        raise SystemExit(f"Freerouting kreeg het in {POGINGEN} pogingen niet "
                         "schoon - meer ruimte maken in de plaatsing")
    if open_:
        print(f"  open op {', '.join(sorted(open_netten))}: dat net heeft een "
              "vlak, de DRC beslist of het via het vlak dicht is")

    if not pcbnew.ImportSpecctraSES(bord, ses):
        raise SystemExit("sessie inlezen mislukt")
    pcbnew.ZONE_FILLER(bord).Fill(bord.Zones())
    pcbnew.SaveBoard(pcb, bord)
    banen = [t for t in bord.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    vias = [t for t in bord.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    print(f"{len(banen)} banen, {len(vias)} via's")


if __name__ == "__main__":
    main()
