# Pinmapping esp32ct rev C, voor de ESPHome-configuratie

Afgeleid uit de netlist van rev C (`esp32ct-revc/esp32ct-revc.net`) en naast
de draaiende firmware (`../firmware/esp32ct-revc.yaml`) gelegd. Module: MH-ET Live ESP32
MiniKit, board `mhetesp32minikit`.

Bijna alles blijft zoals het is. **Voor rev C moeten er vier dingen in de
YAML veranderen:**

| # | Wat | Nu (huidige bord) | Rev C |
|---|---|---|---|
| 1 | P1 data-request | `request_pin: GPIO19` | `request_pin: GPIO23` |
| 2 | mux-adres S1 | `pin_s1: GPIO12` | `pin_s1: GPIO4`. GPIO12 is een strapping pin en hangt op rev C nergens meer aan |
| 3 | Belrelais op GPIO33 en GPIO25 | geen `inverted` | `inverted: true` + `restore_mode: ALWAYS_OFF`. Het Arduino-relaisbordje is actief-laag; zonder dit gaat de bel bij elke reboot |
| 4 | P1-uitgang naar de laadpaal | bestaat niet | tweede UART, TX op GPIO17, **niet** inverted (Q4 inverteert al in hardware) |

Verder: de ESP32 één keer via USB flashen **vóórdat de HW-178 erin gaat**. De
USB-kant wijst naar de mux en daar past geen stekker meer tussen. Daarna gaat
het via OTA.

## Per GPIO

| GPIO | Pad | Net | Functie | Op het bord | ESPHome |
|---|---|---|---|---|---|
| 34 | 11 | SIG_MUX1 | analoge uitgang van de mux (ADC1_CH6) | HW-178 SIG | `adc`, `attenuation: 12db`, `update_interval: never`; ongewijzigd |
| 13 | 18 | MUX_S0 | mux-adres bit 0 | HW-178 S0 | `cd74hc4067` `pin_s0`; ongewijzigd |
| **4** | 32 | MUX_S1 | mux-adres bit 1 | HW-178 S1 | `pin_s1: GPIO4` (**was GPIO12**) |
| 14 | 13 | MUX_S2 | mux-adres bit 2 | HW-178 S2 | `pin_s2`; ongewijzigd |
| 27 | 24 | MUX_S3 | mux-adres bit 3 | HW-178 S3 | `pin_s3`; ongewijzigd |
| 18 | 8 | P1_RX | P1-data van de meter, na inverter Q1 | J2 (P1 INPUT) pin 5 | `uart` `rx_pin`, 115200; niet inverted; ongewijzigd |
| **23** | 12 | P1_RTS | data-request naar de meter | J2 (P1 INPUT) pin 2 | `dsmr` `request_pin: GPIO23` (**was GPIO19**) |
| 32 | 28 | WATER_PULS | watermeterpuls, R18 10k naar 3,3 V | J3 pin 2 (PULS) | `pulse_meter` en `binary_sensor`, `inverted: true`; ongewijzigd. `pullup: true` mag blijven staan |
| 33 | 9 | BEL_HUIS | relais 1 (huis) | J5 pin 1 (BEL1) naar IN1 | `switch` gpio, **`inverted: true`** |
| 25 | 26 | BEL_GARAGE | relais 2 (garage) | J5 pin 2 (BEL2) naar IN2 | `switch` gpio, **`inverted: true`** |
| 26 | 6 | BEL_IN | deurbelknop, maakcontact naar GND | J6 pin 1 (KNOP) | `binary_sensor`, `INPUT_PULLUP`, `inverted: true`; ongewijzigd |
| **17** | 29 | P1OUT_TX | nagebootste P1-data naar de laadpaal | via R13 + Q4 naar J8 (P1 OUTPUT) pin 5 | **nieuw**: UART2 TX, 115200 8N1, **niet** inverted |
| **16** | 31 | P1OUT_RTS | data-request van de laadpaal | J8 pin 2 via deler 10k/15k (5 V wordt ~3,0 V) | **nieuw**, optioneel: `binary_sensor`. Mag je negeren en gewoon elke seconde zenden |

Voeding: 5 V op pad 35 (VCC), 3,3 V op pad 16, GND op pad 1, 22 en 33. De
3,3 V komt van de regelaar op de module en voedt de mux, de LM358 (VBIAS
1,65 V) en de pull-ups.

**Geen strapping pins in gebruik.** GPIO0, 2, 5, 12 en 15 bepalen bij het
opstarten de opstartmodus en de flashspanning. Een hoge GPIO12 zet het
flashgeheugen op 1,8 V, en dan start de module niet. Daarom zit S1 op rev C op
GPIO4. `check_net.py` faalt als er ooit weer iets aan een van deze vijf hangt.

**Vrij en nergens aangesloten:** GPIO19, 21, 22, 35, 36 en 39. Wil je er later
iets mee, soldeer dan een draadje op de pad aan de onderkant. GPIO35, 36 en
39 zijn alleen ingang. De strapping pins zijn ook vrij, maar gebruik die
liever niet. GPIO1/3 (TXD/RXD) zijn de USB-seriële poort. SD0 tot en met SD3,
CMD en CLK gaan naar het flashgeheugen en zijn niet bruikbaar.

## CT-kanalen

Eén mux, 16 kanalen. **CT-nummer op de zeefdruk = mux-kanaal + 1.** Dat past
bij de huidige firmware: `ai1` heeft `number: 0`, en zo verder tot `ai16` met
`number: 15`.

| Zeefdruk | Klem | Mux-kanaal (`number:`) | Plek op het bord |
|---|---|---|---|
| CT1 t/m CT8 | J11 t/m J18 | 0 t/m 7 | bovenrand, van links naar rechts |
| CT9 t/m CT16 | J19 t/m J26 | 8 t/m 15 | onderrand, van links naar rechts |

