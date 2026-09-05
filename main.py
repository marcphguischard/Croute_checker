import pandas as pd
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import scale
from datetime import datetime
from math import cos, radians
import xml.etree.ElementTree as ET
import glob
import os

# CSV einlesen
df = pd.read_csv("reporting_points.csv")

RTZ_NS = {"rtz": "http://www.cirm.org/RTZ/1/1"}

# RTZ-Routendatei einlesen und Wegpunkte extrahieren
def lade_rtz_route(pfad):
    baum = ET.parse(pfad)
    wurzel = baum.getroot()
    routen_name = wurzel.find("rtz:routeInfo", RTZ_NS).get("routeName")
    wegpunkte = []
    for wp in wurzel.find("rtz:waypoints", RTZ_NS).findall("rtz:waypoint", RTZ_NS):
        pos = wp.find("rtz:position", RTZ_NS)
        lat = float(pos.get("lat"))
        lon = float(pos.get("lon"))
        wegpunkte.append((lon, lat, wp.get("name")))
    return routen_name, wegpunkte

GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}

# GPX-Routendatei einlesen und Wegpunkte extrahieren.
# GPX kennt (anders als RTZ) keinen Pflicht-Routennamen und keinen Pflicht-Namen pro
# Wegpunkt - falls das <name>-Element fehlt, wird der Dateiname bzw. "WP1", "WP2", ...
# als Ersatz verwendet.
def lade_gpx_route(pfad):
    baum = ET.parse(pfad)
    wurzel = baum.getroot()
    route = wurzel.find("gpx:rte", GPX_NS)

    name_element = route.find("gpx:name", GPX_NS)
    if name_element is not None and name_element.text:
        routen_name = name_element.text
    else:
        routen_name = os.path.splitext(os.path.basename(pfad))[0]

    wegpunkte = []
    for i, wp in enumerate(route.findall("gpx:rtept", GPX_NS), start=1):
        lat = float(wp.get("lat"))
        lon = float(wp.get("lon"))
        name_element = wp.find("gpx:name", GPX_NS)
        name = name_element.text if name_element is not None and name_element.text else f"WP{i}"
        wegpunkte.append((lon, lat, name))
    return routen_name, wegpunkte

# Fragt eine Ja/Nein-Frage ab und gibt so lange erneut nach,
# bis "Ja" oder "Nein" eingegeben wurde. Gibt den Text "Ja" oder "Nein" zurück.
def frage_ja_nein(frage):
    while True:
        antwort = input(f"{frage} (Yes/No): ").strip().capitalize()
        if antwort in ("Yes", "No"):
            return antwort
        print("Please enter 'Yes' or 'No'.")

# Fragt eine Zahl ab und gibt so lange erneut nach, bis eine gültige Zahl eingegeben wurde.
# ist_ganzzahl=True verlangt eine ganze Zahl (z.B. für Personenanzahl), sonst sind Kommazahlen erlaubt (z.B. für GT).
def frage_zahl(frage, ist_ganzzahl=False):
    while True:
        eingabe = input(f"{frage}: ").strip()
        try:
            return int(eingabe) if ist_ganzzahl else float(eingabe)
        except ValueError:
            print("Please enter a number.")

# ============================================================
# S-127-Kategorien (IHO S-127 Marine Traffic Management, Edition 1.0.0)
# Werte 1:1 aus s127_kategorien_uebersicht.md übernommen. Codes 18/19 sind
# Tool-Erweiterungen über die Basisliste hinaus (S-127 erlaubt das explizit:
# "S100_Codelist, erweiterbar") - ohne sie könnten die bestehenden Fähren-/
# LNG-Sonderhinweise (Dover/Ramsgate/Dunkirk VTS) nicht mehr unterschieden
# werden, die es schon vor dieser Umstellung gab.
# ============================================================
CATEGORY_OF_VESSEL = {
    1: "General cargo vessel",
    2: "Container carrier",
    3: "Tanker",
    4: "Bulk carrier",
    5: "Passenger vessel",
    6: "Roll-on roll-off",
    7: "Refrigerated cargo vessel",
    8: "Fishing vessel",
    9: "Service",
    10: "Warship",
    11: "Towed or pushed composite unit",
    12: "Tug and tow",
    13: "Light recreational",
    14: "Semi-submersible offshore installation",
    15: "Jackup exploration or project installation",
    16: "Livestock carrier",
    17: "Sport fishing",
    18: "Ferry",       # Tool-Erweiterung (nicht in der offiziellen S-127-Basisliste)
    19: "LNG tanker",  # Tool-Erweiterung (nicht in der offiziellen S-127-Basisliste)
}

CATEGORY_OF_CARGO = {
    1: "Bulk",
    2: "Container",
    3: "General",
    4: "Liquid",
    5: "Passenger",
    6: "Livestock",
    7: "Dangerous or hazardous",
    8: "Heavy lift",
    9: "Ballast",
}
DANGEROUS_CARGO_CODE = 7

