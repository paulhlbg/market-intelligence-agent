"""Gemeinsame Runner-Bausteine der B-ES-Auswertungen (B1–B3).

Die Auswertungs-Runner (b1_volatilitaet, b2_praemie, …) teilen sich die immer
gleichen Schritte: Registry-Prüfung vor dem Rechnen (Registry konsistent,
Hypothese eingefroren, Fenster wie registriert), Laden der lokal gecachten
Rohdaten (kein Netz), Markdown-Ergebnistabellen und die Kurzform der
Datenversion für registry/auswertungen.csv. Hier steht keine Rechenlogik —
die liegt in mie.es.statistik und mie.es.masszahlen. Die Funktionen wurden
in B2 unverändert aus b1_volatilitaet.py hierher gezogen.
"""

import pandas as pd

from mie import registry
from mie.es import EsError
from mie.es.ereignistage import CPI_CSV, FOMC_CSV, load_cpi_days, load_fomc_days
from mie.sources import raw_paths, read_meta, tiingo

GRUPPEN_LABEL = {"fomc": "FOMC", "cpi": "CPI", "gepoolt": "gepoolt"}


def termine_im_fenster(termine: pd.DatetimeIndex, start: str, ende: str) -> pd.DatetimeIndex:
    return termine[(termine >= pd.Timestamp(start)) & (termine <= pd.Timestamp(ende))]


# --- Report-Tabellen ----------------------------------------------------------------


def pp(x: float) -> str:
    return f"{x * 100:+.3f}"


def vergleichstabelle(zeilen: list[dict]) -> list[str]:
    kopf = [
        "| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline "
        "| Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    return kopf + [
        f"| {v['asset']} | {GRUPPEN_LABEL[v['gruppe']]} | {v['n_ereignis']} | {v['n_baseline']} "
        f"| {v['ereignis_stat'] * 100:.3f} % | {v['baseline_stat'] * 100:.3f} % "
        f"| {pp(v['delta'])} | [{pp(v['ki_low'])}; {pp(v['ki_high'])}] "
        f"| {'ja' if v['ki_low'] > 0 else 'nein'} |"
        for v in zeilen
    ]


def placebo_tabelle(zeilen: list[dict]) -> list[str]:
    kopf = [
        "| Asset | Gruppe | n Placebo | n Baseline | Δ (P−B) in pp | 95-%-KI in pp | 0 im KI |",
        "|---|---|---|---|---|---|---|",
    ]
    return kopf + [
        f"| {p['asset']} | {GRUPPEN_LABEL[p['gruppe']]} | {p['n_placebo']} | {p['n_baseline']} "
        f"| {pp(p['delta'])} | [{pp(p['ki_low'])}; {pp(p['ki_high'])}] "
        f"| {'ja' if p['ki_low'] < 0 < p['ki_high'] else 'nein'} |"
        for p in zeilen
    ]


def data_version_kurz(datenversion: list[dict]) -> str:
    """Kurzform der Datenversion (volle SHA-256 stehen im Report)."""
    return "+".join(f"{d['schluessel']}={d['sha256'][:12]}" for d in datenversion)


# --- Registry-Prüfung und Laden der echten Daten (nur Cache, kein Netz) -------------


def pruefe_registry(experiment_id: str, registriertes_fenster: tuple[str, str]) -> dict:
    """Vor jeder Rechnung: Registry konsistent, Hypothese eingefroren, Fenster passt."""
    probleme = registry.check_registry()
    if probleme:
        raise EsError("Registry-Check fehlgeschlagen: " + " | ".join(probleme))
    experimente = registry.load_experiments().set_index("experiment_id")
    if experiment_id not in experimente.index:
        raise EsError(f"{experiment_id}: nicht in registry/experimente.csv registriert")
    zeile = experimente.loc[experiment_id].to_dict()
    zeile["experiment_id"] = experiment_id
    if (zeile["fenster_start"], zeile["fenster_ende"]) != registriertes_fenster:
        raise EsError(
            f"registriertes Fenster {zeile['fenster_start']} – {zeile['fenster_ende']} "
            f"weicht von {registriertes_fenster} ab — stoppen und Projektinhaber fragen"
        )
    return zeile


def lade_daten(tickers) -> tuple[dict, pd.DatetimeIndex, pd.DatetimeIndex, list[dict]]:
    """Kursframes je Ticker plus FOMC-/CPI-Termine und R3-Datenversion laden."""
    kursframes: dict[str, pd.DataFrame] = {}
    datenversion: list[dict] = []
    for ticker in tickers:
        raw_path, _ = raw_paths(tiingo.SOURCE, ticker, tiingo.EXT)
        kursframes[ticker] = tiingo.parse_cached(raw_path)
        meta = read_meta(tiingo.SOURCE, ticker, tiingo.EXT)
        datenversion.append(
            {
                "schluessel": f"tiingo_{ticker.lower()}",
                "label": f"Tiingo {ticker} (data/raw/tiingo/{ticker.lower()}_daily.json)",
                "sha256": meta["sha256"],
                "stand": meta["retrieved_utc"],
                "n": int(meta["rows"]),
                "einheit": "Zeilen",
            }
        )
    fomc = load_fomc_days()
    cpi = load_cpi_days()
    datenversion.append(
        {
            "schluessel": "fomc",
            "label": "FOMC-Termine (data/processed/fomc_termine.csv · nur meeting_type=meeting)",
            "sha256": registry.file_sha256(FOMC_CSV),
            "stand": "committet (A3)",
            "n": int(len(fomc)),
            "einheit": "reguläre Sitzungen",
        }
    )
    datenversion.append(
        {
            "schluessel": "cpi",
            "label": "CPI-Termine (data/processed/cpi_termine.csv · inkl. Korrektur 1998-02-24)",
            "sha256": registry.file_sha256(CPI_CSV),
            "stand": "committet (A3)",
            "n": int(len(cpi)),
            "einheit": "Release-Tage",
        }
    )
    return kursframes, fomc, cpi, datenversion
