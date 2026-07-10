"""B1-Auswertung: Replikation `rep_ereignistag_volatilitaet` (Ederington/Lee 1993).

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.es.b1_volatilitaet report      # rechnet und schreibt den Report
    uv run python -m mie.es.b1_volatilitaet eintragen   # hängt die Auswertungszeile an

Gerechnet wird ausschließlich der eingefrorene Auswertungsplan aus
registry/hypothesen/rep_ereignistag_volatilitaet.md (SHA-256-gepinnt in
registry/experimente.csv): 24 Vergleiche — 2 Assets (SPY, QQQ) × 3 Gruppierungen
(FOMC, CPI, gepoolt) × 2 Maße (|Tages-TR|, Spanne) × 2 Statistiken (Mittelwert,
Median) — plus 6 jahresgeschichtete R4-Placebo-Tests auf der primären Kennzahl.
Auslegungsentscheid des Projektinhabers vom 09.07.2026: volles Raster (Mediane
auch für die Spanne). Seeds sind vorab im Code fixiert und werden nicht nach
Ergebnis nachgezogen; berichtet wird, wie es ausfällt (Modelloutput/Szenario,
keine Anlageempfehlung). Kein Netzzugriff — nur lokal gecachte Rohdaten.
"""

import argparse
import sys
from datetime import UTC, datetime

import pandas as pd

from mie import registry
from mie.es import EsError
from mie.es.masszahlen import abs_tages_tr, spanne
from mie.es.runner import (
    GRUPPEN_LABEL,
    data_version_kurz,
    lade_daten,
    placebo_tabelle,
    pp,
    pruefe_registry,
    termine_im_fenster,
    vergleichstabelle,
)
from mie.es.statistik import im_fenster, ohne_lockbox, placebo_vergleich, vergleich
from mie.sources import REPO_ROOT

EXPERIMENT_ID = "rep_ereignistag_volatilitaet"
REPORT_REL = f"docs/reports/b_es_{EXPERIMENT_ID}.md"
REPORT_PATH = REPO_ROOT / REPORT_REL

# Eingefrorene Fenster (Hypothese: SPY ab 1994-02-04, QQQ ab Reihenbeginn 1999-03-10;
# Ende 2024-12-31 = letzter Tag vor dem Lockbox-Stichtag).
FENSTER = {"SPY": ("1994-02-04", "2024-12-31"), "QQQ": ("1999-03-10", "2024-12-31")}
REGISTRIERTES_FENSTER = ("1994-02-04", "2024-12-31")

MASSE = {"abs_tr": ("|Tages-TR|", abs_tages_tr), "spanne": ("Spanne", spanne)}
STATS = ["mittelwert", "median"]
GRUPPEN = ["fomc", "cpi", "gepoolt"]

N_BOOT = 10_000
ALPHA = 0.05
# Vorab fixiert: Vergleiche fortlaufend ab SEED_BASIS (Reihenfolge Asset → Maß →
# Statistik → Gruppe), Placebos fortlaufend ab SEED_BASIS + PLACEBO_SEED_OFFSET.
SEED_BASIS = 20260709
PLACEBO_SEED_OFFSET = 100


