"""A4-CLI: wöchentliche Ledger-Routine (Prognosen + Auflösungen) und Status.

Aufrufe (aus dem Repo-Wurzelverzeichnis):
    uv run python -m mie.a4_ledger weekly [--dry-run] [--no-refresh]
    uv run python -m mie.a4_ledger events [--dry-run] [--no-refresh]
    uv run python -m mie.a4_ledger status

weekly: (1) Tiingo-Cache SPY+QQQ und Coinbase-Cache BTC auffrischen, (2) fällige
Prognosen auflösen, (3) je Asset eine 1-Wochen-Prognose anhängen (klimatologie_v0;
SPY/QQQ: Ziel w1_up_v1 über 5 Handelstage, BTC: Ziel btc_w1_up_v1 über
7 Kalendertage UTC — docs/zieldefinitionen.md), (4) kommende FOMC/CPI-Termine
registrieren (B4: Ziele fomc_on_up_v1/cpi_d1_up_v1, Modelle klimatologie_ev_v0
+ Referenz klimatologie_alltage_v0 — mie.ledger.ereignis).

events: nur der Ereigniszweig (Tiingo-Refresh SPY+QQQ, fällige
Ereignis-Auflösungen, kommende Termine registrieren) — für Läufe zwischen den
Wochenläufen, wenn eine Registrierungs-Deadline vor dem nächsten Wochenlauf
liegt.

Alle ausgegebenen Wahrscheinlichkeiten sind Modelloutputs
(Klimatologie-Basisraten) — keine Anlageempfehlung. Netzzugriff passiert nur
hier (CLI), nie in Tests. Danach: Ausgabe gegenlesen, `make check`, committen
(docs/routinen.md).
"""

import argparse
import sys
from datetime import UTC, datetime

import pandas as pd

from mie import ledger
from mie.checks import check_duplicates, check_gaps
from mie.ledger import ereignis
from mie.ledger.klimatologie import HORIZON_TRADING_DAYS, base_rate
from mie.sources import coinbase, raw_paths, read_meta, tiingo, validate_standard_frame

ASSETS = ["SPY", "QQQ"]  # Festlegung Projektinhaber 08.07.2026 (CLAUDE.md §3.1)
HORIZON_LABEL = "w1_5td"
MODEL_ID = "klimatologie_v0"

BTC_ASSET = "BTC"  # eigener Ledger-Zweig (A6) — NICHT Teil der Ereignisstudie (CLAUDE.md §3.2)
BTC_HORIZON_LABEL = "w1_7cd"
BTC_HORIZON_DAYS = 7  # Kalendertage UTC (docs/zieldefinitionen.md, btc_w1_up_v1)


def _refresh_etfs() -> None:
    for ticker in ASSETS:
        try:
            _, meta = tiingo.download_daily(ticker)
        except OSError as exc:
            raise SystemExit(
                f"Tiingo nicht erreichbar ({exc}) — Lauf später wiederholen; "
                "kein stiller Quellenwechsel (docs/zieldefinitionen.md)."
            ) from exc
        print(f"tiingo/{ticker}: {meta['rows']} Zeilen (sha256 {meta['sha256'][:12]}…)")


def _refresh() -> None:
    _refresh_etfs()
    try:
        _, meta = coinbase.download_daily()
    except OSError as exc:
        raise SystemExit(
            f"Coinbase nicht erreichbar ({exc}) — Lauf später wiederholen; "
            "kein stiller Quellenwechsel (docs/zieldefinitionen.md)."
        ) from exc
    print(f"coinbase/{coinbase.TICKER}: {meta['rows']} Zeilen (sha256 {meta['sha256'][:12]}…)")


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


