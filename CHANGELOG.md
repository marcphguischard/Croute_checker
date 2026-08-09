# Changelog

Strukturierte, chronologische Übersicht der Entwicklungsschritte am Route Checker.
Jeder Eintrag: Datum, was gemacht wurde, warum.

## 2026-08-09 – Outbound-Meldepflichten, Fähren/LNG, GT-Ausnahme, Boulogne/Rye, UK MAREP

Basiert auf einer vollständigen Wort-für-Wort-Erfassung aller ADP-Texte der Dover-Strait-
Region (8 Gebiete + 3 reine Lotsen-Häfen). Marc hat daraus gezielt gefiltert, was ins Tool
kommt - nicht jede Einzelheit aus den ADP-Texten wurde übernommen (siehe "Bewusst nicht
umgesetzt" unten).

- **WICHTIGE KORREKTUR - Ramsgate-Zentrum**: Der bisherige Wert (51.32583) war ein
  Rechenfehler in der vorherigen Vorlage. Korrektes Mittel aus den beiden
  Leuchttonnen-Positionen (51°19.56'N + 51°19.46'N) / 2 = 51°19.51'N = **51.32517**.
  Korrigiert in `reporting_points.csv`.
- **Outbound-Meldepflichten (NEU)** (`main.py`, `reporting_points.csv`): Bisher wurde nur
  geprüft, ob ein Hafen (Dover, Ramsgate) tatsächlich Ziel der Route ist (`bedingt_inbound`,
  letzter Wegpunkt). Jetzt zusätzlich `bedingt_outbound`: prüft den **ersten** Wegpunkt der
  Route - greift nur, wenn die Route tatsächlich im Hafenkreis startet (auslaufendes
  Schiff), nicht bei reinem Durchtransit. Neue Gebiete "Dover VTS (Outbound)" und "Ramsgate
  (Outbound)" (gleicher Kreis/Radius wie die bestehenden Inbound-Gebiete, nur andere
  Pflicht_Typ-Prüfung).
- **Neue Schiffstypen**: "Ferry" und "LNG tanker" (LNG tanker zählt zu `TANKER_TYPEN`).
  Grund: Fähren haben bei Dover/Ramsgate abweichende Melde-Prozeduren (PEC-Nummer, Priority
  Slots, kürzere Vorlaufzeiten statt 1h), LNG-Tanker bei Dunkerque VTS eine eigene ETA-Kette
  und Sperrzonen-Regel.
- **Neue Interviewfragen**: "Restricted in ability to manoeuvre" und "Defective
  navigational aids" - bewusst OHNE "not under command" (auf Rückfrage: nicht planbar, tritt
  unerwartet ein, im Gegensatz zu eingeschränkter Manövrierfähigkeit die z.B. bei
  Schleppverbänden auch planmäßig vorliegen kann).
- **GT-Ausnahme-Logik** (`erfuellt_schiffskriterien()`): Neue CSV-Spalte
  `GT_Ausnahme_Bei_Einschraenkung`. Für CALDOVREP gesetzt: Schiffe <300GT melden trotzdem,
  wenn eingeschränkt manövrierfähig ODER Navigationshilfen defekt sind (ADP Abs. 2).
- **Zusatzinfos in der Ausgabe** (Konsole + `ergebnis.txt`), neue CSV-Spalten dafür:
  - `Meldeinhalt`: Pflichtfelder der Meldung (A/B/C/... wie im ADP-Text), jetzt für ALLE
    Gebiete befüllt und bei jedem Treffer angezeigt.
  - `Dauerpflicht`: Dauer-/Zusatzpflichten (Hörwache-Kanäle, Sonderfälle), ebenfalls für
    alle Gebiete befüllt und angezeigt. Bei SURNAV Gris-Nez steht hier u.a. die
    Unfallmeldepflicht für ALLE Schiffe ≥300GT unabhängig von Ladung (rein informativ, kein
    Trigger - siehe unten). Bei Dunkirk VTS die LNG-Sonderregeln.
  - `Faehre_Hinweis` / `LNG_Hinweis`: nur angezeigt, wenn Schiffstyp passend (Ferry bzw.
    LNG tanker) - bei Dover in/out (Fähre) und Dunkirk VTS (LNG).
  - Diese Felder wurden nur auf der jeweils ERSTEN Zeile jedes Gebiets befüllt (einzige
    Zeile, die `baue_gebiete()` tatsächlich liest), nicht auf jeder Punkte-Zeile wiederholt
    wie die kurzen Kriterien-Spalten - sonst wäre die CSV bei WETREP (24 Punkte) & Co.
    unnötig aufgebläht.
