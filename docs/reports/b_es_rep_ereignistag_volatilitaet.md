# B1 — Replikation `rep_ereignistag_volatilitaet`: Volatilität an FOMC-/CPI-Tagen

**Generiert:** 2026-07-09T19:48:26+00:00 · **Commit:** `203b743` · Erzeugt von `uv run python -m mie.es.b1_volatilitaet report` — nicht von Hand editieren.

**Frage (eingefroren):** Erhoehte Volatilitaet an FOMC/CPI-Tagen (Ederington/Lee 1993) — ist die Tagesvolatilität von SPY/QQQ an FOMC-/CPI-Ereignistagen höher als an Baseline-Tagen (Handelstage ohne FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein Unterschied.

Eingefrorene Hypothese: `registry/hypothesen/rep_ereignistag_volatilitaet.md` (sha256 `0ebbd3cc6c059e38762b42f625653b7c4e94368e6cc026ddbe8aa36a14770f4e`, registriert 2026-07-08T21:13:22+00:00). Fenster 1994-02-04 – 2024-12-31 — endet vor dem Lockbox-Stichtag 2025-01-01; diese Auswertung ist keine Lockbox-Auswertung (lockbox=0, Zähler unverändert).

## Vorregistrierung und Umfang

- **Auslegungsentscheid des Projektinhabers (09.07.2026):** Der ergänzende Teil der Hypothese („Differenz der Mediane … und Maß (b) als Zweitmessung“) wird als **volles Raster** gelesen — Mediane auch für die Intraday-Spanne.
- **Anzahl Tests (R6-Multiplizität):** 24 Vergleiche (davon 6 primär: Mittelwert |Tages-TR| je Asset × Gruppierung) + 6 Placebo-Tests. Alle werden vollständig berichtet — kein Auswahl-Reporting.
- **Bootstrap:** Perzentil-KI, n_boot=10000, alpha=0.05. Seeds vorab fixiert: Basis 20260709, Vergleiche fortlaufend (Reihenfolge Asset → Maß → Statistik → Gruppe), Placebos ab Basis+100 fortlaufend.
- **Maße** (Tiingo-Rohfelder, nie adj_close): (a) primär |Tages-TR| = |(close_T + div_cash_T) · split_factor_T / close_(T−1) − 1|; (b) sekundär Spanne = (high_T − low_T) · split_factor_T / close_(T−1).
- **Gruppen:** FOMC = reguläre Sitzungen (meeting_type=meeting), Ereignistag = letzter Sitzungstag; CPI = Release-Tage inkl. Einzelfall-Korrektur 1998-02-24. Bei den getrennten Vergleichen sind die Tage des jeweils anderen Ereignistyps aus der Baseline ausgeschlossen; gepoolt = Vereinigungsmenge, Überlappungstage einmal gezählt.

## Datenversion (R3)

- Tiingo SPY (data/raw/tiingo/spy_daily.json): sha256 `f306a5612bf841e3adb71c4fac06206bdb957bece3507d62d4d37493da32da74` · Stand 2026-07-08T22:03:10+00:00 · n = 8416 Zeilen
- Tiingo QQQ (data/raw/tiingo/qqq_daily.json): sha256 `f23b7f8a5c9ec49458e8fd29ff3d4e7ea354247632f90608abe1c40080cbc4da` · Stand 2026-07-08T22:03:11+00:00 · n = 6874 Zeilen
- FOMC-Termine (data/processed/fomc_termine.csv · nur meeting_type=meeting): sha256 `31a1a014398ce458f0ce967530748a69b32626b213aef9e5c0aa2948da619091` · Stand committet (A3) · n = 272 reguläre Sitzungen
- CPI-Termine (data/processed/cpi_termine.csv · inkl. Korrektur 1998-02-24): sha256 `89450a8d335a1e85d0174152db79d9f5950d29bea809135b0b67a9ebe39b53a5` · Stand committet (A3) · n = 394 Release-Tage

## Stichprobe je Asset

| Asset | Zeitraum (verwendet) | Handelstage | FOMC | CPI | Überlappung | gepoolt |
|---|---|---|---|---|---|---|
| SPY | 1994-02-04 – 2024-12-31 | 7780 | 248 | 369 | 20 | 597 |
| QQQ | 1999-03-11 – 2024-12-31 | 6495 | 207 | 308 | 16 | 499 |

Termine im Fenster ohne Handelstag im Kursframe (nicht still verworfen):

- SPY: 2017-04-14 · 2020-04-10
- QQQ: 2017-04-14 · 2020-04-10

## Primäres Ergebnis — Mittelwert |Tages-TR| (Ereignis − Baseline)

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 7183 | 0.875 % | 0.790 % | +0.085 | [-0.017; +0.193] | nein |
| SPY | CPI | 369 | 7183 | 0.843 % | 0.790 % | +0.053 | [-0.036; +0.148] | nein |
| SPY | gepoolt | 597 | 7183 | 0.851 % | 0.790 % | +0.060 | [-0.011; +0.134] | nein |
| QQQ | FOMC | 207 | 5996 | 1.240 % | 1.146 % | +0.094 | [-0.077; +0.276] | nein |
| QQQ | CPI | 308 | 5996 | 1.150 % | 1.146 % | +0.004 | [-0.129; +0.148] | nein |
| QQQ | gepoolt | 499 | 5996 | 1.184 % | 1.146 % | +0.038 | [-0.072; +0.151] | nein |

## Ergänzende Ergebnisse

### Median |Tages-TR| (robust gegen Extremtage)

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 7183 | 0.672 % | 0.539 % | +0.133 | [+0.017; +0.242] | ja |
| SPY | CPI | 369 | 7183 | 0.587 % | 0.539 % | +0.048 | [-0.027; +0.115] | nein |
| SPY | gepoolt | 597 | 7183 | 0.603 % | 0.539 % | +0.064 | [+0.006; +0.130] | ja |
| QQQ | FOMC | 207 | 5996 | 0.777 % | 0.760 % | +0.017 | [-0.075; +0.207] | nein |
| QQQ | CPI | 308 | 5996 | 0.789 % | 0.760 % | +0.029 | [-0.044; +0.143] | nein |
| QQQ | gepoolt | 499 | 5996 | 0.784 % | 0.760 % | +0.024 | [-0.034; +0.121] | nein |

### Mittelwert Spanne

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 7183 | 1.552 % | 1.305 % | +0.247 | [+0.128; +0.370] | ja |
| SPY | CPI | 369 | 7183 | 1.368 % | 1.305 % | +0.063 | [-0.041; +0.172] | nein |
| SPY | gepoolt | 597 | 7183 | 1.435 % | 1.305 % | +0.130 | [+0.049; +0.215] | ja |
| QQQ | FOMC | 207 | 5996 | 2.188 % | 1.917 % | +0.271 | [+0.061; +0.487] | ja |
| QQQ | CPI | 308 | 5996 | 1.966 % | 1.917 % | +0.049 | [-0.124; +0.227] | nein |
| QQQ | gepoolt | 499 | 5996 | 2.057 % | 1.917 % | +0.140 | [+0.005; +0.287] | ja |

### Median Spanne

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 7183 | 1.296 % | 1.059 % | +0.237 | [+0.112; +0.348] | ja |
| SPY | CPI | 369 | 7183 | 1.091 % | 1.059 % | +0.032 | [-0.039; +0.126] | nein |
| SPY | gepoolt | 597 | 7183 | 1.169 % | 1.059 % | +0.110 | [+0.056; +0.202] | ja |
| QQQ | FOMC | 207 | 5996 | 1.686 % | 1.459 % | +0.226 | [-0.029; +0.425] | nein |
| QQQ | CPI | 308 | 5996 | 1.529 % | 1.459 % | +0.070 | [-0.117; +0.232] | nein |
| QQQ | gepoolt | 499 | 5996 | 1.589 % | 1.459 % | +0.129 | [-0.035; +0.263] | nein |

## R4-Placebo (jahresgeschichtet, Mittelwert |Tages-TR|)

Je Kalenderjahr werden so viele zufällige Nicht-Ereignistage gezogen wie echte handelbare Termine; echte Termine (und bei getrennten Vergleichen der jeweils andere Ereignistyp) bleiben komplett außen vor. Erwartung: Differenz ≈ 0, das KI überdeckt die 0 — konstruktionsbedingt verfehlt ein 95-%-KI die 0 aber in ~5 % der Ziehungen.

| Asset | Gruppe | n Placebo | n Baseline | Δ (P−B) in pp | 95-%-KI in pp | 0 im KI |
|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 6935 | -0.058 | [-0.151; +0.043] | ja |
| SPY | CPI | 369 | 6814 | -0.058 | [-0.137; +0.025] | ja |
| SPY | gepoolt | 597 | 6586 | +0.039 | [-0.038; +0.122] | ja |
| QQQ | FOMC | 207 | 5789 | -0.013 | [-0.166; +0.146] | ja |
| QQQ | CPI | 308 | 5688 | +0.020 | [-0.131; +0.189] | ja |
| QQQ | gepoolt | 499 | 5497 | -0.089 | [-0.197; +0.019] | ja |

## Zusammenfassung (automatisch aus den Zahlen)

- 0 von 6 primären 95-%-KIs (Mittelwert |Tages-TR|) liegen vollständig über 0.
- 6 von 6 Placebo-KIs überdecken die 0.

## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)

1. **Anderes Underlying und andere Frequenz:** Paper = Zins-/Devisen-Futures mit Intraday-Daten; hier Aktien-ETFs mit Tagesdaten. Tagesdaten verschmieren den Intraday-Effekt; ein schwächerer oder fehlender Befund kann daran liegen.
2. **FOMC ist im Paper nicht der zentrale Termin** (Schwerpunkt Arbeitsmarkt/CPI); der FOMC-Teil ist eher Erweiterung als strikte Replikation.
3. **Volatilitäts-Clustering** bleibt auch nach der Jahres-Schichtung eine Restquelle für Verzerrung.

## Einordnung

Alle Werte sind Modelloutputs/Szenarien aus einer historischen Ereignisstudie — keine Anlageempfehlung, keine Aussage über zukünftige Kurse. Zahlen stammen ausschließlich aus committetem Code auf lokal gecachten Rohdaten (R1); Reproduktion: `uv run python -m mie.es.b1_volatilitaet report` auf dem oben genannten Commit- und Datenstand.
