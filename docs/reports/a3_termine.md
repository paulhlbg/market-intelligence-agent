# A3 — Verfügbarkeits- und Qualitätsreport Termine (FOMC, CPI)

**Generiert:** 2026-07-08T05:11:49+00:00 · **Commit:** `fabcd40` · Erzeugt von `uv run python -m mie.a3_termine report` — nicht von Hand editieren.

R3-Felder: n, Zeitraum und Datenversion stehen je Quelle unten. **Baseline-Delta: n. a. · Konfidenzintervall: n. a.** — reiner Verfügbarkeits-/Qualitätsreport ohne Effektschätzung; kein Kursbezug.

Ereignisdatum FOMC = letzter Sitzungstag (Bekanntgabetag); CPI = Release-Tag. Uhrzeiten sind ET (America/New_York); UTC-Ableitung DST-korrekt via zoneinfo — 14:00 ET ist je nach Datum 19:00 (Winter) oder 18:00 (Sommer) UTC. Zur Deckung: FOMC ab 1994 (erstes Fed-Statement Feb. 1994, davor kein definierter Bekanntgabezeitpunkt); CPI-Archivtiefe siehe unten.

## FOMC (Quelle „fed“)

- n = **318** Termine (davon 306 bis heute) · Zeitraum **1994-02-04 – 2027-12-08** (inkl. angekündigter Sitzungen)
- Datenversion: 28 Rohdatei(en), kombiniert sha256 `0cee2a6252297a09…`, abgerufen 2026-07-08T04:56:11+00:00 – 2026-07-08T04:56:31+00:00
- Schema-Validierung: ok
- Checks: Duplikate **0** · Wochenend-Termine **3** · an NYSE-Feiertagen **5** (2001-09-13, 2008-01-21, 2009-02-07, 2010-05-09, 2020-03-15)
- Terminarten: meeting **272** · conference_call **35** · unscheduled **5** · notation_vote **5** · cancelled **1**
- Reguläre Sitzungen je abgeschlossenem Jahr (Soll 8, 32 Jahre): Abweichungen: **2003: 9, 2020: 7**
- Kreuzabgleich Kalender × Pressemitteilungs-Links (reguläre Sitzungen ab Mai 1999, n = 218): Statement am Entscheidungstag **216** · fehlend **1** (2003-09-15) · abweichend **1** (2007-06-28 (Statement 2007-06-18))
- Vor Mai 1999 (Statement nur bei Zinsänderung üblich): 42 reguläre Sitzungen, davon 12 mit Statement am Entscheidungstag

## CPI (Quelle „bls“)

- n = **394** Termine (davon 388 bis heute) · Zeitraum **1994-02-17 – 2026-12-10** (inkl. angekündigter Termine)
- Datenversion: 2 Rohdatei(en), kombiniert sha256 `d4e56fed07bbf67a…`, abgerufen 2026-07-08T04:56:31+00:00 – 2026-07-08T04:56:31+00:00
- Schema-Validierung: ok
- Checks: Duplikate **0** · Wochenend-Termine **0** · an NYSE-Feiertagen **2** (2017-04-14, 2020-04-10)
- Lücken > 45 Tage zwischen Releases: **2** — 1995-12-14 → 1996-02-01 (49 Tage); 2025-10-24 → 2025-12-18 (55 Tage)
- Uhrzeiten laut Terminplan-Seite (nur kommende Termine): 08:30 ET × 13; das Release-Archiv nennt keine Uhrzeiten

## Kreuzabgleich CPI: bls × fred

- **übersprungen** — kein FRED-Cache vorhanden (FRED_API_KEY fehlt, Stand der Report-Generierung). Nachholen: Key setzen, dann `uv run python -m mie.a3_termine all`.

## Verarbeitete Terminlisten

- `data/processed/fomc_termine.csv` (318 Zeilen) und `data/processed/cpi_termine.csv` (394 Zeilen); Spalten siehe Modul-Doku. Gemeinfreie US-Regierungsdaten, werden committet.

