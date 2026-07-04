"""Wake cycle — the executor.

ReAct loop:
1. Retrieve top-k skills + similar past episodes (memory injection).
2. Step loop: prompt LLM → parse Thought/Action/ActionInput → execute tool
   → append observation → repeat until `submit_solution` or max_steps.
3. If failure and self-critique enabled, run Critic → optional retry.
4. Persist Episode (success or failure).
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import embedding
from .compilation import CompiledMacro, execute_macro
from .config import CONFIG
from .context_engine import ContextEngine
from .episode import Episode, Trace
from .llm import ToolCall, get_llm, resolve_model
from .memory import EpisodicMemory
from .observability import emit, get_log
from .prompts import (
    CRITIC_SYSTEM,
    CRITIC_USER_TEMPLATE,
    WAKE_EPISODES_BLOCK_HEADER,
    WAKE_SKILLS_BLOCK_HEADER,
    WAKE_SYSTEM,
    WAKE_USER_TEMPLATE,
)
from .selection import (
    Choice,
    EpisodeChoice,
    consider_episodes,
    consider_skills,
    select_top,
)
from .skill import Skill, SkillLibrary
from .tools import ToolResult, ToolSpec, default_tools
from .wake_strategy import (
    NativeToolsStrategy,
    ParsedTurn,
    ReActStrategy,
    ToolObservation,
    WakeStrategy,
)
from .wake_strategy import (
    parse_react_step as parse_react_step,  # re-export for legacy callers
)
from .working_memory import (
    estimate_size as _wm_estimate_size,
)
from .working_memory import (
    native_tool_is_candidate,
    native_tool_replace,
    prune_messages,
    react_obs_is_candidate,
    react_obs_replace,
)

log = get_log()


# `parse_react_step` lives in `wake_strategy.ReActStrategy` and is
# re-exported via the import above so legacy callers continue working.

# --- Validator protocol ----------------------------------------------------


Validator = Callable[[str], tuple[bool, str]]
"""A validator takes the agent's final answer and returns (success, message)."""


def trivial_validator(answer: str) -> tuple[bool, str]:
    return bool(answer.strip()), "non-empty answer"


# --- Prompt-injection defense (CVE-008) -----------------------------------

# Tools whose output is sourced from externally controllable channels.
# Wrapping their results in `<untrusted_content>` markers tells the model to
# treat the body as data, not instructions.
_EXTERNAL_TOOLS: frozenset[str] = frozenset({
    "web_fetch", "web_search", "vision_describe",
    "webcam_describe", "webcam_snapshot",
})

# Tools that, when invoked AFTER an external-content tool, are considered
# dangerous and trigger the prompt-injection review hook (refused unless the
# user explicitly enabled HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL=1).
# `desktop_screenshot` is intentionally OUT — it's read-only (captures screen
# bytes) and gating it after a web_fetch was over-broad (review MAJOR #1).
_DANGEROUS_TOOLS_AFTER_EXTERNAL: frozenset[str] = frozenset({
    "shell_run",
    "desktop_click", "desktop_type", "desktop_key",
    "desktop_move",
})


def _wrap_untrusted(observation: str, source_tool: str,
                    source_arg: str = "") -> str:
    """Wrap observation in untrusted_content markers when source is external.

    The model is instructed (via system prompt) to treat anything inside
    these markers as data, never as instructions.
    """
    if source_tool not in _EXTERNAL_TOOLS:
        return observation
    src = f'{source_tool}'
    if source_arg:
        src += f':{source_arg[:120]}'
    return (
        f'<untrusted_content source="{src}">\n'
        f'{observation}\n'
        f'</untrusted_content>'
    )


def _is_external_source_in_recent_traces(
    traces: list[Trace], lookback: int = 3,
) -> bool:
    """True if any of the last `lookback` traces was an external-source tool.

    Used by the tool-call review hook: if the model is about to invoke a
    dangerous tool right after fetching external content, that's the classic
    prompt-injection chain — block by default.

    NOTE on lookback: the parameter remains for compatibility with the
    explicit-window check, but the production gate (`_injection_review_blocks_call`)
    no longer relies on lookback alone — see `_episode_is_contaminated`.
    """
    if not traces:
        return False
    for tr in traces[-lookback:]:
        if (tr.action or "") in _EXTERNAL_TOOLS:
            return True
    return False


def _episode_is_contaminated(traces: list[Trace]) -> bool:
    """True iff any past trace fetched external content.

    Once an episode has touched external content, the episode stays
    contaminated for the duration of the wake loop. This closes the
    'lookback wash' bypass: an attacker page can no longer escape the
    dangerous-tool gate by inserting N benign run_python steps after
    web_fetch — the contamination latches until the user starts a new task.
    """
    if not traces:
        return False
    for tr in traces:
        if (tr.action or "") in _EXTERNAL_TOOLS:
            return True
    return False


def _injection_review_blocks_call(action: str, recent_traces: list[Trace]) -> bool:
    """Return True if the impending tool call should be refused."""
    if os.environ.get(
        "HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "",
    ).strip().lower() in ("1", "true", "yes", "on"):
        return False
    if action not in _DANGEROUS_TOOLS_AFTER_EXTERNAL:
        return False
    # Latching contamination: once external content was fetched, stay strict.
    return _episode_is_contaminated(recent_traces)


def _macro_blocked_by_injection_guard(macro: Any, episode_traces: list[Trace]) -> bool:
    """CVE-008 (rescan2 2026-06-02): the procedural macro fast-path bypassed
    the prompt-injection gate that the LLM loop applies per tool-call. Return
    True when the episode is already contaminated by external content AND the
    macro would run a tool in ``_DANGEROUS_TOOLS_AFTER_EXTERNAL`` — so that
    ``_try_compiled_macro`` defers to the gated LLM loop instead of executing
    the macro. Honors the same HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL escape
    hatch as ``_injection_review_blocks_call``.
    """
    if os.environ.get(
        "HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "",
    ).strip().lower() in ("1", "true", "yes", "on"):
        return False

    def _tool_of(step: Any) -> str | None:
        tool = getattr(step, "tool", None)
        if tool is None and isinstance(step, dict):
            tool = step.get("tool")
        return tool

    steps = list(getattr(macro, "steps", []) or [])
    # Case 1: the EPISODE is already contaminated by external content and the
    # macro runs any dangerous tool -> defer to the gated LLM loop.
    if _episode_is_contaminated(episode_traces):
        for step in steps:
            if _tool_of(step) in _DANGEROUS_TOOLS_AFTER_EXTERNAL:
                return True
    # Case 2 (3-round audit, R3 #18): the macro is SELF-CONTAMINATING — an
    # external-content tool precedes a dangerous tool within the macro's OWN
    # steps. A fresh episode whose macro does web_fetch -> shell_run would
    # otherwise run the injection chain ungated on the deterministic fast-path,
    # since _episode_is_contaminated only inspects the episode's prior traces.
    external_seen = False
    for step in steps:
        tool = _tool_of(step)
        if tool in _EXTERNAL_TOOLS:
            external_seen = True
        elif external_seen and tool in _DANGEROUS_TOOLS_AFTER_EXTERNAL:
            return True
    return False


def _extract_source_arg(tc: ToolCall) -> str:
    """Pick the first 'sourcey' field from a tool call's input.

    Used to label external-content observations: a `web_fetch` to
    `https://x.com/path` produces `<untrusted_content source="web_fetch:https://x.com/path">`.
    The label helps the model (and human reviewers) trace where a
    given observation came from. Truncated to 120 chars to keep
    log lines tractable.
    """
    if tc.input and isinstance(tc.input, dict):
        for key in ("url", "image", "query", "path"):
            if key in tc.input:
                return str(tc.input.get(key, ""))[:120]
    return ""


