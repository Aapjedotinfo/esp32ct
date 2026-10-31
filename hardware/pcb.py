#!/usr/bin/env python3
"""
Bouwt esp32ct-revc.kicad_pcb uit de netlist: bordomtrek, alle footprints op hun
plek, elk pad op het juiste net, en een koperverbod onder de ESP32-antenne.
De banen legt dit script NIET - dat is handwerk of de autorouter.

Draaien met de Python van KiCad, niet met die van het systeem - alleen die
heeft de pcbnew-module. Het versienummer staat nergens vast; build.sh pakt de
nieuwste installatie en dit script leidt de footprintmap af uit sys.executable:
  "/c/Program Files/KiCad/<versie>/bin/python.exe" pcb.py

Bordmaat: standaard BORD_B x BORD_H hieronder. Voor het zoeken naar de kleinste
maat kun je ze overschrijven met de omgevingsvariabelen PCB_B en PCB_H.

Uitgangspunten voor de indeling:
  - alle schroefklemmen en beide RJ12's aan de rand, met de opening naar buiten
  - de 16 CT-kanalen langs de twee lange zijden, met hun burden en jumper er
    direct achter, zodat de gevoelige lus kort blijft
  - het HW-178-voetje midden tussen de twee CT-rijen, de middenrail links
  - de ESP32 aan de rechterrand met de antenne naar buiten, voor de ontvangst
  - beide RJ12's naast elkaar rechtsboven, met hun P1-schakelingen eronder
"""
import os, re, sys, math
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netlist

HIER = os.path.dirname(os.path.abspath(__file__))
PROJ = "esp32ct-revc"
UIT = os.path.join(HIER, PROJ)
NET = os.path.join(UIT, PROJ + ".net")


def kicad_footprints():
    """De standaard-footprintmap van de KiCad waaronder dit script draait."""
    wortel = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    pad = os.path.join(wortel, "share", "kicad", "footprints")
    if os.path.isdir(pad):
        return pad
    for k, v in os.environ.items():
        if re.fullmatch(r"KICAD\d+_FOOTPRINT_DIR", k) and os.path.isdir(v):
            return v
    raise SystemExit(f"footprintmap niet gevonden; gezocht in {pad}")


KICAD_FP = kicad_footprints()

BORD_B = float(os.environ.get("PCB_B", 115))
BORD_H = float(os.environ.get("PCB_H", 103))

# --- oriëntatie van de randconnectoren --------------------------------------
# Schroefklem (MaiXu MX126): de draadinvoer zit aan de +Y-kant van de
# footprint - de pads liggen 3,80 mm van die rand en 4,00 mm van de andere, en
# de fab-laag tekent daar een aparte band. Niet aan een echt blokje nagemeten;
# klopt het niet, zet INVOER op 0 en alle klemmen draaien in een keer om.
INVOER = 180
BOVEN, ONDER = INVOER, (INVOER + 180) % 360
LINKS, RECHTS = (INVOER + 90) % 360, (INVOER + 270) % 360

# RJ12 (Amphenol 54601): de pinnen zitten achterin op Y = 0..2,5, het lichaam
# loopt door tot Y = 16,8. De stekker gaat er dus aan de +Y-kant in. Dat is
# wel zeker: aan de pinkant kan geen stekker in.
RJ_BOVEN, RJ_ONDER, RJ_RECHTS = 180, 0, 90

# --- montagegaten: 4x M3 in de hoeken ----------------------------------------
GAT = 4.5                  # hart van het gat tot beide randen
GAT_FP = "MountingHole:MountingHole_3.2mm_M3"

# --- CT-kanalen: acht boven, acht onder -------------------------------------
# Begint op x = 14: links in de hoeken zitten de montagegaten.
# Met staande burdens bepaalt de klem zelf de steek. De klemmen staan vrijwel
# tegen elkaar: body 10,5 mm, steek 10,795 mm, ~0,3 mm lucht ertussen. Daarom
# een eigen footprint met de courtyard op de body (lib/MX126_2P_5mm_krap).
# Een veelvoud van het routeraster (17 x 0,635), zodat pin 1 van elk kanaal
# even ver verschuift; bij 12,5 raakten door die afronding onderdelen elkaar.
CT_STAP = 10.795
CT_X = [14 + CT_STAP * i for i in range(8)]
Y_KLEM, Y_BURDEN = 6.0, 16.0           # gemeten vanaf de eigen bordrand
DX_BURDEN = 2.54                       # burden onder pin 1, jumper onder pin 2


