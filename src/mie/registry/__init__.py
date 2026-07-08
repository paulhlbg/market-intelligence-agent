"""Experiment-Registry v0 (A5): Schema, Validierung, Append-only-I/O, Lockbox-Zähler.

Registrieren vor Auswerten (R6, docs/verfassung.md §4). Zwei committete
CSV-Dateien im Repo:
- registry/experimente.csv  — eine Zeile je registriertem Experiment
- registry/auswertungen.csv — eine Zeile je Auswertung; das Ergebnisfeld eines
  Experiments ist leer, solange hier keine Zeile existiert

Der Hypothesen-Volltext liegt in registry/hypothesen/<experiment_id>.md und
wird bei der Registrierung per SHA-256 eingefroren: registriert = eingefroren,
nachträgliche Änderungen fallen im check auf; Präzisierungswunsch = neue
experiment_id. Lockbox-Auswertungen (Daten ab 01.01.2025, CLAUDE.md §3.6) sind
auf maximal 2 begrenzt; der Zähler ist die Anzahl der Auswertungszeilen mit
lockbox=1. Append-only-Kern: mie.appendonly (geteilt mit dem Ledger).
"""

import hashlib
import re
from pathlib import Path

import pandas as pd

from mie import appendonly
from mie.sources import REPO_ROOT

EXPERIMENT_COLUMNS = [
    "experiment_id",
    "registered_utc",
    "typ",
    "titel",
    "assets",
    "datenbasis",
    "fenster_start",
    "fenster_ende",
    "hypothese_datei",
    "hypothese_sha256",
    "code_commit",
]

EVALUATION_COLUMNS = [
    "experiment_id",
    "evaluated_utc",
    "lockbox",
    "ergebnis_kurz",
    "report_datei",
    "data_version",
    "code_commit",
]
REQUIRED_EVALUATION_FIELDS = [c for c in EVALUATION_COLUMNS if c != "report_datei"]

TYPES = {"replikation", "exploration"}  # strikt getrennt geführt (CLAUDE.md §3.7)
LOCKBOX_MAX = 2
LOCKBOX_START = "2025-01-01"

# Schlüssel, die die Frontmatter der Hypothesen-Datei liefert; der Rest der Zeile
# (registered_utc, hypothese_datei, hypothese_sha256, code_commit) entsteht beim Registrieren.
FRONTMATTER_KEYS = [
    "experiment_id",
    "typ",
    "titel",
    "assets",
    "datenbasis",
    "fenster_start",
    "fenster_ende",
]

_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RegistryError(appendonly.AppendOnlyError):
    """Fehler im Registry-Betrieb; führt stets zum Abbruch statt zu stiller Reparatur."""


