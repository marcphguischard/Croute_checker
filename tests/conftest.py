# Stellt sicher, dass relative Pfade (reporting_points.csv, tests/routes/...)
# unabhaengig davon funktionieren, aus welchem Verzeichnis pytest gestartet
# wird - indem das Arbeitsverzeichnis fuer die gesamte Testsitzung auf das
# Projekt-Wurzelverzeichnis gesetzt wird.
import os

import pytest

PROJEKT_WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True, scope="session")
def _projekt_wurzel_als_arbeitsverzeichnis():
    vorher = os.getcwd()
    os.chdir(PROJEKT_WURZEL)
    yield
    os.chdir(vorher)
