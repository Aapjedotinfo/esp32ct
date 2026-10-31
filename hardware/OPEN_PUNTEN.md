# Open punten — esp32ct rev C

Dit is een **ontwerp** voor een nieuw bord. Het is afgeleid van het bord dat
nu in de meterkast hangt, maar wijkt er bewust van af. Hieronder: wat
vaststaat, wat je moet nameten of testen voordat je bestelt, en wat er
onderweg misging en hoe dat nu wordt afgevangen.

## Eerst dit: controleer voordat je bestelt

| Wat | Waarom | Hoe |
|---|---|---|
| **Rijafstand HW-178** | het voetje heeft twee female strips op 15,24 mm hart-op-hart. Wijkt jouw kloon af, dan steekt hij niet | schuifmaat tussen de SIG-rij en de C-rij |
| **Draadinvoer schroefklemmen** | alle 20 klemmen staan met de invoer naar buiten, afgeleid uit de footprint, niet nagemeten | vergelijk `plaatsing.pdf` met een echt blokje; fout = `INVOER = 0` in `pcb.py` |
| **Relaisbordje op 3,3 V** | zie hieronder bij de deurbel | IN aan 3,3 V hangen, VCC aan 5 V, kijken of het relais afvalt |
| **GPIO16/17 op de MiniKit** | nodig voor de P1-uitgang | kijk of die pinnen op jouw module naar buiten komen |
| **Breedte CT-klemmen** | de 16 CT-klemmen en de belknop staan op 10,795 mm steek; de footprint gaat uit van een body van 10,5 mm, dan blijft er ~0,3 mm tussen. Is jouw YIXISI-blokje breder, dan passen ze niet naast elkaar | schuifmaat over de breedte van één blokje: moet ≤ 10,7 mm zijn |
| **USB van de ESP32** | de USB-kant wijst naar de mux; tussen de twee modules zit ~9 mm, te weinig voor een stekker | eerste keer flashen vóórdat de HW-178 erin zit, daarna via OTA |

## Wat vaststaat

De pinbezetting van de bestaande functies is gelijk aan het huidige bord, op
twee pinnen na: P1_RTS en mux S1. Die kosten elk één regel in de firmware;
de volledige lijst met de YAML erbij staat in `PINMAPPING.md`.

| GPIO | Functie |
|---|---|
| 13 / 4 / 14 / 27 | S0 / S1 / S2 / S3 van de multiplexer — **S1 was GPIO12**; firmware: `pin_s1: GPIO4` |
| 34 | SIG van de multiplexer (ADC1_CH6) |
| 18 | P1 UART RX, vanaf de slimme meter |
| 23 | P1 data-request — **was GPIO19**; firmware: `request_pin: GPIO23` |
| 32 | watermeterpuls, inverted; nu met pull-up R18 (10k) naar 3,3 V op het bord |
| 33 | BEL1 (huis) naar het relaisbordje |
| 25 | BEL2 (garage) naar het relaisbordje |
| 26 | deurbelknop in, interne pull-up, inverted |
| 17 / 16 | **nieuw** — TX en data-request van de P1-uitgang naar de laadpaal |
| 35 | **vrij** — was SIG van de tweede multiplexer |

Besloten op 22 en 23-09-2026:

- **16 universele CT-kanalen**, zonder groepsnamen op het bord. Welke groep
  waar zit is bedrading en hoort bij de bedrading en staat niet in deze repository.
- **Eén multiplexer**, als HW-178-breakout plat op twee female headers.
  De laadpaal wordt gestuurd via de nagebootste P1-uitgang.
- **Per kanaal een 33 Ω burden met een jumper in serie.** Dicht voor een kale
  ringkern, open voor een klem met eigen burden zoals de SCT013. Een jumper
  *over* de burden zou de klem kortsluiten.
- **Alle externe aansluitingen op schroefklem** (YIXISI, 5,00 mm), behalve de
  twee RJ12's.
- **De relais zijn van het bord af.** Een kant-en-klaar Arduino-relaisbordje
  hangt met vier draden aan twee klemmen (J4/J5). De deurbelknop blijft op
  dit bord.

Besloten op 25-09-2026:

- **Watermeter op 5 V.** De sensor is een inductieve 5V-NPN (open collector,
  normally open): bruin +5 V, blauw GND, zwart puls. De pull-up R18 gaat naar
  **3,3 V**, niet naar 5 V: de sensor schakelt alleen naar massa, dus er komt
  nooit meer dan 3,3 V op GPIO32 en een deler is niet nodig.
