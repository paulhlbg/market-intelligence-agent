# A2 — Quellenprüfung und Nutzungsbedingungen (manuell verfasst)

Stand: 07.07.2026 · Ergänzt den generierten Qualitätsreport `a2_kursdaten.md`.
Zahlen in diesem Dokument stammen aus dem committeten Code des Qualitätsreports (R1);
dieses Dokument ergänzt Einordnung, Nutzungsbedingungen und Empfehlungen.

## 1. Geprüfte Quellen — Ergebnisübersicht

| Quelle | Ergebnis | Zugriffsweg | Kosten |
|---|---|---|---|
| **Tiingo** | ✅ nutzbar | offizielle REST-API, kostenloser Key | 0 € |
| **Yahoo (yfinance)** | ✅ nutzbar (Grauzone, s. u.) | inoffizielle API via OSS-Bibliothek | 0 € |
| **Stooq** | ❌ nicht skriptbar (Stand 07.07.2026) | CSV-Endpoint | — |

### Stooq — negativer R2-Befund

Der CSV-Endpoint (`stooq.com/q/d/l/`) lieferte am 07.07.2026 bei zwei Versuchen
(mit und ohne Browser-User-Agent) statt Daten eine JavaScript-Bot-Schutz-Seite
(Proof-of-Work-Challenge). Ein programmatisches Umgehen dieser Schutzmaßnahme
kommt nicht infrage (Wille des Betreibers, ToS-Risiko). Stooq wird daher nicht
weiterverfolgt; ein späterer regulärer Neuversuch bleibt möglich.

### Yahoo via yfinance — nutzbar, aber Grauzone

- Direkte HTTP-Abrufe der Chart-API waren am 07.07.2026 rate-limitiert (HTTP 429);
  der Zugriffsweg der Bibliothek (Cookie+Crumb) funktioniert dagegen zuverlässig
  (R2-Mini-Check und Volldownload bestanden).
- **Einordnung:** yfinance (Apache-2.0-Bibliothek) nutzt eine von Yahoo nicht
  offiziell als Datendienst lizenzierte Schnittstelle. Für private
  Forschungsnutzung verbreitet, aber ohne Zusagen: Der Zugang kann jederzeit
  brechen, Datenqualität „as is".
- **Konsequenzen für dieses Projekt:** rein private, nicht-kommerzielle Nutzung;
  keine Redistribution — Rohdaten bleiben lokal (`data/raw/` ist gitignored);
  Yahoo ist nicht alleinige Quelle (Kreuzabgleich mit Tiingo); geringe
  Abruffrequenz (Volldownload = 3 Requests).

### Tiingo — offizielle API, kostenloses Kontingent

- Registrierung + API-Key kostenlos; Key liegt ausschließlich in der
  Umgebungsvariable `TIINGO_API_KEY` (nie im Repo, Übertragung nur als Header).
- **Nutzungsbedingungen (tiingo.com, gesichtet 07.07.2026):** Daten für
  persönliche/interne Nutzung; Redistribution untersagt → Rohdaten bleiben
  lokal und werden nicht committet. (Im Repo liegt lediglich ein 5-Zeilen-Fixture
  für Format-Tests.)
- **Kontingent:** Freikontingent mit Stunden-/Tageslimits laut Preisseite; unser
  Bedarf (6 Abrufe für den kompletten Volldownload, danach seltene Refreshs)
  liegt um Größenordnungen darunter. Historientiefe im Freikontingent per
  Volldownload verifiziert: SPY vollständig ab 1993-01-29.

## 2. Zentrale Befunde zu den Daten (Details im generierten Report)

1. **Deckung perfekt:** Beide Quellen liefern für alle drei Ticker exakt dieselben
   Handelstage (Überlappung = 100 %, keine Lücken gegen den NYSE-Kalender,
   keine Duplikate, keine OHLC-Verstöße).
2. **„Roh" heißt nicht überall dasselbe:** yfinance-Close ist rückwirkend
   **split-adjustiert**, Tiingo-close ist der **tatsächlich gehandelte Kurs**.
   Nachweis über Split-Termine (VOO 2013: Verhältnis exakt 0,5; QQQ 2000: 2,0).
   Für Renditeberechnungen über Split-Termine hinweg sind die Reihen daher
   nicht naiv mischbar — die Zieldefinition in A4 muss die Preisreihe exakt
   festlegen.
3. **Adjustierte Kurse weichen systematisch ab** (unterschiedliche
   Adjustierungsmethodik, wachsend mit Historientiefe; QQQ bis 2,7 %).
   Erwartbar und dokumentiert; für den Kreuzabgleich zählt der rohe Close.
4. **Toleranz-Fazit:** 0,1 % auf den rohen Close bestätigt sich als sinnvoll —
   nach Ausklammern der split-erklärten Tage bleiben nur Einzeltage
   (SPY 2, VOO 1, QQQ 16; überwiegend hochvolatile Tage bzw.
   Bruchteil-Notierung vor 2001).

## 3. Empfehlungen (Festlegung durch den Projektinhaber)

- **Quellen-Rollen:** Tiingo als Primärquelle (echte Rohkurse, explizite
  Dividenden-/Split-Felder, offizielle API), Yahoo als Kreuzabgleich-Quelle.
- **Ticker: SPY + QQQ.**
  - *SPY statt VOO:* 8 415 Handelstage ab 1993 (VOO: 3 979 ab 2010 — deckt
    weder Dotcom- noch Finanzkrise ab); SPY zudem splitfrei → sauberste Reihe.
  - *QQQ:* einziger geprüfter Nasdaq-100-Kandidat, ab 1999, ein dokumentierter
    Split (20.03.2000).
