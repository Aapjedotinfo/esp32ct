#!/usr/bin/env python3
"""
Controleert de gegenereerde netlist op de dingen die echt moeten kloppen.
Draait na sheets.py + kicad-cli; faalt hard als er iets niet klopt, zodat een
fout in de generator niet stilletjes in het schema blijft staan.
"""
import sys, os
import netlist

KANALEN = range(1, 17)

NET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "esp32ct-revc", "esp32ct-revc.net")

# Wat er per net op aangesloten hoort te zijn. U1=ESP32, U3=de multiplexer.
# U1-pinnummers zijn de ECHTE padnummers van de module, niet de GPIO-nummers:
# GPIO34=pad 11, GPIO13=18, GPIO4=32, GPIO14=13, GPIO27=24,
# GPIO18=8, GPIO23=12, GPIO32=28, GPIO33=9, GPIO25=26, GPIO26=6, GPIO17=29,
# GPIO16=31, 3V3=16, 5V=35, GND=1/22/33.
VERWACHT = {
    "SIG_MUX1": {"U1.11", "U3.17"},
    "MUX_S0":   {"U1.18", "U3.19"},
    # S1 zat op het oude bord op GPIO12 (pad 30), een strapping pin. Sinds rev B
    # GPIO4 (pad 32). De firmware moet mee: pin_s1 GPIO4.
    "MUX_S1":   {"U1.32", "U3.20"},
    "MUX_S2":   {"U1.13", "U3.21"},
    "MUX_S3":   {"U1.24", "U3.22"},
    "P1_RX":    {"U1.8", "Q1.1", "R4.2"},
    # P1_RTS zat op het oude bord op GPIO19 (pad 10). Sinds rev B GPIO23 (pad 12):
    # pad 10 zat ingeklemd tussen de P1-lijnen en Freerouting kreeg het er
    # niet schoon langs. De firmware moet mee: request_pin GPIO23.
    "P1_RTS":   {"U1.12", "J2.2"},
    # De externe 5 V gaat eerst door F1 (0 Ω of een zekering) en pas dan het
    # bord op. Hangt hier nog iets anders aan, dan zit het vóór de zekering.
    "+5V_IN":   {"J1.1", "F1.1"},
    # Pull-up R18 naar 3,3 V: de sensor is een 5V-NPN met open collector.
    "WATER_PULS": {"U1.28", "J3.2", "R18.2"},
    # De relais zitten op een los Arduino-relaisbordje; J4 (5V/GND) en J5
    # (BEL1/BEL2) zijn de klemmen erheen.
    "BEL_HUIS": {"U1.9", "J5.1"},
    "BEL_GARAGE": {"U1.26", "J5.2"},
    "BEL_IN":   {"U1.6", "J6.1"},
    # Nagebootste P1-uitgang naar de laadpaal (nog niet gebouwd).
    "P1OUT_TX":  {"U1.29", "R13.1"},
    "P1OUT_RTS": {"U1.31", "R16.2", "R17.1"},
}

