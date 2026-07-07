# Market Intelligence Engine (MIE)

Forschungsprojekt: aus Marktdaten kalibrierte Wahrscheinlichkeiten für Kursverhalten ableiten — ohne jede Trade-Ausführung. Alle Ausgaben sind Szenarien/Wahrscheinlichkeiten/Modelloutputs, **keine Anlageberatung**.

Erster Schritt (ES-MVP): historische Ereignisstudie zu US-Makro-Terminen (FOMC, CPI) auf zwei ETFs, plus ein wöchentlicher Prognose-Ledger mit Klimatologie als Modell v0.

## Voraussetzungen

- macOS (entwickelt auf Apple Silicon), `make` (vorinstalliert) und [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Kein eigenes Python nötig: uv installiert die gepinnte Version (3.13) selbst

## Setup und Checks (je ein Befehl)

```sh
make setup   # Umgebung exakt aus uv.lock reproduzieren (uv sync --frozen)
make check   # Lint + Format-Check (ruff) und Tests (pytest)
```

## Datenquellen (A2)

```sh
uv run python -m mie.a2_kursdaten download   # Rohdaten cachen (SPY, VOO, QQQ × yahoo, tiingo)
uv run python -m mie.a2_kursdaten report     # Qualitäts-/Kreuzabgleich-Report generieren
```

Für die Quelle Tiingo wird ein kostenloser API-Key benötigt (https://www.tiingo.com):

```sh
export TIINGO_API_KEY=…   # nur in der Shell setzen — nie committen
```

## Struktur

| Pfad | Zweck |
|---|---|
| `data/raw/`, `data/processed/` | lokale Datencaches — nicht versioniert |
| `ledger/` | Append-only-Prognose-Ledger (versioniert) |
| `registry/` | Experiment-Registry (versioniert) |
| `src/mie/` | Python-Paket |
| `tests/` | Tests |
| `docs/` | Projektverfassung u. a. |

## Verbindliche Grundlagen

- [docs/verfassung.md](docs/verfassung.md) — Projektverfassung: Ziele/Nicht-Ziele, Regeln R1–R6, Registry- und Lockbox-Regel, Freigabe-Workflow
- [CLAUDE.md](CLAUDE.md) — maßgebliche operative Arbeitsgrundlage des Projekts
