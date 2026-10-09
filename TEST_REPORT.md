# MVP-Abnahme — 09.10.2026

- 12 automatisierte Tests bestanden (unittest, isolierte Python-Umgebung).
- JavaScript-Syntax mit node --check geprüft.
- Browserprüfung im Simulationsmodus: Verbindung, Startpunkt, S905-Kalibrierung,
  A6-Vorschau, Trockenlauf, Freigabe und Schreibauftrag vollständig durchlaufen.
- Beide Aufträge enden im Simulator bei Arbeitsposition 0/0 und Stift oben.
- Browser-Konsole ohne Fehler oder Warnungen.
- Responsive Darstellung bei schmalem Standardfenster und Desktop-Breakpoint geprüft.
- Endgültiger Projektpfad: C:\Users\malte\PhpstormProjects\VGX4-Control
- Separates Git-Repository, MST unverändert.
- Lokale Echtbetriebsoberfläche gestartet; COM4 wird aufgelistet, aber nicht geöffnet.
- Hardwaresteuerung des neuen MVP ist noch nicht am Gerät abgenommen.
  Die vorherigen direkten PowerShell-Schreibtests bei S905 waren erfolgreich.

## Erweiterung: Dokumentvorschau und Geschwindigkeit
- 14 Tests bestanden: gerundete Schreibpfade stimmen mit SVG exakt ueberein.
- Geschwindigkeit 25-150 Prozent, identische Geometrie; Schreib- und Trockenlauf-Feeds stimmen ueberein.
- Automatische Vorschau bei Seitenstart und nach Aenderungen; Browserpruefung bei 50 Prozent.
- Keine Hardwarebewegung bei Entwicklung und Tests.

## Erweiterung: Stiftlatenz und Fahrwegansicht

18 Tests bestanden. Neue serielle Simulationstests prüfen wiederverwendete WCO-Meldungen, kurze Idle-Abfrage ohne Koordinaten und gemeldete Position statt geplantem Ziel. G92 verwirft den alten Offset. Browserprüfung im Simulator: Stift hoch lässt den Editor aktiv; Positionspunkt bei 0/0 sichtbar. Reale Website zeigt schaltbare Leerfahrten und Randrahmen. USB wurde für den Serverneustart im Idle getrennt; keine Bewegungsbefehle am Gerät ausgeführt.


## Optionaler Trockenlauf und Live-Tempo
20 automatisierte Tests bestanden; JavaScript-Syntax und git diff --check fehlerfrei. Geprüft: direktes Schreiben mit bestätigtem bekannten Papierkontakt ohne Trockenlauf, unveränderte Rückfahrt im G-Code bei ausgeblendeter letzter roter Verbindung, Echtzeit-Overridebytes und Tempoänderung während eines simulierten Auftrags. Lokale Website neu geladen: Kontaktbestätigung, Startbedingung und Live-Regler vorhanden. Echtzeit-Tempo am physischen Vigo-Controller noch nicht geprüft.

## Überarbeitung Oberfläche und Bedienung

23 automatisierte Tests bestanden; JavaScript-Syntax mit node --check geprüft. Neu geprüft: Aufträge werden erst beim Start gespeichert, typografische Zeichen werden ersetzt, deutsche Fehlermeldungen mit Feldnamen, Zeitschätzung aus Vorschub und Servopausen, Ergebnis des letzten Laufs. Browserprüfung im Simulator (Desktop 1440 × 900, Handy 375 px, hell und dunkel): Verbinden, Startpunkt, Stift absenken/bestätigen, Checkliste, Schreiben, Trockenlauf, Pause/Fortsetzen und Abbruch über die feste Laufleiste, Fehleranzeigen für ungültige Eingaben und zu langen Text. Kein horizontales Scrollen auf Handybreite. Keine Hardwarebewegung.

## Umbruch, Simulation, Stiftwechsel und Tempo

27 automatisierte Tests bestanden. Zeilenumbruch nach gemessener Glyphenbreite statt Zeichenzahl (längste Zeile füllt mindestens 85 % der Breite, nie über den rechten Rand). Server startet immer live; Simulation nur über „Ohne Roboter testen“ oder `--demo`. Berührende Striche werden ohne Stiftwechsel gezeichnet (Beispielgedicht 109 → 77 Stiftwechsel, Brieftext 136 → 85), in allen Stilen und Größen; i-Punkte und Kreuzungen bleiben getrennt. Stiftpause einstellbar (Standard 300 ms statt 450 ms), Tempo bis 300 % bei Vorschubgrenze 2200 mm/min. Geschätzte Dauer Beispielgedicht A6: vorher 2:16 min (150 %), jetzt 1:29 min (150 %, 300 ms) bzw. 0:56 min (300 %, 150 ms). Stiftpause unter 450 ms und Tempo über 150 % sind am Gerät noch nicht geprüft.

## Gerätelimits

Mit `$$` am VG-X4 ausgelesen (nur lesend, keine Bewegung): `$110`/`$111` = 5000 mm/min, `$120`/`$121` = 400 mm/s², `$11` = 0,1 mm, `$32` = 0 (kein Lasermodus, Stiftwechsel stoppen die Bewegung). Vorschubgrenze von 2200 auf 5000 mm/min angehoben, Profilbeschleunigung oberhalb 100 % bis 400 mm/s². G-Code bis 100 % bitgenau unverändert. Beispielgedicht A6 bei 300 % und 200 ms: 1:04 → 0:53 min geschätzt. 28 Tests bestanden. Tempo über 150 % am Gerät noch nicht geprüft.
