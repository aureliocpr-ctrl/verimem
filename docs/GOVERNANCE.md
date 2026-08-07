# Governance — seeing and reversing what the memory decides

VeriMem retires and quarantines facts on its own judgment. This manual covers
the **governance surface**: how to see every one of those decisions, how to
reverse the wrong ones, and what the numbers you read actually mean. Built and
verified 2026-08-04 (branch `ws6/control-room`); every claim here was measured
on a live store, most of them on this repository's real corpus.

---

## 1. The three ways a fact disappears

A write receipt saying `stored: true` does not mean the fact will be served.
A stored fact can be:

| State | Meaning | Visible in default recall? |
|---|---|---|
| **servable** | alive, served by search/recall | yes |
| **retired** (superseded) | replaced by a newer fact; kept for lineage | no |
| **quarantined** | blocked by the admission gate; kept, auditable | no |

The canonical *servable* predicate — use this one, everywhere:

```sql
superseded_by IS NULL AND status NOT IN ('quarantined')
```

Counting only `superseded_by IS NULL` looks like "alive" and is not: a
quarantined fact passes that filter and is still never served. This exact
confusion made a fix look done on 2026-08-04 while it only moved the loss
from one name to the other. Every counter in the governance surface ships
its formula alongside the number.

### The quartet

`written = servable + retired + quarantined` — an identity, not a hope.
Read it per topic or globally:

```bash
verimem facts retirement-log --counts            # CLI
```
```python
Memory(db).survivability(topic="lab/")           # SDK
```
```
hippo_retirement_log {"counts": true}            # MCP tool
GET /v1/retirements?counts=true                  # HTTP (Bearer key)
```

On this repository's own corpus the first ever reading was:
`written 7767 · servable 5346 · retired 1761 · quarantined 660` — 31% of
everything ever written was not servable, and no API had ever said so.

### Known blind spot: said vs written

The quartet counts what reached the store. It **cannot see** content lost
*before* the gate — measured live on `verimem import`: 3 conversations
declared imported, facts extracted from only 1, quartet green (20/20
servable). Ingest surfaces need their own counter (`messages_in →
facts_out` per conversation); until then, treat "0 rejected" on an import
as "nothing that arrived was rejected", not "everything arrived".

### Known blind spot: a field named for a verification that is not one

`last_verified_at` reads as "when this was last verified" and is not. Measured
2026-08-07 (ws5): it advances on **2762** facts — up to 87 days after the write
— and **zero** of those carry a `grounding_score`. It moves exactly where a
verdict never happened: a migration or a re-embed. A touch, not a judgement.

Two governance surfaces derived from it and were corrected: the trust dossier
computed `age_days`/`freshness` from it (990 never-verified facts read as
`live`), and `fact_payload` emitted the key only when it *differed* from
`created_at` — i.e. **only on the never-verified facts**, the signal inverted.
Both now go through `fact_contract.verifica_sostenuta`: the field counts as a
verification only when a verdict backs it.

**Still open, and not on this branch**: `semantic._fact_is_stale` uses the same
field as the age base, and it runs in the default recall view. On the real
corpus **993** servable facts clear the 45-day freshness cut *only* because of
an unbacked touch, and all 993 are unjudged.
⚠️ What the data does NOT show: judged facts being hidden — 0 of the 1306
stale-hidden ones carry a verdict. The reason is temporal, not epistemic: write
-time grounding started 2026-07-28, so the oldest judged fact is 9.6 days old.
**Falsifiable prediction**: from **2026-09-11** the first judged facts cross the
cut, and from then on the filter will hide verified facts while keeping touched
-but-never-verified ones. The mechanism is already there; the effect is not yet
in the data. Changing it is retrieval behaviour, so it belongs to the write-path
owner. A `doctor` check for it is deliberately deferred — the doctor suite
probes the local judge and takes 60-90s, and the machine was reserved.

---

## 2. Seeing retirements: the retirement log

The `quarantine_log` equivalent for supersessions. Newest first, always as
the **pair** (loser, winner) — a human judges a pair in seconds:

```bash
verimem facts retirement-log                     # table: loser → winner, reason, when, undo handle
verimem facts retirement-log --with-text         # adds both propositions (local judging)
verimem facts retirement-log --topic lab/ --reason "same-source evolution"
```

Every port: SDK `Memory.retirement_log(...)`, MCP `hippo_retirement_log`,
HTTP `GET /v1/retirements`. Fields per row: `loser_id/topic/status`,
`winner_id/topic/status`, `reason`, `superseded_at`, `reversible`,
`undo_op_id`. Network/UI feeds carry **metadata only** — propositions are
opt-in (`with_text`) for local judging.

`reversible: false` is honest but was mute, and `irreversible_because` now
splits the three cases an operator handles differently:

| value | what it means | what to do |
|---|---|---|
| `no snapshot` | the build that performed the retirement leaves no handle | look at *which code* is writing (`verimem doctor` reports branch + revision) |
| `undo window expired` | the snapshot existed; the 7-day TTL passed | nothing today — the product worked, the calendar did not |
| `already undone` | the handle was used and the fact was retired again | it is a ping-pong; hunting for an undo is hunting the wrong thing |

On the real corpus 2026-08-05: **1805 retired, 2 still reversible** — every
other row reads `no snapshot`, including the five the unattended maintenance
pass performed at 23:08, because the build that runs it does not carry the
helm. `retired_reversible` in the quartet is the size of that repair window:
"1805 retired" alone does not say whether one can be recovered or a thousand.

The handle itself is withheld when it cannot be used: an `undo_op_id` that
`undo` would refuse reads as a repair that is available.

### Where the verdict and the fate disagree

`--mismatches` (SDK `verdict_mismatches`, MCP `hippo_retirement_log
{"mismatches": true}`, HTTP `?mismatches=true`) lists three populations, and
decides nothing:

| list | what it means | real corpus 2026-08-05 |
|---|---|---|
| `judged_true_but_withheld` | the moat said the source supports it and the fact is kept out anyway | 11 (ten ≥ 99) |
| `judged_false_but_served` | the moat rejected it and the store serves it as its own | 10, down to 0.22 |
| `contested_band` | 40–70: the outcome depended on **which judge was up**, not on the text | 23, all withheld |

The band is a category of its own because the admission cut is not one number
(40 on the fallback scale, 70 on the fine-tuned one — measured by ws4): there
the disagreement is *uncertainty*, not incoherence, and merging it into the
other two would be a choice dressed as a measurement. The low cut is
deliberate, so `judged_false_but_served` is a **lower bound**: below 40 any
cut rejects.

The live twin: `flow.write` carries `withheld_despite_judge`, and the Engine
Room prints **QUARANTINED DESPITE THE JUDGE** in yellow — not red, because red
here means "the defence worked" and this line says the opposite. One
threshold serves both (`retirement_log.judged_true`); a threshold written
twice diverges.

### The live feed

Every retirement emits `flow.supersession` (loser, winner, topics, reason,
branch, `reversible`, `undo_op_id` — never text). Every undo emits
`flow.undo`. Watch them in the Engine Room (`/ui/engine`), in
`verimem flow tail`, or straight from `events.jsonl`.

---

## 3. Reversing: the helm

Every supersession snapshots the loser's row **in the same transaction** as
the retirement (`facts_undo_log`, op_type `supersede`, TTL 7 days). The
handle travels with every receipt:

- `add()` that retired something → `superseded_undo_ops: {loser_id: op_id}`
- `update()` → `undo_op_id`
- retirement-log rows → `undo_op_id`

Reverse it from any port:

```bash
verimem facts undo <op_id>        # CLI (accepts an id prefix)
```
```python
m.undo(op_id)                     # SDK
```
```
hippo_undo_destructive_op {"op_id": ...}   # MCP
POST /v1/undo/{op_id}                      # HTTP
```

**The loser comes back servable; the winner stays alive.** Both facts live —
that is the correct end state for the measured failure mode (two distinct
entities wrongly fused), and it is what the ping-pong loop (rewrite the lost
fact → another one dies → no user action escapes) needed: one action out.