KLEM_Y0 = 26.5     # y van J1, net onder de bovenste CT-band plus zijn titel
P1 = 25.0          # y van de bovenste rij P1-onderdelen, onder de CT-rij
P1_A, P1_B = 79.5, 89.3    # x van hun twee kolommen


def plaatsing(B, H):
    """Alle posities als (x, y, rotatie) van het middelpunt van de courtyard."""
    mid = H / 2
    p = {}
    for i, x in enumerate(CT_X):
        # Staande burden en jumper naast elkaar in een rij onder de klem: de
        # burden onder pin 1 (het meetpunt), de jumper onder pin 2 (VBIAS).
        # Boven zit pin 1 rechts, onder links; de onderste rij is gespiegeld.
        p[f"J{11 + i}"] = (x, Y_KLEM, BOVEN)
        p[f"R{101 + i}"] = (x + DX_BURDEN, Y_BURDEN, 270)
        p[f"JP{101 + i}"] = (x - DX_BURDEN, Y_BURDEN, 0)
        p[f"J{19 + i}"] = (x, H - Y_KLEM, ONDER)
        p[f"R{109 + i}"] = (x - DX_BURDEN, H - Y_BURDEN, 90)
        p[f"JP{109 + i}"] = (x + DX_BURDEN, H - Y_BURDEN, 180)

    p.update({
        # linkerrand: voeding, watermeter en de relais, van boven naar onder,
        # tussen de twee CT-banden in. Klemmen die bij elkaar horen staan
        # 11,43 mm uit elkaar, tussen twee groepen zit 13,335 mm voor de titel
        # (POWER IN, WATER, RELAIS). Beide veelvouden van het routeraster, zodat
        # het afronden van pin 1 de klemmen niet tegen elkaar schuift.
        "J1": (7, KLEM_Y0, LINKS),
        "J3": (7, KLEM_Y0 + 13.335, LINKS),
        "J9": (7, KLEM_Y0 + 13.335 + 11.43, LINKS),
        "J4": (7, KLEM_Y0 + 2 * 13.335 + 11.43, LINKS),
        "J5": (7, KLEM_Y0 + 2 * 13.335 + 2 * 11.43, LINKS),
        # zekering F1 (0 Ω-brug) rechts boven de voedingsklem, boven de opamp
        "F1": (18, 22.5, 0),
        "R18": (36, mid - 1, 90),             # pull-up watermeter naar 3,3 V

        # 1,65 V middenrail, direct naast de klemmen
        "U2": (22, mid - 17, 0),
        "C1": (19, mid - 5, 0),
        "C2": (28, mid - 5, 0),
        "R1": (24, mid + 3, 0),
        "R2": (24, mid + 8, 0),
        "C3": (21, mid + 17, 0),

        # HW-178 in het midden tussen de twee CT-rijen, zodat de CT-lijnen van
        # boven en onder even kort zijn. Staand: C0-C7 boven (waar CT1-8
        # vandaan komen), C8-C15 onder (CT9-16). Liggend moesten de acht
        # bovenste CT-lijnen om het hele voetje heen.
        "U3": ((CT_X[0] + CT_X[-1]) / 2, mid, 90),

        # Beide RJ12's onder elkaar op de rechterrand, opening naar buiten.
        # Zo staat er op de bovenrand alleen de CT-rij en kan het bord ~30 mm
        # smaller. P1 vanaf de meter boven, de nagebootste P1 naar de laadpaal
        # eronder. Niet direct tegen montagegat H2 aan: ~6 mm lucht, zodat de
        # schroefkop en een stekker elkaar niet hinderen.
        "J2": (B - 9.4, 21.5, RJ_RECHTS),
        "J8": (B - 9.4, 36.1, RJ_RECHTS),

        # ESP32 aan de rechterrand onder de RJ12's, gedraaid met de antenne
        # naar buiten: aan drie kanten van de antenne dan geen koper en geen
        # connectoren. De USB-kant wijst naar binnen, naar de mux.
        "U1": (B - 22.6, P1 + 41.5, 270),

        # P1-onderdelen zo ver mogelijk naar rechts, tegen de RJ12's aan. Het
        # vak links ervan, rechts van de mux, is de doorgang voor de CT-lijnen
        # 6-8 naar de mux; stonden daar onderdelen, dan kwam CT8 er niet door.
        # Weerstanden 5 mm onder elkaar: bij 4 mm viel de referentie op de
        # weerstand erboven.
        # rechts, bij de pinnen van de RJ12's: de weerstanden van beide ingangen
        "R3": (P1_B, P1, 0),
        "R4": (P1_B, P1 + 5, 0),
        "R13": (P1_B, P1 + 10, 0),
        "R14": (P1_B, P1 + 15, 0),
        "R15": (P1_B, P1 + 20, 0),
        # links daarvan, rechtop: de rest van de laadpaaluitgang, de twee
        # transistors en de 5V-jumper
        "R17": (P1_A + 1.7, P1 + 5.5, 90),
        "R16": (P1_A - 3.0, P1 + 5.5, 90),
        "Q1": (P1_A, P1 + 15, 0),
        "Q4": (P1_A, P1 + 22, 0),
        "JP1": (P1_A - 6, P1 + 18, 0),
        # zekering F2 op die 5 V, direct links van JP1. Liggend en rechtop
        # (rev C; was staand), zodat hij de CT-lijnen links ervan niet in de
        # weg zit; de uitleg "5V NAAR P1 OUT" komt eronder.
        "F2": (P1_A - 10, P1 + 18, 90),

        # onderrand: deurbelknop, als negende klem achter CT16
        "J6": (CT_X[-1] + CT_STAP, H - Y_KLEM, ONDER),
    })
    return p