def auswertung(
    kursframes: dict[str, pd.DataFrame],
    fomc_days,
    cpi_days,
    *,
    fenster: dict[str, tuple[str, str]],
    n_boot: int = N_BOOT,
    seed_basis: int = SEED_BASIS,
    melde=None,
) -> dict:
    """Eingefrorenen Auswertungsplan ausführen: Vergleichsraster + R4-Placebos.

    Baseline ist stets „Handelstage ohne FOMC- und ohne CPI-Termin": bei den
    getrennten Vergleichen werden die Tage des jeweils anderen Ereignistyps
    ausgeschlossen; gepoolt zählt Überlappungstage einmal (Vereinigungsmenge).
    """
    n_vergleiche = len(kursframes) * len(MASSE) * len(STATS) * len(GRUPPEN)
    if n_vergleiche >= PLACEBO_SEED_OFFSET:
        raise EsError("Seed-Kollision: mehr Vergleiche als PLACEBO_SEED_OFFSET")
    fehlend = [a for a in kursframes if a not in fenster]
    if fehlend:
        raise EsError(f"Fenster fehlt für Assets: {fehlend}")
    fomc_idx = pd.DatetimeIndex(fomc_days)
    cpi_idx = pd.DatetimeIndex(cpi_days)
    ergebnis: dict = {"assets": {}, "vergleiche": [], "placebos": []}
    seed_idx = 0
    placebo_idx = 0
    for asset, frame in kursframes.items():
        start, ende = fenster[asset]
        werte = {
            mass: im_fenster(ohne_lockbox(fn(frame)), start, ende)
            for mass, (_, fn) in MASSE.items()
        }
        handelstage = pd.DatetimeIndex(werte["abs_tr"]["date"])
        fomc_w = termine_im_fenster(fomc_idx, start, ende)
        cpi_w = termine_im_fenster(cpi_idx, start, ende)
        gepoolt_w = fomc_w.union(cpi_w)
        gruppen_termine = {
            "fomc": (fomc_w, cpi_w),
            "cpi": (cpi_w, fomc_w),
            "gepoolt": (gepoolt_w, pd.DatetimeIndex([])),
        }
        ueberlappung = fomc_w.intersection(cpi_w)
        ohne_handelstag = gepoolt_w[~gepoolt_w.isin(handelstage)]
        ergebnis["assets"][asset] = {
            "zeitraum_start": werte["abs_tr"]["date"].min().date().isoformat(),
            "zeitraum_ende": werte["abs_tr"]["date"].max().date().isoformat(),
            "n_handelstage": int(len(handelstage)),
            "n_fomc": int(fomc_w.isin(handelstage).sum()),
            "n_cpi": int(cpi_w.isin(handelstage).sum()),
            "n_ueberlappung": int(ueberlappung.isin(handelstage).sum()),
            "n_gepoolt": int(gepoolt_w.isin(handelstage).sum()),
            "termine_ohne_handelstag": [d.date().isoformat() for d in ohne_handelstag],
        }
        for mass in MASSE:
            for stat in STATS:
                for gruppe in GRUPPEN:
                    if melde:
                        melde(f"{asset} · {MASSE[mass][0]} · {stat} · {GRUPPEN_LABEL[gruppe]}")
                    ereignistage, ausschluss = gruppen_termine[gruppe]
                    r = vergleich(
                        werte[mass],
                        ereignistage,
                        ausschluss,
                        stat=stat,
                        n_boot=n_boot,
                        seed=seed_basis + seed_idx,
                        alpha=ALPHA,
                    )
                    r.update(
                        asset=asset,
                        mass=mass,
                        stat=stat,
                        gruppe=gruppe,
                        primaer=(mass == "abs_tr" and stat == "mittelwert"),
                    )
                    ergebnis["vergleiche"].append(r)
                    seed_idx += 1
        for gruppe in GRUPPEN:
            if melde:
                melde(f"{asset} · Placebo · {GRUPPEN_LABEL[gruppe]}")
            ereignistage, ausschluss = gruppen_termine[gruppe]
            r = placebo_vergleich(
                werte["abs_tr"],
                ereignistage,
                ausschluss,
                stat="mittelwert",
                n_boot=n_boot,
                seed=seed_basis + PLACEBO_SEED_OFFSET + placebo_idx,
                alpha=ALPHA,
            )
            r.update(asset=asset, gruppe=gruppe)
            ergebnis["placebos"].append(r)
            placebo_idx += 1
    return ergebnis


# --- Report ---------------------------------------------------------------------


