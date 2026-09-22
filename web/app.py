# Flask-Web-Oberflaeche fuer den Route Checker (Phase 2). Nutzt ausschliesslich
# das route_checker-Paket fuer die eigentliche Pruef-Logik - dieselbe Logik
# wie cli.py, nur mit Browser-Formular statt input()-Abfragen.
#
# Start lokal: flask --app web.app run  (siehe README.md)
from datetime import datetime

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for

from route_checker.ausgabe import (
    erzeuge_textbericht,
    formatiere_action_zeile,
    formatiere_frequenz,
    formatiere_schiffszusammenfassung,
)
from route_checker.gebiete import baue_geometrie_fuer_gebiet, geometrie_zu_geojson, lade_gebiete
from route_checker.kategorien import (
    CATEGORY_OF_CARGO,
    CATEGORY_OF_DANGEROUS_CARGO,
    CATEGORY_OF_VESSEL,
)
from route_checker.pruefung import pruefe_route, uk_marep_hinweis
from route_checker.routen_import import (
    RouteImportError,
    lade_gpx_route_aus_datei,
    lade_rtz_route_aus_datei,
)

app = Flask(__name__)
# Nur fuer Flash-Nachrichten (Fehlermeldungen) noetig - dieses Tool ist ein
# lokal laufender Forschungs-Prototyp ohne Nutzerkonten/Sessions mit
# schuetzenswerten Daten, daher genuegt ein fester Key statt einem echten
# Secret-Management.
app.secret_key = "route-checker-prototype"
# Kleinkorrektur/Vorgabe aus dem Auftrag: Upload max. 2 MB.
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# CSV einmal beim Start des Servers laden (aendert sich waehrend eines Laufs
# nicht) statt bei jeder Anfrage neu einzulesen.
GEBIETE = lade_gebiete()


# Baut das Schiffsdaten-Dict (gleiche Schluessel wie cli.frage_schiffsdaten())
# aus einem Formular-Mapping - gemeinsam genutzt von /check (Formular-Upload)
# und /download (Hidden-Field-Repost), damit dieselbe Logik nicht doppelt
# gepflegt werden muss. Wirft ValueError/KeyError bei fehlenden/ungueltigen
# Feldern - vom Aufrufer abzufangen.
def _schiffsdaten_aus_formular(formular):
    schiffstyp_code = int(formular["schiffstyp_code"])
    cargo_code = int(formular["cargo_code"])
    imdg_codes = [int(c) for c in formular.getlist("imdg_codes")]

    return {
        "schiffstyp": CATEGORY_OF_VESSEL[schiffstyp_code],
        "category_of_vessel_code": schiffstyp_code,
        "category_of_cargo_code": cargo_code,
        "category_of_cargo": CATEGORY_OF_CARGO[cargo_code],
        "imdg_classes": imdg_codes,
        "gt": float(formular["gt"]),
        "tdw": float(formular["tdw"]),
        "loa": float(formular["loa"]),
        "draught": float(formular["draught"]),
        "internationale_fahrt": formular["internationale_fahrt"],
        "gefahrgut": formular["gefahrgut"],
        "imdg_klasse": ", ".join(CATEGORY_OF_DANGEROUS_CARGO[c] for c in imdg_codes),
        "schweroel_ladung": formular["schweroel_ladung"],
        "personen_an_bord": int(formular["personen_an_bord"]),
        "sondertransport": formular["sondertransport"],
        "eingeschraenkt_manoevrierfaehig": formular["eingeschraenkt_manoevrierfaehig"],
        "defekte_navigationshilfen": formular["defekte_navigationshilfen"],
        "anker_in_tss": formular["anker_in_tss"],
        "vessel_registry": formular["vessel_registry"],
        "in_ballast": formular["in_ballast"],
        "government_non_commercial": formular["government_non_commercial"],
    }


# Laedt die Route aus dem Upload-Feld (Werkzeug FileStorage) - je nach
# Dateiendung ueber den passenden Parser. Datei wird nur im Speicher
# verarbeitet, nicht dauerhaft gespeichert (Vorgabe aus dem Auftrag).
def _route_aus_upload(datei_storage):
    dateiname = datei_storage.filename
    if dateiname.lower().endswith(".gpx"):
        return lade_gpx_route_aus_datei(datei_storage.stream, dateiname)
    if dateiname.lower().endswith(".rtz"):
        return lade_rtz_route_aus_datei(datei_storage.stream, dateiname)
    raise RouteImportError(f"Unsupported file type: '{dateiname}' - please upload a .rtz or .gpx file.")


