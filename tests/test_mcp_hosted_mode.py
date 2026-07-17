"""FORGIA pezzo #206 — HOSTED MODE: delegate LLM to the calling host.

Aurelio's principle: "if I'm inside Claude Code, the LLM should be
Claude Code's subscription tokens, not the configured API key in
data/user_settings.json. The 2 paid tools (run_task, consolidate)
should not auto-fire — instead, expose a 'prepare/record' split that
returns context for the host to act on, then records the result."

* ``hippo_prepare_task``      — assemble {rendered_skills, recall, prompt}
                                without calling any LLM. Free.
* ``hippo_record_episode``    — store an episode the host has executed
                                using its own LLM. Free, just SQLite.
* ``hippo_run_task`` (hosted) — when env HIPPO_HOSTED=1, refuses with
                                a clear instruction to use prepare+record.
* ``hippo_consolidate_light`` — sleep-cycle subset that runs WITHOUT
                                LLM (dedup + promote + retire only,
                                no dreamer/critic). Free.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server

# ---------- Fakes --------------------------------------------------------


class _FakeSkill:
    def __init__(self, sid: str, *, name: str, body: str = "",
                  trigger: str = "", fitness_mean: float = 0.5,
                  trials: int = 0, successes: int = 0,
                  status: str = "promoted") -> None:
        self.id = sid
        self.name = name
        self.body = body
        self.trigger = trigger
        self.fitness_mean = fitness_mean
        self.trials = trials
        self.successes = successes
        self.status = status

    def render(self) -> str:
        return f"### Skill: {self.name}\n_When:_ {self.trigger}\n\n{self.body}\n"


class _FakeSkillsStore:
    def __init__(self) -> None:
        self._skills = [
            _FakeSkill("sk1", name="reverse string",
                       body="reverse char by char",
                       trigger="when reversing strings",
                       fitness_mean=0.9, trials=5, successes=4),
            _FakeSkill("sk2", name="capitalize words",
                       body="upper each word's first letter",
                       trigger="when capitalizing",
                       fitness_mean=0.85, trials=3, successes=3),
        ]
        # Cycle #8: spy su update_fitness per catturare bug
        # "hippo_record_episode non chiama update_fitness".
        self.update_fitness_calls: list[tuple[str, bool, int]] = []

    def retrieve(self, task: str, k: int = 3,
                  status: str | None = None) -> list[_FakeSkill]:
        items = list(self._skills)
        if status:
            items = [s for s in items if s.status == status]
        return items[:k]

    def all(self, status: str | None = None) -> list[_FakeSkill]:
        items = list(self._skills)
        if status:
            items = [s for s in items if s.status == status]
        return items

    def get(self, sid: str) -> _FakeSkill | None:
        for s in self._skills:
            if s.id == sid:
                return s
        return None

    def update_fitness(self, skill_id: str, success: bool, tokens: int,
                        task_text: str = "") -> _FakeSkill | None:
        """Real `SkillLibrary.update_fitness` increments trials + successes
        + last_used_at. Fake records the call so tests can assert it fired.
        """
        self.update_fitness_calls.append((skill_id, success, tokens))
        s = self.get(skill_id)
        if s is None:
            return None
        s.trials += 1
        if success:
            s.successes += 1
        return s


class _FakeEpisode:
    def __init__(self, eid: str, task: str, outcome: str = "success",
                  final_answer: str = "ok",
                  skills_used: list[str] | None = None,
                  tokens_used: int = 100, num_steps: int = 2,
                  task_id: str | None = None) -> None:
        self.id = eid
        self.task_id = task_id or f"t-{eid}"
        self.task_text = task
        self.outcome = outcome
        self.final_answer = final_answer
        self.skills_used = skills_used or []
        self.tokens_used = tokens_used
        self.num_steps = num_steps
        self.created_at = 1000.0
        self.notes = ""
        self.critique = ""


class _FakeMemory:
    def __init__(self) -> None:
        self._episodes: list[_FakeEpisode] = []
        self._stored_via_record: list[_FakeEpisode] = []

    def recall(self, query: str, k: int = 5,
                outcome_filter: str | None = None) -> list:
        return [(_FakeEpisode("ep_pre", "earlier reverse task",
                                final_answer="olleh"), 0.7)]

    def store(self, episode: _FakeEpisode, *, embed: str = "sync", **_kwargs) -> None:
        # Mirror the real EpisodicMemory.store signature: the hosted
        # hippo_record_episode handler calls store(ep, embed="auto") for the
        # non-blocking save path. Accept (and ignore) embed + any future
        # keyword so the double never diverges from the production interface.
        self._episodes.append(episode)
        self._stored_via_record.append(episode)

    def count(self, outcome_filter=None) -> int:
        if outcome_filter:
            return sum(1 for e in self._episodes
                        if e.outcome == outcome_filter)
        return len(self._episodes)


class _FakeSemantic:
    def count(self) -> int:
        return 0


class _FakeAgent:
    def __init__(self) -> None:
        self.skills = _FakeSkillsStore()
        self.memory = _FakeMemory()
        self.semantic = _FakeSemantic()


# ---------- Helpers ------------------------------------------------------


async def _invoke_tool(name: str, arguments: dict[str, Any] | None = None):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    return [c.text for c in payload.content if hasattr(c, "text")]


@pytest.fixture
def fake_agent(monkeypatch: pytest.MonkeyPatch) -> _FakeAgent:
    a = _FakeAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    # Build_episode factory monkeypatchable for record tool.
    def _factory(task_id: str, task_text: str, final_answer: str,
                  outcome: str = "success",
                  skills_used: list[str] | None = None,
                  tokens_used: int = 0,
                  num_steps: int = 1) -> _FakeEpisode:
        import uuid
        eid = uuid.uuid4().hex[:12]
        return _FakeEpisode(
            eid, task_text, outcome=outcome, final_answer=final_answer,
            skills_used=skills_used or [], tokens_used=tokens_used,
            num_steps=num_steps, task_id=task_id,
        )
    monkeypatch.setattr(mcp_server, "_build_episode", _factory,
                          raising=False)
    return a


# ---------- listing -----------------------------------------------------


@pytest.mark.asyncio
async def test_hosted_tools_listed(fake_agent: _FakeAgent) -> None:
    from mcp.types import ListToolsRequest, PaginatedRequestParams
    handler = mcp_server.server.request_handlers[ListToolsRequest]
    req = ListToolsRequest(method="tools/list", params=PaginatedRequestParams())
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    names = {tool.name for tool in payload.tools}
    for n in ("hippo_prepare_task", "hippo_record_episode",
              "hippo_consolidate_light"):
        assert n in names, f"missing tool: {n}"


# ---------- hippo_prepare_task ------------------------------------------


@pytest.mark.asyncio
async def test_prepare_task_returns_context(fake_agent: _FakeAgent) -> None:
    """No LLM call. Returns the prompt context the host can use."""
    blocks = await _invoke_tool(
        "hippo_prepare_task",
        {"task": "reverse the string 'hello'"},
    )
    payload = json.loads(blocks[0])
    assert payload["llm_called"] is False
    assert payload["task"] == "reverse the string 'hello'"
    assert "skills" in payload
    assert "recall" in payload
    assert "rendered_prompt" in payload
    # Skills must include the reverse-string skill.
    skill_names = [s["name"] for s in payload["skills"]]
    assert any("reverse" in n for n in skill_names)
    # rendered_prompt must contain the task and skill bodies.
    assert "reverse the string 'hello'" in payload["rendered_prompt"]
    assert "reverse char by char" in payload["rendered_prompt"]


@pytest.mark.asyncio
async def test_prepare_task_respects_k(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_prepare_task",
        {"task": "x", "k_skills": 1, "k_episodes": 1},
    )
    payload = json.loads(blocks[0])
    assert len(payload["skills"]) == 1
    assert len(payload["recall"]) <= 1


# ---------- hippo_record_episode ----------------------------------------


@pytest.mark.asyncio
async def test_record_episode_stores(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "reverse hello",
         "final_answer": "olleh",
         "outcome": "success",
         "skills_used": ["sk1"],
         "tokens_used": 1234},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    assert "episode_id" in payload
    # Persisted via fake memory.
    assert len(fake_agent.memory._stored_via_record) == 1
    ep = fake_agent.memory._stored_via_record[0]
    assert ep.task_text == "reverse hello"
    assert ep.final_answer == "olleh"
    assert ep.outcome == "success"
    assert ep.skills_used == ["sk1"]
    assert ep.tokens_used == 1234


@pytest.mark.asyncio
async def test_record_episode_minimal(fake_agent: _FakeAgent) -> None:
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "x", "final_answer": "y"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    ep = fake_agent.memory._stored_via_record[0]
    assert ep.outcome == "success"  # default
    assert ep.skills_used == []  # default
    assert ep.tokens_used == 0  # default


# ---------- CYCLE #8 — bug: update_fitness was never called -------------


@pytest.mark.asyncio
async def test_record_episode_updates_skill_fitness(
    fake_agent: _FakeAgent,
) -> None:
    """CYCLE #8 regression: hippo_record_episode MUST call
    update_fitness for every skill_id in skills_used, otherwise
    candidate skills exposed via hippo_skills_for/hippo_prepare_task
    can never accumulate trials → never promoted.

    Mirrors the behaviour of wake.py:1265 and chat.py:141 which already
    invoke update_fitness; the hosted-mode record path was missing it.
    """
    # Pre-state: sk1 has trials=5, sk2 has trials=3 (from fixture).
    sk1_before = fake_agent.skills.get("sk1")
    sk2_before = fake_agent.skills.get("sk2")
    assert sk1_before.trials == 5
    assert sk2_before.trials == 3

    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "compose op",
         "final_answer": "result",
         "outcome": "success",
         "skills_used": ["sk1", "sk2"],
         "tokens_used": 200},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True

    # update_fitness must have fired once per skill_id.
    calls = fake_agent.skills.update_fitness_calls
    sids_called = [c[0] for c in calls]
    assert "sk1" in sids_called, (
        "BUG: hippo_record_episode did not call update_fitness('sk1')"
    )
    assert "sk2" in sids_called
    # success flag propagates from outcome.
    for sid, success, tokens in calls:
        if sid in ("sk1", "sk2"):
            assert success is True

    # trials must be incremented by 1.
    assert fake_agent.skills.get("sk1").trials == 6
    assert fake_agent.skills.get("sk2").trials == 4


@pytest.mark.asyncio
async def test_record_episode_failure_outcome_propagates_to_fitness(
    fake_agent: _FakeAgent,
) -> None:
    """outcome='failure' must record a failed trial (success=False).
    Otherwise we'd silently treat every recorded episode as a win, biasing
    the Bayesian fitness toward over-promotion.
    """
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "broken op",
         "final_answer": "err",
         "outcome": "failure",
         "skills_used": ["sk1"]},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    calls = fake_agent.skills.update_fitness_calls
    sk1_calls = [c for c in calls if c[0] == "sk1"]
    assert len(sk1_calls) == 1
    _, success, _ = sk1_calls[0]
    assert success is False
    # successes counter must NOT increment on failure.
    sk1 = fake_agent.skills.get("sk1")
    assert sk1.trials == 6  # bumped
    assert sk1.successes == 4  # unchanged from fixture


@pytest.mark.asyncio
async def test_record_episode_empty_skills_used_no_calls(
    fake_agent: _FakeAgent,
) -> None:
    """Episode senza skills_used → ZERO update_fitness invocations.
    Esistenti 191/562 episodi senza skills_used non devono toccare nulla."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "no skills", "final_answer": "ok"},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    # Nessuna chiamata su update_fitness.
    assert fake_agent.skills.update_fitness_calls == []