# Gebied onder de antenne van de ESP32-module waar geen koper mag komen, in
# footprint-coördinaten. Zo getekend (gearceerd, "NO COPPER - KEEP OUT") in de
# footprint van r0oland.
ANTENNE = [(-15.24, -19.05), (15.24, -19.05), (15.24, -12.70), (-15.24, -12.70)]


def laad_footprint(spec):
    lib, naam = spec.split(":", 1)
    pad = os.path.join(UIT, lib + ".pretty") if lib == "esp32ct" \
        else os.path.join(KICAD_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(pad, naam)
    if fp is None:
        raise SystemExit(f"footprint niet gevonden: {spec}")
    return fp


def mm(v):
    return pcbnew.FromMM(float(v))


def lichaam(fp):
    """Omhullende van de courtyard; zonder courtyard die van de hele footprint."""
    c = fp.GetCourtyard(pcbnew.F_CrtYd)
    if c.OutlineCount():
        return c.BBox()
    return fp.GetBoundingBox(False, False)


# Raster van route.py. Pin 1 van elk onderdeel komt hierop te liggen; omdat de
# meeste footprints een steek van 1,27 of 2,54 hebben, vallen hun andere pinnen
# - en de middens ertussen - dan ook op het raster. Zonder dat viel het
# dichtstbijzijnde roosterpunt tussen twee ESP32-pinnen 1,10 mm van een pad,
# te dichtbij, en kon de router niet uit de binnenste pinrijen weg.
RASTER = 0.635


def zet_op(fp, x, y, rot):
    """Plaatst op het middelpunt van de courtyard, niet op de oorsprong, en
    schuift daarna pin 1 op het routeraster.

    De oorsprong van een klemmenblok ligt op pad 1, die van een RJ12 op de
    pinnen achterin. Zonder deze correctie schuift alles een paar millimeter op.
    """
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    mid = lichaam(fp).Centre()
    fp.Move(pcbnew.VECTOR2I(mm(x) - mid.x, mm(y) - mid.y))
    pads = {p.GetNumber(): p for p in fp.Pads()}
    if "1" in pads:
        p = pads["1"].GetPosition()
        px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        fp.Move(pcbnew.VECTOR2I(mm(round(px / RASTER) * RASTER - px),
                                mm(round(py / RASTER) * RASTER - py)))


def naar_bord(fp, punten):
    """Zet footprint-coördinaten om naar bordcoördinaten.

    Afgeleid uit twee pads waarvan de lokale positie vastligt, zodat het klopt
    voor elke rotatie zonder zelf de draairichting van KiCad te hoeven kennen.
    """
    pads = {p.GetNumber(): p for p in fp.Pads()}
    a_l, b_l = (-13.97, -11.43), (13.97, 11.43)            # pad 1 en pad 40
    a_b = [pcbnew.ToMM(v) for v in (pads["1"].GetPosition().x, pads["1"].GetPosition().y)]
    b_b = [pcbnew.ToMM(v) for v in (pads["40"].GetPosition().x, pads["40"].GetPosition().y)]
    hoek = (math.atan2(b_b[1] - a_b[1], b_b[0] - a_b[0])
            - math.atan2(b_l[1] - a_l[1], b_l[0] - a_l[0]))
    c, s = math.cos(hoek), math.sin(hoek)
    uit = []
    for px, py in punten:
        dx, dy = px - a_l[0], py - a_l[1]
        uit.append((a_b[0] + c * dx - s * dy, a_b[1] + s * dx + c * dy))
    return uit


def antenne_verbod(bord, esp):
    """Regelgebied onder de antenne: geen koper, geen banen, geen via's."""
    z = pcbnew.ZONE(bord)
    lagen = pcbnew.LSET()
    lagen.AddLayer(pcbnew.F_Cu)
    lagen.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(lagen)
    z.SetIsRuleArea(True)
    z.SetZoneName("antenne ESP32")
    # KiCad 9 heet het CopperPour, KiCad 10 ZoneFills.
    for naam in ("SetDoNotAllowZoneFills", "SetDoNotAllowCopperPour"):
        if hasattr(z, naam):
            getattr(z, naam)(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    o = z.Outline()
    o.NewOutline()
    for x, y in naar_bord(esp, ANTENNE):
        o.Append(mm(x), mm(y))
    bord.Add(z)


# --- zeefdruk bij de aansluitingen -------------------------------------------
# Per pad een label. De tekst volgt het NET op de pad, niet de pinvolgorde:
# wisselt die ooit in het schema, dan verhuist de opdruk vanzelf mee en kan hij
# nooit iets anders zeggen dan wat er op het koper zit.
PINLABELS = {
    "J4":  {"+5V": "5V", "GND": "GND"},
    "J5":  {"BEL_HUIS": "BEL1", "BEL_GARAGE": "BEL2"},
    "J1":  {"+5V_IN": "5V", "GND": "GND"},
    "J3":  {"+5V": "5V", "WATER_PULS": "PULS"},
    "J9":  {"GND": "GND"},
    "J6":  {"BEL_IN": "KNOP", "GND": "GND"},
}
# Eén label per blok: bij een CT-klem gaat het om het kanaal, niet om de pool.
BLOKLABELS = {f"J{10 + n}": f"CT{n}" for n in range(1, 17)}
# De twee RJ12's zien er hetzelfde uit; een verwisseling stuurt de laadpaal
# echte meterdata of de ESP de nepdata. Dus hun functie erbij, niet J2/J8.
BLOKLABELS.update({"J2": "P1 INPUT", "J8": "P1 OUTPUT"})
# Standaard staat een bloklabel boven het blok (of eronder op de bovenrand).
# J2 en J8 staan tegen elkaar op de rechterrand: J8 krijgt zijn naam eronder.
LABEL_ONDER = {"J8"}
# Titel boven een klem, voor klemmen die bij elkaar horen. J3 en J9 zijn samen
# de watermeter; zonder titel zijn twee losse blokjes met GND GND een raadsel.
TITELS = {"J3": "WATER", "J1": "POWER IN", "J4": "RELAIS"}

# Uitleg onder een onderdeel dat niet aan de rand staat, voor jumpers waarvan
# je anders moet raden wat ze doen. F2 + JP1 zetten 5 V op pin 1 van de
# P1-uitgang; JP1 open als de laadpaal zichzelf voedt. De tekst staat
# in twee regels onder F2 en JP1; op een regel liep hij over Q4.
UITLEG = {"F2": "5V NAAR" + chr(10) + "P1 OUT"}

TEKST, MARGE = 1.0, 0.8        # letterhoogte en afstand tot de courtyard, mm


# --- waarden op de zeefdruk (rev C) -------------------------------------------
# Wie het bord zelf bestukt, wil bij elk onderdeel zien wat erin moet, zonder
# de stuklijst ernaast. De tekst komt uit de waarde in het schema, zodat hij
# nooit iets anders kan zeggen dan de stuklijst. Een "(?)" daar betekent
# "niet nagemeten op het oude bord"; op de zeefdruk staat de ontwerpwaarde.
# Waar het staat hangt van de vorm af:
#   - liggende weerstand/zekering: in het lijf (de referentie staat erboven)
#   - staande burden: in de spleet tussen burden en jumper, rechtop
#   - condensator: eronder
#   - transistor: op één regel met de referentie; boven en onder zit geen plek
#   - opamp: in het lijf van de DIP
def waarde_tekst(ref, waarde):
    w = re.sub(r"\s*\(\?\)", "", waarde).strip()
    if ref.startswith("C"):
        m = re.fullmatch(r"(\d+)([pnu])", w)
        if m:
            w = m.group(1) + {"p": "p", "n": "n", "u": "µ"}[m.group(2)] + "F"
    return w


def veld(t, tekst, x, y, hoek=0, uitlijnen=pcbnew.GR_TEXT_H_ALIGN_CENTER):
    t.SetText(tekst)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetVisible(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(TEKST), mm(TEKST)))
    t.SetTextThickness(mm(0.15))
    t.SetHorizJustify(uitlijnen)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(hoek)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))


