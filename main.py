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
                'frequenz': reihe['Frequenz']
            }
        
        # Koordinaten zum aktuellen Gebiet hinzufügen
        if aktuelles_gebiet and pd.notna(reihe['Lat. Grad in Dezimal']):
            lat = reihe['Lat. Grad in Dezimal']
            lon = reihe['Long. Grad in Dezimal']
            if lat > 1:  # Leere Zeilen filtern
                gebiete[aktuelles_gebiet]['punkte'].append((lon, lat))
    
    return gebiete

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

# Schritt 3: Prüfen welche Gebiete die Route kreuzt
# Ergebnisse sammeln und ausgeben
print("=== ROUTE CHECKER ===")
print("Prüfe Route auf Meldepflichten...\n")

gebiete = baue_gebiete(df)
ergebnisse = []

for name, daten in gebiete.items():
    if len(daten['punkte']) >= 3:
        polygon = Polygon(daten['punkte'])
        if testroute.intersects(polygon):
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
            print("✅ Keine Meldepflichten für diese Route gefunden.")

# Ergebnis als Textdatei speichern
import datetime
with open("ergebnis.txt", "w") as datei:
    datei.write("=== ROUTE CHECKER - MELDEPFLICHTEN ===\n\n")
    datei.write(f"Erstellt: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    if routen_name:
        datei.write(f"Route: {routen_name}\n")
    datei.write(f"Geprüfte Wegpunkte: {len(wegpunkte)}\n\n")
    for e in ergebnisse:
        datei.write(f"MELDEPFLICHT: {e['gebiet']}\n")
        datei.write(f"Typ:          {e['typ']}\n")
        datei.write(f"Frequenz:     {e['frequenz']}\n")
        datei.write(f"Aktion:       Melden Sie sich auf {e['frequenz']} beim zuständigen MRCC\n")
        datei.write("\n")
       

print("=== PRÜFUNG ABGESCHLOSSEN ===")
print(f"\nErgebnis gespeichert als 'ergebnis.txt' in deinem Projektordner")
