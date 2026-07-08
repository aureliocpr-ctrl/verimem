"""Sleep cycle — multi-stage consolidation.

Inspired by the two-stage model of memory consolidation
(Walker & Stickgold 2004; Diekelmann & Born 2010):

  - NREM (slow-wave): replay episodes, extract invariant patterns →
    consolidate into PROCEDURAL skills + SEMANTIC facts.
  - REM (paradoxical): creative recombination of consolidated skills →
    novel hypotheses (hybrid skills) for testing in next wake cycle.
  - Pruning: skills/facts below fitness threshold archived (forgetting curve).
  - Schema formation: clusters of similar skills get a parent meta-skill.

All stages are LLM-driven but the *selection* of what to consolidate is
done with classic clustering + fitness math (no LLM needed).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .compilation import compile_macro
from .config import CONFIG
from .episode import Episode
from .llm import get_llm, resolve_model
from .memory import EpisodicMemory
from .observability import emit, get_log
from .prompts import (
    COUNTERFACTUAL_SYSTEM,
    COUNTERFACTUAL_USER_TEMPLATE,
    CURATOR_MERGE_SYSTEM,
    CURATOR_MERGE_USER_TEMPLATE,
    DREAMER_NREM_SYSTEM,
    DREAMER_NREM_USER_TEMPLATE,
    DREAMER_REM_SYSTEM,
    DREAMER_REM_USER_TEMPLATE,
    PRACTICE_SYSTEM,
    PRACTICE_USER_TEMPLATE,
    SCHEMA_SYSTEM,
    SCHEMA_USER_TEMPLATE,
)
from .semantic import Fact, SemanticMemory
from .skill import Skill, SkillLibrary

log = get_log()


# --- Replay priority -------------------------------------------------------


def replay_priority(
    ep: Episode,
    now: float,
    max_age: float,
    skill_avg_steps: dict[str, float] | None = None,
) -> float:
    """Score 0..1 — failures get priority, then recency, diversity, and surprise.

    Components:
      - failure        : failures replayed more than successes
      - recency        : recent episodes prioritised over old
      - diversity      : episodes with few/no skills used = novel
      - surprise (NEW) : episodes whose num_steps deviates from the
        mean num_steps of their skill cluster get a salience boost.
        Cognitive analogue: hippocampal replay disproportionately
        encodes prediction errors (Buzsáki 2015, Singer & Frank 2009)
        — anomalous outcomes carry more learning signal than typical ones.

    The surprise term is OPTIONAL: when `skill_avg_steps` is None or the
    episode used no skill we recognise, we fall back to the original
    three-component score. This keeps the function backward-compatible
    with existing callers.
    """
    p_failure = 1.0 if ep.outcome == "failure" else 0.3
    age = max(0.0, now - ep.created_at)
    p_recent = max(0.0, 1.0 - (age / max_age)) if max_age > 0 else 0.5
    p_diverse = 1.0 / (1 + len(ep.skills_used))

    # Surprise: relative deviation from skill's typical num_steps. We pick
    # the SMALLEST relative deviation across all skills the episode used —
    # an episode that's typical for one skill but anomalous for another
    # is mostly typical (the right skill explains it). For an episode
    # whose skills haven't yet accumulated stats we score 0.
    p_surprise = 0.0
    if skill_avg_steps:
        deviations: list[float] = []
        n_steps = ep.num_steps
        for sid in ep.skills_used:
            avg = skill_avg_steps.get(sid, 0.0)
            if avg > 0.0:
                deviations.append(abs(n_steps - avg) / avg)
        if deviations:
            # Squash to [0, 1] with a soft cap. A 100% deviation
            # (e.g. 6 steps when the average was 3) gives 0.5.
            raw = min(deviations)
            p_surprise = raw / (1.0 + raw)

    weight_surprise = float(getattr(
        CONFIG, "sleep_replay_priority_surprise", 0.0,
    ))
    # FORGIA pezzo #19 — cached `salience_score` (computed by
    # `EpisodicMemory.compute_salience` at store time) is a per-episode
    # continuous prediction-error signal (Buzsáki 2015). When the weight
    # is non-zero it adds directly to the replay priority — surprising
    # episodes (high salience) are preferentially replayed, generalising
    # the binary `failure` flag. Defaults to 0.0 (off) so legacy callers
    # are unaffected.
    weight_salience = float(getattr(
        CONFIG, "sleep_replay_priority_salience", 0.0,
    ))
    p_salience = float(getattr(ep, "salience_score", 0.0))
    return (
        CONFIG.sleep_replay_priority_failure * p_failure
        + CONFIG.sleep_replay_priority_recent * p_recent
        + CONFIG.sleep_replay_priority_diverse * p_diverse
        + weight_surprise * p_surprise
        + weight_salience * p_salience
    )


def compute_skill_avg_steps(
    memory: EpisodicMemory,
    skill_ids: set[str],
) -> dict[str, float]:
    """Map each skill_id to the mean num_steps across its past episodes.

    Used to compute the surprise term in replay_priority. We touch the
    DB exactly once and aggregate in-memory; for a sleep cycle that
    runs over ~hundreds of episodes this is a single SELECT.

    CYCLE #21 perf: implementazione SQL aggregate con json_each, evitando
    di deserializzare TUTTI gli ep (memory.all() carica traces + DG emb).
    Bench live a N=5K: Python scan = 164ms, SQL = ~20ms (~8x speedup).
    Conta ogni occorrenza di sid (NO dedup): se la stessa skill compare
    2 volte nello stesso episodio, num_steps di quell'ep entra due volte
    nella media — replica la semantica del codice originale (l'aggregate
    è la media delle "skill citations" non degli episodi distinti).
    """
    if not skill_ids:
        return {}
    import sqlite3 as _sql
    try:
        with memory._connect() as conn:
            # COUNT episodes that have num_steps stored; aggregate per sid.
            # NOTE: num_steps non è colonna diretta, è derivata dai traces
            # via len(traces). Aggrego direttamente come COUNT(traces).
            # Workaround: usare json_each + JOIN su traces COUNT.
            rows = conn.execute(
                """SELECT je.value AS sid,
                          AVG(coalesce((SELECT COUNT(*) FROM traces t
                                        WHERE t.episode_id = e.id), 0)) AS avg_steps
                   FROM episodes e, json_each(e.skills_used) je
                   WHERE je.value IN (""" + ",".join("?" * len(skill_ids)) + """)
                   GROUP BY je.value""",
                tuple(skill_ids),
            ).fetchall()
        result = {r["sid"]: float(r["avg_steps"] or 0.0) for r in rows}
        # Skill senza occorrenze → 0.0
        for sid in skill_ids:
            result.setdefault(sid, 0.0)
        return result
    except (_sql.OperationalError, Exception):  # noqa: BLE001
        # Fallback Python (vecchie SQLite / JSON malformato).
        counters: dict[str, list[int]] = {sid: [] for sid in skill_ids}
        for ep in memory.all():
            for sid in ep.skills_used:
                if sid in counters:
                    counters[sid].append(ep.num_steps)
        return {
            sid: (sum(steps) / len(steps)) if steps else 0.0
            for sid, steps in counters.items()
        }


# --- JSON extractor (LLMs sometimes wrap in fences) -----------------------


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON OBJECT from a possibly-wrapped LLM response.

    Thin alias for the shared `jsonutil.extract_json_object` helper —
    kept here for backward-compat with existing imports. New callers
    should import from `engram.jsonutil` directly.
    """
    from .jsonutil import extract_json_object
    return extract_json_object(text)