def padmidden(fp):
    ps = [p.GetPosition() for p in fp.Pads()]
    return (pcbnew.ToMM(sum(p.x for p in ps) / len(ps)),
            pcbnew.ToMM(sum(p.y for p in ps) / len(ps)))


def waarden(fps):
    for ref, fp in fps.items():
        if not (re.fullmatch(r"[RCFQ]\d+", ref) or ref == "U2"):
            continue
        tekst = waarde_tekst(ref, fp.GetValue())
        naam = fp.GetFPID().GetLibItemName().wx_str()
        cx, cy = padmidden(fp)
        cb = lichaam(fp)
        if ref[0] in "RF" and "Horizontal" in naam:
            veld(fp.Value(), tekst, cx, cy, fp.GetOrientationDegrees() % 180)
        elif ref[0] == "R" and "Vertical" in naam:
            jp = fps["JP" + ref[1:]]
            jx, _ = padmidden(jp)
            veld(fp.Value(), tekst, (cx + jx) / 2, cy, 90)
        elif ref[0] == "C":
            veld(fp.Value(), tekst, pcbnew.ToMM(cb.Centre().x),
                 pcbnew.ToMM(cb.GetBottom()) + 0.3 + TEKST / 2)
        elif ref[0] == "Q":
            # referentie en type samen gecentreerd op de plek van de referentie
            r = fp.Reference()
            rx, ry = (pcbnew.ToMM(v) for v in (r.GetPosition().x, r.GetPosition().y))
            veld(r, ref, 0, 0)
            veld(fp.Value(), tekst, 0, 0)
            wr = pcbnew.ToMM(r.GetBoundingBox().GetWidth())
            wv = pcbnew.ToMM(fp.Value().GetBoundingBox().GetWidth())
            links = rx - (wr + 0.8 + wv) / 2
            veld(r, ref, links, ry, 0, pcbnew.GR_TEXT_H_ALIGN_LEFT)
            veld(fp.Value(), tekst, links + wr + 0.8, ry, 0, pcbnew.GR_TEXT_H_ALIGN_LEFT)
        elif ref == "U2":
            veld(fp.Value(), tekst, cx, cy, 90)
        else:
            raise SystemExit(f"{ref}: geen plek voor de waarde ({naam})")


