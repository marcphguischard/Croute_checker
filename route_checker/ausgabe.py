# Formatiert die von pruefung.pruefe_route() gelieferten Rohdaten zu
# lesbaren Texten - fuer die CLI-Konsolenausgabe, die ergebnis.txt-Datei und
# (Phase 2) die Web-Ergebnisseite/den Download-Button.
import pandas as pd

from .kategorien import CATEGORY_OF_SHIP_REPORT


# Formatiert Report_Types (Codes) als lesbare, kommagetrennte Liste von Bezeichnungen
def formatiere_report_typen(codes):
    return ", ".join(CATEGORY_OF_SHIP_REPORT.get(c, f"Report type {c}") for c in codes)


# Formatiert Notice_Time_Hours (z.B. [48, 12, 2]) + Notice_Time_Text zu einer Zeile,
# z.B. "Report required: 48h, 12h and 2h before arrival"
def formatiere_vorlaufzeit(stunden, text):
    teile = []
    if stunden:
        if len(stunden) == 1:
            zeit_teil = f"{stunden[0]:g}h before arrival"
        else:
            kopf, letzte = stunden[:-1], stunden[-1]
            zeit_teil = ", ".join(f"{s:g}h" for s in kopf) + f" and {letzte:g}h before arrival"
        teile.append(f"Report required: {zeit_teil}.")
    if text:
        teile.append(text)
    return " ".join(teile)


# Ordnet den Relationship_Type-Wert einer Statuszeile fuer die Ausgabe zu
# (aktuell sind alle geometrisch geprueften Gebiete "required" - die anderen Zweige
# sind fuer zukuenftige, als "recommended" o.ae. markierte Gebiete vorbereitet)
def relationship_status_label(relationship_type):
    if relationship_type in ("recommended", "permitted"):
        return "RECOMMENDED (voluntary system)"
    if relationship_type in ("not_required", "not_recommended", "prohibited"):
        return "NOTE (not required)"
    return "REPORTING REQUIRED"


# Formatiert den Frequenzwert (Zahl aus der CSV) als "Ch 13" o.ae. Faellt auf
# "see ADP" zurueck, wenn keine Frequenz hinterlegt ist (main.py-Verhalten,
# bewusst NICHT geaendert - siehe Rueckfrage/Antwort dazu).
def formatiere_frequenz(frequenz_wert):
    if pd.notna(frequenz_wert):
        return f"Ch {int(float(frequenz_wert))}"
    return "see ADP"


# Baut die "Checked for: ..."-Zusammenfassungszeile - von CLI-Konsolenausgabe
# UND erzeuge_textbericht() genutzt, um Doppelpflege zu vermeiden.
def formatiere_schiffszusammenfassung(Schiffsdaten):
    return (
        f"Checked for: {Schiffsdaten['schiffstyp']}, {Schiffsdaten['gt']:.0f} GT, "
        f"dangerous goods: {Schiffsdaten['gefahrgut']}, "
        f"international voyage: {Schiffsdaten['internationale_fahrt']}"
    )


# Baut die "Action:"-Zeile eines Eintrags. Kleinkorrektur 1.2.6: "to the
# responsible MRCC" ist fachlich nicht fuer alle Gebiete richtig (Hafen-VTS
# sind keine MRCC) - stattdessen nur "Report on {freq}", ergaenzt um
# "to {reporting_station}", falls die (optionale, aktuell in der CSV noch
# nicht vorhandene) Spalte Reporting_Station befuellt ist.
def formatiere_action_zeile(eintrag):
    if eintrag['reporting_station']:
        return f"Report on {eintrag['frequenz']} to {eintrag['reporting_station']}"
    return f"Report on {eintrag['frequenz']}"


# Baut den vollstaendigen Textbericht (wie main.py bisher in ergebnis.txt
# geschrieben hat) als String - wiederverwendbar fuer die CLI-Datei UND den
# Web-Download-Button (Phase 2).
def erzeuge_textbericht(Schiffsdaten, routen_name, wegpunkte, ergebnisse, jetzt, uk_marep_hinweis=None):
    zeilen = ["=== ROUTE CHECKER - REPORTING OBLIGATIONS ===", ""]
    zeilen.append(f"Created: {jetzt.strftime('%d.%m.%Y %H:%M')}")
    if routen_name:
        zeilen.append(f"Route: {routen_name}")
    zeilen.append(f"Waypoints checked: {len(wegpunkte)}")
    zeilen.append(formatiere_schiffszusammenfassung(Schiffsdaten))
    zeilen.append("")

    for e in ergebnisse:
        zeilen.append(f"{e['status_label']}: {e['gebiet']}")
        zeilen.append(f"Type:          {e['typ']}")
        zeilen.append(f"Frequency:     {e['frequenz']}")
        zeilen.append(f"Action:        {formatiere_action_zeile(e)}")
        if e['meldeinhalt']:
            zeilen.append(f"Report content: {e['meldeinhalt']}")
        if e['dauerpflicht']:
            zeilen.append(f"Continuous watch/duty: {e['dauerpflicht']}")
        if e['faehre_hinweis']:
            zeilen.append(f"Ferry note:    {e['faehre_hinweis']}")
        if e['lng_hinweis']:
            zeilen.append(f"LNG note:      {e['lng_hinweis']}")
        if e['report_typen_text']:
            zeilen.append(f"Report type(s): {e['report_typen_text']}")
        if e['vorlaufzeit_text']:
            zeilen.append(f"Notice:        {e['vorlaufzeit_text']}")
        if e['source_reference']:
            zeilen.append(f"Source:        {e['source_reference']}")
        zeilen.append("")

    if uk_marep_hinweis is not None:
        zeilen.append(uk_marep_hinweis['titel'])
        zeilen.append(uk_marep_hinweis['text'])
        zeilen.append("")

    return "\n".join(zeilen) + "\n"
