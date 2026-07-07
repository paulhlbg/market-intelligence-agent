"""Kursdaten-Quellen (A2).

Gemeinsames Einheitsschema und Cache-Helfer. Jede Quelle liefert nach dem Parsen
einen DataFrame mit den Spalten STANDARD_COLUMNS (zusätzliche Spalten erlaubt,
z. B. div_cash/split_factor bei Tiingo). Rohdaten werden unverändert gecacht,
Parsing ist strikt davon getrennt.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# Einheitsschema nach dem Parsen: ein Handelstag je Zeile, date aufsteigend.
STANDARD_COLUMNS = ["date", "open", "high", "low", "close", "adj_close", "volume"]

# Repo-Wurzel = drei Ebenen über dieser Datei (src/mie/sources/__init__.py).
REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"


def raw_paths(source: str, ticker: str, ext: str) -> tuple[Path, Path]:
    """Pfade für Rohdatei und Meta-Sidecar eines Downloads."""
    base = RAW_DIR / source
    return base / f"{ticker.lower()}_daily.{ext}", base / f"{ticker.lower()}_daily.meta.json"


def write_raw_cache(
    source: str,
    ticker: str,
    payload: bytes,
    ext: str,
    params: dict,
    rows: int,
    extra_meta: dict | None = None,
) -> tuple[Path, dict]:
    """Rohbytes unverändert cachen und Meta-Sidecar schreiben.

    Meta enthält Abrufparameter, UTC-Zeitpunkt, SHA-256 und Umfang —
    das ist die „Datenversion" im Sinne von R3. Niemals Zugangsdaten aufnehmen.
    """
    raw_path, meta_path = raw_paths(source, ticker, ext)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    meta = {
        "source": source,
        "ticker": ticker,
        "params": params,
        "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "rows": rows,
    }
    if extra_meta:
        meta.update(extra_meta)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return raw_path, meta


def read_meta(source: str, ticker: str, ext: str) -> dict:
    """Meta-Sidecar eines gecachten Downloads lesen."""
    _, meta_path = raw_paths(source, ticker, ext)
    return json.loads(meta_path.read_text())


def validate_standard_frame(df: pd.DataFrame) -> list[str]:
    """Schema-Prüfung; gibt Liste der Probleme zurück (leer = ok)."""
    problems: list[str] = []
    missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
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
    return problems
