#!/usr/bin/env python3
"""
Ruwe opmaakcontrole: valt alles binnen het blad, en staan er geen symbolen
bovenop elkaar? Vervangt geen blik op de tekening, maar vangt wel de fouten
waar een generator last van heeft.
"""
import re, sys, os, glob, math

A3 = (420.0, 297.0)
RAND = 5.0          # tekstblokken mogen niet in de bladrand lopen
MINAFSTAND = 6.0    # symbolen dichter dan dit op elkaar is verdacht


def punten(tekst):
    """(x, y) van elk symbool, label en tekstblok op het blad."""
    syms, rest = [], []
    for m in re.finditer(r'\(symbol\n\t\t\(lib_id "[^"]+"\)\n\t\t\(at ([\d.-]+) ([\d.-]+)',
                         tekst):
        syms.append((float(m.group(1)), float(m.group(2))))
    for m in re.finditer(r'\((?:global_label|text) "(?:[^"\\]|\\.)*"[^\n]*'
                         r'\(at ([\d.-]+) ([\d.-]+)', tekst):
        rest.append((float(m.group(1)), float(m.group(2))))
    return syms, rest


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    proj = sys.argv[1] if len(sys.argv) > 1 else "esp32ct-revc"
    fouten = []
    bladen = sorted(glob.glob(os.path.join(hier, proj, "*.kicad_sch")))
    if not bladen:
        print(f"FOUT: geen schemabladen gevonden in {proj}")
        return 1
    for pad in bladen:
        naam = os.path.basename(pad)
        t = open(pad, encoding="utf-8").read()
        syms, rest = punten(t)

        buiten = [p for p in syms + rest
                  if not (RAND <= p[0] <= A3[0] - RAND and RAND <= p[1] <= A3[1] - RAND)]
        if buiten:
            fouten.append(f"{naam}: {len(buiten)} element(en) buiten het blad, "
                          f"bv. {buiten[0]}")

        dichtbij = []
        for i, a in enumerate(syms):
            for b in syms[i + 1:]:
                if math.dist(a, b) < MINAFSTAND:
                    dichtbij.append((a, b))
        if dichtbij:
            fouten.append(f"{naam}: {len(dichtbij)} symboolpaar(en) < {MINAFSTAND} mm, "
                          f"bv. {dichtbij[0]}")

        print(f"{naam:34s} {len(syms):3d} symbolen  {len(rest):3d} labels/teksten")

    if fouten:
        print("\nLET OP:")
        for f in fouten:
            print("  -", f)
        return 1
    print("\nalles binnen het blad, geen symbolen bovenop elkaar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
