"""Parser-Tests auf eingefrorenen Fixtures — kein Netzzugriff.

Fixtures sind format-authentisch (Spalten/Feldnamen exakt wie von der Quelle),
die Werte synthetisch bzw. gerundet. Das Tiingo-Fixture wird beim R2-Mini-Check
durch 5 echte Datensätze ersetzt (probe --freeze-fixture) und so verifiziert.
"""

from pathlib import Path

from mie.sources import (
    STANDARD_COLUMNS,
    coinbase,
    tiingo,
    tiingo_crypto,
    validate_standard_frame,
    yahoo,
)

FIXTURES = Path(__file__).parent / "fixtures"

BTC_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def test_yahoo_parse_standard_schema():
    df = yahoo.parse_cached(FIXTURES / "yahoo_spy_sample.csv")
    assert list(df.columns) == STANDARD_COLUMNS
    assert len(df) == 3
    assert validate_standard_frame(df) == []
    assert df["date"].iloc[0].date().isoformat() == "2024-11-01"
    assert df["close"].iloc[2] > 576  # roher Close, nicht adjustiert
    assert df["adj_close"].iloc[2] < df["close"].iloc[2]


def test_tiingo_parse_standard_schema_plus_extras():
    # Fixture = 5 echte API-Datensätze (SPY 01.–07.11.2024), eingefroren am 07.07.2026
    # via `probe --source tiingo --freeze-fixture` — verifiziert das reale Response-Format.
    df = tiingo.parse_cached(FIXTURES / "tiingo_spy_sample.json")
    for col in STANDARD_COLUMNS:
        assert col in df.columns
    assert {"div_cash", "split_factor"} <= set(df.columns)
    assert len(df) == 5
    assert validate_standard_frame(df) == []
    # UTC-Zeitstempel der API wird zu naivem Tagesdatum
    assert df["date"].iloc[0].isoformat() == "2024-11-01T00:00:00"
    assert df["date"].iloc[4].isoformat() == "2024-11-07T00:00:00"
    # Fenster ohne Ex-Dividende/Split (SPY-Q4-Ausschüttung erst im Dezember)
    assert (df["div_cash"] == 0).all()
    assert (df["split_factor"] == 1).all()
    # Adjustierte Kurse liegen vor der Dezember-Dividende unter den rohen
    assert (df["adj_close"] < df["close"]).all()


def test_tiingo_crypto_parse():
    # Fixture = 5 echte API-Datensätze (BTC 01.–05.06.2026), eingefroren am 08.07.2026
    # via `mie.a6_btc_quellen probe --freeze-fixture` — verifiziert das reale Response-Format
    # (ein Ticker-Objekt mit verschachteltem priceData, UTC-Mitternachts-Stempel).
    df = tiingo_crypto.parse_cached(FIXTURES / "tiingo_crypto_btcusd_sample.json")
    assert list(df.columns) == BTC_COLUMNS
    assert len(df) == 5
    assert df["date"].iloc[0].isoformat() == "2026-06-01T00:00:00"
    assert df["date"].is_monotonic_increasing
    assert (df["close"] > 0).all()


def test_coinbase_parse():
    # Fixture = 5 echte Kerzen (BTC-USD 01.–05.06.2026), eingefroren am 08.07.2026 —
    # verifiziert das reale Format [time, low, high, open, close, volume],
    # time = Bucket-Start in Epochensekunden UTC.
    df = coinbase.parse_cached(FIXTURES / "coinbase_btcusd_sample.json")
    assert list(df.columns) == BTC_COLUMNS
    assert len(df) == 5
    assert df["date"].iloc[0].isoformat() == "2026-06-01T00:00:00"
    assert df["date"].is_monotonic_increasing
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()


def test_validate_standard_frame_detects_problems():
    df = tiingo.parse_cached(FIXTURES / "tiingo_spy_sample.json")
    assert validate_standard_frame(df.drop(columns=["close"])) != []
    assert validate_standard_frame(df.iloc[0:0]) != []
    unsorted = df.sort_values("date", ascending=False).reset_index(drop=True)
    assert validate_standard_frame(unsorted) != []
