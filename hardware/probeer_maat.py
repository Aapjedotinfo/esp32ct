#!/usr/bin/env python3
"""
Plaatst het bord op een opgegeven maat en draait de DRC. Meldt alleen echte
plaatsingsfouten; 'onverbonden items' horen erbij zolang er geen banen liggen.

  python3 probeer_maat.py 150 110          een maat proberen
  python3 probeer_maat.py zoek             kleinste schone maat zoeken

Draait zelf pcb.py onder de Python van de nieuwste KiCad.
"""
import glob, os, re, subprocess, sys

HIER = os.path.dirname(os.path.abspath(__file__))
KICAD = sorted(glob.glob(r"C:\Program Files\KiCad\*"),
               key=lambda p: [int(x) for x in re.findall(r"\d+", os.path.basename(p))])[-1]
PY = os.path.join(KICAD, "bin", "python.exe")
CLI = os.path.join(KICAD, "bin", "kicad-cli.exe")
PCB = os.path.join(HIER, "esp32ct-revc", "esp32ct-revc.kicad_pcb")
DRC = os.path.join(HIER, "esp32ct-revc", "drc.txt")


def probeer(b, h, stil=False):
    env = dict(os.environ, PCB_B=str(b), PCB_H=str(h))
    r = subprocess.run([PY, "pcb.py"], cwd=HIER, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit("pcb.py faalde")
    subprocess.run([CLI, "pcb", "drc", "--severity-error", "--severity-warning",
                    "-o", DRC, PCB], capture_output=True)
    t = open(DRC, encoding="utf-8", errors="replace").read()
    blokken = re.split(r"\n(?=\[)", t)
    fouten = [b_ for b_ in blokken
              if b_.startswith("[") and not b_.startswith("[unconnected_items]")]
    if not stil:
        soorten = {}
        for f in fouten:
            s = f.split("]")[0] + "]"
            soorten[s] = soorten.get(s, 0) + 1
        print(f"{b} x {h} mm: {len(fouten)} plaatsingsfouten {soorten or ''}")
        for f in fouten[:12]:
            wie = re.findall(r"(?:Footprint|van) ([A-Z]+\d+)", f)
            print(f"   {f.split(']')[0]}]  {', '.join(dict.fromkeys(wie))}")
    return len(fouten)


if __name__ == "__main__":
    if sys.argv[1:] == ["zoek"]:
        # Hoogte en breedte los van elkaar omlaag, telkens 5 mm, tot het misgaat.
        b, h = 160, 120
        assert probeer(b, h, stil=True) == 0, "zelfs 160 x 120 is niet schoon"
        while b > 60 and probeer(b - 5, h, stil=True) == 0:
            b -= 5
        while h > 60 and probeer(b, h - 5, stil=True) == 0:
            h -= 5
        print(f"kleinste schone maat: {b} x {h} mm")
        probeer(b, h)
    else:
        probeer(float(sys.argv[1]), float(sys.argv[2]))
