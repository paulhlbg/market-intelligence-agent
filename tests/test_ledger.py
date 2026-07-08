"""Ledger v0: Schema-Check, Append-only-Wächter, Auflösungslogik (alles offline).

Der Append-only-Wächter wird gegen ein temporäres Git-Repo getestet — genau der
Mechanismus, der im echten Repo Änderungen an alten Ledger-Zeilen verweigert.
"""

import subprocess

import pandas as pd
import pytest

from mie import ledger


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _commit(repo):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "test")


@pytest.fixture()
def repo(tmp_path):
    """Temporäres Git-Repo mit leeren (nur Header) Ledger-Dateien, committet."""
    (tmp_path / "ledger").mkdir()
    ledger.prognosen_path(tmp_path).write_text(",".join(ledger.FORECAST_COLUMNS) + "\n")
    ledger.aufloesungen_path(tmp_path).write_text(",".join(ledger.RESOLUTION_COLUMNS) + "\n")
    _git(tmp_path, "init", "-q")
    _commit(tmp_path)
    return tmp_path


def _forecast_row(**over):
    row = {
        "forecast_id": "2024-11-01_spy_w1",
        "created_utc": "2024-11-01T22:00:00+00:00",
        "asset": "SPY",
        "horizon": "w1_5td",
        "target_id": "w1_up_v1",
        "anchor_date": "2024-11-01",
        "anchor_close": "571.04",
        "target_date": "2024-11-08",
        "probability": "0.5600",
        "model_id": "klimatologie_v0",
        "train_n": "8000",
        "train_start": "1993-01-29",
        "train_end": "2024-11-01",
        "data_version": "abc123",
        "code_commit": "deadbee",
        "event_type": "",
        "event_date": "",
    }
    row.update(over)
    return row


def _resolution_row(**over):
    row = {
        "forecast_id": "2024-11-01_spy_w1",
        "resolved_utc": "2024-11-08T22:00:00+00:00",
        "realized_return": "0.012345",
        "outcome": "1",
        "resolution_date": "2024-11-08",
        "data_version": "abc123",
        "code_commit": "deadbee",
    }
    row.update(over)
    return row


def _price_frame(dates, close):
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "close": [float(c) for c in close],
            "div_cash": [0.0] * len(close),
            "split_factor": [1.0] * len(close),
        }
    )


def _empty_resolutions():
    return pd.DataFrame(columns=ledger.RESOLUTION_COLUMNS)


# ---------- Schema ----------


def test_schema_pflichtfelder():
    problems = ledger.validate_forecast_row(_forecast_row(probability=""))
    assert any("probability" in p for p in problems)
    assert ledger.validate_forecast_row(_forecast_row()) == []


def test_schema_wertebereiche():
    assert any(
        "probability" in p for p in ledger.validate_forecast_row(_forecast_row(probability="1.5"))
    )
    assert any(
        "target_date" in p
        for p in ledger.validate_forecast_row(_forecast_row(target_date="2024-10-31"))
    )
    assert any("Zeichen" in p for p in ledger.validate_forecast_row(_forecast_row(asset="SPY,QQQ")))
    # outcome muss zum gespeicherten realized_return passen (Regel: 1 gdw. TR > 0)
    assert any(
        "outcome" in p
        for p in ledger.validate_resolution_row(_resolution_row(realized_return="-0.010000"))
    )
    assert ledger.validate_resolution_row(_resolution_row()) == []


# ---------- Append-only ----------


def test_append_und_laden(repo):
    assert ledger.append_forecasts([_forecast_row()], repo) == 1
    df = ledger.load_forecasts(repo)
    assert len(df) == 1
    assert df.loc[0, "forecast_id"] == "2024-11-01_spy_w1"
    assert df.loc[0, "event_type"] == ""


def test_doppelte_forecast_id_verweigert(repo):
    ledger.append_forecasts([_forecast_row()], repo)
    with pytest.raises(ledger.LedgerError, match="vorhanden oder doppelt"):
        ledger.append_forecasts([_forecast_row()], repo)


def test_append_only_verweigert_geaenderte_zeile(repo):
    """Kernanforderung A4: Das Skript verweigert Änderungen an alten Zeilen."""
    ledger.append_forecasts([_forecast_row()], repo)
    _commit(repo)
    path = ledger.prognosen_path(repo)
    path.write_text(path.read_text().replace("0.5600", "0.9900"))  # alte Zeile manipuliert
    with pytest.raises(ledger.LedgerError, match="Append-only"):
        ledger.append_forecasts(
            [
                _forecast_row(
                    forecast_id="2024-11-08_spy_w1",
                    anchor_date="2024-11-08",
                    target_date="2024-11-15",
                )
            ],
            repo,
        )


