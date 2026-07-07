# Projektverfassung — Market Intelligence Engine

**Stand: 07.07.2026 · Status: Abgenommen am 07.07.2026 (Gegenlesen durch den Projektinhaber)**

## 0. Präambel

Diese Verfassung bündelt die dauerhaften Grundregeln des Projekts auf 1–2 Seiten. Sie konsolidiert ausschließlich die in `CLAUDE.md` protokollierten Beschlüsse und stellt keine neuen Regeln auf. `CLAUDE.md` bleibt die maßgebliche operative Arbeitsgrundlage; bei Widerspruch zwischen beiden Dokumenten wird gestoppt und der Projektinhaber gefragt — nichts wird still entschieden. Änderungen an dieser Verfassung nur mit ausdrücklicher Zustimmung des Projektinhabers.

## 1. Ziele

- **Langfristig:** eine Market Intelligence Engine, die aus Marktdaten kalibrierte Wahrscheinlichkeiten für Kursverhalten ableitet — ohne jede Trade-Ausführung. *(Kalibriert heißt: Wenn das Modell „70 %“ sagt, tritt das Ereignis auf lange Sicht auch in etwa 70 % dieser Fälle ein.)*
- **Erster Schritt (ES-MVP, beschlossen 06.07.2026):** eine historische Ereignisstudie zu US-Makro-Terminen (FOMC-Zinsentscheide, US-CPI-Veröffentlichungen) auf zwei ETFs (1× S&P 500, 1× Nasdaq 100; Ticker-Festlegung erst nach Datenprüfung), plus ein sofort startender wöchentlicher Prognose-Ledger mit Klimatologie als Modell v0. *(Klimatologie heißt: Als Prognose dient schlicht die historische Basisrate — wie oft das Ereignis in der Vergangenheit eingetreten ist.)*
- **Ehrliche Evidenz als Zielbestandteil:** Ein nachweisbarer Prognose-Edge ist Bonus, nicht Erwartung. Volatilitätseffekte um Ereignistage sind vermutlich nachweisbar, ein Richtungseffekt ist vermutlich ≈ 0. Auch Null- und Negativbefunde werden vollständig berichtet, nicht schöngeredet.

## 2. Nicht-Ziele

- **Keine Trade-Ausführung, keine Broker-Anbindung** — auch nicht als Prototyp. **Keine Anlageempfehlungen und keine Empfehlungssprache:** Alle Ausgaben sind als Szenario, Wahrscheinlichkeit oder Modelloutput gekennzeichnet; nie „sicher“, nie Kauf-/Verkaufsaufforderungen.
- **Nicht im MVP:** Earnings-Ereignisse. Bitcoin ist nicht Teil der Ereignisstudie (höchstens optionaler, jederzeit ersatzlos streichbarer Zweig im Wochen-Ledger).
- **Teil des Zielsystems, aber erst nach separater Freigabe** (nicht anfangen, auch nicht „nebenbei“): News-/Social-Pipelines und Forward-Collector, Portfolio-Modul, Apps/Interfaces, Stop-/Ziel-/Exit-Simulationen, Intraday, Derivate, jedes Modelltraining (auch logistische Regression), Walk-forward-Backtest-Harness.

## 3. Regeln R1–R6 (verbindlich für jede Ausgabe)

