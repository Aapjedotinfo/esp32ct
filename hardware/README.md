# esp32ct — hardware

KiCad-project voor **rev C** van het CT-bord: schema, netlist en een volledig
gerout bord, tot en met de Gerbers voor de printfabriek. Rev C is rev B met de
waarden van alle onderdelen op de zeefdruk en een liggende F2; elektrisch en
qua pinbezetting zijn ze gelijk. Basis is het huidige
bord, gereconstrueerd uit de draaiende firmware en uit opgave van de eigenaar;
er lag geen eerder ontwerp.

Gebouwd en gecontroleerd met **KiCad 10.0.6**. `build.sh` pakt zelf de nieuwste
installatie die het vindt; zet `KICAD_DIR` als je een andere wilt afdwingen.
Let op: het bord wordt door pcbnew 10 weggeschreven in het 10-formaat en is
daarmee niet meer met KiCad 9 te openen. Het schema schrijft de generator zelf,
nog in het 9-formaat, en dat leest 10 probleemloos.

Lees `OPEN_PUNTEN.md` voordat je hier iets uit overneemt. Daarin staat wat
vaststaat, wat aangenomen is, en wat er verandert ten opzichte van het bord dat
er nu hangt.

Wat je niet over het hoofd moet zien:

- **Bestelklaar:** `esp32ct-revc/esp32ct-revc-gerbers.zip`. 115 × 103 mm,
  2 lagen, FR4 1,6 mm, HASL (loodvrij mag).
- **Meet eerst je HW-178 en een schroefklem na** — zie `OPEN_PUNTEN.md` voor
  wat je vóór het bestellen controleert. De klemmen staan vrijwel tegen elkaar.
- **De relais zitten op een los Arduino-relaisbordje.** Die zijn actief-laag;
  de firmware heeft dan `inverted: true` nodig, anders rinkelt de bel bij elke
  reboot.
- **16 kanalen, één multiplexer.** De laadpaal wordt voortaan via de
  nagebootste P1-uitgang gestuurd in plaats van met CT's gemeten.
- **Firmware voor rev C:** `PINMAPPING.md` heeft de pinbezetting per GPIO en
  per connector, en wat er in `firmware/esp32ct-revc.yaml` moet veranderen.

## Openen

```bash
"/c/Program Files/KiCad/10.0/bin/kicad.exe" esp32ct-revc/esp32ct-revc.kicad_pro
```

Of blader door `esp32ct-revc/esp32ct-revc.pdf` (schema) en `plaatsing.pdf`
(bord) als je alleen wilt kijken.

## Bladindeling

| Blad | Inhoud |
|---|---|
| 1 | Overzicht en ESP32 — de complete pinbezetting |
| 2 | Voeding en VBIAS — 5 V in, de 1,65 V middenrail |
| 3 | Multiplexer — voetje voor het HW-178-breakout (CD74HC4067) |
| 4 | CT-kanalen 1-16, elk met burden en jumper |
| 5 | P1 slimme meter — ingang vanaf de echte meter |
| 6 | Deurbel en watermeter |
| 7 | P1-uitgang naar de laadpaal |

Alle bladen zijn onderling verbonden met globale labels; er zijn geen
hiërarchische pinnen. Een net met dezelfde naam is overal hetzelfde net.

## Schema én PCB zijn gegenereerd, niet getekend

`gen_sch.py` bevat de symbolen en de KiCad-primitieven, `sheets.py` beschrijft
het schema, `pcb.py` de plaatsing. **Pas de KiCad-bestanden niet met de hand
aan** — wijzig het script en bouw opnieuw, anders is je wijziging bij de
volgende run weg.

Dat is bewust: zestien identieke kanalen met de hand tekenen én plaatsen is
foutgevoelig, en het ontwerp verandert nog. Nu is de bron van waarheid een
leesbare lijst.

```bash
python3 sheets.py && python3 check_net.py
```

