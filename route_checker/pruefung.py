# Zentrale Pruef-Logik: entscheidet, ob ein Gebiet fuer eine Route/ein Schiff
# eine Meldepflicht ausloest.
from shapely.geometry import LineString, Point

from .ausgabe import (
    formatiere_frequenz,
    formatiere_report_typen,
    formatiere_vorlaufzeit,
    relationship_status_label,
)
from .gebiete import baue_geometrie_fuer_gebiet, geometrie_zu_geojson
from .kategorien import TANKER_TYPEN
from .routen_import import RouteImportError

# ============================================================
# Generische S-127-Schwellenwert-Pruefung (ersetzt die vorherigen fest verdrahteten
# GT/TDW-Vergleiche). Ein Gebiet traegt EINE Schwellenwert-Bedingung
# (Threshold_Characteristic/Operator/Value/Unit); das reicht fuer alle bisherigen
# Gebiete, da nie mehr als eine Kenngroesse gleichzeitig geprueft wird.
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
    # trotzdem melden, wenn sie eingeschraenkt manoevrierfaehig sind, defekte
    # Navigationshilfen haben, oder in der TSS/ihren ITZs vor Anker liegen (ADP: "not under
    # command or at anchor in the TSS or its ITZs" / "restricted in ability to manoeuvre" /
    # "defective navigational aids" - "not under command" bewusst nicht erfragt, siehe
    # cli.frage_schiffsdaten()). Gilt nur fuer GT-Schwellen.
    if (merkmal == "gross_tonnage" and daten['gt_ausnahme'] == "Ja"
            and (Schiffsdaten['eingeschraenkt_manoevrierfaehig'] == "Yes"
                 or Schiffsdaten['defekte_navigationshilfen'] == "Yes"
                 or Schiffsdaten['anker_in_tss'] == "Yes")):
        return True

    return False


# Prueft, ob die Schiffsdaten die Melde-Kriterien eines Gebiets erfuellen
def erfuellt_schiffskriterien(daten, Schiffsdaten):
    if not erfuellt_schwellenwert(daten, Schiffsdaten):
        return False

    ist_tanker = Schiffsdaten['schiffstyp'] in TANKER_TYPEN
    hat_gefahrgut = Schiffsdaten['gefahrgut'] == "Yes"

    if daten['tanker_oder_gefahrgut'] == "Ja":
        # Manche Gebiete (z.B. SURNAV Gris-Nez) gelten fuer Tankschiffe ODER Schiffe mit
        # Gefahrgut an Bord (z.B. Containerschiffe mit IMDG-Ladung) - hier ODER statt UND.
        if not (ist_tanker or hat_gefahrgut):
            return False
    else:
        # Falls das Gebiet nur bei Gefahrgut meldepflichtig ist (Requires_IMDG: yes/no/any)
        if daten['erfordert_imdg'] == "yes" and not hat_gefahrgut:
            return False

        # Falls das Gebiet nur fuer Tankschiffe gilt
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

    # Falls das Gebiet nur bei Schweroel-/Schweroelkraftstoff-/Bitumen-Ladung gilt (z.B. WETREP)
    if daten['schweroel_pflicht'] == "Ja" and Schiffsdaten['schweroel_ladung'] != "Yes":
        return False

    # Falls das Gebiet nur bei internationaler Fahrt gilt
    if daten['nur_internationale_fahrt'] == "Ja" and Schiffsdaten['internationale_fahrt'] != "Yes":
        return False

    return True


