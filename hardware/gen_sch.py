#!/usr/bin/env python3
"""
Genereert het KiCad-project 'esp32ct-revc': het ontwerp van het nieuwe CT-bord.

Basis is het huidige bord (gereconstrueerd uit de ESPHome-firmware), met de
wijzigingen van 22-09-2026: 16 universele CT-kanalen in plaats van 22, geen
tweede multiplexer meer, schroefklemmen voor alles behalve de twee RJ12's, en
een nagebootste P1-uitgang naar de laadpaal.

Bewust een generator en geen handwerk. De CT-kanalen zijn repetitief; zo blijft
de bron van waarheid deze leesbare lijst in plaats van 20.000 regels s-expressie,
en is het schema opnieuw te bouwen zodra er iets aan het bord verandert.

Draaien:  python3 gen_sch.py
"""
import uuid as _uuid, os, datetime

NS = _uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
uid = lambda k: str(_uuid.uuid5(NS, k))
snap = lambda v: round(round(v / 1.27) * 1.27, 2)

LIB, PROJ = "esp32ct", "esp32ct-revc"

# Standaardfootprint per symbooltype; sheets.py vult dit. Een expliciete
# footprint bij sym() gaat hier altijd voor. Zonder footprint valt er geen
# PCB te maken, dus alles wat op het bord komt hoort hierin te staan.
DEFAULT_FP = {}
REV, DATE = "C", datetime.date.today().isoformat()
F = "(effects (font (size 1.27 1.27)))"
HID = '(effects (font (size 1.27 1.27)) (hide yes))'

