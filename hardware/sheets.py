#!/usr/bin/env python3
"""
Beschrijving van het esp32ct-bord rev C, uitgedrukt in de primitieven uit
gen_sch.py. Dit bestand is de bron van waarheid; het schema wordt eruit
gegenereerd en mag niet met de hand worden bijgewerkt.

Herkomst van de gegevens:
  - digitale pinbezetting  -> esp32ct.yaml (de draaiende firmware)
  - analoge voorzijde      -> opgave van de eigenaar, 22-09-2026
  - alles met (?)          -> NIET geverifieerd, staat in OPEN PUNTEN

Verschillen met het huidige bord staan in OPEN_PUNTEN.md.

Draaien:  python3 sheets.py
"""
import os, shutil
from gen_sch import (Sheet, SYMDEF, DEFAULT_FP, PROJ, uid, DATE, REV,
                     write_library, write_lib_table, write_fp_table)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, PROJ)

# ------------------------------------------------------------------ kanalen ---
# 16 identieke kanalen. Bewust GEEN groepsnamen in het schema: welke groep op
# welk kanaal zit is bedrading, geen eigenschap van het bord. Die toewijzing
# staat in ../kanalen.md en verandert zonder dat het bord verandert.
KANALEN = range(1, 17)

# Alles op het raster van 1,27 mm. sym() zet symbolen daar zelf op, dus
# draadpunten moeten dat ook doen - anders landt een draad net naast een pin
# en valt de verbinding stilletjes weg. g(n) rekent rastereenheden om naar mm.
def g(n):
    return round(n * 1.27, 2)


# YIXISI 2-polig, 5 mm steek (het gangbare KF301/blauwe type) - op voorraad,
# dus overal hetzelfde blokje. Let op: 5,00 mm, NIET 5,08.
# Eigen kopie met de courtyard op de body, zodat de CT-klemmen dicht naast
# elkaar mogen; zie lib/MX126_2P_5mm_krap.HERKOMST.txt.
FP_SCREW = "esp32ct:MX126_2P_5mm_krap"
FP_DIP24 = "Package_DIP:DIP-24_W7.62mm"
FP_R_STAAND = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical"
FP_DIP8 = "Package_DIP:DIP-8_W7.62mm"
FP_DIP4 = "Package_DIP:DIP-4_W7.62mm"

# Alles doorstekend (THT): met de hand te solderen, en de klemmen en de module
# zijn toch al THT. Een expliciete footprint bij sym() gaat hierboven.
DEFAULT_FP.update({
    "R":   "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "R_H": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "C":   "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "C_H": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "D":       "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "LED":     "LED_THT:LED_D5.0mm",
    # Brede variant: 2,54 mm steek in plaats van 1,27. Makkelijker met de hand
    # en er past een baan tussen. De smalle had maar 0,22 mm tussen de pads.
    "Q_NPN":   "Package_TO_SOT_THT:TO-92_Inline_Wide",
    "JUMPER":  "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "RJ12":    "Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal",
    "CONN_4":  "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "SCREW_2": FP_SCREW,
    "HW178":   "esp32ct:HW178_socket",
    "LM358": FP_DIP8,
    "PC817": FP_DIP4,
    "ESP32_MINIKIT": "esp32ct:ESP32_mini",
})


def ct_block(sh, x, y, nr):
    """Een CT-kanaal.

    De burden staat PARALLEL over de klem, met de jumper in SERIE erachter.
    Dicht = 33 ohm actief (kale ring). Open = burden eruit, voor een klem die
    er zelf al een heeft, zoals de SCT013. Een jumper OVER de weerstand zou de
    klem kortsluiten en het signaal juist wegnemen.
    """
    j = sh.sym("SCREW_2", f"J{nr + 10}", f"CT{nr}", x, y, FP_SCREW,
               "CT-klem of ringkern")
    p1, p2 = sh.at(j, "1"), sh.at(j, "2")
    # Staand: elektrisch gelijk, maar de CT-banden worden zo smaller en minder
    # diep, en het bord kleiner.
    r = sh.sym("R_H", f"R{nr + 100}", "33R", x + g(16), p1[1], FP_R_STAAND,
               descr="burden 33R -> 0,033 V/A theoretisch, 0,0307 V/A gefit")
    jp = sh.sym("JUMPER", f"JP{nr + 100}", "burden", x + g(28), p1[1] + g(1),
                descr="dicht: burden actief. open: klem heeft eigen burden")
    rl, rr = sh.at(r, "1"), sh.at(r, "2")
    jl, jr = sh.at(jp, "1"), sh.at(jp, "2")

    # Bovenste klempool is het meetpunt: naar de burden en naar de mux.
    knoop = (x + g(10), p1[1])
    sh.wire(p1, knoop)
    sh.wire(knoop, rl)
    sh.wire(knoop, (knoop[0], p1[1] - g(6)))
    sh.label(f"CT{nr}", (knoop[0], p1[1] - g(6)), 90)
    sh.junction(knoop)

    # Burden en jumper in serie, en dan onderlangs terug naar de andere pool.
    sh.wire(rr, jl)
    retour = (p2[0], p2[1] + g(5))
    sh.wire(jr, (jr[0] + g(3), jr[1]), (jr[0] + g(3), retour[1]), retour)
    sh.wire(retour, p2)
    sh.wire(retour, (retour[0] - g(10), retour[1]))
    sh.label("VBIAS", (retour[0] - g(10), retour[1]), 180)
    sh.junction(retour)


