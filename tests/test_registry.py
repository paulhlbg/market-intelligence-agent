"""Registry v0: Frontmatter, Schema, Append-only-Wächter, Lockbox-Zähler (alles offline).

Wie beim Ledger wird der Append-only-Wächter gegen ein temporäres Git-Repo
getestet; zusätzlich das Hash-Pinning der Hypothesen-Dateien (registriert =
eingefroren) und das Lockbox-Limit von 2 Auswertungen.
"""

import subprocess

import pytest

from mie import registry


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _commit(repo):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "test")


FRONTMATTER = """---
experiment_id: rep_test_effekt
typ: replikation
titel: Test-Effekt (Quelle 2015)
assets: SPY+QQQ
datenbasis: tiingo_tagesdaten+fomc_termine
fenster_start: 1999-05-01
fenster_ende: 2024-12-31
---

# Hypothese

Testtext.
"""


def _write_hypothese(repo, experiment_id, fenster_ende="2024-12-31"):
    text = FRONTMATTER.replace("rep_test_effekt", experiment_id).replace("2024-12-31", fenster_ende)
    path = registry.hypothese_path(experiment_id, repo)
    path.write_text(text)
    return path


@pytest.fixture()
def repo(tmp_path):
    """Temporäres Git-Repo mit leeren Registry-Dateien + einer Hypothesen-Datei, committet."""
    (tmp_path / "registry" / "hypothesen").mkdir(parents=True)
    registry.experimente_path(tmp_path).write_text(",".join(registry.EXPERIMENT_COLUMNS) + "\n")
    registry.auswertungen_path(tmp_path).write_text(",".join(registry.EVALUATION_COLUMNS) + "\n")
    _write_hypothese(tmp_path, "rep_test_effekt")
    _git(tmp_path, "init", "-q")
    _commit(tmp_path)
    return tmp_path


def _experiment_row(repo, experiment_id="rep_test_effekt", **over):
    row = registry.registration_row(
        registry.hypothese_path(experiment_id, repo),
        now_utc="2026-07-08T12:00:00+00:00",
        commit="deadbee",
        repo_root=repo,
    )
    row.update(over)
    return row


def _evaluation_row(**over):
    row = {
        "experiment_id": "rep_test_effekt",
        "evaluated_utc": "2026-08-01T12:00:00+00:00",
        "lockbox": "0",
        "ergebnis_kurz": "nicht_repliziert",
        "report_datei": "",
        "data_version": "abc123",
        "code_commit": "deadbee",
    }
    row.update(over)
    return row


# ---------- Frontmatter ----------


def test_frontmatter_parsing(repo):
    fields = registry.parse_hypothesis_file(registry.hypothese_path("rep_test_effekt", repo))
    assert fields["experiment_id"] == "rep_test_effekt"
    assert fields["typ"] == "replikation"
    assert fields["fenster_ende"] == "2024-12-31"


def test_frontmatter_fehler(repo, tmp_path):
    path = registry.hypothese_path("rep_kaputt", repo)
    path.write_text("# kein Frontmatter\n")
    with pytest.raises(registry.RegistryError, match="Frontmatter fehlt"):
        registry.parse_hypothesis_file(path)
    path.write_text("---\nexperiment_id: rep_kaputt\n")  # nicht geschlossen
    with pytest.raises(registry.RegistryError, match="nicht geschlossen"):
        registry.parse_hypothesis_file(path)
    path.write_text(FRONTMATTER.replace("typ: replikation\n", ""))  # Pflichtschlüssel fehlt
    with pytest.raises(registry.RegistryError, match="fehlen: typ"):
        registry.parse_hypothesis_file(path)


def test_registration_row_pfadbindung(repo):
    """Dateiname muss zur experiment_id in der Frontmatter passen."""
    path = registry.hypothese_path("rep_falscher_name", repo)
    path.write_text(FRONTMATTER)  # Frontmatter sagt rep_test_effekt
    with pytest.raises(registry.RegistryError, match="muss unter"):
        registry.registration_row(path, "2026-07-08T12:00:00+00:00", "deadbee", repo)


# ---------- Schema ----------


def test_schema_experiment(repo):
    assert registry.validate_experiment_row(_experiment_row(repo)) == []
    assert any(
        "typ" in p for p in registry.validate_experiment_row(_experiment_row(repo, typ="modell"))
    )
    assert any(
        "Zeichen" in p
        for p in registry.validate_experiment_row(_experiment_row(repo, titel="a, b"))
    )
    assert any(
        "hypothese_sha256" in p
        for p in registry.validate_experiment_row(_experiment_row(repo, hypothese_sha256="xyz"))
    )
    assert any(
        "fenster_ende" in p
        for p in registry.validate_experiment_row(_experiment_row(repo, fenster_ende="1990-01-01"))
    )