# ============================================================== symbooldefinities
# 'box'  : rechthoek met benoemde pinnen links/rechts
# '2pin' : discreet onderdeel met eigen tekening
SYMDEF = {
 "R":   dict(k="2pin", ref="R", g="R", vert=True),
 # Eigen tekening: het lichaam moet liggen als de draden er van opzij in gaan.
 "R_H": dict(k="2pin", ref="R", g="R_H", vert=False),
 "C":   dict(k="2pin", ref="C", g="C", vert=True),
 "C_H": dict(k="2pin", ref="C", g="C", vert=False),
 "D":   dict(k="2pin", ref="D", g="D", vert=True),
 "LED": dict(k="2pin", ref="D", g="LED", vert=True),
 "JUMPER": dict(k="box", ref="JP", w=10.16,
   l=[("1","1","passive")], r=[("2","2","passive")]),
 # Voetje voor het HW-178-breakout, NIET de losse chip. De pinnummers zijn de
 # padnummers van footprint HW178_socket (zie hw178.py) en hebben niets met de
 # pinbezetting van de CD74HC4067 zelf te maken. Zet hier nooit een DIP- of
 # SOIC-footprint onder: dan klopt geen enkele pin, en hangt VCC aan GND.
 "HW178": dict(k="box", ref="U", w=35.56,
   l=[(str(i+1), f"C{i}", "passive") for i in range(16)],
   r=[("17","SIG","passive"),("18","~{EN}","input"),("19","S0","input"),("20","S1","input"),
      ("21","S2","input"),("22","S3","input"),("23","VCC","power_in"),("24","GND","power_in")]),
 # Pinnummers volgens de ECHTE LM358 (gecontroleerd tegen KiCad's eigen symbool):
 # 1 OUT A, 2 IN- A, 3 IN+ A, 4 V-, 5 IN+ B, 6 IN- B, 7 OUT B, 8 V+.
 # Tot 23-09-2026 stonden 2 en 3 hier verwisseld; de VBIAS-volger had dan
 # meekoppeling gekregen en was tegen een voedingsrail vastgelopen.
 "LM358": dict(k="box", ref="U", w=25.4,
   l=[("3","1IN+","input"),("2","1IN-","input"),("6","2IN-","input"),
      ("5","2IN+","input"),("4","V-","power_in")],
   r=[("1","1OUT","output"),("7","2OUT","output"),("8","V+","power_in")]),
 # Pinnummers zijn de ECHTE padnummers van de module, zodat het symbool op de
 # footprint ESP32_mini past. Pad 1-20 zitten links op het bord, 21-40 rechts.
 # Bron: r0oland/ESP32_mini_KiCad_Library (Apache 2.0) - zie lib/.
 "ESP32_MINIKIT": dict(k="box", ref="U", w=38.1,
   l=[("1","GND","power_in"),("2","RST/EN","input"),("3","NC","no_connect"),
      ("4","IO36/SVP","input"),("5","IO39/SVN","input"),("6","IO26","bidirectional"),
      ("7","IO35/ADC1_7","input"),("8","IO18","bidirectional"),
      ("9","IO33","bidirectional"),("10","IO19","bidirectional"),
      ("11","IO34/ADC1_6","input"),("12","IO23","bidirectional"),
      ("13","IO14","bidirectional"),("14","IO05","bidirectional"),
      ("15","NC","no_connect"),("16","3V3","power_out"),
      ("17","IO09/SD2","bidirectional"),("18","IO13","bidirectional"),
      ("19","CMD","bidirectional"),("20","IO10/SD3","bidirectional")],
   r=[("21","TXD","output"),("22","GND","power_in"),("23","RXD","input"),
      ("24","IO27","bidirectional"),("25","IO22","bidirectional"),
      ("26","IO25","bidirectional"),("27","IO21","bidirectional"),
      ("28","IO32","bidirectional"),("29","IO17","bidirectional"),
      ("30","IO12 (strap)","bidirectional"),("31","IO16","bidirectional"),
      ("32","IO04","bidirectional"),("33","GND","power_in"),
      ("34","IO00","bidirectional"),("35","VCC (USB)","power_in"),
      ("36","IO02","bidirectional"),("37","TD0","bidirectional"),
      ("38","SD1","bidirectional"),("39","SD0","bidirectional"),
      ("40","CLK","bidirectional")]),
 "SCREW_2": dict(k="box", ref="J", w=10.16, l=[],
   r=[("1","1","passive"),("2","2","passive")]),
 "CONN_3": dict(k="box", ref="J", w=10.16, l=[],
   r=[("1","1","passive"),("2","2","passive"),("3","3","passive")]),
 "RJ12": dict(k="box", ref="J", w=15.24, l=[],
   r=[(str(i),str(i),"passive") for i in range(1,7)]),
 "PC817": dict(k="box", ref="U", w=17.78,
   l=[("1","A","passive"),("2","K","passive")],
   r=[("4","C","passive"),("3","E","passive")]),
 # Pinnummers volgens de ECHTE BC547 in TO-92 (gecontroleerd tegen KiCad's
 # eigen symbool): 1 = C, 2 = B, 3 = E. Andere NPN's hebben vaak E-B-C (S8050,
 # 2N3904) - gebruik je die, dan moet deze volgorde mee.
 # Tot 23-09-2026 stond hier 1 = B, 2 = C: beide P1-transistors verkeerd.
 "Q_NPN": dict(k="box", ref="Q", w=12.7, l=[("2","B","input")],
   r=[("1","C","passive"),("3","E","passive")]),
 "CONN_4": dict(k="box", ref="J", w=10.16, l=[],
   r=[("1","1","passive"),("2","2","passive"),("3","3","passive"),("4","4","passive")]),
 # Vertelt de ERC dat deze rail van buiten het schema gevoed wordt; er zit
 # geen echt onderdeel achter.
 "PWR_FLAG": dict(k="flag", ref="#FLG"),
}

GRAPHIC = {
 "R": '\t\t\t\t(rectangle (start -1.016 -2.54) (end 1.016 2.54)\n'
      '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))',
 "R_H": '\t\t\t\t(rectangle (start -2.54 -1.016) (end 2.54 1.016)\n'
        '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))',
 "C": '\t\t\t\t(polyline (pts (xy -2.032 0.508) (xy 2.032 0.508))\n'
      '\t\t\t\t\t(stroke (width 0.508) (type default)) (fill (type none)))\n'
      '\t\t\t\t(polyline (pts (xy -2.032 -0.508) (xy 2.032 -0.508))\n'
      '\t\t\t\t\t(stroke (width 0.508) (type default)) (fill (type none)))',
 "D": '\t\t\t\t(polyline (pts (xy -1.27 1.27) (xy 1.27 1.27))\n'
      '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))\n'
      '\t\t\t\t(polyline (pts (xy 1.27 -1.27) (xy -1.27 -1.27) (xy 0 1.27) (xy 1.27 -1.27))\n'
      '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type outline)))',
}
GRAPHIC["D_UP"] = (
 '\t\t\t\t(polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27))\n'
 '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none)))\n'
 '\t\t\t\t(polyline (pts (xy 1.27 1.27) (xy -1.27 1.27) (xy 0 -1.27) (xy 1.27 1.27))\n'
 '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type outline)))')