# categoryOfShipReport - Meldungstypen (fuer Report_Types-Spalte)
CATEGORY_OF_SHIP_REPORT = {
    1: "Sailing Plan",
    2: "Position Report",
    3: "Deviation Report",
    4: "Final Report",
    5: "Dangerous Goods Report",
    6: "Harmful Substances Report",
    7: "Marine Pollutants Report",
    8: "Other Report",
}

CATEGORY_OF_DANGEROUS_CARGO = {
    1: "Class 1 Div. 1.1", 2: "Class 1 Div. 1.2", 3: "Class 1 Div. 1.3",
    4: "Class 1 Div. 1.4", 5: "Class 1 Div. 1.5", 6: "Class 1 Div. 1.6",
    7: "Class 2 Div. 2.1", 8: "Class 2 Div. 2.2", 9: "Class 2 Div. 2.3",
    10: "Class 3", 11: "Class 4 Div. 4.1", 12: "Class 4 Div. 4.2",
    13: "Class 4 Div. 4.3", 14: "Class 5 Div. 5.1", 15: "Class 5 Div. 5.2",
    16: "Class 6 Div. 6.1", 17: "Class 6 Div. 6.2", 18: "Class 7",
    19: "Class 8", 20: "Class 9", 21: "Harmful Substances in packaged form",
}

# Fragt aus einer nummerierten Liste (Dictionary Code -> Text) einen einzelnen Code ab
def frage_auswahl_code(frage, optionen):
    print(f"{frage}:")
    for code in sorted(optionen):
        print(f"  {code}) {optionen[code]}")
    while True:
        auswahl = input("Selection (number): ").strip()
        if auswahl.isdigit() and int(auswahl) in optionen:
            return int(auswahl)
        print("Please enter a valid number.")

# Fragt aus einer nummerierten Liste mehrere, kommagetrennte Codes ab (z.B. IMDG-Klassen)
def frage_auswahl_codes_mehrfach(frage, optionen):
    print(f"{frage} (comma-separated if more than one):")
    for code in sorted(optionen):
        print(f"  {code}) {optionen[code]}")
    while True:
        eingabe = input("Selection (number(s)): ").strip()
        teile = [t.strip() for t in eingabe.split(",") if t.strip()]
        codes = []
        gueltig = bool(teile)
        for t in teile:
            if t.isdigit() and int(t) in optionen:
                codes.append(int(t))
            else:
                gueltig = False
                break
        if gueltig:
            return codes
        print("Please enter one or more valid numbers, separated by commas.")

