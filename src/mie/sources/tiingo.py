"""Quelle „tiingo": Tageskurse via Tiingo REST-API (kostenloses Kontingent).

API-Key ausschließlich aus der Umgebungsvariable TIINGO_API_KEY; er wird per
Authorization-Header gesendet und taucht nie in URL, Cache, Meta oder Logs auf.
Rohdaten = exakte Response-Bytes (JSON). Felder laut API-Doku: close/adjClose
getrennt sowie divCash/splitFactor je Tag — Format wird beim R2-Mini-Check
gegen einen echten Response verifiziert (Fixture wird daraus eingefroren).
"""

import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

from mie.sources import write_raw_cache

SOURCE = "tiingo"
EXT = "json"
BASE_URL = "https://api.tiingo.com/tiingo/daily"
START_DATE = "1990-01-01"  # vor SPY-Auflegung 1993; API liefert ab Verfügbarkeit


def _api_key() -> str:
    key = os.environ.get("TIINGO_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "TIINGO_API_KEY ist nicht gesetzt. Kostenlosen Key anlegen (tiingo.com), "
            "dann: export TIINGO_API_KEY=…"
        )
    return key


def fetch_raw(
    ticker: str, start_date: str = START_DATE, end_date: str | None = None
) -> tuple[bytes, dict]:
    """Tageshistorie als Roh-JSON-Bytes holen (ohne zu cachen); end_date nur für Mini-Checks."""
    url = f"{BASE_URL}/{ticker.lower()}/prices?startDate={start_date}&format=json"
    if end_date:
        url += f"&endDate={end_date}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {_api_key()}",
            "Accept": "application/json",
            "User-Agent": "mie-a2 (privates Forschungsprojekt)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    params = {"endpoint": f"{BASE_URL}/<ticker>/prices", "startDate": start_date, "format": "json"}
    if end_date:
        params["endDate"] = end_date
    return payload, params


def download_daily(ticker: str) -> tuple[Path, dict]:
    """Volle Tageshistorie abrufen und roh cachen. Gibt (Rohpfad, Meta) zurück."""
    payload, params = fetch_raw(ticker)
    rows = len(json.loads(payload))
    return write_raw_cache(SOURCE, ticker, payload, EXT, params, rows=rows)


def parse_bytes(payload: bytes) -> pd.DataFrame:
    """Roh-JSON in das Einheitsschema überführen (+ div_cash, split_factor)."""
    records = json.loads(payload)
    if not records:
        raise ValueError("tiingo: leerer Response")
    df = pd.DataFrame.from_records(records)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
    df = df.rename(
        columns={"adjClose": "adj_close", "divCash": "div_cash", "splitFactor": "split_factor"}
    )
    cols = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "div_cash",
        "split_factor",
    ]
    return df[cols].sort_values("date").reset_index(drop=True)


def parse_cached(raw_path: Path) -> pd.DataFrame:
    """Gecachte Roh-JSON-Datei parsen."""
    return parse_bytes(raw_path.read_bytes())