Chain semantics, all bench-verified: undoing a mid-chain retirement revives
that loser next to the final winner; re-retiring after an undo issues a NEW
handle; double-undo of the same handle is `already_undone` (never a double
resurrection); a lost concurrency race deletes its orphan handle in the same
transaction (an orphan undo would have resurrected the loser behind the
concurrent winner's back).

Quarantine release is separate and per-port too: SDK `m.restore(fact_id)`,
MCP `hippo_quarantine_restore`, CLI, and HTTP `POST /v1/memories/{id}/restore`.

---

## 4. The Engine Room and the governance panel

`/ui/engine` shows the pipeline as chambers whose heat is real events. Since
the helm it also shows:

- the **SUPERSEDE chamber** (`flow.supersession` heat, `RETIRED ↺` stamp);
- the **governance panel**: retirement pairs with an *undo* button, the
  quarantine with a *restore* button — the buttons drive the real endpoints
  of this gateway, and the feed shows the effect;
- the **quartet in the header**, all six numbers the endpoint returns and not
  four: `written · servable (judged N) · retired (undoable N) · quarantined`.
  The two in brackets are the ones that answer the product's own questions —
  "is it verified?" and "can we go back?" — and the panel omitted both until
  2026-08-07. They ride as ratios on their denominator because a bare count
  says nothing, and a missing key renders `?`, never `0`;
- the **chamber map**, which declares its own blind spots instead of looking
  complete. Rows marked **LIT** carry the date their telemetry arrived; the
  rest still mutate or decide with **no event a live surface can hear**:

  | Chamber | State (2026-08-05) |
  |---|---|
  | QUARANTINE ⇄ | **LIT** — `flow.quarantine` + `flow.restore`. The entry was visible at write time and the exit never was, so the queue could only appear to grow |
  | EPISODES | **LIT** — `flow.episode` carries `outcome`, because 405 of 413 say "success" and none has failed since May 19 (a skew you notice only if every episode wears its outcome) |
  | SKILLS | **LIT** — `flow.skill` on fitness and promotion; 369 skills, 281 with zero trials, last update May 15 |
  | DOCUMENTS | **LIT** — `flow.document` index+search; was the ONLY tier with no `emit` call at all, and it is the one this team leans on |
  | DREAM / maintenance | **LIT** — `flow.dream` on `run_maintenance`, which runs UNATTENDED every 4h and retires facts: measured on the home corpus 2026-08-05 23:07, `healed_superseded 5` and `skipped_equal_trust 95` over a 6476-fact scan. The event carries the steps that FAILED: each is wrapped ("a step failure never crashes the worker") and the error only reached `consolidate_last.json`, a file nobody opens. Fail-open stays; invisible fail-open does not |
  | DECAY | **LIT** — `flow.decay` on the product's mass write, carrying `updated_by_population`: the formula reads neither the moat verdict nor the row's fate, so a fact judged 99 and one never judged decay identically, and retired/quarantined rows (served to nobody) are decayed too. Declared, not decided — the pass still touches exactly the same rows |
  | FORGET | **LIT** — `flow.forget` carries `undoable`, and `forget_with_report` says WHERE the fact is still readable (see §6) |
  | CONTRADICTION SCAN | **LIT** — `flow.conflict` carries new detections next to `already_known`, because a scan that re-finds 2495 and adds 31 is doing something different from one that finds 31 on a clean corpus. It matters because the maintenance pass ACTS on what this registers, and ws4 sampled 25 of the 2526 registered clashes finding zero real ones. Still open (write-path owner): it excludes superseded rows *by design*, so the two defences are in series and the first removes the second's input; and no detector covers a categorical clash (Milan vs Rome) |

A gateway without the governance routes makes the panel say so
("pre-helm build") — an absent route must never render as "nothing lost".

⚠️ **Editing the panel's JS**: `webui.asset()` is `@cache`d — the file is read
ONCE per process, so an edit to `engine.js` is invisible until the server
restarts. The ETag hashes the cached body, so it stays self-consistent (the
server never serves content X labelled as Y) and no browser reload helps.
Correct for a shipped package, a trap while developing: it cost a round on
2026-08-07. And when you check whether your edit is live, grep for a string
UNIQUE to the change — the first probe here matched `undoable`, a word the old
file already contained in another renderer, and reported success.

⚠️ **Reading the panel from an automated browser**: `feedFlush` runs inside
`requestAnimationFrame`, which browsers suspend for a hidden tab. A pane that
is not on screen shows `LIVE` and an empty feed while the stream is perfectly
healthy. Probe `document.visibilityState` before calling a UI defect: if it
says `hidden`, verify from the endpoint instead (this cost three rounds on
2026-08-05, and the lesson was already in memory from July 16).

## 5. Numbers and tags you can trust

**Surface.** Flow events carry `surface`. Since 2026-08-04 an undeclared
caller is tagged `unknown` (before, the default was the *name of a real
surface* — 97% of the real corpus wore "sdk" chosen by nobody). `cli`, `mcp`,
`gateway` are set by their entrypoints; an explicit `ENGRAM_FLOW_SURFACE`
always wins.

**Tenant.** Every governance action carries the tenant that asked for it. The
restore/undo routes did not, at first: their events left as `surface=unknown`
with no tenant, which meant no one could tie a governance action to a
customer — and in personal mode it surfaced on the machine feed. Fixed the
same day it was measured.

**Where the log lives.** `<data dir>/events.jsonl` — the log follows the
store the caller chose. It used to be `~/.engram` hardcoded, so isolating a
bench with `HIPPO_DATA_DIR` still wrote telemetry into the home corpus.
`ENGRAM_EVENT_LOG` remains the explicit override.

**Unknown is not a number.** Counts a tier cannot answer read `unavailable`,
not `-1`, and a success/failure split is not printed at all when the tier did
not respond: "0 success, 0 failure" on a corpus holding 405 successes is as
false as `-1` and harder to spot. In the machine-readable dicts the value is
`None` — a program sums `-1` without noticing.
A sentinel value is a defect when it travels ALONE; next to an explicit
declaration (`checks[...] = "error: …"`, `status = "degraded"`) it is
legitimate, and `hippo_health` keeps its own for that reason.

**The HTTP write receipt mirrors the SDK one, verbatim.** `POST
/v1/memories` returns the SDK receipt object itself, so a field added to
`Memory.add()` reaches HTTP clients with no gateway work. Worth stating,
because grepping `gateway.py` for a receipt field finds only comments and
reads as "HTTP does not have it" — measured on 2026-08-05, when the missing
field was missing from *both* ports for the same reason: the merge base
lacked it. Pinned by `tests/test_http_rispecchia_la_ricevuta.py`, which
injects a key on the SDK side and reads it back over HTTP; the day someone
whitelists the response, that test fails instead of the contract silently
splitting in two. The mirror is total in the other direction too: a key
added to the receipt is published to HTTP callers without review.

## 6. Deleting: what "forgotten" really covers

`forget` clears every live table, the entity graph included. It does not
touch the whole-DB copies the Auto-Dream worker keeps: rotating ones for a
few hours, MANUAL ones forever — the May 12 copy still holds 60 facts the
live store dropped. `Memory.forget_with_report` deletes AND reports where
the fact is still readable, distinguishing copies that rotate from copies
that do not, because "for a couple of hours" and "forever" are different
promises. The scan checks each copy for real (a primary-key lookup) rather
than estimating, and never blocks the erasure if it fails.

Whether the manual dream copies should rotate or be purged is a product
decision, not a defect — but now the data to make it is visible.

Every port: SDK `forget_with_report`, MCP `hippo_forget_with_report`, and the
CLI prints the residual copies after a hard delete — the GDPR case, and the
one where "deleted" without "but the dream worker keeps copies forever" is an
incomplete answer given confidently. One body in
`residual_copies.forget_with_report`: the first MCP handler *rewrote* it, and
a copy instead of one surface is the defect class this branch keeps curing.

## 6b. Where each tier actually lives

`verimem tiers` (SDK `tier_inventory`, MCP `hippo_tier_inventory`, HTTP
`GET /v1/tiers`) names the store file per tier and counts its rows:

```
facts     8232   semantic/semantic.db          entities  9079   entity_kg/entity_kg.db
episodes   413   episodes/episodes.db          skills     324   skills/skills_index.db
documents   68   documents/documents.db
```

It exists because on 2026-08-05 the five entity tables inside `semantic.db`
— an empty migration shell — were counted as the tier, producing "the entity
tier is empty" while the graph held 9078 entities and 87387 edges, and a work
direction was retired on that reading. `verimem doctor` said nothing about
where a tier lives, so counting files by hand was the only way to find out,
i.e. the act that goes wrong.

Nine **decoys** live in the data-dir root, each carrying a tier's obvious
name (`semantic.db`, `episodes.db`, `entities.db`, `hippo.db`…). The
inventory lists them with their row counts rather than merely avoiding them:
avoiding protects this code, naming protects whoever counts by hand.
`~/.engram/semantic.db` is the worst of the nine because it *has* the table
and answers `0` — a plausible number instead of an error. A missing store
reads `unavailable`, never `0`: an empty container and an absent one return
the same number, and only the second announces itself.

## 6c. Why a claim was blocked — and when we don't know

`quarantine_log(explain=True)` re-runs the deterministic screens on the
proposition and names the one that fired. Two things it must never do, both
learned the hard way on 2026-08-05 (ws1, found by *using* the product):

- **It re-runs the store screen too, not only the validation gate.**
  `detect_injection` lives inside `store()`, which the gate does not cross,
  so for every fact the injection screen held, re-running the gate alone
  found nothing — and the fallback branch asserted L4. That family could
  never have been explained correctly.
- **When nothing fires, it declares instead of deducing.** The old fallback
  said "stopped by the comparison with its source (L4)" for any row it could
  not explain — false on a record whose `grounding_score` was 99.98, i.e.
  approved by that very layer. Now the row's own verdict decides the wording:
  never judged → "not L4, and not reconstructible"; approved → "NOT L4, the
  moat approved it and the fact is withheld anyway"; below the cut →
  "consistent with an L4 block, but this row does not assert it".

Measured breadth: `reason` is None on 500/500 records and `layers` empty on
183/500, because the deciding layer is computed at write time and not
persisted. Persisting it is a write-path column and stays open. A mute
surface gets noticed; an assertive and wrong one sends you looking in the
opposite direction.

## 7. What governance does NOT do

It does not make retirements *right* — it makes them visible and reversible.
The decision to retire (the write path) is a separate concern with its own
open defects (see the night reports of 2026-08-04: twin-entity fusion, MCP's
parallel write path that never supersedes, multi-principal retirement that
ignores `writer_principal`). A wrong retirement you can SEE and UNDO costs a
click; a wrong retirement you cannot see costs the fact — and the trust.
