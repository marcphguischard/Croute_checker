# Interaktive Kommandozeilen-Bedienung des Route Checkers (bisher main.py).
# Nutzt ausschliesslich das route_checker-Paket fuer die eigentliche Logik -
# main.py ist nur noch ein duenner Wrapper, der main() hier aufruft.
import glob
import os
import textwrap
from datetime import datetime  # Kleinkorrektur 1.2.1: einheitlicher Import, kein zweiter
                                # "import datetime" mehr (ueberschrieb diesen vorher lokal)

from route_checker.ausgabe import erzeuge_textbericht, formatiere_action_zeile, formatiere_schiffszusammenfassung
from route_checker.gebiete import lade_gebiete
from route_checker.kategorien import (
    CATEGORY_OF_CARGO,
    CATEGORY_OF_DANGEROUS_CARGO,
    CATEGORY_OF_VESSEL,
)
from route_checker.pruefung import pruefe_route, uk_marep_hinweis
from route_checker.routen_import import (
    RouteImportError,
    lade_gpx_route,
    lade_rtz_route,
)


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

    # 2. Ladungstyp (categoryOfCargo) - beschreibt die Hauptladung. Bewusst UNABHAENGIG von
    #    der Gefahrgut-Frage unten: ein Schiff kann z.B. Bulk-Ladung UND zusaetzlich
    #    Gefahrgut an Bord haben, "dangerous or hazardous" als Ladungstyp ist nur EINE
    #    mögliche Haupt-Einordnung, kein Ausschlusskriterium fuer die anderen Typen.
    ladungstyp_code = frage_auswahl_code("Cargo type", CATEGORY_OF_CARGO)

    # 3. Gefahrgut an Bord: eigene, vom Ladungstyp unabhaengige Ja/Nein-Frage
    gefahrgut = frage_ja_nein("Dangerous goods on board")

    # 3b. IMDG-Klasse(n) (categoryOfDangerousOrHazardousCargo) - nur bei Gefahrgut = Ja
    imdg_codes = []
    if gefahrgut == "Yes":
        imdg_codes = frage_auswahl_codes_mehrfach("IMDG class(es)", CATEGORY_OF_DANGEROUS_CARGO)
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
    # route_checker.pruefung.erfuellt_schwellenwert()). "Not under command" wird bewusst
    # NICHT gefragt, da das nicht planbar ist (tritt unerwartet ein) - eingeschraenkte
    # Manoevrierfaehigkeit kann dagegen auch planmaessig vorliegen (z.B. Schleppverband,
    # Baggerarbeiten). "At anchor in der TSS/ihren ITZs" ist der dritte im ADP-Text genannte
    # Ausnahmegrund (neben "not under command", das wie oben begruendet bewusst ausgelassen
    # wird) und IST planbar/erfragbar.
    eingeschraenkt_manoevrierfaehig = frage_ja_nein("Restricted in ability to manoeuvre")
    defekte_navigationshilfen = frage_ja_nein("Defective navigational aids")
    anker_in_tss = frage_ja_nein("At anchor within the Dover Strait TSS or its Inshore Traffic Zones (ITZs)")

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
        "anker_in_tss": anker_in_tss,
        "vessel_registry": vessel_registry,
        "in_ballast": in_ballast,
        "government_non_commercial": regierungsschiff,
    }
    print()
    return Schiffsdaten


# Route auswaehlen: aus RTZ-/GPX-Datei importieren oder manuell eingeben.
# Gibt (routen_name, wegpunkte als [(lon, lat), ...]) zurueck, oder wirft
# RouteImportError bei einer kaputten Datei bzw. zu wenigen Wegpunkten
# (Kleinkorrektur 1.2.3 - main.py ist vorher hier abgestuerzt).
def waehle_route():
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

        if len(wegpunkte) < 2:
            raise RouteImportError(
                f"Nur {len(wegpunkte)} Wegpunkt(e) eingegeben - mindestens 2 werden benoetigt."
            )

    return routen_name, wegpunkte


# Druckt den UK-MAREP-Hinweis auf der Konsole (aktuell inaktiv, UK_MAREP_AKTIV=False -
# dieser Zweig laeuft derzeit nie, siehe route_checker.pruefung). Nutzt denselben Text
# wie erzeuge_textbericht() (dort als ein durchgehender Absatz geschrieben), fuer die
# Konsole hier mit textwrap zeilenumgebrochen statt main.py's vorher fest verdrahteten
# Zeilenumbruechen - inhaltlich identisch, nur die Umbruchstellen koennen abweichen.
def drucke_uk_marep_hinweis(hinweis):
    print(f"   {hinweis['titel']}")
    for zeile in textwrap.wrap(hinweis['text'], width=75):
        print(f"   {zeile}")
    print()


def main():
    # Schritt 1: Schiffsdaten am Programmstart abfragen (vor der Routenprüfung)
    Schiffsdaten = frage_schiffsdaten()

    # Schritt 2: Route auswaehlen
    try:
        routen_name, wegpunkte = waehle_route()
    except RouteImportError as fehler:
        print(f"\nError: {fehler}")
        return

    # Schritt 3: Gebiete laden, Route pruefen
    gebiete = lade_gebiete()

    zusammenfassung_schiff = formatiere_schiffszusammenfassung(Schiffsdaten)
    print("=== ROUTE CHECKER ===")
    print(zusammenfassung_schiff)
    print("Checking route for reporting obligations...\n")

    try:
        ergebnisse = pruefe_route(Schiffsdaten, wegpunkte, gebiete)
    except RouteImportError as fehler:
        print(f"\nError: {fehler}")
        return

    for e in ergebnisse:
        print(f"   {e['status_label']}: {e['gebiet']}")
        print(f"   Type:          {e['typ']}")
        print(f"   Frequency:     {e['frequenz']}")
        print(f"   Action:        {formatiere_action_zeile(e)}")
        if e['meldeinhalt']:
            print(f"   Report content: {e['meldeinhalt']}")
        if e['dauerpflicht']:
            print(f"   Continuous watch/duty: {e['dauerpflicht']}")
        if e['faehre_hinweis']:
            print(f"   Ferry note:    {e['faehre_hinweis']}")
        if e['lng_hinweis']:
            print(f"   LNG note:      {e['lng_hinweis']}")
        if e['report_typen_text']:
            print(f"   Report type(s): {e['report_typen_text']}")
        if e['vorlaufzeit_text']:
            print(f"   Notice:        {e['vorlaufzeit_text']}")
        if e['source_reference']:
            print(f"   Source:        {e['source_reference']}")
        print()

    if len(ergebnisse) == 0:
        print("No reporting obligations found for this route.")

    hinweis = uk_marep_hinweis(Schiffsdaten)
    if hinweis is not None:
        drucke_uk_marep_hinweis(hinweis)

    # Ergebnis als Textdatei speichern
    jetzt = datetime.now()
    bericht = erzeuge_textbericht(Schiffsdaten, routen_name, wegpunkte, ergebnisse, jetzt, hinweis)
    # Kleinkorrektur 1.2.2: encoding="utf-8" explizit setzen (main.py ist vorher unter
    # Windows bei Sonderzeichen wie "³" abgestuerzt, da open() sonst die System-Codepage
    # verwendet).
    with open("ergebnis.txt", "w", encoding="utf-8") as datei:
        datei.write(bericht)

    print("=== CHECK COMPLETE ===")
    print("\nResult saved as 'ergebnis.txt' in your project folder")


if __name__ == "__main__":
    main()
