# Route Checker

Prüft eine ECDIS-Route (RTZ/GPX) und Schiffsdaten gegen die funktechnischen
Meldepflichten in der Straße von Dover (CALDOVREP, Dover VTS, Ramsgate,
SURNAV, WETREP, Calais/Dunkirk VTS, Boulogne, Rye).

> **Prototype for research purposes. Not for navigational use. Always
> consult the official nautical publications.**

Es gibt zwei Bedienarten:

- **Kommandozeile** (`main.py`): interaktive Abfrage im Terminal, wie bisher.
- **Web-Oberfläche** (`web/app.py`): Formular im Browser, mit Karte und
  Download-Button - für die Vergleichsstudie mit Nautikern gedacht.

Beide nutzen dieselbe Prüf-Logik aus dem Paket `route_checker/`.

## Installation

Python 3.10+ wird vorausgesetzt.

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Mac/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Kommandozeile starten

```bash
python3 main.py
```

Liest wahlweise eine Routendatei aus `routes/` (RTZ oder GPX) oder Wegpunkte
manuell ein, fragt die Schiffsdaten ab und schreibt das Ergebnis nach
`ergebnis.txt`.

Alternativ: `Start Route Checker.command` (Mac) bzw. `Start.bat` /
„Route Checker starten.lnk" (Windows) legen bei Bedarf automatisch eine
virtuelle Umgebung an und starten `main.py`.

## Web-Oberfläche starten

### Windows (PowerShell, im aktivierten venv)

```powershell
$env:FLASK_APP = "web.app"
flask run
```

### Mac/Linux (im aktivierten venv)

```bash
flask --app web.app run
```

(Falls der `flask`-Befehl nicht gefunden wird: `python3 -m flask --app web.app run` verwenden.)

Danach im Browser `http://127.0.0.1:5000` öffnen. Formular ausfüllen,
Routendatei (`.rtz`/`.gpx`, max. 2 MB) hochladen, „Check route" - Ergebnis
erscheint als Tabelle plus Karte, mit Download-Button für den Textbericht.

Die Route-Datei wird nur im Arbeitsspeicher verarbeitet, nicht dauerhaft
gespeichert. `reporting_points.csv` wird beim Start des Servers einmal
eingelesen.

## Tests

```bash
python3 -m pytest
```

44 Tests zur Prüf-Logik (`tests/test_geometrie.py`, `tests/test_schwellenwert.py`,
`tests/test_plausibilitaet.py` - basierend auf `testprotokoll_plausibilitaet.txt`)
plus 8 Tests zur Web-Oberfläche (`tests/test_web.py`) plus 9 Tests zum
Primärquellen-Nachweis (`tests/test_quellen.py`, siehe unten).

## Projektstruktur

```
route_checker/     Pruef-Logik (Kategorien, Routen-Import, Geometrie, Regeln, Ausgabe)
cli.py              Kommandozeilen-Bedienung
main.py             duenner Einstiegspunkt fuer "python3 main.py"
web/                Flask-Web-Oberflaeche (app.py, templates/, static/)
tests/              pytest-Tests + Testrouten
scripts/            Hilfsskripte (z.B. pruefe_quellen.py)
reporting_points.csv  Meldegebiete (Geometrie + Kriterien)
CHANGELOG.md        Entwicklungsverlauf
```

Siehe `CHANGELOG.md` für Details zu allen Entwicklungsschritten.

## Datengrundlage und Quellennachweis

`reporting_points.csv` dokumentiert für jedes Meldegebiet zwei getrennte
Quellenangaben:

- **`Source_Type` / `Source_Reference`**: das nautische Arbeitsmittel
  (ADP/ALRS), über das das System ursprünglich gefunden wurde. Bleibt
  unverändert als Fundstellen-Nachweis erhalten.
- **`Primary_Source_Type` / `Primary_Source_Reference` / `Primary_Source_Date`
  / `Primary_Source_URL`**: die Primärquelle (IMO-Entschließung, nationaler
  Erlass/Arrêté, britische General Directions), auf die die Bachelorarbeit
  sich stützt.

Der Bearbeitungsstand jeder Primärquelle steht in `Verification_Status`:

| Status | Bedeutung |
| --- | --- |
| `verified` | Primärquelle geprüft und bestätigt; `Primary_Source_Reference`, `Primary_Source_Date` und `Verification_Date` sind gefüllt. |
| `candidate` | Primärquelle recherchiert, aber noch nicht gegengeprüft. |
| `open` | Noch keine Primärquelle gefunden. |
| `no_public_source` | Es existiert keine öffentlich zugängliche Primärquelle; die Angabe stützt sich weiterhin auf ADP/ALRS. |

Textbericht und Web-Ergebnisseite zeigen unter „Source" die Primärquelle,
sofern vorhanden, sonst wie bisher `Source_Reference` - bei `open`/`candidate`
mit dem Zusatz „(source not yet verified)", bei `no_public_source` mit
„(no public primary source; based on nautical publications)".

Mit `python scripts/pruefe_quellen.py` (optional `--markdown`) lässt sich der
aktuelle Bearbeitungsstand aller Gebiete als Bericht ausgeben, inklusive
Warnungen bei unvollständigen `verified`-Einträgen.
