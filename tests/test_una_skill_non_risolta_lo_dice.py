"""`skills_used` imparava a vuoto, in silenzio.

`hippo_record_episode` accetta `skills_used` e aggiorna la fitness di ognuna.
`SkillLibrary.update_fitness` restituisce `None` quando l'id non esiste, e
l'handler faceva:

    if s is not None:
        fitness_updates.append(sid)

senza ramo `else`. Un'etichetta che non risolve spariva dalla ricevuta: il
chiamante riceveva `fitness_updated` con i soli riusciti e non aveva modo di
sapere che gli altri erano stati ignorati.

Non è un caso di bordo. Misurato dall'altra istanza sull'audit di produzione:
**519 etichette su 558 non risolvono**, e questo spiega i **230 skill su 325
senza trials** senza bisogno di invocare l'esposizione semantica. Gli id veri
sono hash esadecimali (325 file in `~/.engram/skills/`, zero nomi leggibili) e
lo schema del tool non ha `description`: chi chiama passa quasi sempre un
NOME, e il nome non è un id.

Il difetto è il silenzio, non la mancata risoluzione: un chiamante che sa di
aver passato tre etichette e ne vede tornare una può correggere, uno che non
lo sa continua a insegnare a vuoto.
"""
from __future__ import annotations

import asyncio
import json

import pytest


def _record(args: dict) -> dict:
    from verimem import mcp_server as srv
    res = asyncio.run(srv.call_tool("hippo_record_episode", args))
    return json.loads(res[0].text)


@pytest.fixture()
def agente(tmp_path, monkeypatch):
    from verimem import mcp_server as srv
    from verimem.client import Memory
    from verimem.memory import EpisodicMemory
    from verimem.skill import Skill, SkillLibrary

    lib = SkillLibrary(dir_path=tmp_path / "sk", db_path=tmp_path / "sk.db")
    lib.store(Skill(id="a1b2c3d4", name="deploy the release",
                    trigger="release", status="promoted"))
    mem = Memory(path=tmp_path / "m.db")

    class _Ag:
        # `.memory` è una `EpisodicMemory`, come su `VerimemAgent`: l'handler
        # ci salva l'episodio. Un doppio che mette qui il `Memory` dell'SDK
        # (o `None`) fa fallire lo store con un `AttributeError` che non
        # c'entra nulla col difetto sotto esame.
        skills = lib
        semantic = mem.semantic
        memory = EpisodicMemory(db_path=tmp_path / "ep.db")
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())
    return lib


_BASE = {"task_text": "un compito", "final_answer": "fatto",
         "outcome": "success"}


def test_un_id_che_non_risolve_viene_DETTO(agente):
    out = _record({**_BASE, "skills_used": ["a1b2c3d4", "non-esiste"]})
    ignorati = out.get("skills_not_found") or out.get("skills_unresolved")
    assert ignorati, (
        f"l'etichetta non risolta è sparita dalla ricevuta: {sorted(out)}")
    assert "non-esiste" in ignorati, ignorati


def test_quelle_che_risolvono_continuano_a_risolvere(agente):
    out = _record({**_BASE, "skills_used": ["a1b2c3d4", "non-esiste"]})
    assert "a1b2c3d4" in (out.get("fitness_updated") or []), out


def test_passare_un_NOME_invece_dell_id_non_e_silenzioso(agente):
    """Il caso che produce i 519 su 558: gli id sono hash esadecimali e chi
    chiama passa il nome leggibile."""
    out = _record({**_BASE, "skills_used": ["deploy the release"]})
    assert not (out.get("fitness_updated") or []), out
    ignorati = out.get("skills_not_found") or out.get("skills_unresolved")
    assert ignorati and "deploy the release" in ignorati, out


def test_senza_ignorati_la_ricevuta_non_si_sporca(agente):
    """Un campo che compare sempre, anche vuoto, diventa rumore da saltare."""
    out = _record({**_BASE, "skills_used": ["a1b2c3d4"]})
    assert not out.get("skills_not_found"), out
