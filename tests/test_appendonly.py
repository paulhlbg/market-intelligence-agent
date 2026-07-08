"""Append-only-Wächter über die committeten CSVs dieses Repos (Wächter-Fix, Beschluss 08.07.2026).

ensure_append_only lief bisher nur beim Schreiben (append_rows) — eine nachträgliche
Änderung committeter Zeilen wäre erst beim nächsten Wochenlauf aufgefallen. Dieser
Test lässt den bestehenden Wächter bei jedem `make check` über alle vier
Append-only-Dateien des echten Repos laufen. Angehängte, noch nicht committete
Zeilen bestehen (der Wächter prüft nur, dass der Inhalt mit dem committeten Stand
beginnt) — nur veränderte oder gelöschte alte Zeilen schlagen fehl.
"""

import pytest

from mie import appendonly, ledger, registry


@pytest.mark.parametrize(
    "path",
    [
        ledger.prognosen_path(),
        ledger.aufloesungen_path(),
        registry.experimente_path(),
        registry.auswertungen_path(),
    ],
    ids=lambda p: p.name,
)
def test_append_only_echtes_repo(path):
    appendonly.ensure_append_only(path)
