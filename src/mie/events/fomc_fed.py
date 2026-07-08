"""Quelle „fed": FOMC-Termine von federalreserve.gov (gemeinfreie US-Regierungsseite).

Zwei Seitentypen (R2-verifiziert am 08.07.2026):
- historische Jahresseiten /monetarypolicy/fomchistorical<JAHR>.htm (1994–2020),
  Termine als <h5>-Überschriften wie „January 28-29 Meeting - 2020",
  „March 15 (unscheduled) Meeting - 2020", „February 28 Conference Call - 1994";
- aktuelle Kalenderseite /monetarypolicy/fomccalendars.htm (ab 2021, inkl.
  zukünftiger Sitzungen), Termine als fomc-meeting-Blöcke unter Jahres-Panels,
  Datumszelle z. B. „27-28", „17-18*" (* = Sitzung mit Summary of Economic
  Projections), „22 (notation vote)".

Ereignisdatum = letzter Sitzungstag (dort wird die Entscheidung bekanntgegeben).
Zum Kreuzabgleich wird je Termin das Datum aus den verlinkten Presse-
mitteilungen (…monetary<YYYYMMDD>…) extrahiert: statement_date.
Zeitraum ab 1994: erst seit Februar 1994 gibt die Fed Entscheidungen zeitnah
per Statement bekannt; davor existiert kein definierter Ereigniszeitpunkt.
"""

import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

from mie.sources import cache_paths, write_cache

SOURCE = "fed"
EXT = "html"
BASE_URL = "https://www.federalreserve.gov/monetarypolicy"
FIRST_YEAR = 1994  # erstes FOMC-Statement: 04.02.1994
LAST_HIST_YEAR = 2020  # ab 2021 deckt die aktuelle Kalenderseite ab (R2-verifiziert)
USER_AGENT = "mie-a3 (privates Forschungsprojekt)"

_MONTHS = {
    name: i
    for i, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}
_MONTHS.update({name[:3]: i for name, i in list(_MONTHS.items())})

# Terminarten laut Seitentext; nur reguläre Sitzungen gelten als scheduled.
_TYPE_PATTERNS = [
    ("cancelled", "cancelled"),
    ("notation vote", "notation_vote"),
    ("unscheduled", "unscheduled"),
    ("conference call", "conference_call"),
    ("meeting", "meeting"),
]

_H5 = re.compile(r"<h5[^>]*>\s*(?P<text>[^<]+?)\s*-\s*(?P<year>\d{4})\s*</h5>")
_DESCRIPTOR = re.compile(
    r"^(?P<months>[A-Za-z]+(?:/[A-Za-z]+)?)\s+(?P<d1>\d{1,2})"
    r"(?:\s*-\s*(?:(?P<m2>[A-Za-z]+)\s+)?(?P<d2>\d{1,2}))?\s*(?P<rest>.*)$"
)
# Statement-Links, je nach Ära: /newsevents/pressreleases/monetary20190130a.htm,
# /boarddocs/press/monetary/2002/20020806/…, press/monetary/20080122,
# /boarddocs/press/general/1999/19990518/ (1999–2002 unter „general" einsortiert)
# oder /fomc/19940204default.htm (früheste Ära; Link existiert nur bei
# Zinsaktion — R2-verifiziert an 1994: genau die 6 Aktionstermine haben ihn)
_STATEMENT_LINK = re.compile(r"(?:(?:monetary|press/general)/?(?:\d{4}/)?|/fomc/)(\d{8})")
_YEAR_PANEL = re.compile(r"(\d{4}) FOMC Meetings")
# Achtung, echtes Markup ist fehlerhaft (『<div class="row fomc-meeting" ">』, überzähliges
# Anführungszeichen) — daher kein schließendes > im Muster verlangen.
_MEETING_BLOCK = re.compile(r'<div class="[^"]*\brow fomc-meeting\b[^"]*"')
_MONTH_CELL = re.compile(r"fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>")
_DATE_CELL = re.compile(r"fomc-meeting__date[^>]*>([^<]*)<")


