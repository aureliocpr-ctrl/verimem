"""The proactive briefing must not present low-trust facts as "recent facts".

briefing.build_briefing() lists "recent facts" via semantic.list_facts(). That
excludes superseded rows but NOT the statuses the moat hides from recall
(quarantined / orphaned / user_belief), so the briefing surfaced, as current
knowledge, claims the anti-confab gate had rejected on write — the same
context-poisoning as the session-start banner, through a different channel.

The fix cannot change list_facts()'s default: 28 MCP tools (export_all,
find_duplicates, cluster_by_topic…) legitimately need to see the WHOLE corpus,
quarantined rows included, to analyse or clean it. So list_facts() gains an
opt-in `hide_low_trust` flag; the briefing sets it, the analysis tools do not.
"""
from __future__ import annotations

import pytest

from verimem.semantic import Fact, SemanticMemory


def _seed(tmp_path):
    m = SemanticMemory(db_path=tmp_path / "s.db")
    m.store(Fact(proposition="Tank holds 750 liters.", topic="ops",
                 status="verified"))
    m.store(Fact(proposition="Deploy is green.", topic="ci",
                 status="model_claim"))
    m.store(Fact(proposition="Suspect contradictory claim.", topic="ops",
                 status="quarantined"))
    m.store(Fact(proposition="Orphaned scrubbed row.", topic="ops",
                 status="orphaned"))
    m.store(Fact(proposition="An unverified user belief.", topic="ops",
                 status="user_belief"))
    return m


def test_list_facts_default_still_sees_everything(tmp_path):
    """The 28 analysis/cleanup tools must keep seeing the whole corpus."""
    m = _seed(tmp_path)
    props = {f.proposition for f in m.list_facts()}
    assert "Suspect contradictory claim." in props
    assert "Orphaned scrubbed row." in props
    assert "An unverified user belief." in props


def test_list_facts_hide_low_trust_drops_the_hidden_statuses(tmp_path):
    m = _seed(tmp_path)
    props = {f.proposition for f in m.list_facts(hide_low_trust=True)}
    assert "Tank holds 750 liters." in props        # verified stays
    assert "Deploy is green." in props              # model_claim stays
    assert "Suspect contradictory claim." not in props   # quarantined gone
    assert "Orphaned scrubbed row." not in props         # orphaned gone
    assert "An unverified user belief." not in props     # user_belief gone


def test_briefing_recent_facts_hide_low_trust(tmp_path):
    """End-to-end: the briefing's 'recent facts' must not carry hidden-status
    rows."""
    m = _seed(tmp_path)
    from types import SimpleNamespace

    from verimem.briefing import get_briefing
    agent = SimpleNamespace(semantic=m, memory=None, skills=None)
    brief = get_briefing(agent=agent)
    props = " | ".join(f.get("proposition", "")
                       for f in brief.get("recent_facts", []))
    assert "Tank holds 750 liters." in props
    assert "Suspect" not in props and "Orphaned" not in props
    assert "user belief" not in props
