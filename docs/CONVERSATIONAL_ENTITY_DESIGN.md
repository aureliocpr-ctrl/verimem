# Conversational entity extraction — design note

Status: **design only** (2026-07-08). Nothing here is implemented. This note
exists so the next graph iteration starts from tonight's measurements
instead of re-deriving them.

## The measured problem

The entity-KG + PPR retrieval signal is real but starved on conversational
corpora. On the HaluMem e2e store (1,261 facts from dialogue):

- `extract_entities_lite` (regex, tuned for TECHNICAL text: paths, snake_case,
  SHAs, acronyms, CamelCase) yields **49 entities** — and the user entity
  links 1,258/1,259 facts, so PPR seeded there ranks ~uniformly (measured:
  fusion at k=12 EVICTED good dense hits; fixed by the hub-guard +
  dense-floor in `27f10cc`).
- The graph never contributes on the questions where a graph should shine
  (Multi-hop 0.39–0.50): the hop entities ("Albi B&B" as a place, "guest
  services" as an activity, "Sarah" as a companion) are either missing or
  hub-adjacent noise.

Conclusion tonight was to *guard* the weak signal. This note is the plan to
*strengthen* it.

## What a conversational extractor must produce

Typed entities with RELATIONS, not just names:

| type | examples | why it discriminates |
|---|---|---|
| person (non-user) | "Sarah", "Michael Rodriguez" | companions/colleagues split the hub |
| place | "Albi", "Japan", "the B&B" | trips/moves are multi-hop backbones |
| organization | "Albi B&B", "the tourism board" | career/business questions |
| activity/service | "personalized tours", "yoga class" | strategy/habit questions |
| artifact/possession | "the espresso machine", "EDM playlist" | preference questions |
| event | "the layoff", "the promotion" | temporal anchors for transitions |

Relations worth an edge (subject is usually the user): `visited(place)`,
`with(person)`, `works_at(org)`, `offers(service)`, `owns(artifact)`,
`happened(event, date)`. Even 6 relation types would turn the current
star-graph (everything→user) into a graph with PATHS — which is what PPR
actually needs.

## Three candidate tiers (build in this order)

1. **Lite-v2 (regex+POS, zero LLM)** — extend the current extractor with
   conversational patterns: proper-noun pairs after prepositions ("with
   Sarah", "in Japan"), determiner+noun chunks for services/artifacts, event
   nouns from a closed list (promotion, layoff, move, wedding...). Cheap,
   deterministic, testable. Expected: 49 → 150-250 entities on the same
   store. Risk: noise — mitigate with the existing hub-guard + per-fact cap.
2. **Extraction-time piggyback (zero EXTRA LLM calls)** — the atomic fact
   extractor already reads every turn with an LLM; ask it for typed entities
   in the SAME call (one more JSON field). Cost stays flat; quality jumps.
   This is the likely winner — measure against tier 1 before committing.
3. **Dedicated NER/RE pass (opt-in)** — only if 1-2 measurably cap out.

## Measurement plan (when a claude-p slot is free)

Zero-LLM first: rebuild the entity KG on the existing u1 store with tier 1,
report (a) entity count and degree distribution (hub share must DROP), (b)
evidence-coverage delta on the 10 Multi-hop wrong questions with fusion ON
at k=12 (the proxy harness from tonight is reusable). Only if coverage moves
→ paired answer micro-bench (correct AND wrong sets — method lesson from
tonight) → e2e.

## Explicit non-goals

- No LLM-per-query entity extraction (latency + cost on the hot path).
- No graph features that bypass the trust gate: promoted edges cite the
  fact they came from, like everything else.
