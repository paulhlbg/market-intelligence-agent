"""Kreuzabgleich-Tests: synthetische Frames mit exakt bekannter Abweichung (R4-Geist).

Fenster überspannt bewusst den Lockbox-Stichtag 01.01.2025, damit die
getrennte Vor/Ab-Statistik geprüft wird.
"""

import pandas as pd
import pytest

from mie.crosscheck import crosscheck

PRE = ["2024-12-26", "2024-12-27", "2024-12-30", "2024-12-31"]
POST = ["2025-01-02", "2025-01-03"]


def make_frame(dates: list[str], close: list[float]) -> pd.DataFrame:
    d = pd.to_datetime(dates)
    return pd.DataFrame(
        {
            "date": d,
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "adj_close": close,
            "volume": [1_000_000] * len(d),
        }
    )


def test_known_deviations_and_lockbox_split():
    base = [100.0] * 6
    dev = base.copy()
    dev[2] = 100.2  # 2024-12-30: +0,2 % → über Toleranz (0,1 %)
    dev[5] = 100.05  # 2025-01-03: +0,05 % → innerhalb
    df_a = make_frame(PRE + POST, dev)
    df_b = make_frame(PRE + POST, base)

    r = crosscheck(df_a, df_b, "a", "b")

    assert r["n_overlap"] == 6
    s = r["close"]
    assert s["all"]["exceed"] == 1
    assert s["all"]["max"] == pytest.approx(0.002)
    assert s["pre_lockbox"]["n"] == 4
    assert s["pre_lockbox"]["exceed"] == 1
    assert s["post_lockbox"]["n"] == 2
    assert s["post_lockbox"]["exceed"] == 0
    assert s["post_lockbox"]["max"] == pytest.approx(0.0005)
    # adj_close hier identisch konstruiert → gleiche Statistik
    assert r["adj_close"]["all"]["exceed"] == 1


def test_partial_overlap_counted():
    df_a = make_frame(PRE + POST + ["2025-01-06"], [100.0] * 7)
    df_b = make_frame(PRE + POST, [100.0] * 6)
    r = crosscheck(df_a, df_b, "a", "b")
    assert r["n_overlap"] == 6
    assert r["only_a"] == 1
    assert r["only_b"] == 0
    assert r["close"]["all"]["exceed"] == 0


def test_identical_sources_zero_deviation():
    df = make_frame(PRE, [101.5, 102.0, 103.3, 99.9])
    r = crosscheck(df, df.copy(), "a", "b")
    assert r["close"]["all"]["median"] == 0.0
    assert r["close"]["all"]["max"] == 0.0
    assert r["close"]["all"]["exceed"] == 0
    assert r["close"]["post_lockbox"]["n"] == 0
    assert r["close"]["post_lockbox"]["median"] is None
