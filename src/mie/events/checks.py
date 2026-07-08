"""Datenqualitäts-Checks für Terminlisten im Einheitsschema (A3).

Reine Termin-Hygiene — kein Kursbezug, keine Effektanalyse. Läuft wie in A2
über den vollen Zeitraum inkl. Lockbox (Beschluss 07.07.2026: auch der
Lockbox-Zeitraum braucht saubere Daten; hier wird nichts exploriert).
"""

import pandas as pd

from mie.checks import expected_trading_days


def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Zeilen mit doppeltem Datum je Ereignistyp (alle Vorkommen)."""
    return df[df.duplicated(subset=["event_type", "date"], keep=False)]


def check_weekend(df: pd.DataFrame) -> pd.DataFrame:
    """Termine an Samstagen/Sonntagen (bei US-Makroterminen unplausibel)."""
    return df[df["date"].dt.dayofweek >= 5]


def check_non_trading(
    df: pd.DataFrame, today: pd.Timestamp, trading_days: pd.DatetimeIndex | None = None
) -> pd.DataFrame:
    """Vergangene Termine an NYSE-Feiertagen/Wochenenden.

    Nur informativ: Makrotermine können theoretisch auf Börsenfeiertage fallen
    (BLS richtet sich nach Bundes-, nicht Börsenkalender). trading_days ist
    injizierbar (Tests, R4); Default ist der echte NYSE-Kalender.
    """
    past = df[df["date"] <= today]
    if len(past) == 0:
        return past
    if trading_days is None:
        trading_days = expected_trading_days(past["date"].min(), past["date"].max())
    return past[~past["date"].isin(trading_days)]


def per_year_counts(df: pd.DataFrame) -> pd.Series:
    """Anzahl Termine je Kalenderjahr."""
    return df["date"].dt.year.value_counts().sort_index()


def check_gaps_days(df: pd.DataFrame, max_days: int) -> pd.DataFrame:
    """Aufeinanderfolgende Termine mit Abstand > max_days (z. B. fehlender CPI-Monat).

    Ergebnis: Zeilen mit Vorgänger-Datum und Abstand in Tagen.
    """
    dates = df["date"].sort_values().reset_index(drop=True)
    diff = dates.diff().dt.days
    hits = diff > max_days
    return pd.DataFrame(
        {
            "prev_date": dates.shift(1)[hits],
            "date": dates[hits],
            "gap_days": diff[hits].astype(int),
        }
    )


def run_all(
    df: pd.DataFrame,
    today: pd.Timestamp,
    gap_max_days: int | None = None,
    trading_days: pd.DatetimeIndex | None = None,
) -> dict:
    """Alle Checks; kompakte Zusammenfassung mit Anzahl je Befund."""
    weekend = check_weekend(df)
    non_trading = check_non_trading(df, today, trading_days)
    result = {
        "n": len(df),
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
        "n_past": int((df["date"] <= today).sum()),
        "duplicates": len(check_duplicates(df)),
        "weekend": len(weekend),
        "weekend_days": [d.date().isoformat() for d in weekend["date"][:10]],
        "non_trading": len(non_trading),
        "non_trading_days": [d.date().isoformat() for d in non_trading["date"][:10]],
    }
    if gap_max_days is not None:
        gaps = check_gaps_days(df[df["date"] <= today], gap_max_days)
        result["gaps"] = len(gaps)
        result["gap_list"] = [
            f"{r.prev_date.date()} → {r.date.date()} ({r.gap_days} Tage)" for r in gaps.itertuples()
        ]
    return result


def fomc_scheduled_deviations(df: pd.DataFrame, today: pd.Timestamp) -> dict:
    """Reguläre FOMC-Sitzungen je abgeschlossenem Jahr; Abweichungen von 8 gelistet.

    Seit 1981 hält das FOMC 8 reguläre Sitzungen pro Jahr — Abweichungen sind
    Parsing- oder Quellenfehler (oder Sonderjahre wie 2020 mit abgesagter Sitzung).
    """
    scheduled = df[df["scheduled"] & (df["date"].dt.year < today.year)]
    counts = per_year_counts(scheduled)
    deviations = {int(y): int(n) for y, n in counts.items() if n != 8}
    return {"years": len(counts), "deviations": deviations}


def fomc_statement_crosscheck(df: pd.DataFrame, today: pd.Timestamp) -> dict:
    """Kreuzabgleich Kalendereintrag × verlinkte Pressemitteilung (statement_date).

    Erwartung: Bei regulären Sitzungen erscheint das Statement am letzten
    Sitzungstag. Vor Mai 1999 gab die Fed nur bei Zinsänderungen ein Statement
    heraus — fehlende Statements dort sind normal und werden getrennt gezählt.
    """
    past = df[df["scheduled"] & (df["date"] <= today)]
    routine = past[past["date"] >= "1999-05-18"]  # ab hier Statement nach jeder Sitzung
    early = past[past["date"] < "1999-05-18"]
    match = routine[routine["statement_date"] == routine["date"]]
    missing = routine[routine["statement_date"].isna()]
    mismatch = routine[
        routine["statement_date"].notna() & (routine["statement_date"] != routine["date"])
    ]
    return {
        "n_routine": len(routine),
        "n_match": len(match),
        "n_missing": len(missing),
        "missing_days": [d.date().isoformat() for d in missing["date"][:10]],
        "n_mismatch": len(mismatch),
        "mismatch_days": [
            f"{r.date.date()} (Statement {r.statement_date.date()})" for r in mismatch.itertuples()
        ][:10],
        "n_early": len(early),
        "n_early_with_statement": int((early["statement_date"] == early["date"]).sum()),
    }


def crosscheck_dates(a: pd.DataFrame, b: pd.DataFrame, name_a: str, name_b: str) -> dict:
    """Terminmengen zweier Quellen im Überlappungszeitraum vergleichen (exakte Gleichheit)."""
    start = max(a["date"].min(), b["date"].min())
    end = min(a["date"].max(), b["date"].max())
    set_a = set(a.loc[(a["date"] >= start) & (a["date"] <= end), "date"])
    set_b = set(b.loc[(b["date"] >= start) & (b["date"] <= end), "date"])
    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)
    return {
        "start": start,
        "end": end,
        "n_match": len(set_a & set_b),
        f"only_{name_a}": [d.date().isoformat() for d in only_a[:10]],
        f"n_only_{name_a}": len(only_a),
        f"only_{name_b}": [d.date().isoformat() for d in only_b[:10]],
        f"n_only_{name_b}": len(only_b),
    }
