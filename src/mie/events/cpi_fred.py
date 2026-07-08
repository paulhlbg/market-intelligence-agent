"""Quelle „fred": historische CPI-Release-Termine via FRED-API (St. Louis Fed).

Endpoint /fred/release/dates, release_id 10 = „Consumer Price Index"
(die Release-ID wird beim R2-Mini-Check per /fred/release gegengeprüft).
Kostenloser API-Key nötig; FRED akzeptiert ihn nur als Query-Parameter —
der Key wird daher aus URL-Ausgaben, Meta und Logs herausgehalten.

Rolle: Kreuzabgleich-Quelle zum BLS-Archiv (R2-verifiziert am 08.07.2026:
Release-ID 10 = „Consumer Price Index", 456 Termine ab 18.01.1990). Achtung,
FREDs Release-Kalender ist eine Obermenge der monatlichen CPI-Releases: Er
enthält zusätzlich die jährlichen Saisonbereinigungs-Revisionen (Februar) und
Sonder-Releases (z. B. die Korrektur vom 28.09.2000) — Details im Quellen-Report.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from mie.sources import cache_paths, write_cache

SOURCE = "fred"
EXT = "json"
BASE_URL = "https://api.stlouisfed.org/fred"
RELEASE_ID = 10
REALTIME_START = "1990-01-01"  # vor SPY-Start 1993; API liefert ab Verfügbarkeit
USER_AGENT = "mie-a3 (privates Forschungsprojekt)"


def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FRED_API_KEY ist nicht gesetzt. Kostenlosen Key anlegen "
            "(fred.stlouisfed.org → My Account → API Keys), dann: export FRED_API_KEY=…"
        )
    return key


def _get(path: str, params: dict) -> bytes:
    query = urllib.parse.urlencode({**params, "api_key": _api_key(), "file_type": "json"})
    req = urllib.request.Request(f"{BASE_URL}/{path}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_release_info() -> dict:
    """Release-Stammdaten (Name zur ID) — für den R2-Mini-Check."""
    payload = _get("release", {"release_id": RELEASE_ID})
    return json.loads(payload)["releases"][0]


def fetch_raw() -> tuple[bytes, dict]:
    """Alle historischen Release-Termine als Roh-JSON-Bytes holen (ohne zu cachen)."""
    params = {
        "release_id": RELEASE_ID,
        "realtime_start": REALTIME_START,
        "limit": 10000,
        "sort_order": "asc",
    }
    payload = _get("release/dates", params)
    # api_key gehört nie in die Meta-Parameter (R3-Datenversion ohne Zugangsdaten)
    return payload, {"endpoint": f"{BASE_URL}/release/dates", **params}


def parse_bytes(payload: bytes) -> pd.DataFrame:
    """Roh-JSON in das Einheitsschema überführen."""
    data = json.loads(payload)
    dates = data.get("release_dates", [])
    if not dates:
        raise ValueError("fred: Response ohne release_dates")
    df = pd.DataFrame(
        {
            "event_type": "cpi",
            "date": pd.to_datetime([d["date"] for d in dates]),
            "scheduled": True,
            "source": SOURCE,
        }
    )
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def download_all() -> list[tuple[Path, dict]]:
    """Release-Termine abrufen und roh cachen."""
    payload, params = fetch_raw()
    n = len(parse_bytes(payload))
    return [write_cache(SOURCE, "cpi_release_dates", payload, EXT, params, rows=n)]


def load_events() -> pd.DataFrame | None:
    """Gecachte Release-Termine parsen; None, wenn (noch) kein Cache existiert."""
    raw_path, _ = cache_paths(SOURCE, "cpi_release_dates", EXT)
    if not raw_path.exists():
        return None
    return parse_bytes(raw_path.read_bytes())
