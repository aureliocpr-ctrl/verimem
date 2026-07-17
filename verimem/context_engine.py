"""TCM contextual reinstatement (Howard & Kahana 2002).

Paper: "A distributed representation of temporal context",
J. Math. Psychol. 46:269–299, DOI 10.1006/jmps.2001.1388.

Human episodic memory is indexed by a *drifting context vector*: a
continuous neural state that evolves with each observation. Encoding
binds a memory to the context-at-encoding-time; retrieval is most
effective when the current context resembles the encoding context.
This is Tulving's "encoding specificity principle" (1973) given a
mathematical form.

The drift equation is a single one-line:

    context_t = ρ · context_{t-1} + (1 - ρ) · obs_emb_t

Tuning:
  - ρ = 0.85 (default): empirical sweet spot from cognitive lit;
    the context retains ~5 recent observations effectively.
  - ρ = 1.0: frozen — context never moves (bypass).
  - ρ = 0.0: fully reactive — context = latest observation.

For HippoAgent, the wake loop streams every observation through one
of these engines. At episode-store time, the current context vector
is saved alongside the episode (FORGIA-grade: this primitive is
ready, the cabling is a separate pezzo). At recall, the caller can
combine cosine(query, summary) with cosine(current_context,
ep.context) to bias retrieval toward episodes encoded in similar
contexts — Tulving's specificity in code.

What this is NOT:
  - It's not a replacement for `salience_score` or `recency_weight`
    — context is orthogonal: it indexes BY WHAT WAS HAPPENING AROUND
    THE EPISODE, not by what the episode IS.
  - It's not stored on disk by default; the engine is process-state.
    Persistence would require a separate ContextStore (out of scope).
"""
from __future__ import annotations

import numpy as np


class ContextEngine:
    """Drifting context vector — a one-state object you observe into.

    Thread-safety note: not thread-safe by design. The wake loop is
    single-threaded and the engine drift is sequential by construction.
    Cross-thread access would require external locking.
    """

    def __init__(self, *, dim: int, rho: float = 0.85) -> None:
        if not (0.0 <= rho <= 1.0):
            raise ValueError(
                f"rho must be in [0, 1]; got {rho}"
            )
        if dim <= 0:
            raise ValueError(f"dim must be positive; got {dim}")
        self._dim = int(dim)
        self._rho = float(rho)
        # Initial state: zero vector. The first observation thus
        # produces a context = (1-ρ) · obs, which converges quickly to
        # the running drift. We don't seed with random because that
        # would inject noise into a real signal-tracking task.
        self._state = np.zeros(self._dim, dtype=np.float32)

    @property
    def state(self) -> np.ndarray:
        """The current context vector. Returned as a fresh copy so the
        caller can mutate without affecting the engine state."""
        return self._state.copy()

    @property
    def rho(self) -> float:
        return self._rho

    @property
    def dim(self) -> int:
        return self._dim

    def observe(self, obs: np.ndarray) -> np.ndarray:
        """Apply the drift step: `c_t = ρ·c_{t-1} + (1-ρ)·obs`.

        Returns the post-update state (a fresh copy). Defensive on
        dimension — a mis-sized observation raises rather than
        silently corrupting the context.
        """
        obs_arr = np.asarray(obs, dtype=np.float32)
        if obs_arr.shape != (self._dim,):
            raise ValueError(
                f"observation dim {obs_arr.shape} doesn't match "
                f"engine dim ({self._dim},)"
            )
        self._state = self._rho * self._state + (1.0 - self._rho) * obs_arr
        return self.state

    def reset(self) -> None:
        """Snap the context back to the zero state. Useful at task
        boundaries (a new task is a new context regime)."""
        self._state = np.zeros(self._dim, dtype=np.float32)


__all__ = ["ContextEngine"]
