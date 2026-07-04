"""Contradiction detection over the facts table — F#10 anti-pollution.

The bug being prevented: two facts in semantic memory claim the
OPPOSITE state of the world (e.g. 'F#5 IS in main' and 'F#5 is NOT
in main'). Neither tier flags the contradiction, so callers read
whichever surfaces first and act on stale info. These tests pin
that detection works on real data shapes.
"""
from __future__ import annotations

from engram.facts_conflict import (
    ConflictPair,
    find_conflicting_pairs,
    has_negation,
    strip_negation,
)
from engram.semantic import Fact

# ---------- polarity primitives ----------------------------------------


def test_has_negation_catches_syntactic_markers():
    """F#10-bug1: only SYNTACTIC negations count toward polarity."""
    assert has_negation("F#5 IS NOT in main")
    assert has_negation("the fix was never merged")
    assert has_negation("no longer relevant")
    assert has_negation("non ancora rilasciato")
    assert has_negation("mai stato testato")


def test_has_negation_ignores_lexical_status_markers():
    """F#10-bug1: lexical markers (broken/deprecated/rolled back/...)
    describe state, not negate clauses. They MUST NOT flip polarity
    on their own — "the broken endpoint is now fixed" is a positive
    claim, not a negative one."""
    assert not has_negation("rolled back yesterday")
    assert not has_negation("deprecated since v3")
    assert not has_negation("broken endpoint is now fixed")
    assert not has_negation("the obsolete code was finally removed")
    assert not has_negation("reverted the commit cleanly")


def test_has_negation_double_negation_resolves_to_positive():
    """F#10-bug1: parity counting — even number of negations cancels
    out. "F#5 is NOT not in main" asserts F#5 IS in main."""
    assert not has_negation("F#5 is NOT not in main")
    assert not has_negation("it's not never the case")
    assert has_negation("F#5 is NOT in main")  # single, still negative
    assert not has_negation("not not not not the bug")  # 4 negations


def test_has_negation_false_on_positive_assertions():
    assert not has_negation("F#5 is in main")
    assert not has_negation("the build passes consistently")
    assert not has_negation("deployment completed at 14:02")


def test_has_negation_handles_empty_input():
    assert not has_negation("")
    assert not has_negation(None)  # type: ignore[arg-type]


def test_strip_negation_removes_syntactic_markers():
    """F#10-bug2: markers are replaced with a stable sentinel
    (`__X__`) rather than empty space, so short stripped fragments
    don't collapse toward the model centroid."""
    assert "NOT" not in strip_negation("F#5 IS NOT in main")
    assert "F#5" in strip_negation("F#5 IS NOT in main")
    assert "main" in strip_negation("F#5 IS NOT in main")
    assert "never" not in strip_negation("the fix was never merged")
    assert "merged" in strip_negation("the fix was never merged")
    assert "non ancora" not in strip_negation("non ancora rilasciato").lower()
    assert "rilasciato" in strip_negation("non ancora rilasciato")
    assert strip_negation("") == ""


def test_strip_negation_removes_lexical_markers_too():
    """F#10-bug1+2: lexical markers are stripped (replaced with
    sentinel) so two phrasings of the same fact ("broken endpoint
    is fixed" and "endpoint is fixed") map to embedding-close
    neutral surfaces, but with sentinel substitution they preserve
    sentence length and don't collapse to the centroid."""
    out_a = strip_negation("the broken endpoint is now fixed")
    out_b = strip_negation("the endpoint is fixed")
    assert "broken" not in out_a
    assert "endpoint" in out_a and "fixed" in out_a
    # Short-input stability: stripping doesn't leave a 1-token husk.
    out_c = strip_negation("deprecated since v3")
    assert "deprecated" not in out_c
    assert "since v3" in out_c
    # Sentinel preserves positional context.
    out_d = strip_negation("the obsolete code was removed")
    assert "obsolete" not in out_d
    assert "code" in out_d and "removed" in out_d


