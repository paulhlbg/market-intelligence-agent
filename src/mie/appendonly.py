"""Generischer Append-only-CSV-Kern (in A4 gebaut, seit A5 geteilt).

Gemeinsame Grundlage für Ledger (ledger/*.csv) und Registry (registry/*.csv).
Alte Zeilen werden nie verändert. Der Wächter prüft vor jedem Schreiben, dass
der aktuelle Dateiinhalt byteweise mit dem zuletzt committeten Stand (git HEAD)
beginnt — veränderte oder gelöschte alte Zeilen führen zur Verweigerung.
Werte müssen zeilen-diffbar bleiben (kein CSV-Quoting): keine Kommas,
Anführungszeichen oder Zeilenumbrüche in Feldern.
"""

import subprocess
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from mie.sources import REPO_ROOT

FORBIDDEN_CHARS = set(',"\n\r')


class AppendOnlyError(RuntimeError):
    """Fehler im Append-only-Betrieb; führt stets zum Abbruch statt zu stiller Reparatur."""


def code_commit(
    repo_root: Path = REPO_ROOT, error_cls: type[AppendOnlyError] = AppendOnlyError
) -> str:
    """Kurzer Git-Commit-Hash (Pflichtfeld je Zeile; ohne Git kein Betrieb)."""
    res = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=repo_root
    )
    if res.returncode != 0:
        raise error_cls("git rev-parse fehlgeschlagen — code_commit ist Pflichtfeld je Zeile")
    return res.stdout.strip()


def _head_bytes(path: Path, repo_root: Path) -> bytes | None:
    """Inhalt der Datei im letzten Commit; None, wenn dort (noch) nicht vorhanden."""
    rel = path.relative_to(repo_root).as_posix()
    res = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True, cwd=repo_root)
    return res.stdout if res.returncode == 0 else None


def ensure_append_only(
    path: Path, repo_root: Path = REPO_ROOT, error_cls: type[AppendOnlyError] = AppendOnlyError
) -> None:
    """Wächter: aktueller Inhalt muss byteweise mit dem committeten Stand beginnen."""
    head = _head_bytes(path, repo_root)
    if head is None:
        return  # Datei noch nie committet — nichts zu schützen
    if not path.read_bytes().startswith(head):
        raise error_cls(
            f"Append-only verletzt: {path.name} weicht vom committeten Stand ab "
            "(alte Zeilen verändert oder gelöscht?). Schreiben verweigert — "
            "Arbeitskopie prüfen (git diff), nichts still reparieren."
        )


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def common_problems(row: dict, columns: list[str], required: list[str]) -> list[str]:
    """Feld-, Pflichtfeld- und Zeichenprüfung, die für jedes Zeilenschema gilt."""
    problems = [f"unbekanntes Feld: {k}" for k in row if k not in columns]
    problems += [f"{f}: Pflichtfeld fehlt oder leer" for f in required if not str(row.get(f, ""))]
    problems += [
        f"{k}: unzulässige Zeichen (Komma/Anführungszeichen/Zeilenumbruch)"
        for k, v in row.items()
        if FORBIDDEN_CHARS & set(str(v))
    ]
    return problems


def load_csv(
    path: Path, columns: list[str], error_cls: type[AppendOnlyError] = AppendOnlyError
) -> pd.DataFrame:
    """CSV als String-DataFrame laden (Interpretation Sache der Aufrufer)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(df.columns) != columns:
        raise error_cls(f"{path.name}: Spalten passen nicht zum Schema ({list(df.columns)})")
    return df


def append_rows(
    path: Path,
    columns: list[str],
    rows: list[dict],
    validate: Callable[[dict], list[str]],
    repo_root: Path = REPO_ROOT,
    error_cls: type[AppendOnlyError] = AppendOnlyError,
) -> int:
    """Zeilen validieren und anhängen; schreibt nur nach bestandenem Wächter-Check."""
    if not rows:
        return 0
    if not path.exists():
        raise error_cls(f"Append-only-Datei fehlt: {path}")
    content = path.read_bytes()
    header = content.split(b"\n", 1)[0].decode("utf-8")
    if header != ",".join(columns):
        raise error_cls(f"{path.name}: Header passt nicht zum Schema")
    if not content.endswith(b"\n"):
        raise error_cls(f"{path.name}: endet nicht mit Zeilenumbruch (manuell verändert?)")
    ensure_append_only(path, repo_root, error_cls)
    problems = []
    for i, row in enumerate(rows):
        problems += [f"Zeile {i + 1}: {p}" for p in validate(row)]
    if problems:
        raise error_cls("Validierung fehlgeschlagen:\n- " + "\n- ".join(problems))
    lines = "".join(",".join(str(row.get(c, "")) for c in columns) + "\n" for row in rows)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(lines)
    return len(rows)
