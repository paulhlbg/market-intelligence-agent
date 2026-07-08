"""Prognose-Ledger v0 (A4): Schema, Validierung, Append-only-I/O, Auflösung.

Zwei committete CSV-Dateien im Repo:
- ledger/prognosen.csv    — eine Zeile je registrierter Prognose
- ledger/aufloesungen.csv — eine Zeile je aufgelöster Prognose

Alte Zeilen werden nie verändert; Auflösungen sind deshalb eigene angehängte
Zeilen in einer eigenen Datei. Der Append-only-Wächter prüft vor jedem
Schreiben, dass der aktuelle Dateiinhalt byteweise mit dem zuletzt committeten
Stand (git HEAD) beginnt — veränderte oder gelöschte alte Zeilen führen zur
Verweigerung. Zieldefinition w1_up_v1 und Modell klimatologie_v0:
docs/zieldefinitionen.md.
"""

import subprocess
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from mie.checks import expected_trading_days
from mie.ledger.klimatologie import window_return
from mie.sources import REPO_ROOT

TARGET_W1_UP_V1 = "w1_up_v1"

FORECAST_COLUMNS = [
    "forecast_id",
    "created_utc",
    "asset",
    "horizon",
    "target_id",
    "anchor_date",
    "anchor_close",
    "target_date",
    "probability",
    "model_id",
    "train_n",
    "train_start",
    "train_end",
    "data_version",
    "code_commit",
    "event_type",  # leer bis Phase B (ereignisbezogene Prognosen)
    "event_date",  # leer bis Phase B
]
REQUIRED_FORECAST_FIELDS = FORECAST_COLUMNS[:15]  # alles außer event_type/event_date

RESOLUTION_COLUMNS = [
    "forecast_id",
    "resolved_utc",
    "realized_return",
    "outcome",
    "resolution_date",
    "data_version",
    "code_commit",
]

# Werte müssen zeilen-diffbar bleiben (Append-only-Review): kein CSV-Quoting nötig.
_FORBIDDEN_CHARS = set(',"\n\r')


class LedgerError(RuntimeError):
    """Fehler im Ledger-Betrieb; führt stets zum Abbruch statt zu stiller Reparatur."""


def prognosen_path(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "ledger" / "prognosen.csv"


def aufloesungen_path(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "ledger" / "aufloesungen.csv"


def code_commit(repo_root: Path = REPO_ROOT) -> str:
    """Kurzer Git-Commit-Hash (Pflichtfeld je Zeile; ohne Git kein Ledger-Betrieb)."""
    res = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=repo_root
    )
    if res.returncode != 0:
        raise LedgerError("git rev-parse fehlgeschlagen — code_commit ist Pflichtfeld je Zeile")
    return res.stdout.strip()


def _head_bytes(path: Path, repo_root: Path) -> bytes | None:
    """Inhalt der Datei im letzten Commit; None, wenn dort (noch) nicht vorhanden."""
    rel = path.relative_to(repo_root).as_posix()
    res = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True, cwd=repo_root)
    return res.stdout if res.returncode == 0 else None


def ensure_append_only(path: Path, repo_root: Path = REPO_ROOT) -> None:
    """Wächter: aktueller Inhalt muss byteweise mit dem committeten Stand beginnen."""
    head = _head_bytes(path, repo_root)
    if head is None:
        return  # Datei noch nie committet — nichts zu schützen
    if not path.read_bytes().startswith(head):
        raise LedgerError(
            f"Append-only verletzt: {path.name} weicht vom committeten Stand ab "
            "(alte Zeilen verändert oder gelöscht?). Schreiben verweigert — "
            "Arbeitskopie prüfen (git diff), nichts still reparieren."
        )


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def _common_problems(row: dict, columns: list[str], required: list[str]) -> list[str]:
    problems = [f"unbekanntes Feld: {k}" for k in row if k not in columns]
    problems += [f"{f}: Pflichtfeld fehlt oder leer" for f in required if not str(row.get(f, ""))]
    problems += [
        f"{k}: unzulässige Zeichen (Komma/Anführungszeichen/Zeilenumbruch)"
        for k, v in row.items()
        if _FORBIDDEN_CHARS & set(str(v))
    ]
    return problems


