"""A2-CLI: Download, Qualitätschecks, Kreuzabgleich und Report-Generierung.

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a2_kursdaten download [--tickers SPY,VOO,QQQ] [--sources yahoo,tiingo]
    uv run python -m mie.a2_kursdaten probe --source tiingo [--freeze-fixture PFAD]
    uv run python -m mie.a2_kursdaten report [--tickers SPY,VOO,QQQ]
    uv run python -m mie.a2_kursdaten all

Alle Zahlen im generierten Report stammen aus diesem committeten Code (R1).
Netzzugriff passiert nur hier (CLI), nie in Tests.
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from mie import checks
from mie.crosscheck import TOLERANCE_RAW_CLOSE, crosscheck
from mie.sources import REPO_ROOT, raw_paths, read_meta
from mie.sources import tiingo as src_tiingo
from mie.sources import yahoo as src_yahoo

DEFAULT_TICKERS = ["SPY", "VOO", "QQQ"]
DEFAULT_SOURCES = ["yahoo", "tiingo"]
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "a2_kursdaten.md"

_SOURCES = {
    "yahoo": (src_yahoo, src_yahoo.EXT),
    "tiingo": (src_tiingo, src_tiingo.EXT),
}


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


def _pct(x: float | None) -> str:
    return "n. a." if x is None else f"{x * 100:.4f} %"


def cmd_download(tickers: list[str], sources: list[str]) -> None:
    for source in sources:
        module, _ = _SOURCES[source]
        for ticker in tickers:
            path, meta = module.download_daily(ticker)
            print(
                f"{source}/{ticker}: {meta['rows']} Zeilen → {path.name} "
                f"(sha256 {meta['sha256'][:12]}…)"
            )


def cmd_probe_tiingo(freeze_fixture: str | None) -> None:
    """R2-Mini-Check Tiingo: 1 Monat SPY, Felder und Umfang zeigen (kein Cache)."""
    payload, _ = src_tiingo.fetch_raw("SPY", start_date="2024-11-01", end_date="2024-11-30")
    records = json.loads(payload)
    print(f"Datensätze: {len(records)}")
    print(f"Felder: {sorted(records[0].keys())}")
    df = src_tiingo.parse_bytes(payload)
    print(df.head(3).to_string())
    if freeze_fixture:
        fixture = json.dumps(records[:5], indent=2) + "\n"
        Path(freeze_fixture).write_text(fixture)
        print(f"Fixture (5 echte Datensätze) eingefroren: {freeze_fixture}")
    print("R2-CHECK TIINGO: BESTANDEN")


def _load(source: str, ticker: str) -> tuple[pd.DataFrame, dict] | None:
    module, ext = _SOURCES[source]
    raw_path, meta_path = raw_paths(source, ticker, ext)
    if not raw_path.exists() or not meta_path.exists():
        return None
    return module.parse_cached(raw_path), read_meta(source, ticker, ext)


def _check_block(lines: list[str], source: str, ticker: str) -> pd.DataFrame | None:
    loaded = _load(source, ticker)
    if loaded is None:
        lines.append(f"### {ticker}\n\n- **kein Cache vorhanden** (Download ausstehend)\n")
        return None
    df, meta = loaded
    c = checks.run_all(df)
    lines.append(f"### {ticker}\n")
    lines.append(
        f"- n = **{c['n']}** Zeilen · Zeitraum **{c['date_min'].date()} – {c['date_max'].date()}**"
    )
    lines.append(
        f"- Datenversion: sha256 `{meta['sha256'][:16]}…`, abgerufen {meta['retrieved_utc']}"
    )
    lines.append(
        f"- Checks: Duplikate **{c['duplicates']}** · Lücken **{c['gaps']}** · "
        f"Zusatztage **{c['extra_days']}** · OHLC-Verstöße **{c['ohlc_violations']}** · "
        f"Preis ≤ 0: **{c['nonpositive']}** · Volumen = 0: **{c['zero_volume']}**"
    )
    if c["gap_days"]:
        lines.append(f"- erste Lücken-Tage: {', '.join(c['gap_days'])}")
    if c["extra_day_list"]:
        lines.append(f"- erste Zusatztage: {', '.join(c['extra_day_list'])}")
    if "div_cash" in df.columns:
        n_div = int((df["div_cash"] > 0).sum())
        n_split = int((df["split_factor"] != 1).sum())
        last_div = df.loc[df["div_cash"] > 0, "date"].max()
        last_div_s = last_div.date().isoformat() if pd.notna(last_div) else "keiner"
        lines.append(
            f"- Adjustierungs-Ereignisse (Tiingo-Felder): Dividenden **{n_div}** "
            f"(letzte: {last_div_s}) · Splits **{n_split}**"
        )
    lines.append("")
    return df


def _crosscheck_block(lines: list[str], ticker: str) -> None:
    a = _load("yahoo", ticker)
    b = _load("tiingo", ticker)
    if a is None or b is None:
        lines.append(f"### {ticker}\n\n- übersprungen (mindestens eine Quelle ohne Cache)\n")
        return
    r = crosscheck(a[0], b[0], "yahoo", "tiingo")
    lines.append(f"### {ticker}\n")
    lines.append(
        f"- Überlappung n = **{r['n_overlap']}** · nur yahoo: {r['only_a']} · "
        f"nur tiingo: {r['only_b']}"
    )
    for col in ("close", "adj_close"):
        s_all, s_pre, s_post = r[col]["all"], r[col]["pre_lockbox"], r[col]["post_lockbox"]
        lines.append(
            f"- **{col}** |Δ|rel: Median {_pct(s_all['median'])} · "
            f"p95 {_pct(s_all['p95'])} · Max {_pct(s_all['max'])} · "
            f"> Toleranz: **{s_all['exceed']}**"
            f" (vor 2025: {s_pre['exceed']}, ab 2025: {s_post['exceed']})"
        )
    lines.append("")


def cmd_report(tickers: list[str]) -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "# A2 — Verfügbarkeits- und Qualitätsreport Kursdaten",
        "",
        f"**Generiert:** {now} · **Commit:** `{_commit_hash()}` · "
        f"Erzeugt von `uv run python -m mie.a2_kursdaten report` — nicht von Hand editieren.",
        "",
        "R3-Felder: n, Zeitraum und Datenversion stehen je Quelle/Ticker unten. "
        "**Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/"
        "Qualitätsreport ohne Effektschätzung.",
        "",
        "Qualitätschecks laufen über den vollen Zeitraum inkl. Lockbox "
        "(Beschluss 07.07.2026); Kreuzabgleich-Überschreitungen werden zusätzlich "
        "getrennt vor/ab 01.01.2025 ausgewiesen. Keine Rendite-/Musteranalyse.",
        "",
    ]
    for source in DEFAULT_SOURCES:
        lines.append(f"## Quelle „{source}“\n")
        for ticker in tickers:
            _check_block(lines, source, ticker)
    tol_pct = f"{TOLERANCE_RAW_CLOSE * 100:.1f} %"
    lines.append(f"## Kreuzabgleich yahoo × tiingo (Start-Toleranz raw close: {tol_pct})\n")
    for ticker in tickers:
        _crosscheck_block(lines, ticker)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Report geschrieben: {REPORT_PATH.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.a2_kursdaten", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dl = sub.add_parser("download", help="Rohdaten cachen")
    p_dl.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    p_dl.add_argument("--sources", default=",".join(DEFAULT_SOURCES))

    p_probe = sub.add_parser("probe", help="R2-Mini-Check einer Quelle")
    p_probe.add_argument("--source", choices=["tiingo"], required=True)
    p_probe.add_argument("--freeze-fixture", default=None)

    p_rep = sub.add_parser("report", help="Qualitäts-/Kreuzabgleich-Report generieren")
    p_rep.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))

    p_all = sub.add_parser("all", help="download + report")
    p_all.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    p_all.add_argument("--sources", default=",".join(DEFAULT_SOURCES))

    args = parser.parse_args(argv)
    if args.cmd == "download":
        cmd_download(args.tickers.split(","), args.sources.split(","))
    elif args.cmd == "probe":
        cmd_probe_tiingo(args.freeze_fixture)
    elif args.cmd == "report":
        cmd_report(args.tickers.split(","))
    elif args.cmd == "all":
        cmd_download(args.tickers.split(","), args.sources.split(","))
        cmd_report(args.tickers.split(","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
