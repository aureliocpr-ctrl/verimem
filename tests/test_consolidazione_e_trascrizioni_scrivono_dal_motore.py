"""La consolidazione e la promozione di un turno scrivono dal motore, come ogni porta.

Erano due dei quattro scrittori interni che costruivano un `Fact` a mano e lo
salvavano con `store()` (DoD di #159, 29/09). `store()` redige i segreti, fa lo
screen di sicurezza e l'hard-gate sulla provenienza, ma NON e' la scrittura del
prodotto: nessun evento `flow.write`, nessuna voce nel registro della fiducia,
nessuna ricevuta. Per la consolidazione anche nessun cancello: il master di un
gruppo di fatti entrava nel corpus senza che niente lo guardasse. La promozione
di un turno il cancello lo chiamava, ma da una COPIA sua della decisione — la
prima delle classi di difetto che questo prodotto ripete.

La promessa e' quella di riga 24 del registro: una scrittura lascia la stessa
traccia da qualunque porta entri. Qui la traccia che si conta e' l'evento di
scrittura, per DIFFERENZA, perche' il bus degli eventi e' del processo.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory

PREFISSO = "consolidazione/prova"


@pytest.fixture
def isolato(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return tmp_path


def _eventi_di(fid: str) -> int:
    from verimem.observability import BUS

    return sum(1 for e in BUS.history("flow.write", limit=100000)
               if (e.payload or {}).get("fact_id") == fid)


def test_CONTROLLO_il_contatore_vede_una_scrittura_dell_sdk(isolato):
    """Senza questa cella un contatore sempre a zero farebbe sembrare vere le
    due celle sotto per la ragione sbagliata."""
    from verimem.client import Memory

    r = Memory(path=str(isolato / "sdk.db")).add(
        "Il magazzino di Verona chiude alle 18 il sabato.", topic="prova/sdk")
    assert r.get("stored") is True, r
    assert _eventi_di(r["id"]) == 1


def test_il_master_della_consolidazione_lascia_la_traccia_di_una_scrittura(isolato):
    from verimem.consolidation import auto_consolidate
    from verimem.memory import EpisodicMemory

    sm = SemanticMemory(db_path=isolato / "sem.db")
    for k in range(7):
        sm.store(Fact(proposition=f"sub fact #{k} for cluster {PREFISSO}",
                      topic=f"{PREFISSO}/sub-{k}", confidence=0.7,
                      source_episodes=[f"ep_seed_{k}"], status="model_claim"))
    esito = auto_consolidate(sm, EpisodicMemory(db_path=isolato / "ep.db"),
                             min_size=5, prefix_depth=2)
    assert esito.get("masters_persisted") == 1, esito
    with sm._connect() as conn:  # noqa: SLF001
        righe = conn.execute(
            "SELECT id FROM facts WHERE topic = ? AND superseded_by IS NULL",
            (f"{PREFISSO}/auto-MASTER",)).fetchall()
    assert len(righe) == 1, f"master vivi per il topic: {len(righe)}"
    assert _eventi_di(righe[0]["id"]) == 1, (
        "il master della consolidazione e' entrato nel corpus senza l'evento "
        "di scrittura: e' stato salvato da store(), non scritto dal motore")


def test_la_promozione_di_un_turno_lascia_la_traccia_di_una_scrittura(isolato):
    from verimem.transcript_index import TranscriptIndex, Turn
    from verimem.transcript_promote import promote_turn_to_fact

    idx = TranscriptIndex(db_path=isolato / "t.db")
    idx.store(Turn(text="la riunione di revisione si tiene ogni giovedi alle 10",
                   session_id="S1", role="assistant", id="turno-1"))
    sm = SemanticMemory(db_path=isolato / "s.db")
    r = promote_turn_to_fact(idx, "turno-1", sm, topic="conversational/promoted")
    fid = r["id"] if isinstance(r, dict) else r.id
    assert _eventi_di(fid) == 1, (
        "il turno promosso e' entrato nel corpus senza l'evento di scrittura: "
        "e' stato salvato da store(), non scritto dal motore")
