"""Smoke-Tests: prüfen die Pin-Kette Umgebung → Paket → Abhängigkeiten Ende-zu-Ende."""

import sys


def test_python_version_gepinnt():
    """Läuft die gepinnte Python-Version (.python-version / requires-python == 3.13.*)?"""
    assert sys.version_info[:2] == (3, 13)


def test_import_mie():
    """Ist das Projektpaket importierbar (src-Layout korrekt installiert)?"""
    import mie

    assert mie.__version__


def test_import_pandas():
    """Ist die Runtime-Abhängigkeit pandas importierbar (Wheel auf dieser Maschine ok)?"""
    import pandas

    assert pandas.__version__
