"""A4-CLI: wöchentliche Ledger-Routine (Prognosen + Auflösungen) und Status.

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a4_ledger weekly [--dry-run] [--no-refresh]
    uv run python -m mie.a4_ledger status

weekly: (1) Tiingo-Cache SPY+QQQ auffrischen (2 Requests), (2) fällige Prognosen
auflösen, (3) je Asset eine 1-Wochen-Prognose (klimatologie_v0, Ziel w1_up_v1)
anhängen. Alle ausgegebenen Wahrscheinlichkeiten sind Modelloutputs
(Klimatologie-Basisrate) — keine Anlageempfehlung. Netzzugriff passiert nur
hier (CLI), nie in Tests. Danach: Ausgabe gegenlesen, `make check`, committen
(docs/routinen.md).
"""

import argparse
import sys
from datetime import UTC, datetime

import pandas as pd

from mie import ledger
from mie.checks import check_duplicates
from mie.ledger.klimatologie import HORIZON_TRADING_DAYS, base_rate
from mie.sources import raw_paths, read_meta, tiingo, validate_standard_frame

ASSETS = ["SPY", "QQQ"]  # Festlegung Projektinhaber 08.07.2026 (CLAUDE.md §3.1)
HORIZON_LABEL = "w1_5td"
MODEL_ID = "klimatologie_v0"


def _refresh() -> None:
    for ticker in ASSETS:
        try:
            _, meta = tiingo.download_daily(ticker)
        except OSError as exc:
            raise SystemExit(
                f"Tiingo nicht erreichbar ({exc}) — Lauf später wiederholen; "
                "kein stiller Quellenwechsel (docs/zieldefinitionen.md)."
            ) from exc
        print(f"tiingo/{ticker}: {meta['rows']} Zeilen (sha256 {meta['sha256'][:12]}…)")


