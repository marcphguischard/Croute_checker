# Changelog

Strukturierte, chronologische Übersicht der Entwicklungsschritte am Route Checker.
Jeder Eintrag: Datum, was gemacht wurde, warum.

## 2026-09-05 (Teil 3) – Gefahrgut-Frage von Ladungstyp entkoppelt

Marc hat einen echten Logikfehler aus der letzten Session gefunden: "Gefahrgut an Bord"
wurde aus dem Ladungstyp (`categoryOfCargo`) abgeleitet ("dangerous or hazardous" = Ja,
alles andere = Nein). Das ist falsch - ein Schiff kann z.B. Bulk-Ladung UND zusätzlich
Gefahrgut an Bord haben (die Ladungstyp-Kategorien schließen sich nicht gegenseitig mit
"führt Gefahrgut" aus).

- **Gefahrgut-Frage wieder eine eigene, unabhängige Ja/Nein-Frage** (`frage_schiffsdaten()`),
  wie vor der S-127-Umstellung - nicht mehr aus dem Ladungstyp abgeleitet. IMDG-Klasse(n)
  werden weiterhin nur bei "Gefahrgut = Ja" abgefragt, jetzt aber unabhängig davon, was bei
  Ladungstyp gewählt wurde.
- Ladungstyp (`categoryOfCargo`, 9 Werte) bleibt als separate Frage bestehen - beschreibt
  weiterhin die Hauptladung, hat aber keinen Einfluss mehr auf die Gefahrgut-Logik.
- Ungenutzte Konstante `DANGEROUS_CARGO_CODE` entfernt.
- **Getestet**: Bulk carrier mit Ladungstyp "Bulk" UND Gefahrgut=Ja löst SURNAV jetzt
  korrekt aus (über die bestehende Tanker-oder-Gefahrgut-Bedingung); dieselbe Route mit
  Gefahrgut=Nein löst SURNAV korrekt nicht aus. Vor dem Fix wäre der erste Fall
  fälschlich nicht ausgelöst worden, weil Ladungstyp≠"dangerous or hazardous" automatisch
  Gefahrgut=Nein erzwungen hätte.

## 2026-09-05 (Teil 2) – Alle 11 Diskrepanzen aus dem ADP-Rohtext-Abgleich behoben

Marc hat nach kurzer Rückfrage zu zwei echten Logikfragen (Details unten) grünes Licht
für alle 11 gefundenen Diskrepanzen gegeben (siehe Eintrag "2026-08-30" für die
ursprüngliche Liste).

- **#1 CALDOVREP GT-Ausnahme ergänzt**: Neue Interviewfrage "At anchor within the Dover
  Strait TSS or its Inshore Traffic Zones (ITZs)" als dritter Ausnahmegrund (neben
  eingeschränkter Manövrierfähigkeit/defekten Navigationshilfen). "Not under command"
  bleibt bewusst ausgeklammert (nicht planbar, siehe Code-Kommentar). Mit Testfall
  bestätigt: GT<300 + "at anchor in TSS" = Ja löst CALDOVREP jetzt korrekt aus,
  ohne diese Ausnahme weiterhin nicht.
- **#2 CALDOVREP-Kanal jetzt richtungsabhängig** (`bestimme_richtung()`, neue CSV-Spalte
  `Frequenz_SW_Bound`): Berechnet die echten Ein-/Austrittspunkte der Route mit dem
  CALDOVREP-Gebiet (nicht nur ersten/letzten Wegpunkt der Gesamtroute, da davor/danach
  beliebig viel Route liegen kann) und vergleicht deren Reihenfolge *entlang der Route*
  (`LineString.project()`) statt sich auf die von Shapely bei `intersection()`
  zurückgegebene Teile-Reihenfolge zu verlassen, die die Fahrtrichtung nicht
  zuverlässig widerspiegelt. Nordostgehend -> Ch13 (Gris-Nez Traffic), südwestgehend ->
  Ch11 (Channel VTS). Mit Testfall in beide Richtungen bestätigt (identische Route,
  Wegpunkte vertauscht).
- **#5 CALDOVREP/SURNAV 5h-vs-6h nicht "aufgelöst", sondern als das dargestellt, was es
  ist**: Marcs fachliche Einordnung: es handelt sich nicht um einen Widerspruch,
  sondern um **zwei unabhängige, gleichrangige Meldepflichten** (CALDOVREP-eigene
  MRCC-Meldung mit 5h/6h, SEPARAT von der allgemeinen SURNAV-Meldung mit 6h/6h - auch
  wenn beide ggf. beim selben MRCC ankommen). CALDOVREP-Text entsprechend präzisiert,
  keine Zahl "korrigiert" oder verworfen, stattdessen expliziter Hinweis, dass es sich
  um eine separate, parallel geltende Pflicht handelt.
