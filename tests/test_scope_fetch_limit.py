"""scoped_fetch_limit must oversample whenever the matches_scope post-filter
can drop rows — closing the scoped under-return (correctness-hunt #3 medium).

Both hippo_facts_search and hippo_facts_recall narrow by lead_prefix then
post-filter by matches_scope. lead_prefix stops at the first gap, so a
``run_id`` WITHOUT ``agent_id`` yields only ``"user:<u>/"`` — a PARTIAL prefix.
The pre-fix code fetched exactly ``base`` rows under that partial prefix, then
matches_scope dropped every row whose run != the wanted one, silently returning
far fewer than ``base`` scope-matching facts (real info lost at recall).

RED marker: ``scoped_fetch_limit`` does not exist pre-fix; the gap case below
pins that it must oversample (the old inline ``base if has_prefix`` returned
``base`` — the under-return).
"""
from __future__ import annotations

from verimem.scope import scoped_fetch_limit


def test_complete_prefix_user_only_uses_base() -> None:
    # user only → prefix 'user:U/' covers the whole scope, post-filter is a
    # no-op → base is exact, no oversample needed.
    assert scoped_fetch_limit(20, scoped=True, has_prefix=True,
                              agent_id=None, run_id=None, cap=500) == 20


def test_complete_prefix_user_agent_uses_base() -> None:
    assert scoped_fetch_limit(20, scoped=True, has_prefix=True,
                              agent_id="a", run_id=None, cap=500) == 20


def test_complete_prefix_user_agent_run_uses_base() -> None:
    assert scoped_fetch_limit(20, scoped=True, has_prefix=True,
                              agent_id="a", run_id="r", cap=500) == 20


def test_gap_run_without_agent_oversamples() -> None:
    # THE BUG: partial prefix 'user:U/' but matches_scope still filters run →
    # must oversample so the post-filter can't under-return.
    assert scoped_fetch_limit(20, scoped=True, has_prefix=True,
                              agent_id=None, run_id="r", cap=500) == 160


def test_no_prefix_scoped_oversamples() -> None:
    # e.g. a non-leading dim or a topic present → no usable prefix.
    assert scoped_fetch_limit(20, scoped=True, has_prefix=False,
                              agent_id="a", run_id=None, cap=500) == 160


def test_unscoped_uses_base() -> None:
    assert scoped_fetch_limit(20, scoped=False, has_prefix=False,
                              agent_id=None, run_id=None, cap=500) == 20


def test_cap_is_respected() -> None:
    # base*8 = 800 but cap=500 (search) / 200 (recall) bounds the fetch.
    assert scoped_fetch_limit(100, scoped=True, has_prefix=False,
                              agent_id=None, run_id="r", cap=500) == 500
    assert scoped_fetch_limit(50, scoped=True, has_prefix=False,
                              agent_id=None, run_id="r", cap=200) == 200
