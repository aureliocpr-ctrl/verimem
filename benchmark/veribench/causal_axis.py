"""VeriBench causal / do-query axis — "provenance ≠ causality" as a measured axis.

Vivarium's deepest pre-registered NEGATIVE result (causal v10.0 / causal-latent):
honest sources can CORROBORATE a spurious correlation X~Y (a latent confounder Z
drives both), so a high-trust memory answers do(X) questions confidently — and is
WRONG, because do(X) does not move Y. Trust certifies who-said-it-and-corroborated,
NOT causally-true. This axis turns that into a NUMBER: a trust-only (floor-less)
store is confidently wrong on do-contrast probes and nets negative even at the
symmetric λ=1 — so λ=1 is a *defended* floor here, not an arbitrary pick.

CRITICAL (from wf2_causal-generalization): probes are do-CONTRAST ("does do(X=1)
differ from do(X=0)?"), NOT point-Y prediction — predicting Y cannot separate
causal from spurious (observation and intervention score identically on point-Y).

The confounded do-contrast items carry ``gold=None``: the only honest response is
to abstain (or route to an interventional-typed fact). Mixed in are
interventional-ANSWERABLE items so that "always abstain" does not trivially win.

Pure/deterministic: stdlib only, no engram, no model, no network.
"""
from __future__ import annotations

import random
from collections.abc import Callable

from .axes import ProbeItem, run_axis
from .runner import run_bench
from .scoring import crossover_lambda

SAME, DIFFER = "same", "differ"  # do-CONTRAST answer domain (NOT point-Y)


class LatentConfoundWorld:
    """Latent ``Z ~ Bernoulli(p_z)`` drives BOTH X and Y (each a noisy copy of Z).
    ``observe()`` shows X~Y (spurious correlation); ``intervene(x)`` sets X but
    leaves Y ⟂ x (Y is a fresh noisy copy of Z) — so the causal effect of X on Y is
    ZERO. Ported from vivarium/causal_latent.py."""

    def __init__(self, seed: int = 0, p_z: float = 0.7, noise: float = 0.1) -> None:
        self.rng = random.Random(seed)
        self.p_z, self.noise = p_z, noise

    def _z(self) -> int:
        return 1 if self.rng.random() < self.p_z else 0

    def _flip(self, v: int) -> int:
        return v if self.rng.random() > self.noise else 1 - v

    def observe(self) -> tuple[int, int]:
        z = self._z()
        return self._flip(z), self._flip(z)          # X, Y both copy Z -> correlated

    def intervene(self, x_set: int) -> tuple[int, int]:
        z = self._z()
        return x_set, self._flip(z)                  # Y ⟂ x_set -> do(X) has no effect


def defended_lambda(a: float) -> float:
    """λ* at which a floor-less trust-only store (accuracy ``a``, wrong ``1−a``,
    never abstains) crosses NET=0: ``a/(1−a)``. On a binary do-contrast over a
    confounded relation the store is near chance, so ``a<0.5`` → ``λ*<1``: the
    symmetric λ=1 is already a DEFENDED floor (the store is net-negative there),
    not a hand-picked constant. This is "provenance ≠ causality" as a number and
    the closed form of ``crossover_lambda`` on the trust-only arm."""
    if not 0.0 <= a < 1.0:
        raise ValueError("a must be in [0, 1)")
    return a / (1.0 - a)


def build_causal_probes(seed: int = 0, *, n_confounded: int = 40,
                        n_interventional: int = 60,
                        p_causal: float = 0.5) -> list[ProbeItem]:
    """do-CONTRAST probes. Confounded items (pure latent confounder, no
    interventional fact) carry ``gold=None`` — honest = abstain. Interventional
    items are drawn from a MIXED population (causal w.p. ``p_causal`` else spurious)
    with ``gold`` = the interventional truth, so 'always abstain' does not win."""
    rng = random.Random(seed)
    items: list[ProbeItem] = []
    for i in range(n_confounded):
        items.append(ProbeItem(f"do-contrast/conf#{i}: does do(X=1) differ from do(X=0)?",
                               gold=None))
    for i in range(n_interventional):
        causal = rng.random() < p_causal
        items.append(ProbeItem(
            f"do-contrast/int#{i}: does do(X=1) differ from do(X=0)?",
            gold=DIFFER if causal else SAME))
    return items


def make_obs_sut() -> Callable[[str], str | None]:
    """The trust-only / high-recall SUT: it has CORROBORATED the spurious X~Y
    correlation, so it answers every do-contrast with the observational verdict
    ("differ"). WRONG on every confounded item (gold=None) and right only on the
    genuinely-causal half of the answerable items → near chance → net-negative as
    λ rises. This is the failure mode the axis exists to expose."""
    def answer_fn(_query: str) -> str | None:
        return DIFFER
    return answer_fn


def make_interv_sut(golds: dict[str, str | None]) -> Callable[[str], str | None]:
    """The scope-aware reference SUT: abstains (None) on confounded do-contrasts
    and returns the interventional verdict on answerable ones. Illustrative — a
    real system earns this via an interventional-typed fact; here it reads the
    known interventional truth to show what 'good' scores like."""
    def answer_fn(query: str) -> str | None:
        return golds.get(query)
    return answer_fn


def run_causal_axis(seed: int = 0, **kw) -> dict:
    """Score both demo SUTs on the same probes; return their scorecards + the
    defended λ*. The obs SUT's ``crossover_lambda`` IS ``defended_lambda(a)`` by
    construction (self-consistency, nothing hardcoded)."""
    items = build_causal_probes(seed, **kw)
    golds = {it.query: it.gold for it in items}
    obs = run_bench(items, make_obs_sut())
    interv = run_bench(items, make_interv_sut(golds))
    lam_star = crossover_lambda(run_axis(items, make_obs_sut()))
    return {"obs_only": obs, "scope_aware": interv, "defended_lambda": lam_star}


def main() -> None:
    r = run_causal_axis()
    obs, interv, lam = r["obs_only"], r["scope_aware"], r["defended_lambda"]
    rk_obs = round(obs["correct"] / obs["n"], 3)
    rk_int = round(interv["correct"] / interv["n"], 3)
    print("VeriBench causal / do-query axis — provenance ≠ causality\n")
    print("TRUST-ONLY (corroborated the spurious correlation):")
    print(f"  recall@k(correct/n)={rk_obs}  NET λ=1={obs['net']['lambda_1']}  "
          f"NET λ=5={obs['net']['lambda_5']}")
    print("SCOPE-AWARE (abstains on confounded do-queries):")
    print(f"  recall@k(correct/n)={rk_int}  NET λ=1={interv['net']['lambda_1']}  "
          f"NET λ=5={interv['net']['lambda_5']}")
    print(f"\ndefended λ* (trust-only crosses NET=0) = {lam}  (<1 → λ=1 is a "
          f"defended floor: the trust-only store is already net-negative there).")
    print("Scope declaration: Verimem certifies who-said-it & corroborated, "
          "NOT causally-true.")


if __name__ == "__main__":
    main()