GRAPHIC["LED_UP"] = (GRAPHIC["D_UP"] + '\n'
 '\t\t\t\t(polyline (pts (xy 1.778 -1.778) (xy 3.048 -3.048))\n'
 '\t\t\t\t\t(stroke (width 0.152) (type default)) (fill (type none)))\n'
 '\t\t\t\t(polyline (pts (xy 2.286 -0.508) (xy 3.556 -1.778))\n'
 '\t\t\t\t\t(stroke (width 0.152) (type default)) (fill (type none)))')
GRAPHIC["LED"] = (GRAPHIC["D"] + '\n'
 '\t\t\t\t(polyline (pts (xy 1.778 1.778) (xy 3.048 3.048))\n'
 '\t\t\t\t\t(stroke (width 0.152) (type default)) (fill (type none)))\n'
 '\t\t\t\t(polyline (pts (xy 2.286 0.508) (xy 3.556 1.778))\n'
 '\t\t\t\t\t(stroke (width 0.152) (type default)) (fill (type none)))')


def geom(name):
    """Pinposities in symboolcoordinaten (y omhoog positief)."""
    d = SYMDEF[name]
    if d["k"] == "flag":
        return {"1": (0, 0)}
    if d["k"] == "2pin":
        return ({"1": (0, 3.81), "2": (0, -3.81)} if d["vert"]
                else {"1": (-3.81, 0), "2": (3.81, 0)})
    w, top = d["w"], max(max(len(d["l"]), len(d["r"])) * 2.54 + 2.54, 7.62) / 2
    p = {}
    for i, (num, _, _) in enumerate(d["l"]):
        p[num] = (-w / 2 - 2.54, top - 2.54 * (i + 1))
    for i, (num, _, _) in enumerate(d["r"]):
        p[num] = (w / 2 + 2.54, top - 2.54 * (i + 1))
    return p


PWR_FLAG_SYM = '''\t\t(symbol "%s"
\t\t\t(power)
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0) (hide yes))
\t\t\t(exclude_from_sim no) (in_bom no) (on_board yes)
\t\t\t(property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Value" "PWR_FLAG" (at 0 4.445 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "PWR_FLAG_0_0"
\t\t\t\t(pin power_out line (at 0 0 90) (length 0)
\t\t\t\t\t(name "~" (effects (font (size 1.27 1.27))))
\t\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))
\t\t\t\t)
\t\t\t)
\t\t\t(symbol "PWR_FLAG_0_1"
\t\t\t\t(polyline
\t\t\t\t\t(pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27))
\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type none))
\t\t\t\t)
\t\t\t)
\t\t)'''


def build_symbol(name, bare=False):
    """bare=True levert de naam zonder bibliotheekprefix, voor .kicad_sym."""
    ident = name if bare else f"{LIB}:{name}"
    if SYMDEF[name]["k"] == "flag":
        return PWR_FLAG_SYM % ident
    d = SYMDEF[name]
    head = [f'\t\t(symbol "{ident}"']
    if d["k"] == "2pin":
        head += ['\t\t\t(pin_numbers (hide yes))', '\t\t\t(pin_names (offset 0) (hide yes))']
        rx, ry = 2.54, 1.27
    else:
        head += ['\t\t\t(pin_numbers)', '\t\t\t(pin_names (offset 1.016))']
        w, top = d["w"], max(max(len(d["l"]), len(d["r"])) * 2.54 + 2.54, 7.62) / 2
        rx, ry = -w / 2, top + 2.54
    head += ['\t\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
             f'\t\t\t(property "Reference" "{d["ref"]}" (at {rx} {ry} 0) {F})',
             f'\t\t\t(property "Value" "{name}" (at {rx} {-ry if d["k"]=="2pin" else ry+2.54} 0) {F})',
             f'\t\t\t(property "Footprint" "" (at 0 0 0) {HID})',
             f'\t\t\t(property "Datasheet" "" (at 0 0 0) {HID})',
             f'\t\t\t(property "Description" "" (at 0 0 0) {HID})']
    body = [f'\t\t\t(symbol "{name}_0_1"']
    if d["k"] == "2pin":
        body.append(GRAPHIC[d["g"]])
    else:
        body.append(f'\t\t\t\t(rectangle (start {-w/2} {top}) (end {w/2} {-top})\n'
                    '\t\t\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))')
    body.append('\t\t\t)')
    pos, pins = geom(name), [f'\t\t\t(symbol "{name}_1_1"']
    if d["k"] == "2pin":
        lst = [("1", "~", "passive"), ("2", "~", "passive")]
    else:
        lst = d["l"] + d["r"]
    for num, pname, et in lst:
        x, y = pos[num]
        if d["k"] == "2pin":
            ang = (270 if y > 0 else 90) if d["vert"] else (0 if x < 0 else 180)
            ln = 1.27
        else:
            ang, ln = (0 if x < 0 else 180), 2.54
        pins.append(f'\t\t\t\t(pin {et} line (at {x} {y} {ang}) (length {ln})\n'
                    f'\t\t\t\t\t(name "{pname}" {F})\n\t\t\t\t\t(number "{num}" {F})\n\t\t\t\t)')
    pins.append('\t\t\t)')
    return '\n'.join(head + body + pins + ['\t\t)'])