# Bestimmt die Fahrtrichtung durch ein Gebiet (z.B. CALDOVREP), um richtungsabhaengige
# Meldekanaele korrekt zu waehlen (Ch13 Gris-Nez Traffic nordostgehend, Ch11 Channel VTS
# suedwestgehend). Berechnet dazu die echten Ein-/Austrittspunkte der Route mit dem
# Gebiets-Rand (nicht nur erster/letzter Wegpunkt der Gesamtroute, da die Route vor/nach
# der Strait noch beliebig weiterlaufen kann) und vergleicht deren Position entlang der
# Route, um die tatsaechliche Reihenfolge (Ein- vor Austritt) sicherzustellen - die
# Reihenfolge von (Multi-)Geometrie-Teilen, die Shapely bei intersection() zurueckgibt,
# folgt naemlich nicht garantiert der Fahrtrichtung.
# Rueckgabewert: "NE" (Laengengrad nimmt zu), "SW" (nimmt ab) oder None (nicht bestimmbar,
# z.B. Route beruehrt das Gebiet nur in einem Punkt).
def bestimme_richtung(testroute, gebiet_geometrie):
    schnitt = gebiet_geometrie.intersection(testroute)
    if schnitt.is_empty:
        return None

    geometrie_teile = list(schnitt.geoms) if hasattr(schnitt, "geoms") else [schnitt]
    koordinaten = []
    for teil in geometrie_teile:
        if hasattr(teil, "coords"):
            koordinaten.extend(teil.coords)

    if len(koordinaten) < 2:
        return None

    koordinaten.sort(key=lambda koord: testroute.project(Point(koord)))
    eintritt, austritt = koordinaten[0], koordinaten[-1]

    if austritt[0] > eintritt[0]:
        return "NE"
    if austritt[0] < eintritt[0]:
        return "SW"
    return None


# UK MAREP: freiwilliges Meldesystem, keine eigene Geometrie im ADP-Text (verweist nur auf
# Gebiete ausserhalb Dover Strait) - daher als pauschaler Hinweis statt als geprueftes Gebiet,
# analog zur "NACHDRUECKLICH ERMUTIGT"-Formulierung im Originaltext. Gilt fuer Handelsschiffe
# ab 300GT. MANCHEREP/OUESSREP sind die verpflichtenden Versionen ausserhalb Dover Strait -
# ohne eigene Koordinaten in den vorliegenden ADP-Texten, daher nur erwaehnt statt geprueft.
#
# UK MAREP voruebergehend ausgeblendet: soll eigentlich ueber eigene Gebiete (mit Geometrie)
# abgebildet werden statt als pauschaler Hinweis, dafuer fehlen aber noch ADP-Daten fuer die
# angrenzenden Gebiete (OUESSREP/MANCHEREP) - werden voraussichtlich in ~2 Wochen nachgereicht.
# Wieder auf True stellen, sobald diese Gebiete eingepflegt sind.
UK_MAREP_AKTIV = False


# Gibt den UK-MAREP-Hinweistext als Dict zurueck (oder None, wenn nicht anwendbar) -
# eigene Funktion statt eines geprueften Gebiets, siehe Kommentar oben.
#
# HINWEIS ZUR TEXTAENDERUNG: "see ADP" (Fallback-Frequenztext in ausgabe.py) bleibt
# unveraendert bestehen (siehe Rueckfrage/Antwort im Zuge des Phase-1-Umbaus). Hier im
# UK-MAREP-Text wird nur "source ADP texts" (main.py-Originaltext) zu "source documents"
# geaendert (Kleinkorrektur 1.2.5, eingeschraenkt auf diese eine Stelle).
def uk_marep_hinweis(Schiffsdaten):
    if not (UK_MAREP_AKTIV and Schiffsdaten['gt'] >= 300):
        return None
    return {
        'titel': "VOLUNTARY: UK MAREP",
        'text': (
            "This is a voluntary reporting system (not mandatory in this area, since "
            "CALDOVREP already covers the mandatory equivalent for the Dover Strait). "
            "All merchant ships >=300GT are strongly encouraged to participate: report to "
            "the relevant coastal station 1h before entering and again when leaving the "
            "area (POSREP/DEFREP/CHANGEREP format). Mandatory versions of this system type "
            "also apply in TSS Off Ushant (OUESSREP) and TSS Off Casquets (MANCHEREP) - both "
            "outside this tool's Dover Strait scope and without their own coordinates in the "
            "source documents, so not geometrically checked here."
        ),
    }