# Schritt 1: Schiffsdaten interaktiv abfragen und als Dictionary zurückgeben
def frage_schiffsdaten():
    print("=== SHIP DATA ===")

    # 1. Schiffstyp (categoryOfVessel)
    schiffstyp_code = frage_auswahl_code("Ship type", CATEGORY_OF_VESSEL)
    schiffstyp = CATEGORY_OF_VESSEL[schiffstyp_code]

    # 2. Ladungstyp (categoryOfCargo)
    ladungstyp_code = frage_auswahl_code("Cargo type", CATEGORY_OF_CARGO)

    # 3. IMDG-Klasse(n) (categoryOfDangerousOrHazardousCargo) - nur bei Ladungstyp "dangerous or hazardous"
    imdg_codes = []
    if ladungstyp_code == DANGEROUS_CARGO_CODE:
        imdg_codes = frage_auswahl_codes_mehrfach("IMDG class(es)", CATEGORY_OF_DANGEROUS_CARGO)
    # "Gefahrgut an Bord" ergibt sich jetzt aus dem Ladungstyp statt einer eigenen Ja/Nein-Frage
    gefahrgut = "Yes" if ladungstyp_code == DANGEROUS_CARGO_CODE else "No"
    imdg_klasse = ", ".join(CATEGORY_OF_DANGEROUS_CARGO[c] for c in imdg_codes)

    # 4. Tonnage/Abmessungen (mehrere Werte - WETREP nutzt tdw statt GT, Ramsgate nutzt LOA)
    gt = frage_zahl("Gross tonnage (GT)")
    tdw = frage_zahl("Deadweight (tdw)")
    loa = frage_zahl("Length overall (LOA) in metres")
    tiefgang = frage_zahl("Draught in metres")

    # 4b. Schweröl/Schwerölkraftstoff/Bitumen-Ladung (relevant für WETREP; kein IMDG-Wert,
    #     daher weiterhin eigene Frage statt aus der Ladungstyp-Auswahl abgeleitet)
    schweroel_ladung = frage_ja_nein(
        "Heavy fuel oil cargo (density >900kg/m³ at 15°C), heavy fuel (density >900kg/m³ "
        "or viscosity >180mm²/s at 50°C), or bitumen/tar on board"
    )

    # 5. Registrierung (categoryOfVesselRegistry)
    registrierung_code = frage_auswahl_code("Vessel registry", {1: "Domestic", 2: "Foreign"})
    vessel_registry = "domestic" if registrierung_code == 1 else "foreign"

    # 6. Ballast-Status (inBallast)
    in_ballast = frage_ja_nein("Vessel in ballast")

    # 7. Regierungsschiff-Status (relevant für WETREP-Ausnahme: Kriegsschiffe/Marinehilfsschiffe/
    #    sonstige Regierungsschiffe im nicht-kommerziellen Dienst)
    regierungsschiff = frage_ja_nein("Warship / naval auxiliary / other government-owned vessel in non-commercial service")

    # Internationale Fahrt
    internationale_fahrt = frage_ja_nein("International voyage")

    # Anzahl Personen an Bord als ganze Zahl
    personen_an_bord = frage_zahl("Number of persons on board", ist_ganzzahl=True)

    # Tiefgang eingeschränkt / Sondertransport: Ja/Nein
    sondertransport = frage_ja_nein("Restricted draught / special transport")

    # Zustands-Ausnahmen, die die 300GT-Schwelle bei CALDOVREP aushebeln koennen (siehe
    # erfuellt_schiffskriterien()). "Not under command" wird bewusst NICHT gefragt, da das nicht
    # planbar ist (tritt unerwartet ein) - eingeschraenkte Manoevrierfaehigkeit kann dagegen auch
    # planmaessig vorliegen (z.B. Schleppverband, Baggerarbeiten).
    eingeschraenkt_manoevrierfaehig = frage_ja_nein("Restricted in ability to manoeuvre")
    defekte_navigationshilfen = frage_ja_nein("Defective navigational aids")

    Schiffsdaten = {
        "schiffstyp": schiffstyp,
        "category_of_vessel_code": schiffstyp_code,
        "category_of_cargo_code": ladungstyp_code,
        "category_of_cargo": CATEGORY_OF_CARGO[ladungstyp_code],
        "imdg_classes": imdg_codes,
        "gt": gt,
        "tdw": tdw,
        "loa": loa,
        "draught": tiefgang,
        "internationale_fahrt": internationale_fahrt,
        "gefahrgut": gefahrgut,
        "imdg_klasse": imdg_klasse,
        "schweroel_ladung": schweroel_ladung,
        "personen_an_bord": personen_an_bord,
        "sondertransport": sondertransport,
        "eingeschraenkt_manoevrierfaehig": eingeschraenkt_manoevrierfaehig,
        "defekte_navigationshilfen": defekte_navigationshilfen,
        "vessel_registry": vessel_registry,
        "in_ballast": in_ballast,
        "government_non_commercial": regierungsschiff,
    }
    print()
    return Schiffsdaten

# Schiffstypen, die als "Tanker" im Sinne von Nur_Tanker gelten
TANKER_TYPEN = {"Tanker", "LNG tanker"}

# UK MAREP vorübergehend ausgeblendet: soll eigentlich über eigene Gebiete (mit Geometrie)
# abgebildet werden statt als pauschaler Hinweis, dafür fehlen aber noch ADP-Daten für die
# angrenzenden Gebiete (OUESSREP/MANCHEREP) - werden voraussichtlich in ~2 Wochen nachgereicht.
# Wieder auf True stellen, sobald diese Gebiete eingepflegt sind.
UK_MAREP_AKTIV = False

# Baut eine Kreis-Geometrie mit echtem Radius in nautischen Meilen um (lon, lat) -
# z.B. fuer Dover VTS / Ramsgate (3nm- bzw. 2.5nm-Melde-Kreis um die Hafeneinfahrt).
#
# WICHTIG: Ein einfacher Grad-Buffer (buffer(radius_nm/60)) waere KEIN echter Kreis in
# nautischen Meilen, sondern in Ost-West-Richtung zu eng: 1 Grad Breite entspricht ueberall
# ~60nm, aber 1 Grad Laenge entspricht bei ~51 Grad Nord nur ~60*cos(51 Grad) = ~38nm. Ein
# Schiff, das genau von Osten/Westen auf den Hafen zulaeuft, koennte mit dem einfachen
# Buffer faelschlich als "ausserhalb" gewertet werden, obwohl es innerhalb der echten
# 3nm liegt. Deshalb wird der Kreis erst mit dem Breiten-Radius gebaut und dann in
# Laengen-Richtung um 1/cos(Breite) gestreckt, damit er in allen Richtungen ~radius_nm
# entspricht.
def baue_kreis_geometrie(lon, lat, radius_nm):
    mittelpunkt = Point(lon, lat)
    radius_grad = radius_nm / 60.0  # 1 Grad Breite ~= 60 nm
    kreis = mittelpunkt.buffer(radius_grad)
    korrekturfaktor = 1 / cos(radians(lat))
    return scale(kreis, xfact=korrekturfaktor, yfact=1.0, origin=mittelpunkt)

