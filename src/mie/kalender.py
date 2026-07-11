"""Kalender-Erinnerungen (K1): erzeugt eine .ics-Datei für die Betriebsroutinen.

Einträge: Wochenlauf-Serie (samstags 10:00 Europe/Berlin), je kommendem
FOMC/CPI-Termin die Registrierungs-Deadline (mie.ledger.ereignis.deadline_utc —
XNYS-Schluss der Vortages-Session inkl. Early Close), FOMC=CPI-Überlappungstage
als Hinweis „ausgesetzt", eine vierteljährliche Terminabgleich-Serie (Fed/BLS)
und Einmal-Merkposten für den Terminlisten-Refresh (CPI-Liste endet Dez. 2026,
FOMC-Liste Dez. 2027).

Aufruf (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.kalender [--out PFAD]

Kein Netzzugriff: die Termine kommen aus den versionierten Terminlisten
(data/processed/*.csv). Die erzeugte Datei ist ein lokales Artefakt (bewusst
unversioniert, .gitignore) — Import in einen eigenen Kalender „MIE";
Aktualisierung durch Löschen + Neuimport (docs/routinen.md). Reine
Betriebshilfe: keine Auswertung, keine Wahrscheinlichkeiten.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from mie.es import ereignistage
from mie.ledger import ereignis
from mie.sources import REPO_ROOT

OUT_DEFAULT = REPO_ROOT / "data" / "processed" / "mie_erinnerungen.ics"
UID_DOMAIN = "mie.local"
TZID = "Europe/Berlin"
LOOKAHEAD_ALLE = 3660  # Kalendertage: deckt die volle Reichweite beider Terminlisten ab

# Jährlicher R2-Merkposten (docs/routinen.md): Listen rechtzeitig auffrischen.
REFRESH_MERKPOSTEN = (
    ("cpi", pd.Timestamp("2026-12-01"), "CPI", "Dez. 2026"),
    ("fomc", pd.Timestamp("2027-12-01"), "FOMC", "Dez. 2027"),
)

KOPF = (
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Market Intelligence Engine//mie.kalender//DE",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:MIE",
)

# Statische Europe/Berlin-Definition (RFC 5545): letzte März-/Oktober-Sonntage.
VTIMEZONE = (
    "BEGIN:VTIMEZONE",
    f"TZID:{TZID}",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0200",
    "TZNAME:CEST",
    "DTSTART:19700329T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0100",
    "TZNAME:CET",
    "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
)

BESCHREIBUNG_WOCHENLAUF = (
    "Wochenroutine (Ziel ≤ 15 Min): 1) uv run python -m mie.a4_ledger weekly "
    "2) Ausgabe gegenlesen 3) make check 4) committen + pushen. "
    "Ein verschobener Lauf verfälscht nichts (der Anker verschiebt sich nur); "
    "ein Doppellauf am selben Tag ist unschädlich. Anleitung: docs/routinen.md."
)

BESCHREIBUNG_ABGLEICH = (
    "Vierteljährlich prüfen, ob Fed/BLS Termine geändert haben: "
    "1) uv run python -m mie.a3_termine all 2) git diff data/processed/fomc_termine.csv "
    "data/processed/cpi_termine.csv. Kein Diff: fertig, Abgleich committen. "
    "Diff: nichts still übernehmen — betrifft er registrierte Prognosen, Umgang "
    "entscheiden und dokumentieren; danach uv run python -m mie.kalender und den "
    "Kalender MIE ersetzen. Anleitung: docs/routinen.md (Terminabgleich)."
)

BESCHREIBUNG_UEBERLAPPUNG = (
    "FOMC- und CPI-Termin fallen auf denselben Tag — laut Zieldefinition wird der "
    "Termin ausgesetzt und nur ausgewiesen (docs/zieldefinitionen.md). Nichts zu tun."
)


def _deadline_beschreibung(label: str) -> str:
    return (
        f"Registrierungs-Deadline {label} (Börsenschluss der Vortages-Session). "
        "Nur handeln, falls der Wochenlauf diese Woche noch nicht lief — sonst ist der "
        "Termin bereits registriert (Doppellauf unschädlich). Zwischenlauf: "
        "1) uv run python -m mie.a4_ledger events 2) Ausgabe gegenlesen 3) make check "
        "4) committen. Nach Ablauf der Deadline wird der Termin ehrlich ausgelassen "
        "(kein Nachtragen). Anleitung: docs/routinen.md."
    )


def _refresh_beschreibung(name: str, ende: str) -> str:
    return (
        f"Die {name}-Terminliste endet {ende} — ohne Refresh können danach keine "
        f"{name}-Termine mehr registriert werden. Ablauf: uv run python -m mie.a3_termine "
        "all, Diff gegenlesen, committen; danach uv run python -m mie.kalender und die "
        "neue .ics importieren (Kalender MIE ersetzen). Anleitung: docs/routinen.md."
    )


def _escape(text: str) -> str:
    """RFC-5545-Escaping für Textwerte (Backslash, Semikolon, Komma, Zeilenumbruch)."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _falte(zeile: str) -> list[str]:
    """RFC-5545-Zeilenfaltung: max. 75 Oktette je Zeile, Folgezeilen mit Leerzeichen."""
    raw = zeile.encode("utf-8")
    out: list[str] = []
    prefix = b""
    while len(prefix) + len(raw) > 75:
        cut = 75 - len(prefix)
        while (raw[cut] & 0xC0) == 0x80:  # nicht mitten in einem UTF-8-Zeichen schneiden
            cut -= 1
        out.append((prefix + raw[:cut]).decode("utf-8"))
        raw = raw[cut:]
        prefix = b" "
    out.append((prefix + raw).decode("utf-8"))
    return out


