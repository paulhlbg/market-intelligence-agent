# Routinen

## Wöchentliche Ledger-Routine (Ziel: ≤ 15 Minuten, real ≈ 5)

Empfohlener Zeitpunkt: Wochenende oder Montag vor Börsenöffnung (Anker ist dann
der Freitags-Schlusskurs). Die Zieldefinition hängt nur am letzten verfügbaren
Schlusskurs — ein verschobener Lauf verfälscht nichts, er verschiebt nur den
Anker. Ein zweiter Lauf am selben Tag ist unschädlich (gleiche forecast_id wird
erkannt und übersprungen).

1. `uv run python -m mie.a4_ledger weekly`
   (frischt den Tiingo-Cache auf, löst fällige Prognosen auf, hängt je Asset
   eine neue 1-Wochen-Prognose an; `TIINGO_API_KEY` muss gesetzt sein)
2. Ausgabe gegenlesen: plausible Basisrate, richtige Anker-/Zieltage,
   Auflösungen nachvollziehbar.
3. `make check`
4. Committen, z. B.: `git commit -am "ledger: Wochenlauf YYYY-MM-DD (SPY, QQQ)"`

Zwischendurch: `uv run python -m mie.a4_ledger status` zeigt offene und
aufgelöste Prognosen.

### Wenn etwas schiefgeht

- **Tiingo nicht erreichbar:** Lauf einfach später wiederholen. Kein stiller
  Quellenwechsel (docs/zieldefinitionen.md).
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
