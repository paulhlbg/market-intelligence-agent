"""B0-Validierung der Ereignisstudien-Pipeline (R4) — nur synthetische Daten/Fixtures.

Handrechnung zum 5-Tage-Kursframe (Split- und Dividenden-Tag enthalten):

    Tag  open   high   low   close  div  split
    0    99.0   101.0  98.0  100.0  0    1
    1    101.0  104.0  100.0 102.0  0    1
    2    50.0   52.0   49.5  51.0   0    2     (2:1-Split)
    3    50.5   51.0   49.0  50.0   1    1     (Dividende 1)
    4    50.0   52.5   50.0  52.0   0    1

    Tages-TR:     102/100−1 = 0.02 · 51·2/102−1 = 0 · (50+1)/51−1 = 0 · 52/50−1 = 0.04
    Overnight-TR: 101/100−1 = 0.01 · 50·2/102−1 = −2/102 · (50.5+1)/51−1 = 0.5/51 · 50/50−1 = 0
    Spanne:       4/100 = 0.04 · 2.5·2/102 = 5/102 · 2/51 · 2.5/50 = 0.05

R4-Selbsttests: synthetische Reihe mit eingebautem bekannten Effekt (Pipeline
muss ihn finden) und ohne Effekt (≈ 0); Shuffle zerstört die Datum-Zuordnung
(Effekt muss verschwinden); Placebo-Termine zeigen ≈ 0; Lockbox-Cutoff greift.
"""

import numpy as np
import pandas as pd
import pytest

from mie.es import EsError
from mie.es.ereignistage import load_cpi_days, load_fomc_days
from mie.es.masszahlen import abs_tages_tr, overnight_tr, spanne, tages_tr
from mie.es.statistik import (
    im_fenster,
    ohne_lockbox,
    placebo_termine,
    placebo_vergleich,
    split_groups,
    vergleich,
)
from mie.ledger.klimatologie import wealth_index

# --- Messgrößen: Handrechnung -------------------------------------------------


def preis_frame():
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-02", periods=5),
            "open": [99.0, 101.0, 50.0, 50.5, 50.0],
            "high": [101.0, 104.0, 52.0, 51.0, 52.5],
            "low": [98.0, 100.0, 49.5, 49.0, 50.0],
            "close": [100.0, 102.0, 51.0, 50.0, 52.0],
            "div_cash": [0.0, 0.0, 0.0, 1.0, 0.0],
            "split_factor": [1.0, 1.0, 2.0, 1.0, 1.0],
        }
    )


def test_tages_tr_handrechnung():
    out = tages_tr(preis_frame())
    assert out["wert"].tolist() == pytest.approx([0.02, 0.0, 0.0, 0.04])
    assert len(out) == 4  # erster Tag entfällt (kein Vortagesschluss)
    assert out["date"].iloc[0] == pd.Timestamp("2024-01-03")


def test_abs_tages_tr_handrechnung():
    df = preis_frame()
    df.loc[4, "close"] = 48.0  # 48/50−1 = −0.04 → Betrag 0.04
    assert abs_tages_tr(df)["wert"].tolist() == pytest.approx([0.02, 0.0, 0.0, 0.04])


def test_overnight_tr_handrechnung():
    out = overnight_tr(preis_frame())
    assert out["wert"].tolist() == pytest.approx([0.01, -2 / 102, 0.5 / 51, 0.0])


def test_spanne_handrechnung():
    out = spanne(preis_frame())
    assert out["wert"].tolist() == pytest.approx([0.04, 5 / 102, 2 / 51, 0.05])


def test_tages_tr_konsistent_mit_wealth_index():
    """Kumuliertes Produkt der (1 + Tages-TR) muss den A4-Wealth-Index reproduzieren
    (dieselbe TR-Formel wie w1_up_v1, nur tageweise statt als Fenster)."""
    df = preis_frame()
    kum = np.cumprod(1.0 + tages_tr(df)["wert"].to_numpy())
    w = wealth_index(df).to_numpy()
    assert kum.tolist() == pytest.approx((w[1:] / w[0]).tolist())


def test_masszahlen_verweigern_kaputte_frames():
    df = preis_frame()
    with pytest.raises(EsError, match="fehlende Spalten"):
        overnight_tr(df.drop(columns=["open"]))
    with pytest.raises(EsError, match="sortiert"):
        tages_tr(df.iloc[::-1].reset_index(drop=True))
    df_nan = preis_frame()
    df_nan.loc[2, "close"] = np.nan
    with pytest.raises(EsError, match="NaN"):
        tages_tr(df_nan)
    with pytest.raises(EsError, match="mindestens 2"):
        tages_tr(df.iloc[:1])