- **UK MAREP als pauschaler Hinweis** (kein geprüftes Gebiet, da keine eigenen Koordinaten
  im ADP-Text - verweist nur auf Gebiete außerhalb Dover Strait): wird am Ende der Ausgabe
  gezeigt, wenn GT ≥300, mit Hinweis auf Freiwilligkeit. Erwähnt MANCHEREP/OUESSREP als die
  verpflichtenden Pendants außerhalb des Dover-Strait-Fokus (auf Rückfrage: drin lassen,
  "gehört irgendwie dazu", aber ohne eigene Koordinaten nicht geometrisch prüfbar).
- **Neue Gebiete Boulogne und Rye** (`reporting_points.csv`), beide mit **approximiertem
  Melde-Radius**, da der ADP-Text keinen expliziten Kreis nennt (im Gegensatz zu Dover/
  Ramsgate mit klar benanntem Point Zulu/Romeo-Radius) - **klar als Annahme in der
  Info-Spalte gekennzeichnet**, keine ADP-Vorgabe:
  - Boulogne: 4sm-Lotsenpflicht-Gebiet als Näherung für den Melde-Radius übernommen.
    Ladungsabhängig (Kohlenwasserstoffe/Gefahrstoffe, analog SURNAV-Logik via
    `Tanker_Oder_Gefahrgut`).
  - Rye: 5sm (äußere Grenze des im Text genannten VHF-Kontaktbereichs "5-2sm") als
    Näherung, da die eigentliche Referenzposition ("No.2 red light tripod Bn") im Text
    keine Koordinate hat.
- **Point Echo (Dover)**: zeitbasiert (35min vom Hafeneingang), lässt sich nicht als eigene
  Geometrie abbilden - als Hinweis in Dover VTS' `Meldeinhalt` aufgenommen (v.a.
  Fähren-relevant), löst aber keinen eigenen geometrischen Trigger aus.
- **Bewusst nicht umgesetzt** (auf Rückfrage):
  - SURNAV-Unfallmeldepflicht (alle Schiffe ≥300GT, ereignisbasiert): nur als
    Dauerpflicht-Hinweistext, kein eigener Trigger - passt nicht ins
    Vorab-Routenprüfungs-Modell.
  - Dunkerque-Wartebereich (Ch72-Dauerwache) und die 0.5sm-Sperrzone um ankernde
    LNG-Schiffe: keine Koordinaten im ADP-Text vorhanden, daher nicht geometrisch
    prüfbar - nur als Hinweistext in Dunkirk VTS' `Dauerpflicht`/`LNG_Hinweis`.
  - CALDOVREP-Südgrenze (fehlender Küstenpunkt Frankreich): CSV unangetastet gelassen
    (auf Rückfrage: "zu Genüge geprüft").
  - Exemption Certificates (Ramsgate): rein informativer Meldeinhalt-Hinweis, keine
    Filterkriterien-Relevanz - nicht umgesetzt.
- **Getestet** (11 Szenarien, alle bestanden): Dover Inbound/Outbound/Transit (Transit löst
  korrekt weder in- noch outbound aus), Dover Outbound als Ferry (Fähren-Hinweis erscheint),
  Ramsgate Inbound/Outbound, LNG-Tanker durch Dunkirk VTS (LNG-Hinweis erscheint),
  CALDOVREP GT-Ausnahme (GT<300 ohne Ausnahmegrund = kein Trigger, mit eingeschränkter
  Manövrierfähigkeit ODER defekten Navigationshilfen = Trigger), Boulogne
  ladungsabhängig (Tanker = Trigger, General Cargo ohne Gefahrgut = kein Trigger), Rye
  Inbound, UK-MAREP-Hinweis erscheint nur bei GT≥300.
- **WIP-Historie**: Dieser Batch wurde zwischenzeitlich unfertig committet (Outbound-Logik
  fehlte noch, siehe Commit `423f95d`) und in einer Folgesession fertiggestellt - der
  Push nach GitHub war zum Zeitpunkt des Zwischen-Commits nicht möglich (keine
  Zugangsdaten im Tool-Environment hinterlegt, siehe Kommentar dort).

## 2026-08-08 (Teil 3) – Dover VTS, Ramsgate: Kreis-Gebiete mit Inbound-Bedingung

- **Neue Gebiete Dover VTS und Ramsgate** (`reporting_points.csv`): Beide sind keine
  Flächen/Linien wie bisher, sondern ein Melde-Kreis um einen Hafeneinfahrt-Mittelpunkt
  (Dover: 51.11750, 1.33567, Radius 3.0nm; Ramsgate/Point Romeo: 51.32583, 1.45483,
  Radius 2.5nm). Neue Spalte `Radius_NM` dafür ergänzt (0 = kein Kreis-Gebiet). Bei
  Ramsgate wurden nur die im Text gegebenen Dezimalgrad-Werte übernommen, keine
  Grad/Minuten zurückgerechnet, da im Quelltext nur das berechnete Dezimal-Zentrum
  angegeben war (keine eigene Schätzung).
