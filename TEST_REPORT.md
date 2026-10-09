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
