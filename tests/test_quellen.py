# Tests fuer den Primaerquellen-Nachweis (Primary_Source_*/Verification_*-
# Spalten in reporting_points.csv) und die zugehoerige Anzeige-Logik in
# route_checker.ausgabe.formatiere_quellenanzeige().
#
# WICHTIG: Diese Tests duerfen nicht fehlschlagen, solange die neuen Felder
# leer sind (Ist-Zustand) - sie pruefen nur die Konsistenz GEFUELLTER Angaben.
import csv
import sys
from pathlib import Path

PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
CSV_PFAD = PROJEKT_WURZEL / "reporting_points.csv"

sys.path.insert(0, str(PROJEKT_WURZEL / "scripts"))
from pruefe_quellen import ERLAUBTE_STATUS  # noqa: E402  (source of truth, keine Doppelpflege)

from route_checker.ausgabe import formatiere_quellenanzeige  # noqa: E402

NEUE_SPALTEN = [
    "Primary_Source_Type",
    "Primary_Source_Reference",
    "Primary_Source_Date",
    "Primary_Source_URL",
    "Verification_Status",
    "Verification_Date",
]


def _gebietszeilen():
    with open(CSV_PFAD, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [zeile for zeile in reader if zeile["Gebiet"].strip()]


def test_neue_spalten_existieren_im_header():
    with open(CSV_PFAD, newline="", encoding="utf-8-sig") as f:
        header = next(csv.reader(f))
    for spalte in NEUE_SPALTEN:
        assert spalte in header


def test_jede_gebietszeile_hat_alle_neuen_spalten():
    for zeile in _gebietszeilen():
        for spalte in NEUE_SPALTEN:
            # Spalte muss existieren (auch wenn ihr Wert eine leere Zelle ist -
            # csv.DictReader liefert dann "").
            assert spalte in zeile, f"{zeile['Gebiet']}: Spalte {spalte} fehlt"


def test_verification_status_nur_erlaubte_werte_wenn_gefuellt():
    for zeile in _gebietszeilen():
        status = zeile["Verification_Status"].strip()
        if status:
            assert status in ERLAUBTE_STATUS, (
                f"{zeile['Gebiet']}: Verification_Status '{status}' ist nicht erlaubt "
                f"(erlaubt: {', '.join(ERLAUBTE_STATUS)})"
            )


def test_verified_hat_referenz_und_beide_datumsfelder():
    for zeile in _gebietszeilen():
        if zeile["Verification_Status"].strip() == "verified":
            for spalte in ("Primary_Source_Reference", "Primary_Source_Date", "Verification_Date"):
                assert zeile[spalte].strip(), (
                    f"{zeile['Gebiet']}: Status 'verified', aber {spalte} ist leer"
                )


def test_anzeige_primaerquelle_vor_source_reference():
    assert formatiere_quellenanzeige("ADP-Text", "IMO Resolution X", "verified") == "IMO Resolution X"


def test_anzeige_fallback_auf_source_reference_ohne_primaerquelle():
    assert formatiere_quellenanzeige("ADP-Text", "", "") == "ADP-Text"


def test_anzeige_open_oder_candidate_haengt_unverified_hinweis_an():
    for status in ("open", "candidate"):
        text = formatiere_quellenanzeige("ADP-Text", "IMO Resolution X", status)
        assert text == "IMO Resolution X (source not yet verified)"


def test_anzeige_no_public_source_haengt_entsprechenden_hinweis_an():
    text = formatiere_quellenanzeige("ADP-Text", "", "no_public_source")
    assert text == "ADP-Text (no public primary source; based on nautical publications)"


def test_anzeige_verified_ohne_zusatzhinweis():
    text = formatiere_quellenanzeige("ADP-Text", "IMO Resolution X", "verified")
    assert "(" not in text