def _load_prices() -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Kursframes + Datenversion (sha256 der Rohdatei) je Asset; bricht bei Schadbefund ab."""
    frames: dict[str, pd.DataFrame] = {}
    versions: dict[str, str] = {}
    for ticker in ASSETS:
        raw_path, _ = raw_paths(tiingo.SOURCE, ticker, tiingo.EXT)
        if not raw_path.exists():
            raise SystemExit(
                f"Kein Tiingo-Cache für {ticker} — weekly ohne --no-refresh laufen "
                "lassen (TIINGO_API_KEY nötig)."
            )
        frame = tiingo.parse_cached(raw_path)
        problems = validate_standard_frame(frame)
        if len(check_duplicates(frame)):
            problems.append("doppelte Datumszeilen")
        if problems:
            raise SystemExit(f"{ticker}: Kursframe fehlerhaft — {'; '.join(problems)}")
        frames[ticker] = frame
        versions[ticker] = read_meta(tiingo.SOURCE, ticker, tiingo.EXT)["sha256"]
    return frames, versions


def _new_forecast_rows(
    frames: dict[str, pd.DataFrame],
    versions: dict[str, str],
    existing_ids: set[str],
    commit: str,
    now_utc: str,
) -> list[dict]:
    rows = []
    for ticker in ASSETS:
        frame = frames[ticker]
        anchor_date = frame["date"].iloc[-1]
        forecast_id = f"{anchor_date.date()}_{ticker.lower()}_w1"
        if forecast_id in existing_ids:
            print(f"{forecast_id}: bereits registriert (Anker unverändert) — übersprungen")
            continue
        target_date = ledger.next_trading_days(anchor_date, HORIZON_TRADING_DAYS)[-1]
        stats = base_rate(frame)
        rows.append(
            {
                "forecast_id": forecast_id,
                "created_utc": now_utc,
                "asset": ticker,
                "horizon": HORIZON_LABEL,
                "target_id": ledger.TARGET_W1_UP_V1,
                "anchor_date": anchor_date.date().isoformat(),
                "anchor_close": str(float(frame["close"].iloc[-1])),
                "target_date": target_date.date().isoformat(),
                "probability": f"{stats['probability']:.4f}",
                "model_id": MODEL_ID,
                "train_n": str(stats["train_n"]),
                "train_start": stats["train_start"],
                "train_end": stats["train_end"],
                "data_version": versions[ticker],
                "code_commit": commit,
                "event_type": "",
                "event_date": "",
            }
        )
    return rows


def cmd_weekly(dry_run: bool, refresh: bool) -> None:
    if refresh:
        _refresh()
    frames, versions = _load_prices()
    commit = ledger.code_commit()
    now_utc = datetime.now(UTC).isoformat(timespec="seconds")
    forecasts = ledger.load_forecasts()
    resolutions = ledger.load_resolutions()

    res_rows = ledger.due_resolutions(forecasts, resolutions, frames, versions, commit, now_utc)
    print(f"\nFällige Auflösungen: {len(res_rows)}")
    for r in res_rows:
        print(
            f"  {r['forecast_id']}: TR {r['realized_return']} → outcome {r['outcome']} "
            f"(Zieltag {r['resolution_date']})"
        )

    fc_rows = _new_forecast_rows(frames, versions, set(forecasts["forecast_id"]), commit, now_utc)
    print(
        f"\nNeue Prognosen (Modelloutput klimatologie_v0, keine Anlageempfehlung): {len(fc_rows)}"
    )
    for r in fc_rows:
        print(
            f"  {r['forecast_id']}: P(Total-Return > 0 über {HORIZON_TRADING_DAYS} Handelstage) "
            f"= {r['probability']} · n = {r['train_n']} Fenster "
            f"({r['train_start']} – {r['train_end']}) · Anker {r['anchor_date']} "
            f"Close {r['anchor_close']} · Zieltag {r['target_date']} · "
            f"Daten sha256 {r['data_version'][:12]}… · Commit {r['code_commit']}"
        )

    if dry_run:
        print("\nDRY-RUN: nichts geschrieben.")
        return
    n_res = ledger.append_resolutions(res_rows)
    n_fc = ledger.append_forecasts(fc_rows)
    print(
        f"\nAngehängt: {n_res} Auflösung(en), {n_fc} Prognose(n). "
        "Jetzt: Ausgabe gegenlesen, `make check`, committen (docs/routinen.md)."
    )


def cmd_status() -> None:
    forecasts = ledger.load_forecasts()
    resolutions = ledger.load_resolutions()
    resolved_ids = set(resolutions["forecast_id"])
    open_rows = forecasts[~forecasts["forecast_id"].isin(resolved_ids)]
    today = datetime.now(UTC).date().isoformat()
    print(f"Prognosen: {len(forecasts)} · aufgelöst: {len(resolutions)} · offen: {len(open_rows)}")
    for _, r in open_rows.sort_values("target_date").iterrows():
        due = "fällig" if r["target_date"] <= today else f"Zieltag {r['target_date']}"
        print(f"  offen: {r['forecast_id']} ({due})")
    if len(resolutions):
        ones = (resolutions["outcome"] == "1").sum()
        print(
            f"Aufgelöste Ziele: {ones}× eingetreten, {len(resolutions) - ones}× nicht "
            "(reine Buchführung, keine Auswertung — Metriken erst mit ausreichend Forward-Daten)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mie.a4_ledger", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_weekly = sub.add_parser(
        "weekly", help="Wochenroutine: auffrischen, auflösen, prognostizieren"
    )
    p_weekly.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
    p_weekly.add_argument(
        "--no-refresh", action="store_true", help="ohne Tiingo-Abruf (vorhandenen Cache verwenden)"
    )

    sub.add_parser("status", help="offene/aufgelöste Prognosen anzeigen")

    args = parser.parse_args(argv)
    if args.cmd == "weekly":
        cmd_weekly(dry_run=args.dry_run, refresh=not args.no_refresh)
    else:
        cmd_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