def _load_btc() -> tuple[pd.DataFrame, str]:
    """BTC-Frame (nur abgeschlossene UTC-Tage) + Datenversion; bricht bei Schadbefund ab.

    Prüfungen laut docs/zieldefinitionen.md (btc_w1_up_v1): Duplikate, Close ≤ 0
    und Kalendertag-Lücken — nur bei lückenloser Reihe gilt 7 Zeilen =
    7 Kalendertage (Basisrate). Die Kerze des laufenden UTC-Tages ist noch nicht
    final und wird verworfen (Anker = letzter abgeschlossener UTC-Tag).
    """
    raw_path, _ = raw_paths(coinbase.SOURCE, coinbase.TICKER, coinbase.EXT)
    if not raw_path.exists():
        raise SystemExit("Kein Coinbase-Cache für BTC — weekly ohne --no-refresh laufen lassen.")
    frame = coinbase.parse_cached(raw_path)
    today_utc = pd.Timestamp(datetime.now(UTC).date())
    frame = frame[frame["date"] < today_utc].reset_index(drop=True)
    if frame.empty:
        raise SystemExit("BTC: keine abgeschlossenen UTC-Tage im Coinbase-Cache")
    problems = []
    if not frame["date"].is_monotonic_increasing:
        problems.append("date nicht aufsteigend sortiert")
    if len(check_duplicates(frame)):
        problems.append("doppelte Datumszeilen")
    gaps = check_gaps(frame, pd.date_range(frame["date"].min(), frame["date"].max(), freq="D"))
    if len(gaps):
        gap_list = ", ".join(d.date().isoformat() for d in gaps[:5])
        problems.append(f"{len(gaps)} Kalendertag-Lücke(n), z. B. {gap_list}")
    if (frame["close"] <= 0).any():
        problems.append("Close ≤ 0")
    if problems:
        raise SystemExit(
            f"BTC: Kursframe fehlerhaft — {'; '.join(problems)}. "
            "Stoppen und Projektinhaber fragen (kein stilles Weiterrechnen)."
        )
    # BTC kennt keine Dividenden/Splits; die Konstantspalten lassen window_return/
    # base_rate unverändert gelten (docs/zieldefinitionen.md, btc_w1_up_v1).
    frame = frame.assign(div_cash=0.0, split_factor=1.0)
    version = read_meta(coinbase.SOURCE, coinbase.TICKER, coinbase.EXT)["sha256"]
    return frame, version


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


def _btc_forecast_rows(
    frame: pd.DataFrame,
    version: str,
    existing_ids: set[str],
    commit: str,
    now_utc: str,
) -> list[dict]:
    anchor_date = frame["date"].iloc[-1]  # letzter abgeschlossener UTC-Tag (_load_btc)
    forecast_id = f"{anchor_date.date()}_btc_w1"
    if forecast_id in existing_ids:
        print(f"{forecast_id}: bereits registriert (Anker unverändert) — übersprungen")
        return []
    stats = base_rate(frame, horizon=BTC_HORIZON_DAYS)
    target_date = anchor_date + pd.Timedelta(days=BTC_HORIZON_DAYS)
    return [
        {
            "forecast_id": forecast_id,
            "created_utc": now_utc,
            "asset": BTC_ASSET,
            "horizon": BTC_HORIZON_LABEL,
            "target_id": ledger.TARGET_BTC_W1_UP_V1,
            "anchor_date": anchor_date.date().isoformat(),
            "anchor_close": str(float(frame["close"].iloc[-1])),
            "target_date": target_date.date().isoformat(),
            "probability": f"{stats['probability']:.4f}",
            "model_id": MODEL_ID,
            "train_n": str(stats["train_n"]),
            "train_start": stats["train_start"],
            "train_end": stats["train_end"],
            "data_version": version,
            "code_commit": commit,
            "event_type": "",
            "event_date": "",
        }
    ]


def _ziel_text(r: dict) -> str:
    if r["horizon"] == BTC_HORIZON_LABEL:
        return f"P(Close-Rendite > 0 über {BTC_HORIZON_DAYS} Kalendertage UTC)"
    if r["horizon"] == ereignis.HORIZON[ereignis.EV_FOMC]:
        return f"P(Overnight-TR > 0 am FOMC-Statement-Tag {r['event_date']})"
    if r["horizon"] == ereignis.HORIZON[ereignis.EV_CPI]:
        return f"P(Tages-TR > 0 am CPI-Release-Tag {r['event_date']})"
    return f"P(Total-Return > 0 über {HORIZON_TRADING_DAYS} Handelstage)"


def _print_resolutions(res_rows: list[dict]) -> None:
    for r in res_rows:
        print(
            f"  {r['forecast_id']}: TR {r['realized_return']} → outcome {r['outcome']} "
            f"(Zieltag {r['resolution_date']})"
        )


def _print_forecasts(fc_rows: list[dict]) -> None:
    for r in fc_rows:
        print(
            f"  {r['forecast_id']}: {_ziel_text(r)} "
            f"= {r['probability']} [{r['model_id']}] · n = {r['train_n']} "
            f"({r['train_start']} – {r['train_end']}) · Anker {r['anchor_date']} "
            f"Close {r['anchor_close']} · Zieltag {r['target_date']} · "
            f"Daten sha256 {r['data_version'][:12]}… · Commit {r['code_commit']}"
        )


