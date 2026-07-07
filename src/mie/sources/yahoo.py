"""Quelle „yahoo": Tageskurse via yfinance-Bibliothek.

Besonderheit gegenüber Tiingo: Die Bibliothek liefert keinen Roh-Response,
sondern direkt einen DataFrame. „Rohdaten" heißt hier: der unveränderte
Bibliotheks-Output, verlustfrei als CSV eingefroren (dokumentiert im Report).
auto_adjust=False, damit Close (roh) und Adj Close getrennt vorliegen.
"""

import io
from pathlib import Path

import pandas as pd
import yfinance as yf

from mie.sources import write_raw_cache

SOURCE = "yahoo"
EXT = "csv"


def download_daily(ticker: str) -> tuple[Path, dict]:
    """Maximale Tageshistorie abrufen und roh cachen. Gibt (Rohpfad, Meta) zurück."""
    df = yf.download(ticker, period="max", auto_adjust=False, progress=False)
    if df is None or len(df) == 0:
        raise RuntimeError(f"yahoo: leere Antwort für {ticker} — Zugriff blockiert?")
    # MultiIndex-Spalten (Price, Ticker) flach ziehen; Reihenfolge unverändert lassen.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    payload = df.to_csv().encode("utf-8")
    params = {"function": "yfinance.download", "period": "max", "auto_adjust": False}
    extra = {"yfinance_version": yf.__version__, "raw_note": "Bibliotheks-Output als CSV"}
    return write_raw_cache(SOURCE, ticker, payload, EXT, params, rows=len(df), extra_meta=extra)


def parse_cached(raw_path: Path) -> pd.DataFrame:
    """Gecachte CSV in das Einheitsschema überführen."""
    df = pd.read_csv(raw_path, parse_dates=["Date"])
    df = df.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    return df[cols].sort_values("date").reset_index(drop=True)


def parse_bytes(payload: bytes) -> pd.DataFrame:
    """Wie parse_cached, aber direkt aus Bytes (für Tests mit Fixtures)."""
    return parse_cached(io.BytesIO(payload))  # type: ignore[arg-type]
