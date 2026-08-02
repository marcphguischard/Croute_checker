import pandas as pd
from shapely.geometry import Polygon, LineString
from datetime import datetime

# CSV einlesen
df = pd.read_csv("reporting_points.csv")

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

# Route manuell eingeben
print("Wegpunkte eingeben (Format: Latitude Longitude, z.B. 50.5 1.0)")
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
    datei.write(f"Geprüfte Wegpunkte: {len(wegpunkte)}\n\n")
    for e in ergebnisse:
        datei.write(f"MELDEPFLICHT: {e['gebiet']}\n")
        datei.write(f"Typ:          {e['typ']}\n")
        datei.write(f"Frequenz:     {e['frequenz']}\n")
        datei.write(f"Aktion:       Melden Sie sich auf {e['frequenz']} beim zuständigen MRCC\n")
        datei.write("\n")
       

print("=== PRÜFUNG ABGESCHLOSSEN ===")
print(f"\nErgebnis gespeichert als 'ergebnis.txt' in deinem Projektordner")
