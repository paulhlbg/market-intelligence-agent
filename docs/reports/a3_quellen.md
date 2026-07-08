# A3 — Quellenprüfung und Nutzungsbedingungen Termine (manuell verfasst)

Stand: 08.07.2026 · Ergänzt den generierten Qualitätsreport `a3_termine.md`.
Zahlen in diesem Dokument stammen aus dem committeten Code des Qualitätsreports (R1);
dieses Dokument ergänzt Einordnung, Nutzungsbedingungen, Uhrzeiten-Belege und Empfehlungen.

## 1. Geprüfte Quellen — Ergebnisübersicht

| Quelle | Ereignistyp | Ergebnis | Zugriffsweg | Kosten |
|---|---|---|---|---|
| **Federal Reserve** (federalreserve.gov) | FOMC | ✅ nutzbar | HTML-Kalenderseiten (aktuell + 27 Jahresseiten) | 0 € |
| **BLS** (bls.gov) | CPI | ✅ nutzbar (Auflage: Kontakt-UA) | HTML-Terminplan + Release-Archiv | 0 € |
| **FRED** (api.stlouisfed.org) | CPI (Kreuzabgleich) | ✅ nutzbar (Key seit 08.07.2026) | offizielle REST-API, kostenloser Key | 0 € |

### Federal Reserve — gemeinfreie Regierungsseite

- Werke der US-Bundesregierung sind gemeinfrei (17 U.S.C. § 105); keine
  Nutzungsbeschränkung für die Terminlisten. Abruffrequenz minimal
  (28 Seiten je Volldownload, 0,5 s Pause zwischen Requests).
- **Eigenheit:** Das HTML der aktuellen Kalenderseite ist fehlerhaft
  (überzähliges `"` in den Sitzungs-Divs) — der Parser toleriert das; bei
  künftigen Strukturänderungen bricht er absichtlich laut ab statt still
  Termine zu verlieren.

### BLS — gemeinfrei, aber Zugriffsauflage

- Inhalte gemeinfrei; BLS blockiert jedoch automatisierte Abrufe ohne
  Kontaktangabe (HTTP 403 mit Verweis auf die BLS-Richtlinie, R2-verifiziert
  am 08.07.2026). Unser User-Agent enthält daher die Kontakt-E-Mail des
  Projektinhabers; 2 Seiten je Volldownload. Das ist die dokumentierte
  Erwartung des Betreibers, kein Umgehen einer Schutzmaßnahme.

### FRED — offizielle API, verifiziert

- Endpoint `/fred/release/dates`, Release-ID 10 am 08.07.2026 per
  `/fred/release` als „Consumer Price Index" verifiziert; Key liegt als
  `FRED_API_KEY` in `~/.zprofile` (nie im Repo; FRED verlangt ihn als
  Query-Parameter, er wird aus Meta/Logs herausgehalten).
- **Deckung:** 456 Release-Termine 18.01.1990 – 10.06.2026 (Abrufparameter
  `realtime_start=1990-01-01`; früherer Start nicht geprüft, nicht benötigt).
- **Wichtig:** FREDs Release-Kalender ist eine **Obermenge** der monatlichen
  CPI-Releases (enthält auch Revisions-/Sonder-Releases, s. Abschnitt 2) und
  nennt keine Referenzmonate — als Ereignisliste bleibt BLS maßgeblich.
- FRED-ToS: persönliche/interne Nutzung des Freikontingents; wir cachen nur
  Termindaten (Fakten), keine Redistribution der API-Responses.

### Redistribution der Terminlisten

Die verarbeiteten Listen (`data/processed/fomc_termine.csv`,
`cpi_termine.csv`) sind reine Faktenlisten aus gemeinfreien Quellen und
werden committet (Beschluss im A3-Plan vom 08.07.2026). Rohe HTML/JSON-Responses
bleiben lokal (`data/raw/` ist gitignored).

## 2. Zentrale Befunde (Details und Zahlen im generierten Report)

