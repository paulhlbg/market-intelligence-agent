# B3 — Replikation `rep_pre_fomc_drift`: Pre-FOMC-Announcement-Drift

**Generiert:** 2026-07-10T13:43:13+00:00 · **Commit:** `353b50c` · Erzeugt von `uv run python -m mie.es.b3_drift report` — nicht von Hand editieren.

**Frage (eingefroren):** Pre-FOMC-Announcement-Drift (Lucca/Moench 2015) — ist die mittlere Overnight-Total-Return-Rendite (Overnight-TR, Schluss T−1 → Eröffnung T) von SPY/QQQ in den FOMC-Statement-Tag hinein höher als an Baseline-Tagen (Handelstage ohne FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein Unterschied. SPY = primäre Replikation (Paper-Index S&P 500), QQQ = sekundäre Erweiterung (nicht Teil des Paper-Befunds).

Eingefrorene Hypothese: `registry/hypothesen/rep_pre_fomc_drift.md` (sha256 `26a65dd8cf923e7f7b08316636d387585cee528679c6771dee96d23665b6fb23`, registriert 2026-07-08T21:13:22+00:00). Fenster 1999-05-01 – 2024-12-31 — endet vor dem Lockbox-Stichtag 2025-01-01; diese Auswertung ist keine Lockbox-Auswertung (lockbox=0, Zähler unverändert).

## Vorregistrierung und Umfang

- **Anzahl Tests (R6-Multiplizität):** 2 Vergleiche (davon 1 primär: SPY; 1 sekundär: QQQ) + 2 Placebo-Tests (R4-Selbsttest der Pipeline, 1 je Asset). Alle werden vollständig berichtet — kein Auswahl-Reporting. Keine Mediane, keine Zusatzmaße, keine eigene CPI-Auswertung (nicht vorregistriert).
- **Bootstrap:** Perzentil-KI, n_boot=10000, alpha=0.05. Seeds vorab fixiert (Paketplan 10.07.2026): Basis 20260710, Vergleiche fortlaufend (Reihenfolge SPY → QQQ), Placebos ab Basis+100 fortlaufend.
- **Maß** (Tiingo-Rohfelder, nie adj_close): Overnight-TR = (open_T + div_cash_T) · split_factor_T / close_(T−1) − 1 — Dividenden/Splits wirken am Ex-Tag zur Eröffnung, konsistent zur TR-Formel aus Ziel `w1_up_v1`.
- **Ereignistage:** nur reguläre FOMC-Sitzungen (meeting_type=meeting), Statement-Tag = letzter Sitzungstag; Stichprobe ab Mai 1999 (Ära-Grenze der Statement-Zeiten 12:30–14:15 ET — die Eröffnung 09:30 ET liegt in allen Äras vor dem Statement, das Overnight-Fenster ist frei von der Statement-Reaktion).
- **Baseline:** alle übrigen Handelstage ohne FOMC- und ohne CPI-Termin — CPI-Releases (08:30 ET) liegen im Overnight-Fenster und würden die Baseline kontaminieren.
- **Überlappungsregel (anders als B1/B2):** Fällt ein FOMC-Statement-Tag mit einem CPI-Release zusammen, wird der Tag aus dem Haupttest ausgeschlossen (weder Ereignis noch Baseline) und unten gesondert ausgewiesen.

## Datenversion (R3)

- Tiingo SPY (data/raw/tiingo/spy_daily.json): sha256 `f306a5612bf841e3adb71c4fac06206bdb957bece3507d62d4d37493da32da74` · Stand 2026-07-08T22:03:10+00:00 · n = 8416 Zeilen
- Tiingo QQQ (data/raw/tiingo/qqq_daily.json): sha256 `f23b7f8a5c9ec49458e8fd29ff3d4e7ea354247632f90608abe1c40080cbc4da` · Stand 2026-07-08T22:03:11+00:00 · n = 6874 Zeilen
- FOMC-Termine (data/processed/fomc_termine.csv · nur meeting_type=meeting): sha256 `31a1a014398ce458f0ce967530748a69b32626b213aef9e5c0aa2948da619091` · Stand committet (A3) · n = 272 reguläre Sitzungen
- CPI-Termine (data/processed/cpi_termine.csv · inkl. Korrektur 1998-02-24): sha256 `89450a8d335a1e85d0174152db79d9f5950d29bea809135b0b67a9ebe39b53a5` · Stand committet (A3) · n = 394 Release-Tage

## Stichprobe je Asset

| Asset | Zeitraum (verwendet) | Handelstage | FOMC handelbar | davon FOMC=CPI | Ereignis (Haupttest) | CPI-Ausschluss | Baseline |
|---|---|---|---|---|---|---|---|
| SPY | 1999-05-03 – 2024-12-31 | 6459 | 206 | 16 | 190 | 306 | 5963 |
| QQQ | 1999-05-03 – 2024-12-31 | 6459 | 206 | 16 | 190 | 306 | 5963 |

CPI-Ausschluss = alle handelbaren CPI-Tage inkl. Überlappung; Bilanz je Asset: Ereignis + Baseline + CPI-Ausschluss = Handelstage.

Überlappungstage FOMC=CPI im Fenster — aus dem Haupttest ausgeschlossen und hier gesondert ausgewiesen (keine eigene Statistik, nicht vorregistriert):

- SPY: 2000-05-16 · 2003-09-16 · 2008-09-16 · 2008-12-16 · 2009-03-18 · 2009-12-16 · 2013-10-30 · 2014-09-17 · 2014-12-17 · 2016-03-16 · 2017-03-15 · 2017-06-14 · 2017-12-13 · 2019-12-11 · 2020-06-10 · 2024-06-12
- QQQ: 2000-05-16 · 2003-09-16 · 2008-09-16 · 2008-12-16 · 2009-03-18 · 2009-12-16 · 2013-10-30 · 2014-09-17 · 2014-12-17 · 2016-03-16 · 2017-03-15 · 2017-06-14 · 2017-12-13 · 2019-12-11 · 2020-06-10 · 2024-06-12

FOMC-Ereignistage im Fenster ohne Handelstag im Kursframe (nicht still verworfen):

- SPY: keine
- QQQ: keine

## Primäres Ergebnis — Mittelwert Overnight-TR (SPY, Ereignis − Baseline)

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 190 | 5963 | 0.153 % | 0.028 % | +0.125 | [+0.044; +0.204] | ja |

## Sekundäres Ergebnis — Erweiterung QQQ

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| QQQ | FOMC | 190 | 5963 | 0.208 % | 0.057 % | +0.151 | [+0.044; +0.255] | ja |

## R4-Placebo (jahresgeschichtet, Mittelwert Overnight-TR)

Je Kalenderjahr werden so viele zufällige Nicht-Ereignistage gezogen wie echte handelbare FOMC-Statement-Tage des Haupttests; echte FOMC-Tage und alle CPI-Tage bleiben komplett außen vor (wie im Haupttest). Erwartung: Differenz ≈ 0, das KI überdeckt die 0 — konstruktionsbedingt verfehlt ein 95-%-KI die 0 aber in ~5 % der Ziehungen.

| Asset | Gruppe | n Placebo | n Baseline | Δ (P−B) in pp | 95-%-KI in pp | 0 im KI |
|---|---|---|---|---|---|---|
| SPY | FOMC | 190 | 5773 | -0.074 | [-0.172; +0.021] | ja |
| QQQ | FOMC | 190 | 5773 | +0.072 | [-0.069; +0.238] | ja |

## Zusammenfassung (automatisch aus den Zahlen)

- 1 von 1 primären 95-%-KIs (SPY, Mittelwert Overnight-TR) liegen vollständig über 0.
- 1 von 1 sekundären 95-%-KIs (QQQ) liegen vollständig über 0.
- 2 von 2 Placebo-KIs überdecken die 0.

## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)

1. **Tagesdaten statt Intraday:** Unser Overnight-Fenster (16:00 ET T−1 → 09:30 ET T) erfasst nur einen Teil des Paper-Fensters (14:00 ET T−1 → Statement); der Drift-Anteil zwischen 09:30 und dem Statement fehlt. Ein Nullbefund widerlegt das Paper daher nicht automatisch — berichtet wird, was gemessen wurde.
2. **ETF statt Index/Futures** (Tracking-Differenzen, Handelszeiten).
3. **Zeitraum:** ab Mai 1999 (Ära-Grenze der Statement-Zeiten) statt 1994, bis 2024-12-31 (Lockbox-Stichtag) statt 2011. Ein mögliches Abklingen des Effekts nach der Paper-Stichprobe wird in der Literatur diskutiert und hier schlicht mitberichtet.

## Einordnung

Alle Werte sind friktionslos gerechnete (keine Kosten/Spreads) Modelloutputs/Szenarien aus einer historischen Ereignisstudie — keine Anlageempfehlung, keine Aussage über zukünftige Kurse. Zahlen stammen ausschließlich aus committetem Code auf lokal gecachten Rohdaten (R1); Reproduktion: `uv run python -m mie.es.b3_drift report` auf dem oben genannten Commit- und Datenstand.
