# Meldegebiete aus reporting_points.csv einlesen und als Geometrie (Polygon/
# LineString/Kreis) aufbauen.
import warnings
from math import cos, radians

import pandas as pd
from shapely.affinity import scale
from shapely.geometry import LineString, Point, Polygon, mapping


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


# Schritt 1: Gebiete aus CSV als Polygone bauen
def baue_gebiete(df):
    gebiete = {}
    aktuelles_gebiet = None
    hat_reporting_station_spalte = "Reporting_Station" in df.columns

    for _, reihe in df.iterrows():
        # Wenn ein Gebietsname vorhanden ist, neues Gebiet starten
        if pd.notna(reihe['Gebiet']) and reihe['Gebiet'] != 'NaN':
            aktuelles_gebiet = reihe['Gebiet']
            gebiete[aktuelles_gebiet] = {
                'punkte': [],
                'typ': reihe['Typ'],
                'frequenz': reihe['Frequenz'],
                # Alternative Frequenz fuer suedwestgehenden Verkehr (nur CALDOVREP: Ch13
                # Gris-Nez Traffic nordostgehend, Ch11 Channel VTS suedwestgehend) - leer bei
                # allen anderen Gebieten, dann gilt immer 'frequenz'.
                'frequenz_sw_bound': reihe['Frequenz_SW_Bound'] if pd.notna(reihe['Frequenz_SW_Bound']) else None,
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
                # Durchtransit) - siehe pruefung.pruefe_route()
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
                # Primaerquellen-Nachweis (IMO-Entschliessungen, nationale Erlasse,
                # General Directions) - ergaenzt/ersetzt Source_Type/Source_Reference
                # fuer die Anzeige, siehe ausgabe.formatiere_quellenanzeige().
                'primary_source_reference': reihe['Primary_Source_Reference'] if pd.notna(reihe['Primary_Source_Reference']) else "",
                'verification_status': reihe['Verification_Status'] if pd.notna(reihe['Verification_Status']) else "",
                # Optionale Spalte, existiert in der heutigen CSV noch nicht - nur
                # auswerten, wenn vorhanden, sonst Default "" (Kleinkorrektur 1.2.6).
                'reporting_station': (
                    reihe['Reporting_Station']
                    if hat_reporting_station_spalte and pd.notna(reihe['Reporting_Station'])
                    else ""
                ),
            }

        # Koordinaten zum aktuellen Gebiet hinzufügen
        if aktuelles_gebiet and pd.notna(reihe['Lat. Grad in Dezimal']):
            lat = reihe['Lat. Grad in Dezimal']
            lon = reihe['Long. Grad in Dezimal']
            if lat > 1:  # Leere Zeilen filtern
                gebiete[aktuelles_gebiet]['punkte'].append((lon, lat))

    return gebiete


# Liest reporting_points.csv (oder eine andere Datei im selben Format) ein und
# baut daraus das Gebiete-Dict. Kapselt pd.read_csv + baue_gebiete, damit kein
# Modul mehr beim Import automatisch liest (main.py Zeile ~11 vorher).
def lade_gebiete(pfad="reporting_points.csv"):
    df = pd.read_csv(pfad)
    return baue_gebiete(df)


# Baut aus den Gebiets-Rohdaten (ein Eintrag aus baue_gebiete()) die passende
# Shapely-Geometrie: Kreis (1 Punkt + Radius), Polygon (>=3 Punkte) oder
# LineString (2 Punkte, z.B. Zonengrenze SURNAV Gris-Nez). None, wenn keine
# der drei Formen passt (z.B. Gebiet ganz ohne Koordinaten in der CSV).
#
# Nach main.py-Hauptschleife (vorher Zeilen ~604-611) ausgelagert, damit sowohl
# pruefung.pruefe_route() als auch der spaetere /api/areas-Endpoint (Phase 2,
# Karte aller Gebiete) dieselbe Logik nutzen.
def baue_geometrie_fuer_gebiet(daten, gebietsname=None):
    geometrie = None
    if len(daten['punkte']) == 1 and daten['radius_nm'] > 0:
        lon, lat = daten['punkte'][0]
        geometrie = baue_kreis_geometrie(lon, lat, daten['radius_nm'])
    elif len(daten['punkte']) >= 3:
        geometrie = Polygon(daten['punkte'])
        # Kleinkorrektur 1.2.4: ungueltige Polygone nicht stillschweigend
        # reparieren (z.B. kein automatisches buffer(0)) - nur warnen, damit
        # der Fehler in der CSV/den Koordinaten sichtbar bleibt und bewusst
        # behoben werden kann.
        if not geometrie.is_valid:
            warnung = f"Ungueltiges Polygon fuer Gebiet '{gebietsname or '?'}' (z.B. sich selbst schneidende Kanten)."
            warnings.warn(warnung)
    elif len(daten['punkte']) == 2:
        geometrie = LineString(daten['punkte'])
    return geometrie


# Wandelt eine Shapely-Geometrie in ein GeoJSON-faehiges Dict um (fuer die
# Karte in Phase 2).
def geometrie_zu_geojson(geometrie):
    return mapping(geometrie)