def silk(bord, tekst, x, y, uitlijnen):
    t = pcbnew.PCB_TEXT(bord)
    t.SetText(tekst)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(TEKST), mm(TEKST)))
    t.SetTextThickness(mm(0.15))
    t.SetHorizJustify(uitlijnen)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    bord.Add(t)


def rand_van(fp):
    """Aan welke bordrand deze footprint staat: de dichtstbijzijnde."""
    cb = lichaam(fp)
    afstand = {"links": pcbnew.ToMM(cb.GetLeft()),
               "rechts": BORD_B - pcbnew.ToMM(cb.GetRight()),
               "boven": pcbnew.ToMM(cb.GetTop()),
               "onder": BORD_H - pcbnew.ToMM(cb.GetBottom())}
    return min(afstand, key=afstand.get)


def labels_bij(bord, fp):
    """Zeefdruk bij een randconnector, altijd aan de binnenkant van het bord.

    Naast de courtyard, niet op de pad: dan valt de tekst niet op het lichaam
    van de klem en niet over de bordrand.
    """
    ref = fp.GetReference()
    cb = lichaam(fp)
    L, R = pcbnew.ToMM(cb.GetLeft()), pcbnew.ToMM(cb.GetRight())
    T, O = pcbnew.ToMM(cb.GetTop()), pcbnew.ToMM(cb.GetBottom())
    kant = rand_van(fp)
    LI, RE, MI = (pcbnew.GR_TEXT_H_ALIGN_LEFT, pcbnew.GR_TEXT_H_ALIGN_RIGHT,
                  pcbnew.GR_TEXT_H_ALIGN_CENTER)

    if ref in PINLABELS:
        # Op de boven- of onderrand staan de pinlabels op de plek van de
        # referentie (J6 viel over KNOP); de labels zeggen genoeg.
        if kant in ("boven", "onder"):
            fp.Reference().SetVisible(False)
        for p in fp.Pads():
            tekst = PINLABELS[ref].get(p.GetNetname())
            if not tekst:
                raise SystemExit(f"{ref} pad {p.GetNumber()}: geen label voor "
                                 f"net {p.GetNetname()!r}")
            px, py = (pcbnew.ToMM(v) for v in (p.GetPosition().x, p.GetPosition().y))
            if kant == "links":
                silk(bord, tekst, R + MARGE, py, LI)
            elif kant == "rechts":
                silk(bord, tekst, L - MARGE, py, RE)
            elif kant == "boven":
                silk(bord, tekst, px, O + MARGE + TEKST / 2, MI)
            else:
                silk(bord, tekst, px, T - MARGE - TEKST / 2, MI)

    if ref in BLOKLABELS:
        # Het kanaalnummer vervangt de referentie op de zeefdruk: J11 en CT1
        # zouden anders op elkaar vallen, en bij het bedraden zoek je naar CT1.
        # In stuklijst en netlijst blijft J11 gewoon bestaan.
        fp.Reference().SetVisible(False)
        mx = (L + R) / 2
        onder = kant == "boven" or ref in LABEL_ONDER
        y = O + MARGE + TEKST / 2 if onder else T - MARGE - TEKST / 2
        silk(bord, BLOKLABELS[ref], mx, y, MI)

    if ref in TITELS:
        y = T - MARGE - TEKST / 2
        if kant == "rechts":
            silk(bord, TITELS[ref], R, y, RE)
        else:
            silk(bord, TITELS[ref], L, y, LI)


