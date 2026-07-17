"""Single source of truth for machine-state / telemetry topic prefixes.

A fact whose topic starts with one of these is serialized machine state (event
bus traffic, metrics, locks, market/cache/citation simulation blobs, agent
diary exhaust, …), NOT curated natural-language knowledge. Two layers consume
this list and they must NEVER drift:

  - WRITE time: ``verimem.admission_gate`` routes such a write to the telemetry
    store instead of the curated corpus (ROUTE_TELEMETRY) — it never deletes.
  - READ time: ``verimem.semantic`` hides them from a GENERIC (topic=None) recall
    (the cache fast-path SQL, the legacy SQL path, and the cold keyword
    fallback all derive their denylist from this tuple).

Before 2026-06-13 these were two hand-maintained lists (a tuple in semantic +
a regex in admission_gate) that had silently drifted: a live hippo_facts_recall
surfaced cache/ market/ citations/ blobs that semantic's recall denylist had
just been extended to hide but the admission gate still admitted. Centralising
here makes that drift structurally impossible.

This module is a LEAF: it imports nothing from ``engram`` so neither
``semantic`` nor ``admission_gate`` can create an import cycle by reading it.

NOT in this list (deliberately curated knowledge, must stay recallable):
``test/`` (canary fixtures the suite relies on), ``handoff/`` (real operator
mandates), ``bench/`` (benchmark findings), ``project/``, ``lessons/``,
``archive/``, ``decisions/``, ``preferences/``, ``emerging_skill/``.
"""
from __future__ import annotations

#: Topic prefixes treated as machine-state/telemetry. ``startswith`` semantics
#: (each entry is matched as a literal prefix, not a regex).
TELEMETRY_TOPIC_PREFIXES: tuple[str, ...] = (
    # original set (SCAN-68, 2026-06-02)
    "bus/", "metric/", "alloc/", "lock/", "tx/", "nego/", "replay/",
    "dialog/voice",
    # 2026-06-13: serialized JSON machine-state / simulation blobs that a LIVE
    # hippo_facts_recall surfaced at score ~0.82, crowding out real knowledge.
    # Per-namespace sampling (B2) confirmed all are JSON state, not NL knowledge.
    "cache/", "market/", "citations/", "obs/", "signal/",
    "dispatch/", "supervisor/", "namespace/", "diary/",
    # 2026-07-02: the real-corpus NLI truth scan surfaced 26 live dream/<id>
    # facts, all serialized scenario state ({"state": "active", ...}) that had
    # slipped past both layers because the prefix was missing.
    "dream/",
    # 2026-07-03: the first KNOWLEDGE-only scan exposed machine state nested
    # under knowledge namespaces (sampled before listing, B2): pin/<fact_id>
    # JSON pin/unpin state; skill/catalog/* auto-generated registry entries
    # ("Pre-installed Engram skill. Path: ...", 49 near-identical rows = 395
    # of 810 scan conflicts); project/recursive-mas/* MAS-worker exhaust
    # (planner/critic run output incl. raw ANSI escapes). Deliberate skills
    # knowledge (emerging_skill/, other skill/ topics) stays recallable.
    "pin/", "skill/catalog/", "project/recursive-mas/",
)

#: Fact tiers. `classify_tier` is the single source of truth consumed by the
#: truth-reconcile guard, the corpus truth scan, and any bench that must not
#: mix machine state with knowledge (the 2026-07-02 real-corpus scan showed the
#: residual NLI conflicts were telemetry near-duplicates, not knowledge).
TIER_TELEMETRY = "telemetry"
TIER_TEST = "test"
TIER_DIALOG = "dialog"
TIER_KNOWLEDGE = "knowledge"

#: Suite canaries and lab-experiment material: deliberately recallable (see the
#: NOT-in-this-list note above) but never a reconcile/scan subject.
TEST_TOPIC_PREFIXES: tuple[str, ...] = ("test/", "lab/", "project/lab/")

#: Verbatim conversation transcripts (e.g. the founding dialog/doc1-* docs):
#: curated, recallable knowledge of record — but chat turns are not factual
#: assertions, so a reconcile judge must not supersede/contest them.
DIALOG_TOPIC_PREFIX = "dialog/"


def classify_tier(topic: str | None) -> str:
    """Map a fact topic to its tier. Telemetry wins over dialog so that
    ``dialog/voice`` (machine exhaust) stays telemetry while ``dialog/doc*``
    transcripts classify as dialog."""
    t = topic or ""
    if any(t.startswith(p) for p in TELEMETRY_TOPIC_PREFIXES):
        return TIER_TELEMETRY
    if any(t.startswith(p) for p in TEST_TOPIC_PREFIXES):
        return TIER_TEST
    if t.startswith(DIALOG_TOPIC_PREFIX):
        return TIER_DIALOG
    return TIER_KNOWLEDGE


__all__ = [
    "TELEMETRY_TOPIC_PREFIXES",
    "TEST_TOPIC_PREFIXES",
    "DIALOG_TOPIC_PREFIX",
    "TIER_TELEMETRY",
    "TIER_TEST",
    "TIER_DIALOG",
    "TIER_KNOWLEDGE",
    "classify_tier",
]
