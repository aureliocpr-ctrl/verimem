"""Cycle 389 (2026-05-23) — RESONATOR NETWORKS B4 NUCLEAR v2 memory.

POST-CYCLE-388 cross-LLM REVELATION (agy Gemini 3.1):
  "VSA/HRR cleanup memory archivia solo vettori BASE non proposizioni
  complesse. Resonator Networks (Frady/Kent/Olshausen/Sommer 2020
  NeurIPS) fattorizzano M dinamicamente con SOLO alphabet base small
  → database-less raggiungibile via factorization, NON per-fact lookup."

Cycle 388 ha FALSIFIED tesi naive (filler-text cleanup pool). Cycle 389
implementa la versione che NON usa per-fact storage:

ARCHITETTURA:
  - Alphabet codebook = K roles × M atoms × D-dim vectors (FIXED, shared)
    Default: K=3 roles (S,V,O), M=512 atoms each, D=4096
    Storage: 3 × 512 × 4096 × 4B = 24MB ONE-SHOT (shared)
  - Aggregate M ∈ R^D = single vector
    Per write: M += S[s_idx] ⊛ V[v_idx] ⊛ O[o_idx]
    Storage cost per fact: ZERO marginal bytes!
  - Recall via Resonator dynamics convergence (Frady 2020):
    Initialize estimates s_hat, v_hat, o_hat random unit
    Iterate: s_hat ← clean_S(unbind(unbind(M, v_hat), o_hat))
             where clean_S(x) = arg max_atom inner(atom, x), then proj
    Converge in O(few iterations) per recall
  - Storage TOTAL: 24MB shared codebook + 16KB aggregate = 24MB for ALL facts

A3 honest scope:
  - NOT zero storage absolute: codebook IS fixed memory (24MB)
  - BUT amortized: 1 fact OR 10000 facts → same 24MB total
  - Compared SQLite: 24MB == 30000 facts in HippoAgent semantic.db
  - Capacity bound from Frady 2020: ~M^K / sqrt(D) discrete compositions
    At K=3, M=512, D=4096: 134M / 64 = 2M compositions (theoretical max)

Falsifiable contracts (vedi tests/test_resonator_memory.py):
  (a) recall@1(N=1000) ≥ 0.5 WITHOUT per-fact cleanup pool
      → FALSIFIES the cycle 388 lesson if PASSES
  (b) storage(N=1000) = storage(N=100) = 24MB (codebook constant)
  (c) factorize converges in <20 iterations p99 for N ≤ capacity
  (d) over capacity (N >> capacity): recall degrades sharply (cliff)

IMPORTANT NLP MAPPING:
  Real propositions (free text) need encoding into (s_idx, v_idx, o_idx).
  Easy mode: structured key=value tuples. Hard mode: NLP parser.
  This prototype: structured tuple input. NLP is orthogonal layer.

API:
  ResonatorMemory(n_roles=3, atoms_per_role=512, d=4096)
  .remember_tuple((s_idx, v_idx, o_idx)) → bind + add to aggregate
  .recall_tuple(query_hint=None, n_iter=50) → factorize, return (s,v,o)
  .alphabet_atom(role, idx) → vector
  .stats() → storage_bytes, n_facts, codebook_norm, ...
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

D_DEFAULT = 4096  # Resonator paper says D=2048-4096 sweet spot
N_ROLES_DEFAULT = 3
ATOMS_PER_ROLE_DEFAULT = 512
RESONATOR_MAX_ITER = 50
RESONATOR_CONV_THRESHOLD = 1e-4
ALPHABET_SEED_BASE = 0xA1B2C3D4


def _circular_conv(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular convolution via FFT (binding)."""
    return np.real(np.fft.ifft(np.fft.fft(a) * np.fft.fft(b))).astype(np.float32)