# --- Stage outputs ---------------------------------------------------------


@dataclass
class SleepReport:
    n_episodes_replayed: int = 0
    n_clusters: int = 0
    n_nrem_skills: int = 0
    n_rem_skills: int = 0
    n_facts: int = 0
    n_macros_compiled: int = 0
    n_counterfactuals: int = 0
    n_schemas: int = 0
    n_practice_prompts: int = 0
    # FORGIA pezzo #9: count of episodes the Ebbinghaus decay stage
    # pruned in this cycle (their retention fell below threshold).
    n_episodes_decayed: int = 0
    promoted: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    merged: list[tuple[str, str, str]] = field(default_factory=list)
    compiled_skill_ids: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    tokens_used: int = 0
    # FORGIA pezzo #50: surface the per-cycle LLM call count so callers
    # (dashboards, the bench harness, rate-limit monitors) can see at a
    # glance how heavy a given sleep cycle was. Useful when a free-tier
    # provider quotas out mid-bench (groq case in skill_compounding).
    n_llm_calls: int = 0
    # FORGIA pezzo #163: bundles discovered by the sleep engine for
    # potential compound-macro abstraction. `n_bundles_proposed` is
    # the count, `bundle_candidates` carries the (a, b, count) tuples
    # for downstream stages (#164+) to consume.
    n_bundles_proposed: int = 0
    bundle_candidates: list[tuple[str, str, int]] = field(default_factory=list)
    # FORGIA pezzo #165: count of compound-macro candidate skills
    # synthesized from the discovered bundles in this cycle.
    n_bundle_skills: int = 0
    # FORGIA pezzo #170: count of antagonist links written this cycle
    # (lateral inhibition / Földiák 1990).
    n_antagonisms: int = 0
    # FORGIA pezzo #175: count of episodes whose salience got boosted
    # by the synaptic-tagging mechanism (Frey & Morris 1997).
    n_synaptic_tags: int = 0
    # FORGIA pezzo #178: count of engram-crossover hybrids generated.
    n_crossovers: int = 0


# --- Sleep engine ----------------------------------------------------------