# --- Ereignistag-Loader (synthetische Mini-CSVs) --------------------------------


def test_load_fomc_nur_regulaere_sitzungen(tmp_path):
    p = tmp_path / "fomc.csv"
    p.write_text(
        "event_type,date,meeting_start,meeting_type,scheduled,sep,statement_date,source\n"
        "fomc,1994-02-04,1994-02-03,meeting,True,,1994-02-04,fed\n"
        "fomc,1994-02-28,1994-02-28,conference_call,False,,,fed\n"
        "fomc,2020-03-15,2020-03-15,unscheduled,False,,2020-03-15,fed\n"
        "fomc,1994-03-22,1994-03-22,meeting,True,,1994-03-22,fed\n"
    )
    days = load_fomc_days(p)
    assert list(days) == [pd.Timestamp("1994-02-04"), pd.Timestamp("1994-03-22")]


def test_load_cpi_mit_februar_1998_korrektur(tmp_path):
    p = tmp_path / "cpi.csv"
    p.write_text(
        "event_type,date,ref_month,time_et,scheduled,source\n"
        "cpi,1998-01-13,1997-12,,True,bls\n"
        "cpi,1998-02-25,1998-01,,True,bls\n"
    )
    days = load_cpi_days(p)
    # a3_quellen.md §2.6: BLS-Archiv-Dateiname falsch, korrekt ist der 24.02.1998
    assert list(days) == [pd.Timestamp("1998-01-13"), pd.Timestamp("1998-02-24")]


def test_loader_verweigert_fehlende_datei_und_spalten(tmp_path):
    with pytest.raises(EsError, match="fehlt"):
        load_fomc_days(tmp_path / "gibts_nicht.csv")
    p = tmp_path / "fomc.csv"
    p.write_text("event_type,date\nfomc,1994-02-04\n")
    with pytest.raises(EsError, match="fehlende Spalten"):
        load_fomc_days(p)


# --- Gruppenbildung -------------------------------------------------------------


def test_split_groups_handrechnung():
    tage = pd.bdate_range("2024-01-01", periods=10)  # 1.–5. und 8.–12. Januar
    werte = pd.DataFrame({"date": tage, "wert": np.arange(10.0)})
    ereignis = [tage[2], tage[6], pd.Timestamp("2024-01-06")]  # 06.01. ist ein Samstag
    gruppen = split_groups(werte, ereignis, ausschlusstage=[tage[4]])
    assert gruppen["n_ereignis"] == 2
    assert gruppen["ereignis"].tolist() == [2.0, 6.0]
    assert gruppen["n_ausgeschlossen"] == 1
    assert gruppen["n_baseline"] == 7
    assert gruppen["termine_ohne_handelstag"] == ["2024-01-06"]


def test_split_groups_verweigert_leere_gruppen():
    werte = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=5), "wert": [0.0] * 5})
    with pytest.raises(EsError, match="Ereignisgruppe ist leer"):
        split_groups(werte, [pd.Timestamp("2024-06-01")])


# --- R4: synthetische Daten mit bekannter Antwort, Shuffle, Placebo --------------


def synthetische_reihe(effekt: float, seed: int = 7):
    """1100 Handelstage 2015–2019, Rauschen N(0, 0.01); jeder 11. Tag ist „Termin".

    Auf Termintagen wird `effekt` addiert — die richtige Antwort ist also bekannt.
    """
    tage = pd.bdate_range("2015-01-02", periods=1100)
    rng = np.random.default_rng(seed)
    werte = rng.normal(0.0, 0.01, size=len(tage))
    termine = tage[::11]  # 100 Termine, über alle Jahre verteilt
    werte = werte + effekt * tage.isin(termine)
    return pd.DataFrame({"date": tage, "wert": werte}), termine


def test_bekannter_effekt_wird_gefunden():
    werte, termine = synthetische_reihe(effekt=0.01)
    r = vergleich(werte, termine, n_boot=2000, seed=1)
    assert r["delta"] == pytest.approx(0.01, abs=0.004)
    assert r["ki_low"] > 0  # KI schließt 0 aus
    assert r["n_ereignis"] == 100
    assert r["n_baseline"] == 1000
    assert r["stat"] == "mittelwert"


def test_ohne_effekt_ergebnis_nahe_null():
    werte, termine = synthetische_reihe(effekt=0.0)
    r = vergleich(werte, termine, n_boot=2000, seed=2)
    assert abs(r["delta"]) < 0.004
    assert r["ki_low"] < 0 < r["ki_high"]  # KI überdeckt 0