def test_strip_negation_idempotent():
    txt = "F#5 IS NOT in main"
    once = strip_negation(txt)
    twice = strip_negation(once)
    assert once == twice  # no marker survives one pass


def test_strip_negation_short_input_stable_embedding():
    """F#10-bug2 regression — verify that the sentinel substitution
    keeps short stripped fragments anchored. Before the fix,
    `strip("rolled back yesterday") = "yesterday"` — a 1-token
    husk that the model embeds near every other terse temporal
    phrase, producing spurious cross-topic conflicts. After the
    fix, the stripped form retains a sentinel placeholder so the
    embedding stays distinct from arbitrary 1-token strings."""
    import numpy as np

    from engram import embedding
    a = strip_negation("rolled back yesterday")
    b = strip_negation("deprecated since v3")
    # Each stripped form is at least 2 tokens long (sentinel + rest).
    assert len(a.split()) >= 2
    assert len(b.split()) >= 2
    # And the two stripped forms must NOT be near-duplicates just
    # because both are short — they should preserve their unique
    # content tokens via the sentinel anchor.
    va = embedding.encode(a)
    vb = embedding.encode(b)
    cosine = float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))
    assert cosine < 0.85, (
        f"short stripped fragments collapsed to near-duplicate "
        f"(cosine={cosine:.3f}) — sentinel anchor is not working"
    )


# ---------- pair detection ---------------------------------------------


def _f(prop: str, topic: str = "hippoagent/fixes",
        confidence: float = 1.0) -> Fact:
    return Fact(proposition=prop, topic=topic, confidence=confidence)


def test_empty_pool_returns_empty():
    assert find_conflicting_pairs([]) == []
    assert find_conflicting_pairs([_f("solo fact")]) == []


def test_real_contradiction_detected():
    """The exact scenario from 2026-05-11: F#5 in main vs not in main.
    Long descriptive truth vs shorter negation — token Jaccard catches
    them via shared identifiers (`f#5`, `main`, `worktree`)."""
    a = _f("F#5 IMPLEMENTATO 2026-05-11 episode invalidation in main worktree")
    b = _f("F#5 NON ancora portato nel main worktree, autorizzazione richiesta")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.2)
    assert len(pairs) == 1, (
        f"expected 1 conflict pair, got {len(pairs)}"
    )
    conflict = pairs[0]
    assert conflict.positive.id == a.id
    assert conflict.negative.id == b.id
    assert conflict.semantic_similarity >= 0.2


def test_same_polarity_facts_are_not_a_conflict():
    """Two positive facts on the same topic are NOT a conflict —
    they might both be true paraphrases of each other."""
    a = _f("F#5 is in main as of commit a6181a36")
    b = _f("F#5 has landed in the main branch")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.5)
    assert pairs == []


def test_unrelated_facts_not_flagged():
    """A positive and a negative fact on different topics must not
    be flagged. The proposition content must be near-duplicate, not
    just the negation polarity."""
    a = _f("F#5 is in main")
    b = _f("The weekly meeting is NOT on Friday anymore")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.5)
    assert pairs == []


def test_topic_filter_narrows_pool():
    """When `topic` is given, only same-topic facts are compared."""
    a = _f("F#5 is in main", topic="hippoagent/fixes")
    b = _f("F#5 is NOT in main", topic="hippoagent/fixes")
    c = _f("F#5 is in main", topic="other/topic")
    d = _f("F#5 is NOT in main", topic="other/topic")
    pairs = find_conflicting_pairs(
        [a, b, c, d], min_overlap=0.5, topic="hippoagent/fixes",
    )
    # Only the two facts under hippoagent/fixes form a pair.
    assert len(pairs) == 1
    assert {pairs[0].positive.id, pairs[0].negative.id} == {a.id, b.id}


