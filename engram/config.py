"""Configuration: paths, models, hyper-parameters.

Single source of truth — every other module reads from CONFIG.
Hyper-parameters are intentionally explicit and explained: this is a
research prototype, every knob should be reproducible.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_LOG = logging.getLogger("engram.config")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _data_root() -> Path:
    """Resolve the data root from env, else the shared ``~/.engram`` resolver.

    Precedence: ``HIPPO_DATA_DIR`` → ``ENGRAM_DATA_DIR`` env (test isolation /
    multi-tenant / subprocess) → otherwise :func:`engram._compat.data_dir`
    (``~/.engram``). Read at CONFIG-construction time; once CONFIG is built the
    path is frozen.

    Audit A6 (2026-06-08): the old no-env default was ``<project>/data``, which
    on a non-editable ``pip install`` lives INSIDE site-packages (wiped on
    upgrade, frequently read-only) AND disagreed with the ``~/.engram`` path the
    dashboard/auth resolver uses — a silent split-brain / data-loss on the
    canonical first-run path. Delegating the no-env case to ``_compat.data_dir``
    fixes that; we also now honor ``ENGRAM_DATA_DIR`` (the name the README
    ``.mcp.json`` sets) as a fallback.

    ``HIPPO_DATA_DIR`` is checked FIRST (not ENGRAM_DATA_DIR) deliberately: it is
    the long-standing test-isolation handle (conftest + many subprocess tests set
    only it and expect it to win), and a machine whose shell exports
    ``ENGRAM_DATA_DIR`` (the maintainer's → ~/.engram) must not override a test's
    explicit ``HIPPO_DATA_DIR``.
    """
    env = (
        os.environ.get("HIPPO_DATA_DIR")
        or os.environ.get("ENGRAM_DATA_DIR")
        or ""
    ).strip()
    if env:
        return Path(env).expanduser().resolve()
    from ._compat import data_dir as _compat_data_dir
    return _compat_data_dir()


#: Modello LEGACY (storico, MiniLM 384). FROZEN — e' cosa SONO le righe con
#: ``embedding_model`` NULL (prodotte pre-v9). NON cambia mai: e' il fallback
#: COALESCE per i NULL in ``engram.semantic._LEGACY_EMBEDDING_MODEL``.
_LEGACY_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
#: Modello ATTIVO di DEFAULT. GO-LIVE e5 2026-06-04: e5-base 768d (MRR 0.466->0.710
#: +52% MISURATO e2e su copia via path reale as_passage store / as_query recall).
#: Override via env HIPPO_EMBEDDING_MODEL. DECOUPLED da _LEGACY (MiniLM): le righe
#: NULL/legacy restano MiniLM ed escono dal recall sotto e5 (anti cross-spazio),
#: re-embeddate da scripts/flip_e5.py. Prefissi e5 query/passage via
#: embedding.as_query/as_passage (model-gated). Test PINNATI a multilingue-L12/384 in
#: tests/conftest.py (stub 384d) -> suite invariata (server=e5/768, test=L12/384).
_DEFAULT_EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"

#: Output dimension of known sentence-transformer encoders. F6 (bug-hunt
#: 2026-06-13): embedding_model and embedding_dim are independent env vars, so
#: pointing HIPPO_EMBEDDING_MODEL at a model whose dim != the 768 default while
#: leaving HIPPO_EMBEDDING_DIM unset silently blanks ALL semantic recall (every
#: vector is the wrong byte-length and is dropped by the recall length-filter,
#: with no error). __post_init__ derives the dim from this table so a model
#: swap "just works"; an unknown model or an explicit-but-mismatched dim only
#: warns (the operator stays in control). Add models here as they are adopted.
_KNOWN_MODEL_DIMS: dict[str, int] = {
    "intfloat/multilingual-e5-base": 768,
    "intfloat/multilingual-e5-small": 384,
    "intfloat/multilingual-e5-large": 1024,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
}


def _load_env() -> None:
    """Load env vars from candidate .env files.

    Override empty values: shells sometimes export empty vars from earlier
    sourced .envs, blocking load_dotenv with override=False.
    """
    candidates = [
        _project_root() / ".env",
    ]
    # Strip empty critical vars so dotenv can fill them
    for k in ("ANTHROPIC_API_KEY",):
        if k in os.environ and not os.environ[k]:
            del os.environ[k]
    for p in candidates:
        if p.exists():
            load_dotenv(p, override=False)


_load_env()


@dataclass(frozen=True)
class Config:
    # ----- Paths -----
    # `data_dir` honours HIPPO_DATA_DIR for test isolation / multi-tenant
    # deployment. Every other data path derives from it so changing the
    # root in one place re-homes the entire data tree.
    project_root: Path = field(default_factory=_project_root)
    data_dir: Path = field(default_factory=_data_root)
    episodes_db: Path = field(
        default_factory=lambda: _data_root() / "episodes" / "episodes.db"
    )
    skills_dir: Path = field(default_factory=lambda: _data_root() / "skills")
    skills_db: Path = field(
        default_factory=lambda: _data_root() / "skills" / "skills_index.db"
    )
    semantic_db: Path = field(
        default_factory=lambda: _data_root() / "semantic" / "semantic.db"
    )
    runs_dir: Path = field(default_factory=lambda: _data_root() / "runs")
    reports_dir: Path = field(default_factory=lambda: _data_root() / "reports")

    # ----- LLM -----
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model_executor: str = "claude-haiku-4-5-20251001"  # cheap, fast, used for ReAct loop
    # CYCLE #40 — direttiva Aurelio 2026-05-13 (fact c365fec4b42e, preferences/aurelio):
    # default modello dreamer/critic = Claude Opus 4.7 (1M context).
    # Sonnet valido solo se esplicitamente richiesto dall'utente.
    model_dreamer: str = "claude-opus-4-7"  # smarter, used for skill synthesis
    model_critic: str = "claude-haiku-4-5-20251001"
    # Behind-flag encoder upgrade (2026-06-03, additive+reversible). The
    # encoder is env-overridable via HIPPO_EMBEDDING_MODEL / HIPPO_EMBEDDING_DIM
    # so a modern model can be loaded for evaluation WITHOUT touching the
    # default. Env UNSET -> exact legacy values (MiniLM 384) -> zero change
    # to recall. The live re-embed + default switch are a SEPARATE mandate
    # (gated): this only enables loading a different encoder in a fresh DB.
    embedding_model: str = field(
        default_factory=lambda: os.environ.get(
            "HIPPO_EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL
        )
    )
    # Dim of `embedding_model` vectors. Stable contract: if you swap the
    # encoder, also bump CONFIG.dg_seed so old DG-encoded embeddings are
    # re-projected (otherwise stored DG vectors mismatch the new W_dg).
    # NB: the live recall byte-filter (semantic.py _EXPECTED_EMBEDDING_BYTES)
    # is WIRED LIVE to this value (harden 2026-06-07, PEP 562 __getattr__):
    # it reads CONFIG.embedding_dim * 4 on every access, so changing the dim
    # moves the length-guard with it. Cross-dim writes are still filtered out
    # (not poisoned) by both the length-guard AND the per-row embedding_model
    # isolation, so old-dim corpora stay safely excluded after a switch.
    #: True when embedding_dim is an ASSUMPTION (unknown model, no pinned env):
    #: the embedding loader adopts the model's real dim at first load (iter 31 —
    #: kills the silent-empty-recall trap on custom models). Never True for a
    #: known-table model or a pinned HIPPO_EMBEDDING_DIM.
    embedding_dim_assumed: bool = False
    embedding_dim: int = field(
        default_factory=lambda: int(os.environ.get("HIPPO_EMBEDDING_DIM", "768"))
    )

    llm_temperature_executor: float = 0.0  # deterministic execution
    llm_temperature_dreamer: float = 0.7  # creative recombination (REM-like)
    llm_temperature_critic: float = 0.2
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("HIPPO_LLM_MAX_TOKENS", "2048"))
    )
    llm_max_retries: int = 3
    llm_retry_backoff: float = 2.0

    # ----- Wake cycle -----
    wake_max_steps: int = field(
        default_factory=lambda: int(os.environ.get("HIPPO_WAKE_MAX_STEPS", "8"))
    )
    wake_skills_top_k: int = 3  # how many skills to inject
    # Bayesian skill selection — pool size for Thompson-sampled re-rank.
    # Cosine retrieves a wide pool first (cheap), `selection.consider_skills`
    # then re-ranks combining relevance + Beta-posterior fitness. The pool
    # MUST be larger than top_k or the re-rank degenerates to a no-op.
    wake_skills_pool_size: int = 16
    wake_episodes_recall_k: int = 2  # past episodes to inject as few-shot
    wake_self_critique: bool = True  # enable Reflexion-style critique on failure
    wake_critique_retries: int = 1  # retries after critique

    # ----- Sleep cycle -----
    sleep_min_episodes: int = 2  # don't run sleep below this threshold
    sleep_nrem_cluster_min_size: int = 1  # min episodes per cluster for synthesis
    sleep_nrem_max_clusters: int = 6
    sleep_nrem_cluster_threshold: float = 0.40  # cosine threshold (lower = more clustering)
    sleep_rem_recombinations: int = 2  # how many REM hybrids to attempt
    sleep_rem_min_promoted: int = 2  # need ≥N promoted skills to attempt REM
    sleep_replay_priority_failure: float = 0.6  # priority weight for failures
    sleep_replay_priority_recent: float = 0.3
    sleep_replay_priority_diverse: float = 0.1
    # Salience by surprise (Buzsáki 2015): episodes whose step-count
    # deviates strongly from the skill's average get a replay boost.
    # Defaults to 0 (off) so the existing three-weight blend remains the
    # baseline. Setting to ~0.2 gives surprise comparable weight to
    # recency without crowding out failure priority.
    sleep_replay_priority_surprise: float = 0.0
    # FORGIA pezzo #19 — salience_score (cached per-episode by
    # `compute_salience` since pezzo #6, Buzsáki 2015 prediction-error
    # surprise) as a continuous signal in replay priority. Generalises
    # the binary `priority_failure` flag: a banal success gets near 0,
    # a surprising failure gets near 1, a surprising success scores
    # in between. Default 0.0 keeps legacy behaviour; flip to ~0.3 to
    # have salience contribute as much as recency.
    sleep_replay_priority_salience: float = 0.0
    # Episode decay (FORGIA pezzo #9 — cabling pezzo #7 in sleep cycle).
    # During sleep, episodes whose Ebbinghaus retention falls below
    # `episode_decay_threshold` are pruned (CASCADE on traces). The cap
    # protects against unbounded delete in extreme cycles.
    episode_decay_enabled: bool = True
    episode_decay_threshold: float = 0.30
    episode_decay_max_per_cycle: int = 200

    # ----- Dentate Gyrus pattern separation (FORGIA pezzo #11 + #13) -----
    # k-WTA on a high-dim random projection — `dg_encode` separates near-
    # duplicate summary embeddings so cosine top-k surfaces a richer mix
    # of clusters instead of 5 carbon copies. Schema v3 stores the sparse
    # DG vector alongside `summary_embedding`. The seed is FIXED — never
    # change it without a re-encode pass, otherwise old DG vectors stop
    # matching the new W_dg projection.
    dg_d_expand: int = 8192  # ~21× expansion (cf. biological 1M/100k = 10×)
    dg_k_sparse: int = 80    # ~1% sparsity, matches biological granule firing rate
    dg_seed: int = 0xDA1A  # arbitrary fixed value; persistence contract
    # `recall(use_dg=True)` opt-in: caller decides per-call. The default
    # remains cosine-on-summary (legacy behaviour) so existing tests and
    # benchmarks are unaffected. Wake-loop cabling is a follow-up pezzo.
    dg_recall_default: bool = False
    # FORGIA pezzo #16 — wake `_retrieve_episodes` opt-in for DG ranking.
    # When True, near-duplicate past episodes get diversified at retrieval
    # time so the prompt's few-shot block surfaces a richer mix of
    # clusters. Default False to preserve existing test snapshots and
    # the prompt content currently expected by the LLM.
    wake_recall_use_dg: bool = False

    # ----- TCM contextual reinstatement (FORGIA pezzo #12 + #14 + #15) ---
    # Wake-loop cabling: when True, every wake.run() instantiates a
    # ContextEngine seeded with the task_text embedding, observes each
    # tool-result observation embedding, and snapshots the context state
    # on episode store. Enables Tulving (1973) encoding-specificity at
    # recall time — `recall(context_emb=cur_ctx, context_weight=β)` boosts
    # episodes encoded in similar contexts.
    tcm_wake_enabled: bool = True
    tcm_rho: float = 0.85  # ContextEngine persistence (Howard & Kahana 2002)
    # `recall(context_weight=β)` for the wake-side episode injection. 0.0
    # keeps legacy (cosine + salience + recency only). A small positive
    # boost (~0.20) gives Tulving's specificity weight comparable to
    # recency without crowding out cosine relevance.
    tcm_recall_context_weight: float = 0.20
    # FORGIA pezzo #17 — cross-session ContextEngine in WakeAgent.
    # When True, WakeAgent maintains a stateful ContextEngine that
    # drifts across run() calls (the "agent's current cognitive state"
    # in TCM terms — Howard & Kahana 2002 cross-list dynamics).
    # `_retrieve_episodes` uses this state as the context cue for
    # `recall(context_emb=cur_ctx, context_weight=...)` so episodes
    # encoded under similar recent contexts get a boost. Default True
    # because the cabling is no-op when context_weight=0.0.
    tcm_cross_session_enabled: bool = True

    # ----- Skill fitness (Bayesian Beta-Binomial) -----
    fitness_prior_alpha: float = 1.0  # Beta prior: 1,1 = uniform
    fitness_prior_beta: float = 1.0
    fitness_promote_threshold: float = 0.6  # posterior mean to promote
    fitness_retire_threshold: float = 0.25
    fitness_min_trials: int = 3
    fitness_merge_similarity: float = 0.92  # cosine threshold for skill dedup

    # Wake-time episode retrieval: drop episodes whose cosine similarity
    # to the current task falls below this floor. 0.0 = legacy behaviour
    # (return top-k regardless of relevance). 0.30 is a conservative
    # value that drops obviously-irrelevant matches while keeping
    # paraphrases. Worth raising to ~0.50 for high-volume single-domain
    # use; left at 0.0 for now to preserve existing test snapshots.
    wake_episodes_min_similarity: float = 0.0
    # FORGIA pezzo #18 — cabling salience + recency into wake retrieve.
    # `recall()` already accepts these via kwargs but the wake site never
    # set them. Now opt-in via CONFIG so the same `_retrieve_episodes`
    # path can pull a boosted top-k. Defaults are conservative (0.0)
    # to preserve test snapshots; flip to ~0.20 for production.
    wake_salience_weight: float = 0.0
    wake_recency_weight: float = 0.0
    wake_recency_tau_s: float = 7 * 86400.0  # 7 days

    # ----- Hebbian skill embedding (cells that fire together wire together) -----
    # On success, the skill's trigger embedding is lerp'd toward the task
    # embedding — making the skill MORE retrievable for similar future tasks.
    hebbian_alpha: float = 0.05  # lerp factor; small to avoid drift
    hebbian_min_norm: float = 0.5  # safety: don't update if task embedding is degenerate
    # Temporal decay: skills that haven't been used for a while drift back
    # toward their canonical name+trigger embedding (synaptic homeostasis).
    # This prevents stale Hebbian "lock-in" on tasks that no longer recur.
    hebbian_decay_enabled: bool = True
    hebbian_decay_after_s: float = 14 * 24 * 3600.0  # 14 days idle → start decaying
    hebbian_decay_rate: float = 0.10  # per cycle when idle, lerp back to canonical
    hebbian_decay_max_per_cycle: int = 50  # cap LLM-free work per sleep run

    # Spontaneous reactivation (Born & Wilhelm 2012, Stickgold 2013): a
    # default-mode rehearsal stage during sleep that touches a few stale
    # skills to prevent them from drifting into the decay/retirement
    # cliff. No LLM cost. Disabled by default — the effect is meaningful
    # only after weeks of usage, and operators should observe natural
    # decay before opting in.
    spontaneous_reactivation_enabled: bool = False
    spontaneous_reactivation_n: int = 3  # skills touched per cycle
    spontaneous_reactivation_min_age_s: float = 7 * 24 * 3600.0

    # FORGIA pezzo #164: bundle discovery stage. When enabled, the
    # sleep cycle scans `memory.skill_bundle_candidates(...)` and
    # surfaces the result on `SleepReport.bundle_candidates`. Pure
    # data, zero LLM cost. Default off until #165+ wires the
    # downstream macro-abstraction stage that consumes the candidates.
    bundle_discovery_enabled: bool = False
    bundle_discovery_min_count: int = 3
    bundle_discovery_min_overlap: float = 0.6

    # FORGIA pezzo #171: retrieval-time lateral inhibition. When enabled,
    # the wake-time selection greedily skips skills whose antagonist list
    # intersects the already-selected set. The antagonists are populated
    # by sleep stage #170 from `negative_bundle_candidates`. Default off
    # until the bench confirms a measurable accuracy uplift.
    retrieval_inhibition_enabled: bool = False
    # FORGIA pezzo #172: opt-in flag for the negative-bundle sleep stage.
    negative_bundle_enabled: bool = False
    negative_bundle_min_count: int = 3
    negative_bundle_min_fail_ratio: float = 0.7
    # FORGIA pezzo #175: synaptic tagging (Frey & Morris 1997). When
    # enabled, the sleep cycle boosts the salience of failure
    # episodes that were followed by a success on a shared skill
    # within `synaptic_tag_window_s`.
    synaptic_tagging_enabled: bool = False
    synaptic_tag_window_s: float = 3600.0
    synaptic_tag_salience_boost: float = 0.2

    # FORGIA pezzo #178: engram-crossover sleep stage. When enabled,
    # sleep generates `crossover_n_pairs` hybrid skills from the
    # top-`crossover_top_k` skills by fitness via single-point
    # crossover. Zero LLM cost.
    crossover_enabled: bool = False
    crossover_n_pairs: int = 2
    crossover_top_k: int = 5

    # Anti-Hebbian / lateral inhibition (Földiák 1990): when a winning skill
    # consolidates on a task, its rival skills (same cluster, similar trigger
    # embedding) are gently pushed AWAY from that task embedding. Net effect:
    # skill manifolds differentiate over time, the basins of attraction
    # sharpen, retrieval becomes more discriminative. Disabled by default
    # because the effect compounds slowly and we want operators to opt in
    # consciously after observing baseline behaviour.
    lateral_inhibition_enabled: bool = False
    # Cosine threshold above which two skills are considered rivals. Only
    # the top-K rivals (by similarity) are inhibited per success event.
    lateral_inhibition_min_similarity: float = 0.80
    lateral_inhibition_top_k: int = 5
    # Anti-Hebbian alpha. Smaller than the Hebbian alpha because the
    # rival-update is per-event and unbounded (every success triggers it),
    # while Hebbian updates a single skill per success.
    lateral_inhibition_alpha: float = 0.02

    # ----- Procedural compilation (skill → deterministic macro) -----
    # When a skill has been applied successfully many times, distil its
    # trace into a parameterised macro that bypasses the LLM. Compilation
    # itself is LLM-driven (during sleep) but execution is pure code.
    compile_min_successes: int = 5  # need this many successes to attempt
    compile_min_fitness: float = 0.80  # posterior mean ≥
    compile_max_per_cycle: int = 3  # cap per sleep cycle (LLM cost)
    compile_apply_min_similarity: float = 0.72  # task↔skill similarity to fire macro
    compile_apply_min_fitness: float = 0.80  # legacy gate on Beta posterior MEAN
    # Bayesian gate (FORGIA pezzo #4): when True, the macro fast-path uses the
    # 5%-quantile of the Beta posterior (`fitness_lower_bound`) instead of the
    # mean. This makes the gate "we are confident the skill works" rather than
    # "the skill probably works" — meaningful when trials are few.
    #
    # Threshold tuning: a skill with trials=20 successes=18 has mean 0.86 and
    # lower_bound ~0.74 → passes both 0.80 (legacy) and 0.65 (lower_bound).
    # A skill with trials=3 successes=3 has mean 0.80 and lower_bound ~0.47
    # → passes legacy 0.80 but is correctly REJECTED by lower_bound 0.65,
    # matching the intuition that "3/3 successes is not enough evidence to
    # bypass the LLM with a deterministic macro".
    compile_apply_use_lower_bound: bool = True
    compile_apply_min_lower_bound: float = 0.65
    # Adaptive fast-path: high-confidence macros (compiled with strong agreement
    # across past traces) get a permitted similarity drop. The effective
    # threshold is `compile_apply_min_similarity − k * (macro.confidence − 0.5)`,
    # clamped to compile_apply_floor_similarity. This lets fragile models reuse
    # their own well-tested macros even when wording shifts.
    compile_adaptive_enabled: bool = True
    compile_adaptive_k: float = 0.3  # per unit of confidence above 0.5
    compile_apply_floor_similarity: float = 0.55  # never go below this

    # ----- Forward replay (predict before act) -----
    # Hippocampal forward sweeps: simulate the most likely action chain BEFORE
    # the wake loop, anchor reasoning, detect divergence as learning signal.
    forward_replay_enabled: bool = True
    forward_replay_min_fitness: float = 0.5  # legacy: gate on Beta posterior MEAN
    # Bayesian gate (FORGIA pezzo #4): same rationale as `compile_apply_*` —
    # use lower_bound so we don't anchor the LLM with a "predicted path" from
    # a skill we aren't yet confident in. Forward replay is informational
    # (no fast-path), so the cost of pessimism is lower than the macro path,
    # hence a lower threshold (~0.30 vs 0.65 for macro).
    forward_replay_use_lower_bound: bool = True
    forward_replay_min_lower_bound: float = 0.30
    forward_replay_min_episodes: int = 1  # need ≥N past successful episodes for the skill
    # Edge-case replay: also surface the actions of recent FAILED attempts so
    # the model learns from its own mistakes, not just successes. Hippocampal
    # studies (Buzsáki 2015, Singer & Frank 2009) show replay disproportionately
    # encodes salient/aversive trajectories — same idea here.
    forward_replay_include_failures: bool = True
    forward_replay_max_failure_actions: int = 4  # cap to keep prompt tight

    # Reverse-replay / trace alignment: when both a failure AND a successful
    # twin episode are available for the same skill, align them step-by-step
    # on observation embeddings (not actions) and surface the *exact*
    # divergence step in the prompt. Takes the place of the bare avoid-path
    # block when it produces a result. Pure numpy + cached embeddings; no
    # LLM call. See engram.trace_alignment.
    trace_alignment_enabled: bool = True
    # Cosine threshold above which two observations are considered "the
    # same situation" for the purpose of attributing an action mismatch.
    # Tuned conservatively for sentence-transformers/all-MiniLM-L6-v2:
    # paraphrases of the same observation typically score 0.55-0.85,
    # unrelated text below 0.2. Lowering this makes the detector report
    # more divergences (more recall, more false positives).
    trace_alignment_obs_threshold: float = 0.55

    # ----- Counterfactual REM -----
    # When a skill fails, the dreamer generates 1-2 alternative strategies
    # ("what if I had done X instead?") and stores them as candidate skills.
    counterfactual_enabled: bool = True
    counterfactual_min_trials: int = 3
    counterfactual_max_fitness: float = 0.5
    counterfactual_per_cycle: int = 2  # cap per sleep cycle
    # Pre-store dedup: drop counterfactual candidates that are near-duplicates
    # of an existing non-retired skill. Stops the library from filling up with
    # 10 similar variants of the same alternative strategy.
    counterfactual_dedup_threshold: float = 0.90  # cosine over name+trigger

    # ----- Schema formation (skill cluster → meta-skill) -----
    # Tulving's hierarchy: episodic → semantic. Skills that share a domain
    # get a SCHEMA parent — an abstraction that helps the agent navigate
    # large libraries by topic before diving into specifics.
    schema_enabled: bool = True
    schema_cluster_threshold: float = 0.62  # cosine on trigger embeddings
    schema_min_cluster_size: int = 3
    schema_max_per_cycle: int = 2
    # Idempotency: skip clusters that are already covered by an existing schema
    # whose `specialises` lineage matches the cluster's member-id set. Saves
    # one LLM call per untouched cluster per sleep cycle (the main cost
    # contributor for repeat sleeps).
    schema_skip_if_covered: bool = True

    # ----- Self-suggested practice (sleep dream-tasks) -----
    # During NREM the dreamer writes 2-3 practice prompts for each skill in
    # the "uncertain" fitness zone (between counterfactual_max and promote
    # thresholds). Surfaced in the dashboard's skill detail; the user can
    # run them with one click to gather real fitness signal.
    practice_enabled: bool = True
    practice_min_fitness: float = 0.45  # only skills above this get practice
    practice_max_fitness: float = 0.65  # …and below this (avoid promoted)
    practice_min_trials: int = 1
    practice_n_prompts: int = 2  # how many prompts to write per skill
    practice_max_skills_per_cycle: int = 4  # cap LLM cost

    # ----- Working memory pruning (7th mechanism) -----
    # Cortical PFC keeps only task-relevant items in working memory; very long
    # contexts make small models hallucinate. We compress mid-trajectory tool
    # observations (oldest first) once an episode's running message-list size
    # exceeds the budget.
    working_memory_pruning_enabled: bool = True
    # Char budget for the live tool-loop messages (rough proxy for tokens).
    # Defaults conservative for 32k-token models (Qwen 7B). Customise per provider.
    working_memory_max_chars: int = 24000
    # Always keep this many trailing observations un-pruned (recency anchor).
    working_memory_keep_tail: int = 3
    # Truncated observations are replaced with this short marker (preserves
    # message structure so providers' tool-result schemas still validate).
    working_memory_pruned_placeholder: str = "[observation pruned to free working memory]"

    # ----- Sandbox -----
    sandbox_timeout_s: float = 5.0
    sandbox_max_output_chars: int = 4096

    # ----- Dashboard -----
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765

    # ----- Reproducibility -----
    seed: int = 42

    def __post_init__(self) -> None:
        # F6 (bug-hunt 2026-06-13): keep embedding_dim consistent with
        # embedding_model. The two are independent env vars; a model swap that
        # forgets HIPPO_EMBEDDING_DIM otherwise leaves the dim at 768 and every
        # vector is silently dropped by the recall length-filter (a total recall
        # blackout, no error). Derive the dim from the known model UNLESS the
        # operator pinned HIPPO_EMBEDDING_DIM explicitly; warn on any mismatch
        # we can't safely auto-correct. frozen dataclass -> object.__setattr__.
        known = _KNOWN_MODEL_DIMS.get(self.embedding_model)
        dim_pinned = "HIPPO_EMBEDDING_DIM" in os.environ
        if known is not None and known != self.embedding_dim:
            if dim_pinned:
                _LOG.warning(
                    "embedding_dim=%d was pinned via HIPPO_EMBEDDING_DIM but "
                    "model %r is %d-dim — semantic recall will return EMPTY "
                    "(every stored vector is the wrong byte-length and is "
                    "filtered out). Unset HIPPO_EMBEDDING_DIM or set it to %d.",
                    self.embedding_dim, self.embedding_model, known, known,
                )
            else:
                _LOG.warning(
                    "embedding_dim auto-derived %d -> %d from model %r "
                    "(HIPPO_EMBEDDING_DIM was unset). Set it explicitly to "
                    "silence this.",
                    self.embedding_dim, known, self.embedding_model,
                )
                object.__setattr__(self, "embedding_dim", known)
        elif known is None and not dim_pinned and (
            self.embedding_model != _DEFAULT_EMBEDDING_MODEL
        ):
            _LOG.warning(
                "embedding_model=%r is not in the known-dim table and "
                "HIPPO_EMBEDDING_DIM is unset; assuming %d until first model "
                "load, then adopting the model's true dimension automatically. "
                "Pin HIPPO_EMBEDDING_DIM to silence this.",
                self.embedding_model, self.embedding_dim,
            )
            # iter 31: mark it so the embedding loader can adopt the true dim
            # at first load instead of leaving recall silently empty.
            object.__setattr__(self, "embedding_dim_assumed", True)

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir,
            self.episodes_db.parent,
            self.skills_dir,
            self.semantic_db.parent,
            self.runs_dir,
            self.reports_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)


CONFIG = Config()
CONFIG.ensure_dirs()
