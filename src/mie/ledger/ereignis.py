"""Ereignisbezogene Forward-Ledger-Prognosen (B4): Termine, Deadline, Basisraten, Zeilen.

Ziele fomc_on_up_v1 (Overnight-TR > 0 am FOMC-Statement-Tag) und cpi_d1_up_v1
(Tages-TR > 0 am CPI-Release-Tag) sowie Modelle klimatologie_ev_v0
(ereigniskonditionale Basisrate) und klimatologie_alltage_v0 (unkonditionale
Referenz): docs/zieldefinitionen.md. Die Messgrößen-Formeln kommen unverändert
aus mie.es.masszahlen (Formeln der eingefrorenen Hypothesen), die Terminlisten
aus mie.es.ereignistage (meeting-Filter, CPI-Korrektur 1998).

Registrierungs-Deadline: created_utc muss nachweislich vor dem Börsenschluss
der letzten Handelssession vor dem Ereignistag liegen — dort beginnen beide
Messfenster. Verpasste Deadline = Termin wird ausgelassen und ausgewiesen,
kein Nachtragen. Alle ausgegebenen Wahrscheinlichkeiten sind Modelloutputs
(Klimatologie-Basisraten) — Szenario-Rechnungen, keine Anlageempfehlung.
"""

from collections.abc import Iterable

import pandas as pd
import pandas_market_calendars as mcal

from mie import ledger
from mie.es import ereignistage, masszahlen

EV_FOMC = "fomc"
EV_CPI = "cpi"

ASSETS = ("SPY", "QQQ")  # wie Wochen-Ledger (CLAUDE.md §3.1); BTC ist NICHT Teil der Ereignisse
LOOKAHEAD_TAGE = 10  # Kalendertage: deckt die Wochenlauf-Kadenz plus Puffer ab
FOMC_FENSTER_START = pd.Timestamp("1999-05-01")  # Statement-Zeiten-Ära (rep_pre_fomc_drift)

MODEL_EV = "klimatologie_ev_v0"
MODEL_REF = "klimatologie_alltage_v0"
REF_SUFFIX = "_ref"

HORIZON = {EV_FOMC: "ev_on", EV_CPI: "ev_d1"}
TARGET = {EV_FOMC: ledger.TARGET_FOMC_ON_UP_V1, EV_CPI: ledger.TARGET_CPI_D1_UP_V1}
ID_SUFFIX = {EV_FOMC: "fomc_on", EV_CPI: "cpi_d1"}


def mess_serie(frame: pd.DataFrame, target_id: str) -> pd.DataFrame:
    """Messreihe (date/wert) der Zielgröße eines Ereignis-Ziels."""
    if target_id == ledger.TARGET_FOMC_ON_UP_V1:
        return masszahlen.overnight_tr(frame)
    if target_id == ledger.TARGET_CPI_D1_UP_V1:
        return masszahlen.tages_tr(frame)
    raise ledger.LedgerError(f"kein Ereignis-Ziel: {target_id!r}")


def kommende_ereignisse(
    heute: pd.Timestamp,
    fomc_tage: pd.DatetimeIndex | None = None,
    cpi_tage: pd.DatetimeIndex | None = None,
    lookahead_tage: int = LOOKAHEAD_TAGE,
) -> list[dict]:
    """FOMC/CPI-Termine in (heute, heute + lookahead], mit Überlappungs-Flag.

    Terminlisten sind injizierbar (Tests); Default sind die Loader der
    Ereignisstudie (nur meeting_type=meeting, CPI-Korrektur 1998).
    """
    fomc_tage = ereignistage.load_fomc_days() if fomc_tage is None else fomc_tage
    cpi_tage = ereignistage.load_cpi_days() if cpi_tage is None else cpi_tage
    ueberlappung = set(fomc_tage) & set(cpi_tage)
    bis = heute + pd.Timedelta(days=lookahead_tage)
    faellig = [
        {"event_type": typ, "event_date": tag, "ueberlappung": tag in ueberlappung}
        for typ, tage in ((EV_FOMC, fomc_tage), (EV_CPI, cpi_tage))
        for tag in tage
        if heute < tag <= bis
    ]
    return sorted(faellig, key=lambda e: (e["event_date"], e["event_type"]))


def deadline_utc(event_date: pd.Timestamp) -> pd.Timestamp:
    """Registrierungs-Deadline: Börsenschluss der letzten Session vor dem Ereignistag.

    Echte Schlusszeit aus dem XNYS-Kalender (tz-bewusst, UTC) — Early-Close-Tage
    (13:00 ET) sind damit korrekt abgedeckt. Ist der Ereignistag selbst kein
    Handelstag, wird abgebrochen: stoppen und Projektinhaber fragen.
    """
    start = (event_date - pd.Timedelta(days=14)).date()
    sched = mcal.get_calendar("XNYS").schedule(start_date=start, end_date=event_date.date())
    if event_date not in sched.index:
        raise ledger.LedgerError(
            f"Ereignistag {event_date.date()} ist laut XNYS-Kalender kein Handelstag — "
            "verschobener Termin oder Börsenschließung? Stoppen und Projektinhaber fragen."
        )
    vorher = sched.loc[sched.index < event_date, "market_close"]
    if vorher.empty:
        raise ledger.LedgerError(
            f"keine Handelssession vor {event_date.date()} im Kalenderfenster gefunden"
        )
    return vorher.iloc[-1]


def _basisrate_aus(serie: pd.DataFrame, target_id: str) -> dict:
    if serie.empty:
        raise ledger.LedgerError(f"{target_id}: keine Beobachtungen für die Basisrate")
    return {
        "probability": round(float((serie["wert"] > 0).mean()), 4),
        "train_n": len(serie),
        "train_start": serie["date"].iloc[0].date().isoformat(),
        "train_end": serie["date"].iloc[-1].date().isoformat(),
    }


