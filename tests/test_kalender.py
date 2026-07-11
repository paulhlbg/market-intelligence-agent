"""Kalender-Erinnerungen (K1): .ics-Erzeugung offline auf injizierten Terminlisten.

Deadline-Zeiten laufen über mie.ledger.ereignis.deadline_utc (XNYS, gepinnte
Abhängigkeit); die erwarteten Werte sind Handrechnungen gegen den echten
Kalender: Sommerzeit 16:00 EDT = 20:00 UTC = 22:00 MESZ, Winterzeit 16:00 EST =
21:00 UTC = 22:00 MEZ, Early Close (Freitag nach Thanksgiving) 13:00 EST =
18:00 UTC = 19:00 MEZ.
"""

import pandas as pd

from mie import kalender

STAND = pd.Timestamp("2026-07-10")  # Freitag


def _idx(*dates):
    return pd.DatetimeIndex(pd.to_datetime(list(dates)))


def _text(stand=STAND, fomc=(), cpi=()):
    text, meldungen = kalender.kalender_zeilen(stand, _idx(*fomc), _idx(*cpi))
    return text, meldungen


def _entfaltet(text):
    """RFC-5545-Faltung rückgängig machen (Folgezeilen beginnen mit Leerzeichen)."""
    return text.replace("\r\n ", "")


def _block(text, uid_kern):
    """Zeilen eines VEVENT (BEGIN bis END), identifiziert über den UID-Kern."""
    zeilen = _entfaltet(text).split("\r\n")
    start = zeilen.index(f"UID:{uid_kern}@mie.local") - 1
    assert zeilen[start] == "BEGIN:VEVENT"
    ende = zeilen.index("END:VEVENT", start)
    return zeilen[start : ende + 1]


# ---------- Serien (Wochenlauf, Terminabgleich) ----------


def test_wochenserie_beginnt_am_naechsten_samstag():
    text, meldungen = _text()
    block = _block(text, "mie-wochenlauf")
    assert "DTSTART;TZID=Europe/Berlin:20260711T100000" in block
    assert "DTEND;TZID=Europe/Berlin:20260711T103000" in block
    assert "RRULE:FREQ=WEEKLY;BYDAY=SA" in block
    assert any("erster Eintrag 2026-07-11" in m for m in meldungen)


def test_wochenserie_samstag_selbst_zaehlt():
    text, _ = _text(stand=pd.Timestamp("2026-07-11"))  # Samstag
    assert "DTSTART;TZID=Europe/Berlin:20260711T100000" in _block(text, "mie-wochenlauf")


def test_terminabgleich_quartalsserie_am_ersten_monatssamstag():
    # 1. Samstag im Juli (04.07.) liegt vor dem Stand 10.07. → Anker 01.08.2026.
    text, _ = _text()
    block = _block(text, "mie-terminabgleich")
    assert "DTSTART;TZID=Europe/Berlin:20260801T110000" in block
    assert "RRULE:FREQ=MONTHLY;INTERVAL=3;BYDAY=1SA" in block

    text2, _ = _text(stand=pd.Timestamp("2026-08-01"))  # selbst 1. Monatssamstag
    assert "DTSTART;TZID=Europe/Berlin:20260801T110000" in _block(text2, "mie-terminabgleich")


# ---------- Ereignis-Deadlines (Handrechnung gegen XNYS) ----------


def test_deadline_sommerzeit():
    # CPI Di 14.07.2026 → Deadline Mo 13.07. 16:00 EDT = 20:00 UTC = 22:00 MESZ.
    text, meldungen = _text(cpi=("2026-07-14",))
    block = _block(text, "mie-deadline-cpi-2026-07-14")
    assert "DTSTART:20260713T193000Z" in block  # Eintrag beginnt 30 Min vor der Deadline
    assert "DTEND:20260713T200000Z" in block
    assert any("22:00 MESZ" in z for z in block if z.startswith("SUMMARY:"))
    assert block.count("BEGIN:VALARM") == 2
    assert any("CPI 2026-07-14: Deadline 2026-07-13T20:00:00+00:00" in m for m in meldungen)