def test_shuffle_zerstoert_effekt():
    werte, termine = synthetische_reihe(effekt=0.01)
    rng = np.random.default_rng(3)
    werte["wert"] = rng.permutation(werte["wert"].to_numpy())
    r = vergleich(werte, termine, n_boot=2000, seed=3)
    assert abs(r["delta"]) < 0.005
    assert r["ki_low"] < 0 < r["ki_high"]


def test_placebo_vergleich_nahe_null_trotz_echtem_effekt():
    werte, termine = synthetische_reihe(effekt=0.01)
    r = placebo_vergleich(werte, termine, n_boot=2000, seed=4)
    # ≈ 0 statt des echten Effekts 0.01. Bewusst keine KI-Überdeckungs-Prüfung:
    # ein 95-%-KI verfehlt die 0 konstruktionsbedingt in ~5 % der Ziehungen.
    assert abs(r["delta"]) < 0.004
    assert r["n_placebo"] == 100
    assert r["n_ereignis"] == 100  # Placebo-Gruppe
    assert r["n_ausgeschlossen"] == 100  # echte Termine bleiben komplett außen vor


def test_placebo_termine_jahresgeschichtet_und_deterministisch():
    tage = pd.bdate_range("2020-01-01", "2022-12-31")
    echte = [
        pd.Timestamp("2020-03-16"),
        pd.Timestamp("2020-06-15"),
        pd.Timestamp("2020-09-15"),
        pd.Timestamp("2021-03-15"),
        pd.Timestamp("2021-06-15"),
        pd.Timestamp("2022-01-08"),  # Samstag → kein Handelstag → zählt nicht
    ]
    placebo = placebo_termine(tage, echte, seed=11)
    assert len(placebo) == 5
    assert (placebo.year == 2020).sum() == 3  # je Jahr so viele wie echte handelbare Termine
    assert (placebo.year == 2021).sum() == 2
    assert (placebo.year == 2022).sum() == 0
    assert not placebo.isin(echte).any()
    assert placebo.isin(tage).all()
    assert placebo.equals(placebo_termine(tage, echte, seed=11))  # deterministisch
    assert not placebo.equals(placebo_termine(tage, echte, seed=12))


def test_vergleich_deterministisch_bei_gleichem_seed():
    werte, termine = synthetische_reihe(effekt=0.01)
    assert vergleich(werte, termine, n_boot=500, seed=9) == vergleich(
        werte, termine, n_boot=500, seed=9
    )


def test_vergleich_median_und_unbekannte_statistik():
    werte, termine = synthetische_reihe(effekt=0.01)
    r = vergleich(werte, termine, stat="median", n_boot=500, seed=5)
    assert r["stat"] == "median"
    with pytest.raises(EsError, match="stat muss"):
        vergleich(werte, termine, stat="quatsch", n_boot=500, seed=5)


# --- Lockbox-Cutoff (CLAUDE.md §3.6) ---------------------------------------------


def lockbox_frame():
    tage = pd.date_range("2024-12-27", "2025-01-05")
    return pd.DataFrame({"date": tage, "wert": np.zeros(len(tage))})


def test_ohne_lockbox_schneidet_ab_stichtag():
    df = ohne_lockbox(lockbox_frame())
    assert df["date"].max() == pd.Timestamp("2024-12-31")
    assert len(df) == 5


def test_vergleich_verweigert_lockbox_daten():
    df = lockbox_frame()
    with pytest.raises(EsError, match="Lockbox"):
        vergleich(df, [pd.Timestamp("2024-12-30")], n_boot=100, seed=1)


def test_placebo_verweigert_lockbox_daten():
    df = lockbox_frame()
    with pytest.raises(EsError, match="Lockbox"):
        placebo_termine(df["date"], [pd.Timestamp("2024-12-30")], seed=1)


def test_im_fenster_inklusive_und_lockbox_grenze():
    df = ohne_lockbox(lockbox_frame())
    fenster = im_fenster(df, "2024-12-28", "2024-12-30")
    assert fenster["date"].tolist() == [
        pd.Timestamp("2024-12-28"),
        pd.Timestamp("2024-12-29"),
        pd.Timestamp("2024-12-30"),
    ]
    with pytest.raises(EsError, match="Lockbox"):
        im_fenster(df, "2024-12-01", "2025-01-02")
    with pytest.raises(EsError, match="nach Fensterende"):
        im_fenster(df, "2024-12-30", "2024-12-28")
