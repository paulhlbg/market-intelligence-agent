"""Quelle „coinbase": BTC-USD-Tageskerzen via Coinbase-Exchange-Public-API (A6, nur Kreuzabgleich).

Öffentliche Market-Data-Endpoints ohne Key; maximal 300 Kerzen je Request →
Paginierung. Die „Rohdatei" ist deshalb — abweichend von der A2-Konvention
„exakte Response-Bytes" — die zusammengefügte, nach Zeit aufsteigend sortierte
Kerzenliste aller Seiten (ein JSON-Array); die Meta dokumentiert die Anzahl der
Requests. Kerzenformat laut Doku und R2-Check 08.07.2026:
[time, low, high, open, close, volume], time = Bucket-Start in Epochensekunden
UTC (Tagesbucket = UTC-Kalendertag).
"""

import json
import time as time_mod
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from mie.sources import write_raw_cache

SOURCE = "coinbase"
EXT = "json"
BASE_URL = "https://api.exchange.coinbase.com/products"
PRODUCT = "BTC-USD"
TICKER = "btcusd"  # Cache-Name (A2-Konvention <ticker>_daily)
START_DATE = "2015-07-20"  # erster BTC-USD-Handelstag auf Coinbase Exchange (R2-Check)
GRANULARITY = 86400
PAGE_DAYS = 290  # < 300-Kerzen-Limit je Request
REQUEST_PAUSE_S = 0.15  # Public-Rate-Limit ~10 Requests/s — bewusst weit darunter


def _get(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "mie-a6 (privates Forschungsprojekt)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_all_candles(
    product: str = PRODUCT, start_date: str = START_DATE, end_date: str | None = None
) -> tuple[bytes, dict]:
    """Alle Tageskerzen paginiert holen; Ergebnis = ein JSON-Array, aufsteigend sortiert."""
    start = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
    end = (
        datetime.fromisoformat(end_date).replace(tzinfo=UTC)
        if end_date
        else datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    by_time: dict[int, list] = {}
    n_requests = 0
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=PAGE_DAYS - 1), end)
        url = (
            f"{BASE_URL}/{product}/candles?granularity={GRANULARITY}"
            f"&start={cursor.date().isoformat()}T00:00:00Z"
            f"&end={window_end.date().isoformat()}T00:00:00Z"
        )
        candles = json.loads(_get(url))
        n_requests += 1
        for candle in candles:
            by_time[int(candle[0])] = candle  # Duplikate über Seitengrenzen: letzter gewinnt
        cursor = window_end + timedelta(days=1)
        time_mod.sleep(REQUEST_PAUSE_S)
    merged = [by_time[t] for t in sorted(by_time)]
    payload = (json.dumps(merged, separators=(",", ":")) + "\n").encode("utf-8")
    params = {
        "endpoint": f"{BASE_URL}/{product}/candles",
        "granularity": GRANULARITY,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "n_requests": n_requests,
        "assembled": "paginierte Responses zusammengefügt (kein Einzel-Response)",
    }
    return payload, params


def download_daily(ticker: str = TICKER) -> tuple[Path, dict]:
    """Volle Tageshistorie (paginiert) abrufen und cachen. Gibt (Rohpfad, Meta) zurück."""
    if ticker.lower() != TICKER:
        raise ValueError(f"coinbase: nur {TICKER} vorgesehen (Produkt {PRODUCT})")
    payload, params = fetch_all_candles()
    rows = len(json.loads(payload))
    return write_raw_cache(SOURCE, ticker, payload, EXT, params, rows=rows)


def parse_bytes(payload: bytes) -> pd.DataFrame:
    """Kerzen-Array in einen Tages-Frame überführen (date/open/high/low/close/volume)."""
    candles = json.loads(payload)
    if not candles:
        raise ValueError("coinbase: leere Kerzenliste")
    df = pd.DataFrame(candles, columns=["time", "low", "high", "open", "close", "volume"])
    df["date"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_localize(None).dt.normalize()
    cols = ["date", "open", "high", "low", "close", "volume"]
    return df[cols].sort_values("date").reset_index(drop=True)


def parse_cached(raw_path: Path) -> pd.DataFrame:
    """Gecachte Kerzen-Datei parsen."""
    return parse_bytes(raw_path.read_bytes())