def report_text(
    ergebnis: dict, datenversion: list[dict], experiment: dict, generiert_utc: str, commit: str
) -> str:
    """Vollständigen Report rendern (alle Zahlen stammen aus `ergebnis`)."""
    vergleiche = ergebnis["vergleiche"]
    placebos = ergebnis["placebos"]
    primaer = [v for v in vergleiche if v["primaer"]]
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in placebos if p["ki_low"] < 0 < p["ki_high"])

    def block(mass: str, stat: str) -> list[dict]:
        return [v for v in vergleiche if v["mass"] == mass and v["stat"] == stat]

    z: list[str] = []
    z += [
        f"# B1 — Replikation `{EXPERIMENT_ID}`: Volatilität an FOMC-/CPI-Tagen",
        "",
        f"**Generiert:** {generiert_utc} · **Commit:** `{commit}` · Erzeugt von "
        "`uv run python -m mie.es.b1_volatilitaet report` — nicht von Hand editieren.",
        "",
        f"**Frage (eingefroren):** {experiment['titel']} — ist die Tagesvolatilität von "
        "SPY/QQQ an FOMC-/CPI-Ereignistagen höher als an Baseline-Tagen (Handelstage ohne "
        "FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein Unterschied.",
        "",
        f"Eingefrorene Hypothese: `{experiment['hypothese_datei']}` "
        f"(sha256 `{experiment['hypothese_sha256']}`, registriert "
        f"{experiment['registered_utc']}). Fenster {experiment['fenster_start']} – "
        f"{experiment['fenster_ende']} — endet vor dem Lockbox-Stichtag 2025-01-01; "
        "diese Auswertung ist keine Lockbox-Auswertung (lockbox=0, Zähler unverändert).",
        "",
        "## Vorregistrierung und Umfang",
        "",
        "- **Auslegungsentscheid des Projektinhabers (09.07.2026):** Der ergänzende Teil "
        "der Hypothese („Differenz der Mediane … und Maß (b) als Zweitmessung“) wird als "
        "**volles Raster** gelesen — Mediane auch für die Intraday-Spanne.",
        f"- **Anzahl Tests (R6-Multiplizität):** {len(vergleiche)} Vergleiche "
        f"(davon {len(primaer)} primär: Mittelwert |Tages-TR| je Asset × Gruppierung) "
        f"+ {len(placebos)} Placebo-Tests. Alle werden vollständig berichtet — "
        "kein Auswahl-Reporting.",
        f"- **Bootstrap:** Perzentil-KI, n_boot={N_BOOT}, alpha={ALPHA}. Seeds vorab "
        f"fixiert: Basis {SEED_BASIS}, Vergleiche fortlaufend (Reihenfolge Asset → Maß → "
        f"Statistik → Gruppe), Placebos ab Basis+{PLACEBO_SEED_OFFSET} fortlaufend.",
        "- **Maße** (Tiingo-Rohfelder, nie adj_close): (a) primär "
        "|Tages-TR| = |(close_T + div_cash_T) · split_factor_T / close_(T−1) − 1|; "
        "(b) sekundär Spanne = (high_T − low_T) · split_factor_T / close_(T−1).",
        "- **Gruppen:** FOMC = reguläre Sitzungen (meeting_type=meeting), Ereignistag = "
        "letzter Sitzungstag; CPI = Release-Tage inkl. Einzelfall-Korrektur 1998-02-24. "
        "Bei den getrennten Vergleichen sind die Tage des jeweils anderen Ereignistyps "
        "aus der Baseline ausgeschlossen; gepoolt = Vereinigungsmenge, Überlappungstage "
        "einmal gezählt.",
        "",
        "## Datenversion (R3)",
        "",
    ]
    z += [
        f"- {d['label']}: sha256 `{d['sha256']}` · Stand {d['stand']} · n = {d['n']} {d['einheit']}"
        for d in datenversion
    ]
    z += ["", "## Stichprobe je Asset", ""]
    z += [
        "| Asset | Zeitraum (verwendet) | Handelstage | FOMC | CPI | Überlappung | gepoolt |",
        "|---|---|---|---|---|---|---|",
    ]
    z += [
        f"| {asset} | {a['zeitraum_start']} – {a['zeitraum_ende']} | {a['n_handelstage']} "
        f"| {a['n_fomc']} | {a['n_cpi']} | {a['n_ueberlappung']} | {a['n_gepoolt']} |"
        for asset, a in ergebnis["assets"].items()
    ]
    z += [
        "",
        "Termine im Fenster ohne Handelstag im Kursframe (nicht still verworfen):",
        "",
    ]
    z += [
        f"- {asset}: {' · '.join(a['termine_ohne_handelstag']) or 'keine'}"
        for asset, a in ergebnis["assets"].items()
    ]
    z += [
        "",
        "## Primäres Ergebnis — Mittelwert |Tages-TR| (Ereignis − Baseline)",
        "",
        *vergleichstabelle(block("abs_tr", "mittelwert")),
        "",
        "## Ergänzende Ergebnisse",
        "",
        "### Median |Tages-TR| (robust gegen Extremtage)",
        "",
        *vergleichstabelle(block("abs_tr", "median")),
        "",
        "### Mittelwert Spanne",
        "",
        *vergleichstabelle(block("spanne", "mittelwert")),
        "",
        "### Median Spanne",
        "",
        *vergleichstabelle(block("spanne", "median")),
        "",
        "## R4-Placebo (jahresgeschichtet, Mittelwert |Tages-TR|)",
        "",
        "Je Kalenderjahr werden so viele zufällige Nicht-Ereignistage gezogen wie echte "
        "handelbare Termine; echte Termine (und bei getrennten Vergleichen der jeweils "
        "andere Ereignistyp) bleiben komplett außen vor. Erwartung: Differenz ≈ 0, das KI "
        "überdeckt die 0 — konstruktionsbedingt verfehlt ein 95-%-KI die 0 aber in ~5 % "
        "der Ziehungen.",
        "",
        *placebo_tabelle(placebos),
        "",
        "## Zusammenfassung (automatisch aus den Zahlen)",
        "",
        f"- {primaer_pos} von {len(primaer)} primären 95-%-KIs (Mittelwert |Tages-TR|) "
        "liegen vollständig über 0.",
        f"- {placebo_null} von {len(placebos)} Placebo-KIs überdecken die 0.",
        "",
        "## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)",
        "",
        "1. **Anderes Underlying und andere Frequenz:** Paper = Zins-/Devisen-Futures mit "
        "Intraday-Daten; hier Aktien-ETFs mit Tagesdaten. Tagesdaten verschmieren den "
        "Intraday-Effekt; ein schwächerer oder fehlender Befund kann daran liegen.",
        "2. **FOMC ist im Paper nicht der zentrale Termin** (Schwerpunkt Arbeitsmarkt/CPI); "
        "der FOMC-Teil ist eher Erweiterung als strikte Replikation.",
        "3. **Volatilitäts-Clustering** bleibt auch nach der Jahres-Schichtung eine "
        "Restquelle für Verzerrung.",
        "",
        "## Einordnung",
        "",
        "Alle Werte sind Modelloutputs/Szenarien aus einer historischen Ereignisstudie — "
        "keine Anlageempfehlung, keine Aussage über zukünftige Kurse. Zahlen stammen "
        "ausschließlich aus committetem Code auf lokal gecachten Rohdaten (R1); "
        "Reproduktion: `uv run python -m mie.es.b1_volatilitaet report` auf dem oben "
        "genannten Commit- und Datenstand.",
        "",
    ]
    return "\n".join(z)