def build():
    root = Sheet("esp32ct-revc.kicad_sch", "Overzicht en ESP32", page="1")
    voed = Sheet("voeding.kicad_sch", "Voeding en VBIAS", page="2")
    mux = Sheet("mux.kicad_sch", "Multiplexer (HW-178)", page="3")
    ct1 = Sheet("ct_kanalen.kicad_sch", "CT-kanalen 1-16", page="4")
    p1s = Sheet("p1.kicad_sch", "P1 slimme meter", page="5")
    bel = Sheet("bel_water.kicad_sch", "Deurbel en watermeter", page="6")
    p1u = Sheet("p1_uit.kicad_sch", "P1-uitgang naar laadpaal", page="7")
    kids = [voed, mux, ct1, p1s, bel, p1u]
    for k in kids:
        k.path = root.path + "/" + k.sheet_uuid

    # ============================================================ root =========
    u1 = root.sym("ESP32_MINIKIT", "U1", "MH-ET Live D1 mini ESP32",
                  g(110), g(87), "esp32ct:ESP32_mini",
                  "ESP32-WROOM-32, 4 MB flash")
    # Padnummer -> net. Alles wat hier niet in staat blijft onaangesloten.
    NET_PER_PAD = {
        "35": "+5V", "16": "+3V3", "1": "GND", "22": "GND", "33": "GND",
        "11": "SIG_MUX1",
        # S1 zat op het oude bord op GPIO12 (pad 30), een strapping pin: hoog
        # bij het opstarten en de module start niet. Sinds rev B GPIO4 (pad 32),
        # de vrije buurpad; de firmware moet mee: pin_s1 GPIO4.
        "18": "MUX_S0", "32": "MUX_S1", "13": "MUX_S2", "24": "MUX_S3",
        "8": "P1_RX", "12": "P1_RTS", "28": "WATER_PULS",
        "9": "BEL_HUIS", "26": "BEL_GARAGE", "6": "BEL_IN",
        # NIEUW, nog niet gebouwd: de nagebootste P1-uitgang naar de laadpaal.
        # GPIO16/17 zijn UART2 en op dit bord nog vrij.
        "29": "P1OUT_TX", "31": "P1OUT_RTS",
    }
    esp = SYMDEF["ESP32_MINIKIT"]
    for pinnen, dx, rot in ((esp["l"], -g(8), 180), (esp["r"], g(8), 0)):
        for num, _, _ in pinnen:
            p = root.at(u1, num)
            net = NET_PER_PAD.get(num)
            if net is None:
                root.no_connect(p)
                continue
            root.wire(p, (p[0] + dx, p[1]))
            root.label(net, (p[0] + dx, p[1]), rot)

    root.note(
        "esp32ct rev C — 16 CT-kanalen, P1 in en uit, watermeter, deurbel\n\n"
        "ONTWERP. Basis is het huidige bord; de wijzigingen staan hieronder.\n\n"
        "De pinbezetting komt uit de draaiende firmware (esp32ct.yaml), met\n"
        "twee wijzigingen: P1_RTS van GPIO19 naar GPIO23, en mux S1 van\n"
        "GPIO12 naar GPIO4. Nieuw zijn GPIO16 en GPIO17 voor de P1-uitgang.\n\n"
        "Geen strapping pins: GPIO0, 2, 5, 12 en 15 hangen nergens aan.\n"
        "Een hoge GPIO12 bij het opstarten zet de flash op 1,8 V en dan\n"
        "start de module niet.", 20, 25, 1.4)

    root.note(
        "WIJZIGINGEN t.o.v. het huidige bord\n"
        "- 16 CT-kanalen in plaats van 22; de tweede multiplexer vervalt.\n"
        "  Die mat alleen de laadpaal en had een defecte VBIAS-rail.\n"
        "- de mux is een HW-178-breakout op twee female headers.\n"
        "- per kanaal een jumper IN SERIE met de burden, zodat een klem met\n"
        "  eigen burden kan zonder de weerstand weg te knippen.\n"
        "- alles op schroefklem behalve de twee RJ12's.\n"
        "- de relais zitten op een los Arduino-relaisbordje (J4/J5).\n"
        "  Die zijn actief-laag: de firmware heeft inverted: true nodig.\n"
        "- nieuw: P1-uitgang naar de laadpaal (blad 7).\n"
        "- P1_RTS op GPIO23 (was 19), mux S1 op GPIO4 (was 12).\n"
        "GPIO35 komt vrij.", 20, 195, 1.4)

    y = 60
    for k in kids:
        root.sheet_ref(k, 300, y)
        y += 25.4

    # ========================================================= voeding =========
    jp = voed.sym("SCREW_2", "J1", "+5V extern", 40, 60, FP_SCREW,
                  "externe 5 V voeding van het bord")
    a, b = voed.at(jp, "1"), voed.at(jp, "2")
    # F1: de zekering van het hele bord. Op de 5 V hangen de ESP32 (WiFi-
    # pieken tot ~0,5 A), het relaisbordje (~0,15 A met beide relais aan), de
    # watermeter en via F2 de laadpaal (tot 0,2 A): samen hooguit ~1 A.
    # Liggende weerstandsfootprint: past een axiale zekering, of een 0 Ω-brug.
    f1 = voed.sym("R_H", "F1", "1A", a[0] + 12.7 + 3.81, a[1],
                  descr="zekering 1 A traag, axiaal; of een 0 ohm-brug")
    k = (a[0] + 6.35, a[1])
    voed.wire(a, k)
    voed.wire(k, voed.at(f1, "1"))
    voed.label("+5V_IN", k)
    f2 = voed.at(f1, "2")
    voed.wire(f2, (f2[0] + 7.62, f2[1]))
    voed.label("+5V", (f2[0] + 7.62, f2[1]))
    voed.wire(b, (b[0] + 12.7, b[1]))
    voed.label("GND", (b[0] + 12.7, b[1]))

    # De 5 V komt van buiten het schema. Zonder deze vlaggen meldt de ERC
    # terecht dat niets die rail aandrijft.
    for i, (net, x) in enumerate((("+5V", 40), ("GND", 60))):
        fl = voed.sym("PWR_FLAG", f"#FLG{i + 1}", "PWR_FLAG", x, 90)
        p = voed.at(fl, "1")
        voed.wire(p, (p[0], p[1] + 6.35))
        voed.label(net, (p[0], p[1] + 6.35), 270)

    # buffervoorziening op de 5 V rail
    # C1 is een elco: pin 1 = plus, en dat is ook pad 1 (de vierkante) van de
    # CP_Radial-footprint. C2 is keramisch en ongepoold.
    for i, (ref, val, x, fp) in enumerate([
            ("C1", "100u (?)", 90, "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
            ("C2", "100n (?)", 105, "")]):
        c = voed.sym("C", ref, val, x, 70, fp)
        t, bt = voed.at(c, "1"), voed.at(c, "2")
        voed.wire(t, (t[0], t[1] - 5.08))
        voed.wire(bt, (bt[0], bt[1] + 5.08))
        voed.label("+5V", (t[0], t[1] - 5.08), 90)
        voed.label("GND", (bt[0], bt[1] + 5.08), 270)

    # 1,65 V middenrail: deler + volger
    r1 = voed.sym("R", "R1", "10k (?)", 60, 120, descr="bovenste helft van de 1,65 V deler")
    r2 = voed.sym("R", "R2", "10k (?)", 60, 140, descr="onderste helft van de 1,65 V deler")
    c3 = voed.sym("C", "C3", "10u (?)", 75, 140, "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", descr="dempt de middenrail")
    t1, b1 = voed.at(r1, "1"), voed.at(r1, "2")
    t2, b2 = voed.at(r2, "1"), voed.at(r2, "2")
    voed.wire(t1, (t1[0], t1[1] - 7.62))
    voed.label("+3V3", (t1[0], t1[1] - 7.62), 90)
    voed.wire(b1, t2)
    voed.wire(b2, (b2[0], b2[1] + 7.62))
    voed.label("GND", (b2[0], b2[1] + 7.62), 270)
    t3, b3 = voed.at(c3, "1"), voed.at(c3, "2")
    voed.wire((b1[0], b1[1]), (t3[0], b1[1]), t3)
    voed.wire(b3, (b3[0], b3[1] + 6.35))
    voed.label("GND", (b3[0], b3[1] + 6.35), 270)
    voed.junction((b1[0], b1[1]))

    u2 = voed.sym("LM358", "U2", "LM358", 140, 130, FP_DIP8,
                  "opamp als spanningsvolger op de 1,65 V middenrail")
    ip, im, out = voed.at(u2, "3"), voed.at(u2, "2"), voed.at(u2, "1")
    voed.wire((b1[0], b1[1]), (b1[0], ip[1]), ip)
    # terugkoppeling: uitgang terug naar de inverterende ingang
    voed.wire(out, (out[0] + 7.62, out[1]), (out[0] + 7.62, out[1] - 12.7),
              (im[0] - 7.62, out[1] - 12.7), (im[0] - 7.62, im[1]), im)
    voed.wire(out, (out[0] + 17.78, out[1]))
    voed.label("VBIAS", (out[0] + 17.78, out[1]))
    vp, vm = voed.at(u2, "8"), voed.at(u2, "4")
    voed.wire(vp, (vp[0] + 7.62, vp[1]))
    voed.label("+3V3", (vp[0] + 7.62, vp[1]))
    voed.note("voedingsspanning van de opamp\nniet nagekeken (?)",
              vp[0] + 7.62, vp[1] - 14.0, 1.0)
    voed.wire(vm, (vm[0] - 7.62, vm[1]))
    voed.label("GND", (vm[0] - 7.62, vm[1]), 180)
    for p in ("6", "5", "7"):
        voed.no_connect(voed.at(u2, p))

    voed.note(
        "VBIAS — de middenrail van 1,65 V\n\n"
        "De CT's leveren wisselstroom. De ADC van de ESP32 kan alleen 0-3,3 V\n"
        "meten, dus wordt het hele signaal opgetild naar het midden van dat\n"
        "bereik. Elke burden-weerstand hangt met één been aan deze rail.\n\n"
        "Dat maakt VBIAS ook meteen de verdachte in het mux2-probleem: als de\n"
        "rail de ingangen van mux2 niet bereikt, meet die mux niets zinnigs.\n"
        "De tweede opamp van de LM358 is ongebruikt.", 200, 40, 1.4)

    voed.note(
        "OPEN PUNTEN op dit blad\n"
        "- de deelweerstanden en condensatoren zijn NIET van het bord\n"
        "  afgelezen; 10k/10k geeft 1,65 V maar de echte waarden zijn onbekend\n"
        "- of de LM358 op 3,3 V of op 5 V staat is niet nagekeken\n"
        "- of de ongebruikte tweede opamp netjes is afgesloten is onbekend\n"
        "- de 5 V-buffercondensatoren zijn aangenomen, niet geteld", 200, 120, 1.4)

    # ============================================================= mux =========
    u3 = mux.sym("HW178", "U3", "HW-178 (CD74HC4067)", g(90), g(110),
                 descr="voetje voor het HW-178-breakout, plat op twee female headers")
    for i in range(16):
        p = mux.at(u3, str(i + 1))
        mux.wire(p, (p[0] - g(8), p[1]))
        mux.label(f"CT{i + 1}", (p[0] - g(8), p[1]), 180)
    ps = mux.at(u3, "17")
    mux.wire(ps, (ps[0] + g(10), ps[1]))
    mux.label("SIG_MUX1", (ps[0] + g(10), ps[1]))
    pe = mux.at(u3, "18")
    mux.wire(pe, (pe[0] + g(10), pe[1]))
    mux.label("GND", (pe[0] + g(10), pe[1]))
    for k, num in enumerate(("19", "20", "21", "22")):
        p = mux.at(u3, num)
        mux.wire(p, (p[0] + g(10), p[1]))
        mux.label(f"MUX_S{k}", (p[0] + g(10), p[1]))
    for num, net in (("23", "+3V3"), ("24", "GND")):
        p = mux.at(u3, num)
        mux.wire(p, (p[0] + g(10), p[1]))
        mux.label(net, (p[0] + g(10), p[1]))

    mux.note(
        "Een multiplexer, zestien kanalen - en dat is met opzet\n\n"
        "Het vorige bord had er twee, die samen de adreslijnen S0-S3 deelden.\n"
        "Dat werkte alleen met precies EEN cd74hc4067-hub in de firmware:\n"
        "bij twee hubs raakte de interne cache van elk van beide verouderd\n"
        "zodra de ander schakelde, en landden metingen op een verkeerd (vaak\n"
        "zwevend) kanaal. Dat gaf fantoomwaardes van meerdere kW.\n\n"
        "De tweede mux is hier vervallen. Hij mat alleen de laadpaal, en die\n"
        "wordt voortaan aangestuurd via de nagebootste P1-uitgang op blad 7.\n"
        "Daarmee verdwijnt ook het VBIAS-probleem dat mux2 onbruikbaar maakte.\n\n"
        "GPIO35 komt daarmee vrij.", 20, 25, 1.4)

    mux.note(
        "U3 is geen chip maar een VOETJE voor het HW-178-breakout\n\n"
        "Het breakout steekt plat met rechte pinnen in twee female strips:\n"
        "1x16 voor C0-C15 en 1x8 voor SIG..GND, op 15,24 mm hart-op-hart.\n"
        "Maten uit SparkFun's BOB-09056, waar het HW-178 een kloon van is.\n\n"
        "De pinnummers van U3 zijn die van het voetje (footprint\n"
        "HW178_socket), NIET die van de CD74HC4067-chip. Zet hier nooit een\n"
        "DIP- of SOIC-footprint onder: dan klopt geen pin en hangt VCC aan GND.\n\n"
        "EN ligt vast aan massa: de mux staat permanent aan.", 20, 205, 1.4)

    # ======================================================= CT-kanalen =========
    kolommen = (g(24), g(122), g(220))
    for i, nr in enumerate(KANALEN):
        ct_block(ct1, kolommen[i // 6], g(40) + g(19) * (i % 6), nr)

    ct1.note(
        "Zestien identieke kanalen\n\n"
        "Per kanaal: de CT op een schroefklem, met de burden-weerstand\n"
        "parallel over die klem. De jumper staat in SERIE met de burden:\n\n"
        "  dicht  -> 33 ohm actief, voor een kale ringkern\n"
        "  open   -> burden eruit, voor een klem met ingebouwde burden\n"
        "            zoals de SCT013, die zelf al een spanning afgeeft\n\n"
        "Een jumper OVER de weerstand zou de klem kortsluiten en het\n"
        "signaal juist wegnemen; daarom staat hij erachter.\n\n"
        "Welke groep op welk kanaal zit staat bewust NIET op het bord.\n"
        "Dat is bedrading, geen eigenschap van de print - zie kanalen.md.",
        g(24), g(147), 1.4)

    # ============================================================== P1 =========
    jr = p1s.sym("RJ12", "J2", "RJ12 naar slimme meter", 50, 90,
                 descr="P1-poort, DSMR 5")
    p1_names = [("1", "+5V (meter, ongebruikt)"), ("2", "P1_RTS"),
                ("3", "GND"), ("4", "n.c."), ("5", "P1_DATA"), ("6", "GND")]
    for num, net in p1_names:
        p = p1s.at(jr, num)
        # Pin 1 (5 V uit de meter) en pin 4 gebruiken we niet: geen draad,
        # alleen een expliciete "niet verbonden"-markering.
        if net == "n.c." or net.startswith("+5V"):
            p1s.no_connect(p)
            continue
        p1s.wire(p, (p[0] + 15.24, p[1]))
        p1s.label(net, (p[0] + 15.24, p[1]))

    q1 = p1s.sym("Q_NPN", "Q1", "BC547 (?)", 150, 120,
                 descr="inverteert het open-collector datasignaal van de meter")
    rb = p1s.sym("R_H", "R3", "10k (?)", 125, 120)
    rp = p1s.sym("R", "R4", "10k (?)", 175, 100)
    bb = p1s.at(q1, "2")
    p1s.wire(p1s.at(rb, "2"), bb)
    p1s.wire(p1s.at(rb, "1"), (p1s.at(rb, "1")[0] - 10.16, bb[1]))
    p1s.label("P1_DATA", (p1s.at(rb, "1")[0] - 10.16, bb[1]), 180)
    cc, ee = p1s.at(q1, "1"), p1s.at(q1, "3")
    p1s.wire(ee, (ee[0] + 7.62, ee[1]), (ee[0] + 7.62, ee[1] + 7.62))
    p1s.label("GND", (ee[0] + 7.62, ee[1] + 7.62), 270)
    rpb, rpt = p1s.at(rp, "2"), p1s.at(rp, "1")
    p1s.wire(cc, (rpb[0], cc[1]), rpb)
    p1s.wire(rpt, (rpt[0], rpt[1] - 7.62))
    p1s.label("+3V3", (rpt[0], rpt[1] - 7.62), 90)
    p1s.wire((rpb[0], cc[1]), (rpb[0] + 15.24, cc[1]))
    p1s.label("P1_RX", (rpb[0] + 15.24, cc[1]))
    p1s.junction((rpb[0], cc[1]))

    p1s.note(
        "P1-poort van de slimme meter\n\n"
        "De meter zendt inverted TTL op een open-collector uitgang. Een NPN\n"
        "draait het signaal om en tilt het naar 3,3 V, zodat de UART van de\n"
        "ESP32 het kan lezen (GPIO18).\n\n"
        "P1_RTS (GPIO23) vraagt de meter om te zenden: hoog is elke seconde\n"
        "een telegram. De firmware heeft dit als request_pin.", 240, 40, 1.4)

    p1s.note(
        "OPEN PUNTEN op dit blad\n"
        "- de inverter is de gangbare schakeling, maar het type transistor\n"
        "  en de weerstandswaarden zijn NIET van het bord afgelezen\n"
        "- of P1_RTS rechtstreeks aan GPIO23 mag of via een\n"
        "  niveauomzetter naar 5 V, is niet nagekeken\n"
        "- of de meter het bord voedt via RJ12 pin 1 is niet nagekeken;\n"
        "  hier is uitgegaan van de externe 5 V op J1", 240, 120, 1.4)

    # ================================================ deurbel en watermeter ====
    # Twee 2-polige blokjes: een 3-aderige sensor gebruikt er drie polen van,
    # de vierde blijft over als extra massa (handig voor een afscherming).
    # De sensor krijgt 5 V: het is een 5V-type (zie de notitie).
    for ref, y, netten in (("J3", g(196), ("+5V", "WATER_PULS")),
                           ("J9", g(212), ("GND", "GND"))):
        jw = bel.sym("SCREW_2", ref, "watermeter-sensor", g(31), y, FP_SCREW,
                     "pulssensor op de watermeter")
        for num, net in zip(("1", "2"), netten):
            p = bel.at(jw, num)
            bel.wire(p, (p[0] + g(12), p[1]))
            bel.label(net, (p[0] + g(12), p[1]))

    # Pull-up van de open collector naar 3,3 V - NIET naar 5 V, anders krijgt
    # GPIO32 5 V op een pin die dat niet verdraagt.
    rw = bel.sym("R", "R18", "10k", g(60), g(186),
                 descr="pull-up watermeterpuls naar 3,3 V")
    for num, net, dy in (("1", "+3V3", -g(4)), ("2", "WATER_PULS", g(4))):
        p = bel.at(rw, num)
        bel.wire(p, (p[0], p[1] + dy))
        bel.label(net, (p[0], p[1] + dy), 90 if dy < 0 else 270)

    bel.note(
        "Watermeter: inductieve naderingsschakelaar, 5 Vdc NPN, normally\n"
        "open, 4 mm schakelafstand. Bruin = +5 V, blauw = GND, zwart = de\n"
        "open-collector uitgang (op J3 pin 2).\n\n"
        "R18 trekt de uitgang op naar 3,3 V. Omdat de sensor alleen naar\n"
        "massa schakelt, komt er nooit 5 V op GPIO32 - een deler is dus niet\n"
        "nodig. De sensor zelf draait wel op 5 V.\n\n"
        "De firmware gooit sinds 14-09-2026 alles boven 30 L/min weg;\n"
        "dat ving een klapperende sensor af, geen hardwarewijziging.",
        95, 246, 1.4)

    # ------------------------------------- deurbel: twee klemmen naar de relais ---
    # De relais zitten sinds 23-09-2026 niet meer op dit bord. Een kant-en-klaar
    # Arduino-relaisbordje hangt met vier draden aan twee 2-polige klemmen
    # (25-09-2026: klemmen in plaats van een pinheader, net als de rest);
    # beltrafo, Bel 1 en Bel 2 gaan rechtstreeks naar de schroefklemmen van
    # dat relaisbordje.
    for ref, y, netten, wat in (
            ("J4", g(60), ("+5V", "GND"), "voeding van het relaisbordje (VCC/GND)"),
            ("J5", g(70), ("BEL_HUIS", "BEL_GARAGE"), "stuurlijnen naar IN1/IN2")):
        jr = bel.sym("SCREW_2", ref, "naar relaisbordje", g(200), y, FP_SCREW, wat)
        for num, net in zip(("1", "2"), netten):
            p = bel.at(jr, num)
            bel.wire(p, (p[0] + g(10), p[1]))
            bel.label(net, (p[0] + g(10), p[1]))

    # De deurbelknop blijft wel op dit bord: dat is een ingang, geen relais.
    jk = bel.sym("SCREW_2", "J6", "deurbelknop", g(200), g(90), FP_SCREW,
                 "maakcontact in de deur, potentiaalvrij")
    for num, net in (("1", "BEL_IN"), ("2", "GND")):
        p = bel.at(jk, num)
        bel.wire(p, (p[0] + g(10), p[1]))
        bel.label(net, (p[0] + g(10), p[1]))

    bel.note(
        "Deurbel\n\n"
        "De relais zitten niet meer op dit bord. J4 en J5 gaan met vier draden\n"
        "naar een standaard Arduino-relaisbordje met twee kanalen:\n\n"
        "  J4-1  +5V            -> VCC van het relaisbordje\n"
        "  J4-2  GND            -> GND\n"
        "  J5-1  BEL1 (huis)    GPIO33 -> IN1\n"
        "  J5-2  BEL2 (garage)  GPIO25 -> IN2\n\n"
        "De beltrafo (6 V AC) en de twee bellen komen op de schroefklemmen van\n"
        "dat relaisbordje: trafo naar COM van beide relais, NO naar de bel, en\n"
        "de retour van beide bellen rechtstreeks terug naar de trafo.\n\n"
        "De deurbelknop (J6) blijft hier: een gewoon maakcontact in de deur, dat\n"
        "rechtstreeks aan GPIO26 hangt met de interne pull-up.", g(24), g(40), 1.4)

    bel.note(
        "LET OP - de firmware moet mee veranderen\n\n"
        "De gangbare relaisbordjes zijn ACTIEF-LAAG: het relais komt op als IN\n"
        "naar massa gaat. In esp32ct.yaml staan de switches op GPIO33 en GPIO25\n"
        "nu zonder inverted, en een ESP32-pin is laag tijdens het opstarten.\n"
        "Zonder inverted: true gaat de bel dus bij elke reboot.\n\n"
        "En: de logicakant van zo'n bordje hangt aan 5 V, de ESP32 stuurt maar\n"
        "3,3 V. Test of het relais netjes afvalt als IN op 3,3 V staat. Blijft\n"
        "het hangen of klappert het, voed dan VCC van het relaisbordje uit\n"
        "3,3 V en de spoelen (JD-VCC) uit 5 V.", g(24), g(130), 1.4)


    # ============================== P1-uitgang naar de laadpaal (NIEUW) =========
    # Precies het spiegelbeeld van blad 6: daar draait een NPN het signaal VAN
    # de meter om, hier maakt een NPN het signaal dat een meter zou geven.
    j8 = p1u.sym("RJ12", "J8", "RJ12 naar laadpaal", g(55), g(87),
                 descr="NIEUW - nagebootste P1-poort, nog niet gebouwd")
    pin = {n: p1u.at(j8, n) for n in "123456"}

    # pin 1: 5 V naar de laadpaal, afschakelbaar met een jumper
    jp = p1u.sym("JUMPER", "JP1", "5V-doorvoer", g(87), g(76),
                 descr="open laten als de laadpaal zichzelf voedt")
    jp1, jp2 = p1u.at(jp, "1"), p1u.at(jp, "2")
    p1u.wire(pin["1"], (g(70), pin["1"][1]), (g(70), jp1[1]), jp1)
    # F2: eigen zekering op deze 5 V. Kortsluiting in de laadpaalkabel legt dan
    # niet de hele 5V-rail van het bord plat (en blaast F1 niet op). DSMR staat
    # max 250 mA op pin 1 toe, dus 200 mA. Liggend, net als F1 (rev C; was
    # staand): een axiale zekering of een 0 Ω-brug.
    f2 = p1u.sym("R_H", "F2", "200mA", g(101), jp2[1],
                 descr="zekering 200 mA naar de laadpaal, axiaal; of een 0 ohm-brug")
    p1u.wire(jp2, p1u.at(f2, "1"))
    f2b = p1u.at(f2, "2")
    p1u.wire(f2b, (g(110), f2b[1]))
    p1u.label("+5V", (g(110), f2b[1]))

    # pin 2: de laadpaal vraagt om data (5 V) -> deler naar 3,3 V
    r16 = p1u.sym("R_H", "R16", "10k", g(87), pin["2"][1])
    p1u.wire(pin["2"], p1u.at(r16, "1"))
    knoop = (g(98), pin["2"][1])
    p1u.wire(p1u.at(r16, "2"), knoop)
    r17 = p1u.sym("R", "R17", "15k", knoop[0], g(92),
                  descr="onderste helft van de 5V->3V3 deler")
    p1u.wire(knoop, p1u.at(r17, "1"))
    p1u.junction(knoop)
    p1u.wire(p1u.at(r17, "2"), (knoop[0], g(100)))
    p1u.label("GND", (knoop[0], g(100)), 270)
    p1u.wire(knoop, (g(122), knoop[1]))
    p1u.label("P1OUT_RTS", (g(122), knoop[1]))

    # pin 3 en 6: massa. pin 4 is ongebruikt.
    for num in ("3", "6"):
        p1u.wire(pin[num], (pin[num][0] + g(12), pin[num][1]))
        p1u.label("GND", (pin[num][0] + g(12), pin[num][1]))
    p1u.no_connect(pin["4"])

    # pin 5: de datalijn, open collector met pull-up
    q4 = p1u.sym("Q_NPN", "Q4", "BC547", g(75), g(110),
                 descr="maakt het geinverteerde open-collector signaal")
    qb, qc, qe = (p1u.at(q4, n) for n in ("2", "1", "3"))
    # Opgeknipt op g(105): daar takt de pull-up aan, en alleen gedeelde
    # eindpunten verbinden in KiCad.
    col = g(87)
    p1u.wire(qc, (col, qc[1]), (col, g(105)), (col, pin["5"][1]), pin["5"])

    r14 = p1u.sym("R", "R14", "4k7", g(108), g(99),
                  descr="pull-up; bij 115200 baud niet hoger kiezen")
    p1u.wire(p1u.at(r14, "1"), (g(108), g(88)))
    p1u.label("+5V", (g(108), g(88)), 90)
    p1u.wire(p1u.at(r14, "2"), (g(108), g(105)), (col, g(105)))
    p1u.junction((col, g(105)))

    r13 = p1u.sym("R_H", "R13", "1k", g(55), qb[1])
    p1u.wire(p1u.at(r13, "1"), (g(39), qb[1]))
    p1u.label("P1OUT_TX", (g(39), qb[1]), 180)
    basis = (g(63), qb[1])
    p1u.wire(p1u.at(r13, "2"), basis)
    p1u.wire(basis, qb)
    r15 = p1u.sym("R", "R15", "10k", basis[0], g(117),
                  descr="houdt de basis laag als de ESP32 nog niet zendt")
    p1u.wire(basis, p1u.at(r15, "1"))
    p1u.junction(basis)
    p1u.wire(p1u.at(r15, "2"), (basis[0], g(125)))
    p1u.label("GND", (basis[0], g(125)), 270)
    p1u.wire(qe, (g(89), qe[1]), (g(89), g(125)))
    p1u.label("GND", (g(89), g(125)), 270)

    p1u.note(
        "NIEUW - nog niet gebouwd\n\n"
        "Een tweede P1-poort, maar dan andersom: dit bord speelt hier zelf\n"
        "voor slimme meter, zodat de laadpaal op een zelfbedacht vermogen\n"
        "kan loadbalancen. Handig om hem te laten denken dat er 35 kW door\n"
        "de aansluiting gaat en hij dus moet terugregelen.\n\n"
        "Blad 6 is de ingang vanaf de echte meter; dit blad is de uitgang.", 200, 30, 1.4)

    p1u.note(
        "Waarom een transistor en geen rechtstreekse pin\n\n"
        "De P1-datalijn is geinverteerd en werkt op 5 V met een open\n"
        "collector: in rust ligt de lijn LAAG en de pull-up trekt hem hoog\n"
        "voor elke bit. Een ESP32-pin kan dat niet: 3,3 V is te laag en de\n"
        "polariteit klopt niet.\n\n"
        "Q4 lost beide op. De UART van de ESP32 zendt gewoon normaal - rust\n"
        "is hoog - en de transistor draait dat om terwijl R14 de lijn naar\n"
        "5 V tilt. Dezelfde truc als op blad 6, alleen de andere kant op.\n\n"
        "R15 houdt de basis laag zolang de UART nog niet is opgestart, zodat\n"
        "de lijn niet willekeurig gaat zwaaien tijdens het booten.", 200, 70, 1.4)

    p1u.note(
        "Wat de firmware nog moet doen\n\n"
        "- UART2 op GPIO17 (TX), 115200 8N1 voor DSMR 5. Niet inverted in de\n"
        "  software: Q4 doet de inversie al in hardware.\n"
        "- zelf een telegram opbouwen en afsluiten met CRC16 over alles vanaf\n"
        "  de / tot en met de !, anders verwerpt de laadpaal het.\n"
        "- GPIO16 leest of de laadpaal om data vraagt. Mag je negeren en\n"
        "  gewoon elke seconde zenden; dan is R16/R17 optioneel.\n\n"
        "Controleer voor je gaat solderen of de laadpaal DSMR 5 (115200 8N1)\n"
        "verwacht of het oudere DSMR 2/3 (9600 7E1) - dat scheelt alleen\n"
        "firmware, de schakeling blijft hetzelfde.", 200, 140, 1.4)

    p1u.note(
        "OPEN PUNTEN\n"
        "- GPIO16/17 zijn gekozen omdat ze vrij zijn en UART2 vormen. Controleer\n"
        "  of ze op jouw MiniKit ook echt naar buiten zijn gebracht.\n"
        "- of de laadpaal de 5 V van pin 1 nodig heeft is niet nagegaan; JP1\n"
        "  laat je die keuze open.\n"
        "- alle weerstandswaarden zijn ontwerpkeuzes, geen meting.", 200, 210, 1.4)

    # =============================================================== wegschrijven
    os.makedirs(OUT, exist_ok=True)
    pages = [("/", "1")] + [("/" + k.sheet_uuid, k.page) for k in kids]
    for sh, is_root in [(root, True)] + [(k, False) for k in kids]:
        with open(os.path.join(OUT, sh.fname), "w", encoding="utf-8") as f:
            f.write(sh.render(root=is_root, pages=pages))
    with open(os.path.join(OUT, PROJ + ".kicad_pro"), "w", encoding="utf-8") as f:
        f.write(KICAD_PRO)
    alle = set().union(*(sh.used for sh in [root] + kids))
    write_library(os.path.join(OUT, "esp32ct.kicad_sym"), alle)
    write_lib_table(os.path.join(OUT, "sym-lib-table"))
    write_fp_table(os.path.join(OUT, "fp-lib-table"))
    # De ESP32-footprint komt van r0oland/ESP32_mini_KiCad_Library (Apache 2.0)
    # en staat als bron in lib/; hier wordt hij in de projectbibliotheek gezet.
    # Ook het HW-178-voetje uit lib/ (door hw178.py gegenereerd). Altijd
    # opnieuw kopieren: een verouderde footprint in het project zou anders
    # stilletjes blijven staan als lib/ wordt bijgewerkt.
    pretty = os.path.join(OUT, "esp32ct.pretty")
    os.makedirs(pretty, exist_ok=True)
    for naam in sorted(os.listdir(os.path.join(HERE, "lib"))):
        if naam.endswith(".kicad_mod"):
            shutil.copyfile(os.path.join(HERE, "lib", naam),
                            os.path.join(pretty, naam))
    print(f"geschreven naar {OUT}")
    for sh, _ in [(root, True)] + [(k, False) for k in kids]:
        print(f"  {sh.page}  {sh.fname:32s} {sh.title}")


KICAD_PRO = """{
  "board": {"design_settings": {}},
  "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
  "meta": {"filename": "%s.kicad_pro", "version": 1},
  "net_settings": {
    "classes": [
      {"bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25,
       "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3,
       "microvia_drill": 0.1, "name": "Default", "pcb_color": "rgba(0, 0, 0, 0.000)",
       "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.25,
       "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6}
    ],
    "meta": {"version": 3}
  },
  "schematic": {
    "annotate_start_num": 0,
    "legacy_lib_dir": "",
    "legacy_lib_list": [],
    "meta": {"version": 1},
    "page_layout_descr_file": "",
    "plot_directory": "",
    "spice_current_sheet_as_root": false,
    "spice_external_command": "spice \\"%%I\\"",
    "spice_model_current_sheet_as_root": true,
    "spice_save_all_currents": false,
    "spice_save_all_dissipations": false,
    "spice_save_all_voltages": false,
    "subpart_first_id": 65,
    "subpart_id_separator": 0
  },
  "sheets": [],
  "text_variables": {}
}
""" % PROJ

if __name__ == "__main__":
    build()