def validate_forecast_row(row: dict) -> list[str]:
    """Schema-Check einer Prognosezeile; Liste der Probleme (leer = ok)."""
    problems = _common_problems(row, FORECAST_COLUMNS, REQUIRED_FORECAST_FIELDS)
    if problems:
        return problems
    if not _is_iso_datetime(row["created_utc"]):
        problems.append("created_utc: kein ISO-Zeitstempel")
    for f in ["anchor_date", "target_date", "train_start", "train_end"]:
        if not _is_iso_date(row[f]):
            problems.append(f"{f}: kein ISO-Datum")
    try:
        p = float(row["probability"])
        if not 0.0 <= p <= 1.0:
            problems.append("probability: außerhalb [0, 1]")
    except ValueError:
        problems.append("probability: keine Zahl")
    try:
        float(row["anchor_close"])
    except ValueError:
        problems.append("anchor_close: keine Zahl")
    if not str(row["train_n"]).isdigit() or int(row["train_n"]) < 1:
        problems.append("train_n: keine positive ganze Zahl")
    if (
        _is_iso_date(row["anchor_date"])
        and _is_iso_date(row["target_date"])
        and row["target_date"] <= row["anchor_date"]
    ):
        problems.append("target_date: muss nach anchor_date liegen")
    return problems


def validate_resolution_row(row: dict) -> list[str]:
    """Schema-Check einer Auflösungszeile; Liste der Probleme (leer = ok)."""
    problems = _common_problems(row, RESOLUTION_COLUMNS, RESOLUTION_COLUMNS)
    if problems:
        return problems
    if not _is_iso_datetime(row["resolved_utc"]):
        problems.append("resolved_utc: kein ISO-Zeitstempel")
    if not _is_iso_date(row["resolution_date"]):
        problems.append("resolution_date: kein ISO-Datum")
    if row["outcome"] not in {"0", "1"}:
        problems.append("outcome: muss 0 oder 1 sein")
    try:
        tr = float(row["realized_return"])
        if row["outcome"] in {"0", "1"} and (tr > 0) != (row["outcome"] == "1"):
            problems.append("outcome: widerspricht realized_return (Regel: 1 gdw. TR > 0)")
    except ValueError:
        problems.append("realized_return: keine Zahl")
    return problems


