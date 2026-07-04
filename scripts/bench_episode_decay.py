"""Bench: Ebbinghaus forgetting curve — pruning quality vs preservation.

Three dimensions declared BEFORE measuring (FORGIA discipline):

  1. PRUNING REACH:
     A 400-episode synthetic corpus mixing fresh/ancient/active episodes.
     The decay pass should remove the ancient & untouched ones (ideally
     ~30-50% of the corpus) without touching the active ones.

  2. HOT-EPISODE PRESERVATION (no false positives):
     Episodes that ANY of (recent OR recently-accessed OR high-salience
     OR high-access-count) should be preserved. Pruning a hot episode
     is a regression — count those.

  3. RECALL QUALITY POST-PRUNE:
     Run the same set of test queries against the pre-prune corpus and
     post-prune corpus. Top-k cosine should still surface relevant
     active episodes — pruning shouldn't break retrieval. Measure
     overlap between pre and post top-k as a stability score.
"""
from __future__ import annotations

import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory


@dataclass
class BenchOutcome:
    label: str
    n_total_before: int
    n_pruned: int
    n_hot_pruned: int  # false positives: should NOT have been pruned
    recall_overlap: float

    def render(self) -> str:
        return (
            f"  {self.label:<10}  "
            f"pruned={self.n_pruned:>3}/{self.n_total_before}  "
            f"hot_pruned={self.n_hot_pruned}  "
            f"recall_overlap={self.recall_overlap:.3f}"
        )


