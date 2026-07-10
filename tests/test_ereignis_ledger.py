"""Ereigniszweig des Ledgers (B4): Basisraten, Deadline, Überlappung, Auflösung.

Alles offline auf synthetischen Frames mit echten NYSE-Handelstagen; nur der
XNYS-Kalender (gepinnte Abhängigkeit) wird für Deadline-/Session-Fragen genutzt.
Zieldefinitionen fomc_on_up_v1/cpi_d1_up_v1: docs/zieldefinitionen.md.
"""

import pandas as pd
import pytest

from mie import ledger
from mie.ledger import ereignis

# Echte NYSE-Handelstage Anfang November 2024 (wie tests/test_ledger.py).
NOV_DAYS = ["2024-11-01", "2024-11-04", "2024-11-05", "2024-11-06", "2024-11-07", "2024-11-08"]
OPENS = [99.0, 101.0, 102.0, 102.0, 105.0, 103.0]
CLOSES = [100.0, 102.0, 101.0, 103.0, 104.0, 100.0]
# Overnight-TR ab 04.11.: +0.01, 0.0, +0.009901, +0.019417, −0.009615
# Tages-TR    ab 04.11.: +0.02, −0.009804, +0.019802, +0.009709, −0.038462


def _frame(dates=NOV_DAYS, opens=OPENS, closes=CLOSES):
    n = len(dates)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": [float(x) for x in opens],
            "close": [float(x) for x in closes],
            "div_cash": [0.0] * n,
            "split_factor": [1.0] * n,
        }
    )


def _idx(*dates):
    return pd.DatetimeIndex(pd.to_datetime(list(dates)))


# ---------- Basisraten (Handrechnung) ----------


def test_ereignis_basisrate_handrechnung_mit_ausschluss():
    # Ereignistage 05./07./08.11.; 08.11. als Überlappungstag ausgeschlossen.
    # Overnight-TR am 05.11. = 0.0 (zählt als „nicht gestiegen"), am 07.11. > 0 → 1/2.
    stats = ereignis.ereignis_basisrate(
        _frame(),
        _idx("2024-11-05", "2024-11-07", "2024-11-08"),
        ledger.TARGET_FOMC_ON_UP_V1,
        ausschluss_tage=_idx("2024-11-08"),
    )
    assert stats == {
        "probability": 0.5,
        "train_n": 2,
        "train_start": "2024-11-05",
        "train_end": "2024-11-07",
    }


def test_ereignis_basisrate_fensterstart_und_fremde_tage():
    # fenster_start schneidet den 05.11. weg; Tage außerhalb der Reihe fallen heraus.
    stats = ereignis.ereignis_basisrate(
        _frame(),
        _idx("1998-01-02", "2024-11-05", "2024-11-07", "2030-01-02"),
        ledger.TARGET_FOMC_ON_UP_V1,
        fenster_start=pd.Timestamp("2024-11-06"),
    )
    assert stats["probability"] == 1.0
    assert stats["train_n"] == 1
    assert stats["train_start"] == stats["train_end"] == "2024-11-07"


def test_ereignis_basisrate_ohne_treffer_bricht_ab():
    with pytest.raises(ledger.LedgerError, match="keine historischen Ereignistage"):
        ereignis.ereignis_basisrate(_frame(), _idx("2030-01-02"), ledger.TARGET_CPI_D1_UP_V1)


def test_alltage_basisrate_handrechnung():
    # Tages-TR: 5 Werte ab 04.11., davon 3 positiv → 0.6.
    stats = ereignis.alltage_basisrate(_frame(), ledger.TARGET_CPI_D1_UP_V1)
    assert stats == {
        "probability": 0.6,
        "train_n": 5,
        "train_start": "2024-11-04",
        "train_end": "2024-11-08",
    }


# ---------- Deadline (XNYS-Schlusszeiten: Sommer-/Winterzeit, Early Close) ----------


def test_deadline_sommerzeit():
    # FOMC 29.07.2026 (Mi): Vortages-Session 28.07., Schluss 16:00 EDT = 20:00 UTC.
    assert ereignis.deadline_utc(pd.Timestamp("2026-07-29")) == pd.Timestamp(
        "2026-07-28 20:00:00+00:00"
    )


def test_deadline_winterzeit():
    # FOMC 09.12.2026 (Mi): Vortages-Session 08.12., Schluss 16:00 EST = 21:00 UTC.
    assert ereignis.deadline_utc(pd.Timestamp("2026-12-09")) == pd.Timestamp(
        "2026-12-08 21:00:00+00:00"
    )


