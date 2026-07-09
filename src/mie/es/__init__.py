"""Ereignisstudie Phase B-ES: Pipeline-Bausteine (Arbeitspaket B0).

B0 stellt ausschließlich die validierte Mechanik bereit — Messgrößen
(masszahlen), Ereignistag-Loader (ereignistage) sowie Gruppenvergleich,
Bootstrap-KI, Placebo-Ziehung und Lockbox-Schutz (statistik). B0 rechnet
keine echte Ereignis-Statistik; die Tests laufen nur auf synthetischen
Daten und Mini-Fixtures. Die Auswertungen der eingefrorenen Hypothesen
(registry/hypothesen/rep_*.md) folgen erst in B1–B3
(docs/freigabeplan_b_es.md, freigegeben 09.07.2026).
"""


class EsError(ValueError):
    """Fehler in der Ereignisstudien-Pipeline; Abbruch statt stiller Reparatur."""
