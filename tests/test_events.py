"""Parser- und Check-Tests für A3-Terminlisten — kein Netzzugriff.

Die HTML-Fixtures sind echte, unveränderte Ausschnitte der am 08.07.2026
gecachten Quellseiten (Extraktionshinweis im Kommentar am Dateianfang).
Das FRED-Fixture sind 5 echte API-Datensätze, eingefroren am 08.07.2026
via `probe --source fred --freeze-fixture` — verifiziert das reale Response-Format.
"""

from pathlib import Path

import pandas as pd
import pytest

from mie.events import checks, cpi_bls, cpi_fred, et_to_utc, fomc_fed, validate_events_frame

FIXTURES = Path(__file__).parent / "fixtures"


# --- Zeitzonen/Sommerzeit -----------------------------------------------------


def test_et_to_utc_ist_dst_korrekt():
    # Winter (EST, UTC−5): 14:00 ET = 19:00 UTC; Sommer (EDT, UTC−4): 14:00 ET = 18:00 UTC
    winter = et_to_utc(pd.Timestamp("2024-12-18"), "14:00")
    summer = et_to_utc(pd.Timestamp("2024-06-12"), "14:00")
    assert winter.isoformat() == "2024-12-18T19:00:00+00:00"
    assert summer.isoformat() == "2024-06-12T18:00:00+00:00"
    # CPI-Konvention 08:30 ET
    assert et_to_utc(pd.Timestamp("2024-01-11"), "08:30").isoformat() == (
        "2024-01-11T13:30:00+00:00"
    )


# --- FOMC-Parser ---------------------------------------------------------------


def test_fomc_historisch_1994_meeting_und_conference_call():
    html = (FIXTURES / "fed_hist1994_sample.html").read_text()
    df = fomc_fed.parse_historical(html, 1994)
    assert validate_events_frame(df) == []
    feb = df.iloc[0]
    # Zweitägige Sitzung: Ereignisdatum = letzter Sitzungstag
    assert feb["meeting_start"].isoformat() == "1994-02-03T00:00:00"
    assert feb["date"].isoformat() == "1994-02-04T00:00:00"
    assert feb["meeting_type"] == "meeting" and bool(feb["scheduled"])
    # Erstes Fed-Statement überhaupt (04.02.1994), Link-Ära /fomc/…default.htm
    assert feb["statement_date"] == feb["date"]
    call = df.iloc[1]
    assert call["meeting_type"] == "conference_call" and not bool(call["scheduled"])
    assert pd.isna(call["statement_date"])


def test_fomc_historisch_2020_sonderfaelle():
    html = (FIXTURES / "fed_hist2020_sample.html").read_text()
    df = fomc_fed.parse_historical(html, 2020)
    by_date = df.set_index(df["date"].dt.date.astype(str))
    assert by_date.loc["2020-03-15", "meeting_type"] == "unscheduled"
    assert by_date.loc["2020-03-18", "meeting_type"] == "cancelled"
    assert by_date.loc["2020-03-19", "meeting_type"] == "notation_vote"
    assert by_date.loc["2020-01-29", "meeting_type"] == "meeting"
    # Nur reguläre Sitzungen gelten als scheduled
    assert set(df.loc[df["scheduled"], "meeting_type"]) == {"meeting"}
    # Notfallsenkung 15.03.2020: Statement am selben Tag
    assert by_date.loc["2020-03-15", "statement_date"] == pd.Timestamp("2020-03-15")


def test_fomc_historisch_fremdes_jahr_wird_abgelehnt():
    html = (FIXTURES / "fed_hist2020_sample.html").read_text()
    with pytest.raises(ValueError):
        fomc_fed.parse_historical(html, 2019)


def test_fomc_aktuelle_seite_2025():
    html = (FIXTURES / "fed_current_sample.html").read_text()
    df = fomc_fed.parse_current(html)
    assert validate_events_frame(df) == []
    assert len(df) == 9  # 8 reguläre Sitzungen + 1 notation vote
    assert (df["date"].dt.year == 2025).all()
    by_date = df.set_index(df["date"].dt.date.astype(str))
    # Zweitägige Sitzung mit Statement-Link und SEP-Stern
    assert by_date.loc["2025-03-19", "meeting_start"] == pd.Timestamp("2025-03-18")
    assert bool(by_date.loc["2025-03-19", "sep"])
    assert not bool(by_date.loc["2025-01-29", "sep"])
    assert by_date.loc["2025-01-29", "statement_date"] == pd.Timestamp("2025-01-29")
    # Datumszelle „22 (notation vote)"
    nv = by_date.loc["2025-08-22"]
    assert nv["meeting_type"] == "notation_vote" and not bool(nv["scheduled"])