- **Indeling:** de mux in het midden tussen de CT-rijen, de ESP32 aan de
  rechterrand met de antenne naar buiten, de twee RJ12's onder elkaar op de
  rechterrand (~6 mm van het montagegat), en op de linkerrand van boven naar
  onder POWER IN, WATER en RELAIS.
- **Relaisbordje op schroefklemmen** J4 (5V/GND) en J5 (BEL1/BEL2) in plaats
  van een pinheader.
- **Zekeringen.** F1 zit direct achter de voedingsklem J1 (POWER IN): de
  hele 5 V van het bord gaat erdoor. F2 zit op de 5 V naar pin 1 van de
  P1-uitgang, vóór JP1, zodat kortsluiting in de laadpaalkabel niet het hele
  bord platlegt. Waarden en footprint: zie rev C hieronder.
- **P1_RTS op GPIO23** in plaats van GPIO19. Pad 10 zat na de herindeling
  ingeklemd tussen de P1-lijnen en Freerouting kreeg het er niet schoon langs.
  Eén regel in de firmware.
- **Mux S1 op GPIO4** in plaats van GPIO12. GPIO12 is een strapping pin: hoog
  bij het opstarten zet de flash op 1,8 V en dan start de module niet. Op
  het bord hangt aan geen enkele strapping pin (GPIO0, 2, 5, 12, 15) nog iets,
  en `check_net.py` bewaakt dat. Ook één regel in de firmware.
- De RJ12's heten op de zeefdruk **P1 INPUT** (van de meter) en **P1 OUTPUT**
  (naar de laadpaal). Bij JP1/F2 staat "5V NAAR P1 OUT".
- **Staande burdenweerstanden**, elektrisch gelijk aan liggende. Daarmee
  bepaalt de klem de steek en kon het bord kleiner.
- **Aapje.Info** op de zeefdruk, voor en achter.
- Bord **115 × 103 mm** (was 150 × 110).

Rev C, 25-09-2026. Elektrisch gelijk aan rev B; de pinbezetting ook:

- **Waarden op de zeefdruk** bij alle weerstanden, condensatoren, zekeringen,
  transistors en de opamp. Ze komen uit de waarden in het schema, dus ze
  zeggen hetzelfde als de stuklijst. Bij een liggende weerstand staat de
  waarde in het lijf, bij de burdens rechtop tussen burden en jumper, bij de
  condensatoren eronder, bij Q1/Q4 op één regel met de referentie. Een "(?)"
  in de stuklijst (niet nagemeten op het oude bord) staat niet op de
  zeefdruk: daar staat de ontwerpwaarde.
- **F1 = 1 A traag, F2 = 200 mA**, allebei liggend (F2 was staand) met 10,16 mm
  steek: een axiale zekering, of een 0 Ω-brug. Op de 5 V hangen de ESP32
  (WiFi-pieken tot ~0,5 A), het relaisbordje (~0,15 A met beide relais aan),
  de watermeter en via F2 de laadpaal (tot 0,2 A): samen hooguit ~1 A. DSMR
  staat max 250 mA op pin 1 van de P1-poort toe, vandaar 200 mA voor F2.

## Wat NIET geverifieerd is

Ingetekend als de gangbare schakeling, niet van het huidige bord afgelezen.

| Blad | Punt |
|---|---|
| Voeding | waarden van de 1,65 V-deler (R1/R2) en de dempcondensator C3 |
| Voeding | of de LM358 op 3,3 V of op 5 V moet |
| Voeding | aanwezigheid en waarde van de bufferelco's C1/C2 |
| P1 in | weerstandswaarden van de inverter |
| P1 in | of P1_RTS rechtstreeks aan GPIO23 mag of via een niveauomzetter moet |
| P1 uit | alle weerstandswaarden zijn ontwerpkeuzes, geen meting |

## Deurbel: klemmen naar een relaisbordje

J4 en J5 (titel RELAIS op de zeefdruk) gaan met vier draden naar een standaard
Arduino-relaisbordje met twee kanalen:

| Klem | Signaal | Relaisbordje |
|---|---|---|
| J4-1 | +5V | VCC |
| J4-2 | GND | GND |
| J5-1 | BEL1 (huis), GPIO33 | IN1 |
| J5-2 | BEL2 (garage), GPIO25 | IN2 |

De beltrafo en de twee bellen komen op de schroefklemmen van het relaisbordje:
trafo naar COM van beide relais, NO naar de bel, retour van beide bellen
rechtstreeks terug naar de trafo.

**Twee dingen om te weten:**