def _circular_corr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular correlation via FFT (unbinding, approx inverse of conv)."""
    return np.real(np.fft.ifft(
        np.conj(np.fft.fft(a)) * np.fft.fft(b)
    )).astype(np.float32)


def _build_alphabet(
    n_roles: int, atoms_per_role: int, d: int,
    seed: int = ALPHABET_SEED_BASE,
) -> list[np.ndarray]:
    """Generate K random orthonormal-ish codebook matrices.

    Returns: list of K matrices, each shape (M_atoms, D).
    Each row = unit-norm random gaussian vector.
    """
    codebooks = []
    for role in range(n_roles):
        rng = np.random.default_rng(seed + role * 0x10001)
        M = rng.standard_normal((atoms_per_role, d)).astype(np.float32)
        # Normalize rows
        norms = np.linalg.norm(M, axis=1, keepdims=True)
        M /= np.maximum(norms, 1e-9)
        codebooks.append(M)
    return codebooks


def _project_to_codebook(
    x: np.ndarray, codebook: np.ndarray,
) -> tuple[int, np.ndarray, float]:
    """Project x onto codebook (M, D) HARD argmax. Returns (best_idx, atom_vec, score)."""
    scores = codebook @ x  # (M,)
    best = int(np.argmax(scores))
    return best, codebook[best], float(scores[best])


def _soft_project_to_codebook(
    x: np.ndarray, codebook: np.ndarray, beta: float = 8.0,
) -> tuple[int, np.ndarray, float]:
    """Cycle 390 SOFT cleanup: softmax weighted combination over atoms.

    Returns (argmax_idx, soft_combined_vec, top_score).
    Used during iteration to allow gradient-like exploration.
    Hard argmax only at convergence/return.
    """
    scores = codebook @ x  # (M,)
    s = scores - scores.max()
    probs = np.exp(beta * s).astype(np.float32)
    probs /= probs.sum()
    soft = (probs @ codebook).astype(np.float32)
    # Normalize soft vec
    n = float(np.linalg.norm(soft))
    if n > 1e-9:
        soft = soft / n
    best = int(np.argmax(scores))
    return best, soft, float(scores[best])


def _residual_norm(
    aggregate: np.ndarray,
    indices: tuple[int, ...],
    codebooks: list[np.ndarray],
) -> float:
    """||aggregate - bind(atoms)||_2. Lower = better match."""
    atoms = [codebooks[r][i] for r, i in enumerate(indices)]
    bound = atoms[0]
    for a in atoms[1:]:
        bound = _circular_conv(bound, a)
    return float(np.linalg.norm(aggregate - bound))


@dataclass
class ResonatorMemory:
    """Database-less memory via Resonator Networks (Frady et al 2020).

    Storage: single aggregate vector + fixed codebook. No per-fact bytes.
    """
    n_roles: int = N_ROLES_DEFAULT
    atoms_per_role: int = ATOMS_PER_ROLE_DEFAULT
    d: int = D_DEFAULT
    aggregate: np.ndarray = field(default=None)  # type: ignore[assignment]
    codebooks: list[np.ndarray] = field(default_factory=list)
    n_facts: int = 0
    seed: int = ALPHABET_SEED_BASE

    def __post_init__(self) -> None:
        if self.aggregate is None:
            self.aggregate = np.zeros(self.d, dtype=np.float32)
        if not self.codebooks:
            self.codebooks = _build_alphabet(
                self.n_roles, self.atoms_per_role, self.d, self.seed,
            )

    # ---------------- WRITE PATH ----------------
    def remember_tuple(self, indices: tuple[int, ...]) -> dict[str, Any]:
        """Store tuple (idx_0, idx_1, ..., idx_{K-1}).

        Binding: bound = atoms[0] ⊛ atoms[1] ⊛ ... ⊛ atoms[K-1]
        aggregate += bound
        """
        if len(indices) != self.n_roles:
            raise ValueError(
                f"expected {self.n_roles} indices, got {len(indices)}"
            )
        for role, idx in enumerate(indices):
            if not (0 <= idx < self.atoms_per_role):
                raise ValueError(
                    f"role {role} idx {idx} out of range "
                    f"[0,{self.atoms_per_role})"
                )
        atoms = [self.codebooks[r][i] for r, i in enumerate(indices)]
        bound = atoms[0]
        for atom in atoms[1:]:
            bound = _circular_conv(bound, atom)
        self.aggregate = self.aggregate + bound
        self.n_facts += 1
        return {
            "ok": True,
            "indices": indices,
            "n_facts": self.n_facts,
            "aggregate_norm": float(np.linalg.norm(self.aggregate)),
        }

    # ---------------- READ PATH (factorize) ----------------
    def recall_tuple_multi_restart(
        self,
        n_restarts: int = 16,
        n_iter: int = RESONATOR_MAX_ITER,
        hint_indices: tuple[int | None, ...] | None = None,
        beta: float = 8.0,
        target_indices: tuple[int, ...] | None = None,
    ) -> dict[str, Any]:
        """Cycle 390 SOFT Resonator + multi-restart factorize.

        Runs `n_restarts` independent factorizations with random seeds
        and SOFT cleanup, returns the one with lowest residual.

        target_indices (optional): if provided, returns the FIRST restart
        that matched target — useful for benchmarks of pure resonator
        capability (does ANY restart find truth?).

        Returns dict with: indices, best_residual, attempted, found.
        """
        best: dict[str, Any] | None = None
        for restart_i in range(n_restarts):
            r = self.recall_tuple(
                n_iter=n_iter, seed=restart_i,
                hint_indices=hint_indices, soft=True, beta=beta,
            )
            res = _residual_norm(self.aggregate, r["indices"], self.codebooks)
            r["residual"] = res
            r["restart"] = restart_i
            if target_indices is not None and r["indices"] == target_indices:
                return {**r, "found_match": True, "n_restarts": restart_i + 1}
            if best is None or res < best["residual"]:
                best = r
        if best is None:
            best = {"ok": False, "indices": tuple([0] * self.n_roles)}
        return {**best, "found_match": False, "n_restarts": n_restarts}

    def recall_all_via_matching_pursuit(
        self,
        max_facts: int = 100,
        residual_threshold: float = 0.5,
        n_restarts_per_pass: int = 32,  # cycle 395: bumped 16→32, eliminates catastrophic
        n_iter: int = RESONATOR_MAX_ITER,
    ) -> dict[str, Any]:
        """Cycle 391 — Matching Pursuit (Mallat 1993) + Resonator.

        Iteratively factorize aggregate by:
          1. Find best (s, v, o) via soft+multi-restart resonator
          2. Subtract bound(found) from working residual
          3. Repeat until residual_norm < threshold OR max_facts reached

        Closes cycle 389/390 xfail by finding facts WITHOUT hint via
        iterative removal. Inspired by Frady 2020 §3.2 lateral inhibition.

        Returns:
            {found: list[indices], residuals: list[float], n_passes: int}
        """
        original_aggregate = self.aggregate.copy()
        try:
            found_facts: list[tuple[int, ...]] = []
            residuals_trail: list[float] = []
            seen_indices: set[tuple[int, ...]] = set()
            consecutive_fail = 0
            max_consecutive_fail = 3
            for pass_i in range(max_facts):
                # Run multi-restart on current residual
                r = self.recall_tuple_multi_restart(
                    n_restarts=n_restarts_per_pass, n_iter=n_iter,
                )
                indices = r["indices"]
                # Skip if we already accepted this composition
                if indices in seen_indices:
                    consecutive_fail += 1
                    if consecutive_fail >= max_consecutive_fail:
                        break
                    continue
                # Compute bound vector of found composition
                atoms = [self.codebooks[role][idx]
                         for role, idx in enumerate(indices)]
                bound = atoms[0]
                for a in atoms[1:]:
                    bound = _circular_conv(bound, a)
                # Subtract bound from working aggregate (lateral inhibition)
                new_aggregate = self.aggregate - bound
                # Compute residual norms
                pre_norm = float(np.linalg.norm(self.aggregate))
                post_norm = float(np.linalg.norm(new_aggregate))
                if post_norm >= pre_norm - 1e-6:
                    # No progress — skip but don't auto-stop
                    consecutive_fail += 1
                    if consecutive_fail >= max_consecutive_fail:
                        break
                    continue
                # Accept
                found_facts.append(indices)
                seen_indices.add(indices)
                residuals_trail.append(post_norm)
                self.aggregate = new_aggregate
                consecutive_fail = 0
                if post_norm < residual_threshold:
                    break
            return {
                "ok": True,
                "found_facts": found_facts,
                "residuals_trail": residuals_trail,
                "n_passes": len(found_facts),
                "final_residual_norm": (
                    residuals_trail[-1] if residuals_trail else None
                ),
            }
        finally:
            # Restore aggregate (matching pursuit is non-destructive)
            self.aggregate = original_aggregate

    def recall_tuple(
        self,
        n_iter: int = RESONATOR_MAX_ITER,
        seed: int = 0,
        hint_indices: tuple[int | None, ...] | None = None,
        soft: bool = False,
        beta: float = 8.0,
    ) -> dict[str, Any]:
        """Factorize aggregate via Resonator dynamics.

        Algorithm (Frady et al 2020):
          1. Initialize estimates x_r ∈ R^D random unit (or hint atom)
          2. For iter in [0, n_iter):
             For each role r:
               others = circular_conv of all x_{r'} for r' != r
               x_r_noisy = circular_corr(others, aggregate)
               x_r_new = clean(x_r_noisy, codebook_r)
             If converged: break
          3. Return tuple of indices.

        Hint: if hint_indices[r] is given, initialize x_r to that atom
        (useful for partial-query recall).
        """
        rng = np.random.default_rng(seed)
        K = self.n_roles
        # Initialize x_r
        x = []
        for r in range(K):
            if hint_indices and hint_indices[r] is not None:
                x.append(self.codebooks[r][hint_indices[r]].copy())
            else:
                v = rng.standard_normal(self.d).astype(np.float32)
                v /= max(float(np.linalg.norm(v)), 1e-9)
                x.append(v)

        # Roles that have hint must NOT be updated (frozen at hint atom)
        frozen_roles = set()
        if hint_indices:
            for r, h in enumerate(hint_indices):
                if h is not None:
                    frozen_roles.add(r)

        # Precompute hint indices to keep in final result
        hint_idx_map: dict[int, int] = {}
        if hint_indices:
            for r, h in enumerate(hint_indices):
                if h is not None:
                    hint_idx_map[r] = h

        prev_indices: tuple[int, ...] | None = None
        iters_done = 0
        for it in range(n_iter):
            iters_done = it + 1
            new_indices_list = []
            for r in range(K):
                if r in frozen_roles:
                    # Hint role: keep frozen, no update
                    new_indices_list.append(hint_idx_map[r])
                    continue
                # others = product of all x_{r'} for r' != r
                others = None
                for r2 in range(K):
                    if r2 == r:
                        continue
                    if others is None:
                        others = x[r2].copy()
                    else:
                        others = _circular_conv(others, x[r2])
                # Unbind from aggregate
                noisy = _circular_corr(others, self.aggregate)  # type: ignore[arg-type]
                # Clean: soft (cycle 390) or hard projection
                if soft:
                    idx, atom, _score = _soft_project_to_codebook(
                        noisy, self.codebooks[r], beta=beta,
                    )
                else:
                    idx, atom, _score = _project_to_codebook(
                        noisy, self.codebooks[r],
                    )
                x[r] = atom
                new_indices_list.append(idx)
            new_indices = tuple(new_indices_list)
            if new_indices == prev_indices:
                break
            prev_indices = new_indices
        return {
            "ok": True,
            "indices": prev_indices or tuple([0] * K),
            "iters": iters_done,
            "converged": iters_done < n_iter,
        }

    # ---------------- INTROSPECTION ----------------
    def stats(self) -> dict[str, Any]:
        codebook_bytes = sum(c.nbytes for c in self.codebooks)
        return {
            "n_roles": self.n_roles,
            "atoms_per_role": self.atoms_per_role,
            "d": self.d,
            "n_facts": self.n_facts,
            "aggregate_size_bytes": int(self.aggregate.nbytes),
            "codebook_size_bytes": int(codebook_bytes),
            "total_storage_bytes": (
                int(self.aggregate.nbytes) + int(codebook_bytes)
            ),
            "aggregate_norm": float(np.linalg.norm(self.aggregate)),
            "theoretical_capacity_compositions": (
                self.atoms_per_role ** self.n_roles
            ),
        }

    # ---------------- PERSIST ----------------
    def save(self, path: Path | str) -> dict[str, Any]:
        """Save aggregate to .npz (codebook re-derived from seed).

        Cycle 400 fix: avoid double-suffix .npz.npz on Windows. We force
        np.savez to use the EXACT requested path by passing a file handle.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # Open file ourselves to avoid numpy's .npz auto-suffix
        with open(p, "wb") as f:
            np.savez(
                f,
                aggregate=self.aggregate,
                n_roles=np.array(self.n_roles),
                atoms_per_role=np.array(self.atoms_per_role),
                d=np.array(self.d),
                n_facts=np.array(self.n_facts),
                seed=np.array(self.seed),
            )
        return {
            "ok": True,
            "bytes_written": p.stat().st_size,
            "path": str(p),
            "note": "codebook NOT saved; rebuilt from seed on load",
        }

    @classmethod
    def load(cls, path: Path | str) -> ResonatorMemory:
        """Reload aggregate; rebuild codebook from seed.

        Cycle 400 fix: try exact path first; fallback to .npz-suffixed
        version for backward compat with old saves that double-suffixed.
        """
        p = Path(path)
        if not p.exists():
            alt = Path(str(p) + ".npz")
            if alt.exists():
                p = alt
        data = np.load(p)
        n_roles = int(data["n_roles"])
        atoms_per_role = int(data["atoms_per_role"])
        d = int(data["d"])
        n_facts = int(data["n_facts"])
        seed = int(data["seed"])
        aggregate = data["aggregate"].astype(np.float32)
        return cls(
            n_roles=n_roles, atoms_per_role=atoms_per_role,
            d=d, aggregate=aggregate, n_facts=n_facts, seed=seed,
        )


# ---------------- TEXT-TO-INDICES HELPER ----------------
def text_to_indices(
    text: str, n_roles: int, atoms_per_role: int,
) -> tuple[int, ...]:
    """Deterministic mapping: text → (idx_0, ..., idx_{K-1}).

    Uses SHA-256 hash sliced into K chunks. Each chunk mod atoms_per_role.
    Practical bridge for free-text propositions → indexed encoding.
    Reversible only via brute force (one-way).

    For real apps: replace with embedding-based NN projection.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    indices = []
    bytes_per_role = max(len(h) // n_roles, 4)
    for r in range(n_roles):
        chunk = h[r * bytes_per_role:(r + 1) * bytes_per_role]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\x00")
        v = int.from_bytes(chunk[:4], "big")
        indices.append(v % atoms_per_role)
    return tuple(indices)