`check_net.py` controleert de geëxporteerde netlist op de verbindingen die echt
moeten kloppen: de ADC-pin, de adresbus, alle zestien CT-ketens, de VBIAS-rail,
en of de burden-jumper wel in serie staat en niet parallel. Het faalt hard als
er iets niet klopt, zodat een fout in de generator niet stilletjes in het
ontwerp blijft staan.

Daarnaast staat er een lijst van pinnen die los **mogen** hangen. Alles wat
daarbuiten valt is een fout. Die controle is er niet voor niets: tijdens het
bouwen verbraken drie verbindingen stilletjes doordat een draad midden op een
andere draad eindigde. In KiCad verbindt dat niet — ook niet met een junction
erbij — en het schema zag er gewoon goed uit.

En er is een blok **fysieke pinbezetting**: welke pin van het échte onderdeel
op welk net hoort, met de bron erbij (KiCad's eigen symbolen voor de LM358 en
BC547, SparkFun's bordbestand voor het HW-178). Alle andere controles kijken
of het schema met zichzelf klopt; deze kijkt of het klopt met de onderdelen die
je erop soldeert. Hij bestaat omdat drie symbolen verzonnen pinnummers bleken
te hebben — zie `OPEN_PUNTEN.md`. Nagegaan door de oude fouten tijdelijk terug
te zetten: hij vangt ze alle drie.

## De PCB

`pcb.py` bouwt `esp32ct-revc.kicad_pcb` uit de netlist: bordomtrek, alle
footprints op hun plek, elk pad op het juiste net, netklassen, de
massavlakken, het antenneverbod, montagegaten en de zeefdruk. Daarna legt
`freeroute.py` de banen met Freerouting. Het bord wordt bij elke build vanaf
nul geplaatst en gerout; er zit geen handwerk in.

Beide scripts draaien op de Python van KiCad, niet die van het systeem, want
alleen die heeft `pcbnew`. `build.sh` regelt dat zelf.

Bord: **115 × 103 mm**, dubbelzijdig, alles doorstekend, 77 onderdelen plus
4 montagegaten (M3). De indeling:

| Waar | Wat |
|---|---|
| boven- en onderrand | 16 CT-klemmen, acht per zijde, met staande burden en jumper er direct achter; de belknop J6 als negende klem onderaan |
| linkerrand | POWER IN (J1, met zekering F1 erachter), WATER (J3/J9), RELAIS (J4/J5); de 1,65 V-middenrail erachter |
| midden | het HW-178-voetje, precies tussen de twee CT-rijen |
| rechterrand | de twee RJ12's onder elkaar (P1 INPUT boven, P1 OUTPUT onder), met hun P1-onderdelen ernaast (ook F2/JP1: 5 V naar P1 OUT); daaronder de ESP32 met de antenne naar buiten |

De CT-klemmen staan met opzet tegenover elkaar langs de lange zijden, met hun
burden en jumper er meteen achter. Zo blijft de lus van klem naar burden kort;
dat is de gevoelige plek in deze meting. De klemmen staan op 10,795 mm steek,
~0,3 mm tussen de bodies; daarvoor is er een eigen footprint met de courtyard
op de body (`lib/MX126_2P_5mm_krap`).

Onder de antenne van de ESP32 ligt een **verbodsgebied voor koper**, zodat de
massavlakken de WiFi niet verstikken.

### Banen en massa

Freerouting legt alle verbindingen, **ook GND als gewone banen**. Daarbovenop
ligt op beide lagen een GND-vlak. Freerouting krijgt die vlakken bewust niet
te zien: met een vlak erbij legt hij geen enkele GND-baan, en vielen er steeds
GND-pads op een eilandje tussen de signaalbanen. Blijft er toch een
GND-verbinding open, dan beslist de DRC na het gieten van de vlakken of die via
het vlak dicht is. Een open verbinding op elk ander net stopt de build.

Freerouting geeft niet elke run hetzelfde resultaat. Daarom draaien de DRC en
de controles bij elke build opnieuw, en telt een eerdere geslaagde run niet.

### Aannames over de randconnectoren

**Schroefklemmen:** de draadinvoer staat naar buiten, op de aanname dat die aan
de **+Y-kant** van de footprint zit. Dat volgt uit de footprint zelf — de pads
liggen 3,80 mm van die rand en 4,00 mm van de andere, en de fab-laag tekent
daar een aparte band — maar het is niet aan een echt blokje nagemeten. Klopt
het niet, zet `INVOER` bovenin `pcb.py` op `0` en alle klemmen draaien in één
keer om.

**RJ12's:** de stekker gaat er aan de +Y-kant in. Dat is wél zeker: de pinnen
zitten achterin, op Y = 0 tot 2,5 mm, en aan de pinkant kan geen stekker in.

## Alles opnieuw uitvoeren

```bash
bash build.sh
```

Dat genereert het schema, controleert de netlist, draait de ERC, plaatst en
rout het bord, draait de DRC, en maakt tekeningen, renders, stuklijst en
Gerbers. Het stopt bij de eerste fout: een ERC of DRC met ook maar één melding,
of een verbinding die open blijft, levert geen Gerbers op. De huidige stand:
**0 ERC-meldingen, 0 DRC-meldingen, 0 onverbonden items.**

Freerouting (en Java 25) staan gebruikersbreed in
`%LOCALAPPDATA%\Programs\freerouting`; zet `FREEROUTING_JAR` om een andere te
gebruiken. De oude eigen router `route.py` werkt nog, maar de build gebruikt
hem niet meer.

Had je het project open in KiCad: sluit het en open het opnieuw. **Sla niet op
vanuit KiCad** — dat schrijft over de gegenereerde bestanden heen, en bij de
volgende build is het weer weg.

## Gegenereerde bestanden

In `esp32ct-revc/` staan naast de schema- en bordbestanden ook:

| Bestand | Wat |
|---|---|
| `esp32ct-revc-gerbers.zip` | Gerbers + boorbestanden, dit upload je bij de fabriek |
| `productie/` | dezelfde bestanden los |
| `render_top.png`, `render_bottom.png` | 3D-aanzicht van beide kanten |
| `plaatsing.pdf`, `bovenkant.pdf`, `onderkant.pdf` | bordtekeningen; de onderkant gespiegeld |
| `esp32ct-revc.pdf` | het schema |
| `bom.csv` | stuklijst |
| `esp32ct-revc.net`, `erc.txt`, `drc.txt` | netlist en controlerapporten |

Die worden allemaal opnieuw gemaakt door `build.sh` en zijn dus geen handwerk.

De symbolen staan in `esp32ct.kicad_sym`, een projecteigen bibliotheek. Het
project verwijst daar via `sym-lib-table` naar, dus het opent op elke machine
zonder dat je iets hoeft te installeren.

## Onderdelen van derden

De footprint van de ESP32-module komt uit
[r0oland/ESP32_mini_KiCad_Library](https://github.com/r0oland/ESP32_mini_KiCad_Library),
Apache License 2.0. De bron staat in `lib/` samen met de licentietekst;
`sheets.py` kopieert hem naar `esp32ct.pretty/`.

Belangrijk gevolg: **de pinnummers van U1 zijn de echte padnummers van de
module, niet de GPIO-nummers.** GPIO34 is pad 11, GPIO35 is pad 7, GPIO13 is
pad 18, enzovoort. De vertaaltabel staat bovenaan `check_net.py` en in
`sheets.py` als `NET_PER_PAD`. Zonder die nummering sluit het symbool niet aan
op de footprint.

De klemmenblokken zijn het type dat de eigenaar op voorraad heeft: YIXISI
2-polig met **5,00 mm steek** (het blauwe KF301-type) — nadrukkelijk geen
5,08 mm. De footprint is een kopie van KiCad's MaiXu MX126 met een krappere
courtyard en zeefdruk; zie `lib/MX126_2P_5mm_krap.HERKOMST.txt`.