def _naechster_samstag(tag: pd.Timestamp) -> pd.Timestamp:
    return tag + pd.Timedelta(days=(5 - tag.weekday()) % 7)


def _erster_monatssamstag_ab(stand: pd.Timestamp) -> pd.Timestamp:
    """Erster „1. Samstag im Monat" am oder nach stand (Anker der Quartalsserie)."""
    kandidat = _naechster_samstag(stand.replace(day=1))
    if kandidat >= stand:
        return kandidat
    return _naechster_samstag(stand.replace(day=1) + pd.offsets.MonthBegin(1))


def _utc_stempel(ts: pd.Timestamp) -> str:
    return ts.tz_convert("UTC").strftime("%Y%m%dT%H%M%SZ")


def _berlin_label(ts: pd.Timestamp) -> str:
    """Uhrzeit in deutscher Lokalzeit, z. B. „22:00 MESZ" (Sommer) / „22:00 MEZ" (Winter)."""
    lokal = ts.tz_convert(TZID)
    name = {"CEST": "MESZ", "CET": "MEZ"}.get(lokal.tzname(), lokal.tzname())
    return f"{lokal.strftime('%H:%M')} {name}"


def _vevent(
    uid_kern: str,
    dtstamp: str,
    zeit_zeilen: list[str],
    summary: str,
    beschreibung: str,
    alarme: tuple[str, ...] = (),
) -> list[str]:
    zeilen = [
        "BEGIN:VEVENT",
        f"UID:{uid_kern}@{UID_DOMAIN}",
        f"DTSTAMP:{dtstamp}",
        *zeit_zeilen,
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(beschreibung)}",
    ]
    for trigger in alarme:
        zeilen += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape(summary)}",
            f"TRIGGER:{trigger}",
            "END:VALARM",
        ]
    zeilen.append("END:VEVENT")
    return zeilen


def _serie(
    uid_kern: str, dtstamp: str, start: pd.Timestamp, uhr: str, rrule: str, summary: str, text: str
) -> list[str]:
    """Wiederkehrender 30-Minuten-Eintrag in lokaler Zeit (Alarm zum Beginn)."""
    tag = start.strftime("%Y%m%d")
    ende = f"{int(uhr[:2]):02d}{int(uhr[2:4]) + 30:02d}00"
    zeit = [
        f"DTSTART;TZID={TZID}:{tag}T{uhr}00",
        f"DTEND;TZID={TZID}:{tag}T{ende}",
        f"RRULE:{rrule}",
    ]
    return _vevent(uid_kern, dtstamp, zeit, summary, text, ("PT0S",))


