"""Quelle „tiingo_crypto": BTC-Tagesbars (btcusd) via Tiingo-Krypto-REST-API (A6).

API-Key wie bei „tiingo" ausschließlich aus TIINGO_API_KEY (Authorization-Header;
nie in URL, Cache, Meta oder Logs). Der Krypto-Endpoint liefert je Ticker ein
Objekt mit verschachteltem priceData; Bars sind UTC-Kalendertage (Stempel
00:00+00:00), und der laufende, noch unfertige UTC-Tag ist enthalten (R2-Check
08.07.2026) — ihn zu verwerfen ist Sache der Ledger-Schicht (Anker-Regel in
docs/zieldefinitionen.md).

Lange Zeiträume werden vom Endpoint GEKAPPT (R2-Befund 08.07.2026: Volldownload
ab 2011 endete bei 2024-09-09), deshalb wird paginiert abgerufen. Die „Rohdatei"
ist — abweichend von der A2-Konvention „exakte Response-Bytes" — das aus allen
Seiten zusammengefügte Ticker-Objekt in Original-Response-Form; die Meta
dokumentiert die Anzahl der Requests.

Rolle laut Beschluss des Projektinhabers vom 08.07.2026: NUR Kreuzabgleich —
Primärquelle des BTC-Ledger-Zweigs ist „coinbase" (Begründung:
docs/reports/a6_btc_quellen.md; der Feed hier hat eine echte Lücke am
2026-02-15 und aggregiert laut Tiingo-Meta „Bitcoin Tether (BTC/USD)").
"""

import json
import time as time_mod
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from mie.sources import write_raw_cache
from mie.sources.tiingo import _api_key

SOURCE = "tiingo_crypto"
EXT = "json"
BASE_URL = "https://api.tiingo.com/tiingo/crypto/prices"
TICKER = "btcusd"
START_DATE = "2011-01-01"  # Feed beginnt laut R2-Check am 19.08.2011; API liefert ab Verfügbarkeit
PAGE_DAYS = 700  # weit unter der beobachteten Kappungsgrenze (~4700 Zeilen)
REQUEST_PAUSE_S = 0.25  # Freikontingent mit Stundenlimits — bewusst gedrosselt


def fetch_raw(
    ticker: str = TICKER, start_date: str = START_DATE, end_date: str | None = None
) -> tuple[bytes, dict]:
    """Ein Fenster Tagesbars als Roh-JSON-Bytes holen (ohne zu cachen; ein Request)."""
    url = f"{BASE_URL}?tickers={ticker.lower()}&startDate={start_date}&resampleFreq=1day"
    if end_date:
        url += f"&endDate={end_date}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {_api_key()}",
            "Accept": "application/json",
            "User-Agent": "mie-a6 (privates Forschungsprojekt)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
    params = {
        "endpoint": BASE_URL,
        "tickers": ticker.lower(),
        "startDate": start_date,
        "resampleFreq": "1day",
    }
    if end_date:
        params["endDate"] = end_date
    return payload, params


def fetch_all(
    ticker: str = TICKER, start_date: str = START_DATE, end_date: str | None = None
) -> tuple[bytes, dict]:
    """Volle Historie paginiert holen; Ergebnis = ein Ticker-Objekt in Response-Form."""
    start = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
    end = (
        datetime.fromisoformat(end_date).replace(tzinfo=UTC)
        if end_date
        else datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    header: dict = {}
    by_date: dict[str, dict] = {}
    n_requests = 0
    cursor = start
    while True:
        window_end = min(cursor + timedelta(days=PAGE_DAYS - 1), end)
        payload, _ = fetch_raw(ticker, cursor.date().isoformat(), window_end.date().isoformat())
        n_requests += 1
        records = json.loads(payload)
        if records:
            header = {k: v for k, v in records[0].items() if k != "priceData"}
            for bar in records[0].get("priceData", []):
                by_date[bar["date"]] = bar  # Duplikate über Fenstergrenzen: letzter gewinnt
        if window_end >= end:
            break
        # Fenster überlappen um einen Tag: endDate ist je nach Daten-Ära inklusiv
        # oder exklusiv (R2-Befund 08.07.2026) — der Überlapp macht das egal.
        cursor = window_end
        time_mod.sleep(REQUEST_PAUSE_S)
    merged = [{**header, "priceData": [by_date[d] for d in sorted(by_date)]}] if by_date else []
    payload = (json.dumps(merged, separators=(",", ":")) + "\n").encode("utf-8")
    params = {
        "endpoint": BASE_URL,
        "tickers": ticker.lower(),
        "startDate": start.date().isoformat(),
        "endDate": end.date().isoformat(),
        "resampleFreq": "1day",
        "n_requests": n_requests,
        "assembled": "paginierte Responses zusammengefügt (Endpoint kappt lange Zeiträume)",
    }
    return payload, params


def download_daily(ticker: str = TICKER) -> tuple[Path, dict]:
    """Volle Tageshistorie (paginiert) abrufen und cachen. Gibt (Rohpfad, Meta) zurück."""
    payload, params = fetch_all(ticker)
    records = json.loads(payload)
    rows = len(records[0]["priceData"]) if records else 0
    return write_raw_cache(SOURCE, ticker, payload, EXT, params, rows=rows)


def parse_bytes(payload: bytes) -> pd.DataFrame:
    """Roh-JSON in einen Tages-Frame überführen (date/open/high/low/close/volume)."""
    records = json.loads(payload)
    if not records or not records[0].get("priceData"):
        raise ValueError("tiingo_crypto: leerer Response")
    if len(records) != 1:
        raise ValueError(f"tiingo_crypto: {len(records)} Ticker-Objekte statt 1")
    df = pd.DataFrame.from_records(records[0]["priceData"])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
    cols = ["date", "open", "high", "low", "close", "volume"]
    return df[cols].sort_values("date").reset_index(drop=True)


def parse_cached(raw_path: Path) -> pd.DataFrame:
    """Gecachte Roh-JSON-Datei parsen."""
    return parse_bytes(raw_path.read_bytes())
