# esp32ct rev C: beschrijving van de print (voor Codex)

Alle maten in mm, uit `esp32ct-revc/esp32ct-revc.kicad_pcb`. Het coördinatenstelsel is
dat van KiCad: oorsprong linksboven, **x naar rechts, y naar beneden**.

## Printafmetingen

| | |
|---|---|
| Omtrek | rechthoek, **115 × 103 mm** (x 0 tot 115, y 0 tot 103) |
| Lagen | 2 (voor en achter koper), FR4, **1,6 mm** dik |
| Onderdelen | alles doorsteek (THT), op de bovenkant |
| Ruimte | het bord is plat: grootste onderdeel is de ESP32-module met een rij pinnen |

## De 4 bevestigingsgaten

M3, gat 3,2 mm, **4,5 mm vanaf beide randen** van de hoek:

| Gat | x | y |
|---|---|---|
| H1 linksboven | 4,5 | 4,5 |
| H2 rechtsboven | 110,5 | 4,5 |
| H3 linksonder | 4,5 | 98,5 |
| H4 rechtsonder | 110,5 | 98,5 |

Afstand tussen de gaten: **106 mm** horizontaal, **94 mm** verticaal.

## Indeling per rand

- **Bovenrand (y = 5,7):** CT-klemmen CT1 t/m CT8 (J11 t/m J18), x = 16,5 / 27,3 / 38,1 /
  48,9 / 59,7 / 70,5 / 81,3 / 92,1 (steek 10,8 mm). Eronder bij y = 14,6 de
  burden-jumpers JP101 t/m JP108.
- **Onderrand (y = 97,2):** CT9 t/m CT16 (J19 t/m J26), x = 12,1 / 22,9 / 33,7 / 44,5 /
  55,2 / 66,0 / 76,8 / 87,6. Daarnaast de deurbelknop J6 (x = 98,4). Erboven bij y = 88,3
  de burden-jumpers JP109 t/m JP116.
- **Linkerrand (x = 7,0):** J1 (5 V extern, y = 24,1), J3 en J9 (watermeter, y = 37,5 en
  48,9), J4 en J5 (relaisbordje, y = 62,2 en 73,7).
- **Rechterrand (x = 97,8):** twee RJ12-jacks onder elkaar, opening naar buiten (+x):
  J2 = P1 INPUT (y = 24,8) en J8 = P1 OUTPUT (y = 39,4).

## Onderdelen in het midden

- **U1**, ESP32 MiniKit (MH-ET Live D1 mini), op (95,3 / 66,7), 90° gedraaid, antenne naar
  de rechterrand.
- **U3**, voetje voor het HW-178-breakout (CD74HC4067, 16-kanaals mux) op (59,7 / 70,5).
- **U2**, LM358 (DIP-8) op (18,4 / 30,5): opamp als spanningsvolger voor de 1,65 V middenrail.
- Voeding: F1 (1 A) op (12,7 / 22,2), C1 100 µF op (17,8 / 46,4), C2 100 nF op (25,4 / 46,4),
  C3 10 µF op (19,7 / 68,6).
- P1-onderdelen bij de RJ12's: Q1 en Q4 (BC547), F2 (200 mA) en JP1 (5 V naar de P1-uitgang).
- Klemmen zijn 2-polig, 5 mm steek (`MX126_2P_5mm_krap`).

## Wat de print doet

22-kanaals stroommeting (CT-klemmen via een 16-kanaals mux op een ESP32), plus
P1-slimme-meter-ingang (J2), nagebootste P1-uitgang naar een laadpaal (J8),
watermeterpuls (J3/J9), deurbel (knop en twee relais). ESP32-pinmapping staat in
`PINMAPPING.md`.

## Bestanden

`esp32ct-revc/` bevat de Gerbers (zip), PDF's van schema en print, renders, `bom.csv`.
Bron van het ontwerp zijn de Python-scripts in deze map (`sheets.py`, `pcb.py`, `build.sh`).