def test_deadline_winterzeit():
    # CPI Di 15.12.2026 → Deadline Mo 14.12. 16:00 EST = 21:00 UTC = 22:00 MEZ.
    text, _ = _text(cpi=("2026-12-15",))
    block = _block(text, "mie-deadline-cpi-2026-12-15")
    assert "DTEND:20261214T210000Z" in block
    assert any("22:00 MEZ" in z for z in block if z.startswith("SUMMARY:"))


def test_deadline_early_close():
    # Pseudo-Termin Mo 30.11.2026 → Vortages-Session Fr 27.11. (nach Thanksgiving)
    # mit Early Close 13:00 EST = 18:00 UTC = 19:00 MEZ.
    text, _ = _text(fomc=("2026-11-30",))
    block = _block(text, "mie-deadline-fomc-2026-11-30")
    assert "DTEND:20261127T180000Z" in block
    assert any("19:00 MEZ" in z for z in block if z.startswith("SUMMARY:"))


def test_ueberlappungstag_nur_hinweis_ohne_alarm_und_ohne_deadline():
    text, meldungen = _text(fomc=("2026-09-16",), cpi=("2026-09-16",))
    block = _block(text, "mie-ueberlappung-2026-09-16")
    assert "DTSTART;VALUE=DATE:20260916" in block
    assert block.count("BEGIN:VALARM") == 0
    assert "mie-deadline-fomc-2026-09-16" not in text
    assert "mie-deadline-cpi-2026-09-16" not in text
    # Der Tag erscheint in beiden Listen, aber nur als EIN Eintrag/eine Meldung.
    assert _entfaltet(text).count("mie-ueberlappung-2026-09-16") == 1
    assert sum("Überlappungstag" in m for m in meldungen) == 1


def test_vergangene_und_heutige_termine_fehlen():
    text, _ = _text(cpi=("2026-07-01", "2026-07-10"))  # vor bzw. am Stand
    assert "mie-deadline-cpi-2026-07-01" not in text
    assert "mie-deadline-cpi-2026-07-10" not in text


def test_leere_terminlisten_geben_refresh_hinweis():
    _, meldungen = _text()
    assert any("Refresh fällig?" in m for m in meldungen)


# ---------- Merkposten ----------


def test_refresh_merkposten_und_filter():
    text, _ = _text()
    assert "UID:mie-refresh-cpi@mie.local" in _entfaltet(text)
    assert "UID:mie-refresh-fomc@mie.local" in _entfaltet(text)

    text2, _ = _text(stand=pd.Timestamp("2027-01-15"))  # CPI-Merkposten liegt in der Vergangenheit
    assert "UID:mie-refresh-cpi@mie.local" not in _entfaltet(text2)
    assert "UID:mie-refresh-fomc@mie.local" in _entfaltet(text2)


# ---------- Formatregeln (RFC 5545) ----------


def test_zeilen_max_75_oktette_und_crlf():
    text, _ = _text(fomc=("2026-09-16", "2026-11-30"), cpi=("2026-07-14", "2026-09-16"))
    assert text.endswith("END:VCALENDAR\r\n")
    assert "\n" not in text.replace("\r\n", "")  # nur CRLF-Zeilenenden
    for zeile in text.split("\r\n"):
        assert len(zeile.encode("utf-8")) <= 75


def test_escape_sonderzeichen():
    assert kalender._escape("a,b;c\nd\\e") == "a\\,b\\;c\\nd\\\\e"


def test_faltung_erhaelt_inhalt_und_utf8():
    zeile = "DESCRIPTION:" + "Prüfung ätzender Längen — " * 10
    teile = kalender._falte(zeile)
    assert all(len(t.encode("utf-8")) <= 75 for t in teile)
    assert teile[0] + "".join(t[1:] for t in teile[1:]) == zeile


def test_deterministisch_bei_gleichen_eingaben():
    a, _ = _text(fomc=("2026-11-30",), cpi=("2026-07-14",))
    b, _ = _text(fomc=("2026-11-30",), cpi=("2026-07-14",))
    assert a == b
