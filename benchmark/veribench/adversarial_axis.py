"""VeriBench adversarial-trust axis — the capstone: robustness needs TWO channels.

Vivarium's load-bearing result (RQ1 + complementarity): a trusted memory faces two
attacks that NO single channel survives:

  * COLLUSION / manufactured consensus — k copies of one feed (mirrors, aggregators,
    colluders with distinct IDs) assert a FALSE value. Defeated ONLY by counting
    INDEPENDENT corroboration (copies collapse to one witness); a naive source-count
    is fooled. The outcome channel is blind here — the lie has not yet failed in use.
  * TRUSTED SLEEPER — a source earns real, independent corroboration on witnessed
    items, then lies where unwitnessed. Its consistency is genuinely high, so the
    consistency channel trusts the lie. Defeated ONLY by the OUTCOME channel (the lie
    failed in use → the source is demoted).

So each channel covers the OTHER's named hole; ``trust = min(channels)`` is the only
policy net-positive across both attacks. This axis turns that into a NUMBER, and it
does so by driving the REAL ``engram.source_trust.SourceTrustBook`` (the shipped
independence clustering + two channels) — not a toy. Legit items with real
corroboration are mixed in so that "always abstain" cannot win.

Determinism: no rng needed — the scenarios are constructed, not sampled.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from engram.source_trust import SourceTrustBook

from .axes import ProbeItem, run_axis
from .scoring import scorecard

TRUE, FALSE = "true-value", "false-value"

# Trust thresholds for the reputation policies (arms). θ_c on the consistency
# channel, θ_o on the outcome channel. Neutral (0.5) does NOT clear θ_c: an
# un-corroborated source is not trusted on reputation alone.
_THETA_C = 0.6
_THETA_O = 0.5


@dataclass
class _Scenario:
    """The reputation state at the moment the store must accept-or-abstain a claim."""

    kind: str                         # "collusion" | "sleeper" | "legit"
    claim: str                        # value accepted if the claimant is trusted
    claimant: str                     # primary source of the claim
    corroborators: list[str] = field(default_factory=list)
    book: SourceTrustBook = field(default_factory=SourceTrustBook)


def _collusion(i: int) -> _Scenario:
    """k copies of one feed assert FALSE with identical report vectors. Their mutual
    confirmation is independence-REJECTED at build (one cluster), so they never earn
    consistency — exactly the manufactured-consensus attack the write-gate now sees."""
    book = SourceTrustBook()
    liars = [f"c{i}L{j}" for j in range(3)]
    vec = {f"c{i}k{n}": "x" for n in range(3)}          # identical -> copies
    for s in liars:
        for k, v in vec.items():
            book.record_report(s, k, v)
    book.observe_confirmation(liars, require_independent=True)   # 1 cluster -> rejected
    return _Scenario("collusion", FALSE, liars[0], liars, book)


def _sleeper(i: int) -> _Scenario:
    """A source earns REAL independent corroboration on witnessed items (its confirms
    are credited — it is not a copy of its partners), then lies where unwitnessed and
    the lie has FAILED in use (a bad outcome). High consistency, low outcome."""
    book = SourceTrustBook()
    s = f"s{i}"
    partners = [f"s{i}p{j}" for j in range(2)]
    for r in range(4):                                  # 4 independent corroborations
        p = partners[r % 2]
        book.record_report(s, f"s{i}w{r}", "t")
        book.record_report(p, f"s{i}w{r}", "t")         # <3 shared keys -> independent
        book.observe_confirmation([s, p], require_independent=True)
    book.observe_outcome(s, good=False, weight=1.0)     # the unwitnessed lie failed
    return _Scenario("sleeper", FALSE, s, [s], book)


def _legit(i: int) -> _Scenario:
    """Two genuinely independent honest sources corroborate TRUE and it succeeded in
    use — the item that punishes a store for abstaining indiscriminately."""
    book = SourceTrustBook()
    a, b = f"g{i}a", f"g{i}b"
    book.record_report(a, f"g{i}ka", "t")
    book.record_report(b, f"g{i}kb", "t")               # disjoint keys -> independent
    book.observe_confirmation([a, b], require_independent=True)
    book.observe_outcome(a, good=True)
    return _Scenario("legit", TRUE, a, [a, b], book)


def build_adversarial_probes(n_each: int = 20) -> tuple[list[ProbeItem],
                                                        dict[str, _Scenario]]:
    """``n_each`` of collusion / sleeper / legit. Every item's gold is the TRUE value:
    accepting the malicious FALSE claim scores WRONG, abstaining scores ABSTAIN,
    recovering TRUE scores CORRECT."""
    items: list[ProbeItem] = []
    by_q: dict[str, _Scenario] = {}
    for kind, make in (("collusion", _collusion), ("sleeper", _sleeper),
                       ("legit", _legit)):
        for i in range(n_each):
            scn = make(i)
            q = f"adv/{kind}#{i}: accept the claimed value?"
            items.append(ProbeItem(q, gold=TRUE))
            by_q[q] = scn
    return items, by_q


# ---- the four trust policies (arms) ------------------------------------------

def _corroborated_naive(scn: _Scenario) -> bool:
    return len({s for s in scn.corroborators if s}) >= 2          # source COUNT


def _corroborated_independent(scn: _Scenario) -> bool:
    if scn.book.independent_clusters(scn.corroborators) >= 2:     # real corroboration
        return True
    return scn.book.consistency(scn.claimant) >= _THETA_C         # or earned reputation


def make_naive_arm(by_q: dict[str, _Scenario]) -> Callable[[str], str | None]:
    """Corroboration by COUNT, no outcome — fooled by collusion."""
    def fn(q: str) -> str | None:
        scn = by_q[q]
        return scn.claim if _corroborated_naive(scn) else None
    return fn


def make_consistency_arm(by_q: dict[str, _Scenario]) -> Callable[[str], str | None]:
    """Independence-aware corroboration, but NO outcome — fooled by the sleeper."""
    def fn(q: str) -> str | None:
        scn = by_q[q]
        return scn.claim if _corroborated_independent(scn) else None
    return fn


def make_both_arm(by_q: dict[str, _Scenario]) -> Callable[[str], str | None]:
    """min(independence-aware consistency, outcome) — the only arm robust to both."""
    def fn(q: str) -> str | None:
        scn = by_q[q]
        if not _corroborated_independent(scn):
            return None
        if scn.book.outcome(scn.claimant) < _THETA_O:
            return None
        return scn.claim
    return fn


ARMS = {"naive_count": make_naive_arm,
        "consistency_only": make_consistency_arm,
        "min_both": make_both_arm}


def run_adversarial_axis(n_each: int = 20, lambdas=(1.0, 2.0, 5.0)) -> dict:
    """Score every arm on the same collusion+sleeper+legit stream. Returns each arm's
    scorecard; ``min_both`` is the only one net-positive at λ>1 (the capstone)."""
    items, by_q = build_adversarial_probes(n_each)
    out = {}
    for name, make in ARMS.items():
        outcomes = run_axis(items, make(by_q))
        out[name] = scorecard(outcomes, lambdas=lambdas)
    return out


def main() -> None:
    r = run_adversarial_axis()
    print("VeriBench adversarial-trust axis — collusion + sleeper (real SourceTrustBook)\n")
    print(f"{'arm':<18}{'correct':>8}{'wrong':>7}{'abstain':>9}{'NET λ=5':>10}")
    for name, sc in r.items():
        print(f"{name:<18}{sc['correct']:>8}{sc['wrong']:>7}{sc['abstain']:>9}"
              f"{sc['net']['lambda_5']:>10}")
    print("\nnaive_count fooled by collusion; consistency_only fooled by the sleeper;")
    print("only min_both (two channels) is net-positive across both attacks.")


if __name__ == "__main__":
    main()
