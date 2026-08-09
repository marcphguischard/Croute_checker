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

# Schritt 1: Schiffsdaten interaktiv abfragen und als Dictionary zurückgeben
def frage_schiffsdaten():
    print("=== SHIP DATA ===")

    # 1. Schiffstyp aus einer festen Liste auswählen (wie bei der Routenauswahl)
    schiffstypen = ["Tanker", "Chemical tanker", "Gas tanker", "LNG tanker",
                    "Bulk carrier", "General cargo ship", "Ferry", "Other"]
    print("Ship type:")
    for i, typ in enumerate(schiffstypen, start=1):
        print(f"  {i}) {typ}")
    while True:
        auswahl = input("Selection (number): ").strip()
        if auswahl.isdigit() and 1 <= int(auswahl) <= len(schiffstypen):
            schiffstyp = schiffstypen[int(auswahl) - 1]
            break
        print("Please enter a valid number.")

    # 2. Bruttoraumzahl (GT) als Zahl
    gt = frage_zahl("Gross tonnage (GT)")

    # 2b. Tragfähigkeit (tdw) - wird für tonnage-abhängige Meldepflichten wie WETREP benötigt
    #     (tdw ist NICHT dasselbe wie GT, daher eigene Abfrage/Spalte)
    tdw = frage_zahl("Deadweight (tdw)")

    # 3. Internationale Fahrt: Ja/Nein
    internationale_fahrt = frage_ja_nein("International voyage")

    # 4. Gefahrgut an Bord: Ja/Nein, bei Ja zusätzlich die IMDG-Klasse als Freitext
    gefahrgut = frage_ja_nein("Dangerous goods on board")
    imdg_klasse = ""
    if gefahrgut == "Yes":
        imdg_klasse = input("IMDG class: ").strip()

    # 4b. Schweröl/Schwerölkraftstoff/Bitumen-Ladung (relevant für WETREP)
    schweroel_ladung = frage_ja_nein(
        "Heavy fuel oil cargo (density >900kg/m³ at 15°C), heavy fuel (density >900kg/m³ "
        "or viscosity >180mm²/s at 50°C), or bitumen/tar on board"
    )

    # 5. Anzahl Personen an Bord als ganze Zahl
    personen_an_bord = frage_zahl("Number of persons on board", ist_ganzzahl=True)

    # 6. Tiefgang eingeschränkt / Sondertransport: Ja/Nein
    sondertransport = frage_ja_nein("Restricted draught / special transport")

    # 6b/6c. Zustands-Ausnahmen, die die 300GT-Schwelle bei CALDOVREP aushebeln koennen (siehe
    # erfuellt_schiffskriterien()). "Not under command" wird bewusst NICHT gefragt, da das nicht
    # planbar ist (tritt unerwartet ein) - eingeschraenkte Manoevrierfaehigkeit kann dagegen auch
    # planmaessig vorliegen (z.B. Schleppverband, Baggerarbeiten).
    eingeschraenkt_manoevrierfaehig = frage_ja_nein("Restricted in ability to manoeuvre")
    defekte_navigationshilfen = frage_ja_nein("Defective navigational aids")

    Schiffsdaten = {
        "schiffstyp": schiffstyp,
        "gt": gt,
        "tdw": tdw,
        "internationale_fahrt": internationale_fahrt,
        "gefahrgut": gefahrgut,
        "imdg_klasse": imdg_klasse,
        "schweroel_ladung": schweroel_ladung,
        "personen_an_bord": personen_an_bord,
        "sondertransport": sondertransport,
        "eingeschraenkt_manoevrierfaehig": eingeschraenkt_manoevrierfaehig,
        "defekte_navigationshilfen": defekte_navigationshilfen,
    }
    print()
    return Schiffsdaten

# Schiffstypen, die als "Tanker" im Sinne von Nur_Tanker gelten
TANKER_TYPEN = {"Tanker", "Chemical tanker", "Gas tanker", "LNG tanker"}

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