def fetch_page(path: str) -> bytes:
    """Eine Seite von federalreserve.gov holen (ohne zu cachen)."""
    req = urllib.request.Request(
        f"{BASE_URL}/{path}", headers={"User-Agent": USER_AGENT, "Accept": "text/html"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _classify(text: str) -> str:
    lowered = text.lower()
    for needle, name in _TYPE_PATTERNS:
        if needle in lowered:
            return name
    return f"unbekannt:{text.strip()}" if text.strip() else "meeting"


def _span(months: str, m2: str | None, d1: int, d2: int | None, year: int) -> tuple:
    """(Beginn, Ende) einer Sitzung aus Monats-/Tagesangaben („April/May 30-1" u. ä.)."""
    if "/" in months:
        first, second = (m.strip() for m in months.split("/"))
    else:
        first, second = months.strip(), (m2.strip() if m2 else months.strip())
    start = pd.Timestamp(year=year, month=_MONTHS[first], day=d1)
    end = start if d2 is None else pd.Timestamp(year=year, month=_MONTHS[second], day=d2)
    return start, end


def _statement_date(section: str, end: pd.Timestamp) -> pd.Timestamp:
    """Datum der verlinkten Pressemitteilung; bevorzugt exakt der letzte Sitzungstag."""
    found = sorted({pd.Timestamp(d) for d in _STATEMENT_LINK.findall(section)})
    if end in found:
        return end
    return found[0] if found else pd.NaT


def parse_historical(html: str, year: int) -> pd.DataFrame:
    """Historische Jahresseite (<h5>-Überschriften) in das Einheitsschema überführen."""
    rows = []
    matches = list(_H5.finditer(html))
    for i, m in enumerate(matches):
        if int(m.group("year")) != year:
            raise ValueError(f"fed {year}: Überschrift mit fremdem Jahr: {m.group(0)!r}")
        d = _DESCRIPTOR.match(m.group("text"))
        if not d:
            raise ValueError(f"fed {year}: unlesbare Überschrift: {m.group('text')!r}")
        start, end = _span(
            d.group("months"),
            d.group("m2"),
            int(d.group("d1")),
            int(d.group("d2")) if d.group("d2") else None,
            year,
        )
        meeting_type = _classify(d.group("rest"))
        section = html[m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(html)]
        rows.append(
            {
                "event_type": "fomc",
                "date": end,
                "scheduled": meeting_type == "meeting",
                "source": SOURCE,
                "meeting_start": start,
                "meeting_type": meeting_type,
                "statement_date": _statement_date(section, end),
                "sep": pd.NA,  # auf den historischen Seiten nicht markiert
            }
        )
    if not rows:
        raise ValueError(f"fed {year}: keine Termine gefunden (Seitenstruktur geändert?)")
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def parse_current(html: str) -> pd.DataFrame:
    """Aktuelle Kalenderseite (Jahres-Panels mit fomc-meeting-Blöcken) parsen."""
    year_marks = [(m.start(), int(m.group(1))) for m in _YEAR_PANEL.finditer(html)]
    if not year_marks:
        raise ValueError("fed aktuell: keine Jahres-Panels gefunden (Seitenstruktur geändert?)")
    block_starts = [m.start() for m in _MEETING_BLOCK.finditer(html)]
    rows = []
    for i, pos in enumerate(block_starts):
        block = html[pos : block_starts[i + 1] if i + 1 < len(block_starts) else len(html)]
        years_before = [y for p, y in year_marks if p < pos]
        month_m, date_m = _MONTH_CELL.search(block), _DATE_CELL.search(block)
        if not (years_before and month_m and date_m):
            raise ValueError(f"fed aktuell: unlesbarer Sitzungsblock bei Offset {pos}")
        year = years_before[-1]
        cell = date_m.group(1).strip()
        annotation = re.search(r"\(([^)]*)\)", cell)
        days = re.match(r"(\d{1,2})(?:-(\d{1,2}))?", cell)
        if not days:
            raise ValueError(f"fed aktuell: unlesbare Datumszelle: {cell!r}")
        start, end = _span(
            month_m.group(1),
            None,
            int(days.group(1)),
            int(days.group(2)) if days.group(2) else None,
            year,
        )
        meeting_type = _classify(annotation.group(1)) if annotation else "meeting"
        rows.append(
            {
                "event_type": "fomc",
                "date": end,
                "scheduled": meeting_type == "meeting",
                "source": SOURCE,
                "meeting_start": start,
                "meeting_type": meeting_type,
                "statement_date": _statement_date(block, end),
                "sep": "*" in cell,  # * = Sitzung mit Summary of Economic Projections
            }
        )
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def download_all() -> list[tuple[Path, dict]]:
    """Aktuelle Kalenderseite + alle historischen Jahresseiten abrufen und roh cachen."""
    results = []
    payload = fetch_page("fomccalendars.htm")
    n = len(parse_current(payload.decode("utf-8", errors="replace")))
    results.append(
        write_cache(
            SOURCE,
            "fomccalendars",
            payload,
            EXT,
            {"url": f"{BASE_URL}/fomccalendars.htm"},
            rows=n,
        )
    )
    for year in range(FIRST_YEAR, LAST_HIST_YEAR + 1):
        time.sleep(0.5)  # Höflichkeitspause; 28 Seiten, keine Eile
        payload = fetch_page(f"fomchistorical{year}.htm")
        n = len(parse_historical(payload.decode("utf-8", errors="replace"), year))
        results.append(
            write_cache(
                SOURCE,
                f"fomchistorical{year}",
                payload,
                EXT,
                {"url": f"{BASE_URL}/fomchistorical{year}.htm"},
                rows=n,
            )
        )
    return results


def load_events() -> pd.DataFrame:
    """Alle gecachten Fed-Seiten parsen und zu einer Terminliste zusammenführen."""
    frames = []
    for year in range(FIRST_YEAR, LAST_HIST_YEAR + 1):
        raw_path, _ = cache_paths(SOURCE, f"fomchistorical{year}", EXT)
        frames.append(parse_historical(raw_path.read_text(errors="replace"), year))
    raw_path, _ = cache_paths(SOURCE, "fomccalendars", EXT)
    current = parse_current(raw_path.read_text(errors="replace"))
    # Überlapp aktueller Seite mit historischen Jahren vermeiden (Stand 2026: keiner)
    frames.append(current[current["date"].dt.year > LAST_HIST_YEAR])
    df = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    return df