def _load(path: Path, columns: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(df.columns) != columns:
        raise LedgerError(f"{path.name}: Spalten passen nicht zum Schema ({list(df.columns)})")
    return df


def load_forecasts(repo_root: Path = REPO_ROOT) -> pd.DataFrame:
    """Prognosen als String-DataFrame (Interpretation Sache der Aufrufer)."""
    return _load(prognosen_path(repo_root), FORECAST_COLUMNS)


def load_resolutions(repo_root: Path = REPO_ROOT) -> pd.DataFrame:
    """Auflösungen als String-DataFrame."""
    return _load(aufloesungen_path(repo_root), RESOLUTION_COLUMNS)


def _append(path: Path, columns: list[str], rows: list[dict], validate, repo_root: Path) -> int:
    if not rows:
        return 0
    if not path.exists():
        raise LedgerError(f"Ledger-Datei fehlt: {path}")
    content = path.read_bytes()
    header = content.split(b"\n", 1)[0].decode("utf-8")
    if header != ",".join(columns):
        raise LedgerError(f"{path.name}: Header passt nicht zum Schema")
    if not content.endswith(b"\n"):
        raise LedgerError(f"{path.name}: endet nicht mit Zeilenumbruch (manuell verändert?)")
    ensure_append_only(path, repo_root)
    problems = []
    for i, row in enumerate(rows):
        problems += [f"Zeile {i + 1}: {p}" for p in validate(row)]
    if problems:
        raise LedgerError("Validierung fehlgeschlagen:\n- " + "\n- ".join(problems))
    lines = "".join(",".join(str(row.get(c, "")) for c in columns) + "\n" for row in rows)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(lines)
    return len(rows)


def append_forecasts(rows: list[dict], repo_root: Path = REPO_ROOT) -> int:
    """Prognosezeilen anhängen; verweigert doppelte forecast_id."""
    existing = set(load_forecasts(repo_root)["forecast_id"])
    new_ids = [str(r.get("forecast_id", "")) for r in rows]
    dupes = sorted({i for i in new_ids if i in existing or new_ids.count(i) > 1})
    if dupes:
        raise LedgerError(f"forecast_id bereits vorhanden oder doppelt: {', '.join(dupes)}")
    return _append(
        prognosen_path(repo_root), FORECAST_COLUMNS, rows, validate_forecast_row, repo_root
    )


def append_resolutions(rows: list[dict], repo_root: Path = REPO_ROOT) -> int:
    """Auflösungszeilen anhängen; genau eine je existierender, offener Prognose."""
    known = set(load_forecasts(repo_root)["forecast_id"])
    resolved = set(load_resolutions(repo_root)["forecast_id"])
    new_ids = [str(r.get("forecast_id", "")) for r in rows]
    bad = sorted({i for i in new_ids if i not in known})
    if bad:
        raise LedgerError(f"Auflösung ohne Prognose: {', '.join(bad)}")
    dupes = sorted({i for i in new_ids if i in resolved or new_ids.count(i) > 1})
    if dupes:
        raise LedgerError(f"bereits aufgelöst oder doppelt: {', '.join(dupes)}")
    return _append(
        aufloesungen_path(repo_root), RESOLUTION_COLUMNS, rows, validate_resolution_row, repo_root
    )


def next_trading_days(after: pd.Timestamp, n: int) -> pd.DatetimeIndex:
    """Die n nächsten NYSE-Handelstage strikt nach `after` (Kalender XNYS wie in A2)."""
    days = expected_trading_days(after + pd.Timedelta(days=1), after + pd.Timedelta(days=40))
    if len(days) < n:
        raise LedgerError(f"Kalender liefert keine {n} Handelstage nach {after.date()}")
    return days[:n]


def due_resolutions(
    forecasts: pd.DataFrame,
    resolutions: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    data_versions: dict[str, str],
    commit: str,
    now_utc: str,
) -> list[dict]:
    """Auflösungszeilen für alle fälligen offenen Prognosen (Zieldefinition w1_up_v1).

    Nachtrag-Regel laut docs/zieldefinitionen.md: Fehlt der geplante target_date im
    Kursframe und ist er laut (gepinntem) NYSE-Kalender kein Handelstag, gilt der
    nächste vorhandene Handelstag. Ist er laut Kalender Handelstag, wird abgebrochen —
    Datenlücke oder eine Schließung, die der gepinnte Kalender noch nicht kennt;
    das entscheidet der Projektinhaber, nicht das Skript.
    """
    rows: list[dict] = []
    open_rows = forecasts[~forecasts["forecast_id"].isin(set(resolutions["forecast_id"]))]
    for _, r in open_rows.iterrows():
        if r["target_id"] != TARGET_W1_UP_V1:
            raise LedgerError(f"{r['forecast_id']}: unbekannte target_id {r['target_id']!r}")
        frame = prices.get(r["asset"])
        if frame is None:
            raise LedgerError(f"{r['forecast_id']}: kein Kursframe für Asset {r['asset']!r}")
        dates = frame["date"]
        target = pd.Timestamp(r["target_date"])
        if dates.max() < target:
            continue  # noch nicht fällig
        if (dates == target).any():
            resolution_date = target
        else:
            if len(expected_trading_days(target, target)) > 0:
                raise LedgerError(
                    f"{r['forecast_id']}: {target.date()} ist laut NYSE-Kalender Handelstag, "
                    "fehlt aber im Tiingo-Cache — Datenlücke oder dem Kalender unbekannte "
                    "Schließung. Stoppen und Projektinhaber fragen (kein stilles Ausweichen)."
                )
            later = dates[dates > target]
            if later.empty:
                continue  # Ausweichtag liegt noch in der Zukunft
            resolution_date = later.min()
        anchor = pd.Timestamp(r["anchor_date"])
        anchor_rows = frame.loc[dates == anchor, "close"]
        if len(anchor_rows) != 1:
            raise LedgerError(
                f"{r['forecast_id']}: anchor_date {anchor.date()} nicht eindeutig im Kursframe"
            )
        cached_close = float(anchor_rows.iloc[0])
        stored_close = float(r["anchor_close"])
        if abs(cached_close - stored_close) > 1e-6 * max(1.0, abs(stored_close)):
            raise LedgerError(
                f"{r['forecast_id']}: anchor_close {stored_close} ≠ Cache {cached_close} — "
                "Rohdaten rückwirkend geändert? Stoppen und Projektinhaber fragen."
            )
        # outcome aus dem gespeicherten (auf 6 Stellen gerundeten) Wert, damit die
        # Zeile in sich konsistent bleibt (Validator prüft outcome gegen realized_return).
        tr = round(window_return(frame, anchor, resolution_date), 6)
        rows.append(
            {
                "forecast_id": r["forecast_id"],
                "resolved_utc": now_utc,
                "realized_return": f"{tr:.6f}",
                "outcome": "1" if tr > 0 else "0",
                "resolution_date": resolution_date.date().isoformat(),
                "data_version": data_versions[r["asset"]],
                "code_commit": commit,
            }
        )
    return rows