Per kanaal: klem pin 1 gaat naar de mux-ingang en de burden, pin 2 naar VBIAS
(1,65 V). De jumper JP101 t/m JP116 staat **in serie** met de 33 Ω-burden R101
t/m R116:

- **dicht**: burden actief, voor een kale ring zoals de GTA20L1.0 (1000:1)
- **open**: geen burden, voor een klem met ingebouwde burden zoals de
  SCT013 15A/1V

Een kanaal zonder klem: jumper **dicht** laten. Open en zonder klem zweeft de
mux-ingang, en dan meet dat kanaal ruis.

**Jumpers voor een gemengde indeling** (voorbeeld):

| CT | Klem | Jumper |
|---|---|---|
| kanalen met een kale ring (GTA20L1.0) | ring | dicht |
| kanalen met een klem met ingebouwde burden (SCT013) | SCT013 | **open** |

Zo blijven de kalibraties in de firmware geldig: de SCT013-curve hoort bij
"33 Ω weggeknipt" (jumper open), de ringcurve bij 33 Ω (jumper dicht). Wel de
ruisvloer opnieuw meten: die 0,042 in de kwadratische ruisaftrek is gemeten op
het huidige, rommelige bord.

Welke groep op welke CT zit, is bedrading en staat niet op het bord.

## Connectoren

**RJ12 J2, P1 INPUT** (van de slimme meter):

| Pin | Net | |
|---|---|---|
| 1 | niet aangesloten | +5 V van de meter, niet gebruikt |
| 2 | P1_RTS | GPIO23 |
| 3 | GND | data-GND |
| 4 | niet aangesloten | |
| 5 | P1_DATA | via R3 naar de basis van Q1, inverter naar GPIO18 |
| 6 | GND | voedings-GND |

**RJ12 J8, P1 OUTPUT** (naar de laadpaal):

| Pin | Net | |
|---|---|---|
| 1 | 5 V via F2 en JP1 | JP1 dicht = laadpaal krijgt 5 V; open laten als hij zichzelf voedt |
| 2 | RTS van de laadpaal | deler R16/R17 naar GPIO16 |
| 3 | GND | |
| 4 | niet aangesloten | |
| 5 | data | collector van Q4, pull-up R14 4k7 naar 5 V; gestuurd vanuit GPIO17 |
| 6 | GND | |

**Schroefklemmen** (YIXISI, 5,00 mm):

| Klem | Zeefdruk | Pin 1 | Pin 2 |
|---|---|---|---|
| J1 | POWER IN | +5 V in (via F1) | GND |
| J3 | WATER | +5 V voor de sensor (bruin) | PULS, GPIO32 (zwart) |
| J9 | WATER | GND (blauw) | GND |
| J4 | RELAIS | +5 V naar VCC van het relaisbordje | GND |
| J5 | RELAIS | BEL1, GPIO33, naar IN1 | BEL2, GPIO25, naar IN2 |
| J6 | KNOP | deurbelknop, GPIO26 | GND |

## ESPHome: de wijzigingen voor rev C

Alleen wat anders wordt; de rest van `esp32ct-revc.yaml` blijft staan.

```yaml
uart:
  - id: uart_bus            # P1 INPUT (J2), van de slimme meter
    rx_pin: GPIO18
    baud_rate: 115200
    rx_buffer_size: 1700
  - id: uart_p1_uit         # P1 OUTPUT (J8), naar de laadpaal
    tx_pin: GPIO17          # NIET inverted: Q4 draait het signaal al om
    baud_rate: 115200       # DSMR 5: 115200 8N1

cd74hc4067:
  - id: cd74hc4067_shared
    delay: 2ms
    pin_s0:
      number: GPIO13
    pin_s1:
      number: GPIO4         # was GPIO12 (strapping pin)
    pin_s2:
      number: GPIO14
    pin_s3:
      number: GPIO27

dsmr:
  id: dsmr_instance
  uart_id: uart_bus         # nodig zodra er twee UART's zijn
  max_telegram_length: 1700
  request_pin: GPIO23       # was GPIO19
  request_interval: 1s

switch:
  - platform: gpio
    pin:
      number: GPIO33
      inverted: true        # relaisbordje is actief-laag
    restore_mode: ALWAYS_OFF
    name: "Doorbell Relay Huis"
    id: relay_housebell
  - platform: gpio
    pin:
      number: GPIO25
      inverted: true
    restore_mode: ALWAYS_OFF
    name: "Doorbell Relay Garage"
    id: relay_garagebell

binary_sensor:
  - platform: gpio          # optioneel: vraagt de laadpaal om data?
    pin: GPIO16             # ~3,0 V als J8 pin 2 hoog is
    name: "Laadpaal data-request"
```

De laadpaal verwacht een geldig telegram: van `/` tot en met `!`, afgesloten
met een CRC16 (CRC-16/ARC) over precies dat stuk. Dat telegram bouw je zelf op,
bijvoorbeeld in een `interval` met `id(uart_p1_uit).write_str(...)`. Nog
open: of de laadpaal DSMR 5 (115200 8N1) of DSMR 2/3 (9600 7E1) verwacht.
Dat verandert alleen de `uart`-regels.

## Nog niet geverifieerd

- Of de meter de 3,3 V van GPIO23 op RTS als "hoog" ziet. DSMR schrijft 4 tot
  5,5 V voor; in rev C hangt RTS rechtstreeks aan de GPIO.
- Of GPIO16/17 op jouw MiniKit naar buiten komen (zie `OPEN_PUNTEN.md`).
- Of jouw relaisbordje met 3,3 V op IN netjes afvalt (zie `OPEN_PUNTEN.md`,
  deurbel).
