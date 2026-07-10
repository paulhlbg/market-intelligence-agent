# B2 — Replikation `rep_announcement_day_praemie`: Announcement-Day-Prämie an FOMC-/CPI-Tagen

**Generiert:** 2026-07-10T13:23:40+00:00 · **Commit:** `1855a7b` · Erzeugt von `uv run python -m mie.es.b2_praemie report` — nicht von Hand editieren.

**Frage (eingefroren):** Announcement-Day-Praemie an FOMC/CPI-Tagen (Savor/Wilson 2013) — ist die mittlere vorzeichenbehaftete Tagesrendite (Tages-TR, Schluss T−1 → Schluss T) von SPY/QQQ an FOMC-/CPI-Ereignistagen höher als an Baseline-Tagen (Handelstage ohne FOMC- und ohne CPI-Termin)? H1 gerichtet (höher), H0 kein Unterschied.

Eingefrorene Hypothese: `registry/hypothesen/rep_announcement_day_praemie.md` (sha256 `bd74b4c4eb3ef2d769e5b445cb1be770b97346a09fe4fcd152a791c6d29bb62b`, registriert 2026-07-08T21:13:22+00:00). Fenster 1994-02-04 – 2024-12-31 — endet vor dem Lockbox-Stichtag 2025-01-01; diese Auswertung ist keine Lockbox-Auswertung (lockbox=0, Zähler unverändert).

## Vorregistrierung und Umfang

- **Anzahl Tests (R6-Multiplizität):** 6 Vergleiche (davon 2 primär: Mittelwert Tages-TR gepoolt je Asset; 4 sekundär: getrennt nach FOMC/CPI) + 6 Placebo-Tests (R4-Selbsttest der Pipeline, je Asset × Gruppe nach B1-Muster — keine Hypothesenerweiterung). Alle werden vollständig berichtet — kein Auswahl-Reporting. Keine Mediane, keine Spanne, keine Zusatzmaße (nicht vorregistriert).
- **Bootstrap:** Perzentil-KI, n_boot=10000, alpha=0.05. Seeds vorab fixiert (Paketplan 10.07.2026): Basis 20260710, Vergleiche fortlaufend (Reihenfolge Asset → Gruppe), Placebos ab Basis+100 fortlaufend.
- **Maß** (Tiingo-Rohfelder, nie adj_close; Formel aus Ziel `w1_up_v1`): Tages-TR = (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1 — vorzeichenbehaftet, nicht |TR| wie in B1.
- **Gruppen:** FOMC = reguläre Sitzungen (meeting_type=meeting), Ereignistag = letzter Sitzungstag; CPI = Release-Tage inkl. Einzelfall-Korrektur 1998-02-24. Bei den getrennten Vergleichen sind die Tage des jeweils anderen Ereignistyps aus der Baseline ausgeschlossen; gepoolt = Vereinigungsmenge, Überlappungstage (FOMC- und CPI-Tag zugleich) einmal gezählt und in der Stichprobentabelle gesondert ausgewiesen.

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

## Primäres Ergebnis — Mittelwert Tages-TR gepoolt (Ereignis − Baseline)

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | gepoolt | 597 | 7183 | 0.120 % | 0.040 % | +0.079 | [-0.022; +0.180] | nein |
| QQQ | gepoolt | 499 | 5996 | 0.173 % | 0.043 % | +0.131 | [-0.025; +0.286] | nein |

## Sekundäre Ergebnisse — getrennt nach FOMC/CPI

| Asset | Gruppe | n Ereignis | n Baseline | Ereignis | Baseline | Δ (E−B) in pp | 95-%-KI in pp | KI > 0 |
|---|---|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 7183 | 0.259 % | 0.040 % | +0.219 | [+0.074; +0.367] | ja |
| SPY | CPI | 369 | 7183 | 0.068 % | 0.040 % | +0.028 | [-0.098; +0.156] | nein |
| QQQ | FOMC | 207 | 5996 | 0.353 % | 0.043 % | +0.311 | [+0.068; +0.553] | ja |
| QQQ | CPI | 308 | 5996 | 0.104 % | 0.043 % | +0.061 | [-0.130; +0.247] | nein |

## R4-Placebo (jahresgeschichtet, Mittelwert Tages-TR)

Je Kalenderjahr werden so viele zufällige Nicht-Ereignistage gezogen wie echte handelbare Termine; echte Termine (und bei getrennten Vergleichen der jeweils andere Ereignistyp) bleiben komplett außen vor. Erwartung: Differenz ≈ 0, das KI überdeckt die 0 — konstruktionsbedingt verfehlt ein 95-%-KI die 0 aber in ~5 % der Ziehungen.

| Asset | Gruppe | n Placebo | n Baseline | Δ (P−B) in pp | 95-%-KI in pp | 0 im KI |
|---|---|---|---|---|---|---|
| SPY | FOMC | 248 | 6935 | -0.063 | [-0.199; +0.069] | ja |
| SPY | CPI | 369 | 6814 | +0.013 | [-0.117; +0.135] | ja |
| SPY | gepoolt | 597 | 6586 | +0.038 | [-0.073; +0.150] | ja |
| QQQ | FOMC | 207 | 5789 | +0.138 | [-0.100; +0.380] | ja |
| QQQ | CPI | 308 | 5688 | -0.039 | [-0.211; +0.137] | ja |
| QQQ | gepoolt | 499 | 5497 | +0.043 | [-0.114; +0.200] | ja |

## Zusammenfassung (automatisch aus den Zahlen)

- 0 von 2 primären 95-%-KIs (Mittelwert Tages-TR gepoolt) liegen vollständig über 0.
- 6 von 6 Placebo-KIs überdecken die 0.

## Vorab dokumentierte Grenzen (aus der eingefrorenen Hypothese)

1. **Terminset:** nur FOMC + CPI (MVP-Scope); das Paper nutzt zusätzlich den Arbeitsmarktbericht. Wir replizieren also nur einen Ausschnitt des Paper-Befunds.
2. **Rohrendite statt Überrendite:** Das Paper misst Renditen über dem risikofreien Zins; wir testen Tages-Total-Returns ohne Zinsabzug. Bei einem Horizont von einem Tag ist der risikofreie Tageszins klein; die Abweichung gehört trotzdem in die Interpretation.
3. **ETF statt breitem Marktportfolio; Zeitraum 1994–2024 statt 1958–2009** (Fenster endet vor dem Lockbox-Stichtag; QQQ erst ab 1999).

## Einordnung

Alle Werte sind Modelloutputs/Szenarien aus einer historischen Ereignisstudie — keine Anlageempfehlung, keine Aussage über zukünftige Kurse. Zahlen stammen ausschließlich aus committetem Code auf lokal gecachten Rohdaten (R1); Reproduktion: `uv run python -m mie.es.b2_praemie report` auf dem oben genannten Commit- und Datenstand.
