"""classify_write_relation — evolution vs conflict on the write path (task #48 core).

When the contradiction judge flags a new write as clashing with a stored fact, the
disposition depends on WHO said each and WHEN:

  * SAME source, new strictly newer  -> ``"evolution"``  (the source restated its own
    claim with an updated value; the old value should be superseded, not kept alongside
    it — keeping both is how a memory "confabulates" a stale answer at recall time).
  * different source, or no clear time order -> ``"conflict"`` (a genuine disagreement
    between sources; never auto-retire either on ambiguity — the conservative default).

Deterministic and source/time based — it does NOT rely on the NLI model's (absent)
temporal reasoning, which is exactly why it fixes the measured over-flag where the local
cross-encoder calls a same-source value change a contradiction.
"""
from __future__ import annotations

import types

from verimem.supersession_policy import classify_write_relation


def _f(source: str | None, created_at: float):
    vb = [f"source-doc:{source}:x"] if source else []
    return types.SimpleNamespace(verified_by=vb, created_at=created_at)


def test_same_source_newer_is_evolution():
    new = _f("acme", 2000.0)
    old = _f("acme", 1000.0)
    assert classify_write_relation(new, old) == "evolution"


def test_different_source_is_conflict():
    new = _f("acme", 2000.0)
    old = _f("globex", 1000.0)
    assert classify_write_relation(new, old) == "conflict"


def test_same_source_but_new_not_newer_is_conflict():
    # no clear "newer" (equal or older) → do NOT treat as evolution
    assert classify_write_relation(_f("acme", 1000.0), _f("acme", 1000.0)) == "conflict"
    assert classify_write_relation(_f("acme", 900.0), _f("acme", 1000.0)) == "conflict"


def test_missing_timestamp_is_conflict():
    new = types.SimpleNamespace(verified_by=["source-doc:acme:x"], created_at=None)
    old = _f("acme", 1000.0)
    assert classify_write_relation(new, old) == "conflict"


def test_both_unsourced_users_are_same_source_evolution():
    # both canonicalize to the "user" fallback → same single agent → evolution when
    # newer (documented single-agent assumption; measured under observe before enforce)
    new = types.SimpleNamespace(verified_by=[], created_at=2000.0)
    old = types.SimpleNamespace(verified_by=[], created_at=1000.0)
    assert classify_write_relation(new, old) == "evolution"