# ============================================================
# Generische S-127-Schwellenwert-Prüfung (ersetzt die vorherigen fest verdrahteten
# GT/TDW-Vergleiche). Ein Gebiet trägt EINE Schwellenwert-Bedingung
# (Threshold_Characteristic/Operator/Value/Unit); das reicht für alle bisherigen
# Gebiete, da nie mehr als eine Kenngröße gleichzeitig geprüft wird.
# ============================================================
THRESHOLD_SCHIFFSFELD = {
    "gross_tonnage": "gt",
    "deadweight_tonnage": "tdw",
    "length_overall": "loa",
    "draught": "draught",
}
THRESHOLD_VERGLEICH = {
    "greater_than": lambda a, b: a > b,
    "greater_than_or_equal": lambda a, b: a >= b,
    "less_than": lambda a, b: a < b,
    "less_than_or_equal": lambda a, b: a <= b,
    "equal_to": lambda a, b: a == b,
    "not_equal_to": lambda a, b: a != b,
}

def erfuellt_schwellenwert(daten, Schiffsdaten):
    merkmal = daten['schwellenwert_merkmal']
    if not merkmal or merkmal == "none":
        return True  # kein Schwellenwert fuer dieses Gebiet definiert

    schiffsfeld = THRESHOLD_SCHIFFSFELD.get(merkmal)
    vergleichsfunktion = THRESHOLD_VERGLEICH.get(daten['schwellenwert_operator'])
    if schiffsfeld is None or vergleichsfunktion is None or daten['schwellenwert_wert'] is None:
        return True  # Schwellenwert nicht auswertbar -> nicht blockieren

    erfuellt = vergleichsfunktion(Schiffsdaten[schiffsfeld], daten['schwellenwert_wert'])
    if erfuellt:
        return True

    # Bestehende CALDOVREP-Ausnahme bleibt erhalten: Schiffe unter der GT-Schwelle muessen
    # trotzdem melden, wenn sie eingeschraenkt manoevrierfaehig sind oder defekte
    # Navigationshilfen haben (siehe ADP Abs. 2). Gilt nur fuer GT-Schwellen.
    if (merkmal == "gross_tonnage" and daten['gt_ausnahme'] == "Ja"
            and (Schiffsdaten['eingeschraenkt_manoevrierfaehig'] == "Yes"
                 or Schiffsdaten['defekte_navigationshilfen'] == "Yes")):
        return True

    return False

# Prüft, ob die Schiffsdaten die Melde-Kriterien eines Gebiets erfüllen
def erfuellt_schiffskriterien(daten, Schiffsdaten):
    if not erfuellt_schwellenwert(daten, Schiffsdaten):
        return False

    ist_tanker = Schiffsdaten['schiffstyp'] in TANKER_TYPEN
    hat_gefahrgut = Schiffsdaten['gefahrgut'] == "Yes"

    if daten['tanker_oder_gefahrgut'] == "Ja":
        # Manche Gebiete (z.B. SURNAV Gris-Nez) gelten für Tankschiffe ODER Schiffe mit
        # Gefahrgut an Bord (z.B. Containerschiffe mit IMDG-Ladung) - hier ODER statt UND.
        if not (ist_tanker or hat_gefahrgut):
            return False
    else:
        # Falls das Gebiet nur bei Gefahrgut meldepflichtig ist (Requires_IMDG: yes/no/any)
        if daten['erfordert_imdg'] == "yes" and not hat_gefahrgut:
            return False

        # Falls das Gebiet nur für Tankschiffe gilt
        if daten['nur_tanker'] == "Ja" and not ist_tanker:
            return False

    # Falls das Gebiet einen bestimmten Ladungstyp voraussetzt (Requires_Cargo_Type)
    if daten['erforderlicher_ladungstyp'] is not None and \
            Schiffsdaten['category_of_cargo_code'] != daten['erforderlicher_ladungstyp']:
        return False

    # Falls das Gebiet nur bestimmte Schiffstypen zulaesst (Applicable_Vessel_Types)
    if daten['zulaessige_schiffstypen'] and \
            Schiffsdaten['category_of_vessel_code'] not in daten['zulaessige_schiffstypen']:
        return False

    # Falls das Gebiet bestimmte Schiffstypen ausschliesst (Excluded_Vessel_Types)
    if Schiffsdaten['category_of_vessel_code'] in daten['ausgeschlossene_schiffstypen']:
        return False

    # Ausnahme fuer Regierungsschiffe im nicht-kommerziellen Dienst (z.B. WETREP: gilt nicht
    # fuer Kriegsschiffe/Marinehilfsschiffe/sonstige Regierungsschiffe - ADP-Ausnahmeklausel)
    if daten['regierungsschiff_ausnahme'] == "Ja" and Schiffsdaten['government_non_commercial'] == "Yes":
        return False

    # Falls das Gebiet nur bei Schweröl-/Schwerölkraftstoff-/Bitumen-Ladung gilt (z.B. WETREP)
    if daten['schweroel_pflicht'] == "Ja" and Schiffsdaten['schweroel_ladung'] != "Yes":
        return False

    # Falls das Gebiet nur bei internationaler Fahrt gilt
    if daten['nur_internationale_fahrt'] == "Ja" and Schiffsdaten['internationale_fahrt'] != "Yes":
        return False

    return True

