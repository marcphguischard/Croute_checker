# ============================================================
# S-127-Kategorien (IHO S-127 Marine Traffic Management, Edition 1.0.0)
# Werte 1:1 aus s127_kategorien_uebersicht.md uebernommen. Codes 18/19 sind
# Tool-Erweiterungen ueber die Basisliste hinaus (S-127 erlaubt das explizit:
# "S100_Codelist, erweiterbar") - ohne sie koennten die bestehenden Faehren-/
# LNG-Sonderhinweise (Dover/Ramsgate/Dunkirk VTS) nicht mehr unterschieden
# werden, die es schon vor dieser Umstellung gab.
#
# Unveraendert aus main.py uebernommen (Umbau in mehrere Module, Schritt 1
# von Phase 1) - keine Wertaenderung.
# ============================================================
CATEGORY_OF_VESSEL = {
    1: "General cargo vessel",
    2: "Container carrier",
    3: "Tanker",
    4: "Bulk carrier",
    5: "Passenger vessel",
    6: "Roll-on roll-off",
    7: "Refrigerated cargo vessel",
    8: "Fishing vessel",
    9: "Service",
    10: "Warship",
    11: "Towed or pushed composite unit",
    12: "Tug and tow",
    13: "Light recreational",
    14: "Semi-submersible offshore installation",
    15: "Jackup exploration or project installation",
    16: "Livestock carrier",
    17: "Sport fishing",
    18: "Ferry",       # Tool-Erweiterung (nicht in der offiziellen S-127-Basisliste)
    19: "LNG tanker",  # Tool-Erweiterung (nicht in der offiziellen S-127-Basisliste)
}

CATEGORY_OF_CARGO = {
    1: "Bulk",
    2: "Container",
    3: "General",
    4: "Liquid",
    5: "Passenger",
    6: "Livestock",
    7: "Dangerous or hazardous",
    8: "Heavy lift",
    9: "Ballast",
}

# categoryOfShipReport - Meldungstypen (fuer Report_Types-Spalte)
CATEGORY_OF_SHIP_REPORT = {
    1: "Sailing Plan",
    2: "Position Report",
    3: "Deviation Report",
    4: "Final Report",
    5: "Dangerous Goods Report",
    6: "Harmful Substances Report",
    7: "Marine Pollutants Report",
    8: "Other Report",
}

CATEGORY_OF_DANGEROUS_CARGO = {
    1: "Class 1 Div. 1.1", 2: "Class 1 Div. 1.2", 3: "Class 1 Div. 1.3",
    4: "Class 1 Div. 1.4", 5: "Class 1 Div. 1.5", 6: "Class 1 Div. 1.6",
    7: "Class 2 Div. 2.1", 8: "Class 2 Div. 2.2", 9: "Class 2 Div. 2.3",
    10: "Class 3", 11: "Class 4 Div. 4.1", 12: "Class 4 Div. 4.2",
    13: "Class 4 Div. 4.3", 14: "Class 5 Div. 5.1", 15: "Class 5 Div. 5.2",
    16: "Class 6 Div. 6.1", 17: "Class 6 Div. 6.2", 18: "Class 7",
    19: "Class 8", 20: "Class 9", 21: "Harmful Substances in packaged form",
}

# Schiffstypen, die als "Tanker" im Sinne von Nur_Tanker gelten
TANKER_TYPEN = {"Tanker", "LNG tanker"}
