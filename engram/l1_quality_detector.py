"""L1.21 — unsupported quality-superlative / sycophancy detector (2026-07-10).

The red-team corpus surfaced a class the keyword family missed and the L1.20
embedding let slip when a flattery prefix diluted it: absolute quality
superlatives asserted about our own system without evidence — "the pipeline
is perfect and bug-free", "flawless and bulletproof", "100% reliable". These
are the sycophancy/overclaim vector (often opening with "as you correctly
said…"), and a deterministic net is the right backstop for a fuzzy embedding.

Precision-first. Two tiers:
  * STRONG compounds are overclaims on their own — they have no benign
    software reading: flawless, bug-free, bulletproof, rock-solid, impeccable,
    "zero bugs", "no bugs", "100% reliable", "never fails".
  * "perfect" is ambiguous ("the perfect time to migrate") so it fires ONLY
    when it qualifies a system noun within a short window
    (perfect + system/pipeline/code/deploy/release/build/feature/app/…).

Evidence-disarmed like every L1 detector: a runtime/test/bench ref clears it.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# strong overclaims — no benign software reading, fire on their own
_STRONG = re.compile(
    r"\b(?:flawless|bug[-\s]?free|bullet[-\s]?proof|rock[-\s]?solid|"
    r"impeccable|fault[-\s]?less|"
    r"zero\s+bugs?|no\s+bugs?|100\s*%\s*reliable|never\s+fails?)\b",
    re.IGNORECASE,
)

# "perfect" only when it qualifies a system noun (either order, short window)
_SYS_NOUN = (r"system|pipeline|code|codebase|deploy(?:ment)?|release|build|"
             r"feature|app|application|service|module|platform|product|"
             r"implementation|integration")
_PERFECT_SYS = re.compile(
    r"\bperfect\b(?:\s+\w+){0,3}\s+(?:" + _SYS_NOUN + r")\b"
    r"|(?:" + _SYS_NOUN + r")\b(?:\s+\w+){0,4}\s+(?:is|are|was|were|looks?|"
    r"seems?)\s+(?:\w+\s+){0,2}perfect\b",
    re.IGNORECASE,
)

_RUNTIME_EVIDENCE = (
    "pytest:", "test:", "bash:", "cmd:", "smoke:", "runtime:", "ci:",
    "smoke_test:", "bench:", "measure:", "coverage:", "audit:", "file:",
)
_OUTCOME = frozenset({"pass", "passed", "passing", "ok", "green", "exit0"})


@dataclass(frozen=True)
class QualityClaimWarning:
    matched_text: str
    advice: str


def _has_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        low = ref.lower()
        if low.startswith(("pytest:", "bash:", "cmd:", "test:")) and any(
            tok in _OUTCOME for tok in re.split(r"[^a-z0-9]+", low)
        ):
            return True
        if any(low.startswith(p) for p in _RUNTIME_EVIDENCE):
            return True
    return False


def detect_unsupported_quality_claim(
    *, proposition: str, verified_by: Iterable[str] | None,
) -> QualityClaimWarning | None:
    """Warn on an unsupported quality superlative; else None."""
    if not proposition:
        return None
    m = _STRONG.search(proposition) or _PERFECT_SYS.search(proposition)
    if m is None:
        return None
    if _has_evidence(verified_by):
        return None
    return QualityClaimWarning(
        matched_text=m.group(0),
        advice=(
            f"Quality superlative {m.group(0)!r} asserts perfection without "
            f"evidence. Back it with a test/bench/audit ref (pytest:_PASS, "
            f"bench:, audit:) or state it as a goal, not an achieved fact."
        ),
    )


__all__ = ["QualityClaimWarning", "detect_unsupported_quality_claim"]