# Wandelt eine kommagetrennte CSV-Zelle ("3,19") in eine Menge von Ganzzahlen um.
# Leere/fehlende Zelle -> leere Menge.
def parse_int_menge(wert):
    if pd.isna(wert) or str(wert).strip() == "":
        return set()
    # Pandas liest eine Spalte, in der (fast) nur eine einzelne Zahl vorkommt (z.B.
    # Excluded_Vessel_Types mit nur "10" bei WETREP), als Float ein ("10.0") - daher
    # ueber float() statt direkt int() parsen, das funktioniert fuer beide Faelle.
    return {int(float(teil.strip())) for teil in str(wert).split(",") if teil.strip()}

# Wandelt eine kommagetrennte CSV-Zelle ("48,12,2") in eine geordnete Liste von Zahlen um.
def parse_zahlen_liste(wert):
    if pd.isna(wert) or str(wert).strip() == "":
        return []
    return [float(teil.strip()) for teil in str(wert).split(",") if teil.strip()]

# Schritt 1: Gebiete aus CSV als Polygone bauen
def baue_gebiete(df):
    gebiete = {}
    aktuelles_gebiet = None

    for _, reihe in df.iterrows():
        # Wenn ein Gebietsname vorhanden ist, neues Gebiet starten
        if pd.notna(reihe['Gebiet']) and reihe['Gebiet'] != 'NaN':
            aktuelles_gebiet = reihe['Gebiet']
            gebiete[aktuelles_gebiet] = {
                'punkte': [],
                'typ': reihe['Typ'],
                'frequenz': reihe['Frequenz'],
                # Bestehende Schiffs-Kriterien-Spalten (mit sinnvollen Standardwerten,
                # falls in der CSV mal eine Zelle leer sein sollte)
                'nur_tanker': reihe['Nur_Tanker'] if pd.notna(reihe['Nur_Tanker']) else "Nein",
                'nur_internationale_fahrt': reihe['Nur_Internationale_Fahrt'] if pd.notna(reihe['Nur_Internationale_Fahrt']) else "Nein",
                'tanker_oder_gefahrgut': reihe['Tanker_Oder_Gefahrgut'] if pd.notna(reihe['Tanker_Oder_Gefahrgut']) else "Nein",
                'schweroel_pflicht': reihe['Schweroel_Pflicht'] if pd.notna(reihe['Schweroel_Pflicht']) else "Nein",
                # Radius in nm fuer Kreis-Gebiete (Dover VTS, Ramsgate); 0 = kein Kreis-Gebiet
                'radius_nm': reihe['Radius_NM'] if pd.notna(reihe['Radius_NM']) else 0,
                # "bedingt_inbound"/"bedingt_outbound" markieren Gebiete, die nur beim
                # tatsaechlichen Anlaufen bzw. Verlassen des Hafens gelten (nicht bei reinem
                # Durchtransit) - siehe Haupt-Loop
                'pflicht_typ': reihe['Pflicht_Typ'] if pd.notna(reihe['Pflicht_Typ']) else "",
                # GT-Ausnahme bei eingeschraenkter Manoevrierfaehigkeit/defekten Navigationshilfen
                'gt_ausnahme': reihe['GT_Ausnahme_Bei_Einschraenkung'] if pd.notna(reihe['GT_Ausnahme_Bei_Einschraenkung']) else "Nein",
                # Zusatzinfos fuer die Ausgabe (kein Einfluss auf die Trigger-Logik)
                'dauerpflicht': reihe['Dauerpflicht'] if pd.notna(reihe['Dauerpflicht']) else "",
                'meldeinhalt': reihe['Meldeinhalt'] if pd.notna(reihe['Meldeinhalt']) else "",
                'faehre_hinweis': reihe['Faehre_Hinweis'] if pd.notna(reihe['Faehre_Hinweis']) else "",
                'lng_hinweis': reihe['LNG_Hinweis'] if pd.notna(reihe['LNG_Hinweis']) else "",

                # --- S-127-Spalten ---
                # Generischer Schwellenwert (ersetzt die alten festen Min_GT/Min_TDW-Vergleiche;
                # Min_GT/Min_TDW-Spalten bleiben in der CSV als Referenz erhalten, werden aber
                # nicht mehr ausgelesen, um zwei parallele Wahrheitsquellen zu vermeiden)
                'schwellenwert_merkmal': reihe['Threshold_Characteristic'] if pd.notna(reihe['Threshold_Characteristic']) else "",
                'schwellenwert_operator': reihe['Threshold_Operator'] if pd.notna(reihe['Threshold_Operator']) else "",
                'schwellenwert_wert': float(reihe['Threshold_Value']) if pd.notna(reihe['Threshold_Value']) else None,
                'zulaessige_schiffstypen': parse_int_menge(reihe['Applicable_Vessel_Types']),
                'ausgeschlossene_schiffstypen': parse_int_menge(reihe['Excluded_Vessel_Types']),
                'regierungsschiff_ausnahme': reihe['Government_Vessel_Exempt'] if pd.notna(reihe['Government_Vessel_Exempt']) else "Nein",
                'erforderlicher_ladungstyp': int(float(reihe['Requires_Cargo_Type'])) if pd.notna(reihe['Requires_Cargo_Type']) else None,
                'erfordert_imdg': reihe['Requires_IMDG'] if pd.notna(reihe['Requires_IMDG']) else "any",
                'report_types': sorted(parse_int_menge(reihe['Report_Types'])),
                'notice_time_hours': parse_zahlen_liste(reihe['Notice_Time_Hours']),
                'notice_time_text': reihe['Notice_Time_Text'] if pd.notna(reihe['Notice_Time_Text']) else "",
                'relationship_type': reihe['Relationship_Type'] if pd.notna(reihe['Relationship_Type']) else "required",
                'traffic_flow': reihe['Traffic_Flow'] if pd.notna(reihe['Traffic_Flow']) else "",
                'source_type': reihe['Source_Type'] if pd.notna(reihe['Source_Type']) else "",
                'source_reference': reihe['Source_Reference'] if pd.notna(reihe['Source_Reference']) else "",
            }

        # Koordinaten zum aktuellen Gebiet hinzufügen
        if aktuelles_gebiet and pd.notna(reihe['Lat. Grad in Dezimal']):
            lat = reihe['Lat. Grad in Dezimal']
            lon = reihe['Long. Grad in Dezimal']
            if lat > 1:  # Leere Zeilen filtern
                gebiete[aktuelles_gebiet]['punkte'].append((lon, lat))
    
    return gebiete

