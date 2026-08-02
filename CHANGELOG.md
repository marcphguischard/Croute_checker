# Changelog

Strukturierte, chronologische Übersicht der Entwicklungsschritte am Route Checker.
Jeder Eintrag: Datum, was gemacht wurde, warum.

## 2026-08-02

- **RTZ-Routenimport eingebaut** (`main.py`): Bisher wurden Wegpunkte manuell über die
  Konsole eingegeben. Jetzt liest das Skript `.rtz`-Dateien (Standardformat für
  Schiffsrouten, CIRM RTZ 1.1) direkt aus dem `routes/`-Ordner ein und parst die
  Wegpunkt-Koordinaten (Lat/Lon in Dezimalgrad) daraus.
- **Routenauswahl-Menü**: Beim Start werden alle `.rtz`-Dateien in `routes/` automatisch
  aufgelistet und durchnummeriert; Eingabe `0` fällt zurück auf die alte manuelle Eingabe.
- **Erste importierte Route**: `FRDKK PS - Maas PS.rtz` (8 Wegpunkte, Dünkirchen → Maas-Ansteuerung).
  Danach zwölf weitere Routen im `routes/`-Ordner ergänzt.
- **`Start.bat` angelegt**: Startet das Skript per Doppelklick, ohne dass man
  `python main.py` manuell im Terminal eingeben muss.
- **BOM-Fix bei der Eingabe**: Auswahl-Eingabe wird jetzt von einem unsichtbaren
  BOM-Zeichen bereinigt (war beim Testen über PowerShell-Pipe aufgefallen).
- **`Route Checker starten.lnk` als Workaround**: Auf diesem Rechner ist die
  Dateizuordnung für `.bat`-Dateien so eingestellt, dass Doppelklick den Quelltext statt
  ihn auszuführen öffnet. Die Verknüpfung ruft `cmd.exe /c Start.bat` direkt auf und
  umgeht damit die kaputte Zuordnung. (Dauerhafter Fix: Rechtsklick → Öffnen mit →
  Eingabeaufforderung → „Immer diese App verwenden".)
- **Diese Datei (`CHANGELOG.md`) eingerichtet**: Ziel ist eine für Menschen lesbare,
  datierte Übersicht über alle Schritte – ergänzend zur Git-Historie, deren automatische
  Checkpoint-Commits generische Nachrichten haben und daher allein nicht aussagekräftig sind.
