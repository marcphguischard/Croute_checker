# Tests fuer die Flask-Web-Oberflaeche (web/app.py) mit dem Flask-Test-Client.
import io

import pytest

from route_checker.gebiete import lade_gebiete
from route_checker.kategorien import CATEGORY_OF_CARGO, CATEGORY_OF_VESSEL
from route_checker.pruefung import pruefe_route
from route_checker.routen_import import lade_rtz_route
from web.app import app as flask_app


@pytest.fixture
def client():
    flask_app.testing = True
    return flask_app.test_client()


# Vollstaendiges, gueltiges Formular ("Standard-Frachter" wie im Testprotokoll
# Teil A) - einzelne Felder per **overrides ueberschreibbar.
def _schiff_formular(**overrides):
    basis = {
        "schiffstyp_code": "1",
        "cargo_code": "3",
        "gefahrgut": "No",
        "gt": "5000",
        "tdw": "5000",
        "loa": "150",
        "draught": "10",
        "schweroel_ladung": "No",
        "vessel_registry": "domestic",
        "in_ballast": "No",
        "government_non_commercial": "No",
        "internationale_fahrt": "No",
        "personen_an_bord": "20",
        "sondertransport": "No",
        "eingeschraenkt_manoevrierfaehig": "No",
        "defekte_navigationshilfen": "No",
        "anker_in_tss": "No",
    }
    basis.update(overrides)
    return basis


def test_startseite_laedt(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Ship type" in html
    assert "Prototype for research purposes" in html


def test_upload_liefert_erwartete_gebiete(client):
    # Erwartung NICHT hart codiert, sondern direkt aus pruefe_route() (single
    # source of truth) berechnet - keine Doppelpflege der Erwartung.
    pfad = "tests/routes/test_a1_caldovrep.rtz"
    with open(pfad, "rb") as f:
        rtz_bytes = f.read()

    formular = _schiff_formular()
    formular["route_file"] = (io.BytesIO(rtz_bytes), "test_a1_caldovrep.rtz")
    resp = client.post("/check", data=formular, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    _name, wegpunkte_mit_namen = lade_rtz_route(pfad)
    wegpunkte = [(lon, lat) for lon, lat, _n in wegpunkte_mit_namen]
    schiffsdaten = {
        "schiffstyp": CATEGORY_OF_VESSEL[1],
        "category_of_vessel_code": 1,
        "category_of_cargo_code": 3,
        "category_of_cargo": CATEGORY_OF_CARGO[3],
        "imdg_classes": [],
        "gt": 5000.0, "tdw": 5000.0, "loa": 150.0, "draught": 10.0,
        "internationale_fahrt": "No", "gefahrgut": "No", "imdg_klasse": "",
        "schweroel_ladung": "No", "personen_an_bord": 20, "sondertransport": "No",
        "eingeschraenkt_manoevrierfaehig": "No", "defekte_navigationshilfen": "No",
        "anker_in_tss": "No", "vessel_registry": "domestic", "in_ballast": "No",
        "government_non_commercial": "No",
    }
    erwartete_ergebnisse = pruefe_route(schiffsdaten, wegpunkte, lade_gebiete())
    assert erwartete_ergebnisse, "Testroute A1 sollte laut Testprotokoll Meldepflichten ausloesen"
    for eintrag in erwartete_ergebnisse:
        assert eintrag["gebiet"] in html


def test_kaputte_datei_liefert_fehlermeldung_kein_500er(client):
    formular = _schiff_formular()
    formular["route_file"] = (io.BytesIO(b"das ist keine XML-Datei"), "kaputt.rtz")
    resp = client.post("/check", data=formular, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True).lower()
    assert "error" in html or "konnte" in html


def test_falsches_dateiformat_liefert_fehlermeldung(client):
    formular = _schiff_formular()
    formular["route_file"] = (io.BytesIO(b"irgendein Text"), "route.txt")
    resp = client.post("/check", data=formular, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True).lower()
    assert "unsupported file type" in html


def test_weniger_als_2_wegpunkte_liefert_fehlermeldung(client):
    rtz_ein_punkt = (
        '<?xml version="1.0"?>'
        '<route xmlns="http://www.cirm.org/RTZ/1/1">'
        '<routeInfo routeName="Nur ein Punkt" />'
        '<waypoints>'
        '<waypoint id="1" name="WP1"><position lat="51.0" lon="1.0" /></waypoint>'
        '</waypoints></route>'
    )
    formular = _schiff_formular()
    formular["route_file"] = (io.BytesIO(rtz_ein_punkt.encode("utf-8")), "einpunkt.rtz")
    resp = client.post("/check", data=formular, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True).lower()
    assert "wegpunkt" in html or "waypoint" in html


def test_fehlende_datei_redirectet_mit_fehlermeldung(client):
    formular = _schiff_formular()
    resp = client.post("/check", data=formular, content_type="multipart/form-data")
    assert resp.status_code == 302


def test_ungueltige_schiffsdaten_redirectet_statt_500er(client):
    formular = _schiff_formular(gt="nicht-numerisch")
    formular["route_file"] = (io.BytesIO(b"egal"), "egal.rtz")
    resp = client.post("/check", data=formular, content_type="multipart/form-data")
    assert resp.status_code == 302


def test_api_areas_liefert_geojson_fuer_alle_gebiete(client):
    resp = client.get("/api/areas")
    assert resp.status_code == 200
    daten = resp.get_json()
    assert daten["type"] == "FeatureCollection"
    assert len(daten["features"]) == len(lade_gebiete())
    for feature in daten["features"]:
        assert feature["geometry"]["type"] in ("Polygon", "LineString")
        assert feature["properties"]["name"]