# Schritt 1: Schiffsdaten am Programmstart abfragen (vor der Routenprüfung)
Schiffsdaten = frage_schiffsdaten()

# Route auswählen: aus RTZ-/GPX-Datei importieren oder manuell eingeben
routen_dateien = sorted(
    glob.glob(os.path.join("routes", "*.rtz")) + glob.glob(os.path.join("routes", "*.gpx"))
)
routen_name = None

print("=== SELECT ROUTE ===")
if routen_dateien:
    for i, pfad in enumerate(routen_dateien, start=1):
        print(f"  {i}) {os.path.basename(pfad)}")
    print("  0) Enter manually")

    auswahl = input("\nSelect route (number): ").strip().lstrip("﻿")
else:
    auswahl = "0"

if routen_dateien and auswahl != "0":
    gewaehlte_datei = routen_dateien[int(auswahl) - 1]
    # Je nach Dateiendung den passenden Parser verwenden
    if gewaehlte_datei.lower().endswith(".gpx"):
        routen_name, geladene_wegpunkte = lade_gpx_route(gewaehlte_datei)
    else:
        routen_name, geladene_wegpunkte = lade_rtz_route(gewaehlte_datei)
    wegpunkte = [(lon, lat) for lon, lat, _ in geladene_wegpunkte]
    print(f"\nRoute loaded: {routen_name} ({len(wegpunkte)} waypoints)")
    for lon, lat, name in geladene_wegpunkte:
        print(f"  - {name}: {lat:.5f}, {lon:.5f}")
    print()
else:
    print("\nEnter waypoints (format: Latitude Longitude, e.g. 50.5 1.0)")
    print("Leave empty to finish\n")

    wegpunkte = []
    nummer = 1
    while True:
        eingabe = input(f"Waypoint {nummer}: ")
        if eingabe == "":
            break

        lat, lon = eingabe.split()
        wegpunkte.append((float(lon), float(lat)))
        nummer += 1

testroute = LineString(wegpunkte)

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

# Ordnet den Relationship_Type-Wert einer Statuszeile für die Ausgabe zu
# (aktuell sind alle geometrisch geprueften Gebiete "required" - die anderen Zweige
# sind fuer zukuenftige, als "recommended" o.ae. markierte Gebiete vorbereitet)
def relationship_status_label(relationship_type):
    if relationship_type in ("recommended", "permitted"):
        return "RECOMMENDED (voluntary system)"
    if relationship_type in ("not_required", "not_recommended", "prohibited"):
        return "NOTE (not required)"
    return "REPORTING REQUIRED"

