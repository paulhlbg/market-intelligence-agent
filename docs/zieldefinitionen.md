# Zieldefinitionen (Ledger)

**Stand: 10.07.2026 · `w1_up_v1`/`klimatologie_v0` festgelegt vom Projektinhaber
am 08.07.2026 (A4-Plan) · `btc_w1_up_v1` festgelegt am 08.07.2026 (A6) ·
`fomc_on_up_v1`/`cpi_d1_up_v1`/`klimatologie_ev_v0`/`klimatologie_alltage_v0`
festgelegt am 10.07.2026 (B4-Plan, Entscheidungen a–d des Projektinhabers).**

Jede Prognose im Ledger verweist über `target_id` auf genau eine Definition in
dieser Datei. Definitionen sind unveränderlich: Eine inhaltliche Änderung ergibt
eine **neue** ID (`…_v2`); alte IDs bleiben stehen, damit alte Ledger-Zeilen
exakt interpretierbar bleiben.

## Ziel `w1_up_v1` — „steigt in einer Woche" (Assets: SPY, QQQ)

**In einem Satz:** Die Prognose ist die Wahrscheinlichkeit, dass der
Total-Return des ETF über die nächsten 5 Handelstage positiv ist.

- **Preisquelle:** ausschließlich **Tiingo-Rohdaten** (Primärquelle laut A2):
  roher Schlusskurs `close` plus die expliziten Felder `div_cash`
  (Bar-Dividende je Anteil am Ex-Tag, sonst 0) und `split_factor`
  (Split-Verhältnis am Ex-Tag, sonst 1). Der adjustierte Kurs `adj_close` wird
  **nicht** verwendet — er wird bei jeder neuen Dividende rückwirkend neu
  berechnet, dieselbe historische Woche bekäme je nach Abrufdatum andere Werte
  (widerspricht stabiler Datenversion, R3; vgl. docs/reports/a2_quellen.md §2).
  Fällt Tiingo aus: Lauf verschieben bzw. stoppen und den Projektinhaber
  fragen — kein stiller Quellenwechsel.
- **Anker:** `anchor_date` = letzter zum Erstellzeitpunkt im Tiingo-Cache
  verfügbare Handelstag; `anchor_close` = dessen roher Schlusskurs.
- **Zieltag:** `target_date` = der **5. NYSE-Handelstag nach** `anchor_date`
  (Kalender XNYS via `pandas-market-calendars`, wie in A2).
- **Zielgröße — Total-Return:** *(Total-Return = Kursveränderung inklusive
  Dividenden, als würde jede Ausschüttung sofort wieder angelegt.)* Über die
  Handelstage t = anchor_date+1 … target_date:

  `TR = Π_t [ (close_t + div_cash_t) · split_factor_t / close_(t−1) ] − 1`

  Splits sind damit exakt neutralisiert (z. B. QQQ 2:1 am 20.03.2000), Dividenden
  gehen am Ex-Tag ein. Die Formel wird per Test gegen eine Handrechnung und
  gegen das `adj_close`-Verhältnis auf einem echten Fixture plausibilisiert.