def test_deadline_early_close():
    # 02.12.2024 (Mo): Vortages-Session ist der 29.11.2024 (Freitag nach
    # Thanksgiving, verkürzter Handel bis 13:00 EST = 18:00 UTC).
    assert ereignis.deadline_utc(pd.Timestamp("2024-12-02")) == pd.Timestamp(
        "2024-11-29 18:00:00+00:00"
    )


def test_deadline_ereignistag_kein_handelstag_bricht_ab():
    with pytest.raises(ledger.LedgerError, match="kein Handelstag"):
        ereignis.deadline_utc(pd.Timestamp("2026-11-26"))  # Thanksgiving


# ---------- Kommende Ereignisse und Überlappung ----------


def test_kommende_ereignisse_fenster_und_ueberlappung():
    fomc = _idx("2026-07-29", "2026-09-16")
    cpi = _idx("2026-07-14", "2026-07-29")
    faellig = ereignis.kommende_ereignisse(pd.Timestamp("2026-07-27"), fomc, cpi)
    assert [(e["event_type"], e["event_date"].date().isoformat()) for e in faellig] == [
        ("cpi", "2026-07-29"),
        ("fomc", "2026-07-29"),
    ]
    assert all(e["ueberlappung"] for e in faellig)

    faellig = ereignis.kommende_ereignisse(pd.Timestamp("2026-07-10"), fomc, cpi)
    assert [(e["event_type"], e["event_date"].date().isoformat()) for e in faellig] == [
        ("cpi", "2026-07-14")
    ]
    assert not faellig[0]["ueberlappung"]


# ---------- Registrierung (neue_ereignis_zeilen) ----------

FOMC_TAGE = _idx("2024-11-05", "2024-11-07", "2026-07-29")
CPI_TAGE = _idx("2024-11-07")  # 07.11. ist damit historischer Überlappungstag


def _zeilen(now_utc, existing_ids=frozenset(), fomc=FOMC_TAGE, cpi=CPI_TAGE):
    return ereignis.neue_ereignis_zeilen(
        {"SPY": _frame()},
        {"SPY": "sha_test"},
        set(existing_ids),
        "deadbee",
        now_utc,
        fomc_tage=fomc,
        cpi_tage=cpi,
        assets=("SPY",),
    )


def test_registrierung_vor_deadline():
    zeilen, meldungen = _zeilen("2026-07-27T12:00:00+00:00")
    assert [z["forecast_id"] for z in zeilen] == [
        "2026-07-29_spy_fomc_on",
        "2026-07-29_spy_fomc_on_ref",
    ]
    kond, ref = zeilen
    # Basisrate: Überlappungstag 07.11. ausgeschlossen → nur 05.11. (Overnight 0.0) → 0.0
    assert kond["model_id"] == "klimatologie_ev_v0"
    assert kond["probability"] == "0.0000"
    assert kond["train_n"] == "1"
    assert (kond["train_start"], kond["train_end"]) == ("2024-11-05", "2024-11-05")
    # Referenz: Overnight-TR aller Tage, 3 von 5 positiv → 0.6
    assert ref["model_id"] == "klimatologie_alltage_v0"
    assert ref["probability"] == "0.6000"
    assert ref["train_n"] == "5"
    for z in zeilen:
        assert (z["event_type"], z["event_date"]) == ("fomc", "2026-07-29")
        assert z["target_date"] == "2026-07-29"
        assert (z["anchor_date"], z["anchor_close"]) == ("2024-11-08", "100.0")
        assert ledger.validate_forecast_row(z) == []
    assert any("Registrierung vor Deadline 2026-07-28T20:00:00+00:00" in m for m in meldungen)


def test_registrierung_nach_deadline_verweigert():
    # 28.07. 21:00 UTC liegt NACH dem Vortages-Schluss 20:00 UTC → auslassen.
    zeilen, meldungen = _zeilen("2026-07-28T21:00:00+00:00")
    assert zeilen == []
    assert any("verpasst" in m and "kein Nachtragen" in m for m in meldungen)


def test_registrierung_ueberlappungstag_ausgesetzt():
    cpi = _idx("2024-11-07", "2026-07-29")  # kommender Termin nun FOMC=CPI
    zeilen, meldungen = _zeilen("2026-07-27T12:00:00+00:00", cpi=cpi)
    assert zeilen == []
    assert sum("Überlappungstag — ausgesetzt" in m for m in meldungen) == 2  # cpi + fomc