@pytest.mark.asyncio
async def test_record_episode_dedups_repeated_skill_ids(
    fake_agent: _FakeAgent,
) -> None:
    """CYCLE #16 regression — critic-orchestrator counterexample worker:
    Host che manda skills_used=['sk1','sk1'] (pattern naturale quando la
    stessa skill è citata in più step) NON deve doppio-contare trials.
    Pre-fix: trials/successes +=2, Hebbian lerp+renorm doppio (corrompeva
    Bayesian fitness signal). Post-fix: dedup via dict.fromkeys preserva
    ordine, ogni skill aggiornata UNA volta per episode.
    """
    sk1_before = fake_agent.skills.get("sk1")
    assert sk1_before.trials == 5

    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "x", "final_answer": "y",
         "outcome": "success",
         # DUPLICATE intenzionali — pattern critic counterexample
         "skills_used": ["sk1", "sk1", "sk2", "sk1"]},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True

    # update_fitness deve essere chiamato UNA volta per sk1 (non 3)
    calls = fake_agent.skills.update_fitness_calls
    sk1_calls = [c for c in calls if c[0] == "sk1"]
    sk2_calls = [c for c in calls if c[0] == "sk2"]
    assert len(sk1_calls) == 1, (
        f"BUG: sk1 fu chiamata {len(sk1_calls)} volte, deve essere 1 "
        "(dedup mancante)"
    )
    assert len(sk2_calls) == 1
    # trials di sk1: +1 (non +3)
    assert fake_agent.skills.get("sk1").trials == 6
    # fitness_updated nel response: deduplicato
    assert payload["fitness_updated"].count("sk1") == 1


