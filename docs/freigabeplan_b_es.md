# Freigabeplan Phase B-ES — Ereignisstudie FOMC/CPI auf SPY+QQQ

**Status: Freigegeben am 09.07.2026 durch den Projektinhaber (B0–B3).**
**B4 ist zurückgestellt — noch nicht entschieden, wird nicht begonnen.**
Vorgelegt und angenommen am 09.07.2026; dieses Dokument hält den freigegebenen
Umfang unverändert fest. Jede Abweichung davon: stoppen und fragen
(CLAUDE.md §6, Verfassung §6).

## Kontext

Phase A (A0–A6) ist abgeschlossen. In A5 wurden drei Replikationshypothesen registriert und eingefroren (SHA-256 in `registry/experimente.csv`, Commit `c7f67f0`) — **registriert, nicht ausgewertet**. Phase B-ES ist die erste tatsächliche Auswertung: die historische Ereignisstudie zu FOMC/CPI auf SPY+QQQ. Die Datenbasis liegt vollständig lokal gecacht und committet vor: Tiingo-Tagesdaten (SPY ab 1993-01-29, QQQ ab 1999-03-10, Stand 07.07.2026, `docs/reports/a2_kursdaten.md`), Terminlisten (`data/processed/fomc_termine.csv`: 318 Termine ab 1994-02-04; `cpi_termine.csv`: 394 Termine ab 1994-02-17, `docs/reports/a3_termine.md`). **Es ist kein neuer Datenabruf nötig** — die Auswertungsfenster enden am 31.12.2024, weit innerhalb der Caches.

## 1. Was ausgewertet wird — und was nicht

**Ausgewertet werden ausschließlich die drei registrierten Replikationshypothesen**, in dieser Reihenfolge:

| # | experiment_id | Paper | Frage (Kurzform) | Fenster |
|---|---|---|---|---|
| B1 | `rep_ereignistag_volatilitaet` | Ederington/Lee 1993 | Ist die Tagesvolatilität an FOMC/CPI-Tagen höher als an Baseline-Tagen? | 1994-02-04 – 2024-12-31 |
| B2 | `rep_announcement_day_praemie` | Savor/Wilson 2013 | Ist die mittlere Tagesrendite an FOMC/CPI-Tagen höher? | 1994-02-04 – 2024-12-31 |
| B3 | `rep_pre_fomc_drift` | Lucca/Moench 2015 | Ist die Overnight-Rendite in den FOMC-Tag hinein positiv erhöht? | 1999-05-01 – 2024-12-31 |

Reihenfolge-Begründung: B1 zuerst, weil der Volatilitätseffekt laut Erwartungsrahmen (§2) am ehesten nachweisbar ist — findet selbst B1 nichts, ist das ein Warnsignal für die Pipeline, nicht nur ein Nullbefund.