- **Binäres Ziel:** 1, wenn `TR > 0`; sonst 0 (exakt 0 zählt als „nicht
  gestiegen").
- **Nachtrag-Regel (unvorhergesehene Börsenschließung):** Fällt der bei
  Erstellung berechnete `target_date` nachträglich aus (z. B. Trauertag wie am
  05.12.2018), gilt der Schlusskurs des **nächsten tatsächlichen Handelstags
  danach**; der tatsächlich verwendete Tag wird als `resolution_date`
  protokolliert. Fehlt dagegen ein regulärer Handelstag im Tiingo-Cache
  (Datenlücke laut Kalender): stoppen und den Projektinhaber fragen — kein
  stilles Ausweichen.

## Modell `klimatologie_v0` (Basisrate)

*(Klimatologie = als Prognose dient schlicht die historische Basisrate: der
Anteil der Fälle, in denen das Ziel in der Vergangenheit eingetreten ist.)*

- Für **jeden** Handelstag t im Tiingo-Cache, für den t+5 Handelstage vorliegen,
  wird das Ziel nach `w1_up_v1` berechnet (überlappende Fenster).
- Wahrscheinlichkeit = Anteil der Fälle mit Ziel = 1 über **alle zum
  Prognosezeitpunkt verfügbaren Daten** (je Asset, ab Reihenbeginn). Daten ab
  01.01.2025 sind als Live-Prognose-Input ausdrücklich erlaubt
  (Lockbox-Regel, CLAUDE.md §3.6) — gesperrt ist Exploration/Auswertung,
  nicht der Modellinput.
- Im Ledger dokumentiert je Prognose: `train_n` (Anzahl Fenster),
  `train_start`/`train_end` (Zeitraum), `data_version` (SHA-256 der
  Tiingo-Rohdatei), `code_commit`.

## Ziel `btc_w1_up_v1` — „steigt in einer Woche" (Asset: BTC · Horizont-Label `w1_7cd`)

**In einem Satz:** Die Prognose ist die Wahrscheinlichkeit, dass der
Coinbase-BTC-USD-Tagesschlusskurs in 7 Kalendertagen (UTC) über dem
Anker-Schlusskurs liegt.

BTC ist **nicht** Teil der Ereignisstudie (CLAUDE.md §3.2) — nur Wochen-Ledger.
Quellen-Beschluss des Projektinhabers vom 08.07.2026:
docs/reports/a6_btc_quellen.md §4.

- **Preisquelle:** ausschließlich **Coinbase-Exchange-Rohdaten**
  (BTC-USD-Tageskerzen; Primärquelle laut A6). **UTC-Close-Konvention:** Ein
  „Tag" ist der UTC-Kalendertag (Kerzen-Bucket 00:00–24:00 UTC); der
  „Tagesschlusskurs" ist der Close dieser Tageskerze, also der letzte Kurs vor
  Mitternacht UTC. Kein NYSE-Kalender, keine Zeitzonen-/Sommerzeitfragen.
  Tiingo-Krypto dient nur dem Kreuzabgleich. Fällt Coinbase aus: Lauf
  verschieben bzw. stoppen und den Projektinhaber fragen — kein stiller
  Quellenwechsel.
- **Keine Adjustierung:** BTC kennt keine Dividenden und keine Splits; ein
  adj_close-Äquivalent existiert nicht. Rechnerisch wird die
  Total-Return-Formel von `w1_up_v1` mit `div_cash = 0` und
  `split_factor = 1` wiederverwendet — sie reduziert sich exakt auf
  `close_ende / close_start − 1`.
- **Anker:** `anchor_date` = letzter **abgeschlossener** UTC-Kalendertag im
  Coinbase-Cache — die Kerze des laufenden UTC-Tages ist noch nicht final und
  wird verworfen; `anchor_close` = Close dieses Tages.
- **Zieltag:** `target_date` = `anchor_date` + **7 Kalendertage (UTC)**;
  BTC handelt 24/7. Eigenes Horizont-Label **`w1_7cd`** (`w1_up_v1`/`w1_5td`
  werden nicht wiederverwendet: 5 Handelstage ≠ 7 Kalendertage).
- **Binäres Ziel:** 1, wenn Rendite > 0; exakt 0 zählt als „nicht gestiegen".
- **Lücken-Regel:** Fehlt der Zieltag im Cache, obwohl spätere Tage vorliegen
  (Feed-Lücke): stoppen und den Projektinhaber fragen — **kein Ausweichtag**,
  anders als bei `w1_up_v1` gibt es keine „unvorhergesehene Börsenschließung",
  jeder Kalendertag zählt. Liegt der Zieltag schlicht noch nicht im Cache:
  Prognose bleibt offen.
- **Modell `klimatologie_v0` für BTC:** Basisrate = Anteil der überlappenden
  **7-Kalendertage-Fenster** mit Rendite > 0 über alle zum Prognosezeitpunkt
  verfügbaren abgeschlossenen Tage der Coinbase-Reihe (Beginn 2015-07-20;
  Lockbox-Regel wie gehabt — Live-Input erlaubt). Die Reihe wird bei jedem
  Lauf auf Kalendertag-Lücken geprüft; bei Lücke stoppt die Routine, denn nur
  bei lückenloser Reihe gilt 7 Zeilen = 7 Kalendertage. Dokumentiert je
  Prognose: `train_n`, `train_start`/`train_end`, `data_version` (SHA-256 der
  Coinbase-Rohdatei), `code_commit`.

## Ereignistag-Konventionen (für spätere ereignisbezogene Prognosen)

Übernommen aus docs/reports/a3_quellen.md §3; in A4 nur schriftlich fixiert —
ereignisbezogene Ledger-Einträge beginnen erst mit der Phase-B-Freigabe, denn
schon die Basisrate über historische Ereignistage wäre eine
Ereignisstudien-Statistik.

- **FOMC:** Ereignistag = Statement-Tag = letzter Sitzungstag (`date` in
  `data/processed/fomc_termine.csv`). Alle Statement-Zeiten liegen vor
  Börsenschluss 16:00 ET → der Tages-Schlusskurs des Ereignistags enthält die
  Reaktion. Als regulär gilt nur `meeting_type = meeting` (`scheduled = True`).
- **CPI:** Ereignistag = Release-Tag (`date` in
  `data/processed/cpi_termine.csv`), Veröffentlichung 08:30 ET **vor**
  Börsenöffnung → die Marktreaktion beginnt mit der Eröffnung desselben Tages.
- **Registrierung:** ereignisbezogene Prognosen spätestens **T−1** vor dem
  Termin (CLAUDE.md §3.4).

## Gemeinsame Regeln der Ereignis-Ziele (B4, festgelegt 10.07.2026)

Gelten für `fomc_on_up_v1` und `cpi_d1_up_v1`; Umsetzung in
`src/mie/ledger/ereignis.py`.

- **Registrierungs-Deadline (strenger als „T−1"):** Beide Messfenster beginnen
  am Börsenschluss des letzten Handelstags vor dem Ereignistag T. `created_utc`
  muss deshalb nachweislich **vor dem Börsenschluss dieser Vortages-Session**
  liegen — echte Schlusszeit laut XNYS-Kalender (`pandas-market-calendars`),
  womit auch Early-Close-Tage (13:00 ET) korrekt behandelt sind. „Spätestens
  T−1" ist damit stets miterfüllt. Eine verpasste Deadline führt dazu, dass der
  Termin ausgelassen und im Lauf ausgewiesen wird — **kein Nachtragen**.
- **Anker-Semantik (abweichend von `w1_up_v1`, ausdrücklich):**
  `anchor_date`/`anchor_close` = letzter zum Registrierzeitpunkt im
  Tiingo-Cache verfügbarer Handelstag — reine Dokumentation des Datenstands.
  Das Messfenster ergibt sich **allein** aus `target_id` + Ereignistag;
  `target_date` = Ereignistag T.
- **Überlappungsregel (Entscheidung c):** Fällt ein FOMC-Statement-Tag mit
  einem CPI-Release-Tag zusammen, wird für diesen Tag **keine**
  Ereignis-Prognose registriert (aussetzen + ausweisen; konsistent mit der
  eingefrorenen B3-Hypothese, die Überlappungstage ausschließt). Die
  Wochenprognose `w1_up_v1` läuft unverändert weiter.
- **Handelstag-Voraussetzung:** T muss laut XNYS-Kalender Handelstag sein,
  sonst stoppen und Projektinhaber fragen. Wird ein bereits registrierter
  Termin nachträglich verschoben (Fed/BLS), bleibt die Zeile stehen
  (Append-only); die Auflösung stoppt dann mit Fehler — Entscheidung liegt
  beim Projektinhaber, nichts wird still repariert.
- **Auflösung:** sobald der Ereignistag im Tiingo-Cache vorliegt;
  `realized_return` = Zielgröße des Ereignistags (auf 6 Stellen gerundet),
  `outcome` = 1 genau dann, wenn > 0, `resolution_date` = T. Es gibt **keinen
  Ausweichtag**: Fehlt T im Cache, obwohl spätere Tage vorliegen, oder fehlt
  die Vortages-Session im Cache (Fensterbeginn), wird abgebrochen — stoppen
  und Projektinhaber fragen. Preisquelle und Ausfallregel wie `w1_up_v1`
  (nur Tiingo-Rohfelder, kein stiller Quellenwechsel).

## Ziel `fomc_on_up_v1` — „Overnight in den FOMC-Tag hinein positiv" (Assets: SPY, QQQ · Horizont-Label `ev_on`)

**In einem Satz:** Die Prognose ist die Wahrscheinlichkeit, dass der
Overnight-Total-Return vom Schlusskurs des letzten Handelstags vor dem
FOMC-Statement-Tag zur Eröffnung des Statement-Tags positiv ist.

- **Ereignistag T:** FOMC-Statement-Tag laut Ereignistag-Konventionen (oben);
  nur reguläre Sitzungen (`meeting_type = meeting` in
  `data/processed/fomc_termine.csv`).
- **Zielgröße — Overnight-Total-Return** (Tiingo-Rohfelder wie `w1_up_v1`,
  Formel identisch zur eingefrorenen B3-Hypothese `rep_pre_fomc_drift` und zu
  `src/mie/es/masszahlen.py`):

  `Overnight-TR = (open_T + div_cash_T) · split_factor_T / close_(T−1) − 1`

  mit T−1 = letzter Handelstag vor T.
- **Binäres Ziel:** 1, wenn `Overnight-TR > 0`; sonst 0 (exakt 0 zählt als
  „nicht gestiegen").
- **Motivation:** direkter Forward-Test des in B3 bestätigten
  Pre-FOMC-Drift-Befunds (docs/reports/b_es_rep_pre_fomc_drift.md) —
  Entscheidung (a) des Projektinhabers vom 10.07.2026.

## Ziel `cpi_d1_up_v1` — „CPI-Release-Tag endet positiv" (Assets: SPY, QQQ · Horizont-Label `ev_d1`)

**In einem Satz:** Die Prognose ist die Wahrscheinlichkeit, dass der
Tages-Total-Return des CPI-Release-Tags (Schluss Vortag → Schluss
Release-Tag) positiv ist.

- **Ereignistag T:** CPI-Release-Tag laut Ereignistag-Konventionen (oben;
  Veröffentlichung 08:30 ET vor Börsenöffnung, der Tagesschluss enthält die
  Reaktion); Terminliste `data/processed/cpi_termine.csv` inkl. der
  Einzelfall-Korrektur 24.02.1998 (docs/reports/a3_quellen.md §2.6).
- **Zielgröße — Tages-Total-Return** (Tagesformel von `w1_up_v1`):

  `Tages-TR = (close_T + div_cash_T) · split_factor_T / close_(T−1) − 1`

  mit T−1 = letzter Handelstag vor T.
- **Binäres Ziel:** 1, wenn `Tages-TR > 0`; sonst 0.

## Modell `klimatologie_ev_v0` (ereigniskonditionale Basisrate)

*(Wie `klimatologie_v0`, aber bedingt auf Ereignistage: Als Prognose dient der
Anteil der historischen Ereignistage desselben Typs, an denen die Zielgröße
positiv war. Kein Modelltraining.)*

- **Trainingsmenge je Ereignistyp und Asset** (Entscheidung d,
  hypothesenkonsistent):
  - FOMC (`fomc_on_up_v1`): reguläre Statement-Tage **ab 1999-05-01**
    (Statement-Zeiten-Ära, wie `rep_pre_fomc_drift`).
  - CPI (`cpi_d1_up_v1`): Release-Tage ab Beginn der Terminliste (Feb 1994);
    für QQQ faktisch ab Reihenbeginn 1999-03-10.
  - Jeweils **ohne** FOMC=CPI-Überlappungstage (Überlappungsregel oben);
    Ereignistage ohne Kurszeile (vor Reihenbeginn) fallen heraus.
- **Expandierendes Fenster:** alle zum Registrierzeitpunkt im Cache
  verfügbaren Ereignistage. Daten ab 01.01.2025 sind als Live-Prognose-Input
  ausdrücklich erlaubt (Lockbox-Regel, CLAUDE.md §3.6) — gesperrt ist
  Exploration/Auswertung, nicht der Modellinput; ausgegeben wird nur die eine
  Basisrate mit n und Zeitraum, keine weiteren Aufschlüsselungen.
- **Dokumentiert je Prognose:** `train_n` (Anzahl verwendeter historischer
  Ereignistage), `train_start`/`train_end` (erster/letzter verwendeter
  Ereignistag), `data_version` (SHA-256 der Tiingo-Rohdatei), `code_commit`.

## Modell `klimatologie_alltage_v0` (unkonditionale Referenz-Basisrate)

*(Vergleichslatte laut Freigabeplan B4: dieselbe Zielgröße, aber Basisrate
über ALLE Handelstage der Reihe statt nur über Ereignistage.)*

- Anteil aller Handelstage der Reihe (ab Reihenbeginn, expandierend,
  Live-Input wie oben), an denen die Zielgröße positiv war;
  `train_start`/`train_end` = erster/letzter Tag der Messreihe.
- Je Termin und Asset wird **zusätzlich** zur `klimatologie_ev_v0`-Prognose
  eine Referenzzeile registriert (`forecast_id`-Suffix `_ref`, gleiche
  `target_id`, gleiches Fenster). Der spätere paarweise
  Brier-/Log-Loss-/Kalibrierungs-Vergleich „ereigniskonditional vs.
  Klimatologie" ist damit forward registriert statt nachträglich
  rekonstruiert.
- **Ehrliche Einordnung:** Bei ≈ 20 Terminen/Jahr (8 FOMC + 12 CPI) werden
  diese Metriken erst nach rund einem Jahr ansatzweise aussagekräftig; bis
  dahin ist der Ereignis-Ledger reine Buchführung. Alle Wahrscheinlichkeiten
  sind Modelloutputs (Klimatologie-Basisraten) — Szenario-Rechnungen, keine
  Anlageempfehlung.
