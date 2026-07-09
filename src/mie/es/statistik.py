"""Gruppenvergleich, Bootstrap-KI, Placebo-Ziehung und Lockbox-Schutz (B-ES).

Kernvergleich der eingefrorenen Auswertungspläne: Differenz einer Statistik
(Mittelwert oder Median) zwischen Ereignis- und Baseline-Tagen, mit
95-%-Konfidenzintervall per Bootstrap. (Bootstrap = wiederholtes zufälliges
Neu-Ziehen mit Zurücklegen je Gruppe, um die Unsicherheit der Differenz
abzuschätzen, ohne eine Verteilungsform anzunehmen.)

R4-Placebo: zufällig gezogene Nicht-Ereignistage, je Kalenderjahr in gleicher
Anzahl wie die echten (im Kursframe handelbaren) Termine — die
Jahres-Schichtung verhindert, dass ein Scheineffekt allein aus ungleicher
Jahresverteilung entsteht (Volatilitäts-Clustering).

Lockbox (CLAUDE.md §3.6): Jede vergleichende Funktion verweigert Daten ab
LOCKBOX_START — zugeschnitten wird ausdrücklich vorher (ohne_lockbox /
im_fenster), nichts wird still verworfen.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from mie.es import EsError
from mie.registry import LOCKBOX_START

_STATS = {"mittelwert": np.mean, "median": np.median}
_LOCKBOX_TS = pd.Timestamp(LOCKBOX_START)


def _dates(values: Iterable) -> pd.DatetimeIndex:
    as_list = list(values)
    if not as_list:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(pd.to_datetime(as_list)).normalize()


def pruefe_lockbox_frei(dates: pd.Series | pd.DatetimeIndex) -> None:
    """Verweigert jede Berechnung, sobald Daten ab LOCKBOX_START enthalten sind."""
    zu_spaet = pd.DatetimeIndex(dates)[pd.DatetimeIndex(dates) >= _LOCKBOX_TS]
    if len(zu_spaet):
        raise EsError(
            f"Lockbox-Verletzung: {len(zu_spaet)} Datenpunkt(e) ab {LOCKBOX_START} "
            f"(erster: {zu_spaet.min().date()}) — vorher mit ohne_lockbox()/im_fenster() "
            "zuschneiden (CLAUDE.md §3.6)."
        )


def ohne_lockbox(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen ab LOCKBOX_START entfernen (einzige zulässige Stelle dafür)."""
    return df.loc[df["date"] < _LOCKBOX_TS].reset_index(drop=True)


def im_fenster(df: pd.DataFrame, start: str, ende: str) -> pd.DataFrame:
    """Auf das registrierte Auswertungsfenster [start, ende] zuschneiden (inklusive).

    Fenster, die in den Lockbox-Zeitraum reichen, werden verweigert — eine
    Lockbox-Auswertung wäre ein eigener Beschluss mit eigenem, eingefrorenem Code.
    """
    if pd.Timestamp(ende) >= _LOCKBOX_TS:
        raise EsError(
            f"Fensterende {ende} reicht in den Lockbox-Zeitraum (ab {LOCKBOX_START}) — "
            "nicht Teil der B-ES-Freigabe."
        )
    if pd.Timestamp(start) > pd.Timestamp(ende):
        raise EsError(f"Fensterstart {start} liegt nach Fensterende {ende}")
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(ende))
    return df.loc[mask].reset_index(drop=True)


def _check_werte(werte: pd.DataFrame) -> None:
    missing = [c for c in ["date", "wert"] if c not in werte.columns]
    if missing:
        raise EsError(f"Werteframe: fehlende Spalten {missing}")
    if werte[["date", "wert"]].isna().any().any():
        raise EsError("Werteframe: NaN in date/wert")
    if werte["date"].duplicated().any():
        raise EsError("Werteframe: doppelte Handelstage")
    pruefe_lockbox_frei(werte["date"])


def split_groups(
    werte: pd.DataFrame,
    ereignistage: Iterable,
    ausschlusstage: Iterable = (),
) -> dict:
    """Werte in Ereignis- und Baseline-Gruppe teilen.

    Baseline = alle Handelstage, die weder Ereignis- noch Ausschlusstag sind.
    Ereignistage ohne Handelstag im Frame (z. B. Feiertags-Release) werden
    nicht still ignoriert, sondern ausgewiesen.
    """
    _check_werte(werte)
    ereignis_idx = _dates(ereignistage)
    ausschluss_idx = _dates(ausschlusstage)
    tage = pd.DatetimeIndex(werte["date"])

    ist_ereignis = tage.isin(ereignis_idx)
    ist_ausschluss = tage.isin(ausschluss_idx) & ~ist_ereignis
    ohne_handel = ereignis_idx[~ereignis_idx.isin(tage)]

    ereignis = werte.loc[ist_ereignis, "wert"].to_numpy(dtype=float)
    baseline = werte.loc[~ist_ereignis & ~ist_ausschluss, "wert"].to_numpy(dtype=float)
    if len(ereignis) == 0:
        raise EsError("Ereignisgruppe ist leer (kein Ereignistag im Werteframe)")
    if len(baseline) == 0:
        raise EsError("Baseline-Gruppe ist leer")
    return {
        "ereignis": ereignis,
        "baseline": baseline,
        "n_ereignis": int(len(ereignis)),
        "n_baseline": int(len(baseline)),
        "n_ausgeschlossen": int(ist_ausschluss.sum()),
        "termine_ohne_handelstag": [d.date().isoformat() for d in ohne_handel],
    }


