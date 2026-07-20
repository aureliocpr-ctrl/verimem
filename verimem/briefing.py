"""Curated session-context briefing.

FORGIA pezzo #214 — Wave 13. A single function that assembles
"everything Claude Code should know at the start of a conversation"
in one structured payload + a deterministic summary.

Differs from the SessionStart hook (`hooks/hippo_session_start.py`)
only in entry point: the hook runs at session creation time, this
runs on-demand via the MCP tool `hippo_briefing`. Useful when the
user mid-session says "ricaricami il contesto memoria" or after a
manual `/clear`.

PURELY LOCAL — no LLM. Compatible with HOSTED MODE.
"""
from __future__ import annotations

import os
from typing import Any

from ._call_telemetry import is_call_telemetry

# Semantic relevance for the correction signal: instead of 4-token overlap (which
# misses paraphrased tasks), recall the episodes whose MEANING matches the task
# (cosine over summary embeddings) and feed THOSE to detect_correction_pattern.
# Validated 2026-06-13 on the real corpus: 25 semantic clusters of >=3 episodes at
# cosine>=0.85 that the token signature missed (different words, same work).
_CORRECTION_RECALL_K = int(os.environ.get("ENGRAM_BRIEFING_CORRECTION_K", "50") or "50")
_CORRECTION_MIN_SIM = float(
    os.environ.get("ENGRAM_BRIEFING_CORRECTION_MIN_SIM", "0.7") or "0.7"
)

# Cross-LLM critic/ask calls (ask_agy / ask_gemini / …) are auto-recorded as
# episodes by the bridge: 2026-06-13 the live corpus was 123/554 (22%) such rows.
# They are MACHINE telemetry, not user tasks — they pollute the recent-episode
# list a human reads AND dilute the emerging/correction/risk signals. Hide them.
# SINGLE SOURCE OF TRUTH = verimem._call_telemetry, SHARED with the WRITE-time
# episode gate (verimem.memory) so the read-side filter and the write-side router
# can never drift (the critic flagged the earlier duplicated regex here).
def _is_call_telemetry_episode(ep: Any) -> bool:
    """True when the episode's task_text is a cross-LLM call record, not a task."""
    return is_call_telemetry(getattr(ep, "task_text", ""))


def _safe_count(obj: Any, attr: str = "count") -> int:
    """Best-effort `count()` via duck-typing. Returns -1 on error."""
    try:
        fn = getattr(obj, attr, None)
        if callable(fn):
            return int(fn())
    except Exception:
        pass
    return -1