- **#3 Boulogne-Copy-Paste-Fehler behoben**: Der fälschlich aus dem CALAIS-Dokument
  übernommene Satz (Meridian-Regel bei Calais Approche Lt buoy, gilt dort gar nicht)
  ersetzt durch die tatsächliche Boulogne-Pflicht ("vessels carrying
  hydrocarbons/dangerous substances must contact Boulogne Port before entering the
  approach channel..."). Mit Testfall bestätigt.
- **#4 SURNAV-Meldezeitpunkt**: war durch die S-127-`Notice_Time`-Spalten aus der
  vorherigen Session bereits abgedeckt (6h/6h erscheint jetzt in der "Notice:"-Zeile) -
  keine weitere Änderung nötig, nur verifiziert.
- **#6 Dunkirk VTS 12h-ETA-Schritt ergänzt** (Meldeinhalt + Notice_Time_Hours
  "48,2" -> "48,12,2").
- **#7 Dover VTS 2h-Pilot-Ordering-Meldung ergänzt** (Meldeinhalt + Notice_Time_Hours
  "1" -> "2,1"), zusätzlich zur bereits vorhandenen 1h-VTS-Meldung.
- **#8 Dover VTS Pilotage Incident Report ergänzt** (Dauerpflicht) - Unfall-/Beinahe-
  Unfall-Meldepflicht analog zu SURNAV/CALDOVREP.
- **#9 Calais VTS SURNAV-Zusatzwache ergänzt** (Dauerpflicht: Ch13 Gris-Nez während
  Transit Pas-de-Calais-TSS -> Calais-VTS-Gebiet) - war bei Dunkirk VTS bereits korrekt
  vorhanden, bei Calais VTS gefehlt.
- **#10 Dunkirk VTS richtungsabhängige Zuständigkeit ergänzt** (Dauerpflicht: DW10/DW24
  Lt buoy - Koordinaten nicht im Text, daher nur als Hinweistext, nicht geometrisch
  geprüft).
- **#11 Dunkirk VTS Wartebereich-Meldezeitpunkte ergänzt** (Dauerpflicht: 2h/1h vor ETA
  am Lotsenversetzpunkt).
- **Getestet**: 8 gezielte Szenarien - CALDOVREP GT-Ausnahme (positiv+negativ), CALDOVREP
  Richtung (NE+SW), Calais VTS, Dunkirk VTS, Boulogne, Dover VTS Inbound - alle
  Textergänzungen und die neue Richtungslogik bestätigt korrekt.

## 2026-09-04/05 – Schiffsprofil & Datenstruktur an IHO S-127 angelehnt

Umsetzung von `s127_implementierung_prompt.txt` (Marcs Vorgabe, Werte 1:1 aus
`s127_kategorien_uebersicht.md` / IHO S-127 Marine Traffic Management, Edition 1.0.0).
Ziel laut Vorgabe: **keine vollständige S-127-Implementierung**, nur die dort markierten
Kategorien als standardisierte Auswahllisten/Spalten übernehmen. Bestehende Funktionalität
(RTZ/GPX-Import, Geometrieprüfung, Zielhafen-Erkennung) blieb wie gefordert unangetastet
und wurde nach der Umstellung erneut getestet.

