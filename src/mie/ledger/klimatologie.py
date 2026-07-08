"""Modell klimatologie_v0 und Total-Return-Rechnung der Zieldefinition w1_up_v1.

Total-Return = Kursveränderung inklusive Dividenden (sofortige Wiederanlage),
berechnet ausschließlich aus Tiingo-Rohfeldern close/div_cash/split_factor —
NICHT aus adj_close (rückwirkende Neuberechnung, s. docs/zieldefinitionen.md).

Die Basisrate nutzt alle zum Prognosezeitpunkt verfügbaren Daten, auch ab
01.01.2025: Live-Prognose-Input ist laut Lockbox-Regel (CLAUDE.md §3.6)
ausdrücklich erlaubt; gesperrt ist Exploration/Auswertung.
"""

import pandas as pd

HORIZON_TRADING_DAYS = 5  # „1 Woche" laut Festlegung vom 08.07.2026

_NEEDED = ["date", "close", "div_cash", "split_factor"]


def _check_frame(df: pd.DataFrame) -> None:
    missing = [c for c in _NEEDED if c not in df.columns]
    if missing:
        raise ValueError(f"Kursframe: fehlende Spalten {missing}")
    if df[_NEEDED].isna().any().any():
        raise ValueError("Kursframe: NaN in date/close/div_cash/split_factor")
    if not df["date"].is_monotonic_increasing:
        raise ValueError("Kursframe: date nicht aufsteigend sortiert")


def wealth_index(df: pd.DataFrame) -> pd.Series:
    """Total-Return-Index W: W_0 = 1, W_t = W_{t-1} · (close_t + div_cash_t) · sf_t / close_{t-1}.

    Splits sind damit neutralisiert (sf = split_factor), Dividenden gehen am
    Ex-Tag ein; der Fenster-Total-Return zwischen zwei Tagen ist W_ende/W_start − 1.
    """
    gross = (df["close"] + df["div_cash"]) * df["split_factor"] / df["close"].shift(1)
    return gross.fillna(1.0).cumprod()  # erster Tag hat keinen Vortag → Faktor 1


def window_return(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
    """Total-Return vom Schlusskurs start_date zum Schlusskurs end_date (w1_up_v1-Formel)."""
    _check_frame(df)
    w = wealth_index(df)

    def _pos(d: pd.Timestamp) -> int:
        hits = df.index[df["date"] == pd.Timestamp(d)]
        if len(hits) != 1:
            raise ValueError(f"Datum {pd.Timestamp(d).date()} nicht (eindeutig) im Kursframe")
        return hits[0]

    i, j = _pos(start_date), _pos(end_date)
    if j <= i:
        raise ValueError("end_date muss nach start_date liegen")
    return float(w.loc[j] / w.loc[i] - 1.0)


def base_rate(df: pd.DataFrame, horizon: int = HORIZON_TRADING_DAYS) -> dict:
    """Basisrate: Anteil der überlappenden `horizon`-Tage-Fenster mit Total-Return > 0.

    Fenster: jeder Handelstag t mit t+horizon im Frame ist ein Ankertag.
    Rückgabe mit R3-nahen Feldern (n, Zeitraum); probability auf 4 Stellen gerundet.
    """
    _check_frame(df)
    if len(df) <= horizon:
        raise ValueError(f"zu wenig Daten für Horizont {horizon} ({len(df)} Zeilen)")
    w = wealth_index(df).to_numpy()
    tr = w[horizon:] / w[:-horizon] - 1.0
    return {
        "probability": round(float((tr > 0).mean()), 4),
        "train_n": len(tr),
        "train_start": df["date"].iloc[0].date().isoformat(),
        "train_end": df["date"].iloc[-1].date().isoformat(),
    }