1. **Deckung FOMC:** 318 Termine 1994-02-04 – 2027-12-08 (inkl. angekündigter
   Sitzungen — nützlich für die T−1-Registrierung im späteren Ledger).
   Terminarten werden unterschieden (`meeting`, `conference_call`,
   `unscheduled`, `notation_vote`, `cancelled`); nur `meeting` gilt als
   regulär (`scheduled`). Notfallaktionen (z. B. 15.03.2020, Sonntag) sind
   damit erfasst, aber abgrenzbar.
2. **Deckung CPI:** 394 Termine 1994-02-17 – 2026-12-10. Das BLS-Archiv nutzt
   vor Juni 1999 6-stellige Datums-URLs — erst deren Behandlung hebt die
   Deckung von 1999 auf Februar 1994.
3. **Deckung vs. Kursdaten:** SPY beginnt 1993-01-29; die BLS-Reihe erst
   1994-02, FRED reicht bis 1990-01 zurück (49 Termine vor BLS-Start — dieses
   Segment ist aber Ein-Quellen-Lage ohne Kreuzabgleich und ohne Referenzmonat).
   FOMC-seitig beginnt die Ereigniszeit ohnehin erst am 04.02.1994 (erstes
   Statement). Kein Blocker; Startdatum der Ereignisstudie entscheidet Phase B.
4. **Kreuzabgleich FOMC** (Kalendereintrag × Statement-Link, reguläre
   Sitzungen ab Mai 1999): 216 von 218 exakt. Die zwei Abweichungen sind
   Quellen-Eigenheiten, keine Parserfehler:
   - **15.09.2003:** Die Fed-Seite listet am 15. und 16.09.2003 zwei separate
     „Meetings"; der 15. war eine Sondersitzung ohne Statement (daher auch
     die 9 statt 8 regulären Sitzungen 2003 im Report).
   - **28.06.2007:** Der „Statement"-Link der Fed-Seite trägt einen
     URL-Tippfehler (…20070618a…); er führt per Redirect zum echten Statement
     vom 28.06.2007 (manuell verifiziert am 08.07.2026).
5. **Plausibilität als Feature:** Alle Wochenend-/Feiertagstreffer sind echte
   Historie (9/11-Umfeld, Finanzkrise, Corona-Notfallsenkung; CPI-Releases an
   Karfreitagen 2017/2020 — BLS folgt dem Bundes-, nicht dem Börsenkalender).
   Die beiden CPI-Lücken > 45 Tage sind die Government Shutdowns 1995/96 und
   Herbst 2025 (der CPI für Oktober 2025 ist ersatzlos entfallen).
6. **Kreuzabgleich CPI (bls × fred, Überlappung 1994-02 – 2026-06):**
   387 Termine exakt gleich, 1 nur bls, 20 nur fred — alle Abweichungen
   aufgeklärt:
   - **19 der 20 „nur fred" liegen im Februar** (2005–2024): FREDs Kalender
     zählt die jährliche Saisonbereinigungs-Revision des CPI als eigenes
     Release; dazu passt der Ausreißer **28.09.2000** (Sonder-Release der
     CPI-Korrektur nach dem Berechnungsfehler 2000). FRED ist also eine
     Obermenge; die BLS-Liste bleibt die maßgebliche Ereignisliste.
   - **24./25.02.1998 (1 nur fred + 1 nur bls):** derselbe Termin mit
     1 Tag Differenz. Primärbeleg (Header des BLS-Release-Textes
     `cpi_022598.txt`, gesichtet 08.07.2026): „EMBARGOED UNTIL 8:30 A.M. (EST)
     Tuesday, February 24, 1998" — **FRED hat recht, der BLS-Archiv-Dateiname
     trägt ein falsches Datum.** Einzelfall; für Phase B ist der 24.02.1998
     der korrekte Ereignistag.

## 3. Veröffentlichungs-Uhrzeiten (verifiziert vs. dokumentiert)

Alle Zeiten ET (America/New_York); UTC-Umrechnung DST-korrekt via `zoneinfo`
(14:00 ET = 19:00 UTC im Winter, 18:00 UTC im Sommer — Test in
`test_events.py`).

### FOMC-Statement — Ära-Tabelle

