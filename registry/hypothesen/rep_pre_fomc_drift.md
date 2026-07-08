---
experiment_id: rep_pre_fomc_drift
typ: replikation
titel: Pre-FOMC-Announcement-Drift (Lucca/Moench 2015)
assets: SPY+QQQ
datenbasis: tiingo_tagesdaten+fomc_termine+cpi_termine
fenster_start: 1999-05-01
fenster_ende: 2024-12-31
---

# Replikationshypothese: Pre-FOMC-Announcement-Drift

**Status: registriert, NICHT ausgewertet.** Die Auswertung ist Phase B und
einzeln freigabepflichtig. Diese Datei ist ab Registrierung eingefroren
(SHA-256 in `registry/experimente.csv`); jede inhaltliche Änderung wäre ein
neues Experiment mit neuer `experiment_id`.

## Quelle und Literaturbefund

Lucca, D. / Moench, E. (2015): „The Pre-FOMC Announcement Drift", *Journal of
Finance* 70(1). Befund laut Paper (Literaturangabe, keine eigene Zahl): Der
S&P 500 erzielt im ca. 24-Stunden-Fenster **vor** geplanten FOMC-Statements
(ab 14:00 ET des Vortags bis unmittelbar vor der Veröffentlichung ≈ 14:15 ET)
im Mittel deutlich positive Überrenditen; nach der Veröffentlichung ist die
mittlere Rendite in etwa flach. Stichprobe des Papers: 1994–2011,
Intraday-Daten.

## Hypothese

- **H1 (gerichtet):** Die mittlere Overnight-Total-Return-Rendite in den
  FOMC-Statement-Tag hinein (Schlusskurs des Vortags → Eröffnungskurs des
  Statement-Tags) ist positiv und größer als die mittlere Overnight-Rendite
  an Baseline-Tagen.
- **H0:** Kein Unterschied zwischen Ereignis- und Baseline-Tagen.

## Operationalisierung (exakt)

- **Ereignistage:** `data/processed/fomc_termine.csv`, nur reguläre Sitzungen
  (`meeting_type = meeting`); Ereignistag T = Statement-Tag = letzter
  Sitzungstag (Konvention aus docs/zieldefinitionen.md). **Stichprobe ab Mai
  1999:** Laut Ära-Tabelle der Statement-Zeiten (docs/reports/a3_quellen.md §3)
  liegen die Statement-Zeiten seit Mai 1999 zwischen 12:30 und 14:15 ET — die
  Börseneröffnung 09:30 ET liegt damit in allen Äras **vor** dem Statement,
  das Overnight-Fenster ist garantiert frei von der Statement-Reaktion. Vor
  Mai 1999 gab es Statements nur bei Zinsaktionen mit uneinheitlichen, nicht
  frei verifizierbaren Uhrzeiten; dieser Zeitraum bleibt ausgeschlossen.
- **Messgröße je Ereignistag T** (Tiingo-Rohfelder wie in Ziel `w1_up_v1`;
  `adj_*`-Felder werden nicht verwendet):
  `Overnight-TR = (open_T + div_cash_T) · split_factor_T / close_(T−1) − 1`,
  mit T−1 = letzter Handelstag vor T im Kursframe. Dividenden/Splits wirken
  am Ex-Tag zur Eröffnung; das hält die Messgröße konsistent zur
  TR-Formel der Zieldefinition.
- **Baseline:** Overnight-TR aller übrigen Handelstage im Fenster, die weder
  FOMC- noch CPI-Ereignistage sind. CPI-Releases (08:30 ET) liegen **im**
  Overnight-Fenster und würden die Baseline sonst kontaminieren. Fällt ein
  FOMC-Statement-Tag mit einem CPI-Release-Tag zusammen, wird dieser Tag aus
  dem Haupttest ausgeschlossen und gesondert ausgewiesen.
- **Assets:** SPY = primäre Replikation (Paper-Index S&P 500); QQQ =
  sekundäre Erweiterung (nicht Teil des Paper-Befunds). QQQ-Reihe beginnt
  1999-03-10 und deckt das Fenster ab.

## Auswertungsplan (vorab fixiert)

- **Primäre Kennzahl:** Differenz der Mittelwerte (Ereignis − Baseline) je
  Asset, mit 95-%-Konfidenzintervall per Bootstrap. *(Bootstrap = wiederholtes
  zufälliges Neu-Ziehen mit Zurücklegen aus den vorhandenen Beobachtungen, um
  die Unsicherheit einer Kennzahl abzuschätzen, ohne eine Verteilungsform
  anzunehmen.)*
- **R3-Pflichtfelder:** n je Gruppe, Zeitraum, Baseline-Delta,
  Konfidenzintervall, Datenversion, Commit-Hash.
- **R4-Leakage-Selbsttest:** Placebo-Termine — gleich viele zufällig gezogene
  Nicht-Ereignistage (gleiches Fenster, je Kalenderjahr gleiche Anzahl wie
  echte Termine) müssen eine Differenz ≈ 0 zeigen.
- Simulierte Renditen sind friktionslos (keine Kosten/Spreads) und werden so
  gekennzeichnet; Modelloutput/Szenario, keine Anlageempfehlung.

## Abweichungen vom Paper und Grenzen (ehrlich vorab)

1. **Tagesdaten statt Intraday:** Unser Overnight-Fenster (16:00 ET T−1 →
   09:30 ET T) erfasst nur einen Teil des Paper-Fensters (14:00 ET T−1 →
   Statement); der Drift-Anteil zwischen 09:30 und dem Statement fehlt. Ein
   Nullbefund widerlegt das Paper daher nicht automatisch — berichtet wird,
   was gemessen wurde.
2. **ETF statt Index/Futures** (Tracking-Differenzen, Handelszeiten).
3. **Zeitraum:** ab Mai 1999 (Ära-Grenze der Statement-Zeiten) statt 1994,
   bis 2024-12-31 (Lockbox-Stichtag 01.01.2025). Das Paper endet 2011; ein
   mögliches Abklingen des Effekts nach der Paper-Stichprobe wird in der
   Literatur diskutiert und würde von uns schlicht mitberichtet.