def experimente_path(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "registry" / "experimente.csv"


def auswertungen_path(repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "registry" / "auswertungen.csv"


def hypothese_path(experiment_id: str, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "registry" / "hypothesen" / f"{experiment_id}.md"


def code_commit(repo_root: Path = REPO_ROOT) -> str:
    """Kurzer Git-Commit-Hash (Pflichtfeld je Zeile; ohne Git kein Registry-Betrieb)."""
    return appendonly.code_commit(repo_root, error_cls=RegistryError)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_experiment_row(row: dict) -> list[str]:
    """Schema-Check einer Experimentzeile; Liste der Probleme (leer = ok)."""
    problems = appendonly.common_problems(row, EXPERIMENT_COLUMNS, EXPERIMENT_COLUMNS)
    if problems:
        return problems
    if not _ID_PATTERN.match(row["experiment_id"]):
        problems.append("experiment_id: nur Kleinbuchstaben/Ziffern/Unterstriche erlaubt")
    if not appendonly.is_iso_datetime(row["registered_utc"]):
        problems.append("registered_utc: kein ISO-Zeitstempel")
    if row["typ"] not in TYPES:
        problems.append(f"typ: muss eines von {sorted(TYPES)} sein")
    for f in ["fenster_start", "fenster_ende"]:
        if not appendonly.is_iso_date(row[f]):
            problems.append(f"{f}: kein ISO-Datum")
    if (
        appendonly.is_iso_date(row["fenster_start"])
        and appendonly.is_iso_date(row["fenster_ende"])
        and row["fenster_ende"] < row["fenster_start"]
    ):
        problems.append("fenster_ende: liegt vor fenster_start")
    expected = f"registry/hypothesen/{row['experiment_id']}.md"
    if row["hypothese_datei"] != expected:
        problems.append(f"hypothese_datei: muss {expected} sein")
    if not _SHA256_PATTERN.match(row["hypothese_sha256"]):
        problems.append("hypothese_sha256: kein SHA-256-Hex-Wert")
    return problems


def validate_evaluation_row(row: dict) -> list[str]:
    """Schema-Check einer Auswertungszeile; Liste der Probleme (leer = ok)."""
    problems = appendonly.common_problems(row, EVALUATION_COLUMNS, REQUIRED_EVALUATION_FIELDS)
    if problems:
        return problems
    if not appendonly.is_iso_datetime(row["evaluated_utc"]):
        problems.append("evaluated_utc: kein ISO-Zeitstempel")
    if row["lockbox"] not in {"0", "1"}:
        problems.append("lockbox: muss 0 oder 1 sein")
    return problems


def load_experiments(repo_root: Path = REPO_ROOT) -> pd.DataFrame:
    """Experimente als String-DataFrame (Interpretation Sache der Aufrufer)."""
    return appendonly.load_csv(
        experimente_path(repo_root), EXPERIMENT_COLUMNS, error_cls=RegistryError
    )


def load_evaluations(repo_root: Path = REPO_ROOT) -> pd.DataFrame:
    """Auswertungen als String-DataFrame."""
    return appendonly.load_csv(
        auswertungen_path(repo_root), EVALUATION_COLUMNS, error_cls=RegistryError
    )


def lockbox_count(evaluations: pd.DataFrame) -> int:
    """Lockbox-Auswertungszähler = Anzahl Auswertungszeilen mit lockbox=1 (global)."""
    return int((evaluations["lockbox"] == "1").sum())


def parse_hypothesis_file(path: Path) -> dict:
    """Frontmatter (`schlüssel: wert` zwischen zwei ---) einer Hypothesen-Datei lesen.

    Bewusst ohne YAML-Abhängigkeit: nur einfache einzeilige Werte.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise RegistryError(f"{path.name}: Frontmatter fehlt (Datei muss mit '---' beginnen)")
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        raise RegistryError(f"{path.name}: Frontmatter nicht geschlossen (zweites '---' fehlt)")
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not value.strip():
            raise RegistryError(f"{path.name}: Frontmatter-Zeile ohne 'schlüssel: wert': {line!r}")
        fields[key.strip()] = value.strip()
    missing = [k for k in FRONTMATTER_KEYS if k not in fields]
    if missing:
        raise RegistryError(f"{path.name}: Frontmatter-Schlüssel fehlen: {', '.join(missing)}")
    unknown = [k for k in fields if k not in FRONTMATTER_KEYS]
    if unknown:
        raise RegistryError(f"{path.name}: unbekannte Frontmatter-Schlüssel: {', '.join(unknown)}")
    return fields


def registration_row(path: Path, now_utc: str, commit: str, repo_root: Path = REPO_ROOT) -> dict:
    """Registrierungszeile aus einer Hypothesen-Datei bauen (friert die Datei per Hash ein)."""
    fields = parse_hypothesis_file(path)
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        raise RegistryError(f"{path}: liegt nicht im Repo ({repo_root})") from None
    expected = f"registry/hypothesen/{fields['experiment_id']}.md"
    if rel != expected:
        raise RegistryError(
            f"{path.name}: Datei muss unter {expected} liegen (Dateiname = experiment_id)"
        )
    return {
        **{k: fields[k] for k in FRONTMATTER_KEYS},
        "registered_utc": now_utc,
        "hypothese_datei": rel,
        "hypothese_sha256": file_sha256(path),
        "code_commit": commit,
    }


def append_experiments(rows: list[dict], repo_root: Path = REPO_ROOT) -> int:
    """Experimentzeilen anhängen; verweigert doppelte IDs und Hash-Abweichungen."""
    existing = set(load_experiments(repo_root)["experiment_id"])
    new_ids = [str(r.get("experiment_id", "")) for r in rows]
    dupes = sorted({i for i in new_ids if i in existing or new_ids.count(i) > 1})
    if dupes:
        raise RegistryError(f"experiment_id bereits vorhanden oder doppelt: {', '.join(dupes)}")
    for row in rows:
        path = repo_root / str(row.get("hypothese_datei", ""))
        if not path.is_file():
            raise RegistryError(
                f"{row.get('experiment_id')}: Hypothesen-Datei fehlt ({row.get('hypothese_datei')})"
            )
        if file_sha256(path) != row.get("hypothese_sha256"):
            raise RegistryError(
                f"{row.get('experiment_id')}: hypothese_sha256 passt nicht zur Datei — "
                "Datei nach dem Hashen verändert? Registrieren verweigert."
            )
    return appendonly.append_rows(
        experimente_path(repo_root),
        EXPERIMENT_COLUMNS,
        rows,
        validate_experiment_row,
        repo_root,
        error_cls=RegistryError,
    )


def append_evaluations(rows: list[dict], repo_root: Path = REPO_ROOT) -> int:
    """Auswertungszeilen anhängen: max. 1 je Experiment, Lockbox-Limit global ≤ 2.

    In A5 nur Mechanik: Auswertungen selbst sind Phase B und einzeln
    freigabepflichtig — die Guards existieren, damit Zähler und Regeln von
    Anfang an erzwungen sind.
    """
    experiments = load_experiments(repo_root).set_index("experiment_id")
    evaluations = load_evaluations(repo_root)
    evaluated = set(evaluations["experiment_id"])
    new_ids = [str(r.get("experiment_id", "")) for r in rows]
    unknown = sorted({i for i in new_ids if i not in experiments.index})
    if unknown:
        raise RegistryError(
            f"Auswertung ohne registriertes Experiment: {', '.join(unknown)} "
            "(R6: registrieren vor auswerten)"
        )
    dupes = sorted({i for i in new_ids if i in evaluated or new_ids.count(i) > 1})
    if dupes:
        raise RegistryError(
            "bereits ausgewertet oder doppelt (Re-Auswertung = neuer Registry-Eintrag): "
            f"{', '.join(dupes)}"
        )
    for row in rows:
        fenster_ende = str(experiments.loc[row["experiment_id"], "fenster_ende"])
        if fenster_ende >= LOCKBOX_START and str(row.get("lockbox", "")) != "1":
            raise RegistryError(
                f"{row['experiment_id']}: fenster_ende {fenster_ende} reicht in den "
                f"Lockbox-Zeitraum (ab {LOCKBOX_START}) — Auswertung nur als "
                "Lockbox-Auswertung (lockbox=1) zulässig."
            )
    n_lockbox = lockbox_count(evaluations) + sum(
        1 for r in rows if str(r.get("lockbox", "")) == "1"
    )
    if n_lockbox > LOCKBOX_MAX:
        raise RegistryError(
            f"Lockbox-Auswertungszähler würde {n_lockbox} erreichen "
            f"(Maximum {LOCKBOX_MAX}, CLAUDE.md §3.6) — verweigert."
        )
    return appendonly.append_rows(
        auswertungen_path(repo_root),
        EVALUATION_COLUMNS,
        rows,
        validate_evaluation_row,
        repo_root,
        error_cls=RegistryError,
    )


def check_registry(repo_root: Path = REPO_ROOT) -> list[str]:
    """Konsistenz der Registry prüfen; Liste der Probleme (leer = ok).

    Prüft Schema aller Zeilen, Existenz und Hash der Hypothesen-Dateien
    (registriert = eingefroren), referentielle Integrität der Auswertungen
    und das Lockbox-Limit.
    """
    problems: list[str] = []
    experiments = load_experiments(repo_root)
    evaluations = load_evaluations(repo_root)
    ids = list(experiments["experiment_id"])
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"experiment_id doppelt: {', '.join(dupes)}")
    for _, row in experiments.iterrows():
        problems += [f"{row['experiment_id']}: {p}" for p in validate_experiment_row(dict(row))]
        path = repo_root / row["hypothese_datei"]
        if not path.is_file():
            problems.append(
                f"{row['experiment_id']}: Hypothesen-Datei fehlt ({row['hypothese_datei']})"
            )
        elif file_sha256(path) != row["hypothese_sha256"]:
            problems.append(
                f"{row['experiment_id']}: Hypothesen-Datei nachträglich verändert "
                "(Hash weicht von hypothese_sha256 ab — registriert = eingefroren)"
            )
    eval_ids = list(evaluations["experiment_id"])
    unknown = sorted(set(eval_ids) - set(ids))
    if unknown:
        problems.append(f"Auswertung ohne registriertes Experiment: {', '.join(unknown)}")
    eval_dupes = sorted({i for i in eval_ids if eval_ids.count(i) > 1})
    if eval_dupes:
        problems.append(f"mehrfach ausgewertet: {', '.join(eval_dupes)}")
    for _, row in evaluations.iterrows():
        problems += [f"{row['experiment_id']}: {p}" for p in validate_evaluation_row(dict(row))]
    if lockbox_count(evaluations) > LOCKBOX_MAX:
        problems.append(
            f"Lockbox-Auswertungen: {lockbox_count(evaluations)} > Maximum {LOCKBOX_MAX}"
        )
    return problems
