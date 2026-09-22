# Tests fuer route_checker.gebiete: Kreisgeometrie (baue_kreis_geometrie) und
# Fahrtrichtungs-Erkennung (route_checker.pruefung.bestimme_richtung).
from math import cos, radians

from shapely.geometry import LineString, Point, Polygon

from route_checker.gebiete import baue_kreis_geometrie
from route_checker.pruefung import bestimme_richtung

MITTELPUNKT_LON, MITTELPUNKT_LAT = 1.0, 51.0
RADIUS_NM = 3.0


def _punkt_oestlich(distanz_nm):
    # Punkt genau `distanz_nm` oestlich des Testkreis-Mittelpunkts (gleiche
    # Breite, laengengrad-Versatz ueber den Breitengrad-Korrekturfaktor
    # berechnet - dieselbe Formel wie in baue_kreis_geometrie, aber
    # unabhaengig hier nochmal hergeleitet statt kopiert).
    delta_lon = distanz_nm / (60.0 * cos(radians(MITTELPUNKT_LAT)))
    return Point(MITTELPUNKT_LON + delta_lon, MITTELPUNKT_LAT)


def test_kreis_punkt_knapp_innerhalb():
    kreis = baue_kreis_geometrie(MITTELPUNKT_LON, MITTELPUNKT_LAT, RADIUS_NM)
    punkt = _punkt_oestlich(2.9)
    assert kreis.contains(punkt)


def test_kreis_punkt_knapp_ausserhalb():
    kreis = baue_kreis_geometrie(MITTELPUNKT_LON, MITTELPUNKT_LAT, RADIUS_NM)
    punkt = _punkt_oestlich(3.1)
    assert not kreis.contains(punkt)


# Einfaches Rechteck (lon 0-2, lat 50-51) als von der CSV unabhaengiges
# Test-Polygon - unabhaengig von CALDOVREP/CSV-Pflege.
RECHTECK = Polygon([(0, 50), (2, 50), (2, 51), (0, 51)])


def test_richtung_ne_bound():
    # Route von West (lon=-1) nach Ost (lon=3): Laengengrad nimmt zu -> "NE"
    route = LineString([(-1, 50.5), (3, 50.5)])
    assert bestimme_richtung(route, RECHTECK) == "NE"


def test_richtung_sw_bound():
    # Route von Ost (lon=3) nach West (lon=-1): Laengengrad nimmt ab -> "SW"
    route = LineString([(3, 50.5), (-1, 50.5)])
    assert bestimme_richtung(route, RECHTECK) == "SW"


def test_richtung_nicht_bestimmbar_bei_einzelnem_beruehrungspunkt():
    # Route beruehrt das Rechteck nur in einem Punkt (Ecke) -> nicht bestimmbar
    route = LineString([(-1, 50), (0, 50)])
    assert bestimme_richtung(route, RECHTECK) is None
