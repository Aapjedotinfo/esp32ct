# HA: uitgezet tijdens de overstap naar ESP32CT rev C (12-11-2026)

**Stand 12-11-2026 22:10:** de OUDE ESP (MAC e0:5a:1b:d0:7d:38, 192.168.50.41) zit op rev C met
`esphome/esp32ct-oudeesp-revc.yaml` (rev C-firmware onder de oude naam esp32ct, dus de entiteiten
meterkast_esp32ct_* en hun historie lopen door). P1 werkt via de Eneco-splitter; spoor GPIO23 -> J2 pin 2
is doorgeknipt en pin 2 krijgt 5 V via een draadje (de meter zendt niet op 3,3 V). CT-klemmen zijn nog niet
gemonteerd (jumpers zitten), dus alle CT-waarden staan op 0. De USB-C-ESP (esp32ct-revc) is niet in gebruik.
Zonder splitter is waarschijnlijk ook een pull-up op de datalijn (J2 pin 5 naar 5 V, 4k7) nodig.

Op verzoek van Michael uitgezet omdat ze CT-klemwaarden van het oude bord (meterkast_esp32ct) gebruiken.
Weer aanzetten (automation.turn_on) zodra de rev C-entiteiten werken en de verwijzingen kloppen.

| Automatisering | Entiteit | CT-kanaal / groep |
|---|---|---|
| automation.oven_melding_zodra_hij_op_temperatuur_is (Oven - melding zodra hij op temperatuur is) | sensor.meterkast_esp32ct_power_oven | CT8, Oven |
| automation.accuplan_kwartier_opnieuw_beoordelen_als_de_laadpaal_aan_of_uit_gaat | sensor.meterkast_esp32ct_power_laadpaal_totaal | CT3+CT4+CT5, Laadpaal L1-L3 (som) |

## Niet uitgezet: gebruikt P1 (DSMR) van hetzelfde bord, geen CT-klem
Deze vallen ook weg als het oude bord uit is, tenzij rev C de P1 onder dezelfde namen levert.
- Voltage onder 10v op net (voltage_l1..l3)
- ThuisAccu - Dynamische laadlimiet per fase (current_l1..l3, slimmelezer_uptime)
- ThuisAccu - Fasebeveiliging (current_l1..l3, voltage_l1..l3)
- ThuisAccu - Snelle faseruimte (voltage_l1..l3)
- Tesla - terugschakelen bij aanhoudende overbelasting (current_l1..l3)
- Deurbel (sensor.meterkast_esp32ct_doorbell)

## Geen automatisering, wel CT-gebruik (pyscript / Energie)
- accuplan.py: power_droger (CT1), power_wasmachine (CT7), power_oven (CT8), power_vaatwasser (CT10), power_laadpaal_totaal en energy_laadpaal (CT3-5); ook de P1-fasewaarden.
- accuplan_maandprijs.py, energie_gisteren.py, Energie-dashboard bron "Laadpaal": energy_laadpaal (+ _compensation).
- configuration.yaml recorder-exclude: current/power_solaredge (CT15), current/power_laadpaal_l? (CT3-5).

LET OP (Michael, 12-11-2026): de namen en groepen van de kanalen op rev C zijn nog ONBEPAALD. De CT-nummers en groepen hierboven zijn de indeling van het OUDE bord; niet aannemen dat ze op rev C hetzelfde blijven. Pas weer aanzetten of omleggen als Michael de nieuwe indeling heeft vastgesteld.

Kanaalindeling oud bord: zie de overdracht van de ESP32CT-sessie (side-session-notes/.../overdracht-esp32ct-revc.md, 12-11-2026).
Let op uit die overdracht: op 10.13.40.24 stonden alle P1-sensoren van rev C op NA. Of rev C de P1 echt leest is dus nog niet bewezen; dat raakt de zes P1-automatiseringen hierboven.
