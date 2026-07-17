"""Cycle #114 — legacy corpus cleanup (forgettable bucket only).

Cycle 110.D shipped `audit_legacy_corpus` as REPORT-ONLY (PR #48). This
module closes the loop: actually delete the legacy_unverified rows that
the classifier flags as `forgettable` (short text / very-low confidence /
TODO/FIXME/deprecated keyword in the proposition).

Design constraints (conservative on purpose):

* Only the ``forgettable`` bucket is touched. ``verified_on_rereading``
  would need the cycle #111 v2 I/O hard-gate to promote (out of scope —
  the verified_by field on legacy rows is empty, so re-extracting refs
  from the proposition is a separate piece of work).
* ``recoverable`` rows are left for human review.
* Default is ``dry_run=True``. Mutation requires explicit opt-in.
* Only rows with ``status == "legacy_unverified"`` are eligible. The
  function never touches verified / model_claim / provisional rows even
  if their text would look forgettable.

Pure orchestration on top of `legacy_audit.classify_legacy_fact` and
`semantic.SemanticMemory.delete`.
"""
from __future__ import annotations

import time
from typing import Any

from .legacy_audit import classify_legacy_fact
from .semantic import Fact, SemanticMemory

_SAMPLE_LIMIT = 5

# Cycle #114 conservative guardrails. The legacy_audit classifier
# (cycle #110.D) flags any proposition containing the words
# 'deprecated' / 'TODO' / 'FIXME' / 'placeholder' as `forgettable`,
# regardless of length or confidence. On the real corpus this catches
# 200+ char lesson-learned and session-state narratives that merely
# *mention* one of those words. Empirically those rows have
# ``confidence == 1.0`` and ``len(proposition) > 200`` — we refuse to
# delete them and let the recoverable bucket handle them.
_MIN_FORGETTABLE_LENGTH = 200       # > this many chars => keep
_MAX_FORGETTABLE_CONFIDENCE = 0.85  # > this confidence => keep


def _passes_cleanup_guardrails(f: Fact) -> bool:
    """True if the row is safe to actually delete."""
    if len(f.proposition or "") > _MIN_FORGETTABLE_LENGTH:
        return False
    if float(f.confidence) > _MAX_FORGETTABLE_CONFIDENCE:
        return False
    return True


def cleanup_forgettable(
    sm: SemanticMemory,
    *,
    dry_run: bool = True,
    max_forget: int | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Forget every ``legacy_unverified`` fact the classifier flags as
    ``forgettable``.

    Args:
        sm: live SemanticMemory.
        dry_run: when True (default) NO mutation happens; the report
            still lists what WOULD be deleted.
        max_forget: cap on the number of rows the call may delete in
            this run. ``None`` means unlimited. Useful for staged
            cleanup on a large corpus.
        now: optional epoch override (tests use a fixed clock).

    Returns:
        ``{
            "dry_run": bool,
            "forgotten": int,         # actually deleted (0 on dry_run)
            "would_forget": int,      # eligible forgettable rows seen
            "total_legacy_scanned": int,
            "samples": [{fact_id, proposition, bucket_reason}, ...],
        }``
    """
    now_ts = float(now if now is not None else time.time())

    legacy = [
        f for f in sm.all()
        if getattr(f, "status", None) == "legacy_unverified"
    ]

    forgettable = []
    skipped_by_guardrails = 0
    for f in legacy:
        cls = classify_legacy_fact(f, now=now_ts)
        if cls.bucket != "forgettable":
            continue
        if not _passes_cleanup_guardrails(f):
            skipped_by_guardrails += 1
            continue
        forgettable.append((f, cls))

    forgotten = 0
    samples: list[dict[str, Any]] = []

    for f, cls in forgettable:
        # Capture a sample before we (potentially) delete.
        if len(samples) < _SAMPLE_LIMIT:
            samples.append({
                "fact_id": f.id,
                "proposition": (
                    f.proposition[:200]
                    if len(f.proposition) > 200
                    else f.proposition
                ),
                "bucket_reason": cls.bucket_reason,
                "confidence": float(f.confidence),
            })

        if dry_run:
            continue

        if max_forget is not None and forgotten >= max_forget:
            break

        if sm.delete(f.id):
            forgotten += 1

    return {
        "dry_run": bool(dry_run),
        "forgotten": forgotten,
        "would_forget": len(forgettable),
        "skipped_by_guardrails": skipped_by_guardrails,
        "total_legacy_scanned": len(legacy),
        "samples": samples,
    }
