"""Full curation pipeline orchestrator.

FORGIA pezzo #239 — Wave 38. One-shot housekeeping that runs:
  1. derive_predicates_batch (bootstrap STRIPS graph)
  2. apply_recommendations (promote/retire per policy)
  3. find_duplicate_skills (report near-dupes)
  4. predicate_graph_check (sanity)
  5. corpus_size_report
  6. decay_simulate (preview prune)

dry-run by default; `apply=True` persists the predicate-derivation
+ status changes. The other 4 sections are always read-only.
"""
from __future__ import annotations

from typing import Any

from .apply_recommendations import apply_recommendations
from .decay_simulate import decay_simulate
from .find_duplicates import find_duplicate_skills
from .predicate_derivation import derive_predicates_batch
from .predicate_graph_check import predicate_graph_check


def curate_pipeline(
    *,
    agent: Any,
    apply: bool = False,
    duplicate_threshold: float = 0.8,
    derivation_threshold: float = 0.5,
) -> dict[str, Any]:
    """Run the full curation pipeline. Returns the aggregated report.

    Args:
      - `agent`: HippoAgent instance.
      - `apply`: when True, the predicate derivation + the
        recommended promote/retire actions are persisted. Other
        sections (duplicates, graph_check, size, decay) are always
        read-only.
      - `duplicate_threshold`: passed to find_duplicate_skills.
      - `derivation_threshold`: passed to derive_predicates_batch.

    Returns: dict with sections `predicates, recommendations,
    duplicates, predicate_graph, size, decay_preview, summary`.
    """
    # 1. Predicate derivation.
    predicates = derive_predicates_batch(
        agent=agent,
        threshold=derivation_threshold,
        apply=apply,
        overwrite=False,
    )

    # 2. Apply skill_health recommendations.
    recommendations = apply_recommendations(
        agent=agent,
        actions=["promote", "retire"],
        apply=apply,
    )

    # 3. Find duplicate skills (read-only).
    skills_pool = []
    try:
        skills_pool = list(agent.skills.all())
    except Exception:
        skills_pool = []
    duplicates = find_duplicate_skills(
        skills_pool, threshold=duplicate_threshold,
    )

    # 4. Predicate graph sanity check.
    predicate_graph = predicate_graph_check(skills_pool)

    # 5. Corpus size.
    size_payload: dict[str, Any] = {}
    try:
        from .config import CONFIG
        from .corpus_size import corpus_size_report
        size_payload = corpus_size_report(data_dir=CONFIG.data_dir)
    except Exception:
        size_payload = {"unavailable": True}

    # 6. Decay simulate.
    decay_preview = decay_simulate(agent=agent, top_k=10)

    # Summary.
    parts = [
        f"Curation pipeline ({'APPLIED' if apply else 'DRY-RUN'})."
    ]
    parts.append(
        f"Predicates: {predicates['stats']['n_with_preconditions']} "
        f"skills derived pre."
    )
    parts.append(
        f"Recommendations: {recommendations['n_applied']} applied / "
        f"{recommendations['n_proposed']} proposed."
    )
    parts.append(f"Duplicates: {len(duplicates['pairs'])} pairs.")
    parts.append(
        f"Graph: {predicate_graph['n_edges']} edges, "
        f"{len(predicate_graph['cycles'])} cycles."
    )
    if size_payload and "total_mb" in size_payload:
        parts.append(f"Disk: {size_payload['total_mb']:.2f} MB.")
    parts.append(
        f"Decay preview: {len(decay_preview['candidates'])} at-risk."
    )

    return {
        "apply": apply,
        "predicates": predicates,
        "recommendations": recommendations,
        "duplicates": duplicates,
        "predicate_graph": predicate_graph,
        "size": size_payload,
        "decay_preview": decay_preview,
        "summary": " ".join(parts),
    }


__all__ = ["curate_pipeline"]