def test_append_only_verweigert_geloeschte_zeile(repo):
    ledger.append_forecasts([_forecast_row()], repo)
    _commit(repo)
    path = ledger.prognosen_path(repo)
    path.write_text(",".join(ledger.FORECAST_COLUMNS) + "\n")  # Zeile gelöscht
    with pytest.raises(ledger.LedgerError, match="Append-only"):
        ledger.ensure_append_only(path, repo)


def test_append_only_erlaubt_anhaengen(repo):
    ledger.append_forecasts([_forecast_row()], repo)
    _commit(repo)
    n = ledger.append_forecasts([_forecast_row(forecast_id="2024-11-01_qqq_w1", asset="QQQ")], repo)
    assert n == 1
    assert len(ledger.load_forecasts(repo)) == 2


def test_aufloesung_referenzen(repo):
    ledger.append_forecasts([_forecast_row()], repo)
    with pytest.raises(ledger.LedgerError, match="ohne Prognose"):
        ledger.append_resolutions([_resolution_row(forecast_id="gibt_es_nicht")], repo)
    assert ledger.append_resolutions([_resolution_row()], repo) == 1
    with pytest.raises(ledger.LedgerError, match="bereits aufgelöst"):
        ledger.append_resolutions([_resolution_row()], repo)


# ---------- Auflösungslogik ----------

# Echte NYSE-Handelstage Anfang November 2024; Anker 01.11., 5. Handelstag danach = 08.11.
NOV_DAYS = ["2024-11-01", "2024-11-04", "2024-11-05", "2024-11-06", "2024-11-07", "2024-11-08"]


def _due(forecast, frame):
    return ledger.due_resolutions(
        pd.DataFrame([forecast]),
        _empty_resolutions(),
        {"SPY": frame},
        {"SPY": "sha_test"},
        "deadbee",
        "2024-11-08T22:00:00+00:00",
    )


def test_aufloesung_faellig():
    frame = _price_frame(NOV_DAYS, [100, 101, 102, 103, 104, 110])
    rows = _due(_forecast_row(anchor_close="100.0"), frame)
    assert len(rows) == 1
    assert rows[0]["realized_return"] == "0.100000"
    assert rows[0]["outcome"] == "1"
    assert rows[0]["resolution_date"] == "2024-11-08"


def test_aufloesung_noch_nicht_faellig():
    frame = _price_frame(NOV_DAYS[:5], [100, 101, 102, 103, 104])  # Zieltag noch ohne Kurs
    assert _due(_forecast_row(anchor_close="100.0"), frame) == []


def test_nachtrag_regel_unvorhergesehene_schliessung():
    """Zieltag 28.11.2024 (Thanksgiving, laut Kalender kein Handelstag): nächster
    vorhandener Handelstag gilt (docs/zieldefinitionen.md, Nachtrag-Regel)."""
    days = ["2024-11-21", "2024-11-22", "2024-11-25", "2024-11-26", "2024-11-27", "2024-11-29"]
    frame = _price_frame(days, [100, 101, 102, 103, 104, 95])
    forecast = _forecast_row(
        anchor_date="2024-11-21", anchor_close="100.0", target_date="2024-11-28"
    )
    rows = _due(forecast, frame)
    assert len(rows) == 1
    assert rows[0]["resolution_date"] == "2024-11-29"
    assert rows[0]["outcome"] == "0"  # 95/100 − 1 < 0


def test_datenluecke_bricht_ab():
    # 26.11.2024 ist laut NYSE-Kalender Handelstag, fehlt aber im Frame → kein stilles Ausweichen
    days = ["2024-11-21", "2024-11-22", "2024-11-25", "2024-11-27"]
    frame = _price_frame(days, [100, 101, 102, 103])
    forecast = _forecast_row(
        anchor_date="2024-11-21", anchor_close="100.0", target_date="2024-11-26"
    )
    with pytest.raises(ledger.LedgerError, match="Handelstag"):
        _due(forecast, frame)


def test_anchor_integritaet():
    frame = _price_frame(NOV_DAYS, [100, 101, 102, 103, 104, 110])
    with pytest.raises(ledger.LedgerError, match="anchor_close"):
        _due(_forecast_row(anchor_close="999.0"), frame)


def test_next_trading_days():
    days = ledger.next_trading_days(pd.Timestamp("2024-01-05"), 5)
    assert [d.date().isoformat() for d in days] == [
        "2024-01-08",
        "2024-01-09",
        "2024-01-10",
        "2024-01-11",
        "2024-01-12",
    ]
    # über Weihnachten 2024: 25.12. Feiertag, 24.12. verkürzter, aber regulärer Handelstag
    days = ledger.next_trading_days(pd.Timestamp("2024-12-20"), 5)
    assert [d.date().isoformat() for d in days] == [
        "2024-12-23",
        "2024-12-24",
        "2024-12-26",
        "2024-12-27",
        "2024-12-30",
    ]
