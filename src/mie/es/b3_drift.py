"""B3-Auswertung: Replikation `rep_pre_fomc_drift` (Lucca/Moench 2015).

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.es.b3_drift report      # rechnet und schreibt den Report
    uv run python -m mie.es.b3_drift eintragen   # hängt die Auswertungszeile an

Gerechnet wird ausschließlich der eingefrorene Auswertungsplan aus
registry/hypothesen/rep_pre_fomc_drift.md (SHA-256-gepinnt in
registry/experimente.csv): 2 Vergleiche — SPY (primäre Replikation) und QQQ
(sekundäre Erweiterung), je Mittelwert des Overnight-TR (Schluss T−1 →
Eröffnung T) — plus 2 jahresgeschichtete R4-Placebo-Tests. Ereignistage sind
nur reguläre FOMC-Sitzungen (Statement-Tag), Stichprobe ab Mai 1999;
CPI-Release-Tage (08:30 ET, im Overnight-Fenster) sind aus der Baseline
ausgeschlossen. Überlappungsregel anders als B1/B2: Fällt ein
FOMC-Statement-Tag mit einem CPI-Release zusammen, wird der Tag aus dem
Haupttest ausgeschlossen (weder Ereignis noch Baseline) und gesondert
ausgewiesen. Keine Mediane, keine Zusatzmaße, keine eigene CPI-Auswertung
(das wäre typ:exploration mit eigener Registrierung und Freigabe). Seeds sind
vorab im Paketplan vom 10.07.2026 fixiert und werden nicht nach Ergebnis
nachgezogen; berichtet wird, wie es ausfällt (Modelloutput/Szenario, keine
Anlageempfehlung). Kein Netzzugriff — nur lokal gecachte Rohdaten.
"""

import argparse
import sys
from datetime import UTC, datetime

import pandas as pd

