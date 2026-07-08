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