def test_min_semantic_filters_low_similarity():
    """A negative fact on an unrelated proposition should not be
    flagged just because polarity differs."""
    a = _f("F#5 is in main")
    b = _f("The CI runner is NOT running on Ubuntu 24")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.8)
    assert pairs == []


def test_sort_descending_by_similarity():
    """Multiple conflicts are returned sorted by sim descending."""
    a1 = _f("F#5 is in main as of today")
    b1 = _f("F#5 is NOT in main yet")
    a2 = _f("F#6 fix landed last week")
    b2 = _f("F#6 fix was never merged into main")
    pairs = find_conflicting_pairs(
        [a1, b1, a2, b2], min_overlap=0.2,
    )
    assert len(pairs) >= 2
    # Sorted descending.
    sims = [p.semantic_similarity for p in pairs]
    assert sims == sorted(sims, reverse=True)


def test_broken_endpoint_fixed_no_false_conflict():
    """F#10-bug1 regression — the false-conflict scenario the other
    Claude instance flagged. Before the fix:
      A = "the broken endpoint is now fixed"  → has_negation=True (broken)
      B = "the endpoint is fixed"             → has_negation=False
      strip(A) ≈ strip(B) → cosine ~1.0 → FALSE conflict pair flagged.
    After the fix: lexical "broken" doesn't flip polarity, so both
    sides are positive; no pair returned."""
    a = _f("the broken endpoint is now fixed")
    b = _f("the endpoint is fixed")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.5)
    assert pairs == [], (
        "lexical marker 'broken' must not flip polarity on a "
        "positive claim — got spurious conflict"
    )


def test_double_negation_no_false_conflict():
    """F#10-bug1 regression — double negation should resolve to
    positive, matching the positive paraphrase. Before the fix:
      A = "F#5 IS in main"            → has_negation=False
      B = "F#5 is NOT not in main"    → has_negation=True (OR-on-marker)
      strip(A) ≈ strip(B) → FALSE conflict pair flagged.
    After: count parity says B has 2 negations → polarity positive,
    same as A, no conflict."""
    a = _f("F#5 IS in main")
    b = _f("F#5 is NOT not in main")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.5)
    assert pairs == []


def test_real_contradiction_still_detected_after_bug1_fix():
    """F#21 falsification — the canonical real-world case. Before the
    Jaccard rewrite, cosine on stripped sentinel form gave 0.597 here,
    below every reasonable threshold (default was 0.78). The pair
    shared `f#5` + `main` + `in` content tokens, which Jaccard catches
    even though the long tail (`as of commit a6181a36`) makes the
    propositions semantically distant."""
    a = _f("F#5 IS in main as of commit a6181a36")
    b = _f("F#5 is NOT in main yet")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.3)
    assert len(pairs) == 1
    assert pairs[0].positive.id == a.id
    assert pairs[0].negative.id == b.id


def test_find_conflicting_scales_to_100_facts():
    """F#10-bug3 regression — verify the batched/vectorised path
    handles a 100+ fact pool without quadratic-call-cost blowup,
    and that polarity splitting still surfaces conflicts."""
    import time
    facts: list[Fact] = []
    for i in range(50):
        facts.append(_f(f"F#{i} is in main"))
        facts.append(_f(f"F#{i} is NOT in main"))
    t0 = time.perf_counter()
    pairs = find_conflicting_pairs(facts, min_overlap=0.5)
    elapsed = time.perf_counter() - t0
    # Each F#{i} positive matches its F#{i} negative — exactly 50
    # pairs expected (the cross-i pairs share only `main` so Jaccard
    # is well below 0.5).
    assert len(pairs) >= 50, (
        f"expected ≥ 50 conflict pairs on 100-fact pool, got {len(pairs)}"
    )
    # Performance pinning: 100 facts must complete under 5s including
    # the model load on a CI runner. Real measurements: ~200 ms.
    assert elapsed < 5.0, (
        f"100-fact scan took {elapsed:.1f}s — quadratic regression?"
    )