1. **De firmware moet `inverted: true` krijgen.** Die bordjes zijn actief-laag:
   het relais komt op als IN naar massa gaat. In `firmware/esp32ct-revc.yaml` staan de
   switches op GPIO33 en GPIO25 nu zonder `inverted`, en een ESP32-pin is laag
   tijdens het opstarten. Zonder die aanpassing gaat de bel bij elke reboot.
   Bewust niet doorgevoerd: de deurbel op het huidige bord werkt nu.

2. **Vier draden kan krap zijn.** De logicakant van zo'n bordje hangt aan 5 V,
   de ESP32 stuurt maar 3,3 V, dus er blijft 1,7 V over de opto-LED staan.
   Bij sommige bordjes zet dat de opto half open en valt het relais niet netjes
   af. Gekozen voor vier draden; test je bordje eerst. Klappert het, voed dan de
   logicakant (VCC) uit 3,3 V en de spoelen (JD-VCC) uit 5 V, met de jumper op
   het relaisbordje eraf. Dan is er een vijfde draad nodig.

## P1-uitgang naar de laadpaal

Een tweede RJ12 waarmee dit bord zélf voor slimme meter speelt, zodat de
laadpaal op een zelfbedacht vermogen kan loadbalancen.

De P1-datalijn is geïnverteerd, werkt op 5 V en is open-collector: in rust ligt
de lijn laag en een pull-up tilt hem hoog voor elke bit. Een ESP32-pin kan dat
niet — 3,3 V is te laag en de polariteit klopt niet. Q4 lost beide op: de UART
zendt gewoon normaal en de transistor draait het om, terwijl R14 de lijn naar
5 V tilt.

Wat de firmware nog moet doen:

- UART2 op GPIO17, 115200 8N1 voor DSMR 5. **Niet** `inverted` in software —
  Q4 doet de inversie al in hardware.
- zelf een telegram opbouwen en afsluiten met CRC16 over alles vanaf de `/` tot
  en met de `!`, anders verwerpt de laadpaal het.
- GPIO16 mag je negeren en gewoon elke seconde zenden.

Nog open: of de laadpaal DSMR 5 (115200 8N1) of het oudere DSMR 2/3 (9600 7E1)
verwacht — dat scheelt alleen firmware — en of hij de 5 V van RJ12-pin 1 nodig
heeft; JP1 laat die keuze open.

## ESP32-antenne

De module ligt aan de rechterrand met de antenne naar buiten: aan drie kanten
van de antenne geen koper en geen connectoren. Onder de antenne ligt een
verbodsgebied voor koper, banen en via's op beide lagen. De footprint van
r0oland tekent daar zelf "NO COPPER – KEEP OUT". Zonder dat verbod vullen de
massavlakken het dicht en wordt de WiFi-ontvangst slechter — en in een
meterkast is die al niet ruim.

## Wat er misging, en hoe dat nu wordt afgevangen

Op 23-09-2026 bleken drie symbolen **verzonnen pinnummers** te hebben:

| Onderdeel | Echt | Was getekend als | Gevolg |
|---|---|---|---|
| CD74HC4067 | pin 1 SIG, 12 GND, 24 VCC | I0…I15 op pin 1…16 | mux kortgesloten, VCC aan GND |
| LM358 | pin 2 IN−, pin 3 IN+ | andersom | VBIAS-volger meegekoppeld, alle kanalen dood |
| BC547 | 1 C, 2 B, 3 E | 1 B, 2 C, 3 E | beide P1-transistors verkeerd |

Het schema was intern consistent, ERC en netlist waren schoon — en het bord zou
nooit gewerkt hebben. Die controles kijken of het schema *met zichzelf* klopt,
niet of het klopt met het echte onderdeel.

Nu gecorrigeerd, en `check_net.py` bevat een blok **fysieke pinbezetting** dat
de pinnen van de echte onderdelen afdwingt, met de bron erbij: KiCad's eigen
symbolen voor de LM358 en BC547, SparkFun's bordbestand voor het HW-178. Door de
oude fouten tijdelijk terug te zetten is nagegaan dat die controle ze vangt.

Tegelijk bleek dat:

- **de ESP32-footprint geen courtyard had.** DRC kon dus nooit zien of er iets
  onder of over de module lag. Toegevoegd, volgens de zeefdruk van de module.
- **beide RJ12's verkeerd om stonden**, met de opening naar binnen. De pinnen
  zitten achterin, dus de stekker gaat er aan de +Y-kant in.

## Het huidige bord

Het as-built schema van het huidige bord
staat bevroren in `esp32ct-asbuilt/`; let op dat dat nog de foute symbolen
hierboven bevat.
