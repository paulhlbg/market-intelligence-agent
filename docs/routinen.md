# Routinen

Alle Befehle werden aus dem Repo-Wurzelverzeichnis ausgeführt. Die
Kalender-Erinnerungen (Abschnitt unten) verweisen auf die passenden Abschnitte
dieser Datei — bei jeder Erinnerung gilt: diese Anleitung öffnen, Schritt für
Schritt abarbeiten, bei Unklarheit nichts still entscheiden.

| Kalender-Eintrag                     | Rhythmus                | Abschnitt hier                  |
| ------------------------------------ | ----------------------- | ------------------------------- |
| MIE: Wochenlauf Prognose-Ledger      | samstags 10:00          | Wöchentliche Ledger-Routine     |
| MIE: … Registrierungs-Deadline …     | je FOMC/CPI-Termin      | Zwischenlauf `events`           |
| MIE: FOMC=CPI … ausgesetzt           | je Überlappungstag      | (nichts zu tun, nur Hinweis)    |
| MIE: Terminabgleich Fed/BLS          | vierteljährlich         | Vierteljährlicher Terminabgleich |
| MIE: Terminlisten-Refresh …          | Dez. 2026 / Dez. 2027   | Terminlisten-Refresh            |

## Kalender-Erinnerungen (einmalig einrichten)

1. Datei erzeugen:

       uv run python -m mie.kalender

   Kein Netzzugriff; liest die versionierten Terminlisten und schreibt
   `data/processed/mie_erinnerungen.ics` (lokales Artefakt, bewusst
   unversioniert — aus Code + Terminlisten jederzeit reproduzierbar).
2. Apple Kalender öffnen → Ablage → Neuer Kalender → Namen **„MIE"** geben
   (einmalig; eigener Kalender, damit sich alles auf einmal ersetzen lässt).
3. Doppelklick auf `data/processed/mie_erinnerungen.ics` (oder Ablage →
   Importieren…) und beim Import als Zielkalender **MIE** wählen.
4. **Aktualisieren** (nach Terminlisten-Refresh oder geänderten Terminen):
   alle Einträge des Kalenders „MIE" löschen, Datei neu erzeugen (Schritt 1),
   neu importieren (Schritt 3). Die Eintrags-UIDs sind stabil, aber Löschen +
   Neuimport ist der narrensicherste Weg, Duplikate zu vermeiden.

Wenn etwas nicht klappt:

- **„Terminliste fehlt: …"** — `data/processed/fomc_termine.csv` bzw.
  `cpi_termine.csv` fehlen. Repo-Stand prüfen (`git status`); notfalls einmal
  `uv run python -m mie.a3_termine all` laufen lassen.
- **„… ist laut XNYS-Kalender kein Handelstag …"** — ein Termin fällt auf
  einen Feiertag: verschobener Termin oder Börsenschließung. Nichts still
  ändern; Ursache über den Terminabgleich klären und die Entscheidung
  dokumentieren.

## Wöchentliche Ledger-Routine (samstags, Ziel ≤ 15 Minuten, real ≈ 5)

Empfohlener Zeitpunkt: Samstag (Kalender-Serie; Anker ist der
Freitags-Schlusskurs). Die Zieldefinition hängt nur am letzten verfügbaren
Schlusskurs — ein verschobener Lauf verfälscht nichts, er verschiebt nur den
Anker. Ein zweiter Lauf am selben Tag ist unschädlich (gleiche forecast_id wird
erkannt und übersprungen). BTC-Anker ist der letzte **abgeschlossene**
UTC-Kalendertag (die Kerze des laufenden Tages wird verworfen) — er kann daher
von den SPY/QQQ-Ankertagen abweichen; das ist normal.

**Schritt 1 — Lauf** (`TIINGO_API_KEY` muss gesetzt sein):

    uv run python -m mie.a4_ledger weekly

Erwartete Ausgabe der Reihe nach (Werte variieren, Struktur nicht):

    tiingo/SPY: … Zeilen (sha256 …)
    tiingo/QQQ: … Zeilen (sha256 …)
    coinbase/BTC-USD: … Zeilen (sha256 …)

    Fällige Auflösungen: n
      <forecast_id>: TR … → outcome 0|1 (Zieltag …)

    Ereignis-Termine (FOMC/CPI, nächste 10 Kalendertage):
      … registriert / ausgesetzt / Deadline verpasst / keine Termine im Fenster

    Neue Prognosen (Modelloutputs Klimatologie, keine Anlageempfehlung): m
      <forecast_id>: P(…) = 0.… [Modell] · n = … · Anker … · Zieltag …

    Angehängt: n Auflösung(en), m Prognose(n). Jetzt: Ausgabe gegenlesen,
    `make check`, committen (docs/routinen.md).

**Schritt 2 — Gegenlesen** (Checkliste):

- Wahrscheinlichkeiten sind weder 0 noch 1 und liegen nahe den Werten der
  Vorwochen (Vergleich: letzte Zeilen in `ledger/forecasts.csv`);
  `train_n` wächst gegenüber der Vorwoche um wenige Tage.
- Ankertag SPY/QQQ = letzter Handelstag (bei Samstagslauf: Freitag);
  BTC-Anker = letzter abgeschlossener UTC-Tag (Abweichung normal).
- Zieltag: SPY/QQQ 5 Handelstage, BTC 7 Kalendertage nach dem Anker.
- Auflösungen: `outcome` ist genau dann 1, wenn der ausgewiesene TR > 0 ist.
- Ereignis-Meldungen plausibel: „registriert" nur mit Deadline in der Zukunft;
  „ausgesetzt" nur für FOMC=CPI-Tage; „Deadline verpasst" heißt ehrlich
  auslassen — NICHT nachtragen.