# Schritt 4: Zusammenfassung der Schiffsdaten anzeigen
zusammenfassung_schiff = (
    f"Checked for: {Schiffsdaten['schiffstyp']}, {Schiffsdaten['gt']:.0f} GT, "
    f"dangerous goods: {Schiffsdaten['gefahrgut']}, "
    f"international voyage: {Schiffsdaten['internationale_fahrt']}"
)

# Schritt 3: Prüfen welche Gebiete die Route kreuzt
# Ergebnisse sammeln und ausgeben
print("=== ROUTE CHECKER ===")
print(zusammenfassung_schiff)
print("Checking route for reporting obligations...\n")

gebiete = baue_gebiete(df)
ergebnisse = []

letzter_wegpunkt = Point(wegpunkte[-1]) if wegpunkte else None
erster_wegpunkt = Point(wegpunkte[0]) if wegpunkte else None

for name, daten in gebiete.items():
    # Die meisten Gebiete sind Flächen (Polygon, >=3 Punkte) oder eine Zonengrenze
    # zwischen zwei Zuständigkeiten (2 Punkte -> LineString, z.B. SURNAV Gris-Nez).
    # Manche Gebiete (Dover VTS, Ramsgate) sind stattdessen ein Melde-Kreis mit
    # festem Radius um einen einzigen Mittelpunkt (Radius_NM > 0).
    geometrie = None
    if len(daten['punkte']) == 1 and daten['radius_nm'] > 0:
        lon, lat = daten['punkte'][0]
        geometrie = baue_kreis_geometrie(lon, lat, daten['radius_nm'])
    elif len(daten['punkte']) >= 3:
        geometrie = Polygon(daten['punkte'])
    elif len(daten['punkte']) == 2:
        geometrie = LineString(daten['punkte'])

    if geometrie is not None:
        if daten['pflicht_typ'] == "bedingt_inbound":
            # "bedingt_inbound" (z.B. Dover VTS, Ramsgate): Meldepflicht gilt NUR, wenn
            # der Hafen tatsaechlich Ziel der Route ist - nicht bei reinem Durchtransit
            # durch die Naehe. Als Zielhafen gilt der letzte Wegpunkt der Route; nur wenn
            # DER innerhalb des Melde-Kreises liegt, greift die Meldepflicht - unabhaengig
            # davon, ob die Route an anderer Stelle geometrisch durch den Kreis verlaeuft.
            kreuzt = letzter_wegpunkt is not None and geometrie.contains(letzter_wegpunkt)
        elif daten['pflicht_typ'] == "bedingt_outbound":
            # "bedingt_outbound" (z.B. Dover VTS (Outbound), Ramsgate (Outbound)):
            # Spiegelbild von "bedingt_inbound" - Meldepflicht gilt NUR, wenn der Hafen
            # tatsaechlich AUSGANGSPUNKT der Route ist (auslaufendes Schiff), nicht bei
            # reinem Durchtransit. Als Abfahrtshafen gilt der ERSTE Wegpunkt der Route.
            kreuzt = erster_wegpunkt is not None and geometrie.contains(erster_wegpunkt)
        else:
            # Normalfall: JEDE Kreuzung der Route mit dem Gebiet loest die Meldepflicht aus.
            kreuzt = testroute.intersects(geometrie)

        # Geometrische/situative Prüfung (s.o.) UND Schiffs-Kriterien-Prüfung: passen
        # GT/Gefahrgut/Tankertyp/Fahrtgebiet zum Schiff?
        if kreuzt and erfuellt_schiffskriterien(daten, Schiffsdaten):
            freq = f"Ch {int(daten['frequenz'])}" if pd.notna(daten['frequenz']) else "see ADP"
            ist_faehre = Schiffsdaten['schiffstyp'] == "Ferry"
            ist_lng = Schiffsdaten['schiffstyp'] == "LNG tanker"
            status_label = relationship_status_label(daten['relationship_type'])
            report_typen_text = formatiere_report_typen(daten['report_types'])
            vorlaufzeit_text = formatiere_vorlaufzeit(daten['notice_time_hours'], daten['notice_time_text'])
            eintrag = {
                'gebiet': name,
                'typ': daten['typ'],
                'frequenz': freq,
                'dauerpflicht': daten['dauerpflicht'],
                'meldeinhalt': daten['meldeinhalt'],
                'faehre_hinweis': daten['faehre_hinweis'] if ist_faehre else "",
                'lng_hinweis': daten['lng_hinweis'] if ist_lng else "",
                'status_label': status_label,
                'report_typen_text': report_typen_text,
                'vorlaufzeit_text': vorlaufzeit_text,
                'source_reference': daten['source_reference'],
            }
            ergebnisse.append(eintrag)
            print(f"   {status_label}: {name}")
            print(f"   Type:          {daten['typ']}")
            print(f"   Frequency:     {freq}")
            print(f"   Action:        Report on {freq} to the responsible MRCC")
            if eintrag['meldeinhalt']:
                print(f"   Report content: {eintrag['meldeinhalt']}")
            if eintrag['dauerpflicht']:
                print(f"   Continuous watch/duty: {eintrag['dauerpflicht']}")
            if eintrag['faehre_hinweis']:
                print(f"   Ferry note:    {eintrag['faehre_hinweis']}")
            if eintrag['lng_hinweis']:
                print(f"   LNG note:      {eintrag['lng_hinweis']}")
            if report_typen_text:
                print(f"   Report type(s): {report_typen_text}")
            if vorlaufzeit_text:
                print(f"   Notice:        {vorlaufzeit_text}")
            if eintrag['source_reference']:
                print(f"   Source:        {eintrag['source_reference']}")
            print()