def _ereignis_rows(
    frames: dict[str, pd.DataFrame],
    versions: dict[str, str],
    existing_ids: set[str],
    commit: str,
    now_utc: str,
) -> list[dict]:
    """Ereigniszweig (B4): kommende Termine registrieren, jeden Termin ausweisen."""
    ev_rows, meldungen = ereignis.neue_ereignis_zeilen(
        frames, versions, existing_ids, commit, now_utc
    )
    print(f"\nEreignis-Termine (FOMC/CPI, nächste {ereignis.LOOKAHEAD_TAGE} Kalendertage):")
    if not meldungen:
        print("  keine Termine im Fenster")
    for m in meldungen:
        print(f"  {m}")
    return ev_rows


def cmd_weekly(dry_run: bool, refresh: bool) -> None:
    if refresh:
        _refresh()
    frames, versions = _load_prices()
    frames[BTC_ASSET], versions[BTC_ASSET] = _load_btc()
    commit = ledger.code_commit()
    now_utc = datetime.now(UTC).isoformat(timespec="seconds")
    forecasts = ledger.load_forecasts()
    resolutions = ledger.load_resolutions()

    res_rows = ledger.due_resolutions(forecasts, resolutions, frames, versions, commit, now_utc)
    print(f"\nFällige Auflösungen: {len(res_rows)}")
    _print_resolutions(res_rows)

    existing_ids = set(forecasts["forecast_id"])
    fc_rows = _new_forecast_rows(frames, versions, existing_ids, commit, now_utc)
    fc_rows += _btc_forecast_rows(
        frames[BTC_ASSET], versions[BTC_ASSET], existing_ids, commit, now_utc
    )
    fc_rows += _ereignis_rows(frames, versions, existing_ids, commit, now_utc)
    print(f"\nNeue Prognosen (Modelloutputs Klimatologie, keine Anlageempfehlung): {len(fc_rows)}")
    _print_forecasts(fc_rows)

    if dry_run:
        print("\nDRY-RUN: nichts geschrieben.")
        return
    n_res = ledger.append_resolutions(res_rows)
    n_fc = ledger.append_forecasts(fc_rows)
    print(
        f"\nAngehängt: {n_res} Auflösung(en), {n_fc} Prognose(n). "
        "Jetzt: Ausgabe gegenlesen, `make check`, committen (docs/routinen.md)."
    )


def cmd_events(dry_run: bool, refresh: bool) -> None:
    """Nur Ereigniszweig: fällige Ereignis-Auflösungen + kommende Termine registrieren."""
    if refresh:
        _refresh_etfs()
    frames, versions = _load_prices()
    commit = ledger.code_commit()
    now_utc = datetime.now(UTC).isoformat(timespec="seconds")
    forecasts = ledger.load_forecasts()
    resolutions = ledger.load_resolutions()

    ev_forecasts = forecasts[forecasts["target_id"].isin(ledger.EVENT_TARGETS)]
    res_rows = ledger.due_resolutions(ev_forecasts, resolutions, frames, versions, commit, now_utc)
    print(f"\nFällige Ereignis-Auflösungen: {len(res_rows)}")
    _print_resolutions(res_rows)

    existing_ids = set(forecasts["forecast_id"])
    fc_rows = _ereignis_rows(frames, versions, existing_ids, commit, now_utc)
    print(
        f"\nNeue Ereignis-Prognosen (Modelloutputs Klimatologie, "
        f"keine Anlageempfehlung): {len(fc_rows)}"
    )
    _print_forecasts(fc_rows)

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
        "weekly", help="Wochenroutine: auffrischen, auflösen, prognostizieren (inkl. Ereignisse)"
    )
    p_events = sub.add_parser(
        "events", help="nur Ereigniszweig: FOMC/CPI-Prognosen registrieren und auflösen"
    )
    for p in (p_weekly, p_events):
        p.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
        p.add_argument(
            "--no-refresh",
            action="store_true",
            help="ohne Tiingo-Abruf (vorhandenen Cache verwenden)",
        )

    sub.add_parser("status", help="offene/aufgelöste Prognosen anzeigen")

    args = parser.parse_args(argv)
    if args.cmd == "weekly":
        cmd_weekly(dry_run=args.dry_run, refresh=not args.no_refresh)
    elif args.cmd == "events":
        cmd_events(dry_run=args.dry_run, refresh=not args.no_refresh)
    else:
        cmd_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
