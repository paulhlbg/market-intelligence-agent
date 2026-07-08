"""Termin-Quellen (A3): FOMC-Zinsentscheide und US-CPI-Veröffentlichungen.

Gemeinsames Einheitsschema und Zeitzonen-Helfer. Jede Quelle liefert nach dem
Parsen einen DataFrame mit mindestens EVENT_COLUMNS (zusätzliche Spalten je
Quelle erlaubt, z. B. meeting_type bei FOMC, ref_month bei CPI). Rohdaten
werden unverändert gecacht (mie.sources.write_cache), Parsing ist strikt
davon getrennt.

Zeitkonvention: Veröffentlichungszeiten sind US-Ostküstenzeit (ET). ET wechselt
zwischen EST (UTC−5, Winter) und EDT (UTC−4, Sommer); „14:00 ET" ist also je
nach Datum 19:00 oder 18:00 UTC. Umrechnung ausschließlich über et_to_utc
(IANA-Zeitzone America/New_York), nie über feste Offsets.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

# Einheitsschema: eine Zeile je Termin, date = Ankündigungs-/Veröffentlichungstag,
# scheduled = regulär angesetzter Termin (False z. B. bei FOMC-Notfallaktionen).
EVENT_COLUMNS = ["event_type", "date", "scheduled", "source"]
EVENT_TYPES = {"fomc", "cpi"}

ET = ZoneInfo("America/New_York")


def et_to_utc(date: pd.Timestamp, time_et: str) -> pd.Timestamp:
    """Datum + Uhrzeit „HH:MM" in ET (America/New_York) → UTC-Zeitstempel (DST-korrekt)."""
    hour, minute = (int(part) for part in time_et.split(":"))
    local = datetime(date.year, date.month, date.day, hour, minute, tzinfo=ET)
    return pd.Timestamp(local).tz_convert("UTC")


def validate_events_frame(df: pd.DataFrame) -> list[str]:
    """Schema-Prüfung; gibt Liste der Probleme zurück (leer = ok)."""
    problems: list[str] = []
    missing = [c for c in EVENT_COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"fehlende Spalten: {missing}")
        return problems
    if len(df) == 0:
        problems.append("leerer DataFrame")
        return problems
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        problems.append("date ist kein Datetime-Typ")
    elif not df["date"].is_monotonic_increasing:
        problems.append("date nicht aufsteigend sortiert")
    bad_types = set(df["event_type"].unique()) - EVENT_TYPES
    if bad_types:
        problems.append(f"unbekannte event_type-Werte: {sorted(bad_types)}")
    return problems
