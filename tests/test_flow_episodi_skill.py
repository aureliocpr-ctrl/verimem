"""Le camere dark EPISODES e SKILLS: i due tier che mutano e non si vedevano.

Misurato da ws5 sul corpus reale il 2026-08-05:
  * EPISODI — vivi (10 scritti nelle ultime 24 ore) ma con l'esito FALSO:
    413 episodi, 405 "success", ZERO fallimenti registrati dal 19 maggio,
    mentre quattro istanze sbagliavano e ritiravano tutta la notte;
  * SKILL — fermo da tre mesi: 369 skill, 281 con zero trials, ultimo
    aggiornamento 2026-05-15.

Entrambi emettevano già (`episode_stored`, `fitness_updated`,
`skill_promoted`) — ma le superfici live tengono solo i nomi che iniziano
con ``flow.`` (gateway.py:511), quindi un tier fermo e un tier silenzioso
erano indistinguibili dall'esterno. Qui si pinna che l'attività dei due tier
esce sul canale che qualcuno ascolta, `outcome` compreso: è il campo che
rende VISIBILE lo squilibrio invece di lasciarlo soltanto vero.
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events
from verimem.memory import Episode, EpisodicMemory
from verimem.skill import Skill, SkillLibrary


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    return tmp_path


def _flow(tmp_path, name):
    p = tmp_path / "events.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        rec = json.loads(ln)
        if rec.get("name") == name:
            out.append(rec)
    return out


def test_un_episodio_scritto_esce_sul_canale_flow(tmp_env):
    em = EpisodicMemory(db_path=tmp_env / "episodes.db")
    em.store(Episode(task_id="t/uno", task_text="ha girato il banco",
                     outcome="success"))
    evts = _flow(tmp_env, "flow.episode")
    assert len(evts) == 1
    p = evts[0]["payload"]
    assert p["task_id"] == "t/uno" and p["outcome"] == "success"


def test_l_esito_viaggia_e_un_fallimento_si_distingue(tmp_env):
    """Il campo che conta: senza `outcome` sul canale, 405 success su 413
    sono indistinguibili da un tier sano."""
    em = EpisodicMemory(db_path=tmp_env / "episodes.db")
    em.store(Episode(task_id="t/ok", task_text="riuscito", outcome="success"))
    em.store(Episode(task_id="t/ko", task_text="fallito", outcome="failure"))
    esiti = [e["payload"]["outcome"] for e in _flow(tmp_env, "flow.episode")]
    assert esiti == ["success", "failure"], esiti


def test_una_skill_aggiornata_esce_sul_canale_flow(tmp_env):
    lib = SkillLibrary(db_path=tmp_env / "skills.db")
    s = Skill(name="prova", trigger="quando serve", body="fai cosi")
    lib.store(s)
    lib.update_fitness(s.id, success=True, tokens=120,
                       task_text="quando serve")
    evts = _flow(tmp_env, "flow.skill")
    assert evts, "il tier skill mutava la fitness senza dirlo a nessuno"
    p = evts[-1]["payload"]
    assert p["skill_id"] == s.id and p["kind"] == "fitness"
    assert "trials" in p and "status" in p