def kalender_zeilen(
    stand: pd.Timestamp,
    fomc_tage: pd.DatetimeIndex | None = None,
    cpi_tage: pd.DatetimeIndex | None = None,
) -> tuple[str, list[str]]:
    """Vollständiger .ics-Text plus eine Meldung je Eintrag (für die CLI-Ausgabe).

    stand = Erzeugungstag (naiv, Datum); nur Termine NACH stand bekommen einen
    Eintrag. Terminlisten sind injizierbar (Tests); Default sind die Loader der
    Ereignisstudie. Deterministisch: gleiche Eingaben ergeben denselben Text.
    """
    fomc_tage = ereignistage.load_fomc_days() if fomc_tage is None else fomc_tage
    cpi_tage = ereignistage.load_cpi_days() if cpi_tage is None else cpi_tage
    dtstamp = f"{stand.strftime('%Y%m%d')}T000000Z"
    zeilen: list[str] = [*KOPF, *VTIMEZONE]
    meldungen: list[str] = []

    sa = _naechster_samstag(stand)
    zeilen += _serie(
        "mie-wochenlauf",
        dtstamp,
        sa,
        "1000",
        "FREQ=WEEKLY;BYDAY=SA",
        "MIE: Wochenlauf Prognose-Ledger",
        BESCHREIBUNG_WOCHENLAUF,
    )
    meldungen.append(f"Wochenlauf-Serie: samstags 10:00 ({TZID}), erster Eintrag {sa.date()}")

    qa = _erster_monatssamstag_ab(stand)
    zeilen += _serie(
        "mie-terminabgleich",
        dtstamp,
        qa,
        "1100",
        "FREQ=MONTHLY;INTERVAL=3;BYDAY=1SA",
        "MIE: Terminabgleich Fed/BLS",
        BESCHREIBUNG_ABGLEICH,
    )
    meldungen.append(
        f"Terminabgleich-Serie: 1. Samstag alle 3 Monate 11:00, erster Eintrag {qa.date()}"
    )

    termine = ereignis.kommende_ereignisse(stand, fomc_tage, cpi_tage, LOOKAHEAD_ALLE)
    if not termine:
        meldungen.append(
            "keine kommenden FOMC/CPI-Termine in den Terminlisten — "
            "Refresh fällig? (docs/routinen.md)"
        )
    ueberlappt_gesehen: set[pd.Timestamp] = set()
    for ev in termine:
        tag, typ = ev["event_date"], ev["event_type"]
        if ev["ueberlappung"]:
            if tag in ueberlappt_gesehen:  # Tag erscheint als FOMC- UND CPI-Termin
                continue
            ueberlappt_gesehen.add(tag)
            zeilen += _vevent(
                f"mie-ueberlappung-{tag.date()}",
                dtstamp,
                [f"DTSTART;VALUE=DATE:{tag.strftime('%Y%m%d')}"],
                f"MIE: FOMC=CPI {tag.strftime('%d.%m.%Y')} — ausgesetzt (Überlappungstag)",
                BESCHREIBUNG_UEBERLAPPUNG,
            )
            meldungen.append(f"FOMC=CPI {tag.date()}: Überlappungstag — ausgesetzt, nur Hinweis")
            continue
        deadline = ereignis.deadline_utc(tag)
        label = _berlin_label(deadline)
        zeilen += _vevent(
            f"mie-deadline-{typ}-{tag.date()}",
            dtstamp,
            [
                f"DTSTART:{_utc_stempel(deadline - pd.Timedelta(minutes=30))}",
                f"DTEND:{_utc_stempel(deadline)}",
            ],
            f"MIE: {typ.upper()} {tag.strftime('%d.%m.%Y')} — Registrierungs-Deadline {label}",
            _deadline_beschreibung(label),
            ("-PT12H", "-PT2H"),
        )
        meldungen.append(f"{typ.upper()} {tag.date()}: Deadline {deadline.isoformat()} ({label})")

    for schluessel, datum, name, ende in REFRESH_MERKPOSTEN:
        if datum <= stand:
            continue
        zeit = [
            f"DTSTART;TZID={TZID}:{datum.strftime('%Y%m%d')}T100000",
            f"DTEND;TZID={TZID}:{datum.strftime('%Y%m%d')}T103000",
        ]
        zeilen += _vevent(
            f"mie-refresh-{schluessel}",
            dtstamp,
            zeit,
            f"MIE: Terminlisten-Refresh {name} (Liste endet {ende})",
            _refresh_beschreibung(name, ende),
            ("PT0S",),
        )
        meldungen.append(f"Merkposten: {name}-Terminlisten-Refresh am {datum.date()}")

    zeilen.append("END:VCALENDAR")
    text = "\r\n".join(gefaltet for zeile in zeilen for gefaltet in _falte(zeile)) + "\r\n"
    return text, meldungen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.kalender", description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help="Zielpfad der .ics-Datei (Default: data/processed/mie_erinnerungen.ics)",
    )
    args = parser.parse_args(argv)
    stand = pd.Timestamp(datetime.now(UTC).date())
    text, meldungen = kalender_zeilen(stand)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="")
    print("Kalender-Einträge:")
    for m in meldungen:
        print(f"  {m}")
    try:
        ziel = args.out.relative_to(REPO_ROOT)
    except ValueError:
        ziel = args.out
    print(f"\nGeschrieben: {ziel} ({text.count('BEGIN:VEVENT')} Einträge).")
    print(
        'Import: Apple Kalender, eigener Kalender „MIE" — '
        "docs/routinen.md, Abschnitt Kalender-Erinnerungen."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
