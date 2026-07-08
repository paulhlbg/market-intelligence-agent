"""A6-CLI: BTC-Quellenprüfung — Download, Qualitätschecks, Kreuzabgleich, Report.

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a6_btc_quellen download [--sources tiingo_crypto,coinbase]
    uv run python -m mie.a6_btc_quellen probe --source tiingo_crypto|coinbase
                                               [--freeze-fixture PFAD]
    uv run python -m mie.a6_btc_quellen report
    uv run python -m mie.a6_btc_quellen all

Alle Zahlen im generierten Report stammen aus diesem committeten Code (R1).
Netzzugriff passiert nur hier (CLI), nie in Tests. Einordnung/Nutzungsbedingungen:
docs/reports/a6_btc_quellen.md (manuell), Zahlen: docs/reports/a6_btc_kursdaten.md
(generiert). BTC handelt 24/7 — Lücken-Check läuft gegen Kalendertage, nicht
gegen einen Börsenkalender.
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from mie import checks
from mie.crosscheck import crosscheck
from mie.sources import REPO_ROOT, raw_paths, read_meta
from mie.sources import coinbase as src_coinbase
from mie.sources import tiingo_crypto as src_tiingo_crypto

TICKER = "btcusd"
DEFAULT_SOURCES = ["tiingo_crypto", "coinbase"]
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "a6_btc_kursdaten.md"
# Start-Toleranz Kreuzabgleich BTC-Close: 0,5 % relativ — bewusst weiter als bei
# ETFs (0,1 %), weil die Quellen verschiedene Handelsplätze aggregieren bzw. nur
# einen abbilden; endgültige Einordnung nach Befund in docs/reports/a6_btc_quellen.md.
TOLERANCE_BTC_CLOSE = 0.005

_SOURCES = {
    "tiingo_crypto": (src_tiingo_crypto, src_tiingo_crypto.EXT),
    "coinbase": (src_coinbase, src_coinbase.EXT),
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


def cmd_download(sources: list[str]) -> None:
    for source in sources:
        module, _ = _SOURCES[source]
        path, meta = module.download_daily(TICKER)
        print(
            f"{source}/{TICKER}: {meta['rows']} Zeilen → {path.name} "
            f"(sha256 {meta['sha256'][:12]}…)"
        )


def cmd_probe(source: str, freeze_fixture: str | None) -> None:
    """R2-Mini-Check einer BTC-Quelle: 2 Wochen abrufen, Felder zeigen (kein Cache)."""
    start, end = "2026-06-01", "2026-06-15"
    if source == "tiingo_crypto":
        payload, _ = src_tiingo_crypto.fetch_raw(TICKER, start_date=start, end_date=end)
        records = json.loads(payload)
        print(f"Ticker-Objekte: {len(records)}; priceData-Zeilen: {len(records[0]['priceData'])}")
        print(f"Bar-Felder: {sorted(records[0]['priceData'][0].keys())}")
        fixture_obj = [{**records[0], "priceData": records[0]["priceData"][:5]}]
    else:
        payload, params = src_coinbase.fetch_all_candles(start_date=start, end_date=end)
        candles = json.loads(payload)
        print(f"Kerzen: {len(candles)} (Requests: {params['n_requests']})")
        print(f"Kerzenformat [time,low,high,open,close,volume]: {candles[0]}")
        fixture_obj = candles[:5]
    module, _ = _SOURCES[source]
    df = module.parse_bytes(payload)
    print(df.head(3).to_string())
    if freeze_fixture:
        Path(freeze_fixture).write_text(json.dumps(fixture_obj, indent=2) + "\n")
        print(f"Fixture (5 echte Datensätze) eingefroren: {freeze_fixture}")
    print(f"R2-CHECK {source.upper()}: BESTANDEN")


def _load(source: str) -> tuple[pd.DataFrame, dict] | None:
    module, ext = _SOURCES[source]
    raw_path, meta_path = raw_paths(source, TICKER, ext)
    if not raw_path.exists() or not meta_path.exists():
        return None
    return module.parse_cached(raw_path), read_meta(source, TICKER, ext)


def btc_quality(df: pd.DataFrame) -> dict:
    """Qualitätskennzahlen für einen BTC-Tages-Frame (Kalendertage statt Börsenkalender)."""
    calendar_days = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    gaps = checks.check_gaps(df, calendar_days)
    gapfree_start = (gaps.max() + pd.Timedelta(days=1)) if len(gaps) else df["date"].min()
    return {
        "n": len(df),
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
        "duplicates": len(checks.check_duplicates(df)),
        "gaps": len(gaps),
        "gap_days": [d.date().isoformat() for d in gaps[:10]],
        "last_gap": gaps.max().date().isoformat() if len(gaps) else None,
        "gapfree_start": gapfree_start.date().isoformat(),
        "ohlc_violations": len(checks.check_ohlc(df)),
        "nonpositive_close": int((df["close"] <= 0).sum()),
    }


def _check_block(lines: list[str], source: str) -> pd.DataFrame | None:
    loaded = _load(source)
    if loaded is None:
        lines.append(f"### {source}\n\n- **kein Cache vorhanden** (Download ausstehend)\n")
        return None
    df, meta = loaded
    q = btc_quality(df)
    lines.append(f"### {source}\n")
    lines.append(
        f"- n = **{q['n']}** Zeilen · Zeitraum **{q['date_min'].date()} – {q['date_max'].date()}**"
    )
    lines.append(
        f"- Datenversion: sha256 `{meta['sha256'][:16]}…`, abgerufen {meta['retrieved_utc']}"
    )
    lines.append(
        f"- Checks: Duplikate **{q['duplicates']}** · Kalendertag-Lücken **{q['gaps']}** · "
        f"OHLC-Verstöße **{q['ohlc_violations']}** · Close ≤ 0: **{q['nonpositive_close']}**"
    )
    if q["gaps"]:
        lines.append(
            f"- erste Lücken-Tage: {', '.join(q['gap_days'])} · letzter Lücken-Tag: "
            f"**{q['last_gap']}** → lückenfrei ab **{q['gapfree_start']}**"
        )
    else:
        lines.append(f"- lückenfrei ab Reihenbeginn (**{q['gapfree_start']}**)")
    lines.append("")
    return df


def _crosscheck_block(lines: list[str]) -> None:
    a = _load("tiingo_crypto")
    b = _load("coinbase")
    if a is None or b is None:
        lines.append("- übersprungen (mindestens eine Quelle ohne Cache)\n")
        return
    r = crosscheck(a[0], b[0], "tiingo_crypto", "coinbase", TOLERANCE_BTC_CLOSE, columns=("close",))
    lines.append(
        f"- Überlappung n = **{r['n_overlap']}** · nur tiingo_crypto: {r['only_a']} · "
        f"nur coinbase: {r['only_b']}"
    )
    s_all, s_pre, s_post = r["close"]["all"], r["close"]["pre_lockbox"], r["close"]["post_lockbox"]
    lines.append(
        f"- **close** |Δ|rel: Median {_pct(s_all['median'])} · p95 {_pct(s_all['p95'])} · "
        f"Max {_pct(s_all['max'])} · > Toleranz: **{s_all['exceed']}**"
        f" (vor 2025: {s_pre['exceed']}, ab 2025: {s_post['exceed']})"
    )
    if s_all["exceed"]:
        lines.append(
            f"- Überschreitungstage (Stichprobe): {', '.join(r['close']['exceed_days_sample'])} · "
            f"**letzter** Überschreitungstag: **{r['close']['last_exceed_day']}**"
        )
    lines.append("")


def cmd_report() -> None:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    tol_pct = f"{TOLERANCE_BTC_CLOSE * 100:.1f} %"
    lines = [
        "# A6 — Verfügbarkeits- und Qualitätsreport BTC-Tagesdaten",
        "",
        f"**Generiert:** {now} · **Commit:** `{_commit_hash()}` · "
        f"Erzeugt von `uv run python -m mie.a6_btc_quellen report` — nicht von Hand editieren.",
        "",
        "R3-Felder: n, Zeitraum und Datenversion stehen je Quelle unten. "
        "**Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/"
        "Qualitätsreport ohne Effektschätzung. Einordnung und Nutzungsbedingungen: "
        "docs/reports/a6_btc_quellen.md.",
        "",
        "BTC handelt 24/7: Lücken-Check gegen **Kalendertage (UTC)**, kein Börsenkalender. "
        "Die letzte Zeile je Quelle kann der laufende, noch unfertige UTC-Tag sein "
        "(die Ledger-Schicht verwirft ihn; Anker-Regel in docs/zieldefinitionen.md).",
        "",
        "## Quellen\n",
    ]
    for source in DEFAULT_SOURCES:
        _check_block(lines, source)
    lines.append(f"## Kreuzabgleich tiingo_crypto × coinbase (Start-Toleranz close: {tol_pct})\n")
    _crosscheck_block(lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Report geschrieben: {REPORT_PATH.relative_to(REPO_ROOT)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.a6_btc_quellen", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dl = sub.add_parser("download", help="BTC-Rohdaten cachen")
    p_dl.add_argument("--sources", default=",".join(DEFAULT_SOURCES))

    p_probe = sub.add_parser("probe", help="R2-Mini-Check einer BTC-Quelle")
    p_probe.add_argument("--source", choices=sorted(_SOURCES), required=True)
    p_probe.add_argument("--freeze-fixture", default=None)

    sub.add_parser("report", help="Qualitäts-/Kreuzabgleich-Report generieren")

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
