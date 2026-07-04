"""Modern Hopfield pattern completion (Ramsauer et al. 2020).

Paper: "Hopfield Networks is All You Need", arXiv:2008.02217.

The classical Hopfield network has linear capacity in the number of
patterns and binary state vectors — toy. The modern variant
generalises to continuous states and shows that the right energy
function gives **exponential** capacity. The closed-form update is:

    completed_pattern = M.T @ softmax(β · M @ cue)

where:
  - `M ∈ R^{N × d}` is the stored pattern matrix (N patterns, d-dim),
  - `cue ∈ R^d` is a (possibly partial) query vector,
  - `β > 0` is the inverse-temperature controlling concentration.

Attention semantics:
  - β → ∞:  softmax → one-hot at argmax(M @ cue) — hard recall.
  - β → 0:  softmax → uniform — soft mean of all patterns.

For HippoAgent this is a complementary recall path to cosine top-k.
Cosine top-k returns the k nearest existing episodes (discrete picks);
Hopfield completion returns:
  - the *completed pattern* (a soft mixture vector — useful as a
    prior, or as a query for further retrieval),
  - the *attention weights* (a probability distribution over the
    stored patterns — useful for sampling or for surfacing the few
    candidates the cue is converging onto).

Where this matters: the wake loop sometimes has only PARTIAL context
(e.g. just the task_text, or just the last observation) and wants to
ask "what episode does this cue most resemble in the full feature
space?" — that's exactly what completion answers, and it does so
without requiring the cue to encode the same things stored episodes
do. A 5-word task can still complete to a 200-word episode summary.

Cost: one matrix-vector product + one softmax — milliseconds for
N=10k patterns.
"""
from __future__ import annotations

import numpy as np

from .memory import EpisodicMemory


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def _stable_softmax(scores: np.ndarray) -> np.ndarray:
    """Numerically-stable softmax — subtract max before exp.

    Standard trick: `softmax(x) = softmax(x - max(x))`. Without it a
    high-β cue can produce `exp` values that overflow float32.
    """
    if scores.size == 0:
        return scores
    s_max = float(np.max(scores))
    z = np.exp(scores - s_max)
    s = float(z.sum())
    return z / s if s > 0 else np.full_like(z, 1.0 / z.size)


def hopfield_complete(
    memory: EpisodicMemory,
    cue: np.ndarray,
    *,
    beta: float = 8.0,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Pattern completion over `memory.summary_embedding` matrix.

    Args:
      - `memory`: the EpisodicMemory whose summary embeddings form the
        pattern matrix M (rows = stored patterns).
      - `cue`: query vector — must live in the same embedding space as
        the stored patterns. The caller is responsible for encoding;
        this function normalises internally.
      - `beta`: inverse-temperature. Defaults to 8.0 (mid-concentration);
        increase for harder argmax-like recall, decrease for softer
        prior-like behaviour.

    Returns: `(completed_pattern, attention_weights, episode_ids)`.

      - `completed_pattern` ∈ R^d — the soft mixture over stored patterns.
      - `attention_weights` ∈ R^N — probability distribution over
        episodes (sums to 1).
      - `episode_ids` — the ids in the order the weights array indexes.

    Empty memory returns `(empty_array, empty_array, [])` so callers
    can branch without try/except.
    """
    ids, matrix = memory._ensure_recall_index()  # noqa: SLF001
    if not ids:
        return (
            np.zeros(0, dtype=np.float32),
            np.zeros(0, dtype=np.float32),
            [],
        )

    cue_n = _normalize(np.asarray(cue, dtype=np.float32))
    # M @ cue gives the dot products (cosines, since stored patterns
    # are already unit-norm — that's the contract the embedding module
    # honours).
    scores = matrix @ cue_n  # shape (N,)
    weights = _stable_softmax(beta * scores)
    completed = matrix.T @ weights  # shape (d,)
    return completed, weights, list(ids)


def hopfield_recall(
    memory: EpisodicMemory,
    cue: np.ndarray,
    *,
    k: int = 5,
    beta: float = 8.0,
):
    """Hopfield-attention top-k episodes for a partial cue.

    Convenience wrapper: runs `hopfield_complete`, then returns the
    top-k episodes by attention weight. Each tuple is
    `(episode, attention_weight)` — the weight is a probability, not
    a cosine, so it sums-to-one across the entire memory (not just
    the top-k).

    Used by callers that want a "soft argmax" over partial cues
    instead of a pure cosine ranking — the two strategies surface
    different episodes when the corpus has many close-cosine matches
    and a single semantically-nailed pattern.
    """
    completed, weights, ids = hopfield_complete(memory, cue, beta=beta)
    if not ids:
        return []
    if k >= len(ids):
        order = np.argsort(-weights)
    else:
        top = np.argpartition(-weights, k - 1)[:k]
        order = top[np.argsort(-weights[top])]
    wanted = [ids[i] for i in order]
    ep_by_id = memory._batch_get_episodes(wanted)  # noqa: SLF001
    out = []
    for i in order:
        ep = ep_by_id.get(ids[i])
        if ep is not None:
            out.append((ep, float(weights[i])))
    return out


__all__ = ["hopfield_complete", "hopfield_recall"]