def _submit_cutoff_index(tool_calls: list) -> int:
    """rescan2 2026-06-02 (wake.py:1391-1428): index AFTER which parallel tool
    calls in a single turn must NOT execute side-effects — i.e. right after the
    first ``submit_solution``. Once the model has submitted its answer, any
    further parallel call in the same turn is a post-submit side-effect and is
    skipped. Returns ``len(tool_calls)`` when no submit_solution is present
    (every call executes normally).
    """
    for i, tc in enumerate(tool_calls):
        if getattr(tc, "name", None) == "submit_solution":
            return i + 1
    return len(tool_calls)


# --- Wake loop -------------------------------------------------------------


@dataclass
class WakeConfig:
    max_steps: int = CONFIG.wake_max_steps
    skills_top_k: int = CONFIG.wake_skills_top_k
    # Bayesian re-rank pool. See selection.py / FORGIA.md.
    skills_pool_size: int = CONFIG.wake_skills_pool_size
    episodes_recall_k: int = CONFIG.wake_episodes_recall_k
    self_critique: bool = CONFIG.wake_self_critique
    critique_retries: int = CONFIG.wake_critique_retries
    use_skills: bool = True  # toggle for baseline A/B
    use_past_episodes: bool = True
    # When False, fall back to legacy top-k cosine selection (used by
    # the bench harness to measure the Bayesian path's improvement).
    bayesian_skill_selection: bool = True


@dataclass
class WakeResult:
    episode: Episode
    success: bool
    message: str
    skills_retrieved: list[Skill] = field(default_factory=list)
    # FORGIA pezzo #57: did the procedural fast-path fire? Lets bench
    # / dashboard distinguish "wake loop succeeded" from "macro fired
    # zero-LLM". Defaults to False; set by _try_compiled_macro on hit.
    used_macro: bool = False