- **Schiffsdaten-Interview umgestellt** (`main.py`, `frage_schiffsdaten()`):
  - Schiffstyp: 17 standardisierte S-127-`categoryOfVessel`-Werte statt Freitext/eigener
    Liste, **plus zwei Tool-Erweiterungen** (Code 18 "Ferry", 19 "LNG tanker") – S-127
    selbst erlaubt das ("S100_Codelist, erweiterbar"). Ohne diese Erweiterung wären die
    bereits bestehenden Fähren-/LNG-Sonderhinweise (Dover, Ramsgate, Dunkirk VTS) nicht
    mehr abbildbar gewesen, da die offizielle Liste weder "Ferry" noch "LNG tanker" als
    eigenen Typ kennt.
  - Ladungstyp (`categoryOfCargo`, 9 Werte) ersetzt die bisherige separate
    Ja/Nein-Frage zu Gefahrgut – "Gefahrgut an Bord" ergibt sich jetzt automatisch aus
    der Auswahl "dangerous or hazardous".
  - IMDG-Klasse(n) (`categoryOfDangerousOrHazardousCargo`, 21 Werte, Mehrfachauswahl
    kommagetrennt) ersetzt die bisherige IMDG-Freitextabfrage – wird nur gefragt, wenn
    Ladungstyp = "dangerous or hazardous".
  - Neue Zahlenfelder: Length overall (LOA) und Tiefgang in Metern (bislang nicht
    abgefragt, jetzt für die neue Ramsgate-Schwelle gebraucht, siehe unten).
  - Neue Ja/Nein-/Auswahlfelder: Registrierung (domestic/foreign), Ballast-Status,
    Regierungsschiff-Status (Kriegsschiff/Marinehilfsschiff/sonstiges Regierungsschiff im
    nicht-kommerziellen Dienst – für die WETREP-Ausnahme, siehe unten).
- **Generische Schwellenwert-Prüfung** (`erfuellt_schwellenwert()`) ersetzt die bisherigen
  fest verdrahteten `GT < Min_GT` / `TDW < Min_TDW`-Vergleiche durch eine datengetriebene
  Prüfung (`Threshold_Characteristic` + `Threshold_Operator` + `Threshold_Value` je
  Gebiet, S-127 `comparisonOperator`). Die bestehende CALDOVREP-Ausnahme (GT<300 löst
  trotzdem aus bei eingeschränkter Manövrierfähigkeit/defekten Navigationshilfen) bleibt
  als Spezialfall erhalten, da sie sich nicht sauber als reiner Schwellenwert abbilden
  lässt.
- **Echte neue Fähigkeit dadurch**: Ramsgate hatte bisher **gar keine** Größen-Schwelle
  (jedes Boot löste es geometrisch aus). Der ADP-Text nennt aber ">20m LOA" für die
  nicht-lotsenpflichtige Meldekategorie – jetzt als `length_overall > 20m`
  abgebildet (für Ramsgate Inbound UND Outbound). **Verhaltensänderung**, mit Testfällen
  bestätigt: Boot mit LOA 15m löst Ramsgate nicht mehr aus, LOA 25m löst weiterhin aus.
- **Regierungsschiff-Ausnahme generalisiert** (`Government_Vessel_Exempt`-Spalte, S-127
  `categoryOfRelationship`-Gedanke): WETREP nimmt laut ADP-Text nicht nur Kriegsschiffe,
  sondern *jedes* Regierungsschiff im nicht-kommerziellen Dienst aus – bisher gar nicht
  abgebildet. Mit Testfall bestätigt: Kriegsschiff mit Schweröl-Ladung löst WETREP jetzt
  korrekt nicht mehr aus (CALDOVREP/Dover VTS lösen weiterhin normal aus).
- **CSV um 16 neue Spalten erweitert** (`reporting_points.csv`, für alle 11 Gebiete
  befüllt): `Threshold_Characteristic/Operator/Value/Unit`, `Applicable_Vessel_Types`,
  `Excluded_Vessel_Types`, `Government_Vessel_Exempt`, `Requires_Cargo_Type`,
  `Requires_IMDG` (ersetzt `Gefahrgut_Pflicht` als Wahrheitsquelle – alte Spalte bleibt
  zur Referenz stehen, wird aber nicht mehr gelesen), `Report_Types`,
  `Notice_Time_Hours`/`Notice_Time_Text`, `Relationship_Type`, `Traffic_Flow`,
  `Source_Type`/`Source_Reference`. Werte-Zuordnung pro Gebiet (z.B. welche
  Meldungstypen/Vorlaufzeiten) basiert auf den bereits erfassten ADP-Inhalten, an ein
  paar Stellen mit eigener, im Zweifel konservativer Einordnung (z.B. VTS-Meldungen als
  generisches "Other Report", da S-127 keinen eigenen Code dafür hat) - im Code
  dokumentiert.
