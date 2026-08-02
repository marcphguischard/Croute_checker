import pandas as pd
from shapely.geometry import Polygon, LineString
from datetime import datetime
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
        antwort = input(f"{frage} (Ja/Nein): ").strip().capitalize()
        if antwort in ("Ja", "Nein"):
            return antwort
        print("Bitte 'Ja' oder 'Nein' eingeben.")

# Fragt eine Zahl ab und gibt so lange erneut nach, bis eine gültige Zahl eingegeben wurde.
# ist_ganzzahl=True verlangt eine ganze Zahl (z.B. für Personenanzahl), sonst sind Kommazahlen erlaubt (z.B. für GT).
def frage_zahl(frage, ist_ganzzahl=False):
    while True:
        eingabe = input(f"{frage}: ").strip()
        try:
            return int(eingabe) if ist_ganzzahl else float(eingabe)
        except ValueError:
            print("Bitte eine Zahl eingeben.")

# Schritt 1: Schiffsdaten interaktiv abfragen und als Dictionary zurückgeben
def frage_schiffsdaten():
    print("=== SCHIFFSDATEN ===")

    # 1. Schiffstyp aus einer festen Liste auswählen (wie bei der Routenauswahl)
    schiffstypen = ["Tanker", "Chemikalientanker", "Gastanker",
                    "Massengutfrachter", "Stückgutfrachter", "Sonstige"]
    print("Schiffstyp:")
    for i, typ in enumerate(schiffstypen, start=1):
        print(f"  {i}) {typ}")
    while True:
        auswahl = input("Auswahl (Nummer): ").strip()
        if auswahl.isdigit() and 1 <= int(auswahl) <= len(schiffstypen):
            schiffstyp = schiffstypen[int(auswahl) - 1]
            break
        print("Bitte eine gültige Nummer eingeben.")

    # 2. Bruttoraumzahl (GT) als Zahl
    gt = frage_zahl("Bruttoraumzahl (GT)")

    # 3. Internationale Fahrt: Ja/Nein
    internationale_fahrt = frage_ja_nein("Internationale Fahrt")

    # 4. Gefahrgut an Bord: Ja/Nein, bei Ja zusätzlich die IMDG-Klasse als Freitext
    gefahrgut = frage_ja_nein("Gefahrgut an Bord")
    imdg_klasse = ""
    if gefahrgut == "Ja":
        imdg_klasse = input("IMDG-Klasse: ").strip()

    # 5. Anzahl Personen an Bord als ganze Zahl
    personen_an_bord = frage_zahl("Anzahl Personen an Bord", ist_ganzzahl=True)

    # 6. Tiefgang eingeschränkt / Sondertransport: Ja/Nein
    sondertransport = frage_ja_nein("Tiefgang eingeschränkt / Sondertransport")

    Schiffsdaten = {
        "schiffstyp": schiffstyp,
        "gt": gt,
        "internationale_fahrt": internationale_fahrt,
        "gefahrgut": gefahrgut,
        "imdg_klasse": imdg_klasse,
        "personen_an_bord": personen_an_bord,
        "sondertransport": sondertransport,
    }
    print()
    return Schiffsdaten

# Schiffstypen, die als "Tanker" im Sinne von Nur_Tanker gelten
TANKER_TYPEN = {"Tanker", "Chemikalientanker", "Gastanker"}

# Prüft, ob die Schiffsdaten die Melde-Kriterien eines Gebiets erfüllen
def erfuellt_schiffskriterien(daten, Schiffsdaten):
    # GT muss mindestens Min_GT des Gebiets sein
    if Schiffsdaten['gt'] < daten['min_gt']:
        return False

    # Falls das Gebiet nur bei Gefahrgut meldepflichtig ist
    if daten['gefahrgut_pflicht'] == "Ja" and Schiffsdaten['gefahrgut'] != "Ja":
        return False

    # Falls das Gebiet nur für Tankschiffe gilt
    if daten['nur_tanker'] == "Ja" and Schiffsdaten['schiffstyp'] not in TANKER_TYPEN:
        return False

    # Falls das Gebiet nur bei internationaler Fahrt gilt
    if daten['nur_internationale_fahrt'] == "Ja" and Schiffsdaten['internationale_fahrt'] != "Ja":
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

