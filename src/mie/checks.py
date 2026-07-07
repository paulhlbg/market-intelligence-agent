"""Datenqualitäts-Checks für Tageskurs-Frames im Einheitsschema (A2).

Reine Datenhygiene — keine Kursmuster-Analyse. Läuft laut Beschluss vom
07.07.2026 über den vollen Zeitraum inkl. Lockbox (Begründung: auch der
Lockbox-Zeitraum muss saubere Daten haben; hier werden keine Effekte exploriert).
"""

import pandas as pd
import pandas_market_calendars as mcal


def expected_trading_days(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """NYSE-Handelstage (Kalender XNYS) im Bereich [start, end]."""
    cal = mcal.get_calendar("XNYS")
    sched = cal.schedule(start_date=start.date(), end_date=end.date())
    return pd.DatetimeIndex(sched.index)


def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen mit doppeltem Datum (alle Vorkommen)."""
    return df[df["date"].duplicated(keep=False)]


def check_gaps(df: pd.DataFrame, trading_days: pd.DatetimeIndex | None = None) -> pd.DatetimeIndex:
    """Handelstage ohne Datenzeile zwischen erstem und letztem Datum.

    trading_days ist injizierbar (Tests, R4: synthetische Daten mit bekannter Antwort);
    Default ist der echte NYSE-Kalender.
    """
    if trading_days is None:
        trading_days = expected_trading_days(df["date"].min(), df["date"].max())
    present = pd.DatetimeIndex(df["date"].unique())
    return trading_days.difference(present)


def check_extra_days(
    df: pd.DataFrame, trading_days: pd.DatetimeIndex | None = None
) -> pd.DatetimeIndex:
    """Datenzeilen an Nicht-Handelstagen (deutet auf Kalender- oder Quellfehler)."""
    if trading_days is None:
        trading_days = expected_trading_days(df["date"].min(), df["date"].max())
    present = pd.DatetimeIndex(df["date"].unique())
    return present.difference(trading_days)


def check_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen, die die OHLC-Ordnung verletzen (low ≤ open/close ≤ high, low ≤ high)."""
    bad = (
        (df["low"] > df[["open", "close"]].min(axis=1))
        | (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df["high"])
    )
    return df[bad]


def check_nonpositive(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen mit Preis ≤ 0 (roh oder adjustiert) — physikalisch unplausibel."""
    price_cols = ["open", "high", "low", "close", "adj_close"]
    return df[(df[price_cols] <= 0).any(axis=1)]


def check_zero_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen mit Volumen 0 (bei liquiden ETFs verdächtig, aber nicht zwingend falsch)."""
    return df[df["volume"] == 0]


def run_all(df: pd.DataFrame, trading_days: pd.DatetimeIndex | None = None) -> dict:
    """Alle Checks; kompakte Zusammenfassung mit Anzahl je Befund."""
    gaps = check_gaps(df, trading_days)
    extra = check_extra_days(df, trading_days)
    return {
        "n": len(df),
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
        "duplicates": len(check_duplicates(df)),
        "gaps": len(gaps),
        "gap_days": [d.date().isoformat() for d in gaps[:10]],
        "extra_days": len(extra),
        "extra_day_list": [d.date().isoformat() for d in extra[:10]],
        "ohlc_violations": len(check_ohlc(df)),
        "nonpositive": len(check_nonpositive(df)),
        "zero_volume": len(check_zero_volume(df)),
    }
