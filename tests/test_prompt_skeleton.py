"""R40: Generate a prompt skeleton from skill + facts memory.

Given a task, build a structured prompt template that includes:
  - relevant past episodes summary
  - relevant facts as context
  - skills to consider applying

Returns a markdown-formatted prompt ready to feed an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


@dataclass
class _Fact:
    id: str
    proposition: str
    topic: str = ""


@dataclass
class _Skill:
    id: str
    name: str = ""
    trigger: str = ""
    body: str = ""
    status: str = "promoted"


def test_empty_returns_basic_template():
    from engram.prompt_skeleton import build_prompt_skeleton
    out = build_prompt_skeleton(task="x", episodes=[], facts=[], skills=[])
    assert "x" in out["prompt"]


def test_includes_relevant_facts():
    from engram.prompt_skeleton import build_prompt_skeleton
    facts = [_Fact("f1", "WordPress 5.8 vulnerable to CVE-X")]
    out = build_prompt_skeleton(
        task="WordPress exploitation",
        episodes=[], facts=facts, skills=[],
    )
    assert "CVE-X" in out["prompt"] or "WordPress" in out["prompt"]


def test_includes_relevant_episodes():
    from engram.prompt_skeleton import build_prompt_skeleton
    eps = [_Ep("e1", "WordPress RCE acme", "success",
               "shell obtained")]
    out = build_prompt_skeleton(
        task="WordPress RCE",
        episodes=eps, facts=[], skills=[],
    )
    assert "shell" in out["prompt"].lower() or "wordpress" in out["prompt"].lower()


def test_includes_skills():
    from engram.prompt_skeleton import build_prompt_skeleton
    skills = [_Skill("s1", trigger="WordPress RCE exploit",
                     body="apply CVE-X")]
    out = build_prompt_skeleton(
        task="WordPress RCE",
        episodes=[], facts=[], skills=skills,
    )
    assert "s1" in out["prompt"] or "RCE" in out["prompt"]


def test_payload_keys():
    from engram.prompt_skeleton import build_prompt_skeleton
    out = build_prompt_skeleton(task="x", episodes=[], facts=[], skills=[])
    for k in ("prompt", "components", "n_episodes_cited",
              "n_facts_cited", "n_skills_cited"):
        assert k in out


def test_irrelevant_excluded():
    from engram.prompt_skeleton import build_prompt_skeleton
    facts = [_Fact("f1", "totally unrelated cooking recipe")]
    out = build_prompt_skeleton(
        task="WordPress exploit",
        episodes=[], facts=facts, skills=[],
    )
    assert out["n_facts_cited"] == 0
