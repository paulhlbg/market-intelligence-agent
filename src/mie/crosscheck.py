"""Kreuzabgleich zweier Kursdaten-Quellen (A2).

Vergleicht je Handelstag die relative Abweichung von rohem Close und
adjustiertem Close. Start-Toleranz laut Plan: 0,1 % für den rohen Close.
Überschreitungen werden gezählt und ausgewiesen — nie verworfen.
Statistiken zusätzlich getrennt vor/ab dem Lockbox-Stichtag (01.01.2025),
damit sichtbar bleibt, worauf sich Entwicklungsentscheidungen stützen.
"""

import pandas as pd

TOLERANCE_RAW_CLOSE = 0.001  # 0,1 % relativ; endgültige Toleranz nach Befund dokumentieren
LOCKBOX_CUTOFF = pd.Timestamp("2025-01-01")


def _dev_stats(dev: pd.Series, tolerance: float) -> dict:
    """Verteilungskennzahlen der absoluten relativen Abweichung."""
    abs_dev = dev.abs()
    if len(abs_dev) == 0:
        return {"n": 0, "median": None, "p95": None, "max": None, "exceed": None}
    return {
        "n": int(len(abs_dev)),
        "median": float(abs_dev.median()),
        "p95": float(abs_dev.quantile(0.95)),
        "max": float(abs_dev.max()),
        "exceed": int((abs_dev > tolerance).sum()),
    }


def crosscheck(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str,
    label_b: str,
    tolerance: float = TOLERANCE_RAW_CLOSE,
    columns: tuple[str, ...] = ("close", "adj_close"),
) -> dict:
    """Beide Quellen über das Datum verbinden und Abweichungen quantifizieren.

    Relative Abweichung = (a − b) / b. Für close gilt die Toleranz;
    adj_close wird mit derselben Kennzahl berichtet, aber ohne Bestehens-Schwelle
    (Adjustierungsmethoden differieren systematisch zwischen Quellen).
    columns: zu vergleichende Spalten — BTC-Frames (A6) haben kein adj_close,
    dort wird nur ("close",) verglichen.
    """
    merged = df_a.merge(df_b, on="date", how="inner", suffixes=("_a", "_b"))
    result: dict = {
        "label_a": label_a,
        "label_b": label_b,
        "n_a": len(df_a),
        "n_b": len(df_b),
        "n_overlap": len(merged),
        "only_a": int(len(df_a) - len(merged)),
        "only_b": int(len(df_b) - len(merged)),
        "tolerance": tolerance,
    }
    for col in columns:
        dev = (merged[f"{col}_a"] - merged[f"{col}_b"]) / merged[f"{col}_b"]
        pre = dev[merged["date"] < LOCKBOX_CUTOFF]
        post = dev[merged["date"] >= LOCKBOX_CUTOFF]
        exceed_dates = merged.loc[dev.abs() > tolerance, "date"]
        result[col] = {
            "all": _dev_stats(dev, tolerance),
            "pre_lockbox": _dev_stats(pre, tolerance),
            "post_lockbox": _dev_stats(post, tolerance),
            # Stichprobe der Überschreitungstage (max. 5) und letzter Überschreitungstag
            "exceed_days_sample": [d.date().isoformat() for d in exceed_dates.iloc[:5]],
            "last_exceed_day": (
                exceed_dates.iloc[-1].date().isoformat() if len(exceed_dates) else None
            ),
        }
    return result