**Schritt 3 — Checks:**

    make check

Erwartet: ruff ohne Befund, alle Tests grün.

**Schritt 4 — Committen und pushen (Backup):**

    git commit -am "ledger: Wochenlauf YYYY-MM-DD (SPY, QQQ, BTC)"
    git push

Zwischendurch: `uv run python -m mie.a4_ledger status` zeigt offene und
aufgelöste Prognosen.

### Wenn etwas schiefgeht (Wochenlauf)

- **„TIINGO_API_KEY ist nicht gesetzt":** Key steht in `~/.zprofile`; neues
  Terminal öffnen oder `source ~/.zprofile`, dann erneut laufen lassen.
- **Tiingo oder Coinbase nicht erreichbar:** Lauf einfach später wiederholen.
  Kein stiller Quellenwechsel (docs/zieldefinitionen.md).
- **„Feed-Lücke am Zieltag" oder „Kalendertag-Lücke(n)" (BTC):** Für BTC gibt
  es keinen Ausweichtag (24/7-Handel, jeder Kalendertag zählt). Nichts
  reparieren, Ursache klären — Vorfall bekannt: der Tiingo-Krypto-Feed hatte am
  2026-02-15 eine echte Lücke (docs/reports/a6_btc_quellen.md).
- **„Append-only verletzt":** Alte Ledger-Zeilen wurden verändert oder gelöscht.
  Nichts reparieren, `git diff ledger/` ansehen und die Ursache klären, bevor
  irgendetwas committet wird.
- **„laut NYSE-Kalender Handelstag, fehlt aber im Tiingo-Cache":** Entweder
  Datenlücke oder eine Börsenschließung, die der gepinnte Kalender noch nicht
  kennt. Nachtrag-Regel in docs/zieldefinitionen.md anwenden; das Skript weicht
  nie still aus.
- **`make check` rot:** nichts committen. Fehlermeldung lesen; Tests benennen
  die verletzte Regel (Schema, Append-only, …). Keine manuellen Reparaturen am
  Ledger — Ursache klären (z. B. in der nächsten Claude-Session) und die
  Entscheidung dokumentieren.

## Zwischenlauf `events` (nur bei Deadline vor dem nächsten Wochenlauf)

Der Wochenlauf deckt Termine der nächsten 10 Kalendertage automatisch mit ab.
Nur wenn eine Registrierungs-Deadline **vor** dem nächsten Wochenlauf liegt
(Deadline = Börsenschluss des letzten Handelstags vor dem Termin, i. d. R.
16:00 ET = 22:00 deutscher Zeit; die Kalender-Erinnerung nennt die exakte
Uhrzeit), gibt es den schlanken Zwischenlauf:

1. Lauf (nur Tiingo-Refresh SPY+QQQ; löst fällige Ereignis-Prognosen auf und
   registriert kommende Termine — je Termin und Asset zwei Zeilen:
   `klimatologie_ev_v0` und Referenz `klimatologie_alltage_v0`):

       uv run python -m mie.a4_ledger events

2. Ausgabe gegenlesen (wie Wochenlauf-Schritt 2, nur Ereigniszweig), dann:

       make check
       git commit -am "ledger: Ereignislauf YYYY-MM-DD (CPI/FOMC)"
       git push

Regeln (docs/zieldefinitionen.md): verpasste Deadline ⇒ Termin wird ehrlich
ausgelassen (kein Nachtragen); FOMC=CPI-Überlappungstage werden ausgesetzt;
Brier/Log-Loss/Kalibrierung erst nach genügend aufgelösten Ereignissen
(≈ 20/Jahr → Größenordnung ein Jahr) — bis dahin reine Buchführung.

## Vierteljährlicher Terminabgleich (Fed/BLS)

Zweck: verschobene oder geänderte Termine früh bemerken. Eine Verschiebung
nach der Registrierung würde eine registrierte Prognose auf den falschen Tag
zielen lassen — historisch selten, aber die Prüfung ist billig.

1. Neu abrufen (überschreibt Roh-Cache, Report und Terminlisten-CSVs):

       uv run python -m mie.a3_termine all

2. Diff der Terminlisten ansehen:

       git diff data/processed/fomc_termine.csv data/processed/cpi_termine.csv

   - **Kein Diff:** fertig. Die aufgefrischten Reports mit committen:

         git commit -am "termine: Quartalsabgleich YYYY-MM-DD (keine Änderungen)"

   - **Diff vorhanden:** nichts still übernehmen. Ansehen, welcher Termin sich
     geändert hat. Betrifft er bereits **registrierte** Prognosen, Umgang
     bewusst entscheiden und im Commit dokumentieren (die registrierte Zeile
     bleibt append-only bestehen — sie wird nicht angefasst). Danach committen,
     `uv run python -m mie.kalender` laufen lassen und den Kalender „MIE"
     ersetzen (Abschnitt Kalender-Erinnerungen, Punkt 4).

## Terminlisten-Refresh (jährlich; Merkposten Dez. 2026 und Dez. 2027)

**Merkposten (R2):** Die CPI-Terminliste reicht bis Dez. 2026, die FOMC-Liste
bis Dez. 2027 — ohne rechtzeitigen Refresh können danach keine Termine mehr
registriert werden. Ablauf wie beim Terminabgleich (`uv run python -m
mie.a3_termine all`, Diff gegenlesen, committen; Details der Quellen:
docs/reports/a3_termine.md). Danach `uv run python -m mie.kalender` und die
neue .ics importieren (Kalender „MIE" ersetzen), damit die neuen Deadlines im
Kalender stehen.

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
