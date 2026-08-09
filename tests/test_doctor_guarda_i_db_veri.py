"""`doctor` elenca i database che il prodotto USA, non quelli che trova.

TROVATO il 2026-07-30 dal dogfooding in parallelo. Il check `data-dir`
elencava ``d.glob("*.db")`` — solo il livello alto della cartella dati, dove su
questa macchina vivono SEI file da 0 byte (``episodes.db``, ``episodic.db``,
``hippo.db``, ``memory.db``, ``engram_kg.db``, ``entities.db``): scheletri di
layout vecchi, mai popolati. I database VERI stanno annidati e non comparivano:

    semantic/semantic.db      79 MB
    episodes/episodes.db      17 MB
    skills/skills_index.db   1.8 MB

Cioe' la diagnosi mostrava all'operatore un elenco di file vuoti e taceva su
quelli che contengono la sua memoria. Un glob trova i file; il prodotto SA quali
sono i suoi — sono in ``CONFIG``. Si interroga la struttura, non la cartella.

MISURATO NELLO STESSO GIRO, e questo il finding non lo diceva: la cartella dati
sono 12.3 GB, di cui **9.5 GB in 284 snapshot il cui nome contiene "pytest"**.
Il 77% dello store di produzione e' materiale lasciato dai test. Non e' compito
di questo file cancellarli — e' compito di `doctor` DIRLO, perche' oggi nessuna
superficie lo diceva e per accorgersene bisognava guardare il disco a mano.
"""
from __future__ import annotations

import re

import pytest

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture()
def store(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    # scheletri vuoti al livello alto, come sulla macchina vera
    for nome in ("episodes.db", "hippo.db", "memory.db"):
        (tmp_path / nome).write_bytes(b"")
    # i database veri, annidati e con del contenuto
    for sub, nome in (("semantic", "semantic.db"), ("episodes", "episodes.db"),
                      ("skills", "skills_index.db")):
        (tmp_path / sub).mkdir(exist_ok=True)
        (tmp_path / sub / nome).write_bytes(b"x" * 4096)
    return tmp_path


def _check_data_dir(nome="data-dir"):
    from verimem import doctor
    return next(c for c in doctor.run_doctor() if c["name"] == nome)


def test_elenca_i_db_VIVI_non_gli_scheletri(store):
    c = _check_data_dir()
    testo = c["detail"]
    assert "semantic.db" in testo, (
        f"il database che contiene la memoria non compare nella diagnosi:\n{testo}")
    assert "skills_index.db" in testo, testo


def test_dice_la_DIMENSIONE_perche_zero_byte_e_una_diagnosi(store):
    """«c'e' un file di nome episodes.db» e «quel file e' vuoto» mandano
    l'operatore a fare cose diverse."""
    c = _check_data_dir()
    assert re.search(r"\d+(\.\d+)?\s*(B|KB|MB|GB)", c["detail"]), c["detail"]


def test_lo_spazio_dei_test_viene_dichiarato(store, monkeypatch):
    """9.5 GB di snapshot pytest sullo store di produzione non si vedevano da
    nessuna superficie: per accorgersene bisognava guardare il disco a mano."""
    snap = store / "snapshots"
    snap.mkdir()
    for i in range(3):
        (snap / f"178000000{i}_pytest-test.db").write_bytes(b"y" * 200_000)
    (snap / "1780000009_pre-live-launch.db").write_bytes(b"z" * 1000)

    from verimem import doctor
    checks = doctor.run_doctor()
    testo = " ".join(f"{c.get('detail','')} {c.get('fix','')}" for c in checks)
    assert "pytest" in testo.lower(), (
        f"nessun check nomina lo spazio occupato dagli snapshot dei test:\n{testo[:400]}")


def test_uno_store_pulito_non_produce_allarmi(store):
    """La diagnosi non deve gridare su un'installazione normale."""
    from verimem import doctor
    nomi = {c["name"] for c in doctor.run_doctor()}
    assert "data-dir" in nomi
    snapshot_checks = [c for c in doctor.run_doctor()
                       if c["name"] == "test-leftovers"]
    assert not snapshot_checks or snapshot_checks[0]["status"] == "ok", (
        "senza snapshot di test non ci deve essere allarme")