def ereignis_basisrate(
    frame: pd.DataFrame,
    ereignis_tage: pd.DatetimeIndex,
    target_id: str,
    fenster_start: pd.Timestamp | None = None,
    ausschluss_tage: Iterable[pd.Timestamp] = (),
) -> dict:
    """klimatologie_ev_v0: Anteil historischer Ereignistage mit Zielgröße > 0.

    train_start/train_end = erster/letzter verwendeter Ereignistag; Ereignistage
    ohne Kurszeile (vor Reihenbeginn oder in der Zukunft) fallen heraus. Daten
    ab 01.01.2025 sind Live-Prognose-Input (Lockbox-Regel, CLAUDE.md §3.6).
    """
    serie = mess_serie(frame, target_id)
    tage = pd.DatetimeIndex(ereignis_tage).difference(pd.DatetimeIndex(list(ausschluss_tage)))
    if fenster_start is not None:
        tage = tage[tage >= fenster_start]
    treffer = serie[serie["date"].isin(tage)]
    if treffer.empty:
        raise ledger.LedgerError(f"{target_id}: keine historischen Ereignistage in der Kursreihe")
    return _basisrate_aus(treffer, target_id)


def alltage_basisrate(frame: pd.DataFrame, target_id: str) -> dict:
    """klimatologie_alltage_v0: Anteil ALLER Handelstage der Reihe mit Zielgröße > 0."""
    return _basisrate_aus(mess_serie(frame, target_id), target_id)


def neue_ereignis_zeilen(
    frames: dict[str, pd.DataFrame],
    versions: dict[str, str],
    existing_ids: set[str],
    commit: str,
    now_utc: str,
    fomc_tage: pd.DatetimeIndex | None = None,
    cpi_tage: pd.DatetimeIndex | None = None,
    assets: tuple[str, ...] = ASSETS,
    lookahead_tage: int = LOOKAHEAD_TAGE,
) -> tuple[list[dict], list[str]]:
    """Prognosezeilen (klimatologie_ev_v0 + Referenz) für kommende FOMC/CPI-Termine.

    Liefert (zeilen, meldungen). Die Meldungen weisen jeden Termin aus:
    registriert (mit Deadline), Überlappungstag ausgesetzt, Deadline verpasst
    (kein Nachtragen) oder bereits registriert (idempotent).
    """
    now = pd.Timestamp(now_utc)
    if now.tzinfo is None:
        raise ledger.LedgerError("now_utc muss ein tz-bewusster UTC-Zeitstempel sein")
    heute = now.tz_convert("UTC").normalize().tz_localize(None)
    fomc_tage = ereignistage.load_fomc_days() if fomc_tage is None else fomc_tage
    cpi_tage = ereignistage.load_cpi_days() if cpi_tage is None else cpi_tage
    ueberlappungs_tage = pd.DatetimeIndex(sorted(set(fomc_tage) & set(cpi_tage)))
    basis_tage = {EV_FOMC: fomc_tage, EV_CPI: cpi_tage}
    fenster_start = {EV_FOMC: FOMC_FENSTER_START, EV_CPI: None}

    zeilen: list[dict] = []
    meldungen: list[str] = []
    for ev in kommende_ereignisse(heute, fomc_tage, cpi_tage, lookahead_tage):
        tag, typ = ev["event_date"], ev["event_type"]
        label = f"{typ.upper()} {tag.date()}"
        if ev["ueberlappung"]:
            meldungen.append(
                f"{label}: FOMC=CPI-Überlappungstag — ausgesetzt (docs/zieldefinitionen.md)"
            )
            continue
        deadline = deadline_utc(tag)
        if now >= deadline:
            meldungen.append(
                f"{label}: Registrierungs-Deadline {deadline.isoformat()} verpasst — "
                "Termin wird ausgelassen (kein Nachtragen)"
            )
            continue
        meldungen.append(f"{label}: Registrierung vor Deadline {deadline.isoformat()}")
        target_id = TARGET[typ]
        for asset in assets:
            frame = frames[asset]
            basis = ereignis_basisrate(
                frame, basis_tage[typ], target_id, fenster_start[typ], ueberlappungs_tage
            )
            referenz = alltage_basisrate(frame, target_id)
            varianten = (("", MODEL_EV, basis), (REF_SUFFIX, MODEL_REF, referenz))
            for suffix, model_id, stats in varianten:
                forecast_id = f"{tag.date()}_{asset.lower()}_{ID_SUFFIX[typ]}{suffix}"
                if forecast_id in existing_ids:
                    meldungen.append(f"{forecast_id}: bereits registriert — übersprungen")
                    continue
                zeilen.append(
                    {
                        "forecast_id": forecast_id,
                        "created_utc": now_utc,
                        "asset": asset,
                        "horizon": HORIZON[typ],
                        "target_id": target_id,
                        "anchor_date": frame["date"].iloc[-1].date().isoformat(),
                        "anchor_close": str(float(frame["close"].iloc[-1])),
                        "target_date": tag.date().isoformat(),
                        "probability": f"{stats['probability']:.4f}",
                        "model_id": model_id,
                        "train_n": str(stats["train_n"]),
                        "train_start": stats["train_start"],
                        "train_end": stats["train_end"],
                        "data_version": versions[asset],
                        "code_commit": commit,
                        "event_type": typ,
                        "event_date": tag.date().isoformat(),
                    }
                )
    return zeilen, meldungen