# --- netklassen: baanbreedtes voor de autorouter -----------------------------
# Veilig binnen de standaardregels van de gangbare fabrikanten (JLCPCB, PCBWay,
# Aisler): 0,25 mm afstand is ruim boven hun minimum van ~0,13-0,15 mm.
NETKLASSEN = {
    # naam: (baan, afstand, via-diameter, via-boor, netten)
    "Default": (0.30, 0.25, 0.8, 0.4, []),
    # 0,5 mm draagt ruim 1 A; de ESP32 trekt piekend ~0,5 A. Met 0,6 mm sloot
    # Freerouting pad 10 van de ESP (P1_RTS) in tussen de voedingsbanen.
    "Voeding": (0.50, 0.25, 0.8, 0.4, ["+5V_IN", "+5V", "+3V3", "GND"]),
    # VBIAS voedt alle 16 kanalen: een lage impedantie houdt de ruis laag.
    "Bias":    (0.50, 0.25, 0.8, 0.4, ["VBIAS"]),
}


def netklassen(bord):
    ns = bord.GetDesignSettings().m_NetSettings
    for naam, (baan, afstand, via, boor, netten) in NETKLASSEN.items():
        nc = ns.GetDefaultNetclass() if naam == "Default" else pcbnew.NETCLASS(naam)
        nc.SetTrackWidth(mm(baan))
        nc.SetClearance(mm(afstand))
        nc.SetViaDiameter(mm(via))
        nc.SetViaDrill(mm(boor))
        if naam != "Default":
            ns.SetNetclass(naam, nc)
            for net in netten:
                ns.SetNetclassPatternAssignment(net, naam)
    if hasattr(bord, "SynchronizeNetsAndNetClasses"):
        bord.SynchronizeNetsAndNetClasses(True)


