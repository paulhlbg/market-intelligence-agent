"""B2-Runner-Tests — ausschließlich synthetische Mini-Daten (kein echter Kurs).

Getestet wird die Mechanik des Runners (Raster, Gruppenzählung, Determinismus,
Fenster-/Lockbox-Verhalten, Report-Pflichtfelder, appendonly-taugliche
Registry-Felder) plus ein Vorzeichen-Test für das erstmals vorzeichenbehaftete
Maß (eingebauter positiver Rendite-Shift muss gefunden werden, ohne Shift ≈ 0);
die statistischen Bausteine selbst sind in tests/test_es.py R4-validiert.
"""

import numpy as np
import pandas as pd
import pytest

from mie.es import EsError
from mie.es.b2_praemie import (
    EXPERIMENT_ID,
    auswertung,
    ergebnis_kurz,
    report_text,
)
from mie.es.runner import data_version_kurz


def kursframe(start: str, perioden: int, seed: int = 1) -> pd.DataFrame:
    tage = pd.bdate_range(start, periods=perioden)
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, size=perioden))
    return pd.DataFrame({"date": tage, "close": close, "div_cash": 0.0, "split_factor": 1.0})


def setup_daten(perioden: int = 500):
    """Zwei synthetische Assets, FOMC-/CPI-Termine mit genau einem Überlappungstag."""
    frames = {"S1": kursframe("2018-01-02", perioden, seed=1)}
    frames["S2"] = kursframe("2018-01-02", perioden, seed=2)
    tage = pd.DatetimeIndex(frames["S1"]["date"])
    fomc = tage[10::40]
    cpi = tage[5::30].union(tage[[10]])  # tage[10] ist auch FOMC → 1 Überlappungstag
    ende = tage.max().date().isoformat()
    fenster = {"S1": ("2018-01-02", ende), "S2": ("2018-01-02", ende)}
    return frames, fomc, cpi, fenster


def test_auswertung_raster_und_r3_felder():
    frames, fomc, cpi, fenster = setup_daten()
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=150, seed_basis=99)
    assert len(r["vergleiche"]) == 6  # 2 Assets × 3 Gruppen × 1 Statistik (Mittelwert)
    assert len(r["placebos"]) == 6  # 2 Assets × 3 Gruppen
    assert sum(1 for v in r["vergleiche"] if v["primaer"]) == 2  # gepoolt je Asset
    assert all(v["gruppe"] == "gepoolt" for v in r["vergleiche"] if v["primaer"])
    assert all(v["stat"] == "mittelwert" for v in r["vergleiche"])  # keine Mediane
    pflicht = [
        "delta",
        "ki_low",
        "ki_high",
        "n_ereignis",
        "n_baseline",
        "zeitraum_start",
        "zeitraum_ende",
        "stat",
        "seed",
        "n_boot",
    ]
    for v in r["vergleiche"]:
        assert all(k in v for k in pflicht)
    seeds = [v["seed"] for v in r["vergleiche"]]
    assert seeds == list(range(99, 99 + 6))  # vorab fixierte, fortlaufende Seeds
    assert [p["seed"] for p in r["placebos"]] == list(range(199, 199 + 6))


def test_auswertung_deterministisch():
    frames, fomc, cpi, fenster = setup_daten()
    a = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=7)
    b = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=7)
    assert a == b


def test_gruppenzaehlung_und_ueberlappung():
    frames, fomc, cpi, fenster = setup_daten()
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)
    a = r["assets"]["S1"]
    # Werteframes beginnen am 2. Handelstag; alle Termine hier liegen danach und
    # sind Handelstage → volle Zählung, Überlappung einmal in „gepoolt".
    assert a["n_ueberlappung"] == 1
    assert a["n_gepoolt"] == a["n_fomc"] + a["n_cpi"] - a["n_ueberlappung"]
    assert a["termine_ohne_handelstag"] == []
    fuer = {v["gruppe"]: v for v in r["vergleiche"] if v["asset"] == "S1"}
    assert fuer["gepoolt"]["n_ereignis"] == a["n_gepoolt"]
    assert fuer["fomc"]["n_ereignis"] == a["n_fomc"]
    # Baseline der getrennten Vergleiche: CPI-Tage ausgeschlossen (Überlappung zählt
    # dort als Ereignis, nicht als Ausschluss).
    assert fuer["fomc"]["n_ausgeschlossen"] == a["n_cpi"] - a["n_ueberlappung"]
    assert (
        fuer["fomc"]["n_ereignis"] + fuer["fomc"]["n_baseline"] + fuer["fomc"]["n_ausgeschlossen"]
        == a["n_handelstage"]
    )


def frames_mit_shift(shift: float, perioden: int = 500):
    """Zwei Assets, deren Tagesrendite an jedem Ereignistag um `shift` erhöht ist."""
    tage = pd.bdate_range("2018-01-02", periods=perioden)
    fomc_pos = np.arange(10, perioden, 40)
    cpi_pos = np.arange(25, perioden, 40)
    frames = {}
    for asset, seed in [("S1", 3), ("S2", 4)]:
        rng = np.random.default_rng(seed)
        r = rng.normal(0.0, 0.01, size=perioden)
        r[fomc_pos] += shift
        r[cpi_pos] += shift
        close = 100.0 * np.cumprod(1.0 + r)
        frames[asset] = pd.DataFrame(
            {"date": tage, "close": close, "div_cash": 0.0, "split_factor": 1.0}
        )
    ende = tage.max().date().isoformat()
    fenster = {"S1": ("2018-01-02", ende), "S2": ("2018-01-02", ende)}
    return frames, tage[fomc_pos], tage[cpi_pos], fenster