**Abgrenzung Replikation vs. freie Exploration (R6/§3.7):**
- Maßgeblich sind die **eingefrorenen** Hypothesen-Dateien (`registry/hypothesen/rep_*.md`). Ausgewertet wird exakt, was dort vorregistriert steht — nicht mehr.
- Jede Analyse darüber hinaus (andere Fenster, andere Maße, Subgruppen, „mal eben schauen ob…") ist **freie Exploration**: eigener Registry-Eintrag mit `typ: exploration` **vor** der Auswertung, separate Freigabe. In dieser Freigabe **nicht enthalten**.
- Fällt beim Auswerten eine Idee für eine Zusatzanalyse an, wird sie notiert (Registry-Kandidat), aber nicht gerechnet.

**Explizit nicht Teil dieser Freigabe:** Lockbox-Auswertung (Zähler bleibt 0 von 2), jedes Modelltraining, Walk-forward-Harness, Earnings, BTC (bleibt reiner Ledger-Zweig), News-/Forward-Collector.

## 2. Methodik je Hypothese

Die Methodik ist in den eingefrorenen Hypothesen-Dateien bereits exakt vorregistriert; dieser Plan fasst sie zusammen und ändert sie nicht (jede inhaltliche Änderung = neues Experiment mit neuer ID).

**B1 — Volatilität (`rep_ereignistag_volatilitaet`):**
- Maße: primär |Tages-Total-Return|, sekundär Intraday-Spanne (high−low)/close_(T−1), Tiingo-Rohfelder, Split-normiert.
- Primäre Kennzahl: Mittelwert-Differenz Ereignis − Baseline, getrennt FOMC/CPI und gepoolt, je Asset, 95-%-Bootstrap-KI; ergänzend Median-Differenz (robust gegen Crash-Tage).
- R4: Placebo-Termine, je Kalenderjahr geschichtet (wichtig wegen Volatilitäts-Clustering).

**B2 — Announcement-Day-Prämie (`rep_announcement_day_praemie`):**
- Maß: Tages-Total-Return (Schluss T−1 → Schluss T), TR-Formel aus `w1_up_v1`.
- Primäre Kennzahl: Mittelwert-Differenz Ereignis − Baseline, gepoolt über FOMC+CPI, je Asset, 95-%-Bootstrap-KI; sekundär getrennt nach FOMC/CPI. Überlappungstage (FOMC=CPI) einmal gezählt, gesondert ausgewiesen.
- R4: Placebo-Termine, jahresgeschichtet.

**B3 — Pre-FOMC-Drift (`rep_pre_fomc_drift`):**
- Maß: Overnight-Total-Return (Schluss T−1 → Eröffnung T), nur reguläre FOMC-Sitzungen ab Mai 1999 (Ära-Grenze der Statement-Zeiten); CPI-Tage aus der Baseline entfernt (08:30-ET-Release liegt im Overnight-Fenster).
- Primäre Kennzahl: Mittelwert-Differenz je Asset (SPY = Replikation, QQQ = Erweiterung), 95-%-Bootstrap-KI.
- R4: Placebo-Termine. Bekannte Grenze (vorab dokumentiert): Tagesdaten erfassen nur einen Teil des Paper-Fensters — ein Nullbefund widerlegt das Paper nicht automatisch.

**Metriken-Einordnung (§3.5, ehrlich):** Brier-Score inkl. Zerlegung, Log-Loss und Kalibrierungskurven sind Metriken für **Wahrscheinlichkeitsprognosen**. Die drei Replikationstests sind vorregistrierte **Mittelwertvergleiche mit Bootstrap-KI** — dort wären Brier & Co. nicht anwendbar, und die eingefrorenen Pläne werden nicht nachträglich umgebaut. Die §3.5-Metriken greifen (a) im laufenden Wochen-Ledger (unverändert) und (b) im optionalen Paket B4, sobald ereignisbezogene Wahrscheinlichkeitsprognosen forward registriert werden. Trefferquoten nur ergänzend mit Binomial-KI und nur, wo vorregistriert — alles andere wäre post-hoc und würde als solches gekennzeichnet oder unterlassen.

**R4-Selbsttests (vollständig):**
- **Placebo-Termine:** je Hypothese vorregistriert (s. o.) — zufällige Pseudo-Termine müssen Differenz ≈ 0 zeigen.
- **Shuffle-Test und synthetische Daten:** als **Pipeline-Validierung in B0** (siehe unten). Beide testen den Auswertungscode, nicht die Hypothesen — sie ändern die eingefrorenen Dateien nicht. Synthetisch: Datensatz mit eingebautem bekannten Effekt (Pipeline muss ihn finden) und ohne Effekt (Pipeline muss ≈ 0 liefern). Shuffle: nach Zerstören der Datum-Zuordnung muss jeder Effekt verschwinden.

## 3. Umgang mit der Lockbox (§3.6)

- Alle drei Fenster enden am **31.12.2024** — vor dem Lockbox-Stichtag 01.01.2025. Das ist in den eingefrorenen Hypothesen-Dateien so fixiert.
- Der Auswertungscode bekommt einen **harten Cutoff**: Zeilen nach 2024-12-31 werden vor jeder Berechnung verworfen; ein Test prüft, dass die Auswertung Daten aus dem Lockbox-Zeitraum verweigert bzw. nachweislich ausschließt.
- **Lockbox-Zähler bleibt 0 von 2.** Eine spätere Lockbox-Auswertung (z. B. dieselben Fragen auf 2025+) wäre ein eigener Beschluss mit eigener Vorregistrierung und eingefrorenem Code — nicht Teil dieser Freigabe, hier nur als Möglichkeit benannt.
- `registry/auswertungen.csv` ist bereits Append-only-gewacht (`tests/test_appendonly.py`, alle vier CSVs).

## 4. Arbeitspakete (einzeln abnehmbar, V3-Schwelle je Paket)

Je Paket gilt der Zyklus aus Verfassung §6: kurzer Paket-Plan → Bestätigung → Umsetzung → Abschlussmeldung → Umsetzungsstand-Zeile aktualisieren. Überschreitet ein Paket das 1,5-Fache der Schätzung: Stopp, Verkleinern/Neuplanen vorschlagen.

**B0 — Auswertungs-Pipeline + R4-Validierung (Schätzung: 5–7 h)**
- Neues Modul (z. B. `src/mie/es/`): Ereignistag-Markierung (FOMC regulär/CPI inkl. Einzelfall 24.02.1998, Überlappungslogik), Messgrößen (Tages-TR, Overnight-TR, |TR|, Spanne — Wiederverwendung der TR-Logik aus `src/mie/ledger/klimatologie.py`, soweit passend), Gruppenbildung Ereignis/Baseline, Bootstrap-KI, Placebo-Ziehung (jahresgeschichtet, geseedet), Lockbox-Cutoff.
- Tests: Handrechnung auf Mini-Fixture, synthetische Daten mit bekannter Antwort (Effekt/kein Effekt), Shuffle-Test, Lockbox-Cutoff-Test.
- **Wichtig gegen Peeking:** B0 arbeitet ausschließlich auf synthetischen/Fixture-Daten. Die erste echte Ereignis-Statistik entsteht erst in B1 — so kann die Pipeline nicht (auch nicht unbewusst) auf das gewünschte Ergebnis zugeschnitten werden.
- Abnahme: `make check` grün, alle R4-Pipeline-Tests grün, noch keine echte Zahl.

**B1 — Auswertung `rep_ereignistag_volatilitaet` (Schätzung: 2–3 h)**
**B2 — Auswertung `rep_announcement_day_praemie` (Schätzung: 2–3 h)**
**B3 — Auswertung `rep_pre_fomc_drift` (Schätzung: 2–3 h)**
- Je Paket identischer Ablauf: eingefrorenen Plan ausführen → Placebo-Test → Report `docs/reports/b_es_<experiment_id>.md` mit allen R3-Pflichtfeldern (n je Gruppe, Zeitraum, Baseline-Delta, KI, Datenversion = SHA-256 der Rohdateien, Commit-Hash) → Append-Eintrag in `registry/auswertungen.csv` (`lockbox = nein`) → Commit.
- Ergebnis wird berichtet, wie es ausfällt — auch Null- oder Negativbefund, inkl. der vorab dokumentierten Grenzen (Tagesdaten statt Intraday, ETF statt Index, Teil-Terminset).

**B4 (optional, separat entscheidbar — Stand 09.07.2026: zurückgestellt) — Ereignisbezogene Forward-Ledger-Prognosen (Schätzung: 3–4 h)**
- Erst ab Phase-B-Freigabe zulässig (docs/zieldefinitionen.md: schon die Basisrate über historische Ereignistage ist Ereignisstudien-Statistik). Inhalt: neue Zieldefinition (z. B. Ereignistag-Rendite > 0), Modell v0 = ereigniskonditionale Klimatologie, Registrierung spätestens T−1 vor jedem kommenden FOMC/CPI-Termin (§3.4), Auflösung wie gehabt. **Hier** greifen Brier/Log-Loss/Kalibrierung forward.
- Kann ohne Schaden weggelassen oder verschoben werden; B0–B3 hängen nicht davon ab.

**Gesamtschätzung Kern (B0–B3): 11–16 h ≈ 1–1,5 Wochen** bei 10–15 h/Woche. Größte Unsicherheit: B0. Budget: 0 € (keine neuen Abhängigkeiten, keine neuen Abrufe geplant).

## 5. Ehrlicher Erwartungsrahmen (§2) und Multiplizität (R6)

- **B1 (Volatilität): vermutlich nachweisbar** — deckt sich mit Literatur und Projekterwartung; Tagesdaten verschmieren den Intraday-Effekt, der Befund kann also schwächer ausfallen als im Paper.
- **B2/B3 (Richtungseffekte): vermutlich ≈ 0 oder fragil.** Die Papers berichten positive Effekte, aber: unsere Fenster/Instrumente weichen ab (Tagesdaten, ETF, Teil-Terminset), und für den Pre-FOMC-Drift wird in der Literatur ein Abklingen nach der Paper-Stichprobe diskutiert. Eine gescheiterte Replikation wird berichtet, nicht wegdiskutiert — sie ist ein reguläres, verwertbares Ergebnis.
- **Multiplizität:** Es werden ausschließlich die vorregistrierten Vergleiche gerechnet (3 Hypothesen × 2 Assets plus die vorregistrierten Sekundär-Splits) und **alle vollständig berichtet** — kein Auswahl-Reporting. Die Zahl der Tests wird im Report ausgewiesen und fließt in die Bewertung ein.
- Alle Ergebnisse sind friktionslos gerechnete Modelloutputs/Szenarien, keine Anlageempfehlung.

## 6. Verifikation (je Paket, vor Abnahme)

1. `make check` (Tests + Lint + Append-only-Wächter) grün auf frischem Stand.
2. B0: synthetischer Datensatz mit bekanntem Effekt wird gefunden, ohne Effekt ≈ 0; Shuffle zerstört den Effekt; Handrechnung auf Mini-Fixture stimmt; Lockbox-Cutoff-Test greift.
3. B1–B3: Placebo-Differenz ≈ 0 (KI überdeckt 0); Report enthält alle R3-Felder; `auswertungen.csv`-Eintrag vorhanden; keine Daten nach 2024-12-31 in der Auswertung (Test).
4. Dieser Plan liegt committet als `docs/freigabeplan_b_es.md` (Nachvollziehbarkeit); nach jedem Paket Umsetzungsstand-Zeile in CLAUDE.md aktualisieren.

## 7. Offene Punkte außerhalb dieser Freigabe

- **Coinbase-Market-Data-Terms manuell im Browser gegenlesen** (Projektinhaber; docs/reports/a6_btc_quellen.md §2) — unabhängig von B-ES, bleibt offen.
- Wochenroutine SPY+QQQ+BTC läuft unverändert weiter (nächster Lauf laut docs/routinen.md).
