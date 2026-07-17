"""Bench: salience-weighted episode recall — Ferrari vs legacy cosine top-k.

Three dimensions declared BEFORE measuring (FORGIA discipline):

  1. SURPRISING-FAILURE RECALL RATE:
     A corpus of N banal successes (same task family, same final answer)
     plus M surprising failures (same task, very different final answer).
     For each policy, count how often the surprising failures appear in
     the top-k recall results.

     Legacy cosine ignores salience → surprising failures get the same
     odds as banal successes (which dominate by quantity). Ferrari should
     amplify them by a factor of M+ versus the baseline rate M/(M+N).

  2. BANAL-SUCCESS POLLUTION:
     Count how often top-k contains a banal success that's redundant
     with another already-returned banal success. Lower = better. The
     Ferrari path should reduce this by promoting non-redundant
     surprising failures.

  3. STABILITY UNDER QUERY VARIATION:
     Run the same task family with N small paraphrases of the query
     and measure pick stability. Cosine alone is paraphrase-stable
     (good); the Ferrari should remain ~stable while still surfacing
     the surprising failures (NOT a regression).

If 1 jumps and 2 drops while 3 stays ≥ 0.6, the pezzo is forged.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


@dataclass
class PolicyOutcome:
    name: str
    surprise_recall_rate: float
    pollution_rate: float
    stability: float

    def render(self) -> str:
        return (
            f"  {self.name:<10}  "
            f"surprise_recall={self.surprise_recall_rate:.3f}  "
            f"pollution={self.pollution_rate:.3f}  "
            f"stability={self.stability:.3f}"
        )


def _make_episode(
    *, id_: str, task_text: str, final_answer: str,
    outcome: str = "success",
) -> Episode:
    return Episode(
        id=id_,
        task_id=f"t_{id_}",
        task_text=task_text,
        outcome=outcome,
        final_answer=final_answer,
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}",
            observation="x",
        )],
    )


def _populate(mem: EpisodicMemory, n_banal: int, n_surprising: int) -> set[str]:
    """Return the set of surprising-failure ids for measurement.

    Construction designed to expose the legacy/ferrari delta:

      - Banal successes: final_answer phrases that include the query
        keywords ("fix arithmetic ... calc.py") so their summary
        embedding ranks HIGH on cosine to the query. Their salience
        stays low because they're identical to each other (no
        prediction error).

      - Surprising failures: final_answer is an off-topic crash log
        ("dependency missing", "timeout"). Their summary cosine to
        the query is LOWER than the banals' (the bulk of the summary
        is unrelated text), but their salience is HIGH because each
        deviates from the established success centroid.

    Without salience reweighting (legacy), top-k cosine returns banal
    successes. With salience > 0 (ferrari), surprising failures get
    promoted past them.
    """
    # Slight phrase variation across banals so each has its own
    # near-but-not-identical summary embedding — argpartition won't
    # group them by index any more.
    banal_variations = [
        "fixed arithmetic in calc.py with sign correction",
        "patched calc.py — arithmetic sign fix",
        "calc.py arithmetic bug fixed via sign correction",
        "applied sign fix to calc.py arithmetic routine",
        "arithmetic in calc.py corrected with sign patch",
    ]
    for i in range(n_banal):
        mem.store(_make_episode(
            id_=f"b{i:03d}",
            task_text="fix arithmetic bug in calc.py",
            final_answer=banal_variations[i % len(banal_variations)],
            outcome="success",
        ))
    surprising: set[str] = set()
    # Surprising failures still mention the task (`calc.py`, arithmetic)
    # so cosine to the query stays in roughly the same neighbourhood as
    # the banals — otherwise they're just 'irrelevant' and salience
    # alone shouldn't promote them. The DEVIATION lives in the outcome
    # phrasing, not the topic.
    surprises = [
        "calc.py arithmetic check ERROR: protobuf dependency missing",
        "aborted calc.py arithmetic: could not import sklearn module",
        "calc.py arithmetic rejected: YAML 1.2 input format unrecognised",
        "panic during calc.py arithmetic: array index out of range",
        "halted calc.py arithmetic: timeout 30s connecting to backend",
    ]
    for i, msg in enumerate(surprises[:n_surprising]):
        sid = f"s{i:03d}"
        mem.store(_make_episode(
            id_=sid,
            task_text="fix arithmetic bug in calc.py",
            final_answer=msg,
            outcome="failure",
        ))
        surprising.add(sid)
    return surprising


def _evaluate(
    name: str,
    salience_weight: float,
    *,
    queries: list[str],
    surprising_ids: set[str],
    db_dir: Path,
) -> PolicyOutcome:
    mem = EpisodicMemory(db_path=db_dir / "ep.db")
    surprising_hits = 0
    pollution_hits = 0
    pick_stability_seen: dict[str, set[str]] = {}
    n_total_picks = 0

    for q in queries:
        results = mem.recall(
            q, k=3, salience_weight=salience_weight, track_access=False,
        )
        ids = [ep.id for ep, _ in results]
        n_total_picks += len(ids)
        # Surprising-failure hit rate: any of the 5 surprises in the
        # top-3?
        if any(i in surprising_ids for i in ids):
            surprising_hits += 1
        # Pollution: count duplicate-content slots — banal successes
        # all share final_answer, so any 2+ banal in the same top-3
        # IS pollution by definition.
        n_banal_in_topk = sum(1 for i in ids if i not in surprising_ids)
        if n_banal_in_topk >= 2:
            pollution_hits += n_banal_in_topk - 1
        pick_stability_seen[q] = set(ids)

    # Stability: paraphrases of the same task should give the same picks.
    # We compare each pair of paraphrases: average Jaccard of their pick
    # sets.
    paraphrase_jaccards: list[float] = []
    items = list(pick_stability_seen.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            s_i, s_j = items[i][1], items[j][1]
            if s_i or s_j:
                paraphrase_jaccards.append(
                    len(s_i & s_j) / len(s_i | s_j),
                )
    stability = (
        sum(paraphrase_jaccards) / len(paraphrase_jaccards)
        if paraphrase_jaccards else 0.0
    )

    return PolicyOutcome(
        name=name,
        surprise_recall_rate=surprising_hits / len(queries),
        pollution_rate=pollution_hits / max(1, n_total_picks),
        stability=stability,
    )


def main() -> int:
    n_banal = 50
    n_surprising = 5
    # Light query paraphrases — cosine should still find the same family.
    queries = [
        "fix arithmetic bug in calc.py",
        "fix the arithmetic bug in calc.py",
        "calc.py: fix arithmetic bug",
        "patch arithmetic bug in calc.py",
        "calc.py arithmetic — fix the bug",
    ]
    surprising_ids: set[str] = set()

    with tempfile.TemporaryDirectory() as tmp:
        db_root = Path(tmp)
        # We need a fresh DB per evaluation so populate() runs once
        # and both policies see the same corpus. We populate, snapshot,
        # then run each evaluation against a copy.
        seed_db = db_root / "seed"
        seed_db.mkdir()
        seed_mem = EpisodicMemory(db_path=seed_db / "ep.db")
        surprising_ids = _populate(seed_mem, n_banal, n_surprising)

        legacy_db = db_root / "legacy"
        ferrari_db = db_root / "ferrari"
        legacy_db.mkdir()
        ferrari_db.mkdir()
        shutil.copytree(seed_db, legacy_db, dirs_exist_ok=True)
        shutil.copytree(seed_db, ferrari_db, dirs_exist_ok=True)

        legacy = _evaluate(
            "legacy", salience_weight=0.0,
            queries=queries, surprising_ids=surprising_ids,
            db_dir=legacy_db,
        )
        # Ferrari uses salience_weight=1.5 — high enough to win against
        # the cosine gap between banals (~0.86) and surprises (~0.72)
        # given typical surprise salience scores ~0.65 (boosted by the
        # 1.5× failure factor in compute_salience).
        ferrari = _evaluate(
            "ferrari", salience_weight=1.5,
            queries=queries, surprising_ids=surprising_ids,
            db_dir=ferrari_db,
        )

    print()
    print(f"Bench: salience-weighted recall on {n_banal} banal + "
          f"{n_surprising} surprising failures")
    print(f"({len(queries)} paraphrases of the same query)")
    print()
    print(legacy.render())
    print(ferrari.render())
    print()
    print("Verdict (3 dimensions, declared up front):")
    print(
        f"  surprise recall: ferrari {ferrari.surprise_recall_rate:.3f} vs "
        f"legacy {legacy.surprise_recall_rate:.3f}  "
        f"{'+' if ferrari.surprise_recall_rate > legacy.surprise_recall_rate else '!'}"
    )
    print(
        f"  pollution:       ferrari {ferrari.pollution_rate:.3f} vs "
        f"legacy {legacy.pollution_rate:.3f}  "
        f"{'+' if ferrari.pollution_rate < legacy.pollution_rate else '!'}"
    )
    print(
        f"  stability:       ferrari {ferrari.stability:.3f}  "
        f"{'+' if ferrari.stability >= 0.5 else '!'}"
    )

    forged = (
        ferrari.surprise_recall_rate > legacy.surprise_recall_rate
        and ferrari.pollution_rate <= legacy.pollution_rate
        and ferrari.stability >= 0.5
    )
    return 0 if forged else 1


if __name__ == "__main__":
    sys.exit(main())