if len(ergebnisse) == 0:
    print("No reporting obligations found for this route.")

# UK MAREP: freiwilliges Meldesystem, keine eigene Geometrie im ADP-Text (verweist nur auf
# Gebiete ausserhalb Dover Strait) - daher als pauschaler Hinweis statt als geprueftes Gebiet,
# analog zur "NACHDRUECKLICH ERMUTIGT"-Formulierung im Originaltext. Gilt fuer Handelsschiffe
# ab 300GT. MANCHEREP/OUESSREP sind die verpflichtenden Versionen ausserhalb Dover Strait -
# ohne eigene Koordinaten in den vorliegenden ADP-Texten, daher nur erwaehnt statt geprueft.
if UK_MAREP_AKTIV and Schiffsdaten['gt'] >= 300:
    print("   VOLUNTARY: UK MAREP")
    print("   This is a voluntary reporting system (not mandatory in this area, since")
    print("   CALDOVREP already covers the mandatory equivalent for the Dover Strait).")
    print("   All merchant ships >=300GT are strongly encouraged to participate: report to")
    print("   the relevant coastal station 1h before entering and again when leaving the")
    print("   area (POSREP/DEFREP/CHANGEREP format). Mandatory versions of this system type")
    print("   also apply in TSS Off Ushant (OUESSREP) and TSS Off Casquets (MANCHEREP) -")
    print("   both outside this tool's Dover Strait scope and without their own coordinates")
    print("   in the source ADP texts, so not geometrically checked here.")
    print()

# Ergebnis als Textdatei speichern
import datetime
with open("ergebnis.txt", "w") as datei:
    datei.write("=== ROUTE CHECKER - REPORTING OBLIGATIONS ===\n\n")
    datei.write(f"Created: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    if routen_name:
        datei.write(f"Route: {routen_name}\n")
    datei.write(f"Waypoints checked: {len(wegpunkte)}\n")
    datei.write(f"{zusammenfassung_schiff}\n\n")
    for e in ergebnisse:
        datei.write(f"{e['status_label']}: {e['gebiet']}\n")
        datei.write(f"Type:          {e['typ']}\n")
        datei.write(f"Frequency:     {e['frequenz']}\n")
        datei.write(f"Action:        Report on {e['frequenz']} to the responsible MRCC\n")
        if e['meldeinhalt']:
            datei.write(f"Report content: {e['meldeinhalt']}\n")
        if e['dauerpflicht']:
            datei.write(f"Continuous watch/duty: {e['dauerpflicht']}\n")
        if e['faehre_hinweis']:
            datei.write(f"Ferry note:    {e['faehre_hinweis']}\n")
        if e['lng_hinweis']:
            datei.write(f"LNG note:      {e['lng_hinweis']}\n")
        if e['report_typen_text']:
            datei.write(f"Report type(s): {e['report_typen_text']}\n")
        if e['vorlaufzeit_text']:
            datei.write(f"Notice:        {e['vorlaufzeit_text']}\n")
        if e['source_reference']:
            datei.write(f"Source:        {e['source_reference']}\n")
        datei.write("\n")

    if UK_MAREP_AKTIV and Schiffsdaten['gt'] >= 300:
        datei.write("VOLUNTARY: UK MAREP\n")
        datei.write(
            "This is a voluntary reporting system (not mandatory in this area, since "
            "CALDOVREP already covers the mandatory equivalent for the Dover Strait). "
            "All merchant ships >=300GT are strongly encouraged to participate: report to "
            "the relevant coastal station 1h before entering and again when leaving the "
            "area (POSREP/DEFREP/CHANGEREP format). Mandatory versions of this system type "
            "also apply in TSS Off Ushant (OUESSREP) and TSS Off Casquets (MANCHEREP) - both "
            "outside this tool's Dover Strait scope and without their own coordinates in the "
            "source ADP texts, so not geometrically checked here.\n"
        )
        datei.write("\n")


print("=== CHECK COMPLETE ===")
print(f"\nResult saved as 'ergebnis.txt' in your project folder")
