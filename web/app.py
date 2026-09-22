# Flask-Web-Oberflaeche fuer den Route Checker (Phase 2). Nutzt ausschliesslich
# das route_checker-Paket fuer die eigentliche Pruef-Logik - dieselbe Logik
# wie cli.py, nur mit Browser-Formular statt input()-Abfragen.
#
# Start lokal: flask --app web.app run  (siehe README.md)
import os

from flask import Flask, flash, redirect, render_template, url_for

from route_checker.kategorien import (
    CATEGORY_OF_CARGO,
    CATEGORY_OF_DANGEROUS_CARGO,
    CATEGORY_OF_VESSEL,
)

app = Flask(__name__)
# Nur fuer Flash-Nachrichten (Fehlermeldungen) noetig - dieses Tool ist ein
# lokal laufender Forschungs-Prototyp ohne Nutzerkonten/Sessions mit
# schuetzenswerten Daten, daher genuegt ein fester Key statt einem echten
# Secret-Management.
app.secret_key = "route-checker-prototype"
# Kleinkorrektur/Vorgabe aus dem Auftrag: Upload max. 2 MB.
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


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


if __name__ == "__main__":
    # Nur fuer schnelles lokales Testen ohne "flask run" - siehe README.md fuer
    # den empfohlenen Start ueber die Flask-CLI.
    app.run(debug=True)
