"""Momentum skill composition — atomic idea #3 (2026-06-13).

The flip: recall_chain already computes, for each recalled skill, the forward
trajectories the agent historically took next (with calibrated probabilities).
But it hands back a flat list of probabilities and leaves the judgement to the
reader — so compose_macro (which can fuse a chain into one executable skill)
is a tool nobody triggers, because nothing flags WHEN a chain is worth fusing.

momentum_macro_candidate is the missing DECISION layer between recall_chain
(forward_plans + prob) and compose_macro (executes them): it picks the recalled
skill whose best forward chain is both probable (>= min_forward_prob) and a real
multi-skill chain (>= min_path_len distinct steps), and surfaces it as a ready
compose recommendation. PURE, deterministic, no-LLM. Grounded: the live corpus
has 246/554 episodes with skills_used (244 with >=2), so the transition matrix
that feeds forward_plan has real data — this is not an empty signal.

RED marker: the function does not exist yet.
"""
from __future__ import annotations

from verimem.momentum_macro import momentum_macro_candidate


def _recall(skill_id, name, score, plans):
    # plans: list of (path, prob)
    return {
        "skill_id": skill_id,
        "name": name,
        "score": score,
        "forward_plans": [
            {"path": list(p), "log_prob": 0.0, "prob": float(pr)} for p, pr in plans
        ],
    }


def test_high_momentum_multistep_chain_is_a_candidate():
    recalls = [
        _recall("A", "alpha", 0.8, [(["A", "B", "C"], 0.82), (["A", "D"], 0.20)]),
    ]
    out = momentum_macro_candidate(recalls)
    assert out["has_candidate"] is True
    assert out["skill_id"] == "A"
    assert out["macro_path"] == ["A", "B", "C"]
    assert out["forward_prob"] == 0.82
    assert out["n_steps"] == 2  # 3 skills => 2 transitions


def test_below_prob_threshold_is_not_a_candidate():
    recalls = [_recall("A", "a", 0.9, [(["A", "B"], 0.5)])]
    out = momentum_macro_candidate(recalls, min_forward_prob=0.7)
    assert out["has_candidate"] is False
    assert out["macro_path"] == []


def test_single_skill_or_self_loop_is_not_composable():
    # A path with only one distinct skill is not a chain to fuse.
    recalls = [_recall("A", "a", 0.9, [(["A"], 0.99), (["A", "A"], 0.95)])]
    out = momentum_macro_candidate(recalls)
    assert out["has_candidate"] is False, "single skill / self-loop is not a macro"


def test_self_loop_tail_is_collapsed_but_real_chain_survives():
    # forward_plan often appends a sink self-loop (B->B); collapse it but keep A->B.
    recalls = [_recall("A", "a", 0.7, [(["A", "B", "B"], 0.95)])]
    out = momentum_macro_candidate(recalls)
    assert out["has_candidate"] is True
    assert out["macro_path"] == ["A", "B"], "consecutive duplicates must collapse"
    assert out["n_steps"] == 1


def test_highest_momentum_wins_across_recalls():
    recalls = [
        _recall("A", "a", 0.9, [(["A", "B"], 0.72)]),
        _recall("X", "x", 0.5, [(["X", "Y", "Z"], 0.88)]),  # lower recall score, higher momentum
    ]
    out = momentum_macro_candidate(recalls)
    assert out["skill_id"] == "X", "the more probable forward chain wins"
    assert out["macro_path"] == ["X", "Y", "Z"]
    assert out["n_candidates"] == 2


def test_recall_score_gate_excludes_weak_recalls():
    recalls = [_recall("A", "a", 0.1, [(["A", "B"], 0.9)])]
    out = momentum_macro_candidate(recalls, min_recall_score=0.3)
    assert out["has_candidate"] is False, "a weakly-recalled skill is not a confident base"


def test_empty_is_safe():
    out = momentum_macro_candidate([])
    assert out["has_candidate"] is False
    assert out["macro_path"] == []
    assert out["n_candidates"] == 0


# --- wiring into recall_chain (the caller_verification gap) -------------------

from dataclasses import dataclass, field  # noqa: E402

from verimem.skill import Skill  # noqa: E402


@dataclass
class _FakeEp:
    skills_used: list[str] = field(default_factory=list)


class _FakeSkillsStore:
    def __init__(self, skills):
        self._skills = skills

    def all(self, status=None):
        return list(self._skills)

    def retrieve(self, task, k=3, task_embedding=None):
        import re
        tt = set(re.findall(r"[a-z0-9]+", task.lower()))
        scored = []
        for s in self._skills:
            t = set(re.findall(r"[a-z0-9]+", (s.name or "").lower()))
            if t & tt:
                scored.append((s, len(t & tt) / max(len(t | tt), 1)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


class _FakeMemory:
    def __init__(self, eps):
        self._eps = eps

    def all(self, limit=None):
        return list(self._eps)


class _FakeAgent:
    def __init__(self, skills, eps):
        self.skills = _FakeSkillsStore(skills)
        self.memory = _FakeMemory(eps)


def test_recall_chain_exposes_momentum_field_always():
    from verimem.recall_chain import recall_chain
    out = recall_chain(task="x", agent=_FakeAgent([], []))
    assert "momentum" in out, "recall_chain must always expose the momentum field"
    assert out["momentum"]["has_candidate"] is False


def test_recall_chain_momentum_fires_on_a_real_chain():
    from verimem.recall_chain import recall_chain
    skills = [Skill(id="A", name="alpha skill"), Skill(id="B", name="beta skill")]
    eps = [_FakeEp(["A", "B"])] * 5  # A->B is deterministic (P[A,B]=1.0, no smoothing)
    out = recall_chain(task="alpha", agent=_FakeAgent(skills, eps))
    assert out["momentum"]["has_candidate"] is True
    assert out["momentum"]["macro_path"] == ["A", "B"], "the A->B chain must be proposed"
    assert out["momentum"]["forward_prob"] >= 0.7
