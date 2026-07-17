"""Cycle 160 (2026-05-19) — proactive step-level fact injection.

Empirical validation cycle 159.12-14 (10 scaling experiments on IMO 2022
P5): knowledge injection beats multi-agent teams. Memory-injected single
opus closed the formal gap in 33 sec; 5/8 team setups stalled or stayed
partial. Master fact: ``03e8c1d129af``. Master episode:
``abc05354316143a19faf75997926ac50``.

This module wraps ``verimem.briefing.get_briefing(task_text=...)`` for
**step-level** use: between tool calls in a long-running task, the host
LLM can re-run a tiny proactive recall against the *current* sub-goal
without repeating the full session briefing. The complement to cycle
#53's one-shot SessionStart proactive hits.

Design:
- ``StepInjector(agent)`` keeps a per-session cache of fact ids already
  emitted, so the same fact never gets injected twice in a row.
- ``.inject(step_text, *, min_similarity=0.55, top_k=3)`` returns a
  short list of dicts ``{id, proposition, topic, similarity}`` filtered
  by the threshold and de-duplicated against the cache.
- ``.reset()`` clears the cache (e.g. when the user pivots to a new
  task; the host explicitly signals topic change).

The actual recall is delegated to ``verimem.briefing.get_briefing`` so
that the threshold semantics, error handling, and ``ENGRAM_BRIEFING_*``
env-var overrides stay in one place.

PURELY LOCAL — no LLM, no HTTP. Compatible with HOSTED MODE.

**Dependency note (verified empirically 2026-05-19 ~09:38Z):** the
``proactive_hits`` machinery inside ``briefing.get_briefing`` requires
the embedding daemon to be online. With daemon offline the semantic
recall returns no candidates and :meth:`inject` returns ``[]`` even
when relevant facts exist in the store. This is a soft fail by
design — the host LLM degrades gracefully to "no proactive injection
this step" rather than blocking. Restart the embedding worker (cycle
#59 daemon) to re-enable.
"""
from __future__ import annotations

from typing import Any

from .briefing import get_briefing


class StepInjector:
    """Recurrent proactive recall companion to ``hippo_briefing``.

    Construct once at task start, call :meth:`inject` between tool
    calls. The cache of already-emitted fact ids prevents the host LLM
    from being spammed with the same fact each step.
    """

    def __init__(self, agent: Any) -> None:
        self._agent = agent
        self._emitted: set[str] = set()

    def inject(
        self,
        step_text: str,
        *,
        min_similarity: float = 0.30,
        top_k: int = 10,
        use_hybrid: bool = True,
        semantic_weight: float = 0.6,
    ) -> list[dict[str, Any]]:
        """Return up to ``top_k`` facts most relevant to ``step_text``.

        Facts already emitted in this session are filtered out — the
        host LLM has them in context already and re-injection wastes
        tokens. Empty list when ``step_text`` is blank or no fact
        clears the threshold.

        Defaults tuned empirically (2026-05-19 cycle 160-162 bench on
        production store of 1395 facts, 100% trigger_keywords coverage):
          - ``min_similarity=0.30`` — top hits for valid recall land in
            [0.30, 0.45]. The 0.55 default of ``briefing.get_briefing``
            (cycle #53) is calibrated for one-shot prompt-time use where
            false positives are costly; step-level trades higher FPR for
            recall lift.
          - ``top_k=10`` — TPR@5=40%, TPR@10=60%, TPR@20=70% (cycle 160
            bench fact ``9379c8141a3e``). k=10 is the knee of the curve.
          - ``use_hybrid=True`` — cycle 161 fact ``83d009eb7517`` showed
            hybrid recall lifts TPR@5 from 40% → 60% on TRAIN bench and
            20% → 40% on OOD paraphrase bench. Direct path via
            ``SemanticMemory.recall_hybrid`` bypasses the briefing
            wrapper for the active retrieval; briefing still runs in
            the fallback if hybrid isn't available.
          - ``semantic_weight=0.6`` — follows fact 7defa6248327.
        """
        step = (step_text or "").strip()
        if not step:
            return []
        hits: list[dict[str, Any]] = []
        semantic = getattr(self._agent, "semantic", None)
        if use_hybrid and semantic is not None and hasattr(
            semantic, "recall_hybrid"
        ):
            # Cycle 161 path: hybrid recall direct (skips briefing wrapper).
            scored = semantic.recall_hybrid(
                step, k=top_k, semantic_weight=semantic_weight,
            )
            for fact, score in scored:
                if float(score) < min_similarity:
                    continue
                hits.append({
                    "id": getattr(fact, "id", ""),
                    "proposition": getattr(fact, "proposition", ""),
                    "topic": getattr(fact, "topic", ""),
                    "similarity": float(score),
                })
        else:
            # Fallback path: cycle #53 briefing-based proactive recall.
            payload = get_briefing(
                agent=self._agent,
                task_text=step,
                top_k_proactive=top_k,
                threshold_proactive=min_similarity,
            )
            hits = payload.get("proactive_hits", []) or []
        fresh: list[dict[str, Any]] = []
        for hit in hits:
            fid = hit.get("id", "")
            if not fid or fid in self._emitted:
                continue
            self._emitted.add(fid)
            fresh.append(hit)
        return fresh

    def reset(self) -> None:
        """Clear the cache. Use when the task pivots to an unrelated
        topic and the host wants the next ``inject`` to start fresh.
        """
        self._emitted.clear()

    @property
    def emitted_count(self) -> int:
        """Number of distinct facts injected so far in this session."""
        return len(self._emitted)