def test_vorzeichen_eingebauter_positiver_shift_wird_gefunden():
    # Pipeline-Test (synthetisch): +2 pp an Ereignistagen → primäres Δ deutlich > 0.
    frames, fomc, cpi, fenster = frames_mit_shift(0.02)
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=300, seed_basis=1)
    for v in r["vergleiche"]:
        if v["primaer"]:
            assert v["delta"] > 0.015
            assert v["ki_low"] > 0


def test_vorzeichen_ohne_shift_effekt_nahe_null():
    frames, fomc, cpi, fenster = frames_mit_shift(0.0)
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=300, seed_basis=1)
    for v in r["vergleiche"]:
        if v["primaer"]:
            assert abs(v["delta"]) < 0.005
            assert v["ki_low"] < 0 < v["ki_high"]


def test_lockbox_daten_werden_vor_dem_fenster_abgeschnitten():
    frames, fomc, cpi, _ = setup_daten(perioden=2000)  # reicht bis 2025 hinein
    assert frames["S1"]["date"].max() >= pd.Timestamp("2025-01-01")
    fenster = {"S1": ("2018-01-02", "2024-12-31"), "S2": ("2018-01-02", "2024-12-31")}
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)
    for v in r["vergleiche"]:
        assert v["zeitraum_ende"] <= "2024-12-31"  # Freigabeplan §6.3
    for a in r["assets"].values():
        assert a["zeitraum_ende"] <= "2024-12-31"


def test_fenster_in_lockbox_wird_verweigert():
    frames, fomc, cpi, _ = setup_daten(perioden=2000)
    fenster = {"S1": ("2018-01-02", "2025-01-31"), "S2": ("2018-01-02", "2025-01-31")}
    with pytest.raises(EsError, match="Lockbox"):
        auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)


def test_fehlendes_fenster_wird_verweigert():
    frames, fomc, cpi, fenster = setup_daten()
    del fenster["S2"]
    with pytest.raises(EsError, match="Fenster fehlt"):
        auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)


def fake_experiment() -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "titel": "Announcement-Day-Praemie an FOMC/CPI-Tagen (Savor/Wilson 2013)",
        "hypothese_datei": f"registry/hypothesen/{EXPERIMENT_ID}.md",
        "hypothese_sha256": "ab" * 32,
        "registered_utc": "2026-07-08T21:13:22+00:00",
        "fenster_start": "1994-02-04",
        "fenster_ende": "2024-12-31",
    }


def fake_datenversion() -> list[dict]:
    return [
        {
            "schluessel": "tiingo_s1",
            "label": "Tiingo S1 (synthetisch)",
            "sha256": "cd" * 32,
            "stand": "2026-07-08T22:03:10+00:00",
            "n": 500,
            "einheit": "Zeilen",
        }
    ]


def test_report_enthaelt_pflichtfelder():
    frames, fomc, cpi, fenster = setup_daten()
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)
    text = report_text(
        r, fake_datenversion(), fake_experiment(), "2026-07-10T12:00:00+00:00", "abc1234"
    )
    for pflicht in [
        "nicht von Hand editieren",
        "Commit:** `abc1234`",
        "sha256 `" + "ab" * 32 + "`",  # eingefrorene Hypothese
        "sha256 `" + "cd" * 32 + "`",  # Datenversion
        "1994-02-04 – 2024-12-31",
        "n Ereignis | n Baseline",  # R3: n je Gruppe
        "95-%-KI",
        "6 Vergleiche",
        "6 Placebo-Tests",
        "## R4-Placebo",
        "Keine Mediane, keine Spanne",  # eingefrorener Umfang, nicht mehr
        "vorzeichenbehaftet",
        "Arbeitsmarktbericht",  # Grenze 1: Teil-Terminset
        "Rohrendite statt Überrendite",  # Grenze 2
        "ETF statt breitem Marktportfolio",  # Grenze 3 inkl. Fenster/QQQ
        "keine Anlageempfehlung",
    ]:
        assert pflicht in text, f"fehlt im Report: {pflicht}"
    # Alle 12 Ergebnisse als Tabellenzeilen (kein Auswahl-Reporting) + 2 Stichprobenzeilen
    assert text.count("| S1 |") + text.count("| S2 |") == 14


def test_registry_felder_appendonly_tauglich_und_ehrlich():
    frames, fomc, cpi, fenster = setup_daten()
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)
    kurz = ergebnis_kurz(r)
    version = data_version_kurz(fake_datenversion())
    verboten = set(',"\n\r')  # appendonly.FORBIDDEN_CHARS
    assert not verboten & set(kurz)
    assert not verboten & set(version)
    assert "Mittelwert Tages-TR Ereignis-Baseline gepoolt:" in kurz
    assert "primaere KIs > 0:" in kurz
    assert "Placebo-KIs ueberdecken 0:" in kurz
    assert version == "tiingo_s1=" + "cd" * 6