def massavlak(bord, gnd):
    """GND-vlak over beide kanten.

    Afgeschermd tegen stoorvelden in de meterkast, en een lage-impedantie
    retour voor de kleine CT-signalen. Het antenneverbod van de ESP32 houdt
    het vlak vanzelf weg onder de antenne. Wordt pas gevuld na het routen.

    Op beide lagen, omdat Freerouting geen enkele GND-baan legt als er een
    vlak is: een GND-pad dat tussen signaalbanen op een eiland van het
    onderste vlak valt, hangt dan nog aan het bovenste.
    """
    for laag, naam in ((pcbnew.B_Cu, "GND onderkant"), (pcbnew.F_Cu, "GND bovenkant")):
        _vlak(bord, gnd, laag, naam)


def _vlak(bord, gnd, laag, naam):
    z = pcbnew.ZONE(bord)
    z.SetLayer(laag)
    z.SetNet(gnd)
    z.SetZoneName(naam)
    z.SetMinThickness(mm(0.25))
    z.SetLocalClearance(mm(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.5))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    o = z.Outline()
    o.NewOutline()
    r = 0.5                                   # binnen de bordrand blijven
    for x, y in ((r, r), (BORD_B - r, r), (BORD_B - r, BORD_H - r), (r, BORD_H - r)):
        o.Append(mm(x), mm(y))
    bord.Add(z)


def heeft_banen(pad):
    """Liggen er al banen of via's op dit bord?

    Via pcbnew en niet door in de tekst te zoeken: '(via' staat ook in de
    bordinstellingen ('(via_...'), en daar ging een eerdere versie op mis.
    """
    if not os.path.exists(pad):
        return False
    b = pcbnew.LoadBoard(pad)
    return b is not None and len(list(b.GetTracks())) > 0