def bootstrap_diff_ki(
    ereignis: np.ndarray,
    baseline: np.ndarray,
    stat: str,
    *,
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Perzentil-Bootstrap-KI der Differenz stat(Ereignis) − stat(Baseline)."""
    if stat not in _STATS:
        raise EsError(f"stat muss eines von {sorted(_STATS)} sein, nicht {stat!r}")
    stat_fn = _STATS[stat]
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        e = ereignis[rng.integers(0, len(ereignis), len(ereignis))]
        b = baseline[rng.integers(0, len(baseline), len(baseline))]
        diffs[i] = stat_fn(e) - stat_fn(b)
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def vergleich(
    werte: pd.DataFrame,
    ereignistage: Iterable,
    ausschlusstage: Iterable = (),
    *,
    stat: str = "mittelwert",
    n_boot: int = 10_000,
    seed: int,
    alpha: float = 0.05,
) -> dict:
    """Gruppenvergleich mit R3-Feldern: Delta, Bootstrap-KI, n je Gruppe, Zeitraum."""
    gruppen = split_groups(werte, ereignistage, ausschlusstage)
    stat_fn = _STATS.get(stat)
    if stat_fn is None:
        raise EsError(f"stat muss eines von {sorted(_STATS)} sein, nicht {stat!r}")
    ereignis_stat = float(stat_fn(gruppen["ereignis"]))
    baseline_stat = float(stat_fn(gruppen["baseline"]))
    ki_low, ki_high = bootstrap_diff_ki(
        gruppen["ereignis"], gruppen["baseline"], stat, n_boot=n_boot, seed=seed, alpha=alpha
    )
    return {
        "stat": stat,
        "delta": ereignis_stat - baseline_stat,
        "ki_low": ki_low,
        "ki_high": ki_high,
        "ereignis_stat": ereignis_stat,
        "baseline_stat": baseline_stat,
        "n_ereignis": gruppen["n_ereignis"],
        "n_baseline": gruppen["n_baseline"],
        "n_ausgeschlossen": gruppen["n_ausgeschlossen"],
        "termine_ohne_handelstag": gruppen["termine_ohne_handelstag"],
        "zeitraum_start": werte["date"].min().date().isoformat(),
        "zeitraum_ende": werte["date"].max().date().isoformat(),
        "n_boot": n_boot,
        "seed": seed,
        "alpha": alpha,
    }


def placebo_termine(
    handelstage: pd.Series | pd.DatetimeIndex,
    echte_termine: Iterable,
    *,
    seed: int,
    ausschlusstage: Iterable = (),
) -> pd.DatetimeIndex:
    """R4-Placebo: je Kalenderjahr so viele zufällige Nicht-Ereignistage ziehen,
    wie echte Termine in diesem Jahr im Kursframe handelbar sind (ohne Zurücklegen)."""
    tage = pd.DatetimeIndex(handelstage)
    pruefe_lockbox_frei(tage)
    echte = _dates(echte_termine)
    ausschluss = _dates(ausschlusstage)
    handelbar = echte[echte.isin(tage)]
    kandidaten = tage[~tage.isin(echte) & ~tage.isin(ausschluss)]

    rng = np.random.default_rng(seed)
    gezogen: list[np.ndarray] = []
    for jahr, anzahl in handelbar.year.value_counts().sort_index().items():
        pool = kandidaten[kandidaten.year == jahr].to_numpy()
        if len(pool) < anzahl:
            raise EsError(f"Placebo {jahr}: nur {len(pool)} Kandidatentage für {anzahl} Termine")
        gezogen.append(rng.choice(pool, size=int(anzahl), replace=False))
    if not gezogen:
        raise EsError("Placebo: kein echter Termin liegt im Kursframe")
    return pd.DatetimeIndex(np.sort(np.concatenate(gezogen)))


def placebo_vergleich(
    werte: pd.DataFrame,
    echte_termine: Iterable,
    ausschlusstage: Iterable = (),
    *,
    stat: str = "mittelwert",
    n_boot: int = 10_000,
    seed: int,
    alpha: float = 0.05,
) -> dict:
    """Vergleich mit Placebo- statt echten Terminen; echte Termine werden ausgeschlossen.

    Erwartung (R4): Differenz ≈ 0, das KI überdeckt 0 — sonst Leakage-Verdacht
    in Pipeline oder Gruppenbildung.
    """
    echte = _dates(echte_termine)
    ausschluss_idx = _dates(ausschlusstage)
    placebo = placebo_termine(werte["date"], echte, seed=seed, ausschlusstage=ausschluss_idx)
    ausschluss = sorted(set(echte).union(ausschluss_idx))
    ergebnis = vergleich(
        werte, placebo, ausschluss, stat=stat, n_boot=n_boot, seed=seed, alpha=alpha
    )
    ergebnis["n_placebo"] = int(len(placebo))
    return ergebnis
