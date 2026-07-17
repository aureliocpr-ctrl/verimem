"""Bench: wake retrieval with salience + recency — 3 dimensions.

Pezzo #18 wires `wake_salience_weight` + `wake_recency_weight` into
`_retrieve_episodes`. Primitives existed in `recall()` since pezzo
#6; cabling makes them actually visible to the wake's few-shot block.

Dichiarate prima di misurare:

  1. SALIENCE WEIGHT IS PROPAGATED: with `wake_salience_weight=1.5`
     vs 0.0 on the same corpus, the wake retrieve produces a
     DIFFERENT ordering. Salience scores vary across stored episodes
     (compute_salience caches a 0..1 surprise score), so a non-zero
     weight always shifts the rerank. Target: ordering changes in
     ≥ 0.50 of queries (proves the flag is propagated end-to-end).

  2. RECENCY DOMINATES TIES: 5 cosine-tied successes spread across
     different created_at. With recency_weight=0.20, the most-recent
     episode wins top-1 in 100% of cases.

  3. ZERO REGRESSION ON CLEAN RECALL: with salience+recency on but
     a corpus where one episode is clearly the right match, the
     right match still wins ≥ 0.95 of the time.
"""
from __future__ import annotations

import gc
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.config import CONFIG
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.wake import WakeAgent, WakeConfig


def _ep(*, ep_id: str, text: str, outcome: str = "success",
        created_at: float | None = None) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="ok",
        traces=[Trace(step=1, thought="t", action="A",
                      action_input="", observation="o")],
        tokens_used=1, skills_used=[],
        created_at=created_at or time.time(),
    )


def _build_wake(memory):
    wake = object.__new__(WakeAgent)
    wake.memory = memory  # type: ignore[misc]
    wake.cfg = WakeConfig(
        max_steps=4, self_critique=False, episodes_recall_k=5,
    )
    return wake


def _save_cfg(*fields: str) -> dict:
    return {f: getattr(CONFIG, f) for f in fields}


def _restore_cfg(saved: dict) -> None:
    for f, v in saved.items():
        object.__setattr__(CONFIG, f, v)


