# RTZ-/GPX-Routendateien einlesen.
#
# xml.etree.ElementTree wird bewusst durch defusedxml.ElementTree ersetzt (API-
# kompatibel): schuetzt vor praeparierten XML-Dateien (z.B. "billion laughs"/
# externe Entities), was insbesondere fuer den Datei-Upload in der Web-
# Oberflaeche (Phase 2) wichtig ist. Fuer gueltige RTZ-/GPX-Dateien aendert
# sich dadurch nichts am Ergebnis.
import os
import defusedxml.ElementTree as ET

RTZ_NS = {"rtz": "http://www.cirm.org/RTZ/1/1"}
GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}


# Wird geworfen, wenn eine Routendatei nicht sinnvoll eingelesen werden kann
# (kaputtes/falsches Format, oder weniger als 2 Wegpunkte - eine Route mit nur
# einem Punkt kann nicht als LineString geprueft werden). Statt eines rohen
# Absturzes (main.py) bzw. Stacktrace (Web-Oberflaeche) bekommt der Aufrufer
# damit eine verstaendliche, abfangbare Fehlermeldung.
class RouteImportError(Exception):
    pass


# Baut aus dem geparsten RTZ-Baum (routen_name, wegpunkte) - gemeinsame Logik
# fuer den Pfad- und den Datei-Objekt-Import.
def _rtz_aus_baum(wurzel, quelle_fuer_fehlermeldung):
    routen_info = wurzel.find("rtz:routeInfo", RTZ_NS)
    if routen_info is None:
        raise RouteImportError(f"'{quelle_fuer_fehlermeldung}' ist keine gueltige RTZ-Datei (routeInfo fehlt).")
    routen_name = routen_info.get("routeName")

    waypoints_element = wurzel.find("rtz:waypoints", RTZ_NS)
    if waypoints_element is None:
        raise RouteImportError(f"'{quelle_fuer_fehlermeldung}' enthaelt keine Wegpunkte.")

    wegpunkte = []
    for wp in waypoints_element.findall("rtz:waypoint", RTZ_NS):
        pos = wp.find("rtz:position", RTZ_NS)
        lat = float(pos.get("lat"))
        lon = float(pos.get("lon"))
        wegpunkte.append((lon, lat, wp.get("name")))

    if len(wegpunkte) < 2:
        raise RouteImportError(
            f"'{quelle_fuer_fehlermeldung}' hat nur {len(wegpunkte)} Wegpunkt(e) - "
            "eine Route braucht mindestens 2, um geprueft werden zu koennen."
        )
    return routen_name, wegpunkte


# Baut aus dem geparsten GPX-Baum (routen_name, wegpunkte) - gemeinsame Logik
# fuer den Pfad- und den Datei-Objekt-Import.
#
# GPX kennt (anders als RTZ) keinen Pflicht-Routennamen und keinen Pflicht-Namen
# pro Wegpunkt - falls das <name>-Element fehlt, wird routen_name_ersatz bzw.
# "WP1", "WP2", ... als Ersatz verwendet.
def _gpx_aus_baum(wurzel, routen_name_ersatz, quelle_fuer_fehlermeldung):
    route = wurzel.find("gpx:rte", GPX_NS)
    if route is None:
        raise RouteImportError(f"'{quelle_fuer_fehlermeldung}' enthaelt keine Route (<rte>).")

    name_element = route.find("gpx:name", GPX_NS)
    if name_element is not None and name_element.text:
        routen_name = name_element.text
    else:
        routen_name = routen_name_ersatz

    wegpunkte = []
    for i, wp in enumerate(route.findall("gpx:rtept", GPX_NS), start=1):
        lat = float(wp.get("lat"))
        lon = float(wp.get("lon"))
        name_element = wp.find("gpx:name", GPX_NS)
        name = name_element.text if name_element is not None and name_element.text else f"WP{i}"
        wegpunkte.append((lon, lat, name))

    if len(wegpunkte) < 2:
        raise RouteImportError(
            f"'{quelle_fuer_fehlermeldung}' hat nur {len(wegpunkte)} Wegpunkt(e) - "
            "eine Route braucht mindestens 2, um geprueft werden zu koennen."
        )
    return routen_name, wegpunkte


# RTZ-Routendatei (Pfad) einlesen und Wegpunkte extrahieren
def lade_rtz_route(pfad):
    try:
        baum = ET.parse(pfad)
    except Exception as exc:
        raise RouteImportError(f"'{pfad}' konnte nicht als RTZ-Datei gelesen werden: {exc}") from exc
    return _rtz_aus_baum(baum.getroot(), pfad)


# RTZ-Routendatei aus einem datei-aehnlichen Objekt einlesen (z.B. Werkzeug-
# FileStorage/BytesIO bei einem Upload in der Web-Oberflaeche) statt einem Pfad.
def lade_rtz_route_aus_datei(datei_objekt, dateiname="Upload"):
    try:
        baum = ET.parse(datei_objekt)
    except Exception as exc:
        raise RouteImportError(f"'{dateiname}' konnte nicht als RTZ-Datei gelesen werden: {exc}") from exc
    return _rtz_aus_baum(baum.getroot(), dateiname)


# GPX-Routendatei (Pfad) einlesen und Wegpunkte extrahieren
def lade_gpx_route(pfad):
    try:
        baum = ET.parse(pfad)
    except Exception as exc:
        raise RouteImportError(f"'{pfad}' konnte nicht als GPX-Datei gelesen werden: {exc}") from exc
    ersatzname = os.path.splitext(os.path.basename(pfad))[0]
    return _gpx_aus_baum(baum.getroot(), ersatzname, pfad)


# GPX-Routendatei aus einem datei-aehnlichen Objekt einlesen (Upload)
def lade_gpx_route_aus_datei(datei_objekt, dateiname="Upload"):
    try:
        baum = ET.parse(datei_objekt)
    except Exception as exc:
        raise RouteImportError(f"'{dateiname}' konnte nicht als GPX-Datei gelesen werden: {exc}") from exc
    ersatzname = os.path.splitext(dateiname)[0]
    return _gpx_aus_baum(baum.getroot(), ersatzname, dateiname)