# FYSIEKE PINBEZETTING
#
# Alles hierboven controleert of het schema intern klopt. Dat is niet genoeg:
# op 23-09-2026 bleek dat drie symbolen verzonnen pinnummers hadden (de mux,
# de LM358 en de BC547). Het schema was consistent, ERC en netlist waren
# schoon - en het bord zou nooit hebben gewerkt.
#
# Daarom hier de pinnen van de ECHTE onderdelen, uit een bron buiten dit
# project, en op welk net ze moeten zitten:
#   LM358  - KiCad's eigen symbool Amplifier_Operational:LM358
#   BC547  - KiCad's eigen symbool Transistor_BJT:BC547
#   HW-178 - SparkFun's BOB-09056-bordbestand, via footprint HW178_socket
FYSIEK = [
    ("U2.1",  "VBIAS", "LM358 pin 1 is uitgang A"),
    ("U2.2",  "VBIAS", "LM358 pin 2 is IN- A; bij een volger aan de uitgang"),
    ("U2.4",  "GND",   "LM358 pin 4 is V-"),
    ("U2.8",  "+3V3",  "LM358 pin 8 is V+"),
    ("Q1.1",  "P1_RX", "BC547 pin 1 is de collector"),
    ("Q1.3",  "GND",   "BC547 pin 3 is de emitter"),
    ("Q4.3",  "GND",   "BC547 pin 3 is de emitter"),
    ("U3.17", "SIG_MUX1", "HW-178: SIG"),
    ("U3.18", "GND",   "HW-178: EN is actief laag, dus aan massa = altijd aan"),
    ("U3.23", "+3V3",  "HW-178: VCC"),
    ("U3.24", "GND",   "HW-178: GND"),
    ("J4.1",  "+5V",   "relaisklem: 5 V naar VCC van het relaisbordje"),
    ("J4.2",  "GND",   "relaisklem: GND"),
    # De watermetersensor krijgt 5 V, maar zijn pull-up gaat naar 3,3 V: een
    # pull-up naar 5 V zou 5 V op GPIO32 zetten, en die kan dat niet hebben.
    ("J3.1",  "+5V",   "watermeter: voeding van de 5V-sensor"),
    ("F1.2",  "+5V",   "zekering F1: de uitgang is de 5V-rail van het bord"),
    ("F2.2",  "+5V",   "zekering F2 hangt aan de 5V-rail, vóór JP1"),
    ("R18.1", "+3V3",  "watermeter: pull-up naar 3,3 V, niet naar 5 V"),
]
# Pinnen die samen op een naamloos net horen te zitten.
SAMEN = [
    ({"U2.3", "R1.2", "R2.1"}, "LM358 pin 3 (IN+) hoort op het middelpunt van de deler"),
    ({"Q1.2", "R3.2"}, "BC547 pin 2 (basis) hoort aan de basisweerstand"),
    ({"Q4.2", "R13.2", "R15.1"}, "BC547 pin 2 (basis) hoort aan de basisweerstanden"),
    ({"Q4.1", "J8.5", "R14.2"}, "BC547 pin 1 (collector) hoort op de P1-datalijn"),
    # 5 V naar de laadpaal: +5V -> F2 -> JP1 -> RJ12-pin 1, in die volgorde.
    ({"F2.1", "JP1.2"}, "zekering F2 in serie met JP1"),
    ({"JP1.1", "J8.1"}, "JP1 schakelt de 5 V op pin 1 van de P1-uitgang"),
]

# Pinnamen van de echte onderdelen, per pinnummer. Het netlijstblok hierboven
# toetst de nummers; dit toetst of het getekende symbool dezelfde naam aan dat
# nummer geeft. Zonder deze toets draaide de build een middag lang op een
# verouderde versie van de symbolen: verbindingen goed, maar in het schema
# stond "C" waar de basis zat - en de automatische netnamen waren verwisseld.
PINNAMEN = {
    "LM358": {"1": "1OUT", "2": "1IN-", "3": "1IN+", "4": "V-",
              "5": "2IN+", "6": "2IN-", "7": "2OUT", "8": "V+"},
    "Q_NPN": {"1": "C", "2": "B", "3": "E"},
    "HW178": {**{str(i + 1): f"C{i}" for i in range(16)},
              "17": "SIG", "18": "~{EN}", "19": "S0", "20": "S1",
              "21": "S2", "22": "S3", "23": "VCC", "24": "GND"},
}

# Padnummers van de ESP32-module die we niet gebruiken.
# GPIO35 (pad 7) is vrijgekomen nu de tweede multiplexer vervalt, GPIO12
# (pad 30) doordat S1 naar GPIO4 ging.
ESP_ONGEBRUIKT = {2, 3, 4, 5, 7, 10, 14, 15, 17, 19, 20, 21, 23, 25, 27,
                  30, 34, 36, 37, 38, 39, 40}

# Strapping pins van de ESP32: hun niveau bij het opstarten bepaalt de
# opstartmodus en de flashspanning. Een hoge GPIO12 zet de flash op 1,8 V en
# dan start de module niet. Hier hoort niets aan te hangen, wat de lijst
# hierboven ook zegt; deze toets staat apart zodat hij niet stilletjes
# verdwijnt als iemand die lijst bijwerkt. Pad -> GPIO.
ESP_STRAPPING = {"34": "GPIO0", "36": "GPIO2", "14": "GPIO5",
                 "30": "GPIO12", "37": "GPIO15"}