def test_registrierung_idempotent():
    zeilen, meldungen = _zeilen(
        "2026-07-27T12:00:00+00:00", existing_ids={"2026-07-29_spy_fomc_on"}
    )
    assert [z["forecast_id"] for z in zeilen] == ["2026-07-29_spy_fomc_on_ref"]
    assert any("bereits registriert" in m for m in meldungen)


# ---------- Schema (Ereignisfelder) ----------


def _ev_forecast_row(**over):
    row = {
        "forecast_id": "2024-11-06_spy_fomc_on",
        "created_utc": "2024-11-04T12:00:00+00:00",
        "asset": "SPY",
        "horizon": "ev_on",
        "target_id": ledger.TARGET_FOMC_ON_UP_V1,
        "anchor_date": "2024-11-01",
        "anchor_close": "100.0",
        "target_date": "2024-11-06",
        "probability": "0.5000",
        "model_id": "klimatologie_ev_v0",
        "train_n": "1",
        "train_start": "2024-11-05",
        "train_end": "2024-11-05",
        "data_version": "sha_test",
        "code_commit": "deadbee",
        "event_type": "fomc",
        "event_date": "2024-11-06",
    }
    row.update(over)
    return row


def test_schema_ereignisfelder():
    assert ledger.validate_forecast_row(_ev_forecast_row()) == []
    assert any(
        "event_type" in p for p in ledger.validate_forecast_row(_ev_forecast_row(event_type=""))
    )
    assert any(
        "event_type" in p
        for p in ledger.validate_forecast_row(_ev_forecast_row(event_type="earnings"))
    )
    assert any(
        "event_date" in p
        for p in ledger.validate_forecast_row(_ev_forecast_row(event_date="2024-11-07"))
    )


# ---------- Auflösung (due_resolutions mit Ereignis-Zielen) ----------


def _due(forecast, frame):
    return ledger.due_resolutions(
        pd.DataFrame([forecast]),
        pd.DataFrame(columns=ledger.RESOLUTION_COLUMNS),
        {"SPY": frame},
        {"SPY": "sha_test"},
        "deadbee",
        "2024-11-10T12:00:00+00:00",
    )


def test_aufloesung_overnight_handrechnung():
    rows = _due(_ev_forecast_row(), _frame())
    assert len(rows) == 1
    # Overnight 06.11.: open 102 / close(05.11.) 101 − 1 = +0.009901
    assert rows[0]["realized_return"] == "0.009901"
    assert rows[0]["outcome"] == "1"
    assert rows[0]["resolution_date"] == "2024-11-06"


def test_aufloesung_tages_handrechnung():
    forecast = _ev_forecast_row(
        forecast_id="2024-11-08_spy_cpi_d1",
        horizon="ev_d1",
        target_id=ledger.TARGET_CPI_D1_UP_V1,
        target_date="2024-11-08",
        event_type="cpi",
        event_date="2024-11-08",
    )
    rows = _due(forecast, _frame())
    assert len(rows) == 1
    # Tages-TR 08.11.: close 100 / close(07.11.) 104 − 1 = −0.038462
    assert rows[0]["realized_return"] == "-0.038462"
    assert rows[0]["outcome"] == "0"


def test_aufloesung_noch_nicht_faellig():
    frame = _frame(NOV_DAYS[:3], OPENS[:3], CLOSES[:3])  # endet 05.11., Ziel 06.11.
    assert _due(_ev_forecast_row(), frame) == []


def test_aufloesung_fehlender_ereignistag_bricht_ab():
    # 06.11. fehlt, spätere Tage vorhanden → kein Ausweichtag für Ereignis-Ziele.
    keep = [0, 1, 2, 4, 5]
    frame = _frame([NOV_DAYS[i] for i in keep], [OPENS[i] for i in keep], [CLOSES[i] for i in keep])
    with pytest.raises(ledger.LedgerError, match="Ausweichtag"):
        _due(_ev_forecast_row(), frame)


def test_aufloesung_luecke_vor_ereignistag_bricht_ab():
    # 05.11. (Vortages-Session, Fensterbeginn) fehlt im Frame → Abbruch.
    keep = [0, 1, 3, 4, 5]
    frame = _frame([NOV_DAYS[i] for i in keep], [OPENS[i] for i in keep], [CLOSES[i] for i in keep])
    with pytest.raises(ledger.LedgerError, match="Vortages-Session"):
        _due(_ev_forecast_row(), frame)
