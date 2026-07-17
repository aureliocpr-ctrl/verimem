"""Auto-Dream worker — run as a detached subprocess from SessionStart.

Cycle #69 (2026-05-14). Designed to be spawned via:

    python -m verimem.auto_dream_worker

The hook decides *whether* to spawn (env-gate + corpus-size check
via lightweight SQLite read). If the hook spawns this worker, the
worker:

  1. Re-runs `maybe_trigger_dream` (so the *full* decision logic
     applies, not just the hook's pre-filter).
  2. If conditions still hold, calls `propose_dream_tasks` on the
     live engram dir to produce a shadow + pending_tasks artifact.
  3. Writes a brief status JSON to ~/.engram/auto_dream_last.json
     for observability.

The worker is intentionally side-effect-light on the live DBs:
`propose_dream_tasks` (cycle #34/#35) only *snapshots* live data
into a shadow root; it does NOT mutate live.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def _resolve_engram_dir() -> Path:
    cand = os.environ.get("ENGRAM_DATA_DIR") or os.environ.get("HIPPO_DATA_DIR")
    if cand:
        return Path(cand)
    return Path.home() / ".engram"


def _live_dirs_from(engram_dir: Path) -> dict[str, Any]:
    """Build the `live_dirs` dict that `propose_dream_tasks` expects.

    Cycle 216 (2026-05-23): prefer canonical ``semantic/semantic.db`` over
    flat legacy ``semantic.db``. Empirical evidence on the running engram
    dir (~/.engram): the flat file existed but was empty (36864 B, 0 facts)
    while the nested file held the real corpus (1707 facts, 7.4 MB) — the
    old "flat-if-exists else nested" branch silently routed Auto-Dream to
    the empty DB, defeating the cycle 187/211/212 community + thompson
    seeds that depend on a real corpus.
    """
    nested = engram_dir / "semantic" / "semantic.db"
    flat = engram_dir / "semantic.db"
    if nested.exists():
        semantic_db = nested
    elif flat.exists():
        semantic_db = flat
    else:
        # Neither exists; return the canonical location (callers handle
        # the empty-corpus case gracefully — see propose_dream_tasks).
        semantic_db = nested
    return {
        "skills_db": engram_dir / "skills" / "skills_index.db",
        "skills_dir_path": engram_dir / "skills",
        "episodes_db": engram_dir / "episodes" / "episodes.db",
        "semantic_db": semantic_db,
    }


def _prune_old_dreams(engram_dir: Path, keep: int = 3) -> dict[str, Any]:
    """Retention for Auto-Dream shadow snapshots.

    Each dream firing snapshots the full live DB into
    ``<engram_dir>/dreams/auto-<ts>/``. Without pruning these accumulate
    without bound — observed 2026-06-01: 346 stale shadow dirs = ~7.9 GB.
    Keep only the ``keep`` most-recent ``auto-*`` dirs, delete the rest.
    NEVER touches non-``auto-`` dirs (e.g. manual dreams) or the live DB.
    Defensive: never raises (maintenance/observability, not critical path).
    """
    import shutil

    dreams = engram_dir / "dreams"
    if not dreams.is_dir():
        return {"pruned": 0, "kept": 0}
    try:
        autos = [
            d for d in dreams.iterdir()
            if d.is_dir() and d.name.startswith("auto-")
        ]
    except Exception:  # noqa: BLE001
        return {"pruned": 0, "kept": 0}
    keep = max(0, int(keep))
    autos.sort(key=lambda d: d.stat().st_mtime, reverse=True)  # newest first
    pruned = 0
    for d in autos[keep:]:
        try:
            shutil.rmtree(d)
            pruned += 1
        except Exception:  # noqa: BLE001
            pass
    return {"pruned": pruned, "kept": min(len(autos), keep)}


def _persist_emergence_drafts(
    *,
    engram_dir: Path,
    max_n: int = 3,
    min_community_size: int = 4,
    min_topic_purity: float = 0.5,
    min_cohesion: float = 0.3,
    enable_stable_partition: bool = False,
    enable_hybrid: bool = False,
) -> dict[str, Any]:
    """Cycle 223 — write the current emergence drafts to disk for audit.

    Composes cycle 213 detect + cycle 217 draft + cycle 222 persist
    in a single helper, used by ``_propose_via_engram`` so every
    Auto-Dream firing leaves a tangible audit trail under
    ``<engram_dir>/skill_drafts/<YYYYMMDD-HHMMSS>/``.

    Returns ``{"n_written": int, ...}`` (the persist_drafts shape) or
    ``{"n_written": 0}`` on any failure mode (missing DB, no
    candidates, persist error). Never raises.
    """
    from verimem.skill_draft_persist import persist_drafts
    from verimem.skill_drafter import draft_skill_from_community
    from verimem.skill_emergence_detector import detect_emerging_skills

    live_dirs = _live_dirs_from(engram_dir)
    db_path = live_dirs["semantic_db"]
    if not Path(db_path).exists():
        return {"n_written": 0, "batch_dir": "", "skipped": 0}
    try:
        candidates = detect_emerging_skills(
            db_path,
            min_community_size=int(min_community_size),
            min_topic_purity=float(min_topic_purity),
            min_cohesion=float(min_cohesion),
            max_n=int(max_n),
            enable_stable_partition=bool(enable_stable_partition),
            enable_hybrid=bool(enable_hybrid),
        )
    except Exception:  # noqa: BLE001
        return {"n_written": 0, "batch_dir": "", "skipped": 0}
    if not candidates:
        return {"n_written": 0, "batch_dir": "", "skipped": 0}
    drafts: list[dict[str, Any]] = []
    for c in candidates:
        try:
            d = draft_skill_from_community(db_path, c)
        except Exception:  # noqa: BLE001
            continue
        if d.get("skill_name"):
            drafts.append(d)
    if not drafts:
        return {"n_written": 0, "batch_dir": "", "skipped": 0}
    try:
        return persist_drafts(
            drafts, root_dir=engram_dir / "skill_drafts",
        )
    except Exception:  # noqa: BLE001
        return {"n_written": 0, "batch_dir": "", "skipped": 0}


def _propose_via_engram(*, engram_dir: Path) -> dict[str, Any]:
    """Bridge the worker's dream_callable signature to `propose_dream_tasks`.

    Cycle 175.1 (2026-05-22) augments ``instructions`` with a soft retry
    hint for stuck-band candidates (trials ∈ [3, 10], fitness ∈
    (0.3, 0.5)). The hint is gathered by
    ``verimem.dream_stuck_hook.build_stuck_retry_seed`` which composes
    over the cycle 175 ``select_stuck_candidates`` primitive. The
    cluster algorithm inside ``propose_dream_tasks`` is free to ignore
    the hint — soft retry by design. Hard retry deferred to 175.3
    if H1 is falsified after 20 dream cycles. Empty corpus → seed
    suffix is "" so the instructions text is unchanged.

    Imports are local so the module is cheap to import (the hook will
    spawn a fresh process, so this only pays at fire-time).
    """
    from verimem.adaptive_threshold import adaptive_thresholds
    from verimem.dream import propose_dream_tasks
    from verimem.dream_community_hook import build_community_seed
    from verimem.dream_emergence_hook import build_emergence_seed
    from verimem.dream_stuck_hook import build_stuck_retry_seed
    from verimem.dream_thompson_hook import build_thompson_seed

    live_dirs = _live_dirs_from(engram_dir)
    shadow_root = engram_dir / "dreams" / f"auto-{int(time.time())}"
    # Cycle 175.1: stuck-candidate retry seed.
    stuck_seed = build_stuck_retry_seed(
        skill_db=live_dirs["skills_db"], max_n=3,
    )
    # Cycle 187: community topology seed (Louvain top-K dense
    # subgraphs of the fact graph).
    community_seed = build_community_seed(
        semantic_db=live_dirs["semantic_db"], max_n=3,
    )
    # Cycle 212: Thompson warm-up seed (Beta posterior arm sampling
    # over untrialed candidate skills). Closes the gap left by the
    # cycle-174 audit: 233/326 (71 %) untrialed skills.
    thompson_seed = build_thompson_seed(
        skill_db=live_dirs["skills_db"], max_n=3,
    )
    # Cycle 219: emergent-skill DRAFT seed (LLM-free pipeline
    # cycle 213 detect + cycle 217 draft). Surfaces fact-graph
    # communities ready for crystallisation, with deterministic
    # draft names + keywords pre-computed.
    # Cycle 233: align thresholds with `_persist_emergence_drafts` +
    # `register_emerging_drafts_as_facts` (purity=0.4, cohesion=0.2)
    # so the dream INSTRUCTIONS + disk audit + fact registry all
    # surface the SAME candidates. Asymmetry caused a session bug
    # where master-fact (purity 0.44) was registered but absent from
    # the seed text.
    # Cycle 246 A4 finding: at corpus size ~1889 facts the cycle-233
    # default 0.4 surfaces ZERO candidates (master-fact disgregates
    # into sub-clusters with purity 0.11-0.19, see threshold_sweep
    # 04:39). Lowering to 0.2 keeps emergence signal alive across
    # corpus growth. The cycle-184 anti-confab L1.8 gate still filters
    # spurious adoptions; cycle-235 promote stays manual.
    # Cycle 249: read corpus size + use adaptive_thresholds (cycle 248)
    # so the curve auto-tunes as the corpus grows. Fallback to (0.2, 0.1)
    # if the SQL read fails.
    try:
        import sqlite3 as _sql_cnt
        _c = _sql_cnt.connect(str(live_dirs["semantic_db"]))
        try:
            _n_facts = _c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        finally:
            _c.close()
        _purity_adapt, _cohesion_adapt = adaptive_thresholds(int(_n_facts))
    except Exception:  # noqa: BLE001
        _purity_adapt, _cohesion_adapt = (0.2, 0.1)
    # All four seeds are SOFT hints — propose_dream_tasks is free
    # to ignore any of them.
    emergence_seed = build_emergence_seed(
        semantic_db=live_dirs["semantic_db"], max_n=3,
        min_topic_purity=_purity_adapt, min_cohesion=_cohesion_adapt,
    )
    # Cycle 223: also persist the underlying drafts to disk for
    # an audit trail under <engram_dir>/skill_drafts/. Side-effect
    # only — the seed itself is already built above. Defensive:
    # any failure → no-op (this is observability, not critical
    # path).
    try:
        # Lower thresholds slightly compared to the default ones used
        # by build_emergence_seed: the audit trail is more useful when
        # it surfaces the same medium-confidence candidates the
        # instructions seed prioritises, so a future reader can see
        # *why* a given draft made it into a dream cycle.
        # Cycle 246 A4: lowered 0.4→0.2 to match cycle-246 fix in
        # build_emergence_seed above. Audit trail stays consistent
        # with the seed text.
        # Cycle 284: opt-in stable_partition activation via env var.
        # ENGRAM_USE_STABLE_PARTITION=1 routes emergence detection
        # through the cycle 261 cure (10x more stable partition under
        # sequential writes, validated cycle 282 §6.5). Default OFF.
        _use_stable = os.environ.get(
            "ENGRAM_USE_STABLE_PARTITION", "",
        ).strip().lower() in ("1", "true", "yes", "on")
        # Cycle 297: ENGRAM_USE_HYBRID env var (default OFF).
        # When True wins over stable_partition (precedence per cycle 292).
        # Cycle 296 production bench: HYBRID 44 candidates vs 0 other modes.
        _use_hybrid = os.environ.get(
            "ENGRAM_USE_HYBRID", "",
        ).strip().lower() in ("1", "true", "yes", "on")
        _persist_emergence_drafts(
            engram_dir=engram_dir, max_n=5,
            min_topic_purity=_purity_adapt,
            min_cohesion=_cohesion_adapt,
            enable_stable_partition=_use_stable,
            enable_hybrid=_use_hybrid,
        )
    except Exception:  # noqa: BLE001
        pass

    # Cycle 230: also register each draft as a soft fact in semantic.db
    # so the next session's hippo_facts_recall surfaces it without any
    # human or LLM action between firings. status='model_claim' keeps
    # the cycle-184 anti-confab L1.8 gate from picking it up as a
    # verified claim. Defensive: any failure is observability-only.
    try:
        from verimem.emerging_skill_register import (
            register_emerging_drafts_as_facts,
        )
        from verimem.skill_drafter import draft_skill_from_community
        from verimem.skill_emergence_detector import detect_emerging_skills
        db_path = live_dirs["semantic_db"]
        # Cycle 246 A4: 0.4→0.2 / 0.2→0.1 for consistency.
        # Cycle 249: use adaptive_thresholds populated above.
        cands = detect_emerging_skills(
            db_path, min_community_size=4,
            min_topic_purity=_purity_adapt,
            min_cohesion=_cohesion_adapt, max_n=5,
            enable_stable_partition=_use_stable,
            enable_hybrid=_use_hybrid,
        )
        if cands:
            drafts = [draft_skill_from_community(db_path, c) for c in cands]
            register_emerging_drafts_as_facts(db_path, drafts)
    except Exception:  # noqa: BLE001
        pass
    instructions = (
        "Auto-Dream cycle #69 — observe patterns since last trigger."
        + stuck_seed["instructions_suffix"]
        + community_seed["instructions_suffix"]
        + thompson_seed["instructions_suffix"]
        + emergence_seed["instructions_suffix"]
    )
    result = propose_dream_tasks(
        live_dirs=live_dirs,
        shadow_root=shadow_root,
        max_clusters=5,           # small, observe-pattern scope
        min_cluster_size=2,
        cluster_threshold=0.55,
        instructions=instructions,
    )
    # 2026-06-01 (Aurelio mandate): shadow retention. Each firing snapshots
    # the full live DB into dreams/auto-<ts>/; without pruning this grew to
    # 346 stale shadows (~7.9 GB). Keep only the last N (env
    # ENGRAM_DREAM_KEEP, default 3). Never touches non-'auto-' dirs / live DB.
    try:
        _keep = int(os.environ.get("ENGRAM_DREAM_KEEP", "3"))
    except (TypeError, ValueError):
        _keep = 3
    _prune_old_dreams(engram_dir, keep=max(1, _keep))
    return result


def _maintenance_enabled() -> bool:
    return os.environ.get("ENGRAM_AUTO_CONSOLIDATE", "on").strip().lower() not in (
        "0", "off", "false", "no")


def _consolidate_cooldown_s() -> float:
    try:
        return max(0.0, float(os.environ.get("ENGRAM_CONSOLIDATE_COOLDOWN_S", "14400")))
    except ValueError:
        return 14400.0  # 4h default


def run_maintenance(engram_dir: Path, *, now: float | None = None,
                    sm: Any = None, mem: Any = None) -> dict[str, Any]:
    """WF1 SPINE — the self-maintenance half that was dormant: make the corpus DIGEST, not
    just grow. LLM-free, cooldown-gated, fully wrapped (a step failure never crashes the
    worker), and mutations are REVERSIBLE (supersede-not-delete / additive master nodes).

    Steps: cycle_light (promote/retire) -> auto_consolidate (cluster master nodes) ->
    scan_corpus + heal_contradictions (supersede the weaker side of a real conflict).
    Opt-out: ENGRAM_AUTO_CONSOLIDATE=0. Cooldown: ENGRAM_CONSOLIDATE_COOLDOWN_S (default 4h)."""
    now = time.time() if now is None else now
    if not _maintenance_enabled():
        return {"ran": False, "reason": "disabled"}
    marker = engram_dir / "consolidate_last.json"
    try:
        last = (json.loads(marker.read_text(encoding="utf-8")).get("ts", 0.0)
                if marker.exists() else 0.0)
    except Exception:
        last = 0.0
    if now - float(last or 0.0) < _consolidate_cooldown_s():
        return {"ran": False, "reason": "cooldown"}

    out: dict[str, Any] = {"ran": True}
    try:
        if sm is None:
            from verimem.semantic import SemanticMemory
            sm = SemanticMemory()
        if mem is None:
            from verimem.memory import EpisodicMemory
            mem = EpisodicMemory()
        try:
            from verimem.sleep import SleepEngine
            rep = SleepEngine(semantic=sm, memory=mem).cycle_light()
            out["cycle_light"] = {"promoted": getattr(rep, "promoted", None),
                                  "retired": getattr(rep, "retired", None)}
        except Exception as exc:  # noqa: BLE001
            out["cycle_light_err"] = str(exc)[:100]
        try:
            from verimem.consolidation import auto_consolidate
            out["consolidate"] = auto_consolidate(sm, mem, dry_run=False)
        except Exception as exc:  # noqa: BLE001
            out["consolidate_err"] = str(exc)[:100]
        try:
            from verimem.contradiction import heal_contradictions, scan_corpus
            out["scan"] = scan_corpus(sm, time_budget_s=20.0)
            healed = heal_contradictions(sm, limit=100)
            out["healed"] = ({k: len(v) for k, v in healed.items()}
                             if isinstance(healed, dict) else None)
        except Exception as exc:  # noqa: BLE001
            out["heal_err"] = str(exc)[:100]
    except Exception as exc:  # noqa: BLE001 — never crash the worker
        out["fatal"] = str(exc)[:120]
    try:
        marker.write_text(json.dumps({"ts": now, **out}, ensure_ascii=False),
                          encoding="utf-8")
    except Exception:
        pass
    return out


def main() -> int:
    from verimem.auto_dream_trigger import maybe_trigger_dream

    engram_dir = _resolve_engram_dir()
    status = maybe_trigger_dream(
        engram_dir=engram_dir,
        now=time.time(),
        dream_callable=_propose_via_engram,
    )

    # WF1 spine activation: after the dream-propose, run the LLM-free self-maintenance
    # (cooldown-gated). This is the "corpus digests/dedups/heals" half that was dormant.
    try:
        status["maintenance"] = run_maintenance(engram_dir)
    except Exception:  # noqa: BLE001 — must never crash the worker
        status["maintenance"] = {"ran": False, "reason": "error"}

    # Observability: drop a one-line status JSON. SessionStart can show
    # this in the next session's banner ("last auto-dream: …").
    try:
        out_path = engram_dir / "auto_dream_last.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        status_with_meta = {
            **status,
            "worker_finished_at": time.time(),
        }
        out_path.write_text(
            json.dumps(status_with_meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # Observability failure must not crash the worker.
        pass

    return 0 if status.get("triggered") or status.get("reason") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