def get_briefing(
    *,
    agent: Any,
    n_facts: int = 8,
    n_pinned: int = 5,
    n_recent_episodes: int = 5,
    n_top_skills: int = 5,
    task_text: str | None = None,
    top_k_proactive: int = 3,
    threshold_proactive: float = 0.55,
) -> dict[str, Any]:
    """Assemble a curated session-context briefing from the agent's
    three memory tiers.

    Args:
      - `agent`: HippoAgent (or duck-type with `.skills`, `.memory`,
        `.semantic`).
      - `n_facts`: cap on recent facts returned.
      - `n_pinned`: cap on pinned episodes returned.
      - `n_recent_episodes`: cap on recent (any-state) episodes.
      - `n_top_skills`: cap on top-by-fitness skills returned.

    CYCLE #53 (2026-05-14) — proactive semantic recall:
      - `task_text`: if provided and non-empty, the briefing also
        runs a semantic recall against the facts store and returns
        the top hits whose cosine similarity to `task_text` is at
        least `threshold_proactive`. This is the PUSH companion to
        the on-demand PULL of `hippo_recall` / `hippo_facts_recall`.
      - `top_k_proactive`: cap on hits returned (default 3).
      - `threshold_proactive`: minimum cosine similarity (default
        0.55, the median "strong correlation" point on the
        MiniLM-L6-v2 normalized embedding distribution). Override via
        env `ENGRAM_BRIEFING_THRESHOLD` at the call site if you
        want a session-wide default.

    Returns: dict with keys `summary_text`, `stats`, `recent_facts`,
    `pinned_episodes`, `recent_episodes`, `top_skills`, and
    (cycle #53) `proactive_hits` (always present; empty when no
    task_text or no hits above threshold).
    """
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)
    semantic = getattr(agent, "semantic", None)

    # --- Stats ---------------------------------------------------------
    ep_count = _safe_count(memory)
    sk_count = _safe_count(skills_store)
    fact_count = _safe_count(semantic)

    success_count = 0
    failure_count = 0
    if memory is not None and hasattr(memory, "all"):
        try:
            for ep in memory.all():
                outcome = getattr(ep, "outcome", "")
                if outcome == "success":
                    success_count += 1
                elif outcome == "failure":
                    failure_count += 1
        except Exception:
            pass

    # --- Recent facts --------------------------------------------------
    recent_facts: list[dict[str, Any]] = []
    if semantic is not None and hasattr(semantic, "list_facts"):
        try:
            # hide_low_trust: the briefing is memory injected into the
            # session — it must not present quarantined/orphaned/user_belief
            # rows as "recent facts" (context poisoning). The analysis tools
            # that also call list_facts keep the default (whole corpus).
            facts = semantic.list_facts(limit=n_facts, offset=0,
                                        hide_low_trust=True)
            for f in facts:
                recent_facts.append({
                    "id": getattr(f, "id", ""),
                    "proposition": getattr(f, "proposition", ""),
                    "topic": getattr(f, "topic", ""),
                    "created_at": float(getattr(f, "created_at", 0.0)),
                })
        except Exception:
            recent_facts = []

    # --- Pinned episodes ----------------------------------------------
    pinned_episodes: list[dict[str, Any]] = []
    if memory is not None and hasattr(memory, "pinned_episodes"):
        try:
            pinned = memory.pinned_episodes(limit=n_pinned)
            for ep in pinned:
                pinned_episodes.append({
                    "id": getattr(ep, "id", ""),
                    "task_text": (getattr(ep, "task_text", "") or "")[:200],
                    "outcome": getattr(ep, "outcome", ""),
                })
        except Exception:
            pinned_episodes = []

    # --- Recent episodes (regardless of pin) --------------------------
    recent_episodes: list[dict[str, Any]] = []
    if memory is not None and hasattr(memory, "all"):
        try:
            # Oversample, then drop cross-LLM call telemetry so a human sees REAL
            # recent tasks, not ask_agy/ask_gemini exhaust. Cap back to n.
            recent = memory.all(limit=max(n_recent_episodes * 6, n_recent_episodes))
            for ep in recent:
                if _is_call_telemetry_episode(ep):
                    continue
                recent_episodes.append({
                    "id": getattr(ep, "id", ""),
                    "task_text": (getattr(ep, "task_text", "") or "")[:200],
                    "outcome": getattr(ep, "outcome", ""),
                })
                if len(recent_episodes) >= n_recent_episodes:
                    break
        except Exception:
            recent_episodes = []

    # --- Top skills by fitness ---------------------------------------
    top_skills: list[dict[str, Any]] = []
    if skills_store is not None and hasattr(skills_store, "all"):
        try:
            all_skills = skills_store.all()
            scored = [
                (s, float(getattr(s, "fitness_mean", 0.0)))
                for s in all_skills
            ]
            scored.sort(key=lambda x: -x[1])
            for s, fm in scored[:n_top_skills]:
                top_skills.append({
                    "id": getattr(s, "id", ""),
                    "name": getattr(s, "name", ""),
                    "fitness_mean": fm,
                    "trials": int(getattr(s, "trials", 0)),
                    "successes": int(getattr(s, "successes", 0)),
                    "status": getattr(s, "status", ""),
                })
        except Exception:
            top_skills = []

    # --- Stats payload -----------------------------------------------
    stats = {
        "episodes": ep_count,
        "episodes_success": success_count,
        "episodes_failure": failure_count,
        "facts": fact_count,
        "skills": sk_count,
    }

    # --- CYCLE #53: proactive semantic recall -------------------------
    # When task_text is provided, surface facts most relevant to it so
    # the caller (host LLM) sees them at briefing time instead of
    # having to remember to call hippo_recall explicitly. PUSH companion
    # to the on-demand PULL tools.
    proactive_hits: list[dict[str, Any]] = []
    task_text_clean = (task_text or "").strip() if task_text else ""
    if task_text_clean and semantic is not None and hasattr(semantic, "recall"):
        try:
            # Pull k*2 candidates so we have headroom after thresholding.
            # The semantic.recall already orders by similarity desc.
            top_k = max(1, int(top_k_proactive))
            thr = max(0.0, min(1.0, float(threshold_proactive)))
            raw_hits = semantic.recall(task_text_clean, k=top_k * 2)
            for fact, sim in raw_hits:
                if sim < thr:
                    continue
                proactive_hits.append({
                    "id": getattr(fact, "id", ""),
                    "proposition": (
                        getattr(fact, "proposition", "") or ""
                    )[:200],
                    "topic": getattr(fact, "topic", ""),
                    "similarity": float(sim),
                    "created_at": float(getattr(fact, "created_at", 0.0)),
                })
                if len(proactive_hits) >= top_k:
                    break
        except Exception:  # noqa: BLE001
            # Recall failure must NOT abort the whole briefing — keep
            # the static parts of the payload usable.
            proactive_hits = []

    # --- Atomic idea #1: emerging-task early-warning -----------------
    # PUSH (not pull): when task_text matches a RISING task signature, surface
    # the recent same-signature episodes so the session accelerates what you're
    # getting good at instead of re-deriving it. Best-effort: a failure here must
    # never abort the briefing (same robustness rule as proactive_hits above).
    emerging: dict[str, Any] = {
        "is_emerging": False, "task_signature": "",
        "matched_pattern": None, "episodes_recent": [],
    }
    # --- Atomic idea #2: correction-velocity detector ----------------
    # PUSH: when task_text's signature has a FAILURE-then-SUCCESS history, surface
    # the approach that worked + the failed attempts to avoid, so you skip the
    # failed first try instead of re-deriving the correction. Best-effort: same
    # robustness rule as emerging/proactive_hits — a failure here must not abort.
    _correction_empty: dict[str, Any] = {
        "has_correction": False, "task_signature": "",
        "failures_before_success": 0, "correction_latency_days": None,
        "success": None, "recent_failures": [],
    }
    correction: dict[str, Any] = dict(_correction_empty)
    # --- Atomic idea #4: predictive error-guarding -------------------
    # PUSH: when task_text looks like tasks that historically FAILED (high
    # p_failure with enough confidence), warn BEFORE you act and surface the
    # similar failures. Complements #2: #2 needs a fix to exist; this fires on
    # the no-fix-yet case (a task you keep failing). Same robustness rule.
    _risk_empty: dict[str, Any] = {
        "is_risky": False, "p_failure": 0.0, "confidence": 0.0,
        "n_similar": 0, "similar_failures": [], "reason": "",
    }
    risk_guard: dict[str, Any] = dict(_risk_empty)
    if task_text and memory is not None and hasattr(memory, "all"):
        # capture once; all three signals scan it. Drop cross-LLM call telemetry
        # so emerging/correction/risk see real TASK episodes, not ask_* exhaust.
        _eps = [e for e in memory.all() if not _is_call_telemetry_episode(e)]
        # SEMANTIC relevance for correction: recall the episodes whose meaning
        # matches this task (bounded cosine recall) so a paraphrase still connects
        # to past work with different words. None => detect_correction_pattern
        # falls back to token overlap. Best-effort: a recall failure must not abort.
        _relevant_ids: set[Any] | None = None
        if hasattr(memory, "recall"):
            try:
                _hits = memory.recall(
                    task_text, k=_CORRECTION_RECALL_K, min_similarity=_CORRECTION_MIN_SIM,
                )
                _relevant_ids = {getattr(ep, "id", None) for ep, _score in _hits}
                _relevant_ids.discard(None)
            except Exception:  # noqa: BLE001 — fall back to token matching
                _relevant_ids = None
        try:
            from .emerging_briefing import curate_emerging_briefing
            emerging = curate_emerging_briefing(task_text, _eps)
        except Exception:  # noqa: BLE001 — briefing robustness > this signal
            emerging = {
                "is_emerging": False, "task_signature": "",
                "matched_pattern": None, "episodes_recent": [],
            }
        try:
            from .correction_velocity import detect_correction_pattern
            correction = detect_correction_pattern(
                task_text, _eps, relevant_ids=_relevant_ids,
            )
        except Exception:  # noqa: BLE001 — briefing robustness > this signal
            correction = dict(_correction_empty)
        try:
            from .risk_guard import assess_task_risk
            risk_guard = assess_task_risk(task_text, _eps)
        except Exception:  # noqa: BLE001 — briefing robustness > this signal
            risk_guard = dict(_risk_empty)

    # --- Summary text ------------------------------------------------
    parts: list[str] = []
    parts.append(
        f"HippoAgent memory: {ep_count} episode "
        f"({success_count} success, {failure_count} failure), "
        f"{fact_count} fact, {sk_count} skill."
    )
    if recent_facts:
        f0 = recent_facts[0]["proposition"][:80]
        parts.append(f"Most recent fact: {f0!r}.")
    if pinned_episodes:
        parts.append(f"{len(pinned_episodes)} pinned episode active.")
    if top_skills:
        top = top_skills[0]
        parts.append(
            f"Top skill: {top['name']} (fitness {top['fitness_mean']:.2f}, "
            f"{top['trials']} trials)."
        )
    # Atomic idea #1: make the emerging-task signal VISIBLE in the human summary,
    # not just the structured payload — so the push actually reaches the reader.
    if emerging.get("is_emerging"):
        _n = len(emerging.get("episodes_recent", []))
        parts.append(
            f"[EMERGING] rising streak on '{emerging.get('task_signature', '')}' "
            f"tasks — {_n} recent win(s) surfaced; accelerate, don't re-derive."
        )
    # Atomic idea #2: make the correction signal VISIBLE in the human summary —
    # you failed this kind of task before and fixed it; apply the fix, skip the
    # dead end instead of re-deriving the correction.
    if correction.get("has_correction"):
        parts.append(
            f"[CORRECTION] this task failed "
            f"{correction.get('failures_before_success', 0)}x before it worked "
            f"(latency {correction.get('correction_latency_days')}d) — apply the "
            f"known fix, skip the dead end."
        )
    # Atomic idea #4: make the risk guard VISIBLE — warn before you re-commit a
    # pattern that historically fails.
    if risk_guard.get("is_risky"):
        parts.append(f"[RISK] {risk_guard.get('reason', '')}")
    summary_text = " ".join(parts)

    return {
        "summary_text": summary_text,
        "stats": stats,
        "recent_facts": recent_facts,
        "pinned_episodes": pinned_episodes,
        "recent_episodes": recent_episodes,
        "top_skills": top_skills,
        # Cycle #53: empty list when no task_text or no hits.
        "proactive_hits": proactive_hits,
        # Atomic idea #1: {is_emerging, task_signature, matched_pattern,
        # episodes_recent}. is_emerging False when no task_text / no rising match.
        "emerging": emerging,
        # Atomic idea #2: {has_correction, task_signature, failures_before_success,
        # correction_latency_days, success, recent_failures}. has_correction False
        # when no task_text / no failure-then-success history for the signature.
        "correction": correction,
        # Atomic idea #4: {is_risky, p_failure, confidence, n_similar,
        # similar_failures, reason}. is_risky False when no task_text / the task
        # does not resemble a historically-failing pattern with enough confidence.
        "risk_guard": risk_guard,
    }


__all__ = ["get_briefing"]
