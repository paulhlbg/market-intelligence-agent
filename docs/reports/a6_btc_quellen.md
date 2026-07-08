# A6 — BTC-Quellenprüfung und Nutzungsbedingungen (manuell verfasst)

Stand: 08.07.2026 · Ergänzt den generierten Qualitätsreport `a6_btc_kursdaten.md`.
Alle Zahlen in diesem Dokument stammen aus dem committeten Code des
Qualitätsreports (R1, `uv run python -m mie.a6_btc_quellen report`); dieses
Dokument ergänzt Einordnung, Nutzungsbedingungen und den Quellen-Beschluss.

## 1. Geprüfte Quellen — Ergebnisübersicht

| Quelle | Ergebnis | Zugriffsweg | Kosten |
| --- | --- | --- | --- |
| Coinbase Exchange (Public API) | **Primärquelle** (Beschluss unten) | REST ohne Key, paginiert | 0 € |
| Tiingo Krypto-Endpoint | Kreuzabgleich | REST mit TIINGO_API_KEY | 0 € (Freikontingent) |
| Kraken Public OHLC | **nicht getestet** (Reserve) | — | — |
| CoinGecko | **nicht getestet** (Reserve) | — | — |

Kraken/CoinGecko wurden nicht angefasst, weil die zweite geprüfte Quelle
(Coinbase) bestanden hat; zu beiden gibt es hier bewusst **keine** Aussagen
(R2: ungeprüft bleibt Vermutung).

## 2. Befunde je Quelle

### Coinbase Exchange — Primärquelle

- **Verfügbarkeit (verifiziert):** BTC-USD-Tageskerzen lückenlos
  **2015-07-20 bis heute** (n = 4007, Duplikate 0, Kalendertag-Lücken 0,
  OHLC-Verstöße 0, Close ≤ 0: 0). Kerzenformat
  `[time, low, high, open, close, volume]`, `time` = Bucket-Start in
  Epochensekunden **UTC** (Tagesbucket = UTC-Kalendertag). Die Kerze des
  laufenden UTC-Tages ist enthalten und noch nicht final.
- **Zugriff:** öffentliche Market-Data-Endpoints ohne Key; maximal 300 Kerzen
  je Request → Paginierung (~14 Requests für die volle Historie); im Modul
  bewusst gedrosselt (0,15 s Pause).
- **Nutzungsbedingungen:** Die API-Doku (docs.cdp.coinbase.com, gesichtet
  08.07.2026) bindet die Nutzung der Exchange-Market-Data-API an die „Market
  Data Terms of Use" (coinbase.com/legal/market_data). Die Terms-Seite selbst
  ist nur im Browser lesbar (HTTP 403 für Skripte) —
  **Handlungspunkt: einmal manuell im Browser gegenlesen.** Vorsorglich gilt
  dieselbe konservative Haltung wie bei Tiingo: Rohdaten bleiben lokal
  (`data/raw/` ist gitignored), im Repo liegt nur ein 5-Kerzen-Fixture für
  Format-Tests.

### Tiingo Krypto-Endpoint — Kreuzabgleich

- **Verfügbarkeit (verifiziert):** Tagesbars ab **2011-08-19** (n = 5404),
  aber **34 Kalendertag-Lücken**: 30 in 2011, 3 im Januar 2015 und **eine
  echte Feed-Lücke am 2026-02-15** (per Direktabruf bestätigt — kein
  Abruf-Artefakt). Bars mit Stempel `00:00:00+00:00` = UTC-Kalendertage;
  laufender UTC-Tag enthalten.
- **Endpoint-Eigenheiten (verifiziert, im Modul gelöst):** lange Zeiträume
  werden gekappt (Volldownload ab 2011 endete zunächst bei 2024-09-09);
  `endDate` ist je nach Daten-Ära inklusiv oder exklusiv → das Modul ruft
  paginiert mit um einen Tag überlappenden Fenstern ab.
- **Feed-Identität:** Tiingos Meta nennt den Ticker „Bitcoin **Tether**
  (BTC/USD)" — vermutlich ein Multi-Venue-Aggregat inklusive USDT-Märkten
  (Vermutung, nicht weiter verifiziert; für die Kreuzabgleich-Rolle
  unerheblich, für eine Primärquellen-Rolle ein Minus).
- **Nutzungsbedingungen:** wie in A2 gesichtet (a2_quellen.md §2): Daten für
  persönliche/interne Nutzung, Redistribution untersagt → Rohdaten lokal,
  nur 5-Datensatz-Fixture im Repo. Key ausschließlich aus `TIINGO_API_KEY`.

## 3. Kreuzabgleich und UTC-Befund

Zahlen: `a6_btc_kursdaten.md` (Commit dort im Kopf). Überlappung n = 4006;
|Δ|rel am Close: Median 0,05 %, p95 5,07 %, Max 21,66 %; **1117 Tage über der
Start-Toleranz 0,5 % — der letzte am 2023-05-07**, seither liegen alle Tage
innerhalb der Toleranz. Einordnung: Die großen Abweichungen stammen aus der
frühen, illiquiden Ära (Aggregat vs. Einzelbörse, 2015–2017); sie werden
ausgewiesen, nicht wegdiskutiert. Für den Forward-Ledger sind sie ohne Belang,
weil die Zieldefinition `btc_w1_up_v1` auf dem Coinbase-Feed selbst definiert
ist. Die Toleranz 0,5 % bleibt als Arbeitsstand dokumentiert; im
Beobachtungsfenster seit Mitte 2023 wird sie durchgehend eingehalten.

**UTC-Close-Befund:** Beide Quellen liefern Tagesbars mit UTC-Mitternachtsgrenze
(Tiingo: ISO-Stempel `00:00+00:00`; Coinbase: Epochensekunden exakt auf
Mitternacht). Die enge Übereinstimmung der Closes seit Mitte 2023 stützt
identische Bucket-Grenzen. Die UTC-Close-Konvention ist schriftlich fixiert in
`docs/zieldefinitionen.md` (Ziel `btc_w1_up_v1`).

## 4. Beschluss und Konsequenzen

**Beschluss des Projektinhabers vom 08.07.2026: Coinbase ist Primärquelle des
BTC-Ledger-Zweigs; Tiingo-Krypto dient nur dem Kreuzabgleich.** Gründe:
lückenlose Reihe, klar definierter BTC-USD-Spot-Close an einer echten Börse,
null Qualitätsbefunde — gegenüber Tiingos echter Lücke am 2026-02-15,
Aggregat-Charakter und Endpoint-Macken. Preis: kürzere Historie (ab 2015 statt
2011); für die Klimatologie-Basisrate mit ~4000 Tagesfenstern ausreichend.

Konsequenzen:

- Trainingsbasis der Basisrate = Coinbase-Reihe ab 2015-07-20 (lückenlos;
  wird bei jedem Wochenlauf geprüft — bei Lücke stoppt die Routine).
- Fällt ein künftiger Zieltag auf eine Feed-Lücke: stoppen und Projektinhaber
  fragen — kein Ausweichtag, kein stiller Quellenwechsel
  (docs/zieldefinitionen.md).
- R3-Felder: n = 4007 · Zeitraum 2015-07-20 – 2026-07-08 · Baseline-Delta
  n. a. · Konfidenzintervall n. a. (reine Quellenprüfung, keine
  Effektschätzung) · Datenversionen (sha256) und Commit: siehe
  `a6_btc_kursdaten.md`.