def write_library(path, names):
    """Projecteigen symboolbibliotheek, zodat KiCad de symbolen terugvindt."""
    body = "\n".join(build_symbol(n, bare=True) for n in sorted(names))
    with open(path, "w", encoding="utf-8") as f:
        f.write('(kicad_symbol_lib\n\t(version 20241209)\n'
                '\t(generator "esp32ct-gen")\n\t(generator_version "9.0")\n'
                + body + "\n)\n")


def write_lib_table(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write('(sym_lib_table\n\t(version 7)\n'
                f'\t(lib (name "{LIB}")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/{LIB}.kicad_sym")(options "")'
                '(descr "Symbolen voor het esp32ct-bord"))\n)\n')


def write_fp_table(path):
    """Projecteigen footprintbibliotheek: alleen de ESP32-module zit erin,
    de rest komt uit de standaardbibliotheken van KiCad."""
    with open(path, "w", encoding="utf-8") as f:
        f.write('(fp_lib_table\n\t(version 7)\n'
                f'\t(lib (name "{LIB}")(type "KiCad")'
                f'(uri "${{KIPRJMOD}}/{LIB}.pretty")(options "")'
                '(descr "Footprints voor het esp32ct-bord"))\n)\n')


# ==================================================================== tekenblad
class Sheet:
    def __init__(self, fname, title, paper="A3", page="1"):
        self.fname, self.title, self.paper, self.page = fname, title, paper, page
        self.uuid = uid("sheet/" + fname)          # uuid van het BESTAND
        self.sheet_uuid = uid("sheetsym/" + fname) # uuid van het bladsymbool in root
        self.path = "/" + self.uuid                # overschreven voor subbladen
        self.items, self.used, self.n, self.subsheets = [], set(), 0, []

    def _u(self, tag):
        self.n += 1
        return uid(f"{self.fname}/{tag}/{self.n}")

    def at(self, ref_uuid_xy, pinnum):
        x, y, kind = ref_uuid_xy
        px, py = geom(kind)[pinnum]
        return (round(x + px, 2), round(y - py, 2))

    def sym(self, kind, ref, value, x, y, footprint="", descr="", dnp=False):
        x, y = snap(x), snap(y)
        self.used.add(kind)
        u = self._u(ref)
        props = ""
        footprint = footprint or DEFAULT_FP.get(kind, "")
        if footprint:
            props += f'\n\t\t(property "Footprint" "{footprint}" (at {x} {y} 0) {HID})'
        if descr:
            props += f'\n\t\t(property "Description" "{descr}" (at {x} {y} 0) {HID})'
        pins = "".join(f'\n\t\t(pin "{n}" (uuid "{uid(u + n)}"))' for n in geom(kind))
        ry = -2.54 if SYMDEF[kind]["k"] == "box" else -1.27
        dnp_s = " (dnp yes)" if dnp else " (dnp no)"
        self.items.append(
            f'\t(symbol\n\t\t(lib_id "{LIB}:{kind}")\n\t\t(at {x} {y} 0)\n\t\t(unit 1)'
            f'\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes){dnp_s}'
            f'\n\t\t(uuid "{u}")'
            f'\n\t\t(property "Reference" "{ref}" (at {x} {y + ry - 2.54} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left)))'
            f'\n\t\t(property "Value" "{value}" (at {x} {y + ry} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left))){props}{pins}'
            f'\n\t\t(instances\n\t\t\t(project "{PROJ}"'
            f'\n\t\t\t\t(path "{self.path}" (reference "{ref}") (unit 1))\n\t\t\t)\n\t\t)\n\t)')
        return (x, y, kind)

    def wire(self, *pts):
        for a, b in zip(pts, pts[1:]):
            self.items.append(
                f'\t(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]}))'
                f' (stroke (width 0) (type default)) (uuid "{self._u("w")}"))')

    def junction(self, p):
        self.items.append(f'\t(junction (at {p[0]} {p[1]}) (diameter 0) (color 0 0 0 0)'
                          f' (uuid "{self._u("j")}"))')

    def no_connect(self, p):
        self.items.append(f'\t(no_connect (at {p[0]} {p[1]})'
                          f' (uuid "{self._u("nc")}"))')

    def label(self, text, p, rot=0, just="left"):
        self.items.append(
            f'\t(global_label "{text}" (shape passive) (at {p[0]} {p[1]} {rot})'
            f'\n\t\t(effects (font (size 1.27 1.27)) (justify {just}))'
            f'\n\t\t(uuid "{self._u("gl")}")'
            f'\n\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at 0 0 0) {HID})\n\t)')

    def note(self, text, x, y, size=1.27):
        # KiCad wil regeleindes als de twee tekens \ en n binnen de quotes;
        # een echt regeleinde in de string laat het bestand niet laden.
        esc = (text.replace("\\", "\\\\").replace('"', '\\"')
                   .replace("\n", "\\n"))
        self.items.append(
            f'\t(text "{esc}" (at {x} {y} 0)'
            f'\n\t\t(effects (font (size {size} {size})) (justify left top))'
            f'\n\t\t(uuid "{self._u("t")}")\n\t)')

    def sheet_ref(self, child, x, y, w=45.72, h=17.78):
        self.subsheets.append(child)
        self.items.append(
            f'\t(sheet\n\t\t(at {x} {y})\n\t\t(size {w} {h})'
            f'\n\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)'
            f'\n\t\t(stroke (width 0.1524) (type solid))\n\t\t(fill (color 0 0 0 0.0000))'
            f'\n\t\t(uuid "{child.sheet_uuid}")'
            f'\n\t\t(property "Sheetname" "{child.title}" (at {x} {y - 0.71} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left bottom)))'
            f'\n\t\t(property "Sheetfile" "{child.fname}" (at {x} {y + h + 1.27} 0)'
            f' (effects (font (size 1.27 1.27)) (justify left top)))'
            f'\n\t\t(instances\n\t\t\t(project "{PROJ}"'
            f'\n\t\t\t\t(path "{self.path}" (page "{child.page}"))\n\t\t\t)\n\t\t)\n\t)')

    def render(self, root=False, pages=None):
        libs = "\n".join(build_symbol(k) for k in sorted(self.used))
        out = ['(kicad_sch', '\t(version 20250114)', '\t(generator "esp32ct-gen")',
               '\t(generator_version "9.0")', f'\t(uuid "{self.uuid}")',
               f'\t(paper "{self.paper}")', '\t(title_block',
               f'\t\t(title "esp32ct rev {REV} \u2014 {self.title}")',
               f'\t\t(date "{DATE}")', f'\t\t(rev "{REV}")',
               '\t\t(comment 1 "Ontwerp. Basis: het huidige bord plus de wijzigingen van 22-09-2026.")',
               '\t\t(comment 2 "Waarden met (?) zijn NIET van het bord afgelezen - zie OPEN PUNTEN.")',
               '\t\t(comment 3 "Gegenereerd door gen_sch.py - pas dat script aan, niet dit bestand.")',
               '\t)', '\t(lib_symbols', libs, '\t)'] + self.items
        if root:
            si = '\n'.join(f'\t\t(path "{p}" (page "{n}"))' for p, n in pages)
            out.append(f'\t(sheet_instances\n{si}\n\t)')
        out += ['\t(embedded_fonts no)', ')', '']
        return '\n'.join(out)
