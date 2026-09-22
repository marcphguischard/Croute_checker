# Die 18 Plausibilitaetsfaelle aus testprotokoll_plausibilitaet.txt (A1-F2),
# gegen die ECHTE reporting_points.csv (nicht gegen synthetische Test-
# Geometrie), da die erwarteten Ergebnisse an reale Gebietsgrenzen/-mittel-
# punkte gebunden sind (z.B. Dover 51.1175/1.33567, Ramsgate 51.32517/1.45483).
#
# WICHTIG (siehe Auftrag): Die erwarteten Ergebnisse kommen 1:1 aus dem
# Testprotokoll, nicht aus der aktuellen Programmausgabe. Weicht ein Testfall
# ab, wird das gemeldet statt den Test oder den Code stillschweigend
# anzupassen.
import os

import pytest

from route_checker.gebiete import lade_gebiete
from route_checker.kategorien import CATEGORY_OF_CARGO, CATEGORY_OF_VESSEL
from route_checker.pruefung import pruefe_route
from route_checker.routen_import import lade_rtz_route

ROUTEN_ORDNER = os.path.join(os.path.dirname(__file__), "routes")

VESSEL_CODE = {v: k for k, v in CATEGORY_OF_VESSEL.items()}
CARGO_CODE = {v: k for k, v in CATEGORY_OF_CARGO.items()}


@pytest.fixture(scope="module")
def gebiete():
    # Echte CSV, einmal pro Testmodul geladen (nicht pro Testfall).
    return lade_gebiete()


def _route(dateiname):
    _name, wegpunkte_mit_namen = lade_rtz_route(os.path.join(ROUTEN_ORDNER, dateiname))
    return [(lon, lat) for lon, lat, _name in wegpunkte_mit_namen]


# Baut ein vollstaendiges Schiffsdaten-Dict (wie cli.frage_schiffsdaten()) mit
# plausiblen Defaults ("Standard-Frachter" laut Testprotokoll-Teil A), das
# gezielt ueberschrieben werden kann.
def _schiff(schiffstyp="General cargo vessel", cargo="General", gt=5000, tdw=5000, loa=150,
            draught=10, gefahrgut="No", imdg_classes=None, schweroel_ladung="No",
            internationale_fahrt="No", government_non_commercial="No",
            eingeschraenkt_manoevrierfaehig="No", defekte_navigationshilfen="No",
            anker_in_tss="No", vessel_registry="domestic", in_ballast="No",
            sondertransport="No", personen_an_bord=20):
    return {
        "schiffstyp": schiffstyp,
        "category_of_vessel_code": VESSEL_CODE[schiffstyp],
        "category_of_cargo_code": CARGO_CODE[cargo],
        "category_of_cargo": cargo,
        "imdg_classes": imdg_classes or [],
        "gt": gt,
        "tdw": tdw,
        "loa": loa,
        "draught": draught,
        "internationale_fahrt": internationale_fahrt,
        "gefahrgut": gefahrgut,
        "imdg_klasse": "",
        "schweroel_ladung": schweroel_ladung,
        "personen_an_bord": personen_an_bord,
        "sondertransport": sondertransport,
        "eingeschraenkt_manoevrierfaehig": eingeschraenkt_manoevrierfaehig,
        "defekte_navigationshilfen": defekte_navigationshilfen,
        "anker_in_tss": anker_in_tss,
        "vessel_registry": vessel_registry,
        "in_ballast": in_ballast,
        "government_non_commercial": government_non_commercial,
    }


def _gebietsnamen(ergebnisse):
    return sorted(e["gebiet"] for e in ergebnisse)


# ============================================================
# TEIL A: reine Geometrie-Tests (Standard-Frachter, 5000 GT, kein Gefahrgut)
# ============================================================

