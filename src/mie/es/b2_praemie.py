"""B2-Auswertung: Replikation `rep_announcement_day_praemie` (Savor/Wilson 2013).

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.es.b2_praemie report      # rechnet und schreibt den Report
    uv run python -m mie.es.b2_praemie eintragen   # hängt die Auswertungszeile an

Gerechnet wird ausschließlich der eingefrorene Auswertungsplan aus
registry/hypothesen/rep_announcement_day_praemie.md (SHA-256-gepinnt in
registry/experimente.csv): 6 Vergleiche — 2 Assets (SPY, QQQ) × 3 Gruppierungen
(gepoolt = primär; FOMC, CPI getrennt = sekundär) × 1 Statistik (Mittelwert des
vorzeichenbehafteten Tages-TR) — plus 6 jahresgeschichtete R4-Placebo-Tests.
Keine Mediane, keine Spanne, keine Zusatzmaße (das wäre typ:exploration mit
eigener Registrierung und Freigabe). Seeds sind vorab im Paketplan vom
10.07.2026 fixiert und werden nicht nach Ergebnis nachgezogen; berichtet wird,
wie es ausfällt (Modelloutput/Szenario, keine Anlageempfehlung). Kein
Netzzugriff — nur lokal gecachte Rohdaten.
"""

import argparse
import sys
from datetime import UTC, datetime

import pandas as pd

from mie import registry
from mie.es import EsError
from mie.es.masszahlen import tages_tr
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

EXPERIMENT_ID = "rep_announcement_day_praemie"
REPORT_REL = f"docs/reports/b_es_{EXPERIMENT_ID}.md"
REPORT_PATH = REPO_ROOT / REPORT_REL

# Eingefrorene Fenster (Hypothese: SPY ab 1994-02-04, QQQ ab Reihenbeginn 1999-03-10;
# Ende 2024-12-31 = letzter Tag vor dem Lockbox-Stichtag).
FENSTER = {"SPY": ("1994-02-04", "2024-12-31"), "QQQ": ("1999-03-10", "2024-12-31")}
REGISTRIERTES_FENSTER = ("1994-02-04", "2024-12-31")

STAT = "mittelwert"
GRUPPEN = ["fomc", "cpi", "gepoolt"]  # Seed-Reihenfolge wie B1; primär = gepoolt

