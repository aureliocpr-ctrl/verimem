"""B-1 multi-tenancy (2026-06-08): mem0-parity scoping via a zero-schema topic
prefix. Canonical order `user:<u>/agent:<a>/run:<r>/<base-topic>`, each segment
present only when that dimension is supplied. Strict per-dimension isolation on
recall (a fact scoped to user=alice is invisible to a user=bob query); shared
(unscoped) facts are opt-in via include_shared. Reuses the existing `agent:`
convention (engram/agent_scope.py) so agent-only scoping stays consistent.
"""
from __future__ import annotations

import pytest

from verimem.scope import lead_prefix, matches_scope, parse_scope, scoped_topic


def test_scoped_topic_single_dim():
    assert scoped_topic("project/x", user_id="alice") == "user:alice/project/x"
    assert scoped_topic("project/x", agent_id="pentester") == "agent:pentester/project/x"
    assert scoped_topic("project/x", run_id="job1") == "run:job1/project/x"


def test_scoped_topic_multi_dim_canonical_order():
    assert scoped_topic("t", user_id="u", agent_id="a", run_id="r") == "user:u/agent:a/run:r/t"
    # canonical order is independent of kwarg order
    assert scoped_topic("t", run_id="r", user_id="u") == "user:u/run:r/t"


def test_scoped_topic_none_is_noop():
    assert scoped_topic("project/x") == "project/x"


def test_scoped_topic_idempotent():
    once = scoped_topic("t", user_id="alice")
    assert scoped_topic(once, user_id="alice") == once  # no double-wrap
    # re-scoping with an extra dim merges, not nests
    assert scoped_topic(once, agent_id="bob") == "user:alice/agent:bob/t"


def test_scoped_topic_rejects_bad_id():
    for bad in ("a/b", "a:b", ""):
        with pytest.raises(ValueError):
            scoped_topic("t", user_id=bad)


def test_parse_scope():
    assert parse_scope("user:alice/agent:bob/run:job1/project/x") == {
        "user_id": "alice", "agent_id": "bob", "run_id": "job1", "base": "project/x",
    }
    assert parse_scope("project/x") == {
        "user_id": None, "agent_id": None, "run_id": None, "base": "project/x",
    }
    # partial scope
    assert parse_scope("user:alice/t") == {
        "user_id": "alice", "agent_id": None, "run_id": None, "base": "t",
    }


def test_matches_scope_strict_isolation():
    t = scoped_topic("t", user_id="alice")
    assert matches_scope(t, user_id="alice")
    assert not matches_scope(t, user_id="bob")
    # an unscoped fact is NOT returned to a user-scoped query (tenant isolation)…
    assert not matches_scope("plain/topic", user_id="alice")
    # …unless shared facts are explicitly opted in
    assert matches_scope("plain/topic", user_id="alice", include_shared=True)


def test_matches_scope_wildcard_on_unspecified_dim():
    t = scoped_topic("t", user_id="alice", agent_id="bob")
    assert matches_scope(t, user_id="alice")  # agent not constrained -> still matches
    assert not matches_scope(t, user_id="alice", agent_id="carol")


def test_matches_scope_no_query_matches_all():
    # No scope on the query -> no constraint (current/global behavior preserved).
    assert matches_scope("user:alice/t")
    assert matches_scope("plain/t")


# --- Isolation guarantees (regression guards for the security boundary) ---
# These lock the tenant-isolation contract of B-1. A future refactor that
# breaks any of them is a cross-tenant data leak — the most severe failure
# mode of multi-tenancy — so each assertion is a hard guard.


def test_scoped_topic_override_prevents_cross_tenant_hijack():
    # A supplied dim OVERRIDES an existing conflicting scope, so a caller
    # (bob) can never land a write inside another tenant's namespace by
    # passing a pre-scoped topic string — the topic is re-homed to bob.
    assert scoped_topic("user:alice/t", user_id="bob") == "user:bob/t"
    # multi-dim: only the supplied dim is overridden; the rest is preserved.
    assert (
        scoped_topic("user:alice/agent:x/t", user_id="bob")
        == "user:bob/agent:x/t"
    )


def test_scoped_topic_empty_base():
    # Degenerate but valid: scoping an empty topic yields just the prefix.
    assert scoped_topic("", user_id="alice") == "user:alice/"


def test_matches_scope_include_shared_is_not_a_cross_tenant_leak():
    # include_shared widens a query to ALSO see UNSCOPED/global facts — it must
    # NEVER expose another tenant's scoped facts. bob's fact stays invisible to
    # an alice query even with include_shared=True.
    assert not matches_scope("user:bob/t", user_id="alice", include_shared=True)
    # but the genuinely-unscoped fact IS now visible.
    assert matches_scope("plain/t", user_id="alice", include_shared=True)


def test_matches_scope_constrained_mismatch_beats_shared():
    # A mismatch on ANY explicitly-constrained dim returns False regardless of
    # include_shared — shared only relaxes UNSCOPED dims, never wrong ones.
    t = scoped_topic("t", user_id="alice", agent_id="x")
    assert not matches_scope(t, user_id="alice", agent_id="y", include_shared=True)


def test_parse_scope_repeated_dim_stops():
    # A repeated dimension halts parsing; the remainder is the base topic
    # (no silent last-wins overwrite that could mask a malformed topic).
    assert parse_scope("user:a/user:b/t") == {
        "user_id": "a", "agent_id": None, "run_id": None, "base": "user:b/t",
    }


def test_scope_round_trip_with_gap_preserves_dims_and_base():
    # parse_scope ∘ scoped_topic is identity on (dims, base), even with a gap
    # (run set, agent absent) and a multi-segment base topic.
    base = "project/deep/x"
    p = parse_scope(scoped_topic(base, user_id="u1", run_id="r1"))
    assert p == {"user_id": "u1", "agent_id": None, "run_id": "r1", "base": base}


def test_lead_prefix_contiguous_from_user():
    # The SQL-narrow prefix: contiguous user -> agent -> run.
    assert lead_prefix(user_id="u") == "user:u/"
    assert lead_prefix(user_id="u", agent_id="a") == "user:u/agent:a/"
    assert lead_prefix(user_id="u", agent_id="a", run_id="r") == "user:u/agent:a/run:r/"


def test_lead_prefix_stops_at_gap():
    # run without agent -> the prefix stops after user (a LIKE on run would
    # miss "user:u/run:r/..." stored rows). Post-filter handles the run dim.
    assert lead_prefix(user_id="u", run_id="r") == "user:u/"


def test_lead_prefix_none_when_no_leading_user():
    # A non-leading dim can't form a prefix -> None (caller oversamples).
    assert lead_prefix(agent_id="a") is None
    assert lead_prefix(run_id="r") is None
    assert lead_prefix() is None
