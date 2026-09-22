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