def main() -> int:
    saved = _save_cfg(
        "wake_salience_weight", "wake_recency_weight", "wake_recency_tau_s",
        "forward_replay_include_failures",
        "tcm_cross_session_enabled",  # avoid noise from pezzo #17
    )
    object.__setattr__(CONFIG, "tcm_cross_session_enabled", False)

    tmp = Path(tempfile.mkdtemp(prefix="bench_wake_sr_"))
    try:
        # ---- Dimension 1: salience weight is propagated -----------
        # 8 banal episodes + 1 outlier (intentionally varied text so
        # compute_salience scores it differently from the banal cluster).
        # With `wake_salience_weight=1.5` vs 0.0 the rerank should shift.
        object.__setattr__(CONFIG, "wake_recency_weight", 0.0)
        object.__setattr__(CONFIG, "forward_replay_include_failures", False)

        mem = EpisodicMemory(db_path=tmp / "ep1.db")
        for i in range(8):
            mem.store(_ep(ep_id=f"banal{i}", text=f"banal task case {i}"))
        mem.store(_ep(
            ep_id="outlier",
            text="banal task case with unusual outcome twist",
        ))

        wake = _build_wake(mem)
        n = 20
        diff_count = 0
        for i in range(n):
            object.__setattr__(CONFIG, "wake_salience_weight", 0.0)
            base = wake._retrieve_episodes(f"banal task case {i}")  # noqa: SLF001
            base_ids = [ep.id for ep, _ in base if ep.outcome == "success"]
            object.__setattr__(CONFIG, "wake_salience_weight", 1.5)
            sal = wake._retrieve_episodes(f"banal task case {i}")  # noqa: SLF001
            sal_ids = [ep.id for ep, _ in sal if ep.outcome == "success"]
            if base_ids != sal_ids:
                diff_count += 1
        sal_rate = diff_count / n

        # ---- Dimension 2: recency dominates --------------------
        object.__setattr__(CONFIG, "wake_salience_weight", 0.0)
        object.__setattr__(CONFIG, "wake_recency_weight", 0.20)
        object.__setattr__(CONFIG, "wake_recency_tau_s", 86400.0)
        object.__setattr__(CONFIG, "forward_replay_include_failures", False)

        mem2 = EpisodicMemory(db_path=tmp / "ep2.db")
        now = time.time()
        # 5 cosine-tied episodes spread across days.
        ages_days = [10, 7, 5, 3, 0]  # 0 = today, 10 = 10 days ago
        for i, age in enumerate(ages_days):
            mem2.store(_ep(
                ep_id=f"e{i}",
                text="duplicate task body",
                created_at=now - age * 86400,
            ))
        wake2 = _build_wake(mem2)
        rec_hits = 0
        for _ in range(20):
            out = wake2._retrieve_episodes("duplicate task body")  # noqa: SLF001
            ids = [ep.id for ep, _ in out if ep.outcome == "success"]
            if ids and ids[0] == "e4":  # most-recent, age=0
                rec_hits += 1
        rec_rate = rec_hits / 20

        # ---- Dimension 3: relevance preserved ------------------
        object.__setattr__(CONFIG, "wake_salience_weight", 0.5)
        object.__setattr__(CONFIG, "wake_recency_weight", 0.10)
        object.__setattr__(CONFIG, "wake_recency_tau_s", 7 * 86400.0)
        object.__setattr__(CONFIG, "forward_replay_include_failures", False)

        mem3 = EpisodicMemory(db_path=tmp / "ep3.db")
        diverse = [
            ("compute factorial of n", "fact"),
            ("send email via smtp", "email"),
            ("parse json file", "json"),
            ("connect postgres database", "pg"),
            ("render html template", "html"),
        ]
        for text, eid in diverse:
            mem3.store(_ep(ep_id=eid, text=text))
        wake3 = _build_wake(mem3)
        rel_hits = 0
        queries = [
            ("calculate factorial of integer", "fact"),
            ("dispatch email through smtp protocol", "email"),
            ("read json configuration", "json"),
            ("postgres connection string", "pg"),
            ("render template html", "html"),
        ] * 4  # 20 queries total
        for q, expected in queries:
            out = wake3._retrieve_episodes(q)  # noqa: SLF001
            ids = [ep.id for ep, _ in out if ep.outcome == "success"]
            if ids and ids[0] == expected:
                rel_hits += 1
        rel_rate = rel_hits / len(queries)
    finally:
        wake = wake2 = wake3 = None  # type: ignore[assignment]  # noqa: F841
        mem = mem2 = mem3 = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)
        _restore_cfg(saved)

    print()
    print("Bench: wake retrieval with salience + recency cabled")
    print()
    print("  salience weight propagated (1.5 vs 0.0, ranking shifts):")
    print(f"    diff-ordering rate: {sal_rate:.2f} ({diff_count}/{n}) "
          f"(target ≥ 0.50)")
    print()
    print("  recency dominates ties (0.20 weight, τ=1d, 5 ties):")
    print(f"    most-recent top-1: {rec_rate:.2f} ({rec_hits}/20) (target ≥ 0.95)")
    print()
    print("  relevance preserved (sal=0.5 + rec=0.10, diverse corpus):")
    print(f"    correct match: {rel_rate:.2f} ({rel_hits}/{len(queries)}) "
          f"(target ≥ 0.95)")
    print()
    print("Verdict (3 dimensions):")
    d1 = sal_rate >= 0.50
    d2 = rec_rate >= 0.95
    d3 = rel_rate >= 0.95
    print(f"  salience flag propagated: {'+' if d1 else '!'}")
    print(f"  recency tie-break:        {'+' if d2 else '!'}")
    print(f"  relevance preserved:      {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
