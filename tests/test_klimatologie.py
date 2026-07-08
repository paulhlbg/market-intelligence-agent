"""Klimatologie v0 / Total-Return-Formel gegen Handrechnung (R4: bekannte richtige Antwort).

Handrechnung zum Mini-Datensatz (10 Tage, horizon 5): Tages-Bruttofaktor
g_t = (close_t + div_cash_t) · split_factor_t / close_{t−1}, Wealth-Index W = kumuliertes Produkt.

    Tag   close  div  split   g_t                     W
    0     100    0    1       —                       1
    1     102    0    1       102/100 = 1.02          1.02
    2      51    0    2       51·2/102 = 1            1.02      (Split neutralisiert)
    3      50    1    1       (50+1)/51 = 1           1.02      (Dividende gleicht Abschlag aus)
    4      52    0    1       52/50 = 1.04            1.0608
    5      53    0    1       53/52                   1.0812
    6      49    0    1       49/53                   0.9996
    7      51    0    1       51/49                   1.0404
    8      55    0    1       55/51                   1.122
    9      51    0    1       51/55                   1.0404

5-Tage-Fenster TR_i = W_{i+5}/W_i − 1:
    i0: 1.0812/1      − 1 = +0.0812   → 1
    i1: 0.9996/1.02   − 1 = −0.02     → 0
    i2: 1.0404/1.02   − 1 = +0.02     → 1
    i3: 1.122/1.02    − 1 = +0.10     → 1
    i4: 1.0404/1.0608 − 1 ≈ −0.019231 → 0
Basisrate = 3/5 = 0.6, n = 5.
"""

from pathlib import Path

import pandas as pd
import pytest

from mie.ledger.klimatologie import base_rate, wealth_index, window_return
from mie.sources import tiingo

FIXTURES = Path(__file__).parent / "fixtures"

HAND_CLOSE = [100.0, 102.0, 51.0, 50.0, 52.0, 53.0, 49.0, 51.0, 55.0, 51.0]
HAND_DIV = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
HAND_SPLIT = [1.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
HAND_WEALTH = [1.0, 1.02, 1.02, 1.02, 1.0608, 1.0812, 0.9996, 1.0404, 1.122, 1.0404]


def _frame(close, div=None, split=None, start="2024-01-02"):
    n = len(close)
    return pd.DataFrame(
        {
            "date": pd.bdate_range(start, periods=n),
            "close": close,
            "div_cash": div if div is not None else [0.0] * n,
            "split_factor": split if split is not None else [1.0] * n,
        }
    )


def hand_frame():
    return _frame(HAND_CLOSE, HAND_DIV, HAND_SPLIT)


def test_wealth_index_handrechnung():
    w = wealth_index(hand_frame())
    assert w.tolist() == pytest.approx(HAND_WEALTH)


def test_base_rate_handrechnung():
    result = base_rate(hand_frame())
    assert result["probability"] == pytest.approx(0.6)
    assert result["train_n"] == 5
    assert result["train_start"] == "2024-01-02"
    assert result["train_end"] == "2024-01-15"
    # Determinismus: gleicher Frame → identisches Ergebnis
    assert base_rate(hand_frame()) == result


def test_window_return_handrechnung():
    df = hand_frame()
    tr = window_return(df, df["date"].iloc[3], df["date"].iloc[8])  # W8/W3 − 1 = 1.122/1.02 − 1
    assert tr == pytest.approx(0.10)


def test_exakt_null_zaehlt_als_nicht_gestiegen():
    # Konstante Kurse ohne Dividende: alle Fenster-Returns exakt 0.0 → Ziel nie erfüllt.
    result = base_rate(_frame([100.0] * 7))
    assert result["probability"] == 0.0
    assert result["train_n"] == 2


def test_split_neutral_und_dividende_zaehlt():
    # 2:1-Split ohne Kursbewegung: TR = 50·2/100 − 1 = 0
    split_df = _frame([100.0, 50.0], split=[1.0, 2.0])
    assert window_return(split_df, split_df["date"].iloc[0], split_df["date"].iloc[1]) == (
        pytest.approx(0.0)
    )
    # Kurs fällt um den Dividendenabschlag: TR = (99+1)/100 − 1 = 0 (Preis-Return wäre −1 %)
    div_df = _frame([100.0, 99.0], div=[0.0, 1.0])
    assert window_return(div_df, div_df["date"].iloc[0], div_df["date"].iloc[1]) == (
        pytest.approx(0.0)
    )


def test_crosscheck_gegen_adj_close_fixture():
    """Plausibilisierung auf echtem Tiingo-Response: Ohne Dividende/Split im Fenster muss
    der Roh-Total-Return dem adj_close-Verhältnis entsprechen (gleicher Adjustierungsfaktor)."""
    df = tiingo.parse_bytes((FIXTURES / "tiingo_spy_sample.json").read_bytes())
    assert (df["div_cash"] == 0).all() and (df["split_factor"] == 1).all()
    tr_raw = window_return(df, df["date"].iloc[0], df["date"].iloc[-1])
    tr_adj = df["adj_close"].iloc[-1] / df["adj_close"].iloc[0] - 1.0
    assert tr_raw == pytest.approx(tr_adj, rel=1e-6)


def test_base_rate_btc_horizont7_handrechnung():
    """BTC-Zweig (btc_w1_up_v1): div_cash=0/split_factor=1 → Fenster-Return = Close-Verhältnis.

    9 Kalendertage, horizon 7 → 2 Fenster: 105/100 − 1 > 0 → 1; 99/101 − 1 < 0 → 0.
    Basisrate = 1/2 = 0.5.
    """
    close = [100.0, 101.0, 99.0, 98.0, 102.0, 103.0, 104.0, 105.0, 99.0]
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=9, freq="D"),  # Kalendertage, 24/7
            "close": close,
            "div_cash": [0.0] * 9,
            "split_factor": [1.0] * 9,
        }
    )
    result = base_rate(df, horizon=7)
    assert result["probability"] == pytest.approx(0.5)
    assert result["train_n"] == 2
    assert result["train_start"] == "2026-01-01"
    assert result["train_end"] == "2026-01-09"
    tr = window_return(df, df["date"].iloc[0], df["date"].iloc[7])
    assert tr == pytest.approx(0.05)  # 105/100 − 1: reines Close-Verhältnis


def test_zu_wenig_daten_und_unsortiert():
    with pytest.raises(ValueError, match="zu wenig Daten"):
        base_rate(_frame([100.0] * 5))
    df = hand_frame().iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="sortiert"):
        base_rate(df)
