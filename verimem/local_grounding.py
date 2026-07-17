"""Local write-gate judge — the distilled CE backend for the grounding gate.

Why this exists: the write-gate's judge (``grounding_gate.fact_grounding_score``)
costs one ``claude -p`` call per candidate fact; headless subscription calls are
moving to paid, so the gate needs a subscription-independent backend. The model is a
cross-encoder fine-tuned on HaluMem ground truth (``benchmark/local_gate_finetune.py``)
with a binary head: sigmoid(logit)*100 on (source_span, fact) — same 0-100 scale as
the claude judge, thresholded by the gate.

Selection is env-gated and OFF by default (``ENGRAM_GROUNDING_BACKEND=local`` to opt
in; anything else = the injected-llm claude path, unchanged). The model directory is
``ENGRAM_LOCAL_GATE_MODEL`` or ``~/.engram/models/local_gate_ce`` and may carry a
``gate_config.json`` written by the fine-tune run ({threshold, focus_budget, ...});
env thresholds always beat the config (see ``grounding_gate.should_store_fact``).

Injection-only testability (house style, like cross_encoder_rerank): the judge takes
an optional ``scorer`` callable so unit tests never load transformers or download a
model; the real model is lazy-loaded on first use, behind a lock (the write path can
be called from multiple threads).
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from verimem.grounding_gate import select_relevant_span

Scorer = Callable[[list[tuple[str, str]]], list[float]]

_ENV_MODEL_DIR = "ENGRAM_LOCAL_GATE_MODEL"
# v2 (2026-07-02) is the shipped model: same HaluMem skill as v1 (heldout AUROC 0.99,
# false-memory admit 0.042 vs v1's 0.086) PLUS the real-corpus register (real-fact
# admit 0.82→0.98, agreement vs claude 0.76→0.88). Trained by distilling the claude
# DECISION on a mixed HaluMem-GT + real-corpus set (benchmark/local_gate_distill_v2.py).
# v1 (local_gate_ce) is kept on disk for comparison. Override with ENGRAM_LOCAL_GATE_MODEL.
DEFAULT_MODEL_DIR = Path.home() / ".engram" / "models" / "local_gate_ce_v2"
_DEFAULT_FOCUS_BUDGET = 1500


def _resolve_model_dir(model_dir: str | Path | None) -> Path:
    env = os.environ.get(_ENV_MODEL_DIR, "").strip()
    return Path(env or model_dir or DEFAULT_MODEL_DIR).expanduser()


def make_finetuned_scorer(model_dir: str | Path, *, max_length: int = 512,
                          batch_size: int = 32) -> Scorer:
    """Production scorer over the saved binary-head CE: sigmoid(logit)*100 per
    (premise, hypothesis) pair. Imports transformers lazily."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir)).to(device).eval()

    @torch.no_grad()
    def scorer(batch: list[tuple[str, str]]) -> list[float]:
        out: list[float] = []
        for i in range(0, len(batch), batch_size):
            chunk = batch[i:i + batch_size]
            enc = tok([p for p, _ in chunk], [h for _, h in chunk],
                      truncation="longest_first", max_length=max_length,
                      padding=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits.squeeze(-1)
            out.extend((torch.sigmoid(logits) * 100.0).float().cpu().tolist())
        return out

    return scorer


class LocalGroundingJudge:
    """Scores source ⊢ fact in [0, 100] with the local CE. The source is reduced to
    its fact-relevant span (production selector) before scoring — the CE window is
    512 tokens."""

    def __init__(self, model_dir: str | Path | None = None, *,
                 scorer: Scorer | None = None, max_length: int = 512,
                 focus_budget: int | None = None):
        self.model_dir = _resolve_model_dir(model_dir)
        self._scorer = scorer
        self._lock = threading.Lock()
        self.max_length = max_length
        self._focus_budget = focus_budget
        self._config: dict[str, Any] | None = None
        self._load_failed = False

    @property
    def config(self) -> dict[str, Any]:
        """gate_config.json from the model dir ({} when absent/corrupt)."""
        if self._config is None:
            try:
                self._config = json.loads(
                    (self.model_dir / "gate_config.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._config = {}
        return self._config

    @property
    def threshold(self) -> float | None:
        t = self.config.get("threshold")
        return float(t) if isinstance(t, (int, float)) else None

    @property
    def focus_budget(self) -> int:
        if self._focus_budget:
            return int(self._focus_budget)
        b = self.config.get("focus_budget")
        return int(b) if isinstance(b, (int, float)) and b > 0 else _DEFAULT_FOCUS_BUDGET

    def _ensure_scorer(self) -> Scorer:
        if self._scorer is None:
            if self._load_failed:
                raise RuntimeError(f"local gate model unavailable: {self.model_dir}")
            with self._lock:
                if self._scorer is None:
                    t0 = time.time()
                    try:
                        self._scorer = make_finetuned_scorer(
                            self.model_dir, max_length=self.max_length)
                    except Exception:
                        # cache the failure: a broken/absent model must not re-pay
                        # the load attempt on every gated write
                        self._load_failed = True
                        raise
                    self.load_s = round(time.time() - t0, 1)
        return self._scorer

    def score(self, source: str, fact: str, *,
              focus_budget: int | None = None) -> float:
        budget = int(focus_budget) if focus_budget else self.focus_budget
        span = select_relevant_span(source or "", fact or "", budget=budget)
        val = self._ensure_scorer()([(span, fact or "")])[0]
        return min(100.0, max(0.0, float(val)))


_judge: LocalGroundingJudge | None = None
_judge_lock = threading.Lock()


def get_local_judge() -> LocalGroundingJudge:
    """Process-wide lazy singleton (model loads once)."""
    global _judge
    if _judge is None:
        with _judge_lock:
            if _judge is None:
                _judge = LocalGroundingJudge()
    return _judge


def set_local_judge(judge: LocalGroundingJudge | None) -> None:
    """Inject a judge (tests) — pass None to clear."""
    global _judge
    _judge = judge


def reset_local_judge() -> None:
    set_local_judge(None)


def get_local_threshold() -> float | None:
    """The fine-tune-calibrated admission threshold, if the model ships one."""
    return get_local_judge().threshold


_warned_fallback = False


def try_local_score(source: str, fact: str, *,
                    focus_budget: int | None = None,
                    ) -> tuple[float, float | None] | None:
    """(score, config_threshold) via the local judge, or None when the local model is
    unavailable (the caller falls back to its injected llm at the CLAUDE-scale
    threshold — the config cut must never be applied to a claude-scale score). The
    load failure is cached; the fallback warning fires once per process."""
    global _warned_fallback
    judge = get_local_judge()
    try:
        score = judge.score(source, fact, focus_budget=focus_budget)
    except Exception:  # noqa: BLE001 — any load/inference failure -> fail over
        if not _warned_fallback:
            _warned_fallback = True
            import warnings
            warnings.warn(
                f"ENGRAM_GROUNDING_BACKEND=local but the model at {judge.model_dir} "
                f"is unavailable — falling back to the injected llm judge",
                RuntimeWarning, stacklevel=2)
        return None
    return score, judge.threshold


__all__ = ["LocalGroundingJudge", "make_finetuned_scorer", "get_local_judge",
           "set_local_judge", "reset_local_judge", "get_local_threshold",
           "try_local_score", "DEFAULT_MODEL_DIR"]
