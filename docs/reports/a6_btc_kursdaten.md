# A6 — Verfügbarkeits- und Qualitätsreport BTC-Tagesdaten

**Generiert:** 2026-07-08T21:57:34+00:00 · **Commit:** `be35ed5` · Erzeugt von `uv run python -m mie.a6_btc_quellen report` — nicht von Hand editieren.

R3-Felder: n, Zeitraum und Datenversion stehen je Quelle unten. **Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/Qualitätsreport ohne Effektschätzung. Einordnung und Nutzungsbedingungen: docs/reports/a6_btc_quellen.md.

BTC handelt 24/7: Lücken-Check gegen **Kalendertage (UTC)**, kein Börsenkalender. Die letzte Zeile je Quelle kann der laufende, noch unfertige UTC-Tag sein (die Ledger-Schicht verwirft ihn; Anker-Regel in docs/zieldefinitionen.md).

## Quellen

### tiingo_crypto

- n = **5404** Zeilen · Zeitraum **2011-08-19 – 2026-07-08**
- Datenversion: sha256 `28d984dc6bd3f3e3…`, abgerufen 2026-07-08T21:52:02+00:00
- Checks: Duplikate **0** · Kalendertag-Lücken **34** · OHLC-Verstöße **0** · Close ≤ 0: **0**
- erste Lücken-Tage: 2011-08-24, 2011-08-27, 2011-08-28, 2011-08-29, 2011-08-30, 2011-09-01, 2011-09-04, 2011-09-06, 2011-09-10, 2011-09-11 · letzter Lücken-Tag: **2026-02-15** → lückenfrei ab **2026-02-16**

### coinbase

- n = **4007** Zeilen · Zeitraum **2015-07-20 – 2026-07-08**
- Datenversion: sha256 `6260ce75b65a53c4…`, abgerufen 2026-07-08T21:46:50+00:00
- Checks: Duplikate **0** · Kalendertag-Lücken **0** · OHLC-Verstöße **0** · Close ≤ 0: **0**
- lückenfrei ab Reihenbeginn (**2015-07-20**)

## Kreuzabgleich tiingo_crypto × coinbase (Start-Toleranz close: 0.5 %)

- Überlappung n = **4006** · nur tiingo_crypto: 1398 · nur coinbase: 1
- **close** |Δ|rel: Median 0.0503 % · p95 5.0727 % · Max 21.6590 % · > Toleranz: **1117** (vor 2025: 1117, ab 2025: 0)
- Überschreitungstage (Stichprobe): 2015-07-20, 2015-07-21, 2015-07-24, 2015-07-26, 2015-07-29 · **letzter** Überschreitungstag: **2023-05-07**

