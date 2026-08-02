# Changelog

Strukturierte, chronologische Übersicht der Entwicklungsschritte am Route Checker.
Jeder Eintrag: Datum, was gemacht wurde, warum.

## 2026-08-02 (Teil 2) – Schiffsspezifische Filterung

- **Schiffsdaten-Abfrage am Programmstart** (`main.py`, `frage_schiffsdaten()`): Vor der
  Routenprüfung fragt das Programm interaktiv Schiffstyp, Bruttoraumzahl (GT),
  internationale Fahrt, Gefahrgut (+ IMDG-Klasse), Personenzahl und
  Tiefgang/Sondertransport ab. Ergebnis liegt im Dictionary `Schiffsdaten`.
- **CSV um Kriterien-Spalten erweitert** (`reporting_points.csv`): `Min_GT`,
  `Gefahrgut_Pflicht`, `Nur_Tanker`, `Nur_Internationale_Fahrt` – aktuell überall mit
  Platzhaltern (300 / Egal / Nein / Nein) befüllt, echte ADP-Werte werden manuell
  nachgetragen.
- **Filterlogik** (`erfuellt_schiffskriterien()`): Ein Gebiet erscheint nur noch in der
  Meldepflichten-Liste, wenn die Route es geometrisch kreuzt UND die Schiffsdaten zu den
  Kriterien des Gebiets passen (GT-Schwelle, Gefahrgutpflicht, Nur-Tanker, Nur-
  internationale-Fahrt).
- **Ausgabe erweitert**: Konsole und `ergebnis.txt` zeigen jetzt zuerst eine
  Schiffs-Zusammenfassung ("Geprüft für: Tanker, 4500 GT, ...") vor der Trefferliste.
- **Nebenbei entdeckter und behobener Bug**: Die "keine Meldepflichten"-Meldung stand im
  Originalcode fälschlich innerhalb der Prüfschleife (statt danach) und nutzte ein
  Emoji, das auf manchen Windows-Konsolen zu einem Absturz führte. Durch die neue
  Filterlogik tritt der Fall "keine Treffer" jetzt regelmäßiger auf, daher direkt mit
  behoben.
- **Getestet**: einmal mit GT über der Platzhalter-Schwelle (2 Treffer, wie vor der
  Änderung) und einmal mit GT darunter (0 Treffer, kein Absturz).

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
  datierte Übersicht über alle Schritte – ergänzend zur Git-Historie (manuelle Commits
  per `git add . / git commit / git push`, bisher mit generischen Nachrichten wie
  „Was wurde gemacht"). Ab jetzt schlägt Claude nach jedem Schritt eine passende
  Commit-Nachricht vor, die direkt für den manuellen Commit genutzt werden kann.