| Zeitraum | Statement-Zeit (ET) | Beleg |
|---|---|---|
| Feb 1994 – Mai 1999 | uneinheitlich; Statement nur bei Zinsaktion | Fed-Jahresseiten (R2: 1994 haben genau die 6 Aktionstermine einen Statement-Link); je-Termin-Uhrzeiten nicht frei verifizierbar |
| Mai 1999 – März 2011 | ≈ 14:15 | Fed-PM 24.03.2011: 12:30 sei „one hour and forty-five minutes earlier than for other FOMC meetings"; ebenso Lucca/Moench (2015) |
| Apr 2011 – Dez 2012 | 12:30 an Pressekonferenz-Terminen (SEP 14:00, PK 14:15 bzw. 14:30); übrige Sitzungen ≈ 14:15 | Fed-PM 24.03.2011 (monetary20110324a); FEDS Note 12.10.2021 |
| ab März 2013 | 14:00 (PK 14:30; seit Jan 2019 PK nach jeder Sitzung) | FEDS Note 12.10.2021; aktuelle Statement-PDFs tragen „For release at 2:00 p.m." |

**Ehrliche Grenze:** Je-Termin-Zeitstempel vor März 2013 sind nicht frei
maschinenlesbar (die HTML-Statements tragen nur „For immediate release",
R2-geprüft an 7 Terminen 2011–2013); die Tabelle ist ära-weise belegt.
Ungeplante Aktionen hatten naturgemäß unregelmäßige Uhrzeiten.
**Konsequenz für Phase B:** Für Tagesschluss-Ereignisstudien unkritisch —
alle Statement-Zeiten liegen vor Börsenschluss 16:00 ET, der Ankündigungstag
ist eindeutig der Ereignistag.

### CPI-Release

- 08:30 ET, laut BLS-Terminplan für alle 13 kommenden Termine (R2-verifiziert);
  das Release-Archiv nennt keine Uhrzeiten. Historischer Stichprobenbeleg:
  der Release-Text vom 24.02.1998 trägt „EMBARGOED UNTIL 8:30 A.M. (EST)" —
  die Konvention gilt also mindestens seit 1998; je Termin ist sie historisch
  nicht von uns verifiziert.
- **Konsequenz für Phase B:** 08:30 ET liegt vor Börsenöffnung (09:30 ET) —
  der Release-Tag ist eindeutig der Ereignistag; die Marktreaktion beginnt
  mit der Eröffnung desselben Tages.

## 4. Empfehlungen (Festlegung durch den Projektinhaber)

- **Quellen-Rollen:** Fed-Kalenderseiten als Primärquelle FOMC (einzige
  vollständige freie Quelle inkl. Sondertermin-Typologie); BLS als
  Primärquelle CPI (Referenzmonate, nur primäre Releases); FRED als
  Kreuzabgleich CPI (durchgeführt am 08.07.2026, s. Abschnitt 2.6).
- **Optionale spätere Ergänzung:** ALFRED führt „FOMC Press Release" als
  eigene Release-Serie (rid 101) — möglicher zweiter maschinenlesbarer
  FOMC-Kreuzabgleich über denselben FRED-Key; für A3 nicht nötig.
- **Für A4 (Zieldefinition):** Ereignistag-Definitionen aus Abschnitt 3
  übernehmen (FOMC: Statement vor Börsenschluss am letzten Sitzungstag;
  CPI: Release vor Börsenöffnung am Release-Tag).

## 5. Quellenverweise Uhrzeiten

- Fed-Pressemitteilung 24.03.2011 („Chairman to hold press briefings…"),
  federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm
- FEDS Note „Questions and Answers: The Information Content of the Post-FOMC
  Meeting Press Conference" (12.10.2021), federalreserve.gov/econres/notes/feds-notes/
- Lucca, D. / Moench, E. (2015): „The Pre-FOMC Announcement Drift",
  Journal of Finance 70(1) — dokumentiert die 14:15-Ära (Replikationskandidat
  laut CLAUDE.md §3.7, in A5 zu registrieren).
- BLS-Terminplanseite bls.gov/schedule/news_release/cpi.htm (Uhrzeiten-Spalte).
