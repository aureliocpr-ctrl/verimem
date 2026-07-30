"""Un dato cancellato non riemerge da nessuna parte, nemmeno dal disco.

Il README lo mette in una tabella di confronto coi concorrenti: «True forget
(GDPR): deleted data cannot resurface via history or time travel — shipped,
probe-tested | mem0 leaked in our probe». E' la riga piu' delicata di quella
tabella, perche' e' una promessa di conformita': se cade, cade su un dato
personale di qualcuno.

Provata il 2026-07-30 su quattro vie, e regge su tutte — anche col DEFAULT
(`purge_history=False`), che e' il percorso che un utente usa davvero:

    recall normale               assente
    time-travel a prima del rm   assente
    get(id) diretto              assente
    ogni colonna di ogni tabella assente   <- incluse FTS e l'undo log

L'ultima e' la verifica che conta: cerca la stringa in TUTTE le colonne di
TUTTE le tabelle, invece di fidarsi delle vie di lettura note. Una tabella
dimenticata — un indice full-text, un log di undo, una copia narrativa — e' il
modo tipico in cui una cancellazione sembra completa e non lo e'.
"""
from __future__ import annotations

import sqlite3
import time

import pytest

SEGRETO = "RSSMRA80A01H501U"
FRASE = f"Il codice fiscale di Mario Rossi e {SEGRETO}."


@pytest.fixture
def mem(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    return Memory(path=tmp_path / "semantic" / "semantic.db")


def _dove_compare(db: str, ago: str) -> list[str]:
    """Ogni colonna di ogni tabella. Niente scorciatoie sulle vie note."""
    trovato: list[str] = []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for (t,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"):
            try:
                for col in con.execute(f"PRAGMA table_info({t})"):
                    n = con.execute(
                        f"SELECT COUNT(*) FROM {t} WHERE CAST({col[1]} AS TEXT) "
                        f"LIKE ?", (f"%{ago}%",)).fetchone()[0]
                    if n:
                        trovato.append(f"{t}.{col[1]} x{n}")
            except sqlite3.Error:
                continue
    finally:
        con.close()
    return trovato


@pytest.mark.security
@pytest.mark.parametrize("purge", [False, True])
def test_il_dato_sparisce_da_ogni_via(mem, purge):
    r = mem.add(FRASE, topic="pii")
    fid = r.get("id")
    prima = time.time()
    assert _dove_compare(str(mem.semantic.db_path), SEGRETO), (
        "il fatto non e' nemmeno stato scritto: il test non proverebbe nulla")

    assert mem.delete(fid, purge_history=purge) is True

    assert SEGRETO not in str(mem.search("codice fiscale Mario Rossi", k=5))
    from verimem.temporal_context import recall_as_of
    assert SEGRETO not in str(recall_as_of(
        mem.semantic, "codice fiscale Mario Rossi", when=prima, k=5))
    assert SEGRETO not in str(mem.semantic.get(fid))
    resti = _dove_compare(str(mem.semantic.db_path), SEGRETO)
    assert not resti, (
        f"il dato cancellato e' ancora sul disco in {resti} — la riga del "
        f"README sul true-forget non regge piu'")
