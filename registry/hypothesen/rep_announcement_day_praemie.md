---
experiment_id: rep_announcement_day_praemie
typ: replikation
titel: Announcement-Day-Praemie an FOMC/CPI-Tagen (Savor/Wilson 2013)
assets: SPY+QQQ
datenbasis: tiingo_tagesdaten+fomc_termine+cpi_termine
fenster_start: 1994-02-04
fenster_ende: 2024-12-31
---

# Replikationshypothese: Announcement-Day-Prämie (FOMC- und CPI-Tage)

**Status: registriert, NICHT ausgewertet.** Die Auswertung ist Phase B und
einzeln freigabepflichtig. Diese Datei ist ab Registrierung eingefroren
(SHA-256 in `registry/experimente.csv`); jede inhaltliche Änderung wäre ein
neues Experiment mit neuer `experiment_id`.

## Quelle und Literaturbefund

Savor, P. / Wilson, M. (2013): „How Much Do Investors Care About
Macroeconomic Risk? Evidence from Scheduled Economic Announcements",
*Journal of Financial and Quantitative Analysis* 48(2). Befund laut Paper
(Literaturangabe, keine eigene Zahl): An Tagen geplanter US-Makro-
Ankündigungen (Inflation, Arbeitsmarkt, FOMC) sind die durchschnittlichen
Aktien-Überrenditen deutlich höher als an Tagen ohne solche Termine
(US-Daten, Paper-Stichprobe 1958–2009, Tagesdaten).

## Hypothese

- **H1 (gerichtet):** Die mittlere Tages-Total-Return-Rendite (Schluss T−1 →
  Schluss T) ist an FOMC- und CPI-Ereignistagen höher als an
  Nicht-Ereignistagen.
- **H0:** Kein Unterschied.

## Operationalisierung (exakt)

- **Ereignistage:**
  - FOMC: `data/processed/fomc_termine.csv`, nur reguläre Sitzungen
    (`meeting_type = meeting`); Ereignistag = Statement- bzw. Entscheidungstag
    = letzter Sitzungstag. Alle Äras ab 1994-02-04: Laut Ära-Tabelle
    (docs/reports/a3_quellen.md §3) liegen alle Statement-Zeiten vor
    Börsenschluss 16:00 ET, der Tagesschlusskurs enthält also die Reaktion.
    In der Ära Feb 1994 – Mai 1999 gab es Statements nur bei Zinsaktion; der
    Entscheidungstag ist trotzdem der Informationstag und bleibt in der
    Stichprobe (dokumentierte Abweichung: kein garantiertes Statement).
  - CPI: `data/processed/cpi_termine.csv`, Ereignistag = Release-Tag
    (08:30 ET, vor Börsenöffnung — Reaktion beginnt mit der Eröffnung
    desselben Tages). Bekannter Einzelfall laut docs/reports/a3_quellen.md
    §2.6: Für den Termin Februar 1998 gilt der 24.02.1998 (der
    BLS-Archiv-Dateiname trägt ein falsches Datum).
  - Fällt ein Tag in beide Listen (FOMC- und CPI-Tag), zählt er einmal als
    Ereignistag und wird zusätzlich gesondert ausgewiesen.
- **Messgröße je Handelstag T** (Tiingo-Rohfelder wie in Ziel `w1_up_v1`):
  `Tages-TR = (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1`.
- **Baseline:** Tages-TR aller Handelstage im Fenster, die weder FOMC- noch
  CPI-Ereignistage sind.
- **Assets:** SPY ab 1994-02-04 (Beginn der FOMC-Ereignisliste; CPI-Liste ab
  1994-02-17), QQQ ab Reihenbeginn 1999-03-10; je Asset wird der tatsächlich
  verwendete Zeitraum berichtet (R3).

## Auswertungsplan (vorab fixiert)

- **Primäre Kennzahl:** Differenz der Mittelwerte (Ereignis − Baseline),
  gepoolt über FOMC- und CPI-Tage, je Asset, mit 95-%-Konfidenzintervall per
  Bootstrap. *(Bootstrap = wiederholtes zufälliges Neu-Ziehen mit Zurücklegen
  aus den vorhandenen Beobachtungen, um die Unsicherheit einer Kennzahl
  abzuschätzen.)*
- **Sekundär:** dieselbe Differenz getrennt nach FOMC-Tagen und CPI-Tagen.
- **R3-Pflichtfelder:** n je Gruppe, Zeitraum, Baseline-Delta,
  Konfidenzintervall, Datenversion, Commit-Hash.
- **R4-Leakage-Selbsttest:** Placebo-Termine — zufällig gezogene
  Nicht-Ereignistage (je Kalenderjahr gleiche Anzahl wie echte Termine)
  müssen eine Differenz ≈ 0 zeigen.
- Friktionslos, Modelloutput/Szenario, keine Anlageempfehlung.

## Abweichungen vom Paper und Grenzen (ehrlich vorab)

1. **Terminset:** nur FOMC + CPI (MVP-Scope); das Paper nutzt zusätzlich den
   Arbeitsmarktbericht. Wir replizieren also nur einen Ausschnitt des
   Paper-Befunds.
2. **Rohrendite statt Überrendite:** Das Paper misst Renditen über dem
   risikofreien Zins; wir testen Tages-Total-Returns ohne Zinsabzug. Bei
   einem Horizont von einem Tag ist der risikofreie Tageszins klein, die
   Abweichung wird aber dokumentiert und bei der Interpretation genannt.
3. **ETF statt breitem Marktportfolio; Zeitraum 1994–2024 statt 1958–2009**
   (Fenster endet am Lockbox-Stichtag; QQQ erst ab 1999).