# Zentrale, reine Pruef-Funktion (keine Ein-/Ausgabe): prueft fuer jedes Gebiet, ob die
# Route es kreuzt (bzw. bei bedingt_inbound/outbound den relevanten Hafen anlaeuft/
# verlaesst) UND die Schiffsdaten die Kriterien erfuellen. Fasst main.py's bisherige
# Hauptschleife (vorher Zeilen ~587-678) zusammen und liefert exakt dieselben
# eintrag-Schluessel wie bisher (plus neu 'reporting_station' und
# 'geometrie_geojson' fuer die Karte in Phase 2).
def pruefe_route(Schiffsdaten, wegpunkte, gebiete):
    if len(wegpunkte) < 2:
        raise RouteImportError(
            f"Die Route hat nur {len(wegpunkte)} Wegpunkt(e) - mindestens 2 werden benoetigt."
        )

    testroute = LineString(wegpunkte)
    letzter_wegpunkt = Point(wegpunkte[-1])
    erster_wegpunkt = Point(wegpunkte[0])

    ergebnisse = []
    for name, daten in gebiete.items():
        geometrie = baue_geometrie_fuer_gebiet(daten, name)
        if geometrie is None:
            continue

        if daten['pflicht_typ'] == "bedingt_inbound":
            # "bedingt_inbound" (z.B. Dover VTS, Ramsgate): Meldepflicht gilt NUR, wenn
            # der Hafen tatsaechlich Ziel der Route ist - nicht bei reinem Durchtransit
            # durch die Naehe. Als Zielhafen gilt der letzte Wegpunkt der Route; nur wenn
            # DER innerhalb des Melde-Kreises liegt, greift die Meldepflicht - unabhaengig
            # davon, ob die Route an anderer Stelle geometrisch durch den Kreis verlaeuft.
            kreuzt = geometrie.contains(letzter_wegpunkt)
        elif daten['pflicht_typ'] == "bedingt_outbound":
            # "bedingt_outbound" (z.B. Dover VTS (Outbound), Ramsgate (Outbound)):
            # Spiegelbild von "bedingt_inbound" - Meldepflicht gilt NUR, wenn der Hafen
            # tatsaechlich AUSGANGSPUNKT der Route ist (auslaufendes Schiff), nicht bei
            # reinem Durchtransit. Als Abfahrtshafen gilt der ERSTE Wegpunkt der Route.
            kreuzt = geometrie.contains(erster_wegpunkt)
        else:
            # Normalfall: JEDE Kreuzung der Route mit dem Gebiet loest die Meldepflicht aus.
            kreuzt = testroute.intersects(geometrie)

        # Geometrische/situative Pruefung (s.o.) UND Schiffs-Kriterien-Pruefung: passen
        # GT/Gefahrgut/Tankertyp/Fahrtgebiet zum Schiff?
        if not (kreuzt and erfuellt_schiffskriterien(daten, Schiffsdaten)):
            continue

        # Richtungsabhaengige Frequenz (aktuell nur CALDOVREP: Ch13 nordostgehend,
        # Ch11 suedwestgehend) - faellt auf die normale 'frequenz' zurueck, wenn das
        # Gebiet keine Richtungsabhaengigkeit hat oder die Richtung nicht bestimmbar ist.
        frequenz_wert = daten['frequenz']
        if daten['frequenz_sw_bound'] and bestimme_richtung(testroute, geometrie) == "SW":
            frequenz_wert = daten['frequenz_sw_bound']
        freq = formatiere_frequenz(frequenz_wert)

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
            'reporting_station': daten['reporting_station'],
            'geometrie_geojson': geometrie_zu_geojson(geometrie),
        }
        ergebnisse.append(eintrag)

    return ergebnisse