def test_find_conflicting_no_pairs_when_all_positive():
    """F#10-bug3: the polarity split short-circuits when one side
    is empty. Verifies the optimisation correctness."""
    facts = [_f(f"F#{i} is fine") for i in range(10)]
    assert find_conflicting_pairs(facts, min_overlap=0.5) == []


def test_find_conflicting_no_pairs_when_all_negative():
    """Symmetric to above — only negatives means no candidates."""
    facts = [_f(f"F#{i} is NOT in main") for i in range(10)]
    assert find_conflicting_pairs(facts, min_overlap=0.5) == []


def test_conflict_pair_as_dict_serializable():
    a = _f("F#5 is in main")
    b = _f("F#5 is NOT in main")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.5)
    assert len(pairs) == 1
    d = pairs[0].as_dict()
    assert d["positive"]["id"] == a.id
    assert d["negative"]["id"] == b.id
    assert "semantic_similarity" in d
    assert isinstance(d["semantic_similarity"], float)


# ---------- cycle 161 precision fix -----------------------------------
# Empirical audit 2026-05-19: sample N=30 random pair on production
# corpus (1361 facts) showed precision = 0/30 (100% FP). Two FP
# patterns dominated:
#   (a) lab-stress noise facts (project/lab/stress-w0/w1) paired with
#       unrelated MASTER nodes via 2-token overlap on common glue
#       tokens. 9/30 sample.
#   (b) test-transient facts (topic prefix test/) paired across
#       sessions. 8/30 sample.
# Fix: add `exclude_topic_prefixes` knob with sensible defaults
# (`lab/`, `project/lab/`, `test/`) to drop these from the pool BEFORE
# polarity split.


def test_excludes_lab_stress_topic_prefix():
    """A lab-stress fact must not pair with any other fact, even if
    polarity-opposite. Empirical FP pattern from audit cycle 161."""
    a = _f("Lab stress test worker 1 write 20 ts=1779017247.995",
            topic="project/lab/stress-w1")
    b = _f("CYCLE 142 RESULT NOT achieved 2026-05-18 worker test",
            topic="lessons/cycle142")
    # Default exclude_topic_prefixes should drop the lab/ fact.
    pairs = find_conflicting_pairs([a, b], min_overlap=0.2)
    assert pairs == [], (
        "lab-stress topic must be excluded by default — got FP pair"
    )


def test_excludes_test_topic_prefix():
    """Same for transient test/ facts — they pollute the conflict
    surface with 2-token overlap matches against unrelated work."""
    a = _f("TEST topic semplice — fact transient verifica bug",
            topic="test/topic-bug-investigation-A")
    b = _f("Cycle 138 NOT confab gate test verifica",
            topic="lessons/cycle138")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.2)
    assert pairs == [], (
        "test/ topic prefix must be excluded by default — got FP pair"
    )


def test_exclude_topic_prefixes_param_override():
    """Caller can override the exclusion list when they want to audit
    the noise corpus itself (e.g. cleanup pipeline)."""
    a = _f("Lab stress test worker 1 write 20",
            topic="project/lab/stress-w1")
    b = _f("Lab stress test worker 1 write NOT 20",
            topic="project/lab/stress-w1")
    # Empty tuple disables the default filter.
    pairs = find_conflicting_pairs(
        [a, b], min_overlap=0.3, exclude_topic_prefixes=(),
    )
    assert len(pairs) == 1, (
        "explicit empty exclusion must re-enable lab-stress pairing"
    )


def test_real_contradiction_survives_default_exclusion():
    """The legit production-style pair (no lab/test prefix) must still
    be flagged with the new defaults. Regression guard."""
    a = _f("F#5 IS in main as of commit a6181a36",
            topic="hippoagent/fixes")
    b = _f("F#5 is NOT in main yet", topic="hippoagent/fixes")
    pairs = find_conflicting_pairs([a, b], min_overlap=0.3)
    assert len(pairs) == 1, (
        "default exclusion must not break real-contradiction detection"
    )
