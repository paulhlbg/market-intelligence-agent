"""Checks-Tests mit synthetischen Daten und bekannter richtiger Antwort (R4-Geist).

Der Handelskalender wird injiziert, damit die Tests deterministisch und
netzunabhängig sind; ein separater Test prüft den echten XNYS-Kalender
an einem festen, bekannten Zeitfenster.
"""

import pandas as pd

from mie import checks

# 5 fiktive Handelstage als injizierter Kalender
DAYS = pd.DatetimeIndex(
    pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
)


def make_frame(dates: list[str]) -> pd.DataFrame:
    d = pd.to_datetime(dates)
    n = len(d)
    return pd.DataFrame(
        {
            "date": d,
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.5] * n,
            "adj_close": [100.5] * n,
            "volume": [1_000_000] * n,
        }
    )


def test_gap_found():
    df = make_frame(["2024-01-02", "2024-01-03", "2024-01-05", "2024-01-08"])  # 04 fehlt
    gaps = checks.check_gaps(df, trading_days=DAYS)
    assert [g.date().isoformat() for g in gaps] == ["2024-01-04"]


def test_extra_day_found():
    df = make_frame(["2024-01-02", "2024-01-03", "2024-01-06"])  # 06 = Samstag
    extra = checks.check_extra_days(df, trading_days=DAYS)
    assert [e.date().isoformat() for e in extra] == ["2024-01-06"]


def test_duplicate_found():
    df = make_frame(["2024-01-02", "2024-01-03", "2024-01-03"])
    assert len(checks.check_duplicates(df)) == 2  # beide Vorkommen


def test_ohlc_violation_found():
    df = make_frame(["2024-01-02", "2024-01-03"])
    df.loc[1, "high"] = 100.0  # high < close (100.5) → Verstoß
    bad = checks.check_ohlc(df)
    assert len(bad) == 1
    assert bad["date"].iloc[0].date().isoformat() == "2024-01-03"


def test_nonpositive_and_zero_volume_found():
    df = make_frame(["2024-01-02", "2024-01-03", "2024-01-04"])
    df.loc[0, "low"] = -1.0
    df.loc[2, "volume"] = 0
    assert len(checks.check_nonpositive(df)) == 1
    assert len(checks.check_zero_volume(df)) == 1


def test_run_all_counts():
    df = make_frame(["2024-01-02", "2024-01-03", "2024-01-05", "2024-01-08"])
    result = checks.run_all(df, trading_days=DAYS)
    assert result["n"] == 4
    assert result["gaps"] == 1
    assert result["gap_days"] == ["2024-01-04"]
    assert result["duplicates"] == 0
    assert result["ohlc_violations"] == 0


def test_real_xnys_calendar_known_week():
    """Echter Kalender, festes Fenster: Weihnachtswoche 2023 (25.12. geschlossen)."""
    days = checks.expected_trading_days(pd.Timestamp("2023-12-22"), pd.Timestamp("2023-12-29"))
    iso = [d.date().isoformat() for d in days]
    assert iso == ["2023-12-22", "2023-12-26", "2023-12-27", "2023-12-28", "2023-12-29"]