- **WICHTIG - Breiten-Korrektur der Kreis-Geometrie** (`main.py`,
  `baue_kreis_geometrie()`): Der ADP-Text schlägt einen einfachen Grad-Buffer vor
  (radius_nm / 60). Das ist geometrisch **kein echter Kreis**: 1° Breite entspricht
  überall ~60nm, aber 1° Länge bei ~51°N nur ~60 · cos(51°) ≈ 38nm. Ein ungestreckter
  Grad-Buffer wäre also in Ost-West-Richtung zu eng (bei Dover z.B. nur ~1.9nm statt
  3nm) – ein Schiff, das exakt von Osten/Westen anläuft, könnte fälschlich als
  "außerhalb" gewertet werden. Behoben durch Streckung des Kreises in Längen-Richtung
  um den Faktor `1/cos(Breite)` (`shapely.affinity.scale`), sodass er in **allen**
  Richtungen ~radius_nm entspricht. Mit Testfall bestätigt: ein Punkt, der beim
  einfachen Grad-Buffer außerhalb läge (0.07° östlich vom Zentrum, naiver Radius nur
  0.05°), wird mit der Korrektur (effektiver Radius ~0.0797°) korrekt als "innerhalb"
  erkannt.
- **Automatische Zielhafen-Erkennung statt Nutzerabfrage** (`main.py`): Dover VTS und
  Ramsgate gelten laut ADP-Text nur "inward-bound", nicht bei reinem Durchtransit durch
  die Nähe. Neue Spalte `Pflicht_Typ = "bedingt_inbound"` markiert solche Gebiete. Für
  diese wird nicht mehr "kreuzt die Route das Gebiet?" geprüft, sondern nur "liegt der
  **letzte** Wegpunkt der Route (= angenommener Zielhafen) innerhalb des Kreises?" - bei
  reinem Durchtransit (Route führt geometrisch durch den Kreis, endet aber woanders)
  greift die Meldepflicht bewusst NICHT. Alle anderen Gebiete (CALDOVREP, Calais/Dunkirk
  VTS, SURNAV, WETREP) behalten die bisherige "jede Kreuzung löst aus"-Logik.
- **Ramsgate-Zusatzkriterium (>20m LOA ohne Lotsen an Bord) bewusst nicht in der Logik
  erzwungen**: Auf Rückfrage nur als Freitext in der Info-Spalte dokumentiert, da noch
  keine LOA-/Lotsen-Abfrage im Schiffsdaten-Interview existiert. Bei Bedarf später wie
  tdw/Schweröl-Ladung als eigene Interviewfrage + Kriterienspalte nachrüstbar.
- **Ramsgate-Kanal**: Im ADP-Text stand keine Kanalnummer bei den Meldezeitpunkten - auf
  Rückfrage ergänzt: Ch14 (Local Port Service), Ch68 als Notfall-Ausweichkanal (in der
  Info-Spalte dokumentiert).
- **Getestet**: (1) Route endet exakt im Dover-Zentrum → Dover VTS löst aus. (2) Route
  verläuft geometrisch mitten durch den Dover-Kreis, endet aber weit entfernt → korrekt
  KEINE Dover-Meldepflicht (reiner Durchtransit). (3) Route endet in Ramsgate → Ramsgate
  löst aus (Ch14). (4) Route endet an einem Punkt, der mit der unkorrigierten
  Grad-Näherung außerhalb des Dover-Kreises läge, mit der Breiten-Korrektur aber
  innerhalb → löst korrekt aus (bestätigt, dass die Korrektur einen echten Unterschied
  macht, nicht nur kosmetisch ist).

## 2026-08-08 (Teil 2) – Englische Programmausgabe & Mac-Start-Befehl

- **Programmausgabe auf Englisch umgestellt** (`main.py`): Alle Konsolentexte (Fragen,
  Zwischenüberschriften, Ergebnisliste) sowie `ergebnis.txt` sind jetzt auf Englisch.
  Ja/Nein-Antworten des Nutzers werden intern jetzt als "Yes"/"No" gespeichert und
  verglichen; die CSV-Kriterienspalten (`Gefahrgut_Pflicht`, `Nur_Tanker` usw.) bleiben
  unverändert auf "Ja"/"Nein"/"Egal", da sie nur intern gelesen werden. Schiffstypen-Liste
  ebenfalls übersetzt (z.B. "Stückgutfrachter" → "General cargo ship"); `TANKER_TYPEN`
  entsprechend angepasst.