- **Ausgabe erweitert** (Konsole + `ergebnis.txt`): pro Treffer zusätzlich Report-Typ(en)
  ausgeschrieben, Vorlaufzeit(en) als Satz ("Report required: 48h, 12h and 2h before
  arrival"), Quellenangabe (`Source: ADP/ALRS Vol 6, ...`). Status-Zeile
  ("REPORTING REQUIRED"/zukünftig auch "RECOMMENDED") jetzt aus `Relationship_Type`
  abgeleitet statt hart codiert - aktuell bei allen aktiven Gebieten weiterhin
  "REPORTING REQUIRED" (keine sichtbare Änderung), aber vorbereitet für später als
  "recommended" markierte Gebiete.
- **Nebenbei behobener Bug**: `parse_int_menge()` musste Zahlen über `float()` statt
  direkt `int()` parsen - pandas liest eine CSV-Spalte, die (fast) nur eine einzelne Zahl
  ohne Komma enthält (hier: `Excluded_Vessel_Types`, nur "10" bei WETREP), als
  Float-Spalte ein ("10.0" statt "10"), was beim direkten `int()`-Parsen abstürzte.
- **Getestet**: 4 Szenarien - (1) Tanker mit Gefahrgut+HFO bis Dover-Kreis
  (CALDOVREP→WETREP→Dover VTS, alle neuen Ausgabefelder korrekt), (2) kleines Boot
  (LOA 15m) zu Ramsgate ohne Treffer, (3) gleiche Route mit LOA 25m mit Ramsgate-Treffer,
  (4) Kriegsschiff mit HFO-Ladung ohne WETREP-Treffer (Regierungsschiff-Ausnahme).
- **Bewusst NICHT umgesetzt** (Scope-Grenze laut Vorgabe): volles S-127-Schema/GML/Feature
  Catalogue, `logicalConnectives` als generisches UND/ODER (die bestehende
  `Tanker_Oder_Gefahrgut`-Spalte deckt den einzigen aktuell vorkommenden ODER-Fall bereits
  ab), `Traffic_Flow` fließt bewusst nicht in die Trigger-Logik ein (rein dokumentarisch -
  die tatsächliche Inbound/Outbound-Erkennung läuft weiterhin über `Pflicht_Typ`).
- Die konkreten Werte in den neuen Spalten sind eine erste, plausible Befüllung aus den
  bereits vorliegenden ADP-Daten - Marc prüft/ergänzt bei Bedarf (analog zu den
  Platzhaltern bei der ersten CSV-Erweiterung).

## 2026-08-30 – ADP-Rohtext-Abgleich (Cross-Check gegen Primärquellen)

Marc hat die vollständigen Original-ADP-PDFs (11 Dokumente: Boulogne, Calais, CALDOVREP,
Dover, Dunkirk, Folkestone, Ramsgate, Rye, SURNAV, UK MAREP, WETREP) zur Verfügung
gestellt, um zu prüfen, ob bei der ursprünglichen Erfassung aus einer gekürzten Vorlage
Nuancen verloren gegangen sind. Reine Analyse, **keine Code-/CSV-Änderung** in dieser
Session (auf Marcs ausdrücklichen Wunsch: "nicht eigenständig etwas vom Skript ändern").

- **Bestätigt korrekt** (punktgenau gegen Originalkoordinaten geprüft): Calais VTS
  (9 Punkte), Dunkirk VTS (19 Punkte), Ramsgate/Point Romeo (Mittelpunkt-Berechnung),
  SURNAV-Gris-Nez-Grenzlinie, Boulogne-Radius (4sm ist im Volltext tatsächlich explizit
  genannt, war keine reine Annahme). Folkestone korrekt nicht erfasst (keine Meldepflicht
  im Quelltext).
- **Gefundene Diskrepanzen** (der Vollständigkeit halber hier festgehalten, Marc hat noch
  nicht entschieden, was davon übernommen wird):
  1. CALDOVREP GT-Ausnahme unvollständig: "at anchor in the TSS/ITZs" als dritte
     Ausnahme-Bedingung fehlt (nur eingeschränkte Manövrierfähigkeit/defekte
     Navigationshilfen sind abgebildet).
  2. CALDOVREP-Kanal ist richtungsabhängig (Ch13 NE-bound / Ch11 SW-bound), Tool zeigt
     bisher immer Ch13.
  3. Boulogne `Dauerpflicht` enthält fälschlich einen Satz aus dem CALAIS-Dokument
     (Meridian-Regel bei Calais Approche Lt buoy) - Copy-Paste-Fehler bei der
     ursprünglichen Erfassung.
  4. SURNAV: Meldezeitpunkt (6h vorher) fehlt komplett in der Ausgabe.
  5. CALDOVREP nennt für die MRCC-Meldung 5h/6h, SURNAV nennt 6h/6h - Widerspruch im
     Quellmaterial selbst, ungeklärt.
  6. Dunkirk VTS: 12h-ETA-Meldeschritt fehlt (springt von 48h direkt auf 2h).
  7. Dover VTS: separate 2h-"Pilot ordering"-Meldung (zusätzlich zur 1h-VTS-Meldung) fehlt.
  8. Dover VTS: Pilotage Incident Report (Unfallmeldepflicht) nicht abgebildet.
  9. Calais VTS: SURNAV-Zusatzwache (Ch13 Gris-Nez) fehlt (bei Dunkirk VTS korrekt vorhanden).
  10. Dunkirk VTS: richtungsabhängige Zuständigkeit (DW10/DW24 Lt buoy) nicht abgebildet.
  11. Dunkirk VTS: Wartebereich-Meldezeitpunkte (2h/1h vor ETA) nicht abgebildet.
- **Nebenfund**: separates Extraktions-Paket von Prof. Denker (`source_manifest.json`)
  bestätigt dieselbe CALDOVREP-Süd-/Westgrenzen-Lücke und nennt einen konkreten neuen
  Anhaltspunkt dafür: "Royal Sovereign light tower" als möglicher fehlender Referenzpunkt
  für die französische Küste - noch nicht verifiziert/übernommen.

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

## 2026-08-11 (Teil 2) – GPX-Routenimport zusätzlich zu RTZ

- **`lade_gpx_route()`** (`main.py`): Neuer Parser für Standard-GPX-1.1-Dateien
  (`<rte><rtept lat="..." lon="..."/></rte>`), analog zum bestehenden RTZ-Parser. GPX hat
  anders als RTZ keinen Pflicht-Routennamen und keinen Pflicht-Namen pro Wegpunkt – falls
  `<name>` fehlt, wird ersatzweise der Dateiname bzw. "WP1", "WP2", ... verwendet.
- **Routenauswahl-Menü zeigt jetzt `.rtz`- UND `.gpx`-Dateien** aus `routes/` gemeinsam
  (alphabetisch sortiert), der passende Parser wird automatisch anhand der Dateiendung
  gewählt.
- **Getestet** mit `Testroute FRCER - FRDKK.gpx` (Marcs erste eigene Testroute, 10
  Wegpunkte ohne Namen im GPX → korrekt als WP1–WP10 angezeigt): löst CALDOVREP, Dunkirk
  VTS und SURNAV Gris-Nez korrekt aus.
- CSV/GML wurden bewusst nicht unterstützt – GPX ist strukturell am nächsten an RTZ
  (klare `lat`/`lon`-Attribute pro Punkt) und deutlich zuverlässiger zu parsen als KML
  (Koordinaten meist als ein einzelner Text-Blob ohne Wegpunktnamen) oder GML (viele
  uneinheitliche Schema-Varianten).

## 2026-08-11 – UK MAREP ausgeblendet, Output komplett auf Englisch

- **UK MAREP vorübergehend deaktiviert** (`main.py`, neuer Schalter `UK_MAREP_AKTIV = False`):
  Marc will das System stattdessen über eigene Gebiete mit echter Geometrie abbilden
  (analog zu SURNAV/WETREP), dafür fehlen aber noch ADP-Daten für die angrenzenden
  Gebiete (OUESSREP/MANCHEREP), die er voraussichtlich in ~2 Wochen bekommt. Code bleibt
  erhalten (nicht gelöscht), einfach `UK_MAREP_AKTIV = True` setzen, sobald die Daten da
  sind.
- **CSV-Ausgabespalten ins Englische übersetzt** (`reporting_points.csv`: `Meldeinhalt`,
  `Dauerpflicht`, `Faehre_Hinweis`, `LNG_Hinweis` – 25 Zellen über 11 Gebiete): Die
  Konsolen-/Interview-Eingabe läuft bereits auf Englisch, das Ergebnis (`ergebnis.txt`
  und Konsole) war aber noch auf Deutsch, weil es direkt aus diesen CSV-Spalten kommt.
  Jetzt einheitlich Englisch. Die `Info`- und `Ladungsbedingung`-Spalten bleiben bewusst
  Deutsch – die tauchen nie im Programm-Output auf, sondern sind reine Doku beim
  CSV-Pflegen, und lassen sich so leichter mit den deutschen ADP-Original-Quelltexten
  abgleichen.
- **Getestet**: Tanker mit Gefahrgut+Schweröl bis Dover-Kreis-Zentrum (CALDOVREP → WETREP
  → Dover VTS) – komplette Ausgabe jetzt durchgängig Englisch, kein UK-MAREP-Hinweis mehr
  am Ende.

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
