# Tests fuer route_checker.pruefung.erfuellt_schwellenwert(): jeder Operator
# aus THRESHOLD_VERGLEICH, die CALDOVREP-Ausnahme unter 300 GT (alle drei
# Ausnahmegruende einzeln) und der Fall "kein Schwellenwert definiert".
import pytest

from route_checker.pruefung import erfuellt_schwellenwert


def _gebiet(merkmal="gross_tonnage", operator="greater_than_or_equal", wert=300.0, gt_ausnahme="Nein"):
    return {
        'schwellenwert_merkmal': merkmal,
        'schwellenwert_operator': operator,
        'schwellenwert_wert': wert,
        'gt_ausnahme': gt_ausnahme,
    }


def _schiff(gt=0, tdw=0, loa=0, draught=0, eingeschraenkt_manoevrierfaehig="No",
            defekte_navigationshilfen="No", anker_in_tss="No"):
    return {
        'gt': gt, 'tdw': tdw, 'loa': loa, 'draught': draught,
        'eingeschraenkt_manoevrierfaehig': eingeschraenkt_manoevrierfaehig,
        'defekte_navigationshilfen': defekte_navigationshilfen,
        'anker_in_tss': anker_in_tss,
    }


@pytest.mark.parametrize("operator, schiffswert, schwellenwert, erwartet", [
    ("greater_than", 101, 100, True),
    ("greater_than", 100, 100, False),
    ("greater_than_or_equal", 100, 100, True),
    ("greater_than_or_equal", 99, 100, False),
    ("less_than", 99, 100, True),
    ("less_than", 100, 100, False),
    ("less_than_or_equal", 100, 100, True),
    ("less_than_or_equal", 101, 100, False),
    ("equal_to", 100, 100, True),
    ("equal_to", 101, 100, False),
    ("not_equal_to", 101, 100, True),
    ("not_equal_to", 100, 100, False),
])
def test_jeder_operator(operator, schiffswert, schwellenwert, erwartet):
    gebiet = _gebiet(operator=operator, wert=schwellenwert)
    schiff = _schiff(gt=schiffswert)
    assert erfuellt_schwellenwert(gebiet, schiff) is erwartet


def test_kein_schwellenwert_definiert_immer_true():
    gebiet = _gebiet(merkmal="", operator="", wert=None)
    schiff = _schiff(gt=0)
    assert erfuellt_schwellenwert(gebiet, schiff) is True


def test_caldovrep_ausnahme_unter_300gt_ohne_sonderstatus_greift_nicht():
    gebiet = _gebiet(gt_ausnahme="Ja")
    schiff = _schiff(gt=299)
    assert erfuellt_schwellenwert(gebiet, schiff) is False


def test_caldovrep_ausnahme_eingeschraenkt_manoevrierfaehig():
    gebiet = _gebiet(gt_ausnahme="Ja")
    schiff = _schiff(gt=299, eingeschraenkt_manoevrierfaehig="Yes")
    assert erfuellt_schwellenwert(gebiet, schiff) is True


def test_caldovrep_ausnahme_defekte_navigationshilfen():
    gebiet = _gebiet(gt_ausnahme="Ja")
    schiff = _schiff(gt=299, defekte_navigationshilfen="Yes")
    assert erfuellt_schwellenwert(gebiet, schiff) is True


def test_caldovrep_ausnahme_anker_in_tss():
    gebiet = _gebiet(gt_ausnahme="Ja")
    schiff = _schiff(gt=299, anker_in_tss="Yes")
    assert erfuellt_schwellenwert(gebiet, schiff) is True


def test_caldovrep_ausnahme_greift_nicht_ohne_gt_ausnahme_flag():
    # Gebiet OHNE gt_ausnahme="Ja" (z.B. Calais/Dunkirk VTS) -> die drei
    # Sonderstatus duerfen die Schwelle NICHT aushebeln.
    gebiet = _gebiet(gt_ausnahme="Nein")
    schiff = _schiff(gt=299, eingeschraenkt_manoevrierfaehig="Yes")
    assert erfuellt_schwellenwert(gebiet, schiff) is False
