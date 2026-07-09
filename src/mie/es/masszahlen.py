"""Tagesbezogene Messgrößen der Ereignisstudie (Tiingo-Rohfelder).

Die Formeln stammen wörtlich aus den eingefrorenen Hypothesen-Dateien
(registry/hypothesen/rep_*.md) und rechnen ausschließlich mit den Rohfeldern
open/high/low/close/div_cash/split_factor — nie mit adj_close (rückwirkende
Neuberechnung, s. docs/zieldefinitionen.md). Dividenden/Splits wirken am
Ex-Tag, wie in der Total-Return-Formel von w1_up_v1.

Jede Funktion liefert einen Frame mit den Spalten date/wert ab dem zweiten
Handelstag — der erste Tag hat keinen Vortagesschluss.
"""

import pandas as pd

from mie.es import EsError

_BASE = ["date", "close", "div_cash", "split_factor"]


def _check_frame(df: pd.DataFrame, needed: list[str]) -> None:
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise EsError(f"Kursframe: fehlende Spalten {missing}")
    if df[needed].isna().any().any():
        raise EsError(f"Kursframe: NaN in {needed}")
    if len(df) < 2:
        raise EsError("Kursframe: mindestens 2 Handelstage nötig (Vortagesschluss)")
    if not df["date"].is_monotonic_increasing:
        raise EsError("Kursframe: date nicht aufsteigend sortiert")
    if df["date"].duplicated().any():
        raise EsError("Kursframe: doppelte Handelstage")


def _result(df: pd.DataFrame, werte: pd.Series) -> pd.DataFrame:
    out = pd.DataFrame({"date": df["date"], "wert": werte.astype(float)})
    return out.iloc[1:].reset_index(drop=True)


def tages_tr(df: pd.DataFrame) -> pd.DataFrame:
    """Tages-Total-Return: (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1."""
    _check_frame(df, _BASE)
    gross = (df["close"] + df["div_cash"]) * df["split_factor"] / df["close"].shift(1)
    return _result(df, gross - 1.0)


def abs_tages_tr(df: pd.DataFrame) -> pd.DataFrame:
    """|Tages-Total-Return| — primäres Volatilitätsmaß (rep_ereignistag_volatilitaet)."""
    out = tages_tr(df)
    out["wert"] = out["wert"].abs()
    return out


def overnight_tr(df: pd.DataFrame) -> pd.DataFrame:
    """Overnight-Total-Return: (open_T + div_cash_T) · split_factor_T / close_(T−1) − 1."""
    _check_frame(df, [*_BASE, "open"])
    gross = (df["open"] + df["div_cash"]) * df["split_factor"] / df["close"].shift(1)
    return _result(df, gross - 1.0)


def spanne(df: pd.DataFrame) -> pd.DataFrame:
    """Intraday-Spanne (high_T − low_T) · split_factor_T / close_(T−1).

    Sekundäres Volatilitätsmaß; an Split-Tagen mit split_factor normiert,
    analog zur TR-Formel (rep_ereignistag_volatilitaet).
    """
    _check_frame(df, [*_BASE, "high", "low"])
    werte = (df["high"] - df["low"]) * df["split_factor"] / df["close"].shift(1)
    return _result(df, werte)
