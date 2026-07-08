"""Quelle „bls": CPI-Veröffentlichungstermine von bls.gov (gemeinfreie US-Regierungsseite).

Zwei Seiten (R2-verifiziert am 08.07.2026):
- Terminplan /schedule/news_release/cpi.htm: die nächsten ~13 Termine als Tabelle
  (Referenzmonat, Release-Datum, Release-Uhrzeit — durchgehend „08:30 AM" ET);
- Release-Archiv /bls/news-release/cpi.htm: alle bisherigen CPI-Releases als
  <li>-Liste, Release-Datum steckt in der Link-URL — cpi_<MMTTJJJJ> ab Juni 1999,
  davor 6-stellig cpi_<MMTTJJ> (z. B. cpi_021794.txt = 17.02.1994); Referenzmonat
  im Linktext. Deckung ab Februar 1994 (R2-verifiziert am 08.07.2026).

BLS blockiert Abrufe ohne Kontaktangabe im User-Agent (HTTP 403 mit Hinweis auf
die BLS-Richtlinie zu automatisierten Abrufen); daher enthält der User-Agent
die Kontakt-E-Mail des Projektinhabers. Kein Umgehen von Schutzmaßnahmen.
"""

import re
import urllib.request
from pathlib import Path

import pandas as pd

from mie.sources import cache_paths, write_cache

SOURCE = "bls"
EXT = "html"
SCHEDULE_URL = "https://www.bls.gov/schedule/news_release/cpi.htm"
ARCHIVE_URL = "https://www.bls.gov/bls/news-release/cpi.htm"
# BLS verlangt Kontaktinfo im UA; E-Mail des Projektinhabers (steht auch in git log).
USER_AGENT = "mie-a3 research (privates Forschungsprojekt; helbigpaul110@gmail.com)"

_LI = re.compile(r"<li>(.*?)</li>", re.S)
_REF_MONTH = re.compile(r"([A-Z][a-z]+ \d{4}) Consumer Price Index")
# Release-Datum in der URL: 8-stellig MMTTJJJJ (ab Juni 1999) oder 6-stellig
# MMTTJJ (Feb. 1994 – Mai 1999); Jahrhundert-Heuristik unkritisch (Daten ab 1994)
_RELEASE_DATE = re.compile(r"cpi_(\d{2})(\d{2})(\d{4}|\d{2})(?!\d)\.(?:htm|pdf|txt)")


def _iso_date(month: str, day: str, year: str) -> str:
    if len(year) == 2:
        year = ("19" if int(year) >= 50 else "20") + year
    return f"{year}-{month}-{day}"


_SCHEDULE_ROW = re.compile(r"<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>")


def fetch_page(url: str) -> bytes:
    """Eine Seite von bls.gov holen (ohne zu cachen)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _ref_month_iso(text: str) -> str:
    """„May 2002" → „2002-05"."""
    return pd.Period(text, freq="M").strftime("%Y-%m")


def parse_archive(html: str) -> pd.DataFrame:
    """Release-Archiv parsen: ein <li> = ein Release (mehrere Formatlinks, ein Datum)."""
    rows = []
    for li in _LI.findall(html):
        dates = {_iso_date(m, d, y) for m, d, y in _RELEASE_DATE.findall(li)}
        if not dates:
            continue  # Navigations-/Fremdeinträge ohne CPI-Release-Link
        if len(dates) > 1:
            raise ValueError(f"bls-Archiv: mehrere Daten in einem Eintrag: {sorted(dates)}")
        ref = _REF_MONTH.search(li)
        rows.append(
            {
                "event_type": "cpi",
                "date": pd.Timestamp(dates.pop()),
                "scheduled": True,
                "source": SOURCE,
                "ref_month": _ref_month_iso(ref.group(1)) if ref else pd.NA,
                "time_et": pd.NA,  # das Archiv nennt keine Uhrzeit
            }
        )
    if not rows:
        raise ValueError("bls-Archiv: keine Releases gefunden (Seitenstruktur geändert?)")
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def parse_schedule(html: str) -> pd.DataFrame:
    """Terminplan-Tabelle parsen (kommende Releases inkl. Uhrzeit)."""
    rows = []
    for ref, date_text, time_text in _SCHEDULE_ROW.findall(html):
        when = pd.to_datetime(date_text.replace(".", ""), format="%b %d, %Y")
        time_et = pd.to_datetime(time_text.strip(), format="%I:%M %p").strftime("%H:%M")
        rows.append(
            {
                "event_type": "cpi",
                "date": when,
                "scheduled": True,
                "source": SOURCE,
                "ref_month": _ref_month_iso(ref.strip()),
                "time_et": time_et,
            }
        )
    if not rows:
        raise ValueError("bls-Terminplan: keine Zeilen gefunden (Seitenstruktur geändert?)")
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def download_all() -> list[tuple[Path, dict]]:
    """Terminplan + Archiv abrufen und roh cachen."""
    results = []
    for name, url, parser in (
        ("cpi_schedule", SCHEDULE_URL, parse_schedule),
        ("cpi_archive", ARCHIVE_URL, parse_archive),
    ):
        payload = fetch_page(url)
        n = len(parser(payload.decode("utf-8", errors="replace")))
        results.append(write_cache(SOURCE, name, payload, EXT, {"url": url}, rows=n))
    return results


def load_events() -> pd.DataFrame:
    """Gecachte Seiten parsen und vereinen; bei Überlapp gewinnt der Archiv-Eintrag,
    die Uhrzeit aus dem Terminplan wird — wo vorhanden — übernommen."""
    archive_path, _ = cache_paths(SOURCE, "cpi_archive", EXT)
    schedule_path, _ = cache_paths(SOURCE, "cpi_schedule", EXT)
    archive = parse_archive(archive_path.read_text(errors="replace"))
    schedule = parse_schedule(schedule_path.read_text(errors="replace"))
    times = schedule.set_index("date")["time_et"]
    archive["time_et"] = archive["date"].map(times).astype("object").fillna(pd.NA)
    extra = schedule[~schedule["date"].isin(archive["date"])]
    df = pd.concat([archive, extra], ignore_index=True).sort_values("date")
    return df.reset_index(drop=True)
