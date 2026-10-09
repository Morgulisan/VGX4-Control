# VG-X4 Schreibatelier — MVP

Lokale Steuerungswebsite mit Python-Server für den VigoTec VG-X4 (VigoWriter 1.1f).
Starten verbindet den Roboter **nicht** automatisch. Kein Flashen, keine Firmwareänderungen,
kein Dongle-Eingriff und keine externen Webdienste.

## Start unter Windows

Python 3.10 oder neuer installieren, dann `START_WINDOWS.bat` doppelklicken.
Beim ersten Start werden die zwei Abhängigkeiten installiert; dafür ist Internet erforderlich.
Danach läuft alles lokal unter **http://127.0.0.1:8765**.

Der Server startet immer **live**: Die Port-Liste zeigt die echten COM-Ports.
Zum Ausprobieren ohne Roboter gibt es in Schritt 01 den bewusst eingeklappten Punkt
**Ohne Roboter testen … → Simulation starten**. Solange die Simulation läuft, zeigen ein gelber Hinweis,
das Badge „SIMULATION“ und der Button „Simuliert schreiben“ das deutlich an; es wird kein COM-Port geöffnet.

`START_DEMO.bat` (bzw. `app.py --demo`) startet einen reinen Simulationsserver ohne echte Ports,
z. B. zum Vorführen. Die Oberfläche weist dann dauerhaft auf den Simulationsmodus hin.
Zum Beenden das Terminal mit Strg+C stoppen.