@pytest.mark.asyncio
async def test_record_episode_unknown_skill_id_does_not_crash(
    fake_agent: _FakeAgent,
) -> None:
    """Skill id non esistente nel DB → update_fitness ritorna None ma
    l'handler non deve crashare. L'episode si store comunque."""
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "x", "final_answer": "y",
         "skills_used": ["sk1", "does_not_exist"]},
    )
    payload = json.loads(blocks[0])
    assert payload["ok"] is True
    # sk1 si è updatata, l'unknown è stata ignorata (o tentata e None).
    sids_called = [c[0] for c in fake_agent.skills.update_fitness_calls]
    assert "sk1" in sids_called


@pytest.mark.asyncio
async def test_record_episode_empty_text_rejected(
    fake_agent: _FakeAgent,
) -> None:
    blocks = await _invoke_tool(
        "hippo_record_episode",
        {"task_text": "", "final_answer": "x"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload


# ---------- hippo_run_task in hosted mode ------------------------------


@pytest.mark.asyncio
async def test_run_task_refuses_when_hosted(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When HIPPO_HOSTED=1, run_task refuses and points to prepare+record."""
    monkeypatch.setenv("HIPPO_HOSTED", "1")
    blocks = await _invoke_tool(
        "hippo_run_task",
        {"task": "anything"},
    )
    payload = json.loads(blocks[0])
    assert "error" in payload
    msg = payload["error"].lower()
    assert "hosted" in msg or "prepare" in msg


@pytest.mark.asyncio
async def test_consolidate_refuses_when_hosted(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_HOSTED", "1")
    blocks = await _invoke_tool("hippo_consolidate", {})
    payload = json.loads(blocks[0])
    assert "error" in payload
    msg = payload["error"].lower()
    assert "hosted" in msg or "consolidate_light" in msg


# ---------- hippo_consolidate_light -----------------------------------


@pytest.mark.asyncio
async def test_consolidate_light_runs_without_llm(
    fake_agent: _FakeAgent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dedup + promote/retire only, no dreamer/critic LLM calls."""
    # Inject a fake light_consolidate that the agent supports via
    # an attribute. The handler should call it.
    called: dict[str, bool] = {"called": False}

    def _fake_light():
        called["called"] = True
        return {
            "duration_s": 0.01,
            "n_episodes_replayed": 0,
            "promoted": [],
            "retired": [],
            "merged": [],
            "tokens_used": 0,
            "llm_calls": 0,
            "mode": "light",
        }
    monkeypatch.setattr(mcp_server, "_consolidate_light",
                          _fake_light, raising=False)
    blocks = await _invoke_tool("hippo_consolidate_light", {})
    payload = json.loads(blocks[0])
    assert payload["mode"] == "light"
    assert payload["llm_calls"] == 0
    assert payload["tokens_used"] == 0
    assert called["called"]