def _ep(
    *, id_: str, task_text: str,
    age_days: float,
    last_accessed_age_days: float | None = None,
    access_count: int = 0,
    salience: float = 0.5,
    outcome: str = "success",
) -> Episode:
    now = time.time()
    return Episode(
        id=id_,
        task_id="t",
        task_text=task_text,
        outcome=outcome,
        final_answer=f"answer for {id_}",
        created_at=now - age_days * 86400,
        last_accessed_at=(
            now - last_accessed_age_days * 86400
            if last_accessed_age_days is not None else 0.0
        ),
        access_count=access_count,
        salience_score=salience,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


def _populate(mem: EpisodicMemory) -> tuple[set[str], set[str]]:
    """Returns (hot_ids, cold_ids) for measurement.

    Hot episodes (must NOT be pruned):
      - 50 fresh successes (created in the last 7 days)
      - 30 frequently accessed episodes (10+ accesses in last 14 days)
      - 20 high-salience surprises (recent failures with salience ≥ 0.7)

    Cold episodes (should be pruned):
      - 200 ancient never-accessed (90+ days, access_count=0, neutral salience)
      - 100 medium-age low-engagement (30 days, access_count=0)
    """
    hot_ids: set[str] = set()
    cold_ids: set[str] = set()

    # Hot: fresh
    for i in range(50):
        ep_id = f"hot_fresh_{i:02d}"
        mem.store(_ep(
            id_=ep_id,
            task_text=f"fresh task {i % 7}",
            age_days=2.0 + (i * 0.1),
        ))
        hot_ids.add(ep_id)

    # Hot: frequently accessed
    for i in range(30):
        ep_id = f"hot_accessed_{i:02d}"
        mem.store(_ep(
            id_=ep_id,
            task_text=f"often-recalled topic {i % 5}",
            age_days=45.0,
            last_accessed_age_days=2.0 + i * 0.05,
            access_count=10 + i,
            salience=0.4,
        ))
        hot_ids.add(ep_id)

    # Hot: surprising recent failures
    for i in range(20):
        ep_id = f"hot_surprise_{i:02d}"
        mem.store(_ep(
            id_=ep_id,
            task_text=f"surprising failure {i % 4}",
            age_days=10.0,
            outcome="failure",
            salience=0.85,
        ))
        hot_ids.add(ep_id)

    # Cold: ancient
    for i in range(200):
        ep_id = f"cold_ancient_{i:03d}"
        mem.store(_ep(
            id_=ep_id,
            task_text=f"ancient irrelevant noise {i}",
            age_days=120.0 + i * 0.1,
        ))
        cold_ids.add(ep_id)

    # Cold: medium age, no engagement
    for i in range(100):
        ep_id = f"cold_medium_{i:03d}"
        mem.store(_ep(
            id_=ep_id,
            task_text=f"medium age dead topic {i}",
            age_days=35.0,
            salience=0.2,  # below the neutral default
        ))
        cold_ids.add(ep_id)

    return hot_ids, cold_ids


def _evaluate(label: str, threshold: float) -> BenchOutcome:
    with tempfile.TemporaryDirectory() as tmp:
        mem = EpisodicMemory(db_path=Path(tmp) / "ep.db")
        hot_ids, _cold_ids = _populate(mem)
        n_total_before = mem.count()

        # Recall snapshot pre-prune for the overlap measurement.
        test_queries = [
            "fresh task",
            "often-recalled topic",
            "surprising failure",
        ]
        pre_picks: dict[str, set[str]] = {}
        for q in test_queries:
            pre_picks[q] = {ep.id for ep, _ in mem.recall(
                q, k=5, track_access=False,
            )}

        deleted = mem.decay_prune(retention_threshold=threshold)

        post_picks: dict[str, set[str]] = {}
        for q in test_queries:
            post_picks[q] = {ep.id for ep, _ in mem.recall(
                q, k=5, track_access=False,
            )}

        n_hot_pruned = len(deleted & hot_ids)
        overlaps = [
            (
                len(pre_picks[q] & post_picks[q])
                / max(1, len(pre_picks[q] | post_picks[q]))
            )
            for q in test_queries
        ]
        recall_overlap = sum(overlaps) / len(overlaps)

        return BenchOutcome(
            label=label,
            n_total_before=n_total_before,
            n_pruned=len(deleted),
            n_hot_pruned=n_hot_pruned,
            recall_overlap=recall_overlap,
        )


def main() -> int:
    print()
    print("Bench: Ebbinghaus decay — pruning quality on a mixed corpus")
    print()
    print("Population: 50 fresh + 30 frequently-accessed + 20 surprising "
          "= 100 hot")
    print("            200 ancient + 100 medium-no-engagement = 300 cold")
    print("            Total: 400")
    print()

    legacy = BenchOutcome(
        label="legacy",
        n_total_before=400,
        n_pruned=0,           # legacy: no decay
        n_hot_pruned=0,
        recall_overlap=1.0,    # nothing changed → perfect overlap
    )
    ferrari_05 = _evaluate("ferrari/0.5", threshold=0.50)
    ferrari_03 = _evaluate("ferrari/0.3", threshold=0.30)

    print(legacy.render())
    print(ferrari_05.render())
    print(ferrari_03.render())

    print()
    print("Verdict (3 dimensions, declared up front):")
    # 1. Reach: ferrari should prune at least 30% of corpus
    reach_ok = ferrari_03.n_pruned >= 0.3 * ferrari_03.n_total_before
    # 2. Hot preservation: ferrari shouldn't prune more than 5% of hot
    hot_safe = ferrari_03.n_hot_pruned <= 0.05 * 100  # 100 hot
    # 3. Recall quality: post-prune recall should match pre-prune within 60%
    recall_ok = ferrari_03.recall_overlap >= 0.6
    print(
        f"  reach (>=30% pruned): "
        f"{ferrari_03.n_pruned}/{ferrari_03.n_total_before} = "
        f"{ferrari_03.n_pruned/ferrari_03.n_total_before:.0%}  "
        f"{'+' if reach_ok else '!'}"
    )
    print(
        f"  hot preserved (<5% false positives): "
        f"{ferrari_03.n_hot_pruned}/100  "
        f"{'+' if hot_safe else '!'}"
    )
    print(
        f"  recall stable (>=60% overlap): "
        f"{ferrari_03.recall_overlap:.3f}  "
        f"{'+' if recall_ok else '!'}"
    )

    return 0 if (reach_ok and hot_safe and recall_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