def test_a1_route_klar_durch_caldovrep(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a1_caldovrep.rtz"), gebiete)
    assert "DS CALDOVREP" in _gebietsnamen(ergebnisse)


def test_a2_route_klar_ausserhalb_aller_gebiete(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a2_ausserhalb.rtz"), gebiete)
    assert _gebietsnamen(ergebnisse) == []


def test_a3_route_durch_calais_vts(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a3_calais_vts.rtz"), gebiete)
    assert "Calais VTS (blau)" in _gebietsnamen(ergebnisse)


def test_a4_route_durch_dunkirk_vts(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a4_dunkirk_vts.rtz"), gebiete)
    assert "Dunkirk VTS" in _gebietsnamen(ergebnisse)


def test_a5_route_durch_mehrere_gebiete_gleichzeitig(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a5_mehrere_gebiete.rtz"), gebiete)
    namen = _gebietsnamen(ergebnisse)
    assert "DS CALDOVREP" in namen
    assert "Calais VTS (blau)" in namen
    assert "Dunkirk VTS" in namen


# ============================================================
# TEIL B: GT-Schwellen-Tests (Geometrie konstant: Route A1)
# ============================================================

def test_b1_schiff_genau_auf_der_schwelle_300gt(gebiete):
    ergebnisse = pruefe_route(_schiff(gt=300), _route("test_a1_caldovrep.rtz"), gebiete)
    assert "DS CALDOVREP" in _gebietsnamen(ergebnisse)


def test_b2_schiff_knapp_unter_der_schwelle_299gt(gebiete):
    ergebnisse = pruefe_route(_schiff(gt=299), _route("test_a1_caldovrep.rtz"), gebiete)
    assert "DS CALDOVREP" not in _gebietsnamen(ergebnisse)


def test_b3_grosses_containerschiff(gebiete):
    ergebnisse = pruefe_route(
        _schiff(schiffstyp="Container carrier", cargo="Container", gt=45000),
        _route("test_a1_caldovrep.rtz"), gebiete,
    )
    assert "DS CALDOVREP" in _gebietsnamen(ergebnisse)


# ============================================================
# TEIL C: ladungsabhaengige Systeme (SURNAV, WETREP)
# ============================================================

def test_c1_surnav_route_ohne_gefahrgut(gebiete):
    schiff = _schiff(gt=10000, tdw=10000, gefahrgut="No", schweroel_ladung="No")
    ergebnisse = pruefe_route(schiff, _route("test_c1c2_surnav.rtz"), gebiete)
    assert "SURNAV Gris-Nez" not in _gebietsnamen(ergebnisse)


def test_c2_gleiche_route_mit_gefahrgut(gebiete):
    # IMDG Klasse 3 = "Class 3" laut CATEGORY_OF_DANGEROUS_CARGO (Code 10)
    schiff = _schiff(gt=10000, tdw=10000, gefahrgut="Yes", imdg_classes=[10])
    ergebnisse = pruefe_route(schiff, _route("test_c1c2_surnav.rtz"), gebiete)
    assert "SURNAV Gris-Nez" in _gebietsnamen(ergebnisse)


def test_c3_wetrep_relevanter_kanalbereich(gebiete):
    schiff = _schiff(schiffstyp="Tanker", cargo="Liquid", tdw=800, schweroel_ladung="Yes")
    ergebnisse = pruefe_route(schiff, _route("test_c3c4c5_wetrep.rtz"), gebiete)
    assert "WETREP" in _gebietsnamen(ergebnisse)


def test_c4_gleiche_route_aber_kein_oeltanker(gebiete):
    schiff = _schiff(gt=10000, tdw=10000, schweroel_ladung="No")
    ergebnisse = pruefe_route(schiff, _route("test_c3c4c5_wetrep.rtz"), gebiete)
    assert "WETREP" not in _gebietsnamen(ergebnisse)


def test_c5_oeltanker_mit_leichtem_statt_schwerem_oel(gebiete):
    # Dichte 850kg/m³ liegt UNTER der 900kg/m³-Schwelle aus der Frage
    # "Heavy fuel oil cargo (density >900kg/m³ ...)" - die richtige Antwort
    # auf diese Ja/Nein-Frage ist deshalb "No", nicht die Dichte selbst.
    schiff = _schiff(schiffstyp="Tanker", cargo="Liquid", tdw=800, schweroel_ladung="No")
    ergebnisse = pruefe_route(schiff, _route("test_c3c4c5_wetrep.rtz"), gebiete)
    assert "WETREP" not in _gebietsnamen(ergebnisse)


# ============================================================
# TEIL D: Zielhafen-Erkennung (Dover, Ramsgate)
# ============================================================

def test_d1_route_mit_zielhafen_dover(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_d1_dover_zielhafen.rtz"), gebiete)
    namen = _gebietsnamen(ergebnisse)
    assert "DS CALDOVREP" in namen
    assert "Dover VTS" in namen


def test_d2_route_verlaeuft_nur_durch_dover_kreis_ziel_liegt_woanders(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_d2_dover_durchtransit.rtz"), gebiete)
    assert "Dover VTS" not in _gebietsnamen(ergebnisse)


def test_d3_route_mit_zielhafen_ramsgate(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_d3_ramsgate_zielhafen.rtz"), gebiete)
    assert "Ramsgate" in _gebietsnamen(ergebnisse)


# ============================================================
# TEIL E: Meldeinhalt-Plausibilitaet (reiner Textvergleich)
# ============================================================

def test_e1_caldovrep_meldeinhalt_basierend_auf_a1(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_a1_caldovrep.rtz"), gebiete)
    caldovrep = next(e for e in ergebnisse if e["gebiet"] == "DS CALDOVREP")
    erwartete_felder = ["A:", "B:", "C/D:", "E:", "F:", "G:", "I:", "O:", "P:", "Q/R:", "T:", "W:", "X:"]
    for feld in erwartete_felder:
        assert feld in caldovrep["meldeinhalt"], f"Feld {feld} fehlt im CALDOVREP-Meldeinhalt"


def test_e2_surnav_meldeinhalt_basierend_auf_c2(gebiete):
    # HINWEIS: Das Testprotokoll prueft hier die SURNAV-FRANCE-Buchstabencodes
    # A,B,C,E,F,G,H,I,K,M,O,P,Q,U,X,Z. Der Meldeinhalt-Text in der CSV ist fuer
    # SURNAV (anders als CALDOVREP/WETREP) aber als FLIESSTEXT ohne Buchstaben-
    # Codes hinterlegt ("Ship name/call sign/flag, date/time, position, ...").
    # Eine automatisierte Pruefung auf einzelne Buchstaben ("A:", "B:", ...) ist
    # daher NICHT moeglich, ohne die Buchstaben-Bedeutung selbst zu erraten
    # (Buchstaben-Codes sind je Meldesystem unterschiedlich belegt) - das wird
    # bewusst nicht getan. Dieser Test prueft nur, dass der Text vorhanden und
    # nicht leer ist; der inhaltliche Soll-Ist-Abgleich gegen die 16 Buchstaben
    # bleibt ein manuell zu pruefender, offener Punkt (siehe Abschlussbericht).
    schiff = _schiff(gt=10000, tdw=10000, gefahrgut="Yes", imdg_classes=[10])
    ergebnisse = pruefe_route(schiff, _route("test_c1c2_surnav.rtz"), gebiete)
    surnav = next(e for e in ergebnisse if e["gebiet"] == "SURNAV Gris-Nez")
    assert surnav["meldeinhalt"].startswith("SURNAV-FRANCE:")
    assert len(surnav["meldeinhalt"]) > 50


def test_e3_wetrep_meldeinhalt_basierend_auf_c3(gebiete):
    # HINWEIS: Das Testprotokoll verlangt hier, dass NUR die Sailing-Plan-
    # Felder (A,B,C,E,F,G,I,P,T,W,X) ausgegeben werden, NICHT die reduzierten
    # Felder von Final Report/Deviation Report. Der Meldeinhalt-Text in der
    # CSV listet aber alle Felder aller drei WETREP-Berichtstypen als EINE
    # gemeinsame, undifferenzierte Liste (inkl. Feld Q, das im Testprotokoll
    # fuer den Sailing-Plan-Fall nicht erwartet wird) - eine Differenzierung
    # "welches Feld gilt fuer welchen Berichtstyp" findet im Text nicht statt.
    # Dieser Test prueft deshalb nur, dass die im Protokoll fuer den Sailing
    # Plan erwarteten Felder VORKOMMEN (notwendige, aber nicht hinreichende
    # Bedingung) - die fehlende Differenzierung ist ein offener Punkt (siehe
    # Abschlussbericht).
    schiff = _schiff(schiffstyp="Tanker", cargo="Liquid", tdw=800, schweroel_ladung="Yes")
    ergebnisse = pruefe_route(schiff, _route("test_c3c4c5_wetrep.rtz"), gebiete)
    wetrep = next(e for e in ergebnisse if e["gebiet"] == "WETREP")
    erwartete_felder = ["A:", "B:", "C:", "E:", "F:", "G:", "I:", "P:", "T:", "W:", "X:"]
    for feld in erwartete_felder:
        assert feld in wetrep["meldeinhalt"], f"Feld {feld} fehlt im WETREP-Meldeinhalt"


# ============================================================
# TEIL F: Negativbeispiel / Grenzfall-Test
# ============================================================

def test_f1_route_knapp_ausserhalb_von_caldovrep(gebiete):
    ergebnisse = pruefe_route(_schiff(), _route("test_f1_knapp_ausserhalb.rtz"), gebiete)
    assert "DS CALDOVREP" not in _gebietsnamen(ergebnisse)


def test_f2_regierungsschiff_ausnahme_bei_wetrep(gebiete):
    # HINWEIS zur Interpretation (siehe Abschlussbericht): Das Testprotokoll
    # beschreibt das Schiffsprofil nur als "Marineschiff/Regierungsschiff im
    # nicht-kommerziellen Dienst", ohne categoryOfVessel festzulegen. Hier
    # wird dafuer "Warship" verwendet (die dafuer vorgesehene S-127-Kategorie).
    # Das fuehrt dazu, dass WETREP bereits ueber die Schiffstyp-Einschraenkung
    # (Applicable_Vessel_Types={Tanker, LNG tanker}) ausgeschlossen wird - die
    # Regierungsschiff-Ausnahme (Government_Vessel_Exempt) selbst wird durch
    # diesen Testfall NICHT isoliert geprueft. Erwartetes Ergebnis (keine
    # WETREP-Pflicht) stimmt trotzdem mit dem Protokoll ueberein.
    schiff = _schiff(schiffstyp="Warship", cargo="General", government_non_commercial="Yes")
    ergebnisse = pruefe_route(schiff, _route("test_c3c4c5_wetrep.rtz"), gebiete)
    assert "WETREP" not in _gebietsnamen(ergebnisse)