- **Mac-Startbefehl behoben**: `Start.bat` und `Route Checker starten.lnk` sind reine
  Windows-Dateien (.bat braucht cmd.exe, .lnk ist ein Windows-Verknüpfungsformat) und
  funktionieren auf dem Mac nicht. Neue Datei `Start Route Checker.command` (ausführbar,
  Doppelklick im Finder startet sie über Terminal.app) legt bei Bedarf automatisch eine
  lokale virtuelle Umgebung (`.venv/`) an und installiert `pandas`/`shapely` dort – ein
  direktes `pip install` scheitert auf dem Mac an Homebrews "externally-managed-
  environment"-Schutz (PEP 668). `.gitignore` neu angelegt, damit `.venv/` nicht
  eingecheckt wird.
- **Getestet**: `Start Route Checker.command` einmal komplett durchlaufen lassen (inkl.
  automatischer Venv-Erstellung und Paketinstallation) – Schiffsdaten-Interview, Routenwahl
  und Ergebnisausgabe liefen fehlerfrei auf Englisch durch.

## 2026-08-08 – ADP-Datenbank-Update: CALDOVREP-Korrektur, SURNAV Gris-Nez, WETREP

- **CALDOVREP korrigiert** (`reporting_points.csv`): Die bisherigen Punkte 1/2 ("SW"/"SE")
  waren falsch und wurden durch die verifizierten Positionen "Southern Head Shoal"
  (50.72417, 0.43483) und "Bassurelle Lt buoy" (50.54667, 0.96333) ersetzt. Punkte 3/4
  (NE/NW) unverändert gelassen, da bereits korrekt. Gebietsname von "DS CALDOVREP SW" zu
  "DS CALDOVREP" bereinigt.
- **Neues Gebiet SURNAV Gris-Nez**: Zonengrenze zwischen zwei CROSS-Zuständigkeiten,
  keine Fläche sondern eine Linie (Cap d'Antifer → Greenwich Lt F). Meldepflicht nur für
  Tank-/Gefahrgutschiffe.
- **Neues Gebiet WETREP**: Riesiges Polygon mit 24 Punkten (a–x), deckt fast ganz
  Westeuropa/Ostatlantik ab. Meldepflicht nur für Öltanker >600 tdw mit Schweröl-,
  Schwerölkraftstoff- oder Bitumen/Teer-Ladung.
- **`main.py` erweitert, um beide neuen Gebiete korrekt zu prüfen**:
  - Gebiete mit genau 2 Punkten werden jetzt als `LineString` statt `Polygon` gebaut
    (bisher wurden nur Flächen ab 3 Punkten erkannt) – nötig für SURNAV Gris-Nez.
  - Neue Interviewfrage "Tragfähigkeit / Deadweight (tdw)" plus CSV-Spalte `Min_TDW`,
    da tdw nicht mit der bereits abgefragten Bruttoraumzahl (GT) gleichzusetzen ist –
    nötig für die 600-tdw-Schwelle von WETREP.
  - Neue Interviewfrage zu Schweröl-/Schwerölkraftstoff-/Bitumen-Ladung plus CSV-Spalte
    `Schweroel_Pflicht` – die bestehende Gefahrgut/IMDG-Frage deckt diese
    WETREP-spezifische Ladungsbedingung nicht ab.
  - Neue CSV-Spalte `Tanker_Oder_Gefahrgut`: SURNAV Gris-Nez gilt für Tankschiffe ODER
    Schiffe mit Gefahrgut an Bord (z.B. Containerschiffe mit IMDG-Ladung) – die bisherige
    Kriterienlogik konnte nur UND-Verknüpfungen abbilden.
  - Neue Info-Spalten `Pflicht_Typ` (verpflichtend/ladungsabhängig) und
    `Ladungsbedingung` (Freitext) für alle Gebiete ergänzt.
- **Nebenbei entdeckter und behobener Bug**: Bei "Dunkirk VTS" war die `Gebiet`-Spalte der
  ersten Zeile leer, wodurch dessen 19 Punkte beim Einlesen fälschlich an das vorherige
  Gebiet "Calais VTS (blau)" angehängt wurden – "Dunkirk VTS" existierte dadurch nie als
  eigenes prüfbares Gebiet. Jetzt korrigiert.
- **Getestet**: Route über den Ärmelkanal mit drei Schiffsprofilen durchgespielt –
  (1) Tanker mit Gefahrgut + Schweröl löst CALDOVREP, SURNAV Gris-Nez und WETREP aus,
  (2) Tanker ohne Gefahrgut/Schweröl löst CALDOVREP und SURNAV Gris-Nez aus, WETREP korrekt
  nicht (fehlende Ladungsbedingung), (3) Stückgutfrachter ohne Gefahrgut löst nur
  CALDOVREP aus, SURNAV Gris-Nez korrekt nicht.

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
