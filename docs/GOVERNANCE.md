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

`reversible: false` on old rows is honest: retirements from before the helm
(2026-08-04) have no undo snapshot and cannot be reversed.

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
- a **`retired` counter** in the header next to admitted/quarantined;
- the **chamber map**, which declares its own blind spots instead of looking
  complete. Rows marked **LIT** carry the date their telemetry arrived; the
  rest still mutate or decide with **no event a live surface can hear**:

  | Chamber | State (2026-08-05) |
  |---|---|
  | QUARANTINE ⇄ | **LIT** — `flow.quarantine` + `flow.restore`. The entry was visible at write time and the exit never was, so the queue could only appear to grow |
  | EPISODES | **LIT** — `flow.episode` carries `outcome`, because 405 of 413 say "success" and none has failed since May 19 (a skew you notice only if every episode wears its outcome) |
  | SKILLS | **LIT** — `flow.skill` on fitness and promotion; 369 skills, 281 with zero trials, last update May 15 |
  | DOCUMENTS | **LIT** — `flow.document` index+search; was the ONLY tier with no `emit` call at all, and it is the one this team leans on |
  | DREAM / consolidation | measured, still dark: consolidates by ADDING a master node, never retires — the specific answer still beats the master in recall |
  | DECAY | measured, still dark: `run_decay_pass` DOES write, flooring aged facts to 0.05 confidence regardless of verification; the default ranking does not read that field, but a signal builder does |
  | FORGET | still dark as an event — but `forget_with_report` now says WHERE the fact is still readable (see §6) |
  | CONTRADICTION SCAN | measured, delivered to the write-path owner: it excludes superseded rows *by design*, so the two defences are in series and the first removes the second's input; and no detector covers a categorical clash (Milan vs Rome) |

A gateway without the governance routes makes the panel say so
("pre-helm build") — an absent route must never render as "nothing lost".

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

## 7. What governance does NOT do

It does not make retirements *right* — it makes them visible and reversible.
The decision to retire (the write path) is a separate concern with its own
open defects (see the night reports of 2026-08-04: twin-entity fusion, MCP's
parallel write path that never supersedes, multi-principal retirement that
ignores `writer_principal`). A wrong retirement you can SEE and UNDO costs a
click; a wrong retirement you cannot see costs the fact — and the trust.