N_BOOT = 10_000
ALPHA = 0.05
# Vorab fixiert (Paketplan 10.07.2026): Vergleiche fortlaufend ab SEED_BASIS
# (Reihenfolge Asset → Gruppe), Placebos fortlaufend ab SEED_BASIS + PLACEBO_SEED_OFFSET.
SEED_BASIS = 20260710
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
    """Eingefrorenen Auswertungsplan ausführen: 6 Vergleiche + 6 R4-Placebos.

    Maß ist der vorzeichenbehaftete Tages-TR (nicht |TR| wie in B1). Baseline ist
    stets „Handelstage ohne FOMC- und ohne CPI-Termin": bei den getrennten
    Vergleichen werden die Tage des jeweils anderen Ereignistyps ausgeschlossen;
    gepoolt zählt Überlappungstage einmal (Vereinigungsmenge).
    """
    n_vergleiche = len(kursframes) * len(GRUPPEN)
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
        werte = im_fenster(ohne_lockbox(tages_tr(frame)), start, ende)
        handelstage = pd.DatetimeIndex(werte["date"])
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
            "zeitraum_start": werte["date"].min().date().isoformat(),
            "zeitraum_ende": werte["date"].max().date().isoformat(),
            "n_handelstage": int(len(handelstage)),
            "n_fomc": int(fomc_w.isin(handelstage).sum()),
            "n_cpi": int(cpi_w.isin(handelstage).sum()),
            "n_ueberlappung": int(ueberlappung.isin(handelstage).sum()),
            "n_gepoolt": int(gepoolt_w.isin(handelstage).sum()),
            "termine_ohne_handelstag": [d.date().isoformat() for d in ohne_handelstag],
        }
        for gruppe in GRUPPEN:
            if melde:
                melde(f"{asset} · Tages-TR · {STAT} · {GRUPPEN_LABEL[gruppe]}")
            ereignistage, ausschluss = gruppen_termine[gruppe]
            r = vergleich(
                werte,
                ereignistage,
                ausschluss,
                stat=STAT,
                n_boot=n_boot,
                seed=seed_basis + seed_idx,
                alpha=ALPHA,
            )
            r.update(asset=asset, gruppe=gruppe, primaer=(gruppe == "gepoolt"))
            ergebnis["vergleiche"].append(r)
            seed_idx += 1
        for gruppe in GRUPPEN:
            if melde:
                melde(f"{asset} · Placebo · {GRUPPEN_LABEL[gruppe]}")
            ereignistage, ausschluss = gruppen_termine[gruppe]
            r = placebo_vergleich(
                werte,
                ereignistage,
                ausschluss,
                stat=STAT,
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
    sekundaer = [v for v in vergleiche if not v["primaer"]]
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in placebos if p["ki_low"] < 0 < p["ki_high"])

    z: list[str] = []
    z += [
        f"# B2 — Replikation `{EXPERIMENT_ID}`: Announcement-Day-Prämie an FOMC-/CPI-Tagen",
        "",
        f"**Generiert:** {generiert_utc} · **Commit:** `{commit}` · Erzeugt von "
        "`uv run python -m mie.es.b2_praemie report` — nicht von Hand editieren.",
        "",
        f"**Frage (eingefroren):** {experiment['titel']} — ist die mittlere "
        "vorzeichenbehaftete Tagesrendite (Tages-TR, Schluss T−1 → Schluss T) von "
        "SPY/QQQ an FOMC-/CPI-Ereignistagen höher als an Baseline-Tagen (Handelstage "
        "ohne FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein Unterschied.",
        "",
        f"Eingefrorene Hypothese: `{experiment['hypothese_datei']}` "
        f"(sha256 `{experiment['hypothese_sha256']}`, registriert "
        f"{experiment['registered_utc']}). Fenster {experiment['fenster_start']} – "
        f"{experiment['fenster_ende']} — endet vor dem Lockbox-Stichtag 2025-01-01; "
        "diese Auswertung ist keine Lockbox-Auswertung (lockbox=0, Zähler unverändert).",
        "",
        "## Vorregistrierung und Umfang",
        "",
        f"- **Anzahl Tests (R6-Multiplizität):** {len(vergleiche)} Vergleiche "
        f"(davon {len(primaer)} primär: Mittelwert Tages-TR gepoolt je Asset; "
        f"{len(sekundaer)} sekundär: getrennt nach FOMC/CPI) "
        f"+ {len(placebos)} Placebo-Tests (R4-Selbsttest der Pipeline, je Asset × "
        "Gruppe nach B1-Muster — keine Hypothesenerweiterung). Alle werden vollständig "
        "berichtet — kein Auswahl-Reporting. Keine Mediane, keine Spanne, keine "
        "Zusatzmaße (nicht vorregistriert).",
        f"- **Bootstrap:** Perzentil-KI, n_boot={N_BOOT}, alpha={ALPHA}. Seeds vorab "
        f"fixiert (Paketplan 10.07.2026): Basis {SEED_BASIS}, Vergleiche fortlaufend "
        f"(Reihenfolge Asset → Gruppe), Placebos ab Basis+{PLACEBO_SEED_OFFSET} "
        "fortlaufend.",
        "- **Maß** (Tiingo-Rohfelder, nie adj_close; Formel aus Ziel `w1_up_v1`): "
        "Tages-TR = (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1 — "
        "vorzeichenbehaftet, nicht |TR| wie in B1.",
        "- **Gruppen:** FOMC = reguläre Sitzungen (meeting_type=meeting), Ereignistag = "
        "letzter Sitzungstag; CPI = Release-Tage inkl. Einzelfall-Korrektur 1998-02-24. "
        "Bei den getrennten Vergleichen sind die Tage des jeweils anderen Ereignistyps "
        "aus der Baseline ausgeschlossen; gepoolt = Vereinigungsmenge, Überlappungstage "
        "(FOMC- und CPI-Tag zugleich) einmal gezählt und in der Stichprobentabelle "
        "gesondert ausgewiesen.",
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
        "## Primäres Ergebnis — Mittelwert Tages-TR gepoolt (Ereignis − Baseline)",
        "",
        *vergleichstabelle(primaer),
        "",
        "## Sekundäre Ergebnisse — getrennt nach FOMC/CPI",
        "",
        *vergleichstabelle(sekundaer),
        "",
        "## R4-Placebo (jahresgeschichtet, Mittelwert Tages-TR)",
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
        f"- {primaer_pos} von {len(primaer)} primären 95-%-KIs (Mittelwert Tages-TR "
        "gepoolt) liegen vollständig über 0.",
        f"- {placebo_null} von {len(placebos)} Placebo-KIs überdecken die 0.",
        "",
        "## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)",
        "",
        "1. **Terminset:** nur FOMC + CPI (MVP-Scope); das Paper nutzt zusätzlich den "
        "Arbeitsmarktbericht. Wir replizieren also nur einen Ausschnitt des "
        "Paper-Befunds.",
        "2. **Rohrendite statt Überrendite:** Das Paper misst Renditen über dem "
        "risikofreien Zins; wir testen Tages-Total-Returns ohne Zinsabzug. Bei einem "
        "Horizont von einem Tag ist der risikofreie Tageszins klein; die Abweichung "
        "gehört trotzdem in die Interpretation.",
        "3. **ETF statt breitem Marktportfolio; Zeitraum 1994–2024 statt 1958–2009** "
        "(Fenster endet vor dem Lockbox-Stichtag; QQQ erst ab 1999).",
        "",
        "## Einordnung",
        "",
        "Alle Werte sind Modelloutputs/Szenarien aus einer historischen Ereignisstudie — "
        "keine Anlageempfehlung, keine Aussage über zukünftige Kurse. Zahlen stammen "
        "ausschließlich aus committetem Code auf lokal gecachten Rohdaten (R1); "
        "Reproduktion: `uv run python -m mie.es.b2_praemie report` auf dem oben "
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
        if v["primaer"]
    ]
    primaer = [v for v in ergebnis["vergleiche"] if v["primaer"]]
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in ergebnis["placebos"] if p["ki_low"] < 0 < p["ki_high"])
    return (
        f"Mittelwert Tages-TR Ereignis-Baseline gepoolt: {'; '.join(teile)}; "
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
    print("  uv run python -m mie.es.b2_praemie eintragen")
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
    parser = argparse.ArgumentParser(prog="mie.es.b2_praemie", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report", help="eingefrorenen Plan rechnen und Report schreiben")
    sub.add_parser("eintragen", help="Auswertungszeile an registry/auswertungen.csv anhängen")
    args = parser.parse_args(argv)
    if args.cmd == "report":
        return cmd_report()
    return cmd_eintragen()


if __name__ == "__main__":
    sys.exit(main())
