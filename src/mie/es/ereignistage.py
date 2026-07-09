"""Ereignistag-Loader der Ereignisstudie (Terminlisten aus data/processed/).

Konventionen aus docs/zieldefinitionen.md („Ereignistag-Konventionen") und den
eingefrorenen Hypothesen-Dateien:
- FOMC: nur reguläre Sitzungen (meeting_type = "meeting"); Ereignistag = date
  (= Statement-/Entscheidungstag = letzter Sitzungstag).
- CPI: Ereignistag = Release-Tag; Einzelfall-Korrektur Februar 1998 laut
  docs/reports/a3_quellen.md §2.6 — der BLS-Archiv-Dateiname trägt ein
  falsches Datum, korrekt ist der 24.02.1998.

Die Loader liefern reine Terminmengen ohne jede Statistik; Auswertung erst in
B1–B3 (docs/freigabeplan_b_es.md).
"""

from pathlib import Path

import pandas as pd

from mie.es import EsError
from mie.sources import REPO_ROOT

FOMC_CSV = REPO_ROOT / "data" / "processed" / "fomc_termine.csv"
CPI_CSV = REPO_ROOT / "data" / "processed" / "cpi_termine.csv"

# Einzelfall Februar 1998 (a3_quellen.md §2.6): BLS-Archiv-Dateiname falsch,
# FRED und der Release-Text selbst belegen den 24.02.1998.
CPI_DATUM_KORREKTUR = {pd.Timestamp("1998-02-25"): pd.Timestamp("1998-02-24")}


def _load_dates(path: Path, needed: list[str]) -> pd.DataFrame:
    if not path.is_file():
        raise EsError(f"Terminliste fehlt: {path}")
    df = pd.read_csv(path)
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise EsError(f"{path.name}: fehlende Spalten {missing}")
    df["date"] = pd.to_datetime(df["date"])
    return df


def _as_index(dates: pd.Series, name: str) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(dates.sort_values().unique())
    if len(idx) == 0:
        raise EsError(f"{name}: keine Ereignistage übrig")
    return idx


def load_fomc_days(path: Path = FOMC_CSV) -> pd.DatetimeIndex:
    """Reguläre FOMC-Ereignistage (meeting_type = "meeting"), aufsteigend, eindeutig."""
    df = _load_dates(path, ["date", "meeting_type"])
    regular = df.loc[df["meeting_type"] == "meeting", "date"]
    return _as_index(regular, "FOMC")


def load_cpi_days(path: Path = CPI_CSV) -> pd.DatetimeIndex:
    """CPI-Release-Tage inkl. Einzelfall-Korrektur Februar 1998, aufsteigend, eindeutig."""
    df = _load_dates(path, ["date"])
    dates = df["date"].replace(CPI_DATUM_KORREKTUR)
    return _as_index(dates, "CPI")
