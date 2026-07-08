"""A3-CLI: Download, Qualitätschecks, Kreuzabgleich und Report für Terminlisten.

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a3_termine download [--sources fed,bls,fred]
    uv run python -m mie.a3_termine probe --source fed|bls|fred [--freeze-fixture PFAD]
    uv run python -m mie.a3_termine report
    uv run python -m mie.a3_termine all

Alle Zahlen im generierten Report stammen aus diesem committeten Code (R1).
Netzzugriff passiert nur hier (CLI), nie in Tests. Der Report geht nach
docs/reports/a3_termine.md; zusätzlich werden die verarbeiteten Terminlisten
als CSV nach data/processed/ geschrieben (gemeinfreie US-Regierungsdaten,
werden committet — Beschluss im A3-Plan vom 08.07.2026).
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from mie.events import checks, validate_events_frame
from mie.events import cpi_bls as src_bls
from mie.events import cpi_fred as src_fred
from mie.events import fomc_fed as src_fed
from mie.sources import REPO_ROOT

DEFAULT_SOURCES = ["fed", "bls", "fred"]
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "a3_termine.md"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

_MODULES = {"fed": src_fed, "bls": src_bls, "fred": src_fred}

FOMC_CSV_COLUMNS = [
    "event_type",
    "date",
    "meeting_start",
    "meeting_type",
    "scheduled",
    "sep",
    "statement_date",
    "source",
]
CPI_CSV_COLUMNS = ["event_type", "date", "ref_month", "time_et", "scheduled", "source"]


def _commit_hash() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unbekannt"


def _combined_version(metas: list[dict]) -> str:
    """Datenversion über mehrere Rohdateien: SHA-256 der sortierten Einzel-Hashes."""
    joined = "\n".join(sorted(m["sha256"] for m in metas))
    return hashlib.sha256(joined.encode()).hexdigest()


def cmd_download(sources: list[str]) -> None:
    for source in sources:
        try:
            results = _MODULES[source].download_all()
        except RuntimeError as exc:  # z. B. fehlender FRED_API_KEY
            print(f"{source}: ÜBERSPRUNGEN — {exc}")
            continue
        for path, meta in results:
            print(f"{source}/{path.name}: {meta['rows']} Termine (sha256 {meta['sha256'][:12]}…)")


def cmd_probe(source: str, freeze_fixture: str | None) -> None:
    """R2-Mini-Check einer Quelle: kleiner Live-Abruf, Felder und Umfang zeigen."""
    if source == "fed":
        payload = src_fed.fetch_page("fomchistorical2020.htm")
        df = src_fed.parse_historical(payload.decode("utf-8", errors="replace"), 2020)
        print(f"Termine 2020: {len(df)}")
        print(df[["date", "meeting_type", "scheduled", "statement_date"]].to_string())
    elif source == "bls":
        payload = src_bls.fetch_page(src_bls.SCHEDULE_URL)
        df = src_bls.parse_schedule(payload.decode("utf-8", errors="replace"))
        print(f"Geplante Releases: {len(df)}")
        print(df.head(3).to_string())
    else:
        info = src_fred.fetch_release_info()
        print(f"Release {src_fred.RELEASE_ID}: {info.get('name')!r}")
        payload, _ = src_fred.fetch_raw()
        df = src_fred.parse_bytes(payload)
        print(f"Release-Termine: {len(df)}, {df['date'].min().date()} – {df['date'].max().date()}")
        if freeze_fixture:
            data = json.loads(payload)
            data["release_dates"] = data["release_dates"][:5]
            Path(freeze_fixture).write_text(json.dumps(data, indent=2) + "\n")
            print(f"Fixture (5 echte Datensätze) eingefroren: {freeze_fixture}")
    print(f"R2-CHECK {source.upper()}: BESTANDEN")


def _load_all() -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """(FOMC/fed, CPI/bls, CPI/fred) aus dem Cache; None, wenn Cache fehlt."""
    try:
        fomc = src_fed.load_events()
    except FileNotFoundError:
        fomc = None
    try:
        cpi = src_bls.load_events()
    except FileNotFoundError:
        cpi = None
    return fomc, cpi, src_fred.load_events()


def _meta_lines(lines: list[str], source: str, names_ext: list[tuple[str, str]]) -> None:
    from mie.sources import read_cache_meta

    metas = [read_cache_meta(source, name, ext) for name, ext in names_ext]
    retrieved = sorted(m["retrieved_utc"] for m in metas)
    lines.append(
        f"- Datenversion: {len(metas)} Rohdatei(en), kombiniert sha256 "
        f"`{_combined_version(metas)[:16]}…`, abgerufen {retrieved[0]} – {retrieved[-1]}"
    )


def _fomc_block(lines: list[str], df: pd.DataFrame, today: pd.Timestamp) -> None:
    problems = validate_events_frame(df)
    c = checks.run_all(df, today)
    lines.append("## FOMC (Quelle „fed“)\n")
    lines.append(
        f"- n = **{c['n']}** Termine (davon {c['n_past']} bis heute) · Zeitraum "
        f"**{c['date_min'].date()} – {c['date_max'].date()}** (inkl. angekündigter Sitzungen)"
    )
    _meta_lines(
        lines,
        "fed",
        [("fomccalendars", "html")]
        + [
            (f"fomchistorical{y}", "html")
            for y in range(src_fed.FIRST_YEAR, src_fed.LAST_HIST_YEAR + 1)
        ],
    )
    lines.append(f"- Schema-Validierung: {'**' + '; '.join(problems) + '**' if problems else 'ok'}")
    lines.append(
        f"- Checks: Duplikate **{c['duplicates']}** · Wochenend-Termine **{c['weekend']}** · "
        f"an NYSE-Feiertagen **{c['non_trading']}**"
        + (f" ({', '.join(c['non_trading_days'])})" if c["non_trading"] else "")
    )
    types = df["meeting_type"].value_counts()
    lines.append("- Terminarten: " + " · ".join(f"{t} **{n}**" for t, n in types.items()))
    dev = checks.fomc_scheduled_deviations(df, today)
    dev_text = (
        ", ".join(f"{y}: {n}" for y, n in dev["deviations"].items())
        if dev["deviations"]
        else "keine"
    )
    lines.append(
        f"- Reguläre Sitzungen je abgeschlossenem Jahr (Soll 8, {dev['years']} Jahre): "
        f"Abweichungen: **{dev_text}**"
    )
    x = checks.fomc_statement_crosscheck(df, today)
    lines.append(
        f"- Kreuzabgleich Kalender × Pressemitteilungs-Links (reguläre Sitzungen ab "
        f"Mai 1999, n = {x['n_routine']}): Statement am Entscheidungstag **{x['n_match']}** · "
        f"fehlend **{x['n_missing']}**"
        + (f" ({', '.join(x['missing_days'])})" if x["n_missing"] else "")
        + f" · abweichend **{x['n_mismatch']}**"
        + (f" ({', '.join(x['mismatch_days'])})" if x["n_mismatch"] else "")
    )
    lines.append(
        f"- Vor Mai 1999 (Statement nur bei Zinsänderung üblich): {x['n_early']} reguläre "
        f"Sitzungen, davon {x['n_early_with_statement']} mit Statement am Entscheidungstag"
    )
    lines.append("")


def _cpi_block(lines: list[str], df: pd.DataFrame, today: pd.Timestamp) -> None:
    problems = validate_events_frame(df)
    c = checks.run_all(df, today, gap_max_days=45)
    lines.append("## CPI (Quelle „bls“)\n")
    lines.append(
        f"- n = **{c['n']}** Termine (davon {c['n_past']} bis heute) · Zeitraum "
        f"**{c['date_min'].date()} – {c['date_max'].date()}** (inkl. angekündigter Termine)"
    )
    _meta_lines(lines, "bls", [("cpi_schedule", "html"), ("cpi_archive", "html")])
    lines.append(f"- Schema-Validierung: {'**' + '; '.join(problems) + '**' if problems else 'ok'}")
    lines.append(
        f"- Checks: Duplikate **{c['duplicates']}** · Wochenend-Termine **{c['weekend']}** · "
        f"an NYSE-Feiertagen **{c['non_trading']}**"
        + (f" ({', '.join(c['non_trading_days'])})" if c["non_trading"] else "")
    )
    lines.append(
        f"- Lücken > 45 Tage zwischen Releases: **{c['gaps']}**"
        + (f" — {'; '.join(c['gap_list'])}" if c["gaps"] else "")
    )
    times = df.loc[df["time_et"].notna(), "time_et"].value_counts()
    time_text = " · ".join(f"{t} ET × {n}" for t, n in times.items()) if len(times) else "keine"
    lines.append(
        f"- Uhrzeiten laut Terminplan-Seite (nur kommende Termine): {time_text}; "
        f"das Release-Archiv nennt keine Uhrzeiten"
    )
    lines.append("")


def _crosscheck_block(lines: list[str], cpi_bls_df, cpi_fred_df, today: pd.Timestamp) -> None:
    lines.append("## Kreuzabgleich CPI: bls × fred\n")
    if cpi_fred_df is None:
        lines.append(
            "- **übersprungen** — kein FRED-Cache vorhanden (FRED_API_KEY fehlt, "
            "Stand der Report-Generierung). Nachholen: Key setzen, dann "
            "`uv run python -m mie.a3_termine all`.\n"
        )
        return
    past = cpi_bls_df[cpi_bls_df["date"] <= today]
    r = checks.crosscheck_dates(past, cpi_fred_df, "bls", "fred")
    lines.append(
        f"- Überlappung **{r['start'].date()} – {r['end'].date()}**: "
        f"übereinstimmend **{r['n_match']}** · nur bls **{r['n_only_bls']}** · "
        f"nur fred **{r['n_only_fred']}**"
    )
    if r["n_only_bls"]:
        lines.append(f"  - nur bls: {', '.join(r['only_bls'])}")
    if r["n_only_fred"]:
        lines.append(f"  - nur fred: {', '.join(r['only_fred'])}")
    lines.append("")


def _write_csv(df: pd.DataFrame, columns: list[str], path: Path) -> None:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.date
    out[columns].to_csv(path, index=False)


def cmd_report() -> None:
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    fomc, cpi, cpi_fred_df = _load_all()
    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "# A3 — Verfügbarkeits- und Qualitätsreport Termine (FOMC, CPI)",
        "",
        f"**Generiert:** {now} · **Commit:** `{_commit_hash()}` · "
        f"Erzeugt von `uv run python -m mie.a3_termine report` — nicht von Hand editieren.",
        "",
        "R3-Felder: n, Zeitraum und Datenversion stehen je Quelle unten. "
        "**Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/"
        "Qualitätsreport ohne Effektschätzung; kein Kursbezug.",
        "",
        "Ereignisdatum FOMC = letzter Sitzungstag (Bekanntgabetag); CPI = Release-Tag. "
        "Uhrzeiten sind ET (America/New_York); UTC-Ableitung DST-korrekt via zoneinfo — "
        "14:00 ET ist je nach Datum 19:00 (Winter) oder 18:00 (Sommer) UTC. "
        "Zur Deckung: FOMC ab 1994 (erstes Fed-Statement Feb. 1994, davor kein "
        "definierter Bekanntgabezeitpunkt); CPI-Archivtiefe siehe unten.",
        "",
    ]
    if fomc is None:
        lines.append("## FOMC (Quelle „fed“)\n\n- **kein Cache vorhanden** (Download ausstehend)\n")
    else:
        _fomc_block(lines, fomc, today)
    if cpi is None:
        lines.append("## CPI (Quelle „bls“)\n\n- **kein Cache vorhanden** (Download ausstehend)\n")
    else:
        _cpi_block(lines, cpi, today)
    if cpi is not None:
        _crosscheck_block(lines, cpi, cpi_fred_df, today)
    if fomc is not None and cpi is not None:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        _write_csv(fomc, FOMC_CSV_COLUMNS, PROCESSED_DIR / "fomc_termine.csv")
        _write_csv(cpi, CPI_CSV_COLUMNS, PROCESSED_DIR / "cpi_termine.csv")
        lines.append("## Verarbeitete Terminlisten\n")
        lines.append(
            f"- `data/processed/fomc_termine.csv` ({len(fomc)} Zeilen) und "
            f"`data/processed/cpi_termine.csv` ({len(cpi)} Zeilen); Spalten siehe "
            "Modul-Doku. Gemeinfreie US-Regierungsdaten, werden committet.\n"
        )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Report geschrieben: {REPORT_PATH.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.a3_termine", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dl = sub.add_parser("download", help="Rohdaten cachen")
    p_dl.add_argument("--sources", default=",".join(DEFAULT_SOURCES))

    p_probe = sub.add_parser("probe", help="R2-Mini-Check einer Quelle")
    p_probe.add_argument("--source", choices=list(_MODULES), required=True)
    p_probe.add_argument("--freeze-fixture", default=None)

    sub.add_parser("report", help="Qualitäts-/Kreuzabgleich-Report + CSV-Export")

    p_all = sub.add_parser("all", help="download + report")
    p_all.add_argument("--sources", default=",".join(DEFAULT_SOURCES))

    args = parser.parse_args(argv)
    if args.cmd == "download":
        cmd_download(args.sources.split(","))
    elif args.cmd == "probe":
        cmd_probe(args.source, args.freeze_fixture)
    elif args.cmd == "report":
        cmd_report()
    elif args.cmd == "all":
        cmd_download(args.sources.split(","))
        cmd_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