# --- Registry-Zeile ---------------------------------------------------------------


def ergebnis_kurz(ergebnis: dict) -> str:
    """Ein-Satz-Ergebnis für registry/auswertungen.csv (ohne Komma/Quote, appendonly)."""
    teile = [
        f"{v['asset']} {pp(v['delta'])}pp KI[{pp(v['ki_low'])};{pp(v['ki_high'])}]"
        for v in ergebnis["vergleiche"]
        if v["primaer"] and v["gruppe"] == "gepoolt"
    ]
    primaer = [v for v in ergebnis["vergleiche"] if v["primaer"]]
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in ergebnis["placebos"] if p["ki_low"] < 0 < p["ki_high"])
    return (
        f"Mittelwert |Tages-TR| Ereignis-Baseline gepoolt: {'; '.join(teile)}; "
        f"primaere KIs > 0: {primaer_pos}/{len(primaer)}; "
        f"Placebo-KIs ueberdecken 0: {placebo_null}/{len(ergebnis['placebos'])}"
    )


# --- Laden der echten Daten (nur Cache, kein Netz) ---------------------------------


def _rechne(melde=None) -> tuple[dict, dict, list[dict]]:
    experiment = pruefe_registry(EXPERIMENT_ID, REGISTRIERTES_FENSTER)
    kursframes, fomc, cpi, datenversion = lade_daten(FENSTER)
    ergebnis = auswertung(kursframes, fomc, cpi, fenster=FENSTER, melde=melde)
    return experiment, ergebnis, datenversion


# --- CLI ---------------------------------------------------------------------------


def cmd_report() -> int:
    experiment, ergebnis, datenversion = _rechne(melde=lambda s: print(f"  rechne {s} …"))
    generiert = datetime.now(UTC).isoformat(timespec="seconds")
    commit = registry.code_commit()
    REPORT_PATH.write_text(report_text(ergebnis, datenversion, experiment, generiert, commit))
    print(f"Report geschrieben: {REPORT_REL} (Commit {commit})")
    print(f"Vorschlag ergebnis_kurz: {ergebnis_kurz(ergebnis)}")
    print(f"Vorschlag data_version:  {data_version_kurz(datenversion)}")
    print("Noch NICHT in registry/auswertungen.csv eingetragen — Report prüfen, dann:")
    print("  uv run python -m mie.es.b1_volatilitaet eintragen")
    return 0


def cmd_eintragen() -> int:
    if not REPORT_PATH.is_file():
        raise EsError(f"Report fehlt ({REPORT_REL}) — zuerst `report` ausführen")
    _, ergebnis, datenversion = _rechne(melde=lambda s: print(f"  rechne {s} …"))
    row = {
        "experiment_id": EXPERIMENT_ID,
        "evaluated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "lockbox": "0",
        "ergebnis_kurz": ergebnis_kurz(ergebnis),
        "report_datei": REPORT_REL,
        "data_version": data_version_kurz(datenversion),
        "code_commit": registry.code_commit(),
    }
    registry.append_evaluations([row])
    zaehler = registry.lockbox_count(registry.load_evaluations())
    print(f"Auswertung eingetragen: {EXPERIMENT_ID} (lockbox=0)")
    print(f"  {row['ergebnis_kurz']}")
    print(f"Lockbox-Zähler: {zaehler} von {registry.LOCKBOX_MAX}. Jetzt: `make check`, committen.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.es.b1_volatilitaet", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report", help="eingefrorenen Plan rechnen und Report schreiben")
    sub.add_parser("eintragen", help="Auswertungszeile an registry/auswertungen.csv anhängen")
    args = parser.parse_args(argv)
    if args.cmd == "report":
        return cmd_report()
    return cmd_eintragen()


if __name__ == "__main__":
    sys.exit(main())
