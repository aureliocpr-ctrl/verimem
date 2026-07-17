"""Local NLI RelationJudge — the subscription-independent contradiction/entailment
judge for the reconcile + semantic-conflict layer.

Why this exists: ``semantic_conflict.LLMRelationJudge`` needs one ``claude -p`` call
per candidate pair (after the cosine pre-filter). Headless subscription calls are
moving to paid, and the truth-maintenance work (evolving facts — the differentiator
category mem0/Tencent don't hold) was "deferred to capacity" for exactly this reason.
This judge runs a cached NLI cross-encoder locally instead: zero claude -p, ~ms/pair
on GPU, offline.

It plugs in unchanged wherever a ``RelationJudge`` is accepted
(``SemanticMemory.set_reconcile_judge`` / ``reconcile_new_fact(judge=...)`` /
``detect_semantic_conflicts``).

Design (mirrors ``local_grounding``): the classifier is INJECTED — a callable
``list[(premise, hypothesis)] -> list[{label: prob}]`` — so unit tests pin the
decision logic with a stub and never load transformers. The real model is lazy-loaded
behind a lock and its label order is read from the model's own ``id2label`` (two
cached NLI models use OPPOSITE orders — nli-deberta-v3-base has contradiction at index
0, MoritzLaurer at index 2 — so positional indexing would silently invert the verdict).

Decision logic — symmetric, precision-biased (same asymmetry as the rest of the
anti-confab stack; a wrong CONTRADICTION impugns a true fact, a wrong NEUTRAL only
misses a warning):
  * NLI is directional, so both (a,b) and (b,a) are scored.
  * CONTRADICTION if EITHER direction's contradiction prob ≥ ``contradiction_threshold``
    (recall-oriented: a real conflict need only surface once).
  * ENTAILMENT (duplicate) only if BOTH directions' entailment prob ≥
    ``entailment_threshold`` (a one-way entailment is a broader/narrower fact, not a
    duplicate — must not be flagged as one).
  * NEUTRAL otherwise, and as the fail-safe on any model error or empty input.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from verimem.semantic_conflict import Relation

# label→prob for one pair; a classifier maps a batch of pairs to these.
LabelProbs = dict[str, float]
Classifier = Callable[[list[tuple[str, str]]], list[LabelProbs]]

_ENV_MODEL = "ENGRAM_LOCAL_NLI_MODEL"
# Default: MoritzLaurer DeBERTa-v3-large (MNLI+FEVER+ANLI+ling+wanli). Chosen for
# PRECISION over speed — the reconcile bench (HaluMem is_update GT, n=60) showed it
# holds update-recall (0.35 base → 0.33 large) while cutting false-supersede on the
# same-subject complementary control 0.196 → 0.054 (−73%). Precision is what matters
# here: a wrong CONTRADICTION supersedes a TRUE fact. The judge runs only on cosine-
# prefiltered pairs, so its extra latency is bounded. Override with the faster/smaller
# ``cross-encoder/nli-deberta-v3-base`` via the env when speed dominates.
DEFAULT_NLI_MODEL = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"

_DEFAULT_CONTRADICTION_THR = 0.5
_DEFAULT_ENTAILMENT_THR = 0.5


def _build_label_mapper(id2label: dict[int, str]) -> Callable[[list[float]], LabelProbs]:
    """Return a fn mapping a per-class probability ROW to a {label: prob} dict using
    the model's own id2label (canonicalized to the three NLI names). Never positional:
    the cached models disagree on index order."""
    canon: dict[int, str] = {}
    for idx, name in id2label.items():
        low = str(name).strip().lower()
        if low.startswith("contradict"):
            canon[int(idx)] = "contradiction"
        elif low.startswith("entail"):
            canon[int(idx)] = "entailment"
        else:
            canon[int(idx)] = "neutral"

    def mapper(row: list[float]) -> LabelProbs:
        out = {"contradiction": 0.0, "entailment": 0.0, "neutral": 0.0}
        for idx, p in enumerate(row):
            out[canon.get(idx, "neutral")] = float(p)
        return out

    return mapper


def make_nli_classifier(model_name: str, *, max_length: int = 256,
                        batch_size: int = 32) -> Classifier:
    """Production classifier over a cached NLI cross-encoder: softmax(logits) mapped
    to {contradiction, entailment, neutral} via the model's id2label. Lazy transformers
    import; runs on CUDA when available."""
    import torch
    from transformers import (
        AutoConfig,
        AutoModelForSequenceClassification,
        AutoTokenizer,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    cfg = AutoConfig.from_pretrained(model_name)
    mapper = _build_label_mapper(dict(cfg.id2label))
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name).to(device).eval()

    @torch.no_grad()
    def classifier(pairs: list[tuple[str, str]]) -> list[LabelProbs]:
        out: list[LabelProbs] = []
        for i in range(0, len(pairs), batch_size):
            chunk = pairs[i:i + batch_size]
            enc = tok([p for p, _ in chunk], [h for _, h in chunk],
                      truncation=True, max_length=max_length, padding=True,
                      return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().tolist()
            out.extend(mapper(row) for row in probs)
        return out

    return classifier


class LocalRelationJudge:
    """A ``RelationJudge`` backed by a local NLI cross-encoder (no claude -p)."""

    def __init__(self, model_name: str | None = None, *,
                 classifier: Classifier | None = None,
                 contradiction_threshold: float = _DEFAULT_CONTRADICTION_THR,
                 entailment_threshold: float = _DEFAULT_ENTAILMENT_THR,
                 max_length: int = 256) -> None:
        self.model_name = (model_name or os.environ.get(_ENV_MODEL, "").strip()
                           or DEFAULT_NLI_MODEL)
        self._classifier = classifier
        self.contradiction_threshold = float(contradiction_threshold)
        self.entailment_threshold = float(entailment_threshold)
        self.max_length = max_length
        self._lock = threading.Lock()
        self._load_failed = False

    def _ensure_classifier(self) -> Classifier:
        if self._classifier is None:
            if self._load_failed:
                raise RuntimeError(f"local NLI model unavailable: {self.model_name}")
            with self._lock:
                if self._classifier is None:
                    try:
                        self._classifier = make_nli_classifier(
                            self.model_name, max_length=self.max_length)
                    except Exception:
                        self._load_failed = True
                        raise
        return self._classifier

    def _decide(self, ab: LabelProbs, ba: LabelProbs) -> Relation:
        p_contra = max(ab.get("contradiction", 0.0), ba.get("contradiction", 0.0))
        if p_contra >= self.contradiction_threshold:
            return Relation.CONTRADICTION
        p_entail = min(ab.get("entailment", 0.0), ba.get("entailment", 0.0))
        if p_entail >= self.entailment_threshold:
            return Relation.ENTAILMENT
        return Relation.NEUTRAL

    def classify(self, a: str, b: str) -> Relation:
        if not (a or "").strip() or not (b or "").strip():
            return Relation.NEUTRAL
        try:
            ab, ba = self._ensure_classifier()([(a, b), (b, a)])
        except Exception:  # noqa: BLE001 — never fabricate a contradiction on error
            return Relation.NEUTRAL
        return self._decide(ab, ba)

    def classify_batch(self, pairs: list[tuple[str, str]]) -> list[Relation]:
        """Order-preserving batch classify. Empty pairs → NEUTRAL without a model
        call; the rest are scored in BOTH directions in one classifier batch."""
        out: list[Relation | None] = [None] * len(pairs)
        flat: list[tuple[str, str]] = []
        index: list[int] = []
        for i, (a, b) in enumerate(pairs):
            if not (a or "").strip() or not (b or "").strip():
                out[i] = Relation.NEUTRAL
            else:
                index.append(i)
                flat.append((a, b))
                flat.append((b, a))
        if flat:
            try:
                scored = self._ensure_classifier()(flat)
            except Exception:  # noqa: BLE001
                scored = None
            for k, i in enumerate(index):
                if scored is None:
                    out[i] = Relation.NEUTRAL
                else:
                    out[i] = self._decide(scored[2 * k], scored[2 * k + 1])
        return [r if r is not None else Relation.NEUTRAL for r in out]


_judge: LocalRelationJudge | None = None
_judge_lock = threading.Lock()


def get_local_relation_judge() -> LocalRelationJudge:
    """Process-wide lazy singleton (model loads once)."""
    global _judge
    if _judge is None:
        with _judge_lock:
            if _judge is None:
                _judge = LocalRelationJudge()
    return _judge


def set_local_relation_judge(judge: LocalRelationJudge | None) -> None:
    global _judge
    _judge = judge


__all__ = [
    "LocalRelationJudge", "make_nli_classifier", "get_local_relation_judge",
    "set_local_relation_judge", "DEFAULT_NLI_MODEL",
]


_ = (Path, Any)  # keep import surface stable for the model factory / typing
