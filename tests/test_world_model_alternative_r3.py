"""Audit 3-round #23 (anti-confab): the suggested alternative action must be the
ACTION extracted from a past episode, not that episode's whole task_text, and it
must carry the source episode id for grounding.

_suggest_alternative returned getattr(ep, "task_text", "") verbatim — the full
"target OTHERCORP WordPress passive crtsh enum" string — presented as the
"alternative action". That confabulates: it echoes a different target's state as
if it were the action, with no traceable evidence id. Fix: return the action
phrase (task_text minus the current state's tokens) + alternative_evidence_id.
"""
from __future__ import annotations

from dataclasses import dataclass

from engram.world_model import simulate_action


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    final_answer: str = ""


def test_alternative_is_action_phrase_with_evidence_id() -> None:
    eps = [
        _Ep("f1", "target acme WordPress aggressive nmap", outcome="failure"),
        _Ep("f2", "target acme WordPress aggressive nmap", outcome="failure"),
        _Ep("a1", "target othercorp WordPress passive crtsh enum",
            outcome="success"),
        _Ep("a2", "target othersite WordPress passive crtsh enum",
            outcome="success"),
    ]
    out = simulate_action(
        state="target acme WordPress", action="aggressive nmap",
        past_episodes=eps,
    )
    assert out["p_success"] < 0.5, "precondition: l'azione corrente fallisce"
    alt = out["alternative"]
    assert alt is not None
    # confabulation guard: the action phrase, not the full foreign task_text.
    assert "passive" in alt.lower(), "l'azione alternativa e' presente"
    assert "wordpress" not in alt.lower(), \
        "i token di stato condivisi sono rimossi (non e' il task_text intero)"
    # grounding: the source episode is traceable.
    assert out["alternative_evidence_id"] in {"a1", "a2"}


def test_no_alternative_keeps_evidence_id_none() -> None:
    eps = [
        _Ep("s1", "target X good action", outcome="success"),
        _Ep("s2", "target Y good action", outcome="success"),
    ]
    out = simulate_action(
        state="target acme", action="good action", past_episodes=eps,
    )
    assert out["alternative"] is None
    assert out["alternative_evidence_id"] is None
