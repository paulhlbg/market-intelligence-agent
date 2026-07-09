"""B1-Runner-Tests — ausschließlich synthetische Mini-Daten (kein echter Kurs).

Getestet wird die Mechanik des Runners (Raster, Gruppenzählung, Determinismus,
Fenster-/Lockbox-Verhalten, Report-Pflichtfelder, appendonly-taugliche
Registry-Felder); die statistischen Bausteine selbst sind in tests/test_es.py
R4-validiert (bekannter Effekt, Shuffle, Placebo, Handrechnung).
"""

import numpy as np
import pandas as pd
import pytest

from mie.es import EsError
from mie.es.b1_volatilitaet import (
    EXPERIMENT_ID,
    auswertung,
    data_version_kurz,
    ergebnis_kurz,
    report_text,
)


def kursframe(start: str, perioden: int, seed: int = 1) -> pd.DataFrame:
    tage = pd.bdate_range(start, periods=perioden)
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, size=perioden))
    open_ = np.concatenate([[100.0], close[:-1]])
    return pd.DataFrame(
        {
            "date": tage,
            "open": open_,
            "high": np.maximum(open_, close) * 1.01,
            "low": np.minimum(open_, close) * 0.99,
            "close": close,
            "div_cash": 0.0,
            "split_factor": 1.0,
        }
    )


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
    assert len(r["vergleiche"]) == 24  # 2 Assets × 2 Maße × 2 Statistiken × 3 Gruppen
    assert len(r["placebos"]) == 6  # 2 Assets × 3 Gruppen
    assert sum(1 for v in r["vergleiche"] if v["primaer"]) == 6
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
    assert seeds == list(range(99, 99 + 24))  # vorab fixierte, fortlaufende Seeds
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
    fuer = {(v["gruppe"], v["stat"], v["mass"]): v for v in r["vergleiche"] if v["asset"] == "S1"}
    gepoolt = fuer[("gepoolt", "mittelwert", "abs_tr")]
    getrennt_fomc = fuer[("fomc", "mittelwert", "abs_tr")]
    assert gepoolt["n_ereignis"] == a["n_gepoolt"]
    assert getrennt_fomc["n_ereignis"] == a["n_fomc"]
    # Baseline der getrennten Vergleiche: CPI-Tage ausgeschlossen (Überlappung zählt
    # dort als Ereignis, nicht als Ausschluss).
    assert getrennt_fomc["n_ausgeschlossen"] == a["n_cpi"] - a["n_ueberlappung"]
    assert (
        getrennt_fomc["n_ereignis"]
        + getrennt_fomc["n_baseline"]
        + getrennt_fomc["n_ausgeschlossen"]
        == a["n_handelstage"]
    )


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
        "titel": "Erhoehte Volatilitaet an FOMC/CPI-Tagen (Ederington/Lee 1993)",
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
        r, fake_datenversion(), fake_experiment(), "2026-07-09T12:00:00+00:00", "abc1234"
    )
    for pflicht in [
        "nicht von Hand editieren",
        "Commit:** `abc1234`",
        "sha256 `" + "ab" * 32 + "`",  # eingefrorene Hypothese
        "sha256 `" + "cd" * 32 + "`",  # Datenversion
        "1994-02-04 – 2024-12-31",
        "n Ereignis | n Baseline",  # R3: n je Gruppe
        "95-%-KI",
        "24 Vergleiche",
        "6 Placebo-Tests",
        "## R4-Placebo",
        "volles Raster",
        "keine Anlageempfehlung",
        "Tagesdaten verschmieren",
    ]:
        assert pflicht in text, f"fehlt im Report: {pflicht}"
    # Alle 30 Ergebnisse als Tabellenzeilen (kein Auswahl-Reporting) + 2 Stichprobenzeilen
    assert text.count("| S1 |") + text.count("| S2 |") == 32


def test_registry_felder_appendonly_tauglich_und_ehrlich():
    frames, fomc, cpi, fenster = setup_daten()
    r = auswertung(frames, fomc, cpi, fenster=fenster, n_boot=100, seed_basis=1)
    kurz = ergebnis_kurz(r)
    version = data_version_kurz(fake_datenversion())
    verboten = set(',"\n\r')  # appendonly.FORBIDDEN_CHARS
    assert not verboten & set(kurz)
    assert not verboten & set(version)
    assert "Placebo-KIs ueberdecken 0:" in kurz
    assert "primaere KIs > 0:" in kurz
    assert version == "tiingo_s1=" + "cd" * 6
