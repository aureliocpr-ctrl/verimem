"""Trace alignment — find where a failed trajectory diverged from a success.

Cognitive analogue:
  Reverse / sharp-wave replay in CA1 hippocampal place cells (Foster &
  Wilson 2006; Karlsson & Frank 2009). After a failed run, the brain
  replays the trajectory and marks where the predicted path-cell sequence
  diverged from the canonical successful one. The marked locus is the
  **prediction error**, the substrate of credit assignment.

What this module does, in one breath:
  Given a failure Episode and a success Episode that used the same skill,
  align them step-by-step on the basis of *observation* embeddings
  (the external ground truth, not the model's actions), then locate the
  first step where the aligned actions diverge while observations were
  still close. That step is the **divergence point** — exactly the locus
  the agent should be told about on the next attempt.

Why on observations and not on actions:
  Observations are what the *world* said. Actions are what the *model*
  chose. If we aligned on actions, two trajectories that took different
  actions for the same situation would look like they happened at
  different times — exactly the case we need to detect. Aligning on
  observations gives us a stable timeline; the action mismatch on top of
  it is the signal.

Cost:
  O(N * M) Needleman-Wunsch with float32 embeddings of dim 384, plus
  one `embedding.encode` call per unique observation. Real ReAct
  trajectories have 5–15 steps, so this fits in a few milliseconds and
  zero LLM calls.

Public API:
  • `align_traces(failure, success) -> Alignment`
  • `find_divergence_point(alignment, ...) -> DivergencePoint | None`
  • `format_divergence(div, alignment) -> str`     (for prompt injection)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import embedding
from .episode import Episode, Trace


# A single matched pair from the alignment. Either side may be None when
# the algorithm chose a "skip" (insertion/deletion in DP terms).
@dataclass
class AlignedPair:
    fail: Trace | None
    success: Trace | None
    obs_similarity: float       # cosine of obs embeddings; -inf when one side is None
    action_match: bool          # True when both actions are identical strings


@dataclass
class Alignment:
    pairs: list[AlignedPair] = field(default_factory=list)
    score: float = 0.0          # NW total score — higher = better global alignment

    @property
    def length(self) -> int:
        return len(self.pairs)


@dataclass
class DivergencePoint:
    """Where the failure broke the success template.

    Indices are 1-based to match Trace.step. A None on either side means
    the alignment chose to skip that side (the failed run inserted or
    skipped a step relative to the canonical success).
    """
    fail_step: int | None
    success_step: int | None
    obs_similarity: float
    fail_action: str
    success_action: str
    rationale: str  # short human-readable description


# ---------------------------------------------------------------------------
# Embedding helper — pure caching wrapper. We do not modify embedding.py;
# the LRU is already there. We just feed it the (truncated) observation
# strings.
# ---------------------------------------------------------------------------


_OBS_TRIM = 1024  # chars; embeddings beyond this length add nothing useful


def _obs_vec(t: Trace) -> np.ndarray:
    """Embed an observation deterministically.

    We trim to _OBS_TRIM chars first so that two observations whose tails
    differ but whose semantic head is the same still embed similarly. If
    the observation is empty (a pure thought-only step, rare but possible)
    we fall back on the action_input — better than a zero vector that
    would make every empty step look identical.
    """
    text = (t.observation or t.action_input or t.thought or "").strip()
    if len(text) > _OBS_TRIM:
        text = text[:_OBS_TRIM]
    return embedding.encode(text)


def _cosine(u: np.ndarray, v: np.ndarray) -> float:
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


# ---------------------------------------------------------------------------
# Needleman-Wunsch over observation embeddings.
# ---------------------------------------------------------------------------


# Gap penalty. Negative; tuned so the algorithm prefers a "skip on one
# side" only when the cosine similarity to every alternative is below
# this threshold. With normalised vectors cosine in [-1, 1], a gap of
# -0.30 says: "I'd rather pair you with anything that has cosine >= -0.30
# than mark you as missing on one side."
_GAP_PENALTY = -0.30


def align_traces(failure: Episode, success: Episode) -> Alignment:
    """Globally align two trajectories on observation similarity.

    Returns an Alignment whose pairs respect the temporal order of both
    inputs. The score is the standard NW total — useful for ranking
    multiple candidate success-twins; absolute value has no meaning.

    Empty inputs are handled gracefully: if either trajectory has no
    traces, the alignment is empty and score is 0.
    """
    f, s = failure.traces, success.traces
    n, m = len(f), len(s)
    if n == 0 or m == 0:
        return Alignment(pairs=[], score=0.0)

    # Pre-embed once. Reuse via the LRU in embedding.encode.
    fv = [_obs_vec(t) for t in f]
    sv = [_obs_vec(t) for t in s]

    # Score matrix. dp[i][j] = best alignment score of f[:i] vs s[:j].
    dp = np.full((n + 1, m + 1), -np.inf, dtype=np.float64)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        dp[i, 0] = dp[i - 1, 0] + _GAP_PENALTY
    for j in range(1, m + 1):
        dp[0, j] = dp[0, j - 1] + _GAP_PENALTY

    # Forward fill.
    sims = np.zeros((n, m), dtype=np.float64)
    for i in range(n):
        for j in range(m):
            sims[i, j] = _cosine(fv[i], sv[j])
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match_score = dp[i - 1, j - 1] + sims[i - 1, j - 1]
            up = dp[i - 1, j] + _GAP_PENALTY
            left = dp[i, j - 1] + _GAP_PENALTY
            dp[i, j] = max(match_score, up, left)

    # Trace back.
    pairs: list[AlignedPair] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i, j] == dp[i - 1, j - 1] + sims[i - 1, j - 1]:
            pairs.append(AlignedPair(
                fail=f[i - 1], success=s[j - 1],
                obs_similarity=float(sims[i - 1, j - 1]),
                action_match=(f[i - 1].action == s[j - 1].action),
            ))
            i -= 1; j -= 1
        elif i > 0 and dp[i, j] == dp[i - 1, j] + _GAP_PENALTY:
            pairs.append(AlignedPair(
                fail=f[i - 1], success=None,
                obs_similarity=float("-inf"),
                action_match=False,
            ))
            i -= 1
        else:
            pairs.append(AlignedPair(
                fail=None, success=s[j - 1],
                obs_similarity=float("-inf"),
                action_match=False,
            ))
            j -= 1
    pairs.reverse()
    return Alignment(pairs=pairs, score=float(dp[n, m]))


# ---------------------------------------------------------------------------
# Divergence detection.
# ---------------------------------------------------------------------------


# Cosine threshold above which two observations are considered the same
# situation. With our deterministic test stub vectors are sparse hashes,
# so unrelated texts cluster around 0 and identical text is exactly 1.
# Real sentence-transformers cluster paraphrases around 0.6-0.85.
_OBS_SAME_SITUATION = 0.55


# Cosine threshold below which two action_inputs (e.g. file paths,
# search queries, code snippets) are considered semantically different
# even when the wrapping tool name is the same. The asymmetry with
# _OBS_SAME_SITUATION is intentional: action_inputs are usually short
# and lexically rigid (paths, identifiers) so we want a stricter cut.
_INPUT_DIFFER_BELOW = 0.50


def find_divergence_point(
    alignment: Alignment,
    obs_threshold: float = _OBS_SAME_SITUATION,
    input_threshold: float = _INPUT_DIFFER_BELOW,
) -> DivergencePoint | None:
    """Return the first step where the failure took a wrong turn.

    Two kinds of divergence are detected, in priority order:

    1. **Action divergence** under matching observations: the most
       informative case — same situation, different decision. Reported
       with kind='action'.

    2. **Input divergence** under matching action: stesso tool name, ma
       action_input semanticamente diverso (cosine sim below
       `input_threshold`). Captures "modello ha letto il file sbagliato"
       / "ha cercato la query sbagliata" — the kind of failure that
       changes the world from step 1 and so produces no aligned
       observations later. Reported with kind='input'.

    We return the FIRST divergence found while walking the aligned
    pairs in order. Action divergence under same situation wins over
    input divergence at a later step, even if both are present.

    If no such pair exists we return None — the failure isn't
    attributable to a single divergent action under a comparable
    situation, nor to a wrong action_input. The cause is elsewhere
    (e.g. an outright tool error, or the failure surfaces only when
    alignment runs out).
    """
    # First pass: action divergence (the high-information signal).
    action_div = _scan_action_divergence(alignment, obs_threshold)
    if action_div is not None:
        return action_div
    # Second pass: input divergence (the "wrong file at step 1" case).
    return _scan_input_divergence(alignment, input_threshold)


def _scan_action_divergence(
    alignment: Alignment, obs_threshold: float,
) -> DivergencePoint | None:
    for pair in alignment.pairs:
        if pair.fail is None or pair.success is None:
            continue
        if pair.obs_similarity < obs_threshold:
            continue
        if pair.action_match:
            continue
        rationale = (
            f"step {pair.fail.step}: same situation "
            f"(obs sim {pair.obs_similarity:.2f}) but action diverged "
            f"({pair.fail.action!r} vs {pair.success.action!r})"
        )
        return DivergencePoint(
            fail_step=pair.fail.step,
            success_step=pair.success.step,
            obs_similarity=pair.obs_similarity,
            fail_action=pair.fail.action,
            success_action=pair.success.action,
            rationale=rationale,
        )
    return None


def _scan_input_divergence(
    alignment: Alignment, input_threshold: float,
) -> DivergencePoint | None:
    """Find the first step where the same tool was called with a
    semantically different action_input.

    This catches the "wrong file at step 1" pattern that action+observation
    alignment misses: when the failure called `fs_read_file("main.py")` and
    the success called `fs_read_file("calc.py")`, the obs_similarity is
    low (different file contents) so the action-divergence scanner skips
    it. But the actions match, and the divergence is in the *input* space.
    """
    for pair in alignment.pairs:
        if pair.fail is None or pair.success is None:
            continue
        if not pair.action_match:
            # An action divergence at this step would have been caught by
            # the first-pass scanner; here we focus on same-action,
            # different-input pairs.
            continue
        f_input = (pair.fail.action_input or "").strip()
        s_input = (pair.success.action_input or "").strip()
        if not f_input or not s_input:
            continue
        if f_input == s_input:
            continue
        # Identical actions with literally identical inputs cannot diverge.
        # Cosine on the embedded inputs catches paraphrases vs real
        # semantic mismatch.
        f_vec = embedding.encode(f_input[:_OBS_TRIM])
        s_vec = embedding.encode(s_input[:_OBS_TRIM])
        sim = _cosine(f_vec, s_vec)
        if sim >= input_threshold:
            continue
        rationale = (
            f"step {pair.fail.step}: same tool ({pair.fail.action!r}) but "
            f"action_input diverged (cosine {sim:.2f}, threshold "
            f"{input_threshold:.2f}); failed input ≠ success input"
        )
        return DivergencePoint(
            fail_step=pair.fail.step,
            success_step=pair.success.step,
            obs_similarity=pair.obs_similarity,
            fail_action=pair.fail.action,
            success_action=pair.success.action,
            rationale=rationale,
        )
    return None


# ---------------------------------------------------------------------------
# Prompt rendering — the only thing wake.py needs to know about.
# ---------------------------------------------------------------------------


def format_divergence(
    div: DivergencePoint,
    alignment: Alignment,
    max_observation_chars: int = 240,
) -> str:
    """Render a divergence point as a compact block for the agent prompt.

    The format is intentionally terse. We include just enough to let the
    next attempt avoid the same trap: the situation up to the divergence,
    what failed, what succeeded. No critique, no editorialising — the
    prompt elsewhere already has those.
    """
    lines = ["## DIVERGENCE FROM SUCCESS PATH"]
    lines.append(div.rationale)

    # Find the failed trace at the divergence point to surface its observation.
    matched: AlignedPair | None = None
    for p in alignment.pairs:
        if p.fail is not None and p.fail.step == div.fail_step:
            matched = p
            break
    if matched is not None and matched.success is not None:
        obs_excerpt = (matched.success.observation or "")[:max_observation_chars]
        if obs_excerpt:
            obs_excerpt = obs_excerpt.replace("\n", " ").strip()
            lines.append(f"At that point the canonical observation was: {obs_excerpt!r}")
        lines.append(
            f"The successful run took: {div.success_action} "
            f"(consider this; deviate only with reason)."
        )
        lines.append(
            f"The failed run took: {div.fail_action} "
            "(this branch did not converge)."
        )
    return "\n".join(lines) + "\n"
