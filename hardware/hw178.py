#!/usr/bin/env python3
"""
Genereert lib/HW178_socket.kicad_mod: twee female headers waar een HW-178
multiplexer-breakout (CD74HC4067) plat in steekt.

Maten komen uit het Eagle-bordbestand van SparkFun's BOB-09056, waarvan het
HW-178 een kloon is, en zijn nagelegd tegen een foto van het HW-178 zelf:
  - 16-pinsrij C0..C15, steek 2,54
  - 8-pinsrij GND..SIG, 15,24 mm (6 x 2,54) van de andere rij
  - de korte rij ligt recht boven C4..C11: SIG boven C11, GND boven C4
  - bordje 17,78 x 40,64 mm

Oriëntatie zoals op de foto, bovenaanzicht, componenten naar boven:
  bovenrij  SIG S3 S2 S1 S0 EN VCC GND
  onderrij  C15 C14 ... C1 C0

LET OP: de padnummers zijn die van DEZE footprint, niet van de chip. Ze moeten
overeenkomen met het symbool HW178 in gen_sch.py. Pad 1..16 = C0..C15,
17 = SIG, 18 = EN, 19..22 = S0..S3, 23 = VCC, 24 = GND.

Draaien: python3 hw178.py
"""
import os

HIER = os.path.dirname(os.path.abspath(__file__))
UIT = os.path.join(HIER, "lib", "HW178_socket.kicad_mod")

P = 2.54
RIJAFSTAND = 6 * P          # 15,24 mm tussen de twee rijen

# Onderrij: C15 links op x=0, C0 rechts. Padnummer k+1 voor Ck.
ONDER = [(str(k + 1), f"C{k}", P * (15 - k), 0.0) for k in range(16)]

# Bovenrij, van links naar rechts, recht boven C11..C4.
BOVEN_VOLGORDE = [("17", "SIG"), ("22", "S3"), ("21", "S2"), ("20", "S1"),
                  ("19", "S0"), ("18", "EN"), ("23", "VCC"), ("24", "GND")]
BOVEN = [(nr, naam, P * (15 - 11) + P * i, -RIJAFSTAND)
         for i, (nr, naam) in enumerate(BOVEN_VOLGORDE)]

# Omtrek van het breakout-bordje zelf (17,78 x 40,64).
BX0, BX1 = -P / 2, P * 15 + P / 2
BY0, BY1 = -RIJAFSTAND - P / 2, P / 2


def lijn(x0, y0, x1, y1, laag, dikte):
    return (f'\t(fp_line\n\t\t(start {x0:.3f} {y0:.3f})\n\t\t(end {x1:.3f} {y1:.3f})\n'
            f'\t\t(stroke\n\t\t\t(width {dikte})\n\t\t\t(type solid)\n\t\t)\n'
            f'\t\t(layer "{laag}")\n\t)')


def rechthoek(x0, y0, x1, y1, laag, dikte):
    return "\n".join([lijn(x0, y0, x1, y0, laag, dikte), lijn(x1, y0, x1, y1, laag, dikte),
                      lijn(x1, y1, x0, y1, laag, dikte), lijn(x0, y1, x0, y0, laag, dikte)])


def tekst(t, x, y, laag, grootte=0.8):
    dik = round(grootte * 0.15, 3)
    return (f'\t(fp_text user "{t}"\n\t\t(at {x:.3f} {y:.3f} 0)\n\t\t(layer "{laag}")\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {grootte} {grootte})\n'
            f'\t\t\t\t(thickness {dik})\n\t\t\t)\n\t\t)\n\t)')


def pad(nr, x, y):
    vorm = "rect" if nr == "1" else "circle"
    return (f'\t(pad "{nr}" thru_hole {vorm}\n\t\t(at {x:.3f} {y:.3f})\n'
            f'\t\t(size 1.7 1.7)\n\t\t(drill 1)\n\t\t(layers "*.Cu" "*.Mask")\n'
            f'\t\t(remove_unused_layers no)\n\t)')


def main():
    delen = [
        '(footprint "HW178_socket"',
        '\t(version 20241229)',
        '\t(generator "esp32ct-gen")',
        '\t(generator_version "9.0")',
        '\t(layer "F.Cu")',
        '\t(descr "Twee female headers (1x16 en 1x8, steek 2,54, rijafstand 15,24 mm) '
        'voor een HW-178 / SparkFun BOB-09056 CD74HC4067-breakout, plat gemonteerd")',
        '\t(tags "HW-178 CD74HC4067 multiplexer breakout socket")',
        f'\t(property "Reference" "REF**"\n\t\t(at {P * 7.5:.3f} {BY0 - 1.5:.3f} 0)\n'
        '\t\t(layer "F.SilkS")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n'
        '\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)',
        f'\t(property "Value" "HW178_socket"\n\t\t(at {P * 7.5:.3f} {BY1 + 1.8:.3f} 0)\n'
        '\t\t(layer "F.Fab")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n'
        '\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)',
        '\t(attr through_hole)',
        # omtrek van het bordje: fab en zeefdruk, afbakening iets ruimer
        rechthoek(BX0, BY0, BX1, BY1, "F.Fab", 0.1),
        rechthoek(BX0 - 0.12, BY0 - 0.12, BX1 + 0.12, BY1 + 0.12, "F.SilkS", 0.12),
        rechthoek(BX0 - 0.5, BY0 - 0.5, BX1 + 0.5, BY1 + 0.5, "F.CrtYd", 0.05),
        # de twee female strips op de fab-laag
        rechthoek(-P / 2, -P / 2, P * 15 + P / 2, P / 2, "F.Fab", 0.1),
        rechthoek(BOVEN[0][2] - P / 2, -RIJAFSTAND - P / 2,
                  BOVEN[-1][2] + P / 2, -RIJAFSTAND + P / 2, "F.Fab", 0.1),
        # herkenning bij het insteken
        tekst("C15", 0, -2.4, "F.SilkS"),
        tekst("C0", P * 15, -2.4, "F.SilkS"),
        tekst("SIG", BOVEN[0][2], -RIJAFSTAND + 2.4, "F.SilkS"),
        tekst("GND", BOVEN[-1][2], -RIJAFSTAND + 2.4, "F.SilkS"),
        tekst("HW-178", P * 7.5, -RIJAFSTAND / 2, "F.SilkS", 1.0),
        tekst("${REFERENCE}", P * 7.5, -RIJAFSTAND / 2 + 2.5, "F.Fab", 1.0),
    ]
    for nr, _, x, y in ONDER + BOVEN:
        delen.append(pad(nr, x, y))
    delen.append(")")
    os.makedirs(os.path.dirname(UIT), exist_ok=True)
    with open(UIT, "w", encoding="utf-8") as f:
        f.write("\n".join(delen) + "\n")
    print(f"geschreven: {UIT}  ({len(ONDER) + len(BOVEN)} pads)")


if __name__ == "__main__":
    main()
