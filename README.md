# VG-X4 Schreibatelier — MVP

Lokale Steuerungswebsite mit Python-Server für den VigoTec VG-X4 (VigoWriter 1.1f).
Starten verbindet den Roboter **nicht** automatisch. Kein Flashen, keine Firmwareänderungen,
kein Dongle-Eingriff und keine externen Webdienste.

## Start unter Windows

Python 3.10 oder neuer installieren, dann `START_WINDOWS.bat` doppelklicken.
Beim ersten Start werden die zwei Abhängigkeiten installiert; dafür ist Internet erforderlich.
Danach läuft alles lokal unter **http://127.0.0.1:8765**.

`START_DEMO.bat` startet dieselbe Oberfläche mit simuliertem Roboter. Dabei wird kein COM-Port geöffnet.
Zum Beenden das Terminal mit Strg+C stoppen.

Alternativ:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
# oder: app.py --demo --no-browser --port 8766
```

## Bedienung

1. USB-Port wählen (am getesteten Gerät COM4) und verbinden; 115200 Baud, Firmwareprüfung.
2. Wagen bei freiem Fahrweg mit 1/5/10-mm-Schritten zum oberen linken Papierrand positionieren.
   +X = rechts, +Y = unten. Jog bewegt mit Stift oben und verwirft einen vorherigen Startpunkt.
3. **Hier ist oben links · 0 / 0** setzt G92 X0 Y0 und hebt den Stift.
4. Stift mit **S905** absenken. Kontakt beobachten, dann **Papierkontakt bestätigen & anheben**.
5. Text, Papier, Stil, Größe und Rand wählen; Vorschau erstellen.
6. Anwesenheit und freien Bereich bestätigen. Trockenlauf ausführen.
7. Tatsächliche freie Fahrt und Rückkehr bestätigen. **Auf Papier schreiben**.

Die Freigabe gilt nur für den exakt erzeugten Auftrag; Änderungen erfordern einen neuen Trockenlauf.
Verbindung wird während einer Sitzung gehalten. Nach Reset/Fehler/Abbruch neu verbinden und Startpunkt setzen.
Alle Jobs enden mit Stift oben und Rückfahrt zum Start. Der Server wartet auf echtes Idle,
bevor er einen Vorgang als fertig meldet.

## Enthalten

- Deutsche responsive Oberfläche ohne CDN, Schrift- oder Netzwerkdienste
- COM-Port-Auswahl, Firmwareprüfung, Arbeitsposition nach abgeschlossenen Vorgängen
- Stift hoch/runter, S0–1000; Standard S905
- A6 und A5, A4 quer, drei generierte Schriftstile, Umlaute
- SVG-Vorschau, überprüfte G-Code-Ausgabe, Download und gespeicherte Aufträge
- Ein laufender Vorgang, Fortschritt nach bestätigten Befehlen, Pause/Fortsetzen und Abbruch
- Demo-Modus und automatisierte Tests ohne Hardware

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
- `jobs/<id>/`: Text, SVG, G-Code und Auftragseinstellungen (nicht in Git)
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

Geschwindigkeit: 25–150 % des bisherigen, kurvenabhängigen Tempos. 100 % entspricht dem getesteten Ausgangstempo. Auch Leerfahrten und Trockenlauf werden angepasst; Servopausen bleiben unverändert. Eine Tempoänderung erzeugt einen neuen Auftrag und benötigt einen neuen Trockenlauf. Das Tempo wird vor dem Start eingestellt, nicht während einer Fahrt.