class WakeAgent:
    def __init__(
        self,
        memory: EpisodicMemory | None = None,
        skills: SkillLibrary | None = None,
        tools: dict[str, ToolSpec] | None = None,
        llm: Any | None = None,
        config: WakeConfig | None = None,
        rng: np.random.Generator | None = None,
        semantic: Any | None = None,
    ) -> None:
        self.memory = memory or EpisodicMemory()
        self.skills = skills or SkillLibrary()
        self.tools = tools or default_tools()
        self.llm = llm or get_llm()
        self.cfg = config or WakeConfig()
        # FORGIA pezzo #181 — schema-driven skill priming. Optional
        # semantic memory used by `prime_skills_via_topics`. None →
        # priming is a no-op (returns base scores unchanged).
        self.semantic = semantic
        # Bayesian skill selection draws from this RNG. Pass a seeded
        # generator (np.random.default_rng(seed)) to make the selection
        # reproducible for tests / replay; default_rng() seeds from the
        # OS for production runs.
        self._rng = rng or np.random.default_rng()
        # Cached on-purpose: the last consideration set, exposed for
        # observability sinks (dashboard / lineage). None until run() fires.
        self.last_consideration: list[Choice] = []
        # FORGIA pezzo #17 — cross-session ContextEngine. Maintains the
        # agent's drifting cognitive context across run() calls so
        # episodes encoded in similar recent contexts get a recall
        # boost (Howard & Kahana 2002 list-context dynamics). The
        # engine starts at zero — the first observed task seeds it.
        self._context_engine = ContextEngine(
            dim=CONFIG.embedding_dim,
            rho=CONFIG.tcm_rho,
        )

    # --- Episode admin API (FORGIA pezzo #113/#132) ----------------------
    def skill_usage_histogram(self) -> dict[str, int]:
        """FORGIA pezzo #142: skill_id → number of episodes that used it.

        Thin alias for `memory.skill_usage_histogram()`. Surfaced on
        the agent for dashboard / debug ergonomics.
        """
        return self.memory.skill_usage_histogram()

    def outcome_breakdown(self) -> dict[str, int]:
        """FORGIA pezzo #146: outcome → episode count.

        Thin alias for `memory.outcome_breakdown()`.
        """
        return self.memory.outcome_breakdown()

    def skill_co_occurrence(
        self, skill_id: str, top_k: int | None = None,
    ) -> dict[str, int]:
        """FORGIA pezzo #159: which skills appear together with `skill_id`.

        Thin alias for `memory.skill_co_occurrence()`. Useful for
        dashboard / debug ergonomics on the agent surface.
        """
        return self.memory.skill_co_occurrence(skill_id, top_k=top_k)

    def skill_bundle_candidates(
        self,
        *,
        min_count: int = 3,
        min_overlap: float = 0.6,
    ) -> list[tuple[str, str, int]]:
        """FORGIA pezzo #161: surface skill_bundle_candidates on the agent.

        Thin alias for `memory.skill_bundle_candidates()`. Useful for
        sleep-engine bundle abstraction triggered from the agent
        surface (e.g. via MCP introspection).
        """
        return self.memory.skill_bundle_candidates(
            min_count=min_count, min_overlap=min_overlap,
        )

    def compound_skills(self) -> list:
        """FORGIA pezzo #167: skills synthesized from a bundle of 2+ parents.

        Returns the list of skills with ``len(parent_skills) >= 2``.
        Skills with a single parent (refinements via REM) are excluded.
        """
        return [s for s in self.skills.all() if len(s.parent_skills) >= 2]

    def prime_skills_via_topics(
        self,
        *,
        task: str,
        base_scores: dict[str, float],
        skills: list,
        boost_strength: float = 0.5,
        k: int = 5,
    ) -> dict[str, float]:
        """FORGIA pezzo #181: schema-driven skill priming.

        Reweights `base_scores` using the topic distribution from
        `SemanticMemory.topics_for_query(task, k)`. Each skill's
        score is multiplied by ``1 + boost_strength * topic_weight``
        when its trigger or name contains the topic substring (case-
        insensitive). Skills not matching any primed topic keep
        their base score.

        Returns a NEW dict; does not mutate `base_scores`.
        Inspired by Preston & Eichenbaum 2013: prefrontal cortex
        pre-activates schemas relevant to the upcoming task.
        """
        if self.semantic is None:
            return dict(base_scores)
        topics = self.semantic.topics_for_query(task, k=k)
        if not topics:
            return dict(base_scores)
        sk_by_id = {s.id: s for s in skills}
        out: dict[str, float] = {}
        for sk_id, base in base_scores.items():
            sk = sk_by_id.get(sk_id)
            if sk is None:
                out[sk_id] = base
                continue
            haystack = f"{sk.trigger} {sk.name}".lower()
            best_match = 0.0
            for topic, weight in topics.items():
                if topic and topic.lower() in haystack:
                    if weight > best_match:
                        best_match = weight
            multiplier = 1.0 + boost_strength * best_match
            out[sk_id] = base * multiplier
        return out

    def _apply_lateral_inhibition(self, skills: list) -> list:
        """FORGIA pezzo #171: greedy filter on antagonist links.

        Walk the ranked list left-to-right; keep a skill iff
            (a) it does not list any already-kept skill as antagonist
            (b) no already-kept skill lists it as antagonist

        Inspired by Földiák (1990) lateral-inhibition learning. The
        antagonists are populated by sleep stage #170 from
        `EpisodicMemory.negative_bundle_candidates`. Idempotent on
        skills with empty antagonist lists.
        """
        if not skills:
            return []
        out: list = []
        kept_ids: set[str] = set()
        for s in skills:
            # Skill blocked if any kept skill is in its antagonist list.
            if any(other_id in s.antagonists for other_id in kept_ids):
                continue
            # Skill blocked if any kept skill lists it as antagonist.
            blocked = False
            for other_id in kept_ids:
                other = self.skills.get(other_id)
                if other is not None and s.id in other.antagonists:
                    blocked = True
                    break
            if blocked:
                continue
            out.append(s)
            kept_ids.add(s.id)
        return out

    def steps_summary(self) -> dict[str, float]:
        """FORGIA pezzo #147: trace-step distribution stats.

        Thin alias for `memory.steps_summary()`.
        """
        return self.memory.steps_summary()

    def token_usage_summary(self) -> dict[str, float]:
        """FORGIA pezzo #148: aggregate token usage across all episodes.

        Thin alias for `memory.token_usage_summary()`.
        """
        return self.memory.token_usage_summary()

    def find_by_task(self, task_text: str, *, limit: int = 10
                      ) -> list[Episode]:
        """FORGIA pezzo #150: find every episode for a given task_text.

        Thin alias for `memory.find_by_task_text(task_text, limit)`.
        """
        return self.memory.find_by_task_text(task_text, limit=limit)

    def episodes_in_window(self, start_ts: float, end_ts: float, *,
                            limit: int = 1000) -> list[Episode]:
        """FORGIA pezzo #150: episodes in [start_ts, end_ts).

        Thin alias for `memory.episodes_in_window(...)`.
        """
        return self.memory.episodes_in_window(start_ts, end_ts, limit=limit)

    def recent_episodes(self, k: int = 5) -> list[Episode]:
        """FORGIA pezzo #132: return the K most recent episodes.

        Thin alias for `memory.all(limit=k)` (which orders by
        `created_at DESC`). Surfaced on the agent for symmetry with
        the other admin / dashboard APIs.
        """
        return list(self.memory.all(limit=k))

    def delete_episode(self, episode_id: str) -> bool:
        """Delete one episode by id. Thin delegate to memory.delete().

        Surfaced on the agent for symmetry with `consolidate()` /
        `run_task()` so callers don't have to reach into
        `self.memory.delete(...)` directly.
        """
        return self.memory.delete(episode_id)

    # --- Lightweight metrics API (FORGIA pezzo #91/#93/#102) ------------
    def metrics(self) -> dict[str, int | float]:
        """Snapshot of WakeAgent-level stats.

        Cheap O(1) counts from memory + skills + last consideration set.
        Useful for dashboards / bench harnesses that want a single
        snapshot dict without poking every internal table.
        """
        # FORGIA #102: count skills with a compiled macro
        n_macros = sum(
            1 for s in self.skills.all() if s.compiled_macro
        )
        n_total = int(self.memory.count())
        n_success = int(self.memory.count(outcome_filter="success"))
        n_failure = int(self.memory.count(outcome_filter="failure"))
        # FORGIA pezzo #130: lifetime success rate.
        success_rate = (n_success / n_total) if n_total > 0 else 0.0
        # FORGIA pezzo #138: token usage summary.
        tokens = self.memory.token_usage_summary()
        return {
            "n_episodes": n_total,
            "n_episodes_success": n_success,
            "n_episodes_failure": n_failure,
            "lifetime_success_rate": float(success_rate),
            "n_skills": int(self.skills.count()),
            "n_skills_promoted": int(self.skills.count(status="promoted")),
            "n_skills_candidate": int(self.skills.count(status="candidate")),
            "n_skills_retired": int(self.skills.count(status="retired")),
            "n_skills_with_macro": int(n_macros),
            "n_last_consideration": len(self.last_consideration),
            "tokens_total": float(tokens["total"]),
            "tokens_mean": float(tokens["mean"]),
            "tokens_max": float(tokens["max"]),
        }

    # --- Context lifecycle (FORGIA pezzo #22) -----------------------------

    def predict_next_skill(
        self, used_skills: list[str], *, top_k: int = 3,
    ) -> list[str]:
        """Predict the most likely next skill given a usage history.

        FORGIA pezzo #24 — cabling the Successor Representation
        primitive (pezzo #20) into the wake API. Builds an empirical
        transition matrix from past episodes' `skills_used` and returns
        the top-k successors of the LAST entry in `used_skills`.

        Returns:
          - Empty list if `used_skills` is empty or its last entry
            isn't in any past episode.
          - Empty list if memory has no episodes.
          - Otherwise top-k skill IDs ordered by transition probability,
            self excluded.

        Cost: builds the P matrix on every call (no cache). For a
        100-skill / 1k-episode corpus this is ~2ms per call. If the
        wake calls this every step, consider caching at the
        instance level (out of scope for this pezzo).
        """
        if not used_skills:
            return []
        episodes = self.memory.all()
        skill_seqs = [ep.skills_used for ep in episodes if ep.skills_used]
        if not skill_seqs:
            return []
        from .successor_repr import build_transition_matrix, predict_next
        ids, P = build_transition_matrix(skill_seqs)
        return predict_next(used_skills[-1], ids, P, top_k=top_k)

    def reset_context(self) -> None:
        """Snap the cross-session ContextEngine state back to zero.

        Use between independent batches / parallel tasks to avoid
        the agent's drift from a previous unrelated task biasing
        retrieval. Pure no-op if `_context_engine` was never set
        (e.g. WakeAgent built via object.__new__ in tests)."""
        engine = getattr(self, "_context_engine", None)
        if engine is not None:
            engine.reset()

    def checkpoint_context(self) -> np.ndarray:
        """Return a defensive COPY of the current context engine state.

        The caller can mutate the returned array without affecting
        the engine. Useful for snapshots ("save before risky run")
        or for debugging ("what was the state when I had this issue").
        Returns a zero-vector if the engine isn't wired (in test
        bypasses) or if its state is genuinely zero."""
        engine = getattr(self, "_context_engine", None)
        if engine is None:
            return np.zeros(CONFIG.embedding_dim, dtype=np.float32)
        return engine.state  # ContextEngine.state already returns a copy

    def restore_context(self, state: np.ndarray) -> None:
        """Load a previously-saved context state into the engine.

        Defensive: validates dimensionality. Raises ValueError on
        mismatch rather than silently corrupting the engine.
        """
        arr = np.asarray(state, dtype=np.float32)
        if arr.shape != (CONFIG.embedding_dim,):
            raise ValueError(
                f"context state dim {arr.shape} doesn't match "
                f"CONFIG.embedding_dim ({CONFIG.embedding_dim},)"
            )
        engine = getattr(self, "_context_engine", None)
        if engine is None:
            # Lazy-instantiate so a test that bypassed __init__ can
            # still call restore_context.
            engine = ContextEngine(
                dim=CONFIG.embedding_dim, rho=CONFIG.tcm_rho,
            )
            self._context_engine = engine
        engine._state = arr.copy()  # noqa: SLF001

    # --- Memory injection --------------------------------------------------

    def _retrieve_skills(self, task: str) -> list[Skill]:
        """Bayesian-weighted retrieval: cosine-pool then Thompson re-rank.

        First we draw a wider candidate pool by cosine similarity (cheap,
        already vectorised in SkillLibrary.retrieve). Then `consider_skills`
        re-ranks combining relevance and the Beta-posterior fitness via
        Thompson sampling. The result obeys the intuition the legacy
        path could never honour: a skill must be both relevant AND
        proven to win — not just one.

        The legacy top-k-cosine path is reachable via
        `cfg.bayesian_skill_selection = False`; the bench harness uses
        that toggle to A/B the two policies on identical data.
        """
        if not self.cfg.use_skills:
            return []

        if not self.cfg.bayesian_skill_selection:
            return self._retrieve_skills_legacy(task)

        # Pull a wider pool than k — selection collapses to a no-op when
        # pool == k, since the rank order can't change.
        pool_size = max(self.cfg.skills_pool_size, self.cfg.skills_top_k * 4)
        promoted = self.skills.retrieve(task, k=pool_size, status="promoted")
        if len(promoted) >= pool_size:
            pool = promoted
        else:
            remaining = pool_size - len(promoted)
            candidates = self.skills.retrieve(task, k=remaining, status="candidate")
            pool = promoted + candidates

        if not pool:
            self.last_consideration = []
            return []

        task_emb = embedding.encode(task)
        choices = consider_skills(
            pool, task_emb,
            encoder=embedding.encode,
            rng=self._rng,
        )
        self.last_consideration = choices

        if choices:
            top = choices[0]
            emit(
                "skill_selection",
                top_id=top.skill.id,
                top_relevance=round(top.relevance, 3),
                top_theta=round(top.theta, 3),
                top_score=round(top.score, 3),
                pool_size=len(pool),
                k=self.cfg.skills_top_k,
            )

        selected = select_top(choices, k=self.cfg.skills_top_k)
        # FORGIA pezzo #171: retrieval-time lateral inhibition. Optional
        # post-filter that drops skills whose antagonists are already in
        # the selected set. Off by default; flips on via
        # `CONFIG.retrieval_inhibition_enabled`. NB: the older
        # `lateral_inhibition_enabled` flag controls the embedding-space
        # anti-Hebbian update on success — different mechanism.
        from .config import CONFIG as _CFG
        if getattr(_CFG, "retrieval_inhibition_enabled", False):
            selected = self._apply_lateral_inhibition(selected)
        return selected

    def _retrieve_skills_legacy(self, task: str) -> list[Skill]:
        """The pre-Bayesian path: top-k cosine, ignores fitness.

        Kept reachable so the bench harness can measure the Bayesian
        path's improvement on identical data. Production should leave
        `bayesian_skill_selection = True`.
        """
        promoted = self.skills.retrieve(task, k=self.cfg.skills_top_k, status="promoted")
        if len(promoted) >= self.cfg.skills_top_k:
            return promoted
        remaining = self.cfg.skills_top_k - len(promoted)
        candidates = self.skills.retrieve(task, k=remaining, status="candidate")
        return promoted + candidates

    def _retrieve_episodes(self, task: str) -> list[tuple[Any, float]]:
        if not self.cfg.use_past_episodes:
            return []
        # Floor: drop episodes whose cosine to the task is below this.
        # Without it, when the task is novel, recall() still returns its
        # top-k of irrelevant past episodes, which the prompt then
        # surfaces as "few-shot examples" — biasing the model toward
        # solutions that don't apply.
        min_sim = float(getattr(CONFIG, "wake_episodes_min_similarity", 0.0))
        # FORGIA pezzo #16 — opt-in DG-encoded retrieval for the wake's
        # few-shot block. When `wake_recall_use_dg=True` near-duplicate
        # episodes get diversified by the dentate-gyrus pattern separator.
        # Outcome-filtered branches use plain cosine (DG index doesn't
        # carry per-outcome filtering in the current implementation).
        use_dg = bool(getattr(CONFIG, "wake_recall_use_dg", False))
        # FORGIA pezzo #17 — context-aware retrieval. When the cross-
        # session ContextEngine is enabled, pass its current state as
        # the recall cue. `tcm_recall_context_weight` controls how much
        # the context cosine adds to the score (defaults small so
        # cosine relevance still dominates).
        # Defensive: tests sometimes instantiate WakeAgent via
        # `object.__new__` (skipping __init__). The engine is optional —
        # if it's missing we cleanly fall back to no-context retrieval.
        ctx_emb: np.ndarray | None = None
        ctx_w = 0.0
        engine = getattr(self, "_context_engine", None)
        if (
            engine is not None
            and CONFIG.tcm_cross_session_enabled
            and CONFIG.tcm_recall_context_weight > 0.0
        ):
            ctx_state = engine.state
            if float(np.linalg.norm(ctx_state)) > 0.0:
                ctx_emb = ctx_state
                ctx_w = float(CONFIG.tcm_recall_context_weight)
        # FORGIA pezzo #18 — cabling salience + recency into wake retrieve.
        sal_w = float(getattr(CONFIG, "wake_salience_weight", 0.0))
        rec_w = float(getattr(CONFIG, "wake_recency_weight", 0.0))
        rec_tau = float(getattr(CONFIG, "wake_recency_tau_s", 7 * 86400.0))
        successes = self.memory.recall(
            task, k=self.cfg.episodes_recall_k, outcome_filter="success",
            min_similarity=min_sim,
            use_dg=use_dg,
            context_emb=ctx_emb,
            context_weight=ctx_w,
            salience_weight=sal_w,
            recency_weight=rec_w,
            recency_tau_s=rec_tau,
        )
        # Pull a small budget of similar FAILURES too — they feed the
        # forward_replay avoid-path block. Keep the prompt-visible episodes
        # block (success-only, in _build_user_prompt) unaffected by tagging
        # failures separately and consumed only by _avoid_path_block.
        if not CONFIG.forward_replay_include_failures:
            return successes
        failures = self.memory.recall(
            task, k=1, outcome_filter="failure",
            min_similarity=min_sim,
            use_dg=use_dg,
            context_emb=ctx_emb,
            context_weight=ctx_w,
            salience_weight=sal_w,
            recency_weight=rec_w,
            recency_tau_s=rec_tau,
        )
        return successes + failures

    def _build_episode_context(
        self, task_text: str, traces: list[Trace],
    ) -> np.ndarray:
        """Run the TCM context drift over the episode's task + observations.

        Math (Howard & Kahana 2002):

            c_t = ρ · c_{t-1} + (1 - ρ) · obs_emb_t

        We seed the engine with the task_text embedding (the first
        thing the agent "sees" when planning), then observe each
        tool-result observation in order. The final state is what
        gets persisted as the encoding context — the average-recent
        signature of what was happening AROUND this episode.

        Empty traces (no tool calls) → context degenerates to the
        task embedding scaled by (1-ρ); still a valid context,
        meaningful for direct-answer tasks.
        """
        engine = ContextEngine(
            dim=CONFIG.embedding_dim,
            rho=CONFIG.tcm_rho,
        )
        # Seed with the task statement. This anchors the context to the
        # initial intent BEFORE any tool result drifts it.
        engine.observe(embedding.encode(task_text))
        # Then observe every observation in chronological order. We
        # use the trace.observation field (post-truncation) — same
        # text the model saw in its working memory.
        for tr in traces:
            obs = tr.observation
            if not obs:
                continue
            engine.observe(embedding.encode(obs))
        return engine.state

    def _build_user_prompt(self, task: str, skills: list[Skill], episodes: list) -> str:
        skills_block = ""
        if skills:
            skills_block = WAKE_SKILLS_BLOCK_HEADER + "\n".join(s.render() for s in skills) + "\n\n"
        eps_block = ""
        # Only successful episodes go in the visible "few-shot" block; failures
        # are reserved for the forward_replay avoid-path so they don't
        # accidentally serve as positive examples.
        success_episodes = [
            (ep, s) for ep, s in episodes
            if getattr(ep, "outcome", None) == "success"
        ]
        if success_episodes:
            eps_block = WAKE_EPISODES_BLOCK_HEADER
            for ep, _sim in success_episodes:
                eps_block += f"- Task: {ep.task_text}\n  Final answer: {ep.final_answer[:200]}\n"
            eps_block += "\n"
        forward_block = self._forward_replay_block(task, skills, episodes)
        prompt = WAKE_USER_TEMPLATE.format(
            skills_block=skills_block,
            episodes_block=eps_block,
            task=task,
            max_steps=self.cfg.max_steps,
        )
        if forward_block:
            # Insert before the final TASK line for maximum salience
            return forward_block + prompt
        return prompt

    # --- Forward replay (predict before act) -------------------------------

    def _forward_replay_block(
        self, task: str, skills: list[Skill], episodes: list
    ) -> str:
        """Build a deterministic 'predicted path' block from past memory.

        For each top skill that has matching successful episodes, list the
        action sequence that worked before. This anchors the LLM's reasoning
        and lets us detect divergence (a learning signal for counterfactual REM).
        Zero LLM calls — pure retrieval over existing traces.
        """
        if not CONFIG.forward_replay_enabled or not skills:
            return ""
        top = skills[0]
        # Bayesian gate (FORGIA pezzo #4) — same rationale as the macro
        # gate: don't anchor the LLM with a "predicted path" derived
        # from a skill we aren't yet confident in. Lower threshold
        # than the macro gate (0.30 vs 0.65) because forward-replay is
        # informational, not a deterministic fast-path.
        if getattr(CONFIG, "forward_replay_use_lower_bound", True):
            if top.fitness_lower_bound < CONFIG.forward_replay_min_lower_bound:
                return ""
        elif top.fitness_mean < CONFIG.forward_replay_min_fitness:
            return ""

        # Find the best past successful episode that used this skill
        successful_for_skill: list[Episode] = []
        for ep, _sim in episodes:
            if ep.outcome == "success" and top.id in ep.skills_used:
                successful_for_skill.append(ep)
        if len(successful_for_skill) < CONFIG.forward_replay_min_episodes:
            # Fallback: any successful similar episode
            successful_for_skill = [ep for ep, _ in episodes if ep.outcome == "success"]
        if not successful_for_skill:
            return ""

        # Build the predicted action sequence from the most recent matching episode
        ref = successful_for_skill[0]
        action_seq = [t.action for t in ref.traces if t.action and t.action != "(none)"]
        if not action_seq:
            return ""

        # Annotate steps that were historically fragile: we run trace
        # alignment between this success ref and every past failure for
        # the same skill, then count which step (1-indexed) of the
        # success was the divergence point. A step that diverged in ≥2
        # past failures gets a "⚠" mark in the rendered path.
        fragile_step_counts = self._historical_divergence_counts(
            top, ref, episodes, task=task,
        )
        rendered_steps: list[str] = []
        for i, action in enumerate(action_seq, start=1):
            count = fragile_step_counts.get(i, 0)
            if count >= 2:
                rendered_steps.append(f"{action}⚠×{count}")
            else:
                rendered_steps.append(action)

        confidence = min(0.99, top.fitness_mean)
        block = (
            "## PREDICTED PATH (forward replay)\n"
            f"Based on {len(successful_for_skill)} similar successful past attempt(s), "
            f"the most likely action sequence is:\n"
            + "  " + " → ".join(rendered_steps) + "\n"
        )
        # Render the legend only when at least one mark actually appeared
        # in the path. A single divergence (N=1) doesn't trigger a mark
        # (it could be one-off bad luck), so its mention in the legend
        # would be misleading.
        if any(c >= 2 for c in fragile_step_counts.values()):
            block += (
                "  Steps marked ⚠×N have been historical divergence points "
                "(N past failures took a different path here). Pause and "
                "verify the situation before committing to that step.\n"
            )
        block += (
            f"Skill anchor: {top.name!r} (fitness {confidence:.2f}). "
            "Deviate ONLY if the task structure clearly differs.\n"
        )
        avoid_block = self._avoid_path_block(top, episodes, task=task)
        if avoid_block:
            block += avoid_block
        block += "\n"
        emit("forward_replay", task=task[:80], skill_id=top.id,
             n_actions=len(action_seq), confidence=confidence,
             with_avoid=bool(avoid_block))
        return block

    def _historical_divergence_counts(
        self, top: Skill, success_ref: Episode, episodes: list,
        *, task: str = "",
    ) -> dict[int, int]:
        """For each step of the success reference, count how many past
        failures diverged at that step.

        Used to annotate the forward-replay block with "⚠" marks.

        Cost: one trace alignment per failure for this skill. Bounded by
        `forward_replay_max_failure_actions` * trajectory_length, which
        in practice is < 50 cosine ops. We bail early if trace alignment
        is disabled or no failures exist.

        FORGIA pezzo #5: when `task` is supplied, the failure pool is
        ranked by `consider_episodes` (relevance + recency) before the
        cap is applied. Old, irrelevant failures get pushed past the
        cap, recent on-topic ones get the alignment budget.

        Returns: {success_step (1-indexed): count of past failures that
        diverged at that step}. Steps not present have zero failures.
        """
        if not getattr(CONFIG, "trace_alignment_enabled", True):
            return {}
        # Reuse the same failure pool that the avoid-path block looks at.
        failures = [
            ep for ep, _ in episodes
            if getattr(ep, "outcome", None) == "failure"
            and top.id in getattr(ep, "skills_used", [])
        ]
        if not failures:
            return {}
        # Cap to keep cost bounded — but the priority primitive decides
        # WHICH 5 we keep, not the iteration order. With `task` supplied,
        # the most informative failures get the budget.
        if task:
            ranked = self._prioritise_episodes(failures, task)
            failures = [c.episode for c in ranked[:5]]
        else:
            failures = failures[:5]
        from .trace_alignment import align_traces, find_divergence_point
        counts: dict[int, int] = {}
        for fail in failures:
            try:
                a = align_traces(fail, success_ref)
                div = find_divergence_point(a)
            except Exception:  # noqa: BLE001
                continue
            if div is None or div.success_step is None:
                continue
            counts[div.success_step] = counts.get(div.success_step, 0) + 1
        return counts

    def _avoid_path_block(
        self, top: Skill, episodes: list, *, task: str = "",
    ) -> str:
        """Surface the action prefix of recent FAILED similar episodes.

        Disclosing 'what we tried and burned on' before the action loop is
        cheap — it costs a couple of tokens — and prevents the model from
        re-walking the same dead end. When a successful twin episode is
        also available we go further and run an observation-anchored
        alignment to pinpoint the exact divergence step (no LLM call;
        see engram.trace_alignment) — that block replaces the bare
        prefix because it carries strictly more signal.

        FORGIA pezzo #5: when `task` is non-empty we pick the most
        informative failure via `consider_episodes` (cosine relevance
        to current task + recency decay). Empty `task` preserves the
        legacy `failed[0]` behaviour for callers that don't have a
        query in scope (some tests).
        """
        if not CONFIG.forward_replay_include_failures:
            return ""
        failed_for_skill = [
            ep for ep, _ in episodes
            if getattr(ep, "outcome", None) == "failure"
            and top.id in getattr(ep, "skills_used", [])
        ]
        if not failed_for_skill:
            return ""

        if task:
            ranked = self._prioritise_episodes(failed_for_skill, task)
            ref_fail = ranked[0].episode if ranked else failed_for_skill[0]
            if ranked:
                emit(
                    "avoid_path_failure_picked",
                    skill_id=top.id, fail_id=ref_fail.id,
                    relevance=round(ranked[0].relevance, 3),
                    recency=round(ranked[0].recency, 3),
                    n_candidates=len(failed_for_skill),
                )
        else:
            ref_fail = failed_for_skill[0]

        # Try the divergence path first. It only fires when we also have
        # a successful twin — a positive example to align against. When
        # either side is silent we fall back to the bare prefix.
        diverg_block = self._divergence_block(
            top, ref_fail, episodes, task=task,
        )
        if diverg_block:
            return diverg_block

        actions = [t.action for t in ref_fail.traces
                   if t.action and t.action != "(none)"]
        actions = actions[: CONFIG.forward_replay_max_failure_actions]
        if not actions:
            return ""
        critique = (getattr(ref_fail, "critique", "") or "").strip()
        critique_line = f" Lesson: {critique[:120]}" if critique else ""
        return (
            "Avoid path (recent FAILURE on a similar task):\n"
            "  " + " → ".join(actions) + ".\n"
            f"  Diverge from this prefix as soon as it diverged then.{critique_line}\n"
        )

    def _divergence_block(
        self, top: Skill, failure: Episode, episodes: list,
        *, task: str = "",
    ) -> str:
        """Run trace alignment between `failure` and a success-twin.

        FORGIA pezzo #5: pick the success-twin via cosine on the failure's
        task text (or the current `task` when supplied), with recency as
        tiebreaker — `consider_episodes` does both. The legacy fallback
        was lowercase-token-overlap, which conflates "same words" with
        "same intent" and ignored when the twin happened.

        If no twin exists or no actionable divergence is found we return
        "" and let the caller use the bare avoid-path fallback.

        Cost: O(N*M) over numpy with cached embeddings — milliseconds, no
        LLM call. The benefit over the bare prefix block is that the
        agent gets to see exactly which step inverted the outcome instead
        of "the first N actions burned on this kind of task".
        """
        if not getattr(CONFIG, "trace_alignment_enabled", True):
            return ""
        obs_threshold = float(getattr(
            CONFIG, "trace_alignment_obs_threshold", 0.55,
        ))
        successful = [
            ep for ep, _ in episodes
            if getattr(ep, "outcome", None) == "success"
            and top.id in getattr(ep, "skills_used", [])
        ]
        if not successful:
            return ""
        # Pick the most informative twin via the priority primitive.
        # Query: prefer the current task when known (the wake loop has it)
        # else fall back to the failure's own task text — matches the
        # intent of finding "what kind of task this failure was about".
        query_text = task or failure.task_text or ""
        if query_text:
            ranked = self._prioritise_episodes(successful, query_text)
            twin = ranked[0].episode if ranked else successful[0]
        else:
            twin = successful[0]

        # Lazy import to keep wake.py's startup graph small and avoid a
        # cycle through the embedding cache when wake.py is unit-tested.
        from .trace_alignment import (
            align_traces,
            find_divergence_point,
            format_divergence,
        )
        try:
            alignment = align_traces(failure, twin)
            div = find_divergence_point(alignment, obs_threshold=obs_threshold)
        except Exception:  # noqa: BLE001
            log.exception("trace_alignment_failed",
                          fail_id=failure.id, twin_id=twin.id)
            return ""
        if div is None:
            return ""
        emit(
            "divergence_detected",
            skill_id=top.id, fail_id=failure.id, twin_id=twin.id,
            fail_step=div.fail_step, success_step=div.success_step,
            obs_similarity=round(div.obs_similarity, 3),
        )
        return format_divergence(div, alignment)

    # --- Procedural compilation fast-path ---------------------------------

    def _try_compiled_macro(
        self,
        episode: Episode,
        task_text: str,
        skills: list[Skill],
        validator: Validator,
    ) -> tuple[bool, str] | None:
        """Run the top skill's compiled macro if applicable.

        Returns (success, msg) on macro execution (success or controlled
        failure), or None if no macro was applicable — signalling the caller
        to fall through to the regular LLM loop.
        """
        if not skills:
            return None
        top = skills[0]
        if not top.compiled_macro:
            return None
        # Bayesian gate (FORGIA pezzo #4) — gate on the 5%-quantile of
        # the Beta posterior, not the mean. This rejects skills whose
        # mean LOOKS good but whose evidence is too thin (e.g. 3/3
        # successes ⇒ mean 0.80 but lower_bound ~0.47). The legacy
        # mean-based gate is reachable via `compile_apply_use_lower_bound=False`
        # for backward compat / A/B comparison.
        if getattr(CONFIG, "compile_apply_use_lower_bound", True):
            if top.fitness_lower_bound < CONFIG.compile_apply_min_lower_bound:
                return None
        elif top.fitness_mean < CONFIG.compile_apply_min_fitness:
            return None
        try:
            macro = CompiledMacro.from_dict(top.compiled_macro)
        except Exception as exc:  # noqa: BLE001
            log.warning("macro_deserialize_failed", skill_id=top.id, error=str(exc))
            return None
        sim = self._skill_similarity(task_text, top)
        threshold = self._adaptive_macro_threshold(macro.confidence)
        if sim < threshold:
            return None

        # CVE-008 (rescan2 2026-06-02): the LLM loop gates dangerous tools
        # after external content; this fast-path must not bypass it. If the
        # episode is contaminated and the macro runs a dangerous tool, defer
        # to the gated LLM loop (return None → fall through).
        if _macro_blocked_by_injection_guard(macro, episode.traces):
            emit("macro_skipped_injection_guard", episode_id=episode.id,
                 skill_id=top.id)
            return None

        emit("macro_attempt", episode_id=episode.id, skill_id=top.id,
             similarity=sim, fitness=top.fitness_mean, n_steps=len(macro.steps),
             threshold=threshold, macro_confidence=macro.confidence)

        result = execute_macro(macro, task_text, self.tools)

        # Always record the partial trace, regardless of success
        for tr in result.traces:
            episode.traces.append(Trace(
                step=tr["step"],
                thought=f"[compiled macro] {top.name}",
                action=tr["tool"],
                action_input=json.dumps(tr["args"])[:1500],
                observation=tr["observation"],
            ))

        if not result.ok:
            emit("macro_aborted", episode_id=episode.id, skill_id=top.id,
                 step=result.aborted_at_step, reason=result.reason)
            # Salvage the partial trace into episode.notes BEFORE we clear
            # them. The clear() call below is mandatory (UNIQUE-constraint
            # on (episode_id, step) when the LLM-loop overlays its own
            # numbering) but the partial trace is data we paid for and
            # would otherwise be lost. Trace-alignment can still query it
            # post-hoc when comparing this failure to its success-twin.
            if result.traces:
                steps_str = " → ".join(
                    f"{tr.get('tool', '?')}@{tr.get('step', '?')}"
                    for tr in result.traces
                )
                episode.notes = (
                    (episode.notes + "\n" if episode.notes else "")
                    + f"[macro_aborted] step={result.aborted_at_step} "
                    f"reason={result.reason!r} prefix={steps_str}"
                )
            # Fall through to LLM loop — but reset traces so step numbering
            # restarts cleanly without UNIQUE-constraint collisions.
            episode.traces.clear()
            return None

        episode.final_answer = result.final_answer
        ok, msg = validator(result.final_answer)
        emit("macro_succeeded", episode_id=episode.id, skill_id=top.id,
             validator_ok=ok, n_steps=len(result.traces))
        return ok, msg

    def _adaptive_macro_threshold(self, macro_confidence: float) -> float:
        """Lower the similarity threshold when the compiled macro is high-confidence.

        Rationale: a macro distilled from N near-identical traces (high LLM-rated
        confidence) generalises better than a low-confidence one. We let it
        fire on slightly less similar tasks. Math: linear in confidence above 0.5,
        clamped to a hard floor so we never short-circuit on weak matches.
        """
        base = CONFIG.compile_apply_min_similarity
        if not CONFIG.compile_adaptive_enabled:
            return base
        delta = max(0.0, float(macro_confidence) - 0.5) * CONFIG.compile_adaptive_k
        return max(CONFIG.compile_apply_floor_similarity, base - delta)

    def _prioritise_episodes(
        self, candidates: list[Episode], query_text: str,
    ) -> list[EpisodeChoice]:
        """Rank a set of candidate episodes by composite priority.

        Used by `_avoid_path_block`, `_historical_divergence_counts`
        and `_divergence_block` to replace the legacy `failed[0]` /
        token-overlap heuristics. The ranking combines cosine
        relevance to the current task and an exponential-decay
        recency factor — see `selection.consider_episodes` for the
        math.

        Encoding cost: one embed per candidate. Bounded to a handful
        of episodes by the upstream `recall(k=...)`. We don't cache
        the per-call dict because callers are short-lived (one
        forward-replay block per wake run).
        """
        if not candidates:
            return []
        query_emb = embedding.encode(query_text)
        eps_embs = {
            ep.id: embedding.encode(ep.task_text or ep.id)
            for ep in candidates
        }
        return consider_episodes(
            candidates, query_emb, episode_embeddings=eps_embs,
        )

    def _skill_similarity(self, task_text: str, skill: Skill) -> float:
        """Cosine similarity between task and the skill's effective trigger embedding.

        Uses the Hebbian-learned embedding when present, otherwise the
        canonical name+trigger encoding.
        """
        try:
            task_emb = embedding.encode(task_text)
            if skill.learned_embedding is not None:
                skill_emb = np.asarray(skill.learned_embedding, dtype=np.float32)
            else:
                skill_emb = embedding.encode(f"{skill.name}\n{skill.trigger}")
            return float(np.dot(task_emb, skill_emb))
        except Exception:  # noqa: BLE001
            return 0.0

    # --- Tool exposure -----------------------------------------------------

    def _tool_catalog(self) -> str:
        lines = []
        for name, spec in self.tools.items():
            lines.append(f"- `{name}`: {spec.description}\n  schema: {json.dumps(spec.schema)}")
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        return WAKE_SYSTEM + "\n\nAVAILABLE TOOLS:\n" + self._tool_catalog()

    # --- Main loop ---------------------------------------------------------

    def run(self, task_id: str, task_text: str, validator: Validator) -> WakeResult:
        emit("episode_started", task_id=task_id)
        # FORGIA pezzo #17 — drift the cross-session context with this
        # task's text BEFORE retrieval, so `_retrieve_episodes` can use
        # the freshly-updated context as the recall cue. This is the
        # Howard & Kahana (2002) list-context update step.
        if CONFIG.tcm_cross_session_enabled:
            self._context_engine.observe(embedding.encode(task_text))
        skills = self._retrieve_skills(task_text)
        episodes = self._retrieve_episodes(task_text)
        emit("memory_retrieved", task_id=task_id, n_skills=len(skills), n_episodes=len(episodes))

        episode = Episode(
            task_id=task_id,
            task_text=task_text,
            skills_used=[s.id for s in skills],
        )

        # PROCEDURAL COMPILATION FAST-PATH ----------------------------------
        # If the top retrieved skill has a compiled macro and matches the task
        # strongly enough, execute the macro deterministically — zero LLM calls.
        # Falls through to the regular ReAct loop on any failure.
        macro_outcome = self._try_compiled_macro(episode, task_text, skills, validator)
        used_macro = False
        if macro_outcome is not None:
            success, msg = macro_outcome
            used_macro = True
        else:
            success, msg = self._run_loop(episode, task_text, skills, episodes, validator)

        # Self-critique on failure
        if (not success) and self.cfg.self_critique:
            episode.critique = self._critique(episode, expected=msg)
            for retry in range(self.cfg.critique_retries):
                emit("critique_retry", task_id=task_id, retry=retry + 1)
                retry_ep = Episode(
                    task_id=task_id,
                    task_text=task_text,
                    skills_used=[s.id for s in skills],
                    notes=f"retry {retry + 1} after critique",
                )
                # Inject critique into the task prompt to anchor learning
                augmented_task = (
                    task_text + f"\n\n[PREVIOUS ATTEMPT FAILED. LESSON: {episode.critique}]"
                )
                success, msg = self._run_loop(
                    retry_ep, augmented_task, skills, episodes, validator
                )
                if success:
                    retry_ep.notes = f"recovered after critique (retry {retry+1})"
                    episode = retry_ep  # supersede
                    break

        episode.outcome = "success" if success else "failure"
        # FORGIA pezzo #15: cabling of ContextEngine (pezzo #12 primitive)
        # into the wake loop. The encoded context is the post-task drift
        # of the TCM context vector seeded with the task text and
        # observed across every tool result. Persisted alongside the
        # episode so future recalls with `context_emb=cur_ctx,
        # context_weight=β > 0` can boost episodes encoded in similar
        # contexts (Tulving 1973 encoding-specificity).
        ctx_emb = (
            self._build_episode_context(task_text, episode.traces)
            if CONFIG.tcm_wake_enabled else None
        )
        # embed="auto" — non-blocking: defer the embedding if the encode daemon
        # is cold/starved so closing the wake loop never hangs the agent.
        self.memory.store(episode, context_emb=ctx_emb, embed="auto")

        # Update skill fitness + Hebbian embedding drift on success
        for s in skills:
            self.skills.update_fitness(
                s.id, success=success, tokens=episode.tokens_used,
                task_text=task_text,
            )

        emit("episode_completed", episode_id=episode.id, task_id=task_id,
             outcome=episode.outcome, steps=episode.num_steps,
             tokens_used=episode.tokens_used, n_skills_used=len(skills))

        return WakeResult(
            episode=episode, success=success, message=msg,
            skills_retrieved=skills, used_macro=used_macro,
        )

    def _run_loop(
        self,
        episode: Episode,
        task_text: str,
        skills: list[Skill],
        episodes: list,
        validator: Validator,
    ) -> tuple[bool, str]:
        """Pick an encoding strategy and run the unified wake loop.

        Native tool-use is preferred — it sidesteps the JSON-in-text
        fragility that caused ~30% of past failures (newline escaping
        in code payloads). On any exception inside the native path we
        fall back to ReAct text mode AFTER clearing the partial trace,
        so the fallback can re-number from step=1 without violating the
        (episode_id, step) unique constraint on `traces`.
        """
        if hasattr(self.llm, "supports_tools") and self.llm.supports_tools():
            try:
                return self._run_with_strategy(
                    NativeToolsStrategy(self._tool_schemas()),
                    episode, task_text, skills, episodes, validator,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "tools_loop_fallback", error=str(exc),
                    tool_traces_dropped=len(episode.traces),
                )
                episode.traces.clear()
        return self._run_with_strategy(
            ReActStrategy(WAKE_SYSTEM, self._tool_catalog()),
            episode, task_text, skills, episodes, validator,
        )

    def _run_with_strategy(
        self,
        strategy: WakeStrategy,
        episode: Episode,
        task_text: str,
        skills: list[Skill],
        episodes: list,
        validator: Validator,
    ) -> tuple[bool, str]:
        """The unified wake loop — single source of truth.

        The flow is identical for native tool-use and ReAct text mode;
        the `strategy` injects the encoding-specific behaviour at four
        seams: prompt building, LLM call, message-list mutation, and
        working-memory pruning. Anything in this function is invariant
        across encodings — if it ever isn't, push the variation into
        the strategy rather than branching here.

        Trace step is monotonic across the whole episode: a single LLM
        turn may emit multiple parallel tool calls, each must have a
        unique step to satisfy the (episode_id, step) primary key on
        the `traces` table.
        """
        user = self._build_user_prompt(task_text, skills, episodes)
        system = strategy.system_prompt(self._tool_catalog())
        messages = strategy.initial_messages(user)
        trace_step = 0

        for step in range(1, self.cfg.max_steps + 1):
            turn = strategy.call(self.llm, system, messages)
            episode.tokens_used += turn.total_tokens

            if not turn.tool_calls:
                trace_step, outcome = strategy.on_no_tool_calls(
                    turn, episode, step, trace_step, validator,
                )
                return outcome

            strategy.append_assistant(messages, turn)

            observations: list[ToolObservation] = []
            answered = False
            answer_text = ""
            answer_validation: tuple[bool, str] | None = None

            # rescan2 2026-06-02: parallel tool calls AFTER submit_solution in
            # the same turn must NOT run side-effects (episode already answered).
            # Still record an observation for each (preserves tool_call/result
            # alignment for the provider message list).
            _submit_cutoff = _submit_cutoff_index(turn.tool_calls)
            for idx, tc in enumerate(turn.tool_calls):
                if idx >= _submit_cutoff:
                    result = ToolResult(
                        ok=False, output="",
                        error=("skipped: parallel tool call after "
                               "submit_solution (no post-submit side-effects)"),
                    )
                elif _injection_review_blocks_call(tc.name, episode.traces):
                    emit("prompt_injection_blocked", episode_id=episode.id,
                         tool=tc.name, mode=strategy.mode_name)
                    refusal = (
                        f"REFUSED: tool {tc.name!r} blocked because the recent "
                        "trajectory included external content (web_fetch / "
                        "vision_describe / web_search). Set "
                        "HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL=1 to override."
                    )
                    result = ToolResult(ok=False, output="", error=refusal)
                else:
                    result = self._call_tool(tc.name, tc.input)

                observation = result.to_observation()
                observation = _wrap_untrusted(
                    observation, tc.name, _extract_source_arg(tc),
                )

                trace_step += 1
                episode.traces.append(Trace(
                    step=trace_step,
                    thought=turn.text or "",
                    action=tc.name,
                    action_input=json.dumps(tc.input)[:1500],
                    observation=observation,
                ))
                emit("react_step", episode_id=episode.id, step=trace_step,
                     action=tc.name, ok=result.ok, mode=strategy.mode_name)

                if tc.name == "submit_solution" and result.ok:
                    answer_text = str(tc.input.get("answer", result.output))
                    answer_validation = validator(answer_text)
                    answered = True

                observations.append(ToolObservation(
                    tool_call_id=tc.id, tool_name=tc.name, observation=observation,
                ))

            strategy.append_observations(messages, turn, observations)

            if CONFIG.working_memory_pruning_enabled:
                messages, n_pruned = strategy.prune(messages)
                if n_pruned > 0:
                    event_name = (
                        "working_memory_pruned"
                        if strategy.mode_name == "tools"
                        else "working_memory_pruned_react"
                    )
                    emit(event_name, n=n_pruned,
                         size_after=_wm_estimate_size(messages))

            if answered:
                episode.final_answer = answer_text
                ok, msg = answer_validation or (False, "(no validator)")
                return ok, msg

        return False, "max_steps reached"

    # --- Native tool-use loop (Anthropic / OpenAI-compat) -----------------

    def _run_loop_tools(
        self,
        episode: Episode,
        task_text: str,
        skills: list[Skill],
        episodes: list,
        validator: Validator,
    ) -> tuple[bool, str]:
        """Native tool-use entry — thin facade over `_run_with_strategy`.

        Preserved as a separate method so existing tests / external
        callers keep working. The actual loop body lives once in
        `_run_with_strategy`.
        """
        return self._run_with_strategy(
            NativeToolsStrategy(self._tool_schemas()),
            episode, task_text, skills, episodes, validator,
        )

    @staticmethod
    def _estimate_messages_size(messages: list[dict[str, Any]]) -> int:
        """Thin wrapper — kept on the class for backward compat with tests
        and downstream callers. The algorithm lives in `working_memory.py`."""
        return _wm_estimate_size(messages)

    def _prune_working_memory(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Trim mid-trajectory tool observations once the running message
        list exceeds the budget. Native tool-use encoding (Anthropic
        tool_result blocks + OpenAI tool role).

        See `working_memory.prune_messages` for the algorithm; this method
        only supplies the candidate predicate + the in-place replacer for
        the native encoding, then emits the observability event.
        """
        messages, n_pruned = prune_messages(
            messages,
            budget=CONFIG.working_memory_max_chars,
            keep_tail=CONFIG.working_memory_keep_tail,
            placeholder=CONFIG.working_memory_pruned_placeholder,
            is_candidate=native_tool_is_candidate,
            replace_in_place=native_tool_replace,
        )
        if n_pruned:
            emit("working_memory_pruned", n=n_pruned,
                 size_after=_wm_estimate_size(messages))
        return messages

    def _format_tool_results(
        self, results: list[dict[str, Any]], raw_assistant: Any
    ) -> list[dict[str, Any]]:
        """Format tool results — backward-compat shim around
        `NativeToolsStrategy.append_observations`.

        The unified loop now appends observations directly via the
        strategy. This method is kept for tests (and any external
        caller) that pinned the legacy entry point.
        """
        observations = [
            ToolObservation(
                tool_call_id=r["tool_call_id"],
                tool_name=r.get("name", ""),
                observation=r["observation"],
            )
            for r in results
        ]
        # Mirror the routing the strategy does internally — list ⇒ Anthropic,
        # dict ⇒ OpenAI / Ollama. We construct an empty staging list, let
        # the strategy push, then return what it produced.
        staging: list[dict[str, Any]] = []
        turn = ParsedTurn(
            text="", tool_calls=[], total_tokens=0, raw=raw_assistant,
        )
        NativeToolsStrategy(tool_schemas=[]).append_observations(
            staging, turn, observations,
        )
        return staging

    def _dispatch_native(self, tc: ToolCall) -> ToolResult:
        """Native tool-use dispatch — args come in already structured.

        Backward-compat thin wrapper: tests call this directly.
        """
        return self._call_tool(tc.name, tc.input)

    def _call_tool(
        self, name: str, args: dict[str, Any], *, error_context: str = "",
    ) -> ToolResult:
        """Execute one tool by name. Single source of truth for both
        the native and the ReAct dispatch paths.

        `error_context` is appended to "bad arguments" errors so the
        legacy ReAct text mode keeps its richer message ("for {action}: ...")
        — the loop can identify which tool's argument shape was wrong
        in a thought trace.
        """
        spec = self.tools.get(name)
        if not spec:
            return ToolResult(ok=False, output="", error=f"unknown tool: {name}")
        try:
            result = spec.handler(**args)
            if isinstance(result, ToolResult):
                return result
            return ToolResult(ok=True, output=str(result))
        except TypeError as exc:
            return ToolResult(
                ok=False, output="",
                error=f"bad arguments{error_context}: {exc}",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, output="", error=f"tool error: {exc}")

    def _tool_schemas(self) -> list[dict[str, Any]]:
        """Build the tools payload for native tool-use APIs."""
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.schema,
            }
            for spec in self.tools.values()
        ]

    # --- ReAct text-parsing loop (legacy fallback) ------------------------

    def _run_loop_react(
        self,
        episode: Episode,
        task_text: str,
        skills: list[Skill],
        episodes: list,
        validator: Validator,
    ) -> tuple[bool, str]:
        """ReAct text-mode entry — thin facade over `_run_with_strategy`.

        Used as the fallback when the active LLM doesn't support native
        tool-use (or `complete_with_tools` raises). The actual loop body
        lives once in `_run_with_strategy`; this method exists for
        backward compat with tests / external callers.
        """
        return self._run_with_strategy(
            ReActStrategy(WAKE_SYSTEM, self._tool_catalog()),
            episode, task_text, skills, episodes, validator,
        )

    def _prune_working_memory_react(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """ReAct text-mode pruner — same algorithm, different encoding.

        ReAct alternates assistant Thought/Action/ActionInput turns with
        user 'Observation: ...' messages. The `react_obs_*` strategy
        functions in `working_memory.py` know how to spot and compact
        those — this method just wires them into the generic pruner and
        emits the observability event.
        """
        messages, n_pruned = prune_messages(
            messages,
            budget=CONFIG.working_memory_max_chars,
            keep_tail=CONFIG.working_memory_keep_tail,
            placeholder=CONFIG.working_memory_pruned_placeholder,
            is_candidate=react_obs_is_candidate,
            replace_in_place=react_obs_replace,
        )
        if n_pruned:
            emit("working_memory_pruned_react", n=n_pruned)
        return messages

    def _dispatch(self, action: str, action_input: str) -> ToolResult:
        """ReAct text-mode dispatch — parses ActionInput as JSON first.

        Delegates the actual handler call to `_call_tool` so error
        handling is single-source. The `for {action}` context is
        re-attached on bad-argument errors to preserve the legacy
        message shape that tests pin against.
        """
        try:
            args = (
                json.loads(action_input)
                if action_input.strip().startswith("{") else {}
            )
        except json.JSONDecodeError as exc:
            return ToolResult(
                ok=False, output="",
                error=f"invalid JSON ActionInput: {exc}",
            )
        return self._call_tool(action, args, error_context=f" for {action}")

    # --- Self-critique (Reflexion-style) ----------------------------------

    def _critique(self, episode: Episode, expected: str) -> str:
        try:
            resp = self.llm.complete(
                system=CRITIC_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": CRITIC_USER_TEMPLATE.format(
                        trajectory=episode.trajectory_text(),
                        expected=expected or "(no oracle hint)",
                    ),
                }],
                temperature=CONFIG.llm_temperature_critic,
                model=resolve_model("critic"),
            )
            episode.tokens_used += resp.total_tokens
            return resp.text.strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("critique_failed", error=str(exc))
            return ""


def _extract_answer(action_input: str, output: str) -> str:
    """Best-effort extraction of the answer from submit_solution payload."""
    try:
        data = json.loads(action_input)
        if "answer" in data:
            return str(data["answer"])
    except Exception:
        pass
    return output or action_input