class SleepEngine:
    def __init__(
        self,
        memory: EpisodicMemory | None = None,
        skills: SkillLibrary | None = None,
        semantic: SemanticMemory | None = None,
        llm: Any | None = None,
        seed: int | None = None,
    ) -> None:
        self.memory = memory or EpisodicMemory()
        self.skills = skills or SkillLibrary()
        self.semantic = semantic or SemanticMemory()
        self.llm = llm or get_llm()
        self.rng = random.Random(seed if seed is not None else CONFIG.seed)

    def cycle_light(self) -> SleepReport:
        """CYCLE #12 — light sleep pass: NO LLM call, only promote/retire
        + skill dedup. Counterpart to `cycle()` for the hosted-mode
        `hippo_consolidate_light` MCP tool.

        Background: il MCP handler `_consolidate_light` (mcp_server.py:149)
        chiamava `a.sleep.cycle_light()` ma il metodo NON ESISTEVA →
        AttributeError catturato → fallback con threshold hardcoded
        (0.7/0.2 + min_trials 5/3) NON allineati a CONFIG (0.6/0.25/3).
        Conseguenza live: 1 candidate t=3 s=3 fit=0.80 (eligible promote
        in CONFIG) restava candidate perché min_trials=5 hardcoded.

        Questo metodo proper:
          - chiama `self.skills.promote_or_retire()` che usa CONFIG corretti
          - ritorna SleepReport con promoted/retired/duration popolati
          - NO chiamate LLM (sicuro in hosted mode)
        """
        import time
        t0 = time.time()
        report = SleepReport()
        try:
            promoted, retired = self.skills.promote_or_retire()
            report.promoted = list(promoted)
            report.retired = list(retired)
        except Exception as exc:  # noqa: BLE001
            emit("sleep_light_failed", error=str(exc))
        report.duration_s = time.time() - t0
        report.n_episodes_replayed = 0  # light cycle non itera episodi
        return report

    def cycle(self) -> SleepReport:
        """Run a full sleep cycle: NREM → REM → Pruning → Curator."""
        import time

        t0 = time.time()
        report = SleepReport()
        n_eps = self.memory.count()
        if n_eps < CONFIG.sleep_min_episodes:
            emit("sleep_skipped", reason="insufficient_episodes", n=n_eps)
            return report

        # FORGIA pezzo #50: count LLM calls per cycle. Wrap `self.llm`
        # for the duration of the cycle so every `complete*` call
        # increments a counter we surface on the SleepReport.
        # fix leak §8 (rescan2): se un cycle precedente e' uscito per eccezione
        # lasciando montato il wrapper _CountingLLM (il restore di fine-ciclo
        # NON e' in un finally), smontalo PRIMA di ri-wrappare -> evita nesting
        # _CountingLLM(_CountingLLM(...)) e conteggio LLM cumulativo falsato.
        original_llm = getattr(self.llm, "_inner", self.llm)
        n_calls = {"v": 0}

        class _CountingLLM:
            def __init__(self, inner):
                self._inner = inner

            def supports_tools(self):
                return getattr(self._inner, "supports_tools", lambda: False)()

            def complete(self, *a, **kw):
                n_calls["v"] += 1
                return self._inner.complete(*a, **kw)

            def complete_with_tools(self, *a, **kw):
                n_calls["v"] += 1
                return self._inner.complete_with_tools(*a, **kw)

        self.llm = _CountingLLM(original_llm)  # type: ignore[assignment]

        emit("sleep_started", n_episodes=n_eps)
        report.tokens_used += self._stage_nrem(report)
        report.tokens_used += self._stage_rem(report)
        report.tokens_used += self._stage_curator(report)
        report.tokens_used += self._stage_compilation(report)
        if CONFIG.counterfactual_enabled:
            report.tokens_used += self._stage_counterfactual(report)
        if CONFIG.schema_enabled:
            report.tokens_used += self._stage_schema(report)
        if CONFIG.practice_enabled:
            report.tokens_used += self._stage_practice(report)
        # Spontaneous reactivation runs AFTER all consolidation stages but
        # BEFORE pruning — so reactivation can rescue skills from the
        # decay/retirement cliff in the same cycle.
        if getattr(CONFIG, "spontaneous_reactivation_enabled", False):
            self._stage_spontaneous_reactivation(report)
        # Episode decay (FORGIA pezzo #9): prune episodes whose Ebbinghaus
        # retention fell below threshold. Runs BEFORE skill pruning so
        # the skill-retention pass sees the cleaned corpus.
        if getattr(CONFIG, "episode_decay_enabled", False):
            self._stage_episode_decay(report)
        # Bundle discovery (FORGIA pezzo #164): surface skill-pair
        # bundles on the report for downstream macro-abstraction.
        # Zero LLM cost. Off by default; opt-in via config.
        if getattr(CONFIG, "bundle_discovery_enabled", False):
            self._stage_bundle_discovery(
                report,
                min_count=getattr(CONFIG, "bundle_discovery_min_count", 3),
                min_overlap=getattr(CONFIG, "bundle_discovery_min_overlap", 0.6),
            )
            # FORGIA pezzo #166: same flag also gates abstraction;
            # if discovery is on, abstraction follows automatically.
            self._stage_abstract_bundles(report)
        # FORGIA pezzo #172: negative-bundle / lateral inhibition stage.
        # Pure data, zero LLM cost. Off by default; opt-in via config.
        if getattr(CONFIG, "negative_bundle_enabled", False):
            self._stage_negative_bundles(
                report,
                min_count=getattr(CONFIG, "negative_bundle_min_count", 3),
                min_fail_ratio=getattr(
                    CONFIG, "negative_bundle_min_fail_ratio", 0.7,
                ),
            )
        # FORGIA pezzo #176: synaptic tagging stage (Frey & Morris 1997).
        # Boosts salience of weak episodes whose family of skills was
        # subsequently mastered. Pure-arithmetic, zero LLM cost.
        if getattr(CONFIG, "synaptic_tagging_enabled", False):
            self._stage_synaptic_tagging(
                report,
                window_s=getattr(CONFIG, "synaptic_tag_window_s", 3600.0),
                salience_boost=getattr(
                    CONFIG, "synaptic_tag_salience_boost", 0.2,
                ),
            )
        # FORGIA pezzo #178: engram-crossover stage. Generates hybrid
        # skills via genetic-programming-style recombination on top-
        # fitness skills. Zero LLM cost. Off by default.
        if getattr(CONFIG, "crossover_enabled", False):
            self._stage_crossover(
                report,
                n_pairs=getattr(CONFIG, "crossover_n_pairs", 2),
                top_k=getattr(CONFIG, "crossover_top_k", 5),
            )
        # Tier-2 consolidation triage (opt-in, ENGRAM_EVIDENCE_REQUIREMENT): quarantine
        # specific-unsourced coincidental-noise facts via the LLM judge (validated 1.0
        # noise-recall / 0.0 false-declass). BEFORE pruning, capped per cycle, fail-safe.
        try:
            from .evidence_requirement import evidence_requirement_enabled
            if evidence_requirement_enabled():
                self._stage_tier2_triage(report)
        except Exception as exc:  # noqa: BLE001 — triage never breaks the cycle
            emit("sleep_tier2_triage_failed", error=str(exc))
        self._stage_pruning(report)
        report.duration_s = time.time() - t0
        # FORGIA #50: surface the call count, then unwrap the counting LLM.
        report.n_llm_calls = n_calls["v"]
        self.llm = original_llm
        emit("sleep_completed",
             nrem_skills=report.n_nrem_skills,
             rem_skills=report.n_rem_skills,
             macros=report.n_macros_compiled,
             counterfactuals=report.n_counterfactuals,
             schemas=report.n_schemas,
             promoted=len(report.promoted),
             retired=len(report.retired),
             merged=len(report.merged),
             n_llm_calls=report.n_llm_calls,
             duration_s=round(report.duration_s, 2))
        return report

    # --- Stage 1: NREM consolidation ---------------------------------------

    def _stage_nrem(self, report: SleepReport) -> int:
        clusters = self.memory.cluster_similar(
            eps_threshold=CONFIG.sleep_nrem_cluster_threshold
        )
        # Filter clusters with min size
        clusters = [c for c in clusters if len(c) >= CONFIG.sleep_nrem_cluster_min_size]
        # Order by replay priority (sum of episode priorities) and cap
        import time
        now = time.time()
        max_age = max((now - ep.created_at for c in clusters for ep in c), default=1.0)
        # Surprise term needs per-skill avg num_steps. Gather skill ids
        # touched by episodes in this batch, query once, feed into the
        # priority function.
        skill_ids = {sid for c in clusters for ep in c for sid in ep.skills_used}
        skill_avg_steps = (
            compute_skill_avg_steps(self.memory, skill_ids)
            if skill_ids and CONFIG.sleep_replay_priority_surprise > 0
            else {}
        )
        clusters.sort(
            key=lambda c: -sum(
                replay_priority(ep, now, max_age, skill_avg_steps) for ep in c
            )
        )
        clusters = clusters[: CONFIG.sleep_nrem_max_clusters]
        report.n_clusters = len(clusters)
        report.n_episodes_replayed = sum(len(c) for c in clusters)
        emit("nrem_started", n_clusters=len(clusters))

        tokens = 0
        for cluster in clusters:
            try:
                skill, fact, t = self._synthesize_from_cluster(cluster)
                tokens += t
                if skill is not None:
                    self.skills.store(skill)
                    report.n_nrem_skills += 1
                    emit("skill_synthesized", skill_id=skill.id, skill_name=skill.name,
                         stage="nrem", from_episodes=len(cluster))
                if fact is not None:
                    self.semantic.store(fact)
                    report.n_facts += 1
            except Exception:
                log.exception("nrem_synth_failed")
        return tokens

    def _synthesize_from_cluster(
        self, cluster: list[Episode]
    ) -> tuple[Skill | None, Fact | None, int]:
        n_success = sum(1 for e in cluster if e.outcome == "success")
        n_failure = sum(1 for e in cluster if e.outcome == "failure")
        body = "\n\n".join(f"### Episode {i+1}\n{e.trajectory_text()}"
                           for i, e in enumerate(cluster[:5]))
        resp = self.llm.complete(
            system=DREAMER_NREM_SYSTEM,
            messages=[{
                "role": "user",
                "content": DREAMER_NREM_USER_TEMPLATE.format(
                    episodes=body, n_success=n_success, n_failure=n_failure,
                ),
            }],
            temperature=CONFIG.llm_temperature_dreamer,
            model=resolve_model("dreamer"),
        )
        data = _extract_json(resp.text)
        if not data or "name" not in data or "body" not in data:
            log.warning("nrem_invalid_json", raw=resp.text[:200])
            return None, None, resp.total_tokens
        skill = Skill(
            name=data.get("name", "")[:80],
            trigger=data.get("trigger", "")[:300],
            body=data.get("body", "")[:2000],
            rationale=data.get("rationale", "")[:300],
            stage="nrem",
            provenance_episodes=[e.id for e in cluster],
        )
        # Derive a one-line semantic fact from the rationale + cluster topic
        fact: Fact | None = None
        if skill.rationale:
            topic = (cluster[0].task_text[:40] or "general").strip()
            fact = Fact(
                proposition=skill.rationale,
                topic=topic,
                confidence=min(0.9, 0.5 + 0.1 * n_success - 0.05 * n_failure),
                source_episodes=[e.id for e in cluster],
            )
        return skill, fact, resp.total_tokens

    # --- Stage 2: REM creative recombination -------------------------------

    def _stage_rem(self, report: SleepReport) -> int:
        promoted = self.skills.all(status="promoted")
        candidates = self.skills.all(status="candidate")
        pool = promoted + candidates
        if len(pool) < CONFIG.sleep_rem_min_promoted:
            emit("rem_skipped", reason="insufficient_skills", n=len(pool))
            return 0
        emit("rem_started", n_pool=len(pool))
        tokens = 0
        for _ in range(CONFIG.sleep_rem_recombinations):
            a, b = self.rng.sample(pool, 2)
            # CQ #13 fix: don't recombine a skill with its own parent / child;
            # the Curator skips this case but REM did not, producing skills
            # whose parent_skills already had the same lineage relationship.
            if b.id in a.parent_skills or a.id in b.parent_skills:
                emit("rem_skipped_pair", reason="lineage_cycle",
                     a_id=a.id, b_id=b.id)
                continue
            try:
                hybrid, t = self._recombine(a, b)
                tokens += t
                if hybrid:
                    self.skills.store(hybrid)
                    report.n_rem_skills += 1
                    emit("skill_synthesized", skill_id=hybrid.id, skill_name=hybrid.name,
                         stage="rem", parents=[a.id, b.id])
            except Exception:
                log.exception("rem_recombine_failed", a_id=a.id, b_id=b.id)
        return tokens

    def _recombine(self, a: Skill, b: Skill) -> tuple[Skill | None, int]:
        resp = self.llm.complete(
            system=DREAMER_REM_SYSTEM,
            messages=[{
                "role": "user",
                "content": DREAMER_REM_USER_TEMPLATE.format(
                    skill_a=a.render(), skill_b=b.render(),
                ),
            }],
            temperature=CONFIG.llm_temperature_dreamer,
            model=resolve_model("dreamer"),
        )
        data = _extract_json(resp.text)
        if not data or "name" not in data or "body" not in data:
            return None, resp.total_tokens
        return Skill(
            name=data.get("name", "")[:80],
            trigger=data.get("trigger", "")[:300],
            body=data.get("body", "")[:2000],
            rationale=data.get("rationale", "")[:300],
            stage="rem",
            parent_skills=[a.id, b.id],
            provenance_episodes=list({*a.provenance_episodes, *b.provenance_episodes}),
        ), resp.total_tokens

    # --- Stage 3: Curator (de-duplication via semantic merge) -------------

    def _stage_curator(self, report: SleepReport) -> int:
        dups = self.skills.find_duplicates()
        tokens = 0
        for a, b, sim in dups[:3]:  # cap merges per cycle
            # Don't merge a parent and its child; that's lineage, not duplication
            if b.id in a.parent_skills or a.id in b.parent_skills:
                continue
            try:
                merged, t = self._merge(a, b)
                tokens += t
                if merged:
                    # Retire the lower-fitness one of the originals
                    loser = a if a.fitness_mean <= b.fitness_mean else b
                    loser.status = "retired"
                    self.skills.store(loser)
                    self.skills.store(merged)
                    report.merged.append((a.id, b.id, merged.id))
                    emit("skills_merged", a=a.id, b=b.id, merged=merged.id, similarity=sim)
            except Exception:
                log.exception("curator_merge_failed", a_id=a.id, b_id=b.id)
        return tokens

    def _merge(self, a: Skill, b: Skill) -> tuple[Skill | None, int]:
        resp = self.llm.complete(
            system=CURATOR_MERGE_SYSTEM,
            messages=[{
                "role": "user",
                "content": CURATOR_MERGE_USER_TEMPLATE.format(a=a.render(), b=b.render()),
            }],
            temperature=CONFIG.llm_temperature_critic,
            model=resolve_model("critic"),
        )
        data = _extract_json(resp.text)
        if not data or "name" not in data:
            return None, resp.total_tokens
        merged = Skill(
            name=data.get("name", "")[:80],
            trigger=data.get("trigger", "")[:300],
            body=data.get("body", "")[:2000],
            rationale=data.get("rationale", "")[:300],
            stage="manual",
            parent_skills=[a.id, b.id],
            provenance_episodes=list({*a.provenance_episodes, *b.provenance_episodes}),
            # audit#3-r3 R12: the merged body is a NEW, never-executed artifact —
            # start it UNTESTED (trials=successes=0, defaults) so it must earn
            # promotion through its own trials. Inheriting the SUM of the
            # parents' track record (the old "conservative carry-over") let the
            # promotion gate auto-promote an untested skill. Mirrors _recombine,
            # which already leaves the recombined skill at the clean defaults.
            status="candidate",
        )
        return merged, resp.total_tokens

    # --- Stage 4a: Procedural compilation -----------------------------------

    def _stage_compilation(self, report: SleepReport) -> int:
        """Distil successful skill traces into deterministic macros.

        For each promoted skill that has accumulated ≥ N successes, ask the
        DREAMER to compile a parameterised macro. Once compiled, the macro
        executes at wake time WITHOUT touching the LLM — making the skill
        faster and cheaper the more it is used.
        """
        candidates: list[Skill] = []
        for s in self.skills.all():
            if s.status == "retired":
                continue
            if s.compiled_macro is not None:
                continue  # already compiled — recompilation is future work
            if s.successes < CONFIG.compile_min_successes:
                continue
            if s.fitness_mean < CONFIG.compile_min_fitness:
                continue
            candidates.append(s)

        # Order by fitness descending so we compile the best skills first
        candidates.sort(key=lambda x: -x.fitness_mean)
        candidates = candidates[: CONFIG.compile_max_per_cycle]
        if not candidates:
            return 0
        emit("compilation_started", n_candidates=len(candidates))

        tokens = 0
        for skill in candidates:
            # Pull the most recent successful episodes that used this skill
            successful = [
                ep for ep in self.memory.all()
                if ep.outcome == "success" and skill.id in ep.skills_used
            ]
            if len(successful) < CONFIG.compile_min_successes:
                continue
            successful = successful[: CONFIG.compile_min_successes]
            try:
                macro = compile_macro(skill, successful, self.llm)
            except Exception:
                log.exception("compile_failed", skill_id=skill.id)
                continue
            if macro is None:
                continue
            skill.compiled_macro = macro.to_dict()
            self.skills.store(skill)
            report.n_macros_compiled += 1
            report.compiled_skill_ids.append(skill.id)
            # NB: token counts are emitted by compile_macro via the LLM client.
        return tokens

    # --- Stage 4b: Counterfactual REM ---------------------------------------

    def _stage_counterfactual(self, report: SleepReport) -> int:
        """Generate alternative strategies for skills that consistently fail.

        For each skill with low fitness and enough trials, find the failed
        episodes that used it and ask the DREAMER to propose 1-2 alternative
        strategies. These become candidate skills with the failed skill as
        parent — they will be tested and either promoted or retired by the
        usual fitness machinery.
        """
        weak: list[Skill] = []
        for s in self.skills.all():
            if s.status == "retired":
                continue
            if s.is_counterfactual:
                continue  # don't recurse on alternatives
            if s.trials < CONFIG.counterfactual_min_trials:
                continue
            if s.fitness_mean > CONFIG.counterfactual_max_fitness:
                continue
            weak.append(s)
        weak.sort(key=lambda x: x.fitness_mean)  # weakest first
        weak = weak[: CONFIG.counterfactual_per_cycle]
        if not weak:
            return 0
        emit("counterfactual_started", n_targets=len(weak))

        tokens = 0
        for skill in weak:
            failed = [
                ep for ep in self.memory.by_outcome("failure")
                if skill.id in ep.skills_used
            ]
            if not failed:
                continue
            try:
                alt, t = self._generate_counterfactual(skill, failed[0])
                tokens += t
                if alt is None:
                    continue
                if self._is_duplicate_skill(alt):
                    emit("counterfactual_skipped_duplicate",
                         from_skill=skill.id, alt_name=alt.name)
                    continue
                self.skills.store(alt)
                report.n_counterfactuals += 1
                emit("counterfactual_synthesized",
                     from_skill=skill.id, alt_skill=alt.id)
            except Exception:
                log.exception("counterfactual_failed", skill_id=skill.id)
        return tokens

    def _is_duplicate_skill(self, candidate: Skill) -> bool:
        """True if `candidate` is a near-duplicate of an existing non-retired skill.

        Done in two cheap passes: trivial name+trigger string equality first,
        then a single cosine similarity check against the most semantically-
        close existing skill (uses the SkillLibrary's index, not a full scan).
        """
        from . import embedding as emb_mod

        threshold = CONFIG.counterfactual_dedup_threshold
        norm_name = candidate.name.strip().lower()
        norm_trig = candidate.trigger.strip().lower()
        for s in self.skills.all():
            if s.status == "retired":
                continue
            if (s.name.strip().lower() == norm_name
                    and s.trigger.strip().lower() == norm_trig):
                return True
        # Embedding pass: retrieve the top-1 against the candidate's own
        # encoded trigger; if cosine ≥ threshold, treat as duplicate.
        query = f"{candidate.name}\n{candidate.trigger}"
        nearest = self.skills.retrieve(query, k=1)
        if not nearest:
            return False
        target = nearest[0]
        target_emb = (
            np.asarray(target.learned_embedding, dtype=np.float32)
            if target.learned_embedding is not None
            else emb_mod.encode(f"{target.name}\n{target.trigger}")
        )
        candidate_emb = emb_mod.encode(query)
        return emb_mod.cosine(candidate_emb, target_emb) >= threshold

    def _generate_counterfactual(
        self, failed_skill: Skill, failed_episode: Episode
    ) -> tuple[Skill | None, int]:
        resp = self.llm.complete(
            system=COUNTERFACTUAL_SYSTEM,
            messages=[{
                "role": "user",
                "content": COUNTERFACTUAL_USER_TEMPLATE.format(
                    skill=failed_skill.render(),
                    trajectory=failed_episode.trajectory_text(),
                    critique=failed_episode.critique or "(none)",
                ),
            }],
            temperature=CONFIG.llm_temperature_dreamer,
            model=resolve_model("dreamer"),
        )
        data = _extract_json(resp.text)
        if not data or "name" not in data or "body" not in data:
            return None, resp.total_tokens
        alt = Skill(
            name=data.get("name", "")[:80],
            trigger=data.get("trigger", failed_skill.trigger)[:300],
            body=data.get("body", "")[:2000],
            rationale=data.get("rationale", "")[:300],
            stage="rem",
            parent_skills=[failed_skill.id],
            provenance_episodes=[failed_episode.id],
            is_counterfactual=True,
        )
        return alt, resp.total_tokens

    # --- Stage 4c: Schema formation ----------------------------------------

    def _stage_schema(self, report: SleepReport) -> int:
        """Cluster semantically-close skills, write meta-skills as 'schemas'.

        A schema is a meta-skill whose body is a one-line rubric for picking
        among its children. Lineage edges (relation='specialises') connect
        the schema → each member skill, exposing the hierarchy in the lineage
        graph and the dashboard.
        """
        clusters = self.skills.cluster_by_embedding(
            threshold=CONFIG.schema_cluster_threshold,
            min_size=CONFIG.schema_min_cluster_size,
        )
        # Don't cluster schemas with each other — they are already abstract
        clusters = [
            [s for s in c if s.stage != "schema"] for c in clusters
        ]
        clusters = [c for c in clusters
                    if len(c) >= CONFIG.schema_min_cluster_size]
        if not clusters:
            return 0
        # Largest clusters first; cap per cycle
        clusters.sort(key=lambda c: -len(c))
        # Skip clusters already covered by an existing schema (avoids spending
        # a fresh LLM call to re-synthesise a meta-skill for the same set).
        if CONFIG.schema_skip_if_covered:
            clusters = [c for c in clusters if not self._cluster_already_covered(c)]
        clusters = clusters[: CONFIG.schema_max_per_cycle]
        if not clusters:
            return 0
        emit("schema_started", n_clusters=len(clusters))

        tokens = 0
        for cluster in clusters:
            try:
                schema, t = self._synthesize_schema(cluster)
                tokens += t
                if schema is None:
                    continue
                self.skills.store(schema)
                for child in cluster:
                    self.skills.add_lineage_edge(schema.id, child.id, "specialises")
                report.n_schemas += 1
                emit("schema_synthesized",
                     schema_id=schema.id, schema_name=schema.name,
                     n_children=len(cluster))
            except Exception:
                log.exception("schema_failed")
        return tokens

    def _cluster_already_covered(self, cluster: list[Skill]) -> bool:
        """True if some existing schema's `specialises` children form a
        superset of this cluster — meaning we already have a schema for it.
        """
        cluster_ids = {s.id for s in cluster}
        graph = self.skills.lineage_graph()
        for node, data in graph.nodes(data=True):
            if data.get("stage") != "schema" or data.get("status") == "retired":
                continue
            children = {
                v for u, v in graph.out_edges(node)
                if graph.edges[u, v].get("relation") == "specialises"
            }
            if cluster_ids.issubset(children):
                return True
        return False

    def _synthesize_schema(
        self, cluster: list[Skill]
    ) -> tuple[Skill | None, int]:
        rendered = "\n".join(
            f"- {s.name}: {s.trigger}" for s in cluster[:8]
        )
        resp = self.llm.complete(
            system=SCHEMA_SYSTEM,
            messages=[{
                "role": "user",
                "content": SCHEMA_USER_TEMPLATE.format(
                    n=len(cluster), skills=rendered,
                ),
            }],
            temperature=CONFIG.llm_temperature_dreamer,
            model=resolve_model("dreamer"),
        )
        text = resp.text.strip()
        if text.upper().startswith("REJECT"):
            return None, resp.total_tokens
        data = _extract_json(text)
        if not data or "name" not in data or "body" not in data:
            return None, resp.total_tokens
        schema = Skill(
            name=data.get("name", "")[:80],
            trigger=data.get("trigger", "")[:300],
            body=data.get("body", "")[:2000],
            rationale=data.get("rationale", "")[:300],
            stage="schema",
            provenance_episodes=list({eid for s in cluster
                                      for eid in s.provenance_episodes})[:50],
            status="candidate",
        )
        return schema, resp.total_tokens

    # --- Stage 4d: Self-suggested practice ---------------------------------

    def _stage_practice(self, report: SleepReport) -> int:
        """Write practice prompts for skills in the uncertain fitness zone.

        Surfaced in the dashboard so the user can launch them with one click
        — turns ambiguous skills into concrete, testable interactions.
        Distinct from counterfactual REM (which targets *failing* skills);
        practice targets the *unproven middle* (fitness 0.45–0.65).
        """
        targets: list[Skill] = []
        for s in self.skills.all():
            if s.status == "retired" or s.stage == "schema":
                continue
            if s.trials < CONFIG.practice_min_trials:
                continue
            f = s.fitness_mean
            if not (CONFIG.practice_min_fitness <= f <= CONFIG.practice_max_fitness):
                continue
            if s.practice_prompts:
                continue  # already has prompts; don't regenerate every cycle
            targets.append(s)
        # Order by Beta posterior VARIANCE (descending) — directly captures
        # 'how much do I still not know about this skill', strictly better
        # than abs(0.5 − mean) because it accounts for sample size:
        #   2/4 successes (mean 0.50, var 0.045) > 6/12 (mean 0.50, var 0.018).
        # Both have identical |0.5 − mean| but the smaller-N skill genuinely
        # benefits more from more trials.
        targets.sort(key=lambda x: -x.fitness_variance)
        targets = targets[: CONFIG.practice_max_skills_per_cycle]
        if not targets:
            return 0
        emit("practice_started", n_targets=len(targets))

        tokens = 0
        for skill in targets:
            try:
                prompts, t = self._write_practice_prompts(skill)
                tokens += t
                if not prompts:
                    continue
                skill.practice_prompts = prompts
                self.skills.store(skill)
                report.n_practice_prompts += len(prompts)
                emit("practice_synthesized",
                     skill_id=skill.id, n_prompts=len(prompts))
            except Exception:
                log.exception("practice_failed", skill_id=skill.id)
        return tokens

    def _write_practice_prompts(self, skill: Skill) -> tuple[list[str], int]:
        n = CONFIG.practice_n_prompts
        resp = self.llm.complete(
            system=PRACTICE_SYSTEM.replace("{n}", str(n)),
            messages=[{
                "role": "user",
                "content": PRACTICE_USER_TEMPLATE.format(
                    skill=skill.render(),
                    trials=skill.trials, successes=skill.successes,
                    fitness=skill.fitness_mean, n=n,
                ),
            }],
            temperature=CONFIG.llm_temperature_dreamer,
            model=resolve_model("dreamer"),
        )
        data = _extract_json(resp.text)
        if not data or not isinstance(data.get("prompts"), list):
            return [], resp.total_tokens
        prompts = [str(p)[:500] for p in data["prompts"] if p]
        # Keep at most n; non-empty
        return prompts[:n], resp.total_tokens

    # --- Spontaneous reactivation (no LLM) --------------------------------

    def _stage_spontaneous_reactivation(self, report: SleepReport) -> int:
        """Default-mode-network style: replay a few old skills to keep them fresh.

        Cognitive analogue (Born & Wilhelm 2012, Stickgold 2013): during
        rest the brain spontaneously reactivates memories that haven't
        been touched recently. This is the substrate of *spaced
        repetition* — old material gets enough exposure to resist
        decay even when the daily activity moves on to new tasks.

        Implementation:
          1. Pick `spontaneous_reactivation_n` non-retired skills whose
             last_used_at is older than `spontaneous_reactivation_min_age_s`.
          2. For each, push `last_used_at` forward by half the decay
             cutoff. This keeps decay_idle_embeddings from snapping the
             skill to its canonical anchor too aggressively.
          3. Emit a `skill_reactivated` event so observers (dashboard,
             logs) can see *which* skills were rehearsed in this cycle.

        No new schema field, no LLM call. Effect compounds across many
        sleep cycles: skills that the agent learned a month ago and
        hasn't used since stay retrievable. Caps at top-N per cycle so
        a huge library doesn't pay a linear scan.
        """
        n = int(getattr(CONFIG, "spontaneous_reactivation_n", 3))
        min_age = float(getattr(
            CONFIG, "spontaneous_reactivation_min_age_s", 7 * 24 * 3600.0,
        ))
        if n <= 0:
            return 0

        import time
        now = time.time()
        cutoff = now - min_age

        # Candidates: non-retired skills not used in `min_age` seconds.
        # We exclude `last_used_at == 0` (never touched after the field
        # shipped) to avoid reactivating skills that the agent never
        # picked up in the first place.
        candidates = [
            s for s in self.skills.all()
            if s.status != "retired"
            and 0 < s.last_used_at < cutoff
        ]
        if not candidates:
            emit("spontaneous_reactivation_skipped", reason="no_candidates")
            return 0

        # Fitness-weighted sample without replacement. Skills that have
        # demonstrated value (high fitness_mean) are more worth keeping
        # alive than rarely-successful ones. We add a small uniform
        # baseline (epsilon=0.05) so newer skills with thin Beta priors
        # still get an exploration chance — pure greedy-by-fitness would
        # never rehearse a skill until it's proven, defeating the point.
        k = min(n, len(candidates))
        weights = [max(0.05, c.fitness_mean) for c in candidates]
        # Sample without replacement, weighted. random.choices() samples
        # WITH replacement, so we draw one at a time and remove.
        chosen: list[Skill] = []
        pool = list(candidates)
        pool_w = list(weights)
        for _ in range(k):
            if not pool:
                break
            picked = self.rng.choices(pool, weights=pool_w, k=1)[0]
            idx = pool.index(picked)
            pool.pop(idx)
            pool_w.pop(idx)
            chosen.append(picked)

        # Half-life rescue: push last_used_at to (now - decay_cutoff/2).
        # The skill stays "old" enough to count as idle for retrieval
        # priority, but young enough that decay_idle_embeddings won't
        # touch it next cycle.
        decay_cutoff = float(getattr(
            CONFIG, "hebbian_decay_after_s", 14 * 24 * 3600.0,
        ))
        rescued_ts = now - decay_cutoff / 2.0

        for s in chosen:
            s.last_used_at = rescued_ts
            self.skills.store(s)
            # `name` is reserved by the emit signature — use skill_name
            # to surface it as a structured field.
            emit("skill_reactivated", skill_id=s.id, skill_name=s.name)

        emit("spontaneous_reactivation",
             n_candidates=len(candidates), n_chosen=k)
        return k

    # --- Stage 4.5: Episode decay (Ebbinghaus, no LLM) -------------------

    def _stage_episode_decay(self, report: SleepReport) -> None:
        """Prune episodes whose Ebbinghaus retention fell below threshold.

        FORGIA pezzo #9 — wires `EpisodicMemory.decay_prune` (pezzo #7)
        into the sleep cycle. Without this stage the primitive would
        sit unused; the corpus would grow monotonically as before.

        Capped by `episode_decay_max_per_cycle` so a degenerate cycle
        (e.g. first cycle after a long offline period with thousands
        of stale episodes) doesn't issue a single 10k-row delete.

        Honours `episode_decay_enabled` even when called directly so
        that a misconfigured run-time flag can't accidentally prune.
        """
        if not getattr(CONFIG, "episode_decay_enabled", False):
            report.n_episodes_decayed = 0
            return
        threshold = float(getattr(CONFIG, "episode_decay_threshold", 0.30))
        cap = int(getattr(CONFIG, "episode_decay_max_per_cycle", 200))
        deleted = self.memory.decay_prune(
            retention_threshold=threshold,
            limit=cap,
        )
        report.n_episodes_decayed = len(deleted)
        emit(
            "sleep_episode_decay",
            n_decayed=len(deleted), threshold=threshold, cap=cap,
        )

    # --- Stage 5: Pruning (no LLM) ----------------------------------------

    def _stage_tier2_triage(self, report: SleepReport, *, max_judged: int = 50) -> None:
        """Consolidation-time Tier-2 anti-confab triage: quarantine specific-unsourced
        coincidental-noise facts via the LLM judge. Capped at ``max_judged`` per cycle
        (future cycles handle the rest). Fail-safe: quarantine is reversible, errors skip,
        the judge can only LOWER trust. Opt-in (gated by the caller)."""
        from .tier2_judge import LLMJudge, triage_corpus
        res = triage_corpus(self.semantic, LLMJudge(self.llm), max_judged=max_judged)
        emit("sleep_tier2_triage",
             reviewed=res["reviewed"], declassed=res["declassed"])

    def _stage_pruning(self, report: SleepReport) -> None:
        promoted, retired = self.skills.promote_or_retire()
        report.promoted.extend(promoted)
        report.retired.extend(retired)
        # Gamba B qualità skill (2026-07-08): promote_or_retire salta le
        # candidate sotto min_trials — le mai-provate restavano attive per
        # sempre. Il sonno ritira anche le DORMIENTI (>30gg senza attività,
        # reversibile, cap 10/ciclo — stessa gradualità del cap merge).
        dormant = self.skills.retire_dormant_candidates()
        report.retired.extend(dormant)
        # Synaptic homeostasis: stale Hebbian drift snaps back toward the
        # canonical anchor so the embedding doesn't lock-in to a one-shot task
        # that no longer recurs.
        n_decayed = self.skills.decay_idle_embeddings()
        emit("pruning_done", promoted=len(promoted),
             retired=len(retired) + len(dormant),
             dormant_retired=len(dormant), hebbian_decayed=n_decayed)

    def _stage_bundle_discovery(
        self,
        report: SleepReport,
        *,
        min_count: int = 3,
        min_overlap: float = 0.6,
    ) -> None:
        """FORGIA pezzo #163: surface skill-bundle candidates on report.

        Pure data stage: no LLM calls. Future stages (#164+) consume
        `report.bundle_candidates` to nominate compound-macro skills.
        """
        pairs = self.memory.skill_bundle_candidates(
            min_count=min_count, min_overlap=min_overlap,
        )
        report.bundle_candidates.extend(pairs)
        report.n_bundles_proposed = len(report.bundle_candidates)
        emit(
            "bundle_discovery_done",
            n=report.n_bundles_proposed,
            min_count=min_count,
            min_overlap=min_overlap,
        )

    def _stage_crossover(
        self,
        report: SleepReport,
        *,
        n_pairs: int = 2,
        top_k: int = 5,
    ) -> None:
        """FORGIA pezzo #178: engram-crossover hybrid generation.

        Picks the top-`top_k` skills by fitness_mean, then samples
        `n_pairs` distinct (a, b) pairs and creates a hybrid skill
        for each via `crossover_skill_bodies`. Pure-arithmetic, zero
        LLM cost. Hybrids enter the standard fitness pipeline and
        either survive (high fitness on real tasks) or get retired.

        Inspired by REM dreaming as engram recombination, executed
        as Koza-style genetic programming on procedural skills.
        """
        from .skill_crossover import crossover_skill_bodies

        candidates = sorted(
            [s for s in self.skills.all() if s.status != "retired"
             and s.body.strip()],
            key=lambda s: -s.fitness_mean,
        )[:top_k]
        if len(candidates) < 2:
            return  # need at least 2 distinct parents
        emit("crossover_started", n_candidates=len(candidates),
             n_pairs=n_pairs)

        seen_pairs: set[tuple[str, str]] = set()
        attempts = 0
        max_attempts = n_pairs * 10
        while report.n_crossovers < n_pairs and attempts < max_attempts:
            attempts += 1
            a = self.rng.choice(candidates)
            b = self.rng.choice(candidates)
            if a.id == b.id:
                continue
            key = tuple(sorted([a.id, b.id]))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            child = crossover_skill_bodies(a, b, rng=self.rng)
            self.skills.store(child)
            report.n_crossovers += 1
        emit("crossover_done", n_hybrids=report.n_crossovers)

    def _stage_synaptic_tagging(
        self,
        report: SleepReport,
        *,
        window_s: float = 3600.0,
        salience_boost: float = 0.2,
    ) -> None:
        """FORGIA pezzo #175: synaptic-tag salience boost.

        For each ``(weak_id, strong_id)`` tuple from
        `memory.synaptic_tag_candidates`, increase the weak episode's
        ``salience_score`` by ``salience_boost`` (capped at 1.0). The
        existing salience-weighted-recall mechanism (Mattar-Daw 2018)
        will then prioritize these episodes during NREM replay.

        Mathematically equivalent to Frey & Morris's "synaptic tag
        capture": a weak event waits for a co-active strong event to
        rescue it from natural decay. Pure-arithmetic, zero LLM cost.
        """
        pairs = self.memory.synaptic_tag_candidates(window_s=window_s)
        boosted: set[str] = set()
        for weak_id, _strong_id in pairs:
            if weak_id in boosted:
                continue
            ep = self.memory.get(weak_id)
            if ep is None:
                continue
            new_salience = min(1.0, ep.salience_score + salience_boost)
            if self.memory.update_salience(weak_id, new_salience):
                boosted.add(weak_id)
                report.n_synaptic_tags += 1
        emit(
            "synaptic_tagging_done",
            n_tagged=report.n_synaptic_tags,
            window_s=window_s,
            salience_boost=salience_boost,
        )

    def _stage_negative_bundles(
        self,
        report: SleepReport,
        *,
        min_count: int = 3,
        min_fail_ratio: float = 0.7,
    ) -> None:
        """FORGIA pezzo #170: lateral inhibition tagging.

        Consume `memory.negative_bundle_candidates(...)` and mark each
        pair as mutual antagonists on the corresponding skills.
        Idempotent: if the link already exists, it is not duplicated.
        Skips silently when either skill is missing from the library.

        The retrieval pipeline (#171) will use these flags to penalize
        the joint selection of antagonist skills — implementing
        Földiák's anti-Hebbian inhibition between rival representations.
        """
        pairs = self.memory.negative_bundle_candidates(
            min_count=min_count, min_fail_ratio=min_fail_ratio,
        )
        for a_id, b_id, _count, _ratio in pairs:
            sa = self.skills.get(a_id)
            sb = self.skills.get(b_id)
            if sa is None or sb is None:
                continue
            changed = False
            if b_id not in sa.antagonists:
                sa.antagonists.append(b_id)
                changed = True
            if a_id not in sb.antagonists:
                sb.antagonists.append(a_id)
                changed = True
            if changed:
                self.skills.store(sa)
                self.skills.store(sb)
                report.n_antagonisms += 1
        emit(
            "negative_bundle_done",
            n_antagonisms=report.n_antagonisms,
            min_count=min_count,
            min_fail_ratio=min_fail_ratio,
        )

    def _stage_abstract_bundles(self, report: SleepReport) -> None:
        """FORGIA pezzo #165: synthesize compound-macro candidate skills.

        For each ``(a, b, count)`` in ``report.bundle_candidates``,
        compose a candidate skill named ``{name(a)}_then_{name(b)}``
        whose body concatenates the parent bodies. Pure-mechanical
        (no LLM): the new skill enters the standard fitness/trial
        pipeline as ``status="candidate"`` and gets its trial signal
        from real wake usage.

        Skips bundles where either parent skill is missing (e.g.
        retired in the same cycle), and skips when an identical
        macro (same `parent_skills` set) already exists.
        """
        from .skill import Skill as _Skill

        existing_pairs: set[tuple[str, ...]] = set()
        for s in self.skills.all():
            if len(s.parent_skills) == 2:
                existing_pairs.add(tuple(sorted(s.parent_skills)))

        for a_id, b_id, _count in report.bundle_candidates:
            sa = self.skills.get(a_id)
            sb = self.skills.get(b_id)
            if sa is None or sb is None:
                continue
            key = tuple(sorted([a_id, b_id]))
            if key in existing_pairs:
                continue
            macro = _Skill(
                name=f"{sa.name}_then_{sb.name}",
                trigger=f"{sa.trigger} ; {sb.trigger}",
                body=f"{sa.body}\n{sb.body}",
                rationale=(
                    f"Synthesized from bundle ({sa.name}, {sb.name}) "
                    f"with count={_count}."
                ),
                status="candidate",
                stage="nrem",
                parent_skills=[a_id, b_id],
            )
            self.skills.store(macro)
            existing_pairs.add(key)
            report.n_bundle_skills += 1
        emit(
            "bundle_abstraction_done",
            n_skills=report.n_bundle_skills,
            n_bundles_in=len(report.bundle_candidates),
        )
