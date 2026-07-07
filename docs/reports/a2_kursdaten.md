# A2 — Verfügbarkeits- und Qualitätsreport Kursdaten

**Generiert:** 2026-07-07T21:13:01+00:00 · **Commit:** `4359caf` · Erzeugt von `uv run python -m mie.a2_kursdaten report` — nicht von Hand editieren.

R3-Felder: n, Zeitraum und Datenversion stehen je Quelle/Ticker unten. **Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/Qualitätsreport ohne Effektschätzung.

Qualitätschecks laufen über den vollen Zeitraum inkl. Lockbox (Beschluss 07.07.2026); Kreuzabgleich-Überschreitungen werden zusätzlich getrennt vor/ab 01.01.2025 ausgewiesen. Keine Rendite-/Musteranalyse.

## Quelle „yahoo“

### SPY

- n = **8415** Zeilen · Zeitraum **1993-01-29 – 2026-07-07**
- Datenversion: sha256 `1f2cda3a46f3a425…`, abgerufen 2026-07-07T21:08:09+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**

### VOO

- n = **3979** Zeilen · Zeitraum **2010-09-09 – 2026-07-07**
- Datenversion: sha256 `1fc991af7d38b0b2…`, abgerufen 2026-07-07T21:08:09+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**

### QQQ

- n = **6873** Zeilen · Zeitraum **1999-03-10 – 2026-07-07**
- Datenversion: sha256 `25c4901492256c97…`, abgerufen 2026-07-07T21:08:09+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**

## Quelle „tiingo“

### SPY

- n = **8415** Zeilen · Zeitraum **1993-01-29 – 2026-07-07**
- Datenversion: sha256 `8d67c1036caa8be9…`, abgerufen 2026-07-07T21:08:11+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**
- Adjustierungs-Ereignisse (Tiingo-Felder): Dividenden **135** (letzte: 2026-06-18) · Splits **0**

### VOO

- n = **3979** Zeilen · Zeitraum **2010-09-09 – 2026-07-07**
- Datenversion: sha256 `d7c87b035a69649a…`, abgerufen 2026-07-07T21:08:12+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**
- Adjustierungs-Ereignisse (Tiingo-Felder): Dividenden **64** (letzte: 2026-06-26) · Splits **1**

### QQQ

- n = **6873** Zeilen · Zeitraum **1999-03-10 – 2026-07-07**
- Datenversion: sha256 `9e1a84f54a27acc5…`, abgerufen 2026-07-07T21:08:13+00:00
- Checks: Duplikate **0** · Lücken **0** · Zusatztage **0** · OHLC-Verstöße **0** · Preis ≤ 0: **0** · Volumen = 0: **0**
- Adjustierungs-Ereignisse (Tiingo-Felder): Dividenden **88** (letzte: 2026-06-22) · Splits **1**

## Kreuzabgleich yahoo × tiingo (Start-Toleranz raw close: 0.1 %)

### SPY

- Überlappung n = **8415** · nur yahoo: 0 · nur tiingo: 0
- **close** |Δ|rel: Median 0.0000 % · p95 0.0001 % · Max 0.1130 % · > Toleranz: **2** (vor 2025: 2, ab 2025: 0)
  - Überschreitungstage (close): 2015-08-21, 2015-08-26
- **adj_close** |Δ|rel: Median 0.0700 % · p95 0.1070 % · Max 0.1900 % · > Toleranz: **794** (vor 2025: 794, ab 2025: 0)

### VOO

- Überlappung n = **3979** · nur yahoo: 0 · nur tiingo: 0
- **close** |Δ|rel: Median 0.0000 % · p95 100.0000 % · Max 100.0180 % · > Toleranz: **788** (vor 2025: 788, ab 2025: 0)
- **adj_close** |Δ|rel: Median 0.0523 % · p95 0.4915 % · Max 0.5005 % · > Toleranz: **1078** (vor 2025: 1078, ab 2025: 0)

### QQQ

- Überlappung n = **6873** · nur yahoo: 0 · nur tiingo: 0
- **close** |Δ|rel: Median 0.0000 % · p95 0.0116 % · Max 51.3024 % · > Toleranz: **276** (vor 2025: 276, ab 2025: 0)
- **adj_close** |Δ|rel: Median 0.1250 % · p95 0.1557 % · Max 2.7265 % · > Toleranz: **5002** (vor 2025: 5002, ab 2025: 0)

## Split-Behandlung der rohen Close-Kurse

Systematischer Quellen-Unterschied (erwartet laut CLAUDE.md §5/A2): yfinance liefert bei `auto_adjust=False` einen **split-adjustierten** Close (nur Dividenden bleiben außen vor), Tiingo dagegen den **unveränderten Handelskurs**. Vor Split-Terminen weichen die „rohen“ Close-Reihen daher genau um den Split-Faktor ab; der weit überwiegende Teil der Toleranz-Überschreitungen ist so erklärt, kleine Restmengen (Einzeltage, v. a. hochvolatile Tage und Bruchteil-Notierungs-Ära vor 2001) werden je Ticker ausgewiesen:

### SPY

- keine Splits (Tiingo splitFactor durchgehend 1) — raw close direkt vergleichbar

### VOO

- Split am **2013-10-24** (Tiingo splitFactor 0.5): Verhältnis close_tiingo/close_yahoo am Vortag = **0.5000** → yahoo-Close ist rückwirkend split-adjustiert, tiingo-close ist der tatsächlich gehandelte Kurs
- close-Überschreitungen: **787** vor dem ersten Split (split-erklärt), **1** danach — Resttage (nicht split-erklärt): 2016-06-24

### QQQ

- Split am **2000-03-20** (Tiingo splitFactor 2.0): Verhältnis close_tiingo/close_yahoo am Vortag = **1.9998** → yahoo-Close ist rückwirkend split-adjustiert, tiingo-close ist der tatsächlich gehandelte Kurs
- close-Überschreitungen: **260** vor dem ersten Split (split-erklärt), **16** danach — Resttage (nicht split-erklärt): 2000-04-10, 2000-04-19, 2000-05-31, 2000-08-31, 2001-04-06 …