- **R1 — Keine Zahl ohne Code und Daten.** Jede berichtete Zahl stammt aus ausgeführtem, committetem Code auf lokal gecachten Rohdaten. Keine „geschätzten“ Ergebnisse aus dem Kopf.
- **R2 — Datenverfügbarkeit wird verifiziert.** Jede Behauptung zur Datenverfügbarkeit wird per Mini-Skript geprüft, bevor sie ins Design eingeht.
- **R3 — Pflichtfelder je Ergebnis:** n (Stichprobengröße), Zeitraum, Baseline-Delta (Abstand zur einfachen Vergleichsbasis), Konfidenzintervall, Datenversion, Commit-Hash. *(Ein Konfidenzintervall ist die Spanne, in der der wahre Wert angesichts der begrenzten Datenmenge plausibel liegt — es macht die Unsicherheit einer Zahl sichtbar.)*
- **R4 — Leakage-Selbsttests.** *(Leakage: Die Auswertung nutzt versehentlich Information, die zum Prognosezeitpunkt noch nicht verfügbar war — Ergebnisse wirken dann unecht gut.)* Pflichttests: Placebo-Termine (zufällige Pseudo-Termine müssen Effekt ≈ 0 zeigen), Shuffle-Tests (wird die zeitliche Zuordnung durch Mischen zerstört, muss der Effekt verschwinden), synthetische Daten mit bekannter richtiger Antwort.
- **R5 — LLM-Analysen nur forward.** LLM-basierte Text-/Sentiment-Analysen nur auf Daten, die selbst forward gesammelt wurden (ab jetzt laufend selbst erhoben, nicht rückwirkend beschafft). Im ES-MVP noch nicht relevant, gilt aber ab sofort.
- **R6 — Experiment-Registry.** Jeder Modell-, Feature- und Auswertungsversuch wird geloggt; Multiplizität fließt in die Bewertung ein. *(Multiplizität: Wer viele Versuche macht, findet rein zufällig irgendwann „signifikant“ aussehende Treffer — deshalb zählt die Anzahl der Versuche bei der Bewertung mit.)*

## 4. Registry-Regel

- **Registrieren vor Auswerten:** Jeder Versuch erhält vor der Auswertung einen Registry-Eintrag mit Hypothese, Registrierdatum, Daten/Zeitfenster, leerem Ergebnisfeld (bis zur Auswertung) und Lockbox-Auswertungszähler.
- **Replikationshypothesen** — bekannte publizierte Effekte (z. B. Pre-FOMC-Drift, Lucca/Moench 2015) — werden vorab registriert und strikt getrennt von freier Exploration geführt. Eine gescheiterte Replikation wird berichtet, nicht wegdiskutiert.

## 5. Lockbox-Regel (Stichtag 01.01.2025)

*(Zweck einer Lockbox: Ein Teil der Daten bleibt während der gesamten Entwicklung unangetastet, damit am Ende eine Bewertung auf Daten möglich ist, die die Entwicklung nicht beeinflusst haben.)*

- Daten ab dem 01.01.2025 sind gesperrt für Exploration, Feature-Entwicklung und historische Auswertung.
- Auswertung des Lockbox-Zeitraums maximal 2×, nur mit vorregistrierten Hypothesen und eingefrorenem Auswertungscode; der Zähler wird in der Registry geführt.
- Ergebnisse aus dem Lockbox-Zeitraum werden stets gekennzeichnet als „pseudo-out-of-sample — Entwicklerwissen (Mensch und KI-Trainingsdaten) reicht in den Zeitraum hinein“.
- Live-Prognosen dürfen selbstverständlich aktuelle Daten als Input nutzen. Höchste Evidenzstufe bleibt der forward geführte Ledger.

## 6. Freigabe-Workflow

- Gearbeitet wird **paketweise in der Reihenfolge A0–A6** (Phase A, freigegeben am 06.07.2026). Alles jenseits von A0–A6 — insbesondere die Ereignis-Auswertungen selbst (Phase B-ES), jedes Modelltraining, jeder Forward-Collector — ist **einzeln freigabepflichtig**.
- **Zyklus je Paket:** kurzer Plan (Was/Warum/Dateien/Abhängigkeiten/Tests/Risiken) → Bestätigung durch den Projektinhaber → Umsetzung → Abschlussmeldung (Zusammenfassung, Dateien, Tests, offene Risiken, Einschränkungen, nächster Schritt, Commit-Message-Vorschlag) → Aktualisierung der Umsetzungsstand-Zeile in `CLAUDE.md`.
- **Jede Abweichung vom beschriebenen Umfang: stoppen und fragen.** Ebenso bei Unklarheit oder Widerspruch — keine stillen Annahmen.
- **Abbruchschwelle (V3):** Überschreitet ein Paket das 1,5-Fache seiner Aufwandsschätzung, wird gestoppt und dem Projektinhaber Verkleinern oder Neuplanen vorgeschlagen.
- **Rahmen:** Budgetziel 0 € (Reserve 30–50 €/Monat nur nach Rücksprache), lokale Entwicklung auf dem MacBook, GitHub free, ca. 10–15 h/Woche.
