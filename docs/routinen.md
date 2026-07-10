# Routinen

## Wöchentliche Ledger-Routine (Ziel: ≤ 15 Minuten, real ≈ 5)

Empfohlener Zeitpunkt: Wochenende oder Montag vor Börsenöffnung (Anker ist dann
der Freitags-Schlusskurs). Die Zieldefinition hängt nur am letzten verfügbaren
Schlusskurs — ein verschobener Lauf verfälscht nichts, er verschiebt nur den
Anker. Ein zweiter Lauf am selben Tag ist unschädlich (gleiche forecast_id wird
erkannt und übersprungen). BTC-Anker ist der letzte **abgeschlossene**
UTC-Kalendertag (die Kerze des laufenden Tages wird verworfen) — er kann daher
von den SPY/QQQ-Ankertagen abweichen; das ist normal.

1. `uv run python -m mie.a4_ledger weekly`
   (frischt Tiingo-Cache SPY+QQQ und Coinbase-Cache BTC auf, löst fällige
   Prognosen auf, hängt je Asset eine neue 1-Wochen-Prognose an — SPY/QQQ:
   5 Handelstage, BTC: 7 Kalendertage UTC; `TIINGO_API_KEY` muss gesetzt sein —
   und registriert FOMC/CPI-Termine der nächsten 10 Kalendertage, sofern deren
   Registrierungs-Deadline noch nicht verstrichen ist; B4,
   docs/zieldefinitionen.md)
2. Ausgabe gegenlesen: plausible Basisraten, richtige Anker-/Zieltage,
   Auflösungen nachvollziehbar, Ereignis-Meldungen (registriert/ausgesetzt/
   Deadline verpasst) plausibel.
3. `make check`
4. Committen, z. B.: `git commit -am "ledger: Wochenlauf YYYY-MM-DD (SPY, QQQ, BTC)"`

Zwischendurch: `uv run python -m mie.a4_ledger status` zeigt offene und
aufgelöste Prognosen.

### Ereigniszweig (B4): FOMC/CPI-Prognosen

Der Wochenlauf deckt Termine der nächsten 10 Kalendertage automatisch mit ab.
Liegt eine Registrierungs-Deadline **vor** dem nächsten Wochenlauf (Deadline =
Börsenschluss des letzten Handelstags vor dem Termin, i. d. R. 16:00 ET =
22:00/21:00 deutscher Zeit), gibt es den schlanken Zwischenlauf:

1. `uv run python -m mie.a4_ledger events`
   (nur Tiingo-Refresh SPY+QQQ; löst fällige Ereignis-Prognosen auf und
   registriert kommende Termine — je Termin und Asset zwei Zeilen:
   `klimatologie_ev_v0` und Referenz `klimatologie_alltage_v0`)
2. Ausgabe gegenlesen, `make check`, committen, z. B.:
   `git commit -am "ledger: Ereignislauf YYYY-MM-DD (CPI/FOMC)"`

Regeln (docs/zieldefinitionen.md): verpasste Deadline ⇒ Termin wird ehrlich
ausgelassen (kein Nachtragen); FOMC=CPI-Überlappungstage werden ausgesetzt;
Brier/Log-Loss/Kalibrierung erst nach genügend aufgelösten Ereignissen
(≈ 20/Jahr → Größenordnung ein Jahr) — bis dahin reine Buchführung.

**Merkposten (R2, jährlich ca. Dezember):** Die CPI-Terminliste reicht bis
Dez. 2026, die FOMC-Liste bis Dez. 2027 — rechtzeitig vorher per A3-Skripten
auffrischen (`uv run python -m mie.a3_termine …`, siehe docs/reports/
a3_termine.md), sonst können keine Termine mehr registriert werden.

### Wenn etwas schiefgeht

- **Tiingo oder Coinbase nicht erreichbar:** Lauf einfach später wiederholen.
  Kein stiller Quellenwechsel (docs/zieldefinitionen.md).
- **„Feed-Lücke am Zieltag" oder „Kalendertag-Lücke(n)" (BTC):** Für BTC gibt
  es keinen Ausweichtag (24/7-Handel, jeder Kalendertag zählt). Nichts
  reparieren, Projektinhaber fragen — Vorfall bekannt: der Tiingo-Krypto-Feed
  hatte am 2026-02-15 eine echte Lücke (docs/reports/a6_btc_quellen.md).
- **„Append-only verletzt":** Alte Ledger-Zeilen wurden verändert oder gelöscht.
  Nichts reparieren, `git diff ledger/` ansehen und den Projektinhaber fragen.
- **„laut NYSE-Kalender Handelstag, fehlt aber im Tiingo-Cache":** Entweder
  Datenlücke oder eine Börsenschließung, die der gepinnte Kalender noch nicht
  kennt. Der Projektinhaber entscheidet nach der Nachtrag-Regel in
  docs/zieldefinitionen.md; das Skript weicht nie still aus.

Alle ausgegebenen Wahrscheinlichkeiten sind Modelloutputs (Klimatologie-
Basisrate) — Szenario-Rechnungen, keine Anlageempfehlung.

## Experiment registrieren (Registry v0, bei Bedarf)

Regel R6 / Verfassung §4: **registrieren vor auswerten**. Die Auswertungen
selbst sind Phase B und einzeln freigabepflichtig — diese Routine registriert
nur.

1. Hypothesen-Datei `registry/hypothesen/<experiment_id>.md` schreiben:
   Frontmatter (`experiment_id`, `typ` = replikation|exploration, `titel`,
   `assets`, `datenbasis`, `fenster_start`, `fenster_ende`; Werte kommafrei)
   plus Volltext (Quelle, Hypothese, exakte Operationalisierung,
   Auswertungsplan, Grenzen). Das Auswertungsfenster endet vor dem
   Lockbox-Stichtag 01.01.2025 — reicht es hinein, lässt sich der Eintrag
   später nur als Lockbox-Auswertung auswerten (Zähler, maximal 2).
2. Aktuellen Code-Stand committen (die Registry-Zeile referenziert den
   Commit-Hash).
3. `uv run python -m mie.a5_registry register registry/hypothesen/<id>.md`
   (erst mit `--dry-run` gegenlesen). Ab dem Registrieren ist die Datei per
   SHA-256 eingefroren — Änderungswunsch = neues Experiment mit neuer ID.
4. `make check`, dann committen, z. B.:
   `git commit -am "registry: <experiment_id> registriert"`

Zwischendurch: `uv run python -m mie.a5_registry status` zeigt alle
Experimente samt Ergebnisfeld und Lockbox-Zähler;
`uv run python -m mie.a5_registry check` prüft Schema, Hypothesen-Hashes,
Referenzen und Lockbox-Limit (läuft auch in den Tests mit).