from mie import registry
from mie.es import EsError
from mie.es.masszahlen import overnight_tr
from mie.es.runner import (
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

EXPERIMENT_ID = "rep_pre_fomc_drift"
REPORT_REL = f"docs/reports/b_es_{EXPERIMENT_ID}.md"
REPORT_PATH = REPO_ROOT / REPORT_REL

# Eingefrorenes Fenster (Hypothese: ab Mai 1999 = Ära-Grenze der Statement-Zeiten;
# Ende 2024-12-31 = letzter Tag vor dem Lockbox-Stichtag). SPY und QQQ identisch —
# die QQQ-Reihe beginnt 1999-03-10 und deckt das Fenster ab.
FENSTER = {"SPY": ("1999-05-01", "2024-12-31"), "QQQ": ("1999-05-01", "2024-12-31")}
REGISTRIERTES_FENSTER = ("1999-05-01", "2024-12-31")

STAT = "mittelwert"
PRIMAER_ASSET = "SPY"  # primäre Replikation (Paper-Index S&P 500); QQQ = Erweiterung

N_BOOT = 10_000
ALPHA = 0.05
# Vorab fixiert (Paketplan 10.07.2026): Vergleiche fortlaufend ab SEED_BASIS
# (Reihenfolge SPY → QQQ), Placebos fortlaufend ab SEED_BASIS + PLACEBO_SEED_OFFSET.
# Basis bewusst wie B2 (gleiche Datums-Konvention); unbedenklich, da anderes Maß
# und andere Gruppen — identische Seeds koppeln hier nichts.
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
    primaer_asset: str = PRIMAER_ASSET,
    melde=None,
) -> dict:
    """Eingefrorenen Auswertungsplan ausführen: 2 Vergleiche + 2 R4-Placebos.

    Maß ist der Overnight-TR (Schluss T−1 → Eröffnung T). Ereignismenge =
    FOMC-Statement-Tage ohne CPI-Überlappung; Ausschlussmenge = alle CPI-Tage
    (Baseline-Kontamination durch 08:30-ET-Releases). Überlappungstage FOMC=CPI
    zählen damit weder als Ereignis noch als Baseline und werden gesondert
    ausgewiesen — die Überlappungsregel der eingefrorenen Hypothese.
    """
    if len(kursframes) >= PLACEBO_SEED_OFFSET:
        raise EsError("Seed-Kollision: mehr Vergleiche als PLACEBO_SEED_OFFSET")
    if primaer_asset not in kursframes:
        raise EsError(f"primäres Asset {primaer_asset} fehlt in den Kursframes")
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
        werte = im_fenster(ohne_lockbox(overnight_tr(frame)), start, ende)
        handelstage = pd.DatetimeIndex(werte["date"])
        fomc_w = termine_im_fenster(fomc_idx, start, ende)
        cpi_w = termine_im_fenster(cpi_idx, start, ende)
        ueberlappung = fomc_w.intersection(cpi_w)
        ereignis_w = fomc_w.difference(cpi_w)
        ohne_handelstag = ereignis_w[~ereignis_w.isin(handelstage)]
        ergebnis["assets"][asset] = {
            "zeitraum_start": werte["date"].min().date().isoformat(),
            "zeitraum_ende": werte["date"].max().date().isoformat(),
            "n_handelstage": int(len(handelstage)),
            "n_fomc": int(fomc_w.isin(handelstage).sum()),
            "n_ueberlappung": int(ueberlappung.isin(handelstage).sum()),
            "ueberlappungstage": [d.date().isoformat() for d in ueberlappung],
            "termine_ohne_handelstag": [d.date().isoformat() for d in ohne_handelstag],
        }
        if melde:
            melde(f"{asset} · Overnight-TR · {STAT} · FOMC")
        r = vergleich(
            werte,
            ereignis_w,
            cpi_w,
            stat=STAT,
            n_boot=n_boot,
            seed=seed_basis + seed_idx,
            alpha=ALPHA,
        )
        r.update(asset=asset, gruppe="fomc", primaer=(asset == primaer_asset))
        ergebnis["vergleiche"].append(r)
        seed_idx += 1
        if melde:
            melde(f"{asset} · Placebo · FOMC")
        r = placebo_vergleich(
            werte,
            ereignis_w,
            cpi_w,
            stat=STAT,
            n_boot=n_boot,
            seed=seed_basis + PLACEBO_SEED_OFFSET + placebo_idx,
            alpha=ALPHA,
        )
        r.update(asset=asset, gruppe="fomc")
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
    primaer_assets = ", ".join(v["asset"] for v in primaer)
    sekundaer_assets = ", ".join(v["asset"] for v in sekundaer)
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    sekundaer_pos = sum(1 for v in sekundaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in placebos if p["ki_low"] < 0 < p["ki_high"])
    fuer = {v["asset"]: v for v in vergleiche}

    z: list[str] = []
    z += [
        f"# B3 — Replikation `{EXPERIMENT_ID}`: Pre-FOMC-Announcement-Drift",
        "",
        f"**Generiert:** {generiert_utc} · **Commit:** `{commit}` · Erzeugt von "
        "`uv run python -m mie.es.b3_drift report` — nicht von Hand editieren.",
        "",
        f"**Frage (eingefroren):** {experiment['titel']} — ist die mittlere "
        "Overnight-Total-Return-Rendite (Overnight-TR, Schluss T−1 → Eröffnung T) von "
        "SPY/QQQ in den FOMC-Statement-Tag hinein höher als an Baseline-Tagen "
        "(Handelstage ohne FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein "
        "Unterschied. SPY = primäre Replikation (Paper-Index S&P 500), QQQ = sekundäre "
        "Erweiterung (nicht Teil des Paper-Befunds).",
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
        f"(davon {len(primaer)} primär: {primaer_assets}; {len(sekundaer)} sekundär: "
        f"{sekundaer_assets}) + {len(placebos)} Placebo-Tests (R4-Selbsttest der "
        "Pipeline, 1 je Asset). Alle werden vollständig berichtet — kein "
        "Auswahl-Reporting. Keine Mediane, keine Zusatzmaße, keine eigene "
        "CPI-Auswertung (nicht vorregistriert).",
        f"- **Bootstrap:** Perzentil-KI, n_boot={N_BOOT}, alpha={ALPHA}. Seeds vorab "
        f"fixiert (Paketplan 10.07.2026): Basis {SEED_BASIS}, Vergleiche fortlaufend "
        f"(Reihenfolge SPY → QQQ), Placebos ab Basis+{PLACEBO_SEED_OFFSET} "
        "fortlaufend.",
        "- **Maß** (Tiingo-Rohfelder, nie adj_close): Overnight-TR = "
        "(open_T + div_cash_T) · split_factor_T / close_(T−1) − 1 — Dividenden/Splits "
        "wirken am Ex-Tag zur Eröffnung, konsistent zur TR-Formel aus Ziel `w1_up_v1`.",
        "- **Ereignistage:** nur reguläre FOMC-Sitzungen (meeting_type=meeting), "
        "Statement-Tag = letzter Sitzungstag; Stichprobe ab Mai 1999 (Ära-Grenze der "
        "Statement-Zeiten 12:30–14:15 ET — die Eröffnung 09:30 ET liegt in allen Äras "
        "vor dem Statement, das Overnight-Fenster ist frei von der Statement-Reaktion).",
        "- **Baseline:** alle übrigen Handelstage ohne FOMC- und ohne CPI-Termin — "
        "CPI-Releases (08:30 ET) liegen im Overnight-Fenster und würden die Baseline "
        "kontaminieren.",
        "- **Überlappungsregel (anders als B1/B2):** Fällt ein FOMC-Statement-Tag mit "
        "einem CPI-Release zusammen, wird der Tag aus dem Haupttest ausgeschlossen "
        "(weder Ereignis noch Baseline) und unten gesondert ausgewiesen.",
        "",
        "## Datenversion (R3)",
        "",
    ]
    z += [
        f"- {d['label']}: sha256 `{d['sha256']}` · Stand {d['stand']} · n = {d['n']} {d['einheit']}"
        for d in datenversion
    ]
    z += [
        "",
        "## Stichprobe je Asset",
        "",
        "| Asset | Zeitraum (verwendet) | Handelstage | FOMC handelbar | davon FOMC=CPI "
        "| Ereignis (Haupttest) | CPI-Ausschluss | Baseline |",
        "|---|---|---|---|---|---|---|---|",
    ]
    z += [
        f"| {asset} | {a['zeitraum_start']} – {a['zeitraum_ende']} | {a['n_handelstage']} "
        f"| {a['n_fomc']} | {a['n_ueberlappung']} | {fuer[asset]['n_ereignis']} "
        f"| {fuer[asset]['n_ausgeschlossen']} | {fuer[asset]['n_baseline']} |"
        for asset, a in ergebnis["assets"].items()
    ]
    z += [
        "",
        "CPI-Ausschluss = alle handelbaren CPI-Tage inkl. Überlappung; Bilanz je Asset: "
        "Ereignis + Baseline + CPI-Ausschluss = Handelstage.",
        "",
        "Überlappungstage FOMC=CPI im Fenster — aus dem Haupttest ausgeschlossen und "
        "hier gesondert ausgewiesen (keine eigene Statistik, nicht vorregistriert):",
        "",
    ]
    z += [
        f"- {asset}: {' · '.join(a['ueberlappungstage']) or 'keine'}"
        for asset, a in ergebnis["assets"].items()
    ]
    z += [
        "",
        "FOMC-Ereignistage im Fenster ohne Handelstag im Kursframe (nicht still verworfen):",
        "",
    ]
    z += [
        f"- {asset}: {' · '.join(a['termine_ohne_handelstag']) or 'keine'}"
        for asset, a in ergebnis["assets"].items()
    ]
    z += [
        "",
        f"## Primäres Ergebnis — Mittelwert Overnight-TR ({primaer_assets}, Ereignis − Baseline)",
        "",
        *vergleichstabelle(primaer),
        "",
        f"## Sekundäres Ergebnis — Erweiterung {sekundaer_assets}",
        "",
        *vergleichstabelle(sekundaer),
        "",
        "## R4-Placebo (jahresgeschichtet, Mittelwert Overnight-TR)",
        "",
        "Je Kalenderjahr werden so viele zufällige Nicht-Ereignistage gezogen wie echte "
        "handelbare FOMC-Statement-Tage des Haupttests; echte FOMC-Tage und alle "
        "CPI-Tage bleiben komplett außen vor (wie im Haupttest). Erwartung: Differenz "
        "≈ 0, das KI überdeckt die 0 — konstruktionsbedingt verfehlt ein 95-%-KI die 0 "
        "aber in ~5 % der Ziehungen.",
        "",
        *placebo_tabelle(placebos),
        "",
        "## Zusammenfassung (automatisch aus den Zahlen)",
        "",
        f"- {primaer_pos} von {len(primaer)} primären 95-%-KIs ({primaer_assets}, "
        "Mittelwert Overnight-TR) liegen vollständig über 0.",
        f"- {sekundaer_pos} von {len(sekundaer)} sekundären 95-%-KIs "
        f"({sekundaer_assets}) liegen vollständig über 0.",
        f"- {placebo_null} von {len(placebos)} Placebo-KIs überdecken die 0.",
        "",
        "## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)",
        "",
        "1. **Tagesdaten statt Intraday:** Unser Overnight-Fenster (16:00 ET T−1 → "
        "09:30 ET T) erfasst nur einen Teil des Paper-Fensters (14:00 ET T−1 → "
        "Statement); der Drift-Anteil zwischen 09:30 und dem Statement fehlt. Ein "
        "Nullbefund widerlegt das Paper daher nicht automatisch — berichtet wird, was "
        "gemessen wurde.",
        "2. **ETF statt Index/Futures** (Tracking-Differenzen, Handelszeiten).",
        "3. **Zeitraum:** ab Mai 1999 (Ära-Grenze der Statement-Zeiten) statt 1994, "
        "bis 2024-12-31 (Lockbox-Stichtag) statt 2011. Ein mögliches Abklingen des "
        "Effekts nach der Paper-Stichprobe wird in der Literatur diskutiert und hier "
        "schlicht mitberichtet.",
        "",
        "## Einordnung",
        "",
        "Alle Werte sind friktionslos gerechnete (keine Kosten/Spreads) Modelloutputs/"
        "Szenarien aus einer historischen Ereignisstudie — keine Anlageempfehlung, "
        "keine Aussage über zukünftige Kurse. Zahlen stammen ausschließlich aus "
        "committetem Code auf lokal gecachten Rohdaten (R1); Reproduktion: "
        "`uv run python -m mie.es.b3_drift report` auf dem oben genannten Commit- und "
        "Datenstand.",
        "",
    ]
    return "\n".join(z)