def main():
    _, rauw = netlist.lees(NET)
    n = {naam: {f"{ref}.{pin}" for ref, pin in knopen}
         for naam, knopen in rauw.items()}
    fouten = []

    for naam, verwacht in VERWACHT.items():
        echt = n.get(naam)
        if echt is None:
            fouten.append(f"net {naam} bestaat niet")
        elif echt != verwacht:
            fouten.append(f"net {naam}: verwacht {sorted(verwacht)}, "
                          f"gevonden {sorted(echt)}")

    # Elk CT-kanaal: klemmenblok + burden + de bijbehorende mux-ingang.
    for i in KANALEN:
        naam = f"CT{i}"
        echt = n.get(naam, set())
        verwacht = {f"J{i + 10}.1", f"R{i + 100}.1", f"U3.{i}"}
        if echt != verwacht:
            fouten.append(f"{naam}: verwacht {sorted(verwacht)}, "
                          f"gevonden {sorted(echt)}")
        # De burden hangt NIET rechtstreeks aan VBIAS: de jumper zit ertussen.
        # Staat die per ongeluk parallel in plaats van in serie, dan valt dat
        # hier op doordat R.2 dan aan VBIAS hangt.
        keten = n.get(f"Net-(JP{i + 100}-Pad1)", n.get(f"Net-(R{i + 100}-Pad2)", set()))
        if keten != {f"R{i + 100}.2", f"JP{i + 100}.1"}:
            fouten.append(f"burdenketen {i}: verwacht R{i+100}.2 + JP{i+100}.1, "
                          f"gevonden {sorted(keten)}")

    # VBIAS hangt aan elke tweede klempool, aan de verre kant van elke jumper,
    # en aan de uitgang van de opamp.
    vb = n.get("VBIAS", set())
    ontbreekt = ({f"J{i + 10}.2" for i in KANALEN}
                 | {f"JP{i + 100}.2" for i in KANALEN} | {"U2.1"}) - vb
    if ontbreekt:
        fouten.append(f"VBIAS mist {sorted(ontbreekt)}")

    # Fysieke pinbezetting van de echte onderdelen.
    net_van = {pin: naam for naam, pinnen in n.items() for pin in pinnen}
    for pin, verwacht, waarom in FYSIEK:
        echt = net_van.get(pin)
        if echt != verwacht:
            fouten.append(f"pinbezetting {pin}: hoort op {verwacht}, zit op {echt} "
                          f"({waarom})")
    for groep, waarom in SAMEN:
        netten = {net_van.get(p) for p in groep}
        if len(netten) != 1 or None in netten:
            fouten.append(f"pinbezetting {sorted(groep)}: niet op een net ({waarom})")
    for pad, gpio in ESP_STRAPPING.items():
        net = net_van.get(f"U1.{pad}", "")
        if not net.startswith("unconnected-"):
            fouten.append(f"strapping pin {gpio} (U1.{pad}) zit op net {net}")
    if "U2.3" in vb:
        fouten.append("pinbezetting U2.3: IN+ zit op VBIAS - dan is de volger "
                      "meegekoppeld en loopt hij vast tegen een voedingsrail")

    # Pinnamen zoals het schema ze werkelijk tekent.
    getekend = netlist.pinnamen(NET)
    for symbool, verwacht in PINNAMEN.items():
        echt = getekend.get(symbool)
        if echt is None:
            fouten.append(f"pinnamen {symbool}: symbool niet in de netlijst")
            continue
        for nr, naam in verwacht.items():
            if echt.get(nr) != naam:
                fouten.append(f"pinnamen {symbool} pin {nr}: getekend als "
                              f"{echt.get(nr)!r}, hoort {naam!r} te zijn")

    # Precies deze pinnen horen los te hangen; al het andere is een fout.
    # Zonder deze lijst glipt een draad die net naast een pin landt ongemerkt
    # door - dat is hier al een keer gebeurd met de relaisspoel.
    mag_los = (
        {f"U1.{n}" for n in ESP_ONGEBRUIKT}           # vrije pinnen van de module
        | {"U2.5", "U2.6", "U2.7"}                    # tweede opamp ongebruikt

        | {"J2.1", "J2.4"}                            # P1-in: 5V en n.c.
        | {"J8.4"}                                    # P1-uit: n.c.
    )
    zwevend = {list(n[k])[0] for k in n if k.startswith("unconnected-")}
    onverwacht = zwevend - mag_los
    gemist = mag_los - zwevend
    if onverwacht:
        fouten.append(f"onverwacht losse pin(nen): {sorted(onverwacht)}")
    if gemist:
        fouten.append(f"verwacht los, maar wel verbonden: {sorted(gemist)}")

    los = [k for k in n if len(n[k]) == 1 and not k.startswith("unconnected-")]
    print(f"netten: {len(n)}   losse enkelpins-netten: {len(los)}   "
          f"bewust niet verbonden: {len(zwevend)}")
    if los:
        print("  eenzame netten:", ", ".join(sorted(los)))

    if fouten:
        print("\nFOUT:")
        for f in fouten:
            print("  -", f)
        return 1
    print("\nalle verwachte verbindingen kloppen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
