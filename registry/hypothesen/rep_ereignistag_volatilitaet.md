---
experiment_id: rep_ereignistag_volatilitaet
typ: replikation
titel: Erhoehte Volatilitaet an FOMC/CPI-Tagen (Ederington/Lee 1993)
assets: SPY+QQQ
datenbasis: tiingo_tagesdaten+fomc_termine+cpi_termine
fenster_start: 1994-02-04
fenster_ende: 2024-12-31
---

# Replikationshypothese: Erhöhte Volatilität an Ereignistagen

**Status: registriert, NICHT ausgewertet.** Die Auswertung ist Phase B und
einzeln freigabepflichtig. Diese Datei ist ab Registrierung eingefroren
(SHA-256 in `registry/experimente.csv`); jede inhaltliche Änderung wäre ein
neues Experiment mit neuer `experiment_id`.

## Quelle und Literaturbefund

Ederington, L. / Lee, J. H. (1993): „How Markets Process Information: News
Releases and Volatility", *Journal of Finance* 48(4). Befund laut Paper
(Literaturangabe, keine eigene Zahl): Geplante US-Makro-Veröffentlichungen
(u. a. CPI) erhöhen die Volatilität in Zins- und Devisen-Futures deutlich,
konzentriert um den Veröffentlichungszeitpunkt (Intraday-Daten). Die
Übertragung auf Aktien-ETFs und Tagesdaten ist unsere Erweiterung; sie macht
zugleich die Projekt-Erwartung aus CLAUDE.md §2 („Volatilitätseffekte um
Ereignistage sind vermutlich nachweisbar") vorab testbar.

## Hypothese

- **H1 (gerichtet):** An FOMC- und CPI-Ereignistagen ist die Tagesvolatilität
  von SPY/QQQ höher als an Nicht-Ereignistagen.
- **H0:** Kein Unterschied.

## Operationalisierung (exakt)

- **Ereignistage und Baseline:** identisch zu `rep_announcement_day_praemie`
  (FOMC: reguläre Sitzungen, Ereignistag = letzter Sitzungstag, ab
  1994-02-04; CPI: Release-Tage inkl. Einzelfall-Korrektur 24.02.1998;
  Baseline = Handelstage ohne FOMC- und ohne CPI-Termin; Überlappungstage
  einmal gezählt und gesondert ausgewiesen).
- **Volatilitätsmaße je Handelstag T** (vorab fixiert, Tiingo-Rohfelder;
  R2-geprüft am 08.07.2026: `high`/`low` liegen im Cache für SPY und QQQ vor):
  - **(a) primär:** absolute Tages-Total-Return-Rendite `|Tages-TR|` mit
    `Tages-TR = (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1`
  - **(b) sekundär:** Intraday-Spanne `(high_T − low_T) / close_(T−1)`
    (roh; an Split-Tagen wird die Spanne mit `split_factor_T` normiert,
    analog zur TR-Formel)
- **Assets:** SPY ab 1994-02-04, QQQ ab Reihenbeginn 1999-03-10; verwendete
  Zeiträume werden je Asset berichtet (R3).

## Auswertungsplan (vorab fixiert)

- **Primäre Kennzahl:** Differenz der Mittelwerte von `|Tages-TR|`
  (Ereignis − Baseline), getrennt nach FOMC-Tagen und CPI-Tagen sowie
  zusätzlich gepoolt, je Asset, mit 95-%-Konfidenzintervall per Bootstrap.
  *(Bootstrap = wiederholtes zufälliges Neu-Ziehen mit Zurücklegen aus den
  vorhandenen Beobachtungen, um die Unsicherheit einer Kennzahl
  abzuschätzen.)*
- **Ergänzend:** Differenz der Mediane (robust — einzelne Extremtage wie
  Crash-Tage verzerren Mittelwerte von Volatilitätsmaßen stark; der Median
  ist der mittlere Wert der sortierten Beobachtungen und dagegen unempfindlich)
  und Maß (b) als Zweitmessung.
- **R3-Pflichtfelder:** n je Gruppe, Zeitraum, Baseline-Delta,
  Konfidenzintervall, Datenversion, Commit-Hash.
- **R4-Leakage-Selbsttest:** Placebo-Termine — zufällig gezogene
  Nicht-Ereignistage, **je Kalenderjahr** in gleicher Anzahl wie echte
  Termine, müssen eine Differenz ≈ 0 zeigen. Die Jahres-Schichtung ist hier
  wichtig, weil Volatilität in Clustern auftritt (turbulente Jahre heben
  jedes Tagesmaß an); ohne Schichtung könnte ein Placebo-Effekt allein aus
  ungleicher Jahresverteilung entstehen.
- Modelloutput/Szenario, keine Anlageempfehlung.

## Abweichungen vom Paper und Grenzen (ehrlich vorab)

1. **Anderes Underlying und andere Frequenz:** Paper = Zins-/Devisen-Futures,
   Intraday; wir = Aktien-ETFs, Tagesdaten. Tagesdaten verschmieren den
   Intraday-Effekt; ein schwächerer oder fehlender Befund kann daran liegen.
2. **FOMC ist im Paper nicht der zentrale Termin** (Schwerpunkt
   Arbeitsmarkt/CPI); der FOMC-Teil ist eher Erweiterung als strikte
   Replikation.
3. **Volatilitäts-Clustering** bleibt auch nach der Jahres-Schichtung eine
   Restquelle für Verzerrung; das wird bei der Interpretation ausgewiesen.