def test_schema_auswertung():
    assert registry.validate_evaluation_row(_evaluation_row()) == []
    assert any(
        "lockbox" in p for p in registry.validate_evaluation_row(_evaluation_row(lockbox="2"))
    )
    assert any(
        "ergebnis_kurz" in p
        for p in registry.validate_evaluation_row(_evaluation_row(ergebnis_kurz=""))
    )


# ---------- Registrieren (append-only) ----------


def test_registrieren_und_laden(repo):
    assert registry.append_experiments([_experiment_row(repo)], repo) == 1
    df = registry.load_experiments(repo)
    assert len(df) == 1
    assert df.loc[0, "experiment_id"] == "rep_test_effekt"
    assert df.loc[0, "hypothese_sha256"] == registry.file_sha256(
        registry.hypothese_path("rep_test_effekt", repo)
    )


def test_doppelte_id_verweigert(repo):
    registry.append_experiments([_experiment_row(repo)], repo)
    with pytest.raises(registry.RegistryError, match="vorhanden oder doppelt"):
        registry.append_experiments([_experiment_row(repo)], repo)


def test_hash_mismatch_verweigert(repo):
    row = _experiment_row(repo)
    path = registry.hypothese_path("rep_test_effekt", repo)
    path.write_text(path.read_text() + "\nNachtrag nach dem Hashen.\n")
    with pytest.raises(registry.RegistryError, match="passt nicht zur Datei"):
        registry.append_experiments([row], repo)


def test_append_only_verweigert_geaenderte_zeile(repo):
    """Kernanforderung: Änderungen an alten Registry-Zeilen werden verweigert."""
    registry.append_experiments([_experiment_row(repo)], repo)
    _commit(repo)
    path = registry.experimente_path(repo)
    path.write_text(path.read_text().replace("replikation", "exploration"))
    _write_hypothese(repo, "rep_zweiter")
    with pytest.raises(registry.RegistryError, match="Append-only"):
        registry.append_experiments([_experiment_row(repo, "rep_zweiter")], repo)


def test_append_only_erlaubt_anhaengen(repo):
    registry.append_experiments([_experiment_row(repo)], repo)
    _commit(repo)
    _write_hypothese(repo, "rep_zweiter")
    assert registry.append_experiments([_experiment_row(repo, "rep_zweiter")], repo) == 1
    assert len(registry.load_experiments(repo)) == 2


# ---------- Auswertungen: Referenzen und Lockbox-Zähler ----------


def test_auswertung_referenzen(repo):
    with pytest.raises(registry.RegistryError, match="ohne registriertes Experiment"):
        registry.append_evaluations([_evaluation_row()], repo)
    registry.append_experiments([_experiment_row(repo)], repo)
    assert registry.append_evaluations([_evaluation_row()], repo) == 1
    with pytest.raises(registry.RegistryError, match="bereits ausgewertet"):
        registry.append_evaluations([_evaluation_row()], repo)


def test_lockbox_limit(repo):
    rows = []
    for i in range(3):
        exp_id = f"rep_lockbox_{i}"
        _write_hypothese(repo, exp_id)
        rows.append(_experiment_row(repo, exp_id))
    registry.append_experiments(rows, repo)
    for i in range(2):
        registry.append_evaluations(
            [_evaluation_row(experiment_id=f"rep_lockbox_{i}", lockbox="1")], repo
        )
    assert registry.lockbox_count(registry.load_evaluations(repo)) == 2
    with pytest.raises(registry.RegistryError, match="Lockbox-Auswertungszähler"):
        registry.append_evaluations(
            [_evaluation_row(experiment_id="rep_lockbox_2", lockbox="1")], repo
        )
    # ohne Lockbox-Flag bleibt das dritte Experiment auswertbar
    assert (
        registry.append_evaluations(
            [_evaluation_row(experiment_id="rep_lockbox_2", lockbox="0")], repo
        )
        == 1
    )


def test_lockbox_fenster_erzwingt_lockbox_flag(repo):
    _write_hypothese(repo, "rep_im_lockbox_fenster", fenster_ende="2026-06-30")
    registry.append_experiments([_experiment_row(repo, "rep_im_lockbox_fenster")], repo)
    with pytest.raises(registry.RegistryError, match="Lockbox-Zeitraum"):
        registry.append_evaluations(
            [_evaluation_row(experiment_id="rep_im_lockbox_fenster", lockbox="0")], repo
        )
    assert (
        registry.append_evaluations(
            [_evaluation_row(experiment_id="rep_im_lockbox_fenster", lockbox="1")], repo
        )
        == 1
    )


# ---------- Konsistenz-Check ----------


def test_check_registry(repo):
    registry.append_experiments([_experiment_row(repo)], repo)
    assert registry.check_registry(repo) == []
    path = registry.hypothese_path("rep_test_effekt", repo)
    path.write_text(path.read_text() + "\nnachträglich verändert\n")
    problems = registry.check_registry(repo)
    assert any("nachträglich verändert" in p for p in problems)


def test_check_registry_echtes_repo():
    """Die committete Registry dieses Repos muss jederzeit konsistent sein."""
    assert registry.check_registry() == []
