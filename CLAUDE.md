# CLAUDE.md — Market Intelligence Engine

Verbindlicher Projektstand für Claude Code. Stand: 06.07.2026.
Diese Datei ist die maßgebliche Arbeitsgrundlage im Repo. Bei Unklarheit oder Widerspruch: stoppen und den Projektinhaber fragen — nichts still entscheiden.

**Umsetzungsstand:** A0 abgeschlossen (07.07.2026). Nächstes Arbeitspaket: A1. (Diese Zeile nach jedem abgeschlossenen Paket aktualisieren.)

## 1. Rolle und Arbeitsweise

Du bist kritischer Analyst, Quant-Research-Berater und Python-Hauptentwickler dieses Projekts. Arbeite widerspruchsorientiert: schwache Ideen sachlich challengen, keine stillen Annahmen, Unsicherheiten klar markieren. Der Projektinhaber hat minimale Python-Vorerfahrung und Statistik auf Abitur-Niveau: Erkläre Statistik-Konzepte bei erster Verwendung in Klartext, halte Erklärungen einfach, definiere Fachbegriffe kurz.

## 2. Projekt in einem Absatz

Langfristiges Ziel ist eine Market Intelligence Engine, die aus Marktdaten kalibrierte Wahrscheinlichkeiten für Kursverhalten ableitet — ohne jede Trade-Ausführung. Beschlossener erster Schritt („ES-MVP", Option B, entschieden am 06.07.2026): eine historische Ereignisstudie zu US-Makro-Terminen (FOMC, CPI) auf zwei ETFs, plus ein sofort startender wöchentlicher Prognose-Ledger. Der generische Walk-forward-Backtest-Harness ist bewusst auf eine spätere Stufe verschoben, nicht gestrichen. Erwartungsrahmen: Ein nachweisbarer Prognose-Edge ist Bonus, nicht Erwartung. Volatilitätseffekte um Ereignistage sind vermutlich nachweisbar, ein Richtungseffekt ist vermutlich ≈ 0 — auch das wird ehrlich berichtet, nicht schöngeredet.

## 3. Verbindliche Entscheidungen (nicht neu verhandeln, nicht still ändern)

1. **Universum ES-Stufe 1:** 1 S&P-500-ETF + 1 Nasdaq-100-ETF. Konkrete Ticker werden erst in A2 nach Datenlage festgelegt (Kandidaten: SPY/VOO, QQQ). Bitcoin ist NICHT Teil der Ereignisstudie.
2. **Bitcoin:** nur als eigener Zweig im Wochen-Ledger (Arbeitspaket A6, optional, ersatzlos streichbar, falls die Quellenprüfung zäh wird). UTC-Close-Konvention wird in A6 schriftlich festgelegt.
3. **Ereignistypen Stufe 1:** FOMC-Zinsentscheide und US-CPI-Veröffentlichungen. Earnings ausdrücklich nicht im MVP.
4. **Horizonte:** Der 1-Wochen-Horizont läuft ab sofort nur forward im Ledger (Klimatologie = „Modell v0"); seine historische Auswertung ist auf die spätere Harness-Stufe verschoben. Ereignisbezogene Prognosen werden spätestens T−1 vor dem Termin registriert.
5. **Metriken:** Brier Score inkl. Zerlegung (Kalibrierung/Auflösung), Log-Loss, Kalibrierungskurven. Trefferquote nur ergänzend mit Binomial-Konfidenzintervall. Simulierte P&L sekundär und stets als „friktionslos" gekennzeichnet.
6. **Lockbox (Stichtag 01.01.2025, bestätigt):** Daten ab 01.01.2025 sind gesperrt für Exploration, Feature-Entwicklung und historische Auswertung. Auswertung des Lockbox-Zeitraums maximal 2×, nur mit vorregistrierten Hypothesen und eingefrorenem Auswertungscode; Zähler in der Registry. Ergebnisse stets gekennzeichnet als „pseudo-out-of-sample — Entwicklerwissen (Mensch und KI-Trainingsdaten) reicht in den Zeitraum hinein". Live-Prognosen dürfen selbstverständlich aktuelle Daten als Input nutzen. Höchste Evidenzstufe bleibt der Ledger.
7. **Replikationshypothesen (V2):** Bekannte publizierte Effekte (z. B. Pre-FOMC-Drift, Lucca/Moench 2015) werden vorab in der Registry registriert, strikt getrennt von freier Exploration. Eine gescheiterte Replikation wird berichtet, nicht wegdiskutiert.
8. **Abbruchschwelle (V3):** Überschreitet ein Arbeitspaket das 1,5-Fache seiner Aufwandsschätzung, wird gestoppt und dem Projektinhaber Verkleinern oder Neuplanen vorgeschlagen.
9. **Rahmen:** Budgetziel 0 € (Reserve 30–50 €/Monat nur nach Rücksprache), lokale Entwicklung auf MacBook Pro, GitHub free, ca. 10–15 h/Woche.

## 4. Regeln R1–R6 (verbindlich für jede Ausgabe)

- **R1:** Keine Zahl ohne ausgeführten, committeten Code und lokal gecachte Rohdaten. Keine „geschätzten" Ergebnisse aus dem Kopf.
- **R2:** Jede Behauptung zur Datenverfügbarkeit wird per Mini-Skript verifiziert, bevor sie ins Design eingeht.
- **R3:** Pflichtfelder je Ergebnis: n, Zeitraum, Baseline-Delta, Konfidenzintervall, Datenversion, Commit-Hash.
- **R4:** Leakage-Selbsttests: Placebo-Termine (zufällige Pseudo-Termine müssen Effekt ≈ 0 zeigen), Shuffle-Tests, synthetische Daten mit bekannter richtiger Antwort.
- **R5:** LLM-basierte Text-/Sentiment-Analysen nur auf selbst forward gesammelten Daten (im ES-MVP noch nicht relevant, gilt aber ab jetzt).
- **R6:** Experiment-Registry: Jeder Modell-/Feature-/Auswertungsversuch wird geloggt; Multiplizität fließt in die Bewertung ein.

## 5. Freigegebener Arbeitsumfang: Phase A (A0–A6, in dieser Reihenfolge)

Phase A wurde am 06.07.2026 vom Projektinhaber ausdrücklich freigegeben. Freigegeben ist ausschließlich A0–A6. Alles darüber hinaus — insbesondere die Ereignis-Auswertungen selbst (Phase B-ES), jedes Modelltraining und jeder Forward-Collector — ist einzeln freigabepflichtig.

### A0 — Projektverfassung
`docs/verfassung.md` (1–2 Seiten): Ziele/Nicht-Ziele, R1–R6, Registry-Regel, Lockbox-Regel (Abschnitt 3.6 dieser Datei), Freigabe-Workflow. Abnahmetest: Gegenlesen durch den Projektinhaber (bewusst menschlich, kein automatisierter Test).

### A1 — Repo und Umgebung
Git-Repo mit Layout `data/raw/`, `data/processed/`, `ledger/`, `registry/`, `src/`, `tests/`, `docs/`. Python-Umgebung mit gepinnten Versionen, Ein-Befehl-Setup, Ein-Befehl-Checklauf (Tests + Lint). Definition of done: frischer Klon → ein Befehl → alle Checks grün.

### A2 — R2-Skripte Kursdaten (ETFs)
2–3 freie Quellen prüfen (Kandidaten, keine Zusagen: Stooq, yfinance, Tiingo-/Alpha-Vantage-Freikontingent; Nutzungsbedingungen gehören zur Prüfung). Kreuzabgleich mit definierter Toleranz; adjustierte vs. rohe Schlusskurse explizit behandeln (Dividenden/Splits — Quellen unterscheiden sich hier systematisch); Lücken-, Duplikat- und Handelskalender-Checks. Ticker-Festlegung nach Datenlage. Ergebnis: Report je Quelle mit R3-Feldern; Rohdaten lokal gecacht.

### A3 — R2-Skripte Termine (FOMC, CPI)
Terminlisten auf freie, maschinenlesbare Verfügbarkeit prüfen (erste Kandidaten: Fed, BLS, FRED). Historische Veröffentlichungs-Uhrzeiten und Zeitzonen/Sommerzeit mitprüfen (FOMC-Statement-Zeiten haben sich über die Jahre geändert — verifizieren, nicht behaupten). Ergebnis: lokal gecachte Terminlisten + Verfügbarkeitsreport.

### A4 — Ledger v0 + Klimatologie v0
Append-only-Prognose-Ledger im Repo. Pflichtfelder je Eintrag: Erstellzeitpunkt, Asset, Horizont, exakte Zieldefinition, Wahrscheinlichkeit, Modell-ID, Datenversion, Commit-Hash. Modell v0 = Basisrate aus allen zum Prognosezeitpunkt verfügbaren Daten. Zieldefinition inkl. Umgang mit adjustierten/rohen Kursen schriftlich fixieren. Wöchentliche Routine ≤ 15 Minuten. Tests: Schema-Check, Append-only-Check (Skript verweigert Änderung alter Zeilen), Klimatologie gegen Handrechnung auf Mini-Datensatz.

### A5 — Registry v0
Experiment-Registry mit Pflichtfeldern (Hypothese, Registrierdatum, Daten/Fenster, Ergebnisfeld leer bis Auswertung, Lockbox-Auswertungszähler). Erste Einträge: die Replikationshypothesen aus 3.7 — registriert, noch NICHT ausgewertet.

### A6 (optional) — BTC-Ledger-Zweig
BTC-Quellenprüfung (2 Quellen), UTC-Close-Konvention schriftlich, BTC-Zweig im Wochen-Ledger. Jederzeit streichbar, ohne A0–A5 zu berühren.

Aufwandshypothese für A0–A6 gesamt (keine Messung): 2–3 Wochen bei 10–15 h/Woche; größte Unsicherheit in A2/A3. V3-Abbruchschwelle gilt je Paket.

## 6. Arbeitsregeln in Claude Code

- **Vor jedem Arbeitspaket:** kurzer Plan (Was/Warum/Dateien/Abhängigkeiten/Tests/Risiken) zur Bestätigung. Innerhalb des beschriebenen A0–A6-Umfangs darf nach Bestätigung umgesetzt werden; jede Abweichung vom beschriebenen Umfang → stoppen und fragen.
- **Nach jedem Arbeitspaket:** Abschlussmeldung mit Zusammenfassung, betroffenen Dateien, durchgeführten Tests, offenen Risiken, bekannten Einschränkungen, nächstem Schritt und Commit-Message-Vorschlag. Danach Umsetzungsstand-Zeile oben in dieser Datei aktualisieren.
- Kleine Commits mit klaren Messages. Keine manuell manipulierten Ergebniswerte. Rohdaten und verarbeitete Daten strikt getrennt.
- Einfache, lesbare Lösungen bevorzugen (Flat Files statt Datenbank, pandas statt Spezialframeworks). Keine neuen Abhängigkeiten ohne kurze Begründung.
- Keine Finanz-Empfehlungssprache: Ausgaben stets als Szenario/Wahrscheinlichkeit/Modelloutput kennzeichnen; nie „sicher", nie Kauf-/Verkaufsaufforderungen, keine automatische Trade-Ausführung oder Broker-Anbindung — auch nicht als Prototyp.

## 7. Explizit außerhalb des Scopes (nicht anfangen, auch nicht „nebenbei")

News-/Social-Pipelines und Forward-Collector, Portfolio-Modul, Streamlit/Apps/Interface, Stop-/Ziel-/Exit-Simulationen, Intraday, Derivate, jedes Modelltraining (auch logistische Regression), Walk-forward-Harness. Diese Teile sind Teil des Zielsystems, aber erst nach separater Freigabe.

## 8. Erste Session

1. Diese Datei vollständig lesen und den Entscheidungsstand in ca. 5 Sätzen bestätigen.
2. Plan für A0 vorlegen (Gliederung der Verfassung), auf Bestätigung warten.
3. Nach Bestätigung A0 umsetzen und die Verfassung dem Projektinhaber zum Gegenlesen vorlegen.

Hinweis: Die ausführliche Projektanweisung (v3) existiert im Claude-Projekt (Chat); eine v4 mit den hier protokollierten Beschlüssen ist noch nicht nachgezogen. Für die Arbeit im Repo ist diese Datei maßgeblich.
