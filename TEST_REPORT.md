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