# Prüft, ob die Schiffsdaten die Melde-Kriterien eines Gebiets erfüllen
def erfuellt_schiffskriterien(daten, Schiffsdaten):
    # GT muss mindestens Min_GT des Gebiets sein - AUSSER das Gebiet erlaubt eine Ausnahme
    # bei eingeschraenkter Manoevrierfaehigkeit/defekten Navigationshilfen (z.B. CALDOVREP:
    # Schiffe <300GT muessen trotzdem melden, wenn "restricted in ability to manoeuvre" oder
    # "defective navigational aids" zutrifft - siehe ADP Abs. 2).
    gt_ausnahme = (
        daten['gt_ausnahme'] == "Ja"
        and (Schiffsdaten['eingeschraenkt_manoevrierfaehig'] == "Yes"
             or Schiffsdaten['defekte_navigationshilfen'] == "Yes")
    )
    if Schiffsdaten['gt'] < daten['min_gt'] and not gt_ausnahme:
        return False

    # Tragfähigkeit (tdw) muss mindestens Min_TDW des Gebiets sein (z.B. WETREP: >600 tdw)
    if Schiffsdaten['tdw'] < daten['min_tdw']:
        return False

    ist_tanker = Schiffsdaten['schiffstyp'] in TANKER_TYPEN
    hat_gefahrgut = Schiffsdaten['gefahrgut'] == "Yes"

    if daten['tanker_oder_gefahrgut'] == "Ja":
        # Manche Gebiete (z.B. SURNAV Gris-Nez) gelten für Tankschiffe ODER Schiffe mit
        # Gefahrgut an Bord (z.B. Containerschiffe mit IMDG-Ladung) - hier ODER statt UND.
        if not (ist_tanker or hat_gefahrgut):
            return False
    else:
        # Falls das Gebiet nur bei Gefahrgut meldepflichtig ist
        if daten['gefahrgut_pflicht'] == "Ja" and not hat_gefahrgut:
            return False

        # Falls das Gebiet nur für Tankschiffe gilt
        if daten['nur_tanker'] == "Ja" and not ist_tanker:
            return False

    # Falls das Gebiet nur bei Schweröl-/Schwerölkraftstoff-/Bitumen-Ladung gilt (z.B. WETREP)
    if daten['schweroel_pflicht'] == "Ja" and Schiffsdaten['schweroel_ladung'] != "Yes":
        return False

    # Falls das Gebiet nur bei internationaler Fahrt gilt
    if daten['nur_internationale_fahrt'] == "Ja" and Schiffsdaten['internationale_fahrt'] != "Yes":
        return False

    return True

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
                # Neue Schiffs-Kriterien-Spalten (mit sinnvollen Standardwerten,
                # falls in der CSV mal eine Zelle leer sein sollte)
                'min_gt': reihe['Min_GT'] if pd.notna(reihe['Min_GT']) else 0,
                'gefahrgut_pflicht': reihe['Gefahrgut_Pflicht'] if pd.notna(reihe['Gefahrgut_Pflicht']) else "Egal",
                'nur_tanker': reihe['Nur_Tanker'] if pd.notna(reihe['Nur_Tanker']) else "Nein",
                'nur_internationale_fahrt': reihe['Nur_Internationale_Fahrt'] if pd.notna(reihe['Nur_Internationale_Fahrt']) else "Nein",
                # Neue Spalten für tonnage-/ladungsabhängige Gebiete (z.B. SURNAV, WETREP)
                'min_tdw': reihe['Min_TDW'] if pd.notna(reihe['Min_TDW']) else 0,
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

# Route auswählen: aus RTZ-Datei importieren oder manuell eingeben
rtz_dateien = sorted(glob.glob(os.path.join("routes", "*.rtz")))
routen_name = None

print("=== SELECT ROUTE ===")
if rtz_dateien:
    for i, pfad in enumerate(rtz_dateien, start=1):
        print(f"  {i}) {os.path.basename(pfad)}")
    print("  0) Enter manually")

    auswahl = input("\nSelect route (number): ").strip().lstrip("﻿")
else:
    auswahl = "0"

if rtz_dateien and auswahl != "0":
    routen_name, geladene_wegpunkte = lade_rtz_route(rtz_dateien[int(auswahl) - 1])
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
            eintrag = {
                'gebiet': name,
                'typ': daten['typ'],
                'frequenz': freq,
                'dauerpflicht': daten['dauerpflicht'],
                'meldeinhalt': daten['meldeinhalt'],
                'faehre_hinweis': daten['faehre_hinweis'] if ist_faehre else "",
                'lng_hinweis': daten['lng_hinweis'] if ist_lng else "",
            }
            ergebnisse.append(eintrag)
            print(f"   REPORTING REQUIRED: {name}")
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
            print()

if len(ergebnisse) == 0:
    print("No reporting obligations found for this route.")

# UK MAREP: freiwilliges Meldesystem, keine eigene Geometrie im ADP-Text (verweist nur auf
# Gebiete ausserhalb Dover Strait) - daher als pauschaler Hinweis statt als geprueftes Gebiet,
# analog zur "NACHDRUECKLICH ERMUTIGT"-Formulierung im Originaltext. Gilt fuer Handelsschiffe
# ab 300GT. MANCHEREP/OUESSREP sind die verpflichtenden Versionen ausserhalb Dover Strait -
# ohne eigene Koordinaten in den vorliegenden ADP-Texten, daher nur erwaehnt statt geprueft.
if Schiffsdaten['gt'] >= 300:
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
        datei.write(f"REPORTING REQUIRED: {e['gebiet']}\n")
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
        datei.write("\n")

    if Schiffsdaten['gt'] >= 300:
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