# --- Registry-Zeile ---------------------------------------------------------------


def ergebnis_kurz(ergebnis: dict) -> str:
    """Ein-Satz-Ergebnis für registry/auswertungen.csv (ohne Komma/Quote, appendonly)."""
    teile = [
        f"{v['asset']} {'primaer' if v['primaer'] else 'sekundaer'} "
        f"{pp(v['delta'])}pp KI[{pp(v['ki_low'])};{pp(v['ki_high'])}]"
        for v in ergebnis["vergleiche"]
    ]
    primaer = [v for v in ergebnis["vergleiche"] if v["primaer"]]
    primaer_pos = sum(1 for v in primaer if v["ki_low"] > 0)
    placebo_null = sum(1 for p in ergebnis["placebos"] if p["ki_low"] < 0 < p["ki_high"])
    return (
        f"Mittelwert Overnight-TR Ereignis-Baseline FOMC: {'; '.join(teile)}; "
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
    print("  uv run python -m mie.es.b3_drift eintragen")
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
    parser = argparse.ArgumentParser(prog="mie.es.b3_drift", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report", help="eingefrorenen Plan rechnen und Report schreiben")
    sub.add_parser("eintragen", help="Auswertungszeile an registry/auswertungen.csv anhängen")
    args = parser.parse_args(argv)
    if args.cmd == "report":
        return cmd_report()
    return cmd_eintragen()


if __name__ == "__main__":
    sys.exit(main())
