"""Prueft den Stand des Primaerquellen-Nachweises in reporting_points.csv.

Liest die CSV NUR LESEND ein und gibt einen Bericht auf der Konsole aus:
- Tabelle aller Gebiete mit Verification_Status und Primary_Source_Reference
- Zusammenfassung (Anzahl/Prozent je Status)
- Warnungen bei unvollstaendigen "verified"-Eintraegen oder unbekannten
  Statuswerten

Aufruf:
    python scripts/pruefe_quellen.py
    python scripts/pruefe_quellen.py --markdown
"""
import argparse
from pathlib import Path

import pandas as pd

CSV_PFAD = Path(__file__).resolve().parent.parent / "reporting_points.csv"

# Einzige erlaubten Werte fuer Verification_Status (siehe Primaerquellen-Auftrag).
ERLAUBTE_STATUS = ["verified", "candidate", "open", "no_public_source"]

# Felder, die bei Verification_Status == "verified" gefuellt sein muessen.
PFLICHTFELDER_BEI_VERIFIED = [
    ("primary_source_reference", "Primary_Source_Reference"),
    ("primary_source_date", "Primary_Source_Date"),
    ("verification_date", "Verification_Date"),
]


def _text(wert):
    if pd.isna(wert):
        return ""
    return str(wert).strip()


# Liest reporting_points.csv und liefert nur die Zeilen, in denen ein
# Gebietsname steht (eine Zeile pro Meldegebiet, nicht pro Meldepunkt).
def lade_gebietszeilen(pfad=CSV_PFAD):
    df = pd.read_csv(pfad)
    df = df[df["Gebiet"].notna() & (df["Gebiet"].astype(str).str.strip() != "")]

    zeilen = []
    for _, reihe in df.iterrows():
        zeilen.append({
            "gebiet": _text(reihe["Gebiet"]),
            "verification_status": _text(reihe.get("Verification_Status")),
            "primary_source_type": _text(reihe.get("Primary_Source_Type")),
            "primary_source_reference": _text(reihe.get("Primary_Source_Reference")),
            "primary_source_date": _text(reihe.get("Primary_Source_Date")),
            "primary_source_url": _text(reihe.get("Primary_Source_URL")),
            "verification_date": _text(reihe.get("Verification_Date")),
        })
    return zeilen


# Warnung je Gebiet: "verified" ohne vollstaendigen Nachweis, oder ein
# Statuswert ausserhalb der erlaubten Liste. Leerer Status ist KEINE Warnung
# (bedeutet nur: noch nicht bearbeitet).
def sammle_warnungen(zeilen):
    warnungen = []
    for z in zeilen:
        status = z["verification_status"]

        if status and status not in ERLAUBTE_STATUS:
            warnungen.append(
                f"{z['gebiet']}: unbekannter Verification_Status '{status}' "
                f"(erlaubt: {', '.join(ERLAUBTE_STATUS)})"
            )

        if status == "verified":
            fehlende_felder = [
                spaltenname for schluessel, spaltenname in PFLICHTFELDER_BEI_VERIFIED
                if not z[schluessel]
            ]
            if fehlende_felder:
                warnungen.append(
                    f"{z['gebiet']}: Status 'verified', aber leer: {', '.join(fehlende_felder)}"
                )
    return warnungen


# Zaehlt Gebiete je Status (absolut + Prozent von der Gesamtzahl aller
# Gebiete). Gebiete ohne gesetzten Status laufen separat unter "(kein Status)".
def sammle_zusammenfassung(zeilen):
    gesamt = len(zeilen)
    zaehlung = {status: 0 for status in ERLAUBTE_STATUS}
    ohne_status = 0

    for z in zeilen:
        status = z["verification_status"]
        if status in zaehlung:
            zaehlung[status] += 1
        else:
            ohne_status += 1

    def prozent(anzahl):
        return (anzahl / gesamt * 100) if gesamt else 0.0

    zeilen_ausgabe = [(status, zaehlung[status], prozent(zaehlung[status])) for status in ERLAUBTE_STATUS]
    zeilen_ausgabe.append(("(kein Status)", ohne_status, prozent(ohne_status)))
    return gesamt, zeilen_ausgabe


def _oder_strich(wert):
    return wert if wert else "-"


def drucke_text(zeilen, warnungen, gesamt, zusammenfassung):
    print("=== Primaerquellen-Nachweis: reporting_points.csv ===\n")

    gebiet_breite = max([len("Gebiet")] + [len(z["gebiet"]) for z in zeilen])
    status_breite = max([len("Verification_Status")] + [len(_oder_strich(z["verification_status"])) for z in zeilen])

    kopf = f"{'Gebiet':<{gebiet_breite}}  {'Verification_Status':<{status_breite}}  Primary_Source_Reference"
    print(kopf)
    print("-" * len(kopf))
    for z in zeilen:
        print(
            f"{z['gebiet']:<{gebiet_breite}}  "
            f"{_oder_strich(z['verification_status']):<{status_breite}}  "
            f"{_oder_strich(z['primary_source_reference'])}"
        )

    print(f"\n=== Zusammenfassung ({gesamt} Gebiete) ===")
    for status, anzahl, anteil in zusammenfassung:
        print(f"{status:<16} {anzahl:>3} / {gesamt}  ({anteil:5.1f}%)")

    print(f"\n=== Warnungen ({len(warnungen)}) ===")
    if warnungen:
        for w in warnungen:
            print(f"- {w}")
    else:
        print("Keine.")


def drucke_markdown(zeilen, warnungen, gesamt, zusammenfassung):
    print("## Primaerquellen-Nachweis: reporting_points.csv\n")

    print("| Gebiet | Verification_Status | Primary_Source_Reference |")
    print("| --- | --- | --- |")
    for z in zeilen:
        gebiet = z["gebiet"].replace("|", "\\|")
        status = _oder_strich(z["verification_status"]).replace("|", "\\|")
        referenz = _oder_strich(z["primary_source_reference"]).replace("|", "\\|")
        print(f"| {gebiet} | {status} | {referenz} |")

    print(f"\n### Zusammenfassung ({gesamt} Gebiete)\n")
    print("| Status | Anzahl | Anteil |")
    print("| --- | --- | --- |")
    for status, anzahl, anteil in zusammenfassung:
        print(f"| {status} | {anzahl} / {gesamt} | {anteil:.1f}% |")

    print(f"\n### Warnungen ({len(warnungen)})\n")
    if warnungen:
        for w in warnungen:
            print(f"- {w}")
    else:
        print("Keine.")


def main():
    parser = argparse.ArgumentParser(
        description="Prueft den Primaerquellen-Nachweis in reporting_points.csv (nur lesend)."
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="Bericht als Markdown-Tabelle statt als Konsolentext ausgeben.",
    )
    args = parser.parse_args()

    zeilen = lade_gebietszeilen()
    warnungen = sammle_warnungen(zeilen)
    gesamt, zusammenfassung = sammle_zusammenfassung(zeilen)

    if args.markdown:
        drucke_markdown(zeilen, warnungen, gesamt, zusammenfassung)
    else:
        drucke_text(zeilen, warnungen, gesamt, zusammenfassung)


if __name__ == "__main__":
    main()