print("=== ROUTE AUSWÄHLEN ===")
if rtz_dateien:
    for i, pfad in enumerate(rtz_dateien, start=1):
        print(f"  {i}) {os.path.basename(pfad)}")
    print("  0) Manuell eingeben")

    auswahl = input("\nRoute wählen (Nummer): ").strip().lstrip("﻿")
else:
    auswahl = "0"

if rtz_dateien and auswahl != "0":
    routen_name, geladene_wegpunkte = lade_rtz_route(rtz_dateien[int(auswahl) - 1])
    wegpunkte = [(lon, lat) for lon, lat, _ in geladene_wegpunkte]
    print(f"\nRoute geladen: {routen_name} ({len(wegpunkte)} Wegpunkte)")
    for lon, lat, name in geladene_wegpunkte:
        print(f"  - {name}: {lat:.5f}, {lon:.5f}")
    print()
else:
    print("\nWegpunkte eingeben (Format: Latitude Longitude, z.B. 50.5 1.0)")
    print("Leere Eingabe zum Beenden\n")

    wegpunkte = []
    nummer = 1
    while True:
        eingabe = input(f"Wegpunkt {nummer}: ")
        if eingabe == "":
            break

        lat, lon = eingabe.split()
        wegpunkte.append((float(lon), float(lat)))
        nummer += 1

testroute = LineString(wegpunkte)

# Schritt 4: Zusammenfassung der Schiffsdaten anzeigen
zusammenfassung_schiff = (
    f"Geprüft für: {Schiffsdaten['schiffstyp']}, {Schiffsdaten['gt']:.0f} GT, "
    f"Gefahrgut: {Schiffsdaten['gefahrgut']}, "
    f"internationale Fahrt: {Schiffsdaten['internationale_fahrt']}"
)

# Schritt 3: Prüfen welche Gebiete die Route kreuzt
# Ergebnisse sammeln und ausgeben
print("=== ROUTE CHECKER ===")
print(zusammenfassung_schiff)
print("Prüfe Route auf Meldepflichten...\n")

gebiete = baue_gebiete(df)
ergebnisse = []

for name, daten in gebiete.items():
    if len(daten['punkte']) >= 3:
        polygon = Polygon(daten['punkte'])
        # Geometrische Prüfung: kreuzt die Route das Gebiet?
        # UND Schiffs-Kriterien-Prüfung: passen GT/Gefahrgut/Tankertyp/Fahrtgebiet zum Schiff?
        if testroute.intersects(polygon) and erfuellt_schiffskriterien(daten, Schiffsdaten):
            freq = f"Ch {int(daten['frequenz'])}" if pd.notna(daten['frequenz']) else "siehe ADP"
            eintrag = {
                'gebiet': name,
                'typ': daten['typ'],
                'frequenz': freq
            }
            ergebnisse.append(eintrag)
            print(f"   MELDEPFLICHT: {name}")
            print(f"   Typ:          {daten['typ']}")
            print(f"   Frequenz:     {freq}")
            print(f"   Aktion:       Melden Sie sich auf {freq} beim zuständigen MRCC")
            print()

if len(ergebnisse) == 0:
    print("Keine Meldepflichten für diese Route gefunden.")

# Ergebnis als Textdatei speichern
import datetime
with open("ergebnis.txt", "w") as datei:
    datei.write("=== ROUTE CHECKER - MELDEPFLICHTEN ===\n\n")
    datei.write(f"Erstellt: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    if routen_name:
        datei.write(f"Route: {routen_name}\n")
    datei.write(f"Geprüfte Wegpunkte: {len(wegpunkte)}\n")
    datei.write(f"{zusammenfassung_schiff}\n\n")
    for e in ergebnisse:
        datei.write(f"MELDEPFLICHT: {e['gebiet']}\n")
        datei.write(f"Typ:          {e['typ']}\n")
        datei.write(f"Frequenz:     {e['frequenz']}\n")
        datei.write(f"Aktion:       Melden Sie sich auf {e['frequenz']} beim zuständigen MRCC\n")
        datei.write("\n")
       

print("=== PRÜFUNG ABGESCHLOSSEN ===")
print(f"\nErgebnis gespeichert als 'ergebnis.txt' in deinem Projektordner")