Alternativ:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
# nur Simulation: app.py --demo --no-browser --port 8766
```

## Bedienung

1. **01 Verbinden:** USB-Port wählen und verbinden; 115200 Baud, Firmwareprüfung.
   Der zuletzt genutzte Port wird vorausgewählt (sonst COM4).
2. **02 Startpunkt & Stift:** Wagen bei freiem Fahrweg mit 1/5/10-mm-Schritten zur oberen linken
   Papierecke fahren. +X = rechts, +Y = unten. Jog hebt den Stift an und verwirft einen gesetzten Startpunkt.
   **Hier ist oben links · 0 / 0** setzt G92 X0 Y0 und hebt den Stift.
   Stift mit dem Stiftwert (Standard **S905**) absenken, Kontakt beobachten, dann
   **Kontakt passt · bestätigen & anheben**.
3. **03 Text:** Text, Papier, Stil, Tempo, Schrifthöhe, Zeilenabstand und Rand wählen.
   Die Vorschau aktualisiert sich automatisch; ↻ erzeugt sie bei Bedarf neu.
4. **04 Prüfen & schreiben:** Die Checkliste zeigt, was noch fehlt (mit Sprung zum jeweiligen Schritt).
   Bereits bekannten Papierkontakt kann man dort direkt bestätigen, wenn er nicht in Schritt 02 getestet wurde.
   Anwesenheit und freien Fahrbereich bestätigen, optional Trockenlauf, dann **Auf Papier schreiben**.

Während einer Fahrt erscheint unten eine feste Laufleiste mit Fortschritt, verstrichener Zeit,
geschätzter Restzeit, Live-Tempo, **Pause/Fortsetzen** und **Abbrechen**; sie bleibt beim Scrollen sichtbar.
Nach dem Schreiben wird die Bestätigung „Fahrbereich frei“ zurückgesetzt, damit dasselbe Blatt
nicht versehentlich zweimal beschrieben wird.

Die Freigabe gilt nur für den exakt erzeugten Auftrag; jede Änderung erzeugt einen neuen Auftrag.
Verbindung wird während einer Sitzung gehalten. Nach Reset/Fehler/Abbruch neu verbinden und Startpunkt setzen.
Alle Jobs enden mit Stift oben und Rückfahrt zum Start. Der Server wartet auf echtes Idle,
bevor er einen Vorgang als fertig meldet.

## Enthalten

- Deutsche responsive Oberfläche ohne CDN, Schrift- oder Netzwerkdienste; heller und dunkler Modus nach Systemeinstellung
- COM-Port-Auswahl, Firmwareprüfung, Arbeitsposition nach abgeschlossenen Vorgängen
- Stift hoch/runter, S0–1000; Standard S905; Stiftzustand im Kopfbereich
- A6 und A5, A4 quer, drei generierte Schriftstile, Umlaute; typografische Anführungszeichen,
  Gedankenstriche und Auslassungspunkte aus Textverarbeitungen werden automatisch ersetzt
- SVG-Vorschau mit Dauerschätzung, überprüfte G-Code-Ausgabe, Download und gespeicherte Aufträge
- Ein laufender Vorgang, Fortschritt nach bestätigten Befehlen, Restzeit, Pause/Fortsetzen und Abbruch
- Text und Einstellungen bleiben im Browser gespeichert (localStorage), auch nach Neuladen
- Simulation nur auf ausdrücklichen Wunsch (Extra-Schritt oder `--demo`) und automatisierte Tests ohne Hardware

## Grenzen und Gerätekontext

Es gibt **keine Z-Achse**, kein Homing und derzeit keine vermessenen mechanischen Soft-Limits.
Papiergrenzen werden geprüft; ob das Papier innerhalb des realen Maschinenfahrwegs liegt,
muss der Bediener prüfen. Jog-Schritte sind auf 20 mm begrenzt und kennen keine absoluten Rahmenanschläge.
Herstellerangabe 310 × 256 mm ist eine Obergrenze für die Software, keine vermessene Freigabe.
A4 hochkant (297 mm nach unten) ist deshalb nicht angeboten.

Pause ist GRBL Feed Hold: Stift kann auf dem Papier bleiben.
Abbruch sendet GRBL Soft Reset; das ist **kein physischer Not-Aus** und garantiert kein Stiftanheben.
Bei einem Fehler wird nicht automatisch zurückgefahren. Netzschalter bleibt direkt erreichbar.
Die Seite darf geschlossen werden, während der lokale Server weiterläuft; sie zeigt nach erneutem Öffnen
den laufenden Status. Eine neue Vorschau ist für einen neuen Start erforderlich.

Die Schrift ist die vorhandene Einzelstrich-Programmschrift mit kleinen Abweichungen.
Persönliche Handschrift, Upload/Nachzeichnen von Schriftproben, freie G-Code-Eingabe,
Netzwerkzugriff und Mehrbenutzerbetrieb sind nicht Teil dieses MVP.

## Dateien

- `app.py`: lokaler HTTP-Server, Zugriffstoken, Browserstart
- `controller.py`: Zustände, Aufträge, Freigaben, Hintergrundausführung
- `device.py`: pySerial/Simulation, ACK, Idle, Echtzeitbefehle
- `web/`: HTML, CSS und JavaScript
- `vgx4_profile.py`, `cli.py`, `core/`, `humanizer/`, `exporter/`: vorhandener Schriftgenerator
- `jobs/<id>/`: Text, SVG, G-Code und Auftragseinstellungen jedes gestarteten Auftrags (nicht in Git).
  Reine Vorschauen werden nicht mehr gespeichert.
- `logs/control.log`: rotierendes lokales Protokoll (nicht in Git)

Der Generator wurde aus dem lokalen, vom Nutzer bereitgestellten Paket
`VGX4_Handschrift_v2.7.2` übernommen. Es wird keine neue Lizenz für diesen Bestand behauptet.
Der Servo-Standard im übernommenen Profil wurde auf den im Gerätetest bestätigten Wert S905 angepasst.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Die Tests simulieren das Gerät. Sie prüfen den Ablauf inklusive Trockenlaufbindung,
Eingabegrenzen, Pause/Abbruch, HTTP-Zugriffsschutz und G-Code. Hardware wurde beim Bau des MVP nicht bewegt.

## Dokumentvorschau und Tempo

Die Vorschau erscheint automatisch beim Öffnen und aktualisiert sich nach Texteingaben oder Einstellungsänderungen. Sie zeigt das gesamte Blatt mit Rand und Position. Ihre Linien werden direkt aus den gerundeten Stift-unten-Koordinaten des tatsächlich gesendeten G-Codes abgeleitet; Leerfahrten werden nicht gezeichnet. Eine reale Strichbreite oder mechanische Abweichung kann die Software nicht vorhersagen.

Ungültige Eingaben (z. B. Schrifthöhe außerhalb 2,5–15 mm) werden am Feld markiert und direkt unter der Vorschau erklärt, ohne den Server zu fragen. Fehler des Generators (Text passt nicht, Wort zu lang, nicht schreibbare Zeichen, Zeilenabstand zu klein) erscheinen dort ebenfalls auf Deutsch. Der Rand gilt für alle vier Seiten.

Geschwindigkeit: 25–300 % des bisherigen, kurvenabhängigen Tempos. 100 % entspricht dem getesteten Ausgangstempo. Auch Leerfahrten und Trockenlauf werden angepasst. Jeder Vorschub bleibt auf höchstens 2200 mm/min begrenzt; gerade Schreibstrecken erreichen diese Grenze ab ca. 176 %, darüber werden vor allem Kurven und Ecken schneller. Eine Tempoänderung im Textbereich erzeugt einen neuen Auftrag. Während einer Fahrt ändert der Live-Regler (10–150 %) das Auftragstempo über GRBL-Echtzeitbefehle; jeder Lauf beginnt bei 100 %.

Stiftpause (100–600 ms, Standard 300 ms, früher fest 450 ms): Wartezeit nach jedem Absenken und Anheben des Stifts. Bei vielen Stiftwechseln ist sie der größte Zeitanteil; das Tempo ändert sie nicht. Zeigen sich Schleifspuren zwischen Buchstaben oder fehlen Strichanfänge, die Pause erhöhen.

Weniger Stiftwechsel: Striche, die sich berühren, werden ohne Anheben gezeichnet (z. B. u, a, n, m, h, E). Dafür fährt der Stift höchstens 1,25 Schrifthöhen (max. 10 mm) exakt über bereits gezeichnete Linien zurück; Lücken bis ca. 0,3 mm durch das Handschrift-Zittern werden überbrückt. Getrennte Elemente wie i-Punkte oder Kreuzungen bleiben getrennt. Das gilt für jeden Schriftstil und jede Größe.

Die Dauer ist eine Schätzung aus Weglänge, Vorschub und Servopausen und zeigt den Anteil der Stiftpausen; Beschleunigungsgrenzen des Controllers können die reale Fahrt verlängern. Die Restzeit während der Fahrt berücksichtigt das Live-Tempo.

## Vorschau mit Fahrwegen und schnelle Stiftbedienung

Leerfahrten sind als rote gestrichelte Pfade einblendbar, die eingestellten Textränder als grüner Rahmen. Die abschließende Rückfahrt bleibt im G-Code, wird aber nicht rot dargestellt. Der rote Punkt zeigt die zuletzt gemeldete Arbeitsposition, sobald ein Startpunkt gesetzt ist; auch beim Joggen bleibt die Referenz sichtbar. Nach Trennen/Reset wird der Punkt ausgeblendet, bis der Startpunkt neu gesetzt ist. Der Punkt bewegt sich anhand der Statusmeldungen, nicht anhand der Befehlsbestätigungen.

Manuelle Stiftbefehle nutzen 120 ms Beruhigungszeit statt 600 ms und benötigen keine neue WCO-Koordinatenmeldung. Die Oberfläche bleibt während dieser kurzen Aktionen editierbar. Hardwarebefehle werden weiterhin nacheinander bestätigt. Schreibaufträge nutzen die eingestellte Stiftpause. Meldungen werden während Fahrten etwa alle 120 ms abgefragt; die Oberfläche liest den Status während eines Vorgangs alle 200 ms, im Leerlauf alle 600 ms.
