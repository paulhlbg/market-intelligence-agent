"""A5-CLI: Experiment-Registry (registrieren, Status, Konsistenz-Check).

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a5_registry register registry/hypothesen/<id>.md [--dry-run]
    uv run python -m mie.a5_registry status
    uv run python -m mie.a5_registry check

register liest die Frontmatter der Hypothesen-Datei, friert die Datei per
SHA-256 ein und hängt eine Zeile an registry/experimente.csv an (append-only).
Registrieren heißt NICHT auswerten: Auswertungen sind Phase B und einzeln
freigabepflichtig (R6: registrieren vor auswerten). Alles offline, kein
Netzzugriff.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from mie import registry


def cmd_register(file: str, dry_run: bool) -> int:
    now_utc = datetime.now(UTC).isoformat(timespec="seconds")
    row = registry.registration_row(Path(file), now_utc=now_utc, commit=registry.code_commit())
    print(f"{row['experiment_id']} [{row['typ']}]: {row['titel']}")
    print(
        f"  Assets {row['assets']} · Fenster {row['fenster_start']} – {row['fenster_ende']} · "
        f"Datenbasis {row['datenbasis']}"
    )
    print(
        f"  Hypothese {row['hypothese_datei']} (sha256 {row['hypothese_sha256'][:12]}…) · "
        f"Commit {row['code_commit']}"
    )
    if dry_run:
        print("DRY-RUN: nichts geschrieben.")
        return 0
    registry.append_experiments([row])
    print(
        "Registriert — Hypothesen-Datei ist damit eingefroren (Hash-Pinning); "
        "Ergebnisfeld bleibt leer bis zur (einzeln freigabepflichtigen) Auswertung. "
        "Jetzt: `make check`, committen."
    )
    return 0


def cmd_status() -> int:
    experiments = registry.load_experiments()
    evaluations = registry.load_evaluations()
    by_id = evaluations.set_index("experiment_id")
    print(f"Experimente: {len(experiments)} · ausgewertet: {len(evaluations)}")
    for _, r in experiments.iterrows():
        if r["experiment_id"] in by_id.index:
            e = by_id.loc[r["experiment_id"]]
            ergebnis = (
                f"Ergebnis: {e['ergebnis_kurz']} "
                f"(ausgewertet {e['evaluated_utc']}, lockbox={e['lockbox']})"
            )
        else:
            ergebnis = "Ergebnis: (leer — noch nicht ausgewertet)"
        print(f"  {r['experiment_id']} [{r['typ']}] {r['titel']}")
        print(
            f"    Fenster {r['fenster_start']} – {r['fenster_ende']} · "
            f"registriert {r['registered_utc']} · {ergebnis}"
        )
    print(f"Lockbox-Auswertungen: {registry.lockbox_count(evaluations)} von {registry.LOCKBOX_MAX}")
    return 0


def cmd_check() -> int:
    problems = registry.check_registry()
    if problems:
        print("Registry-Check FEHLGESCHLAGEN:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Registry-Check ok (Schema, Hypothesen-Hashes, Referenzen, Lockbox-Limit).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.a5_registry", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_register = sub.add_parser(
        "register", help="Experiment aus Hypothesen-Datei registrieren (nicht auswerten)"
    )
    p_register.add_argument("file", help="Pfad zur Hypothesen-Datei (registry/hypothesen/<id>.md)")
    p_register.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")

    sub.add_parser("status", help="alle Experimente + Lockbox-Zähler anzeigen")
    sub.add_parser("check", help="Schema, Hypothesen-Hashes, Referenzen, Lockbox-Limit prüfen")

    args = parser.parse_args(argv)
    if args.cmd == "register":
        return cmd_register(args.file, dry_run=args.dry_run)
    if args.cmd == "status":
        return cmd_status()
    return cmd_check()


if __name__ == "__main__":
    sys.exit(main())
