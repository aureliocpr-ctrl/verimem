"""TDD for engram/local_relation.py — the LOCAL NLI RelationJudge.

The reconcile / semantic-conflict layer needs a 3-way (contradiction / entailment /
neutral) judge. Until now the only judge was LLMRelationJudge = claude -p (deferred
"to capacity"). This is the subscription-independent one: a cached NLI cross-encoder.

Unit tests inject the classifier (a callable returning per-label probabilities), so
they never load transformers or a model. The decision logic (symmetric combine,
thresholds, fail-safe→NEUTRAL) is what is pinned here; the real model is smoke-tested
live (benchmark, GPU).
"""
from __future__ import annotations

import pytest

from engram.local_relation import LocalRelationJudge
from engram.semantic_conflict import Relation, RelationJudge


class StubClassifier:
    """Maps (premise, hypothesis) pairs to label-prob dicts by a scripted table
    keyed on an ordered pair of substrings; records calls."""

    def __init__(self, table, default=None):
        self.table = table
        self.default = default or {"contradiction": 0.0, "entailment": 0.0,
                                   "neutral": 1.0}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, pairs):
        out = []
        for a, b in pairs:
            self.calls.append((a, b))
            probs = self.default
            for (na, nb), p in self.table.items():
                if na in a and nb in b:
                    probs = p
                    break
            out.append(probs)
        return out


def _C(x=0.9):  # contradiction-dominant
    return {"contradiction": x, "entailment": 0.02, "neutral": 1 - x - 0.02}


def _E(x=0.9):  # entailment-dominant
    return {"contradiction": 0.02, "entailment": x, "neutral": 1 - x - 0.02}


def _N():
    return {"contradiction": 0.1, "entailment": 0.1, "neutral": 0.8}


def test_is_a_relation_judge():
    judge = LocalRelationJudge(classifier=StubClassifier({}))
    assert isinstance(judge, RelationJudge)


def test_default_model_is_the_precise_one():
    # Pre-registered: the default is the high-precision large NLI model, not the base.
    # The reconcile bench (n=60) picked it — false-supersede 0.196→0.054 at equal
    # recall. Changing this default must be a conscious, test-visible decision.
    from engram.local_relation import DEFAULT_NLI_MODEL
    assert DEFAULT_NLI_MODEL == "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"


def test_contradiction_detected():
    clf = StubClassifier({("Rome", "Paris"): _C(), ("Paris", "Rome"): _C()})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("John lives in Rome", "John lives in Paris") is Relation.CONTRADICTION


def test_entailment_needs_both_directions():
    # both directions entail -> ENTAILMENT (paraphrase/duplicate)
    clf = StubClassifier({("runs", "jogs"): _E(), ("jogs", "runs"): _E()})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("She runs daily", "She jogs daily") is Relation.ENTAILMENT


def test_one_way_entailment_is_not_duplicate():
    # A entails B but not vice versa (B is broader) -> NOT a duplicate -> NEUTRAL
    clf = StubClassifier({("poodle", "dog"): _E(), ("dog", "poodle"): _N()})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("She owns a poodle", "She owns a dog") is Relation.NEUTRAL


def test_complementary_same_subject_is_neutral():
    # same subject, different attribute — the precision case the lexical path fails
    clf = StubClassifier({("Rome", "30"): _N(), ("30", "Rome"): _N()})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("John lives in Rome", "John is 30") is Relation.NEUTRAL


def test_contradiction_is_symmetric_recall():
    # only ONE direction fires contradiction (NLI is asymmetric) -> still CONTRADICTION
    clf = StubClassifier({("Rome", "Paris"): _N(), ("Paris", "Rome"): _C()})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("John lives in Rome", "John lives in Paris") is Relation.CONTRADICTION


def test_threshold_respected():
    clf = StubClassifier({("a", "b"): {"contradiction": 0.4, "entailment": 0.3,
                                       "neutral": 0.3}}, )
    strict = LocalRelationJudge(classifier=clf, contradiction_threshold=0.5)
    loose = LocalRelationJudge(classifier=clf, contradiction_threshold=0.35)
    assert strict.classify("a x", "b y") is Relation.NEUTRAL
    assert loose.classify("a x", "b y") is Relation.CONTRADICTION


def test_classifier_error_fails_safe_to_neutral():
    def boom(pairs):
        raise RuntimeError("model exploded")
    judge = LocalRelationJudge(classifier=boom)
    # a judge error must NEVER fabricate a contradiction that impugns a true fact
    assert judge.classify("x", "y") is Relation.NEUTRAL


def test_batch_classify_preserves_order():
    clf = StubClassifier({("Rome", "Paris"): _C(), ("Paris", "Rome"): _C(),
                          ("cat", "cat"): _E()})
    judge = LocalRelationJudge(classifier=clf)
    rels = judge.classify_batch([
        ("John in Rome", "John in Paris"),
        ("a cat", "a cat"),
    ])
    assert rels == [Relation.CONTRADICTION, Relation.ENTAILMENT]


def test_empty_inputs_are_neutral_without_calling_model():
    clf = StubClassifier({})
    judge = LocalRelationJudge(classifier=clf)
    assert judge.classify("", "something") is Relation.NEUTRAL
    assert judge.classify("something", "") is Relation.NEUTRAL
    assert clf.calls == []  # short-circuited, no model call


# ---- the real model factory: label order is read from config, never hardcoded ----

def test_make_classifier_maps_by_id2label(monkeypatch):
    """Two cached NLI models use OPPOSITE label orders (nli-deberta-v3-base:
    0=contradiction; MoritzLaurer: 0=entailment). The factory MUST map via the
    model's own id2label, not positional indices."""
    import engram.local_relation as LR

    class FakeTok:
        def __call__(self, prem, hyp, **kw):
            return {"input_ids": [[0]]}

    class FakeLogits:
        def __init__(self, rows): self._rows = rows
        def squeeze(self, *_a): return self
        def tolist(self): return self._rows

    captured = {}

    def fake_softmax(logits):
        captured["softmaxed"] = True
        return logits

    # id2label with contradiction at index 2 (MoritzLaurer order)
    made = LR._build_label_mapper({0: "entailment", 1: "neutral", 2: "contradiction"})
    # a row whose argmax index is 2 must map to 'contradiction'
    probs = made([0.1, 0.2, 0.7])
    assert probs["contradiction"] == pytest.approx(0.7)
    assert probs["entailment"] == pytest.approx(0.1)
    assert probs["neutral"] == pytest.approx(0.2)

    # opposite order (nli-deberta-v3-base): contradiction at index 0
    made2 = LR._build_label_mapper({0: "contradiction", 1: "entailment", 2: "neutral"})
    probs2 = made2([0.7, 0.2, 0.1])
    assert probs2["contradiction"] == pytest.approx(0.7)
    assert probs2["entailment"] == pytest.approx(0.2)
