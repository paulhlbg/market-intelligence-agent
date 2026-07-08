# Zieldefinitionen (Ledger)

**Stand: 08.07.2026 · Festgelegt vom Projektinhaber am 08.07.2026 (A4-Plan).**

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