def main():
    uit = os.path.join(UIT, PROJ + ".kicad_pcb")
    # Dit script bouwt het bord vanaf nul. Een gerout bord overschrijven gooit
    # al het handwerk weg, dus dat weigert het tenzij je het expliciet vraagt.
    # Wijzigingen in het schema gaan na het routen via KiCad zelf: PCB-editor,
    # Gereedschappen > PCB bijwerken vanuit schema (F8).
    if heeft_banen(uit) and os.environ.get("OPNIEUW_PLAATSEN") != "1":
        print(f"OVERGESLAGEN: {uit} is al gerout en wordt niet overschreven.\n"
              "  Wijzigingen in het schema: in KiCad met 'PCB bijwerken vanuit\n"
              "  schema' (F8). Echt opnieuw plaatsen en alle banen weggooien:\n"
              "  OPNIEUW_PLAATSEN=1")
        return
    onderdelen, netten = netlist.lees(NET)
    bord = pcbnew.CreateEmptyBoard()
    PLAATSING = plaatsing(BORD_B, BORD_H)

    hoeken = [(0, 0), (BORD_B, 0), (BORD_B, BORD_H), (0, BORD_H)]
    for a, b in zip(hoeken, hoeken[1:] + hoeken[:1]):
        lijn = pcbnew.PCB_SHAPE(bord)
        lijn.SetShape(pcbnew.SHAPE_T_SEGMENT)
        lijn.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        lijn.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        lijn.SetLayer(pcbnew.Edge_Cuts)
        lijn.SetWidth(mm(0.1))
        bord.Add(lijn)

    netobj = {}
    for naam in netten:
        ni = pcbnew.NETINFO_ITEM(bord, naam)
        bord.Add(ni)
        netobj[naam] = ni
    pad_net = {(ref, pad): naam for naam, knopen in netten.items()
               for ref, pad in knopen}
    netklassen(bord)
    # Een GND-pad waar maar een thermische spaak past (EN van de mux, tussen
    # banen in) is geen fout: het hangt ook via banen of het andere vlak aan GND.
    bord.GetDesignSettings().m_MinResolvedSpokes = 1

    geplaatst, vergeten, esp, fps = 0, [], None, {}
    for ref, info in sorted(onderdelen.items()):
        fpspec = info["footprint"]
        if ref.startswith("#") or not fpspec:
            continue
        if ref not in PLAATSING:
            vergeten.append(ref)
            continue
        fp = laad_footprint(fpspec)
        bord.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        zet_op(fp, *PLAATSING[ref])
        fps[ref] = fp
        for p in fp.Pads():
            naam = pad_net.get((ref, p.GetNumber()))
            if naam:
                p.SetNet(netobj[naam])
        if ref == "U1":
            esp = fp
            # "RST" valt gedraaid over het vakje ernaast, en ligt toch onder de
            # module. De USB-omtrek blijft op de zeefdruk als oriëntatiehint.
            for g in fp.GraphicalItems():
                if isinstance(g, pcbnew.PCB_TEXT) and g.GetText() == "RST":
                    g.SetLayer(pcbnew.F_Fab)
        if ref in PINLABELS or ref in BLOKLABELS or ref in TITELS:
            labels_bij(bord, fp)
        if ref in UITLEG:
            cb = lichaam(fp)
            silk(bord, UITLEG[ref], pcbnew.ToMM(cb.GetLeft()),
                 pcbnew.ToMM(cb.GetBottom()) + MARGE + TEKST,
                 pcbnew.GR_TEXT_H_ALIGN_LEFT)
        # De 16 burdenjumpers zijn identiek en staan direct achter hun CT-klem,
        # die al het kanaalnummer draagt. Hun referentie is alleen ruis op de
        # zeefdruk, en viel bij JP116 over een pad van R16.
        if re.fullmatch(r"JP1\d\d", ref):
            fp.Reference().SetVisible(False)
        geplaatst += 1

    if vergeten:
        raise SystemExit("geen plek opgegeven voor: " + ", ".join(sorted(vergeten)))
    overbodig = sorted(set(PLAATSING) - set(onderdelen))
    if overbodig:
        print("let op, plek opgegeven voor onderdelen die niet bestaan:",
              ", ".join(overbodig))
    waarden(fps)
    antenne_verbod(bord, esp)
    massavlak(bord, netobj["GND"])

    # Montagegaten staan niet in het schema: ze horen bij het bord, niet bij de
    # schakeling. Doorplaat-vrij, dus zonder net.
    for i, (x, y) in enumerate([(GAT, GAT), (BORD_B - GAT, GAT),
                                (GAT, BORD_H - GAT), (BORD_B - GAT, BORD_H - GAT)]):
        gat = laad_footprint(GAT_FP)
        bord.Add(gat)
        gat.SetReference(f"H{i + 1}")
        gat.SetValue("M3")
        gat.Reference().SetVisible(False)      # viel anders over de bordrand
        zet_op(gat, x, y, 0)

    # Afzender, voor en achter. Voor in het vrije vlak onder de
    # middenrail; achter groter tussen de twee pinrijen van de ESP32, waar aan
    # de onderkant geen pads zitten. Het midden daarvan is het midden tussen
    # pad 1 en pad 40.
    pads = {p.GetNumber(): p.GetPosition() for p in esp.Pads()}
    x_achter = pcbnew.ToMM(pads["1"].x + pads["40"].x) / 2
    y_achter = pcbnew.ToMM(pads["1"].y + pads["40"].y) / 2 - 1.5
    for laag, x, y0, groot, klein in ((pcbnew.F_SilkS, 30, 75, 2.0, 1.2),
                                      (pcbnew.B_SilkS, x_achter, y_achter, 3.0, 1.6)):
        for tekst, dy, maat in (("Aapje.Info", 0, groot),):
            t = pcbnew.PCB_TEXT(bord)
            t.SetText(tekst)
            t.SetLayer(laag)
            t.SetTextSize(pcbnew.VECTOR2I(mm(maat), mm(maat)))
            t.SetTextThickness(mm(maat * 0.15))
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
            t.SetMirrored(laag == pcbnew.B_SilkS)   # leesbaar van achteren
            t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y0 + dy)))
            bord.Add(t)

    uit = os.path.join(UIT, PROJ + ".kicad_pcb")
    bord.SetFileName(uit)
    pcbnew.SaveBoard(uit, bord)
    print(f"{geplaatst} onderdelen geplaatst op {BORD_B:.0f} x {BORD_H:.0f} mm")
    print(f"geschreven naar {uit}")


if __name__ == "__main__":
    main()