def test_fomc_monatswechsel_sitzungen():
    # Format-authentische Minimalfälle für Sitzungen über den Monatswechsel
    html = "<h5>January 31-February 1 Meeting - 2023</h5>"
    df = fomc_fed.parse_historical(html, 2023)
    assert df.loc[0, "meeting_start"] == pd.Timestamp("2023-01-31")
    assert df.loc[0, "date"] == pd.Timestamp("2023-02-01")
    html = "<h5>April/May 30-1 Meeting - 2019</h5>"
    df = fomc_fed.parse_historical(html, 2019)
    assert df.loc[0, "meeting_start"] == pd.Timestamp("2019-04-30")
    assert df.loc[0, "date"] == pd.Timestamp("2019-05-01")


# --- CPI-Parser ----------------------------------------------------------------


def test_bls_archiv_beide_url_aeren():
    df = cpi_bls.parse_archive((FIXTURES / "bls_archive_sample.html").read_text())
    assert validate_events_frame(df) == []
    assert len(df) == 4
    # 6-stellige Ära (cpi_021794.txt = 17.02.1994, Referenzmonat Januar 1994)
    assert df.loc[0, "date"] == pd.Timestamp("1994-02-17")
    assert df.loc[0, "ref_month"] == "1994-01"
    # 8-stellige Ära
    assert df.loc[3, "date"] == pd.Timestamp("2026-06-10")
    assert df.loc[3, "ref_month"] == "2026-05"
    assert df["scheduled"].all()


def test_bls_terminplan_mit_uhrzeit():
    df = cpi_bls.parse_schedule((FIXTURES / "bls_schedule_sample.html").read_text())
    assert len(df) == 3
    assert df.loc[0, "date"] == pd.Timestamp("2025-12-18")
    assert df.loc[0, "ref_month"] == "2025-11"
    assert (df["time_et"] == "08:30").all()


def test_fred_parser_echtes_response_format():
    # Fixture = 5 echte API-Datensätze (Release-Termine ab 18.01.1990),
    # eingefroren am 08.07.2026 via `probe --source fred --freeze-fixture`.
    df = cpi_fred.parse_bytes((FIXTURES / "fred_release_dates_sample.json").read_bytes())
    assert validate_events_frame(df) == []
    assert len(df) == 5
    assert df.loc[0, "date"] == pd.Timestamp("1990-01-18")
    assert (df["source"] == "fred").all()


# --- Checks (R4: Mini-Datensätze mit bekannter Antwort) -------------------------


def _mini_events(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_type": "cpi",
            "date": pd.to_datetime(dates),
            "scheduled": True,
            "source": "test",
        }
    )


def test_checks_finden_bekannte_probleme():
    today = pd.Timestamp("2026-01-01")
    # Duplikat und Wochenende (10.01.2026 = Samstag)
    df = _mini_events(["2025-06-10", "2025-06-10", "2026-01-10"])
    assert len(checks.check_duplicates(df)) == 2
    assert checks.check_weekend(df)["date"].dt.date.astype(str).tolist() == ["2026-01-10"]
    # Lücke > 45 Tage
    gaps = checks.check_gaps_days(_mini_events(["2025-01-10", "2025-02-10", "2025-05-10"]), 45)
    assert len(gaps) == 1 and gaps.iloc[0]["gap_days"] == 89
    # Feiertags-Check mit injiziertem Kalender (R4): 02.01. fehlt im Kalender
    trading = pd.DatetimeIndex(pd.to_datetime(["2025-06-10", "2025-01-10"]))
    hits = checks.check_non_trading(_mini_events(["2025-06-10", "2025-01-02"]), today, trading)
    assert hits["date"].dt.date.astype(str).tolist() == ["2025-01-02"]


def test_crosscheck_dates_findet_differenzen():
    a = _mini_events(["2025-01-10", "2025-02-10", "2025-03-10"])
    b = _mini_events(["2025-01-10", "2025-03-10", "2025-04-10"])
    r = checks.crosscheck_dates(a, b, "a", "b")
    # Überlappungsfenster 10.01.–10.03.: 10.04. (nur b) liegt außerhalb
    assert r["n_match"] == 2
    assert r["only_a"] == ["2025-02-10"] and r["n_only_b"] == 0


def test_fomc_scheduled_deviations_bekannte_antwort():
    df = pd.DataFrame(
        {
            "event_type": "fomc",
            "date": pd.to_datetime([f"2024-{m:02d}-15" for m in range(1, 9)] + ["2025-06-15"]),
            "scheduled": True,
            "source": "test",
        }
    )
    dev = checks.fomc_scheduled_deviations(df, pd.Timestamp("2026-01-01"))
    assert dev["deviations"] == {2025: 1}  # 2024 hat Soll 8, 2025 weicht ab