@app.route("/")
def formular():
    return render_template(
        "form.html",
        vessel_types=CATEGORY_OF_VESSEL,
        cargo_types=CATEGORY_OF_CARGO,
        dangerous_cargo_types=CATEGORY_OF_DANGEROUS_CARGO,
    )


# Freundliche Fehlermeldung statt Stacktrace, wenn der Upload das 2-MB-Limit
# ueberschreitet (Flask wirft dafuer von sich aus einen 413 Request Entity
# Too Large).
@app.errorhandler(413)
def datei_zu_gross(_fehler):
    flash("The uploaded file is too large (maximum 2 MB).")
    return redirect(url_for("formular")), 413


# Liefert alle Meldegebiete als GeoJSON FeatureCollection - fuer die Karte auf
# der Ergebnisseite. Enthaelt ALLE Gebiete (nicht nur die fuer die aktuelle
# Route ausgeloesten), damit die Karte auch die nicht ausgeloesten blass
# einzeichnen kann.
@app.route("/api/areas")
def api_areas():
    features = []
    for name, daten in GEBIETE.items():
        geometrie = baue_geometrie_fuer_gebiet(daten, name)
        if geometrie is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": geometrie_zu_geojson(geometrie),
            "properties": {
                "name": name,
                "typ": daten["typ"],
                "frequenz": formatiere_frequenz(daten["frequenz"]),
                "meldeinhalt": daten["meldeinhalt"],
            },
        })
    return jsonify({"type": "FeatureCollection", "features": features})


@app.route("/check", methods=["POST"])
def pruefe():
    try:
        schiffsdaten = _schiffsdaten_aus_formular(request.form)
    except (KeyError, ValueError) as fehler:
        flash(f"Invalid or missing ship data ({fehler}). Please fill in every field.")
        return redirect(url_for("formular"))

    upload = request.files.get("route_file")
    if upload is None or upload.filename == "":
        flash("Please choose a route file (.rtz or .gpx).")
        return redirect(url_for("formular"))

    try:
        routen_name, wegpunkte_mit_namen = _route_aus_upload(upload)
    except RouteImportError as fehler:
        flash(str(fehler))
        return redirect(url_for("formular"))

    wegpunkte = [(lon, lat) for lon, lat, _name in wegpunkte_mit_namen]

    try:
        ergebnisse = pruefe_route(schiffsdaten, wegpunkte, GEBIETE)
    except RouteImportError as fehler:
        flash(str(fehler))
        return redirect(url_for("formular"))

    return render_template(
        "result.html",
        zusammenfassung=formatiere_schiffszusammenfassung(schiffsdaten),
        routen_name=routen_name,
        wegpunkte_mit_namen=wegpunkte_mit_namen,
        ergebnisse=ergebnisse,
        ausgeloeste_gebiete=[e["gebiet"] for e in ergebnisse],
        uk_hinweis=uk_marep_hinweis(schiffsdaten),
        formatiere_action_zeile=formatiere_action_zeile,
        # Fuer den Download-Button (Hidden-Field-Repost, siehe result.html):
        formular_werte=request.form,
        wegpunkte_fuer_repost=wegpunkte,
    )


# Baut denselben Textbericht wie die CLI (route_checker.ausgabe.erzeuge_textbericht)
# aus den per Hidden-Fields zurueckgeschickten Formulardaten der Ergebnisseite
# und liefert ihn als .txt-Download - ohne Server-Session, damit ein einzelner
# Prozess mehrere gleichzeitige Nutzer:innen (Vergleichsstudie!) nicht
# durcheinanderbringt.
@app.route("/download", methods=["POST"])
def download():
    try:
        schiffsdaten = _schiffsdaten_aus_formular(request.form)
    except (KeyError, ValueError) as fehler:
        flash(f"Invalid or missing ship data ({fehler}).")
        return redirect(url_for("formular"))

    routen_name = request.form.get("routen_name") or None
    lons = request.form.getlist("wp_lon")
    lats = request.form.getlist("wp_lat")
    wegpunkte = [(float(lon), float(lat)) for lon, lat in zip(lons, lats)]

    try:
        ergebnisse = pruefe_route(schiffsdaten, wegpunkte, GEBIETE)
    except RouteImportError as fehler:
        flash(str(fehler))
        return redirect(url_for("formular"))

    bericht = erzeuge_textbericht(
        schiffsdaten, routen_name, wegpunkte, ergebnisse, datetime.now(),
        uk_marep_hinweis(schiffsdaten),
    )
    return Response(
        bericht,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=ergebnis.txt"},
    )


if __name__ == "__main__":
    # Nur fuer schnelles lokales Testen ohne "flask run" - siehe README.md fuer
    # den empfohlenen Start ueber die Flask-CLI.
    app.run(debug=True)
