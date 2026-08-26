# Verimem

**Verified memory for AI agents.** Every write passes an admission gate, every
read carries provenance, and when the evidence isn't there the system abstains
instead of guessing.

[![PyPI](https://img.shields.io/pypi/v/verimem)](https://pypi.org/project/verimem/)
[![CI](https://github.com/aureliocpr-ctrl/verimem/actions/workflows/ci.yml/badge.svg)](https://github.com/aureliocpr-ctrl/verimem/actions)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue)](https://github.com/aureliocpr-ctrl/verimem/blob/main/LICENSING.md)
[![Website](https://img.shields.io/badge/web-verimem.com-informational)](https://verimem.com)

Most memory layers optimize for how much they can recall. Verimem optimizes for
whether you can **trust** what comes back: facts are admitted through an
anti-confabulation gate, stored with their sources, revised through explicit
supersession (never silent overwrites), and answered with citations — or with an
honest *"I don't know."*

**On retrieval itself we are competitive — and precise about what that means.**
Our own internal runs (our harness, our embedding model, our judge — **not**
third-party reproduced, and **not** the GPT-4 judge the public leaderboards use,
so these are *not* a like-for-like ranking against them): LongMemEval_s
session-level **recall@5 = 0.87** (judge-free, full 500 questions) and LoCoMo
**QA-accuracy = 0.81** (n=150, Claude judge). That's good retrieval — but the
reason to choose Verimem is the layer *above* it: whether you can trust what comes
back. Method and raw numbers: [`docs/BENCHMARKS.md`](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/BENCHMARKS.md).

## Features

- **Gated writes with the grounding moat ON by default** — every fact enters as
  a low-trust claim and must be backed by evidence to gain status. The
  **source⊢fact grounding gate** (the moat) runs by default: an extraction
  confabulation the source contradicts is quarantined, not absorbed. With an
  injected llm judge it reaches AUROC **0.96–0.97** (sonnet, on **SNLI** held-out;
  on out-of-distribution TruthfulQA/HaluEval it is ~0.81–0.90, and the free CE
  ~0.82 — the honest field numbers, `docs/EVIDENCE-external-2026-07-19.md`); the
  no-setup default is the local CE (scope below). It works **with no llm and in
  any language** once the local judge model is installed (`verimem warmup`
  fetches it; `verimem doctor` verifies): the free local
  cross-encoder judges every write (multilingual — measured EN/IT/FR/ES,
  entailments score ~97–99, most contradictions ~0.6 — no per-fact LLM call). A
  `Memory(llm=...)` uses that llm as the judge instead (highest quality). Only
  when neither an llm nor the local model is present does the gate fail-open
  (admit) — it never blocks a user who has neither, and says so on the write
  with an `L4-skipped` advisory.
  **Honest scope of the CE-only judge** (measured, `benchmark/moat_multilingual_matrix.py`):
  it catches *value/numeric contradictions* across EN/IT/FR/ES and off-topic
  confabs — but **not all of them**: the 2026-07-18 run had 0 numeric escapes in
  the 4-domain matrix, and re-running the same command on 2026-08-25 reports **4**
  (one per language) and exits 1. Run it yourself before trusting either number.
  Two known gaps close only with an llm judge: a *plausible added inference the source never states* (e.g. "…which
  reduced latency") scores high and is admitted — and that gap is the one this
  README used to leave without a number while quantifying every smaller one.
  **Measured 2026-08-25** (`docs/stato-reale/banco-osservatore-il-tasso.py`, 96 cases
  = 8 source types x 6 cases x 2 languages, CE-only judge): **25 of 48 such
  unsupported claims were admitted** — IT 54.2%, EN 50.0%, and **8 of the 48 cases
  get the OPPOSITE verdict in the two languages, in both directions**. Read it as
  the bound it is: on omission-shaped falsehoods the CE-only judge is close to a
  coin toss, which is why `Memory(llm=...)` is the configuration to use when the
  workload is *what the source did not say*; and an *entity-substitution*
  contradiction (swapping one allergen/product for another) can score mid-range
  in some languages — measured ~7% escape in Spanish, concentrated in that shape.
  A two-threshold band (**on by default**, `VERIMEM_CE_BAND_ENFORCE=0` reverts) holds
  the CE's uncertain middle zone, cutting that entity-substitution escape from
  **6.2% → 1.8%** on the moat matrix with **zero** new false-blocks on entailed
  facts (measured) — and the band **escalates to one llm adjudication** OFFLINE-FIRST instead of parking
  the write: a local **ollama** judge (auto-detected; default `qwen2.5:7b-instruct` —
  measured **AUROC 0.858 vs the CE's 0.829**, 2.3% misconception escape vs ~18%, fully
  offline) is preferred, then a `claude` CLI on PATH (subscription, no key), else the
  write is held for review. The verdict admits (judge-of-record `local-band`/`claude-band`
  on the receipt) or blocks; any escalation failure falls back to held-for-review, an
  unreadable verdict never admits (`VERIMEM_BAND_LLM=0` opts out). An air-gapped box with
  ollama thus gets the full moat with no network. The residual ~2% scores high and still needs
  a full llm judge. A third
  measured limit: the CE **hard-rejects true facts that require arithmetic or a
  unit/date conversion** ("0.5 g" ⊢ "500 mg", "two weeks before March 20" ⊢
  "March 6") or a low-resource language — those need an llm judge too. The moat is
  strongest with an llm; the free CE is the no-setup multilingual default.
  **External certification (out-of-distribution, `docs/EVIDENCE-external-2026-07-19.md`):**
  on our own 4-language structured-contradiction matrix the CE scores 0% false-block
  (re-measured 2026-08-25: still 0.0%, 112/112 entailed admitted) / **5.4% escape**
  (1.8% was the 2026-07-18 run; the same command today reports 5.4%);
  on **TruthfulQA heldout** — *plausible misconceptions* it never trained on — it scores **AUROC 0.829**, and at the default cut ~24% of true
  paraphrases are declined and ~18% of plausible misconceptions escape (74% of those
  scoring ≥80, the plausible-inference blind spot). Read honestly: the CE-only judge
  is a high-precision **structured-contradiction** filter, not a universal
  truth-detector — plausible-falsehood / paraphrase-heavy workloads should configure
  `Memory(llm=...)`. The write-gate checks *source ⊢ fact*, not factual truth.
  Opt-in origin tagging (`tag_beliefs=True` at ingest) additionally classes an
  unverified user assertion as `user_belief`: stored, but out of default
  recall until you ask for it (`search(..., include_beliefs=True)`).
- **Cross-fact contradiction + same-source evolution — ON by default.** A plain
  `Memory()` no longer hoards a contradicted value: write "the plan costs 100 €" then
  "…150 €" (same source) and recall returns **only the current one**, the old
  `superseded_by` the new (never a silent overwrite — the old row stays for lineage).
  The deterministic **lexical** detector carries this at the default `validate="full"` for
  **numeric / version / date / negation** changes — measured on
  `benchmark/evolution_moat_vs_mem0.py`: 100€→150€, 2.3.1→4.0.0, March→September (same
  year), 2025-03-06→2025-09-20, signed→*not* signed all retire the stale value with zero
  extra models. **Entity swaps** (one CEO→another) need the **semantic NLI** tier, which
  **auto-enables when its model is already installed** (`verimem warmup` fetches it; a
  pure filesystem check, no flag needed — measured **0/10 stale-leak across the full
  matrix** on a warmed machine, vs mem0's 10/10). No model on disk → the tier stays off
  and costs nothing; `VERIMEM_SEMANTIC_CONFLICT=0` opts out explicitly. A **cross-source** clash
  quarantines the new instead (the griefing guard — one source never retires another's
  fact). Same-source authority is sound within a tenant + a single-agent-per-tenant
  assumption (verimem has no per-writer auth yet); a multi-agent tenant that can't trust
  its writers sets `VERIMEM_SUPERSEDE_SAME_SOURCE=0` (detect, but quarantine instead of
  supersede) — or declares `VERIMEM_MULTI_WRITER=1`, which flips the same default off on its
  own. `Memory(preset="permissive")` / `validate="fast"` skip the moat entirely.

  **Known limit, measured on our own corpus, not on a bench.** Same-source evolution
  assumes the newer number *updates* the older one. When two facts under one topic
  measure **different things**, that assumption is wrong and the newer one retires a
  fact that was true. On our production store we found **171 pairs where both facts
  scored ≥90 with the grounding judge and one still retired the other**; we read 55 of
  them by hand and none was a legitimate update. Guards now separate the cases that
  have a *shape* — different quantity units (`1 failed / 11767 passed` vs `8019
  warnings`), build-matrix cells (`ubuntu-latest` vs `macos-latest`, `py3.12` vs
  `py3.13`), record numbers, dates, disjoint proper nouns — which covers **70 of the
  171**. The remaining 101 have no syntactic shape: what separates them is meaning, and
  a lexical rule cannot see it. **One topic per measurement** is the practical
  mitigation and it is not hygiene advice — on facts written in the last 7 days,
  survival was **2348/2444 on topics used once** against **230/338 on topics reused**.
- **Every write returns an adjudication receipt** — `add()` hands back a visible
  verdict: `{disposition, evidence_class, judge, score, threshold, margin, reason,
  confidence_tier}`. A quarantine is a *reasoned* verdict, never a silent drop,
  and the **judge-of-record** (which judge decided, against what threshold) rides
  every decision. The `confidence_tier` (`high` / `borderline` / `low` /
  `unverified`) is the *instrument's* confidence, **not a truth claim**: a `high`
  tier from the local CE can still be a plausible-but-unstated inference — read
  `evidence_class` for what actually adjudicated the fact.
- **Quarantine recovery — a wrong block is visible and reversible.** When the gate
  holds a legitimate fact (an over-eager keyword flag on a real
  lawyer/engineer/clinician statement, say), you can SEE it and undo it without
  reaching into internals: `Memory.quarantine_log()` lists held claims — pass
  `explain=True` (or `explain: true` on the MCP tool) and each row also says
  WHICH screen stopped it and what would let it through, recomputed on the spot
  so it works on claims held long before you asked. A claim stopped by the
  source-entailment check is the one case that cannot be explained afterwards —
  the source is not retained — and it says so rather than returning nothing. And
  `Memory.restore(fact_id, reason=…)` returns one to default recall. The same pair
  is on the MCP surface (`hippo_quarantine_log` / `hippo_quarantine_restore`). It is
  a *guarded* human override, not a back door: restore refuses a **superseded** fact
  (never resurrects a retired value) and re-screens the proposition **and the topic**
  for prompt-injection — an exfiltration payload the gate quarantined stays
  quarantined even if a caller passes its id.
- **Provenance on every read** — answers cite where each fact came from
  (conversation, document offset, tool call). A `TrustReport` explains *how the
  system knows*: chain of custody, declared conflicts, or an explicit abstention.
  The *ranking* declares itself too: `hippo_facts_recall` returns a `ranking`
  field saying which of the three signals actually ordered the answer — e.g.
  `{"rerank": "timeout_cold", "fusion": "timeout"}` when a cold process kept
  bi-encoder order, `{"rerank": "applied", "fusion": "applied"}` when all three
  ran. Each stage degrades under a wall-clock budget rather than hanging the
  caller, so the same query can legitimately return a different set on a cold
  process than on a warm one — that difference is now stated, not silent.
- **Bi-temporal history** — facts carry both *when it happened* and *when we
  learned it*. Query the past (`as_of`), see transitions ("changed from X to Y
  on date Z"), and audit every revision.
- **Abstention by design** — on questions the store cannot support, Verimem
  says so instead of stitching an answer from the nearest-but-irrelevant facts.
  Memory-boundary abstention holds at 1.0 across our end-to-end runs. What each
  door does with it differs, so: **gateway/console FILTER** — results under the
  self-calibrated floor are not served at all; **MCP SERVES the results and
  flags them** — every read carries `sotto_il_pavimento` (floor, best score,
  and what it means) so the agent has the yardstick, plus `trattenuti` when the
  gate withheld facts on that topic; **the embedded SDK** exposes the same two
  signals on the `Risultati` object, and is left permissive by default so a
  brand-new, near-empty store doesn't over-abstain while it fills up — one
  switch away (`explain(..., min_relevance="auto")` or
  `VERIMEM_MIN_RELEVANCE=auto`), and the floor is sharpest on real-size corpora.
  Note the shape: only `explain`/`trust_report` refuse to answer. `recall` and
  `search` always return the nearest facts — the flag is how you tell "nearest"
  from "right". **Abstention has two levels, and the second one has a
  dependency:** the relevance floor above runs everywhere, but the *sufficiency*
  judge — the one that catches a fact that is on topic yet does not answer the
  question — needs a configured LLM provider. Install Verimem without one and
  `get_llm()` returns a mock: that second check cannot run, `verify.sufficiency`
  reports `no_provider`, and the dossier comes back without it. The floor still
  abstains on out-of-domain questions; what you lose is the on-topic-but-wrong
  catch.
- **Document memory, cited on the indexed text** — index PDF/DOCX/HTML/EPUB/text
  files; semantic search returns passages with source, version and character
  offsets, where `indexed_text[start:end] == passage`; passages can be promoted
  to memory *through the gate*, citation attached. The offsets are exact on the
  index and the passage text always comes back with them — they are not a
  promise that the original file still opens, since paths are stored as given.
  Reachable from all three surfaces: `verimem index` / `verimem search-docs` on
  the CLI, `verimem_document_*` over MCP, and `Memory.index_document(path)` /
  `Memory.search_documents(query)` from the SDK. Documents indexed through a
  `Memory` live next to that memory's facts, not in a shared system index.
- **Consent-first import** — bootstrap from your ChatGPT / Claude export:
  conversations are listed first, nothing is ingested without an explicit
  selection.
- **Opt-in auto-memory** — `AutoMemory(memory).observe(role, text)` watches a
  live conversation and remembers on its own, but through the SAME gated
  pipeline as explicit writes (extraction → gate → provenance). Opt-in by
  construction: if you don't instantiate it, it doesn't exist.
- **Trust odometer** — `m.trust_stats()` / `verimem stats`: persistent
  counters of what the gate actually *did* on your store — writes admitted,
  quarantined, rejected, and honest read-path abstentions, with per-layer
  attribution. Observable actions, not marketing claims; no fact text is
  copied into the counter.
- **True forget** — `delete(purge_history=True)` removes the fact *and* its
  supersession chain; the deleted data does not resurface through history or
  time-travel queries.
- **Per-source trust, two channels** *(flag-gated)* — every writing source earns
  a reputation from inter-source agreement (consistency) and from how its claims
  fare in use (outcome); the weaker observed channel decides. Independence
  clustering collapses copies/colluders of one feed to a single witness, so
  manufactured consensus cannot self-confirm. Reproduced on a real held-out
  corpus (HaluEval, 3/3 seeds): a 4-id cartel that self-confirms to 0.90 under
  naive counting is demolished to 0.20, honest sources restored to 0.95, and
  the hallucinated answers it pushed drop out of recall entirely.
- **Epistemic labels** — a fact can carry the *kind* of guarantee behind it:
  `proven` (a named machine-checkable proof), `unbeaten` (held up to a declared
  bound — the bound only grows), or `refuted` (a named counterexample,
  absorbing). "Held to 10^6" and "proven" are never conflated.
- **Derived knowledge, through the same gate** — the composition ring derives
  new candidate facts from verified ones (declared substitution patterns),
  pushes them through the *same* admission gate as every other writer, and
  admits survivors signed (`actor:composer` — engine writes never testify for
  themselves), traced (`derives_from` parents, retractable if a parent falls)
  and labeled with the exact check that passed. Few but zero-false by
  construction. Run it one-shot (`python -m verimem.compose_daemon --db ...`,
  schedule with cron/Task Scheduler): the daemon refuses to compose when the
  engine's own writes already dominate the recent stream (self-echo
  guard-rail).
- **Read-path guardian** — when the store holds a better-guaranteed truth about
  the same subject, a read doesn't just abstain: it *corrects*, citing both
  facts (`correct_read` → ACCEPT / CORRECT / ABSTAIN; a refuted fact is never
  served). Paired with **active probes** that build the query which would
  falsify a stored fact — finding independent counter-evidence proposes a
  `refuted` label, surviving grows its `unbeaten` bound — the store falsifies
  itself instead of waiting for a contradiction to arrive.
  *Scope, measured:* "the same subject" is resolved by parsing a copula
  ("X is a Y"), so the comparison only happens on facts with that shape — **7
  of 5194 live facts** on our own corpus (2026-08-02), which is prose. On the
  rest the read is served with `not comparable — no conflict search ran`
  rather than a silent "unchallenged": the guardian says when it did not look,
  and on prose-shaped memory that is most of the time.
- **Ignorance map** — "I don't know" becomes "here is *what* I'm missing": each
  unanswerable query is classed (no evidence / below the floor / evidence
  quarantined / a live conflict) with the concrete source or audit that would
  answer it — the active complement of abstention.
- **Provenance signing** *(opt-in)* — an unforgeable HMAC of *who is speaking*
  rides inside each write's provenance ref, complementing the entailment gate's
  *what deserves admission*: content authenticity **and** channel authenticity,
  the two halves no deterministic content filter alone can certify against an
  adaptive adversary.
- **Local-first** — SQLite storage, local embeddings, injectable LLM. Runs
  air-gapped (`verimem airgap` verifies zero-egress configuration).

## Install

```bash
pip install verimem
```

<!-- ⛔ RILASCIO — LEGGERE PRIMA DI PUBBLICARE.
     La nota qui sotto vale FINCHE' il pacchetto pubblicato e' vecchio. Nel momento in cui
     si pubblica diventa FALSA, e non resta un dettaglio interno: `pyproject.toml:16` dice
     `readme = "README.md"`, quindi QUESTO FILE E' LA PAGINA DI PyPI. Pubblicare senza
     toccarla spedisce al mondo una vetrina che dice «cio' che PyPI vi serve non e' cio'
     che questa pagina descrive» -- riferito a se stessa.
     Chi pubblica: aggiornare i numeri (release, distanza in commit) o togliere il blocco.
     Aggiunta il 2026-08-26 da ws7 insieme alla nota stessa, per non lasciare una mina a
     chi fara' il rilascio. -->
> **What PyPI serves you today is not what this page describes.** The latest release
> is **0.7.0 (22 July)**; `main` is **994 commits** ahead of it. Two consequences you
> should know before you start, both measured on 2026-08-26:
>
> - **The MCP server does not start.** `verimem 0.7.0` declares `mcp>=1.0.0` with no
>   upper bound, so pip resolves it to `mcp 2.1.1`, which removed `list_tools`,
>   `call_tool` and `list_resources` -- the low-level API this server calls in 11
>   places. The ceiling (`mcp>=1.0.0,<2`) has been in the repo since 29 July
>   (`bd4ff5ba`) and is not in the published package -- `bd4ff5ba` is not an ancestor
>   of `v0.7.0`. This is observed, not inferred: `pip install --dry-run
>   verimem==0.7.0` in a clean venv reports *"Would install ... mcp-2.1.1 ...
>   verimem-0.7.0"*, and on that installed `mcp` the API is gone at runtime:
>   `list_tools`, `call_tool` and `list_resources` are absent from both the class and
>   an instance, against an `mcp 1.26.0` control where all three are present on both.
>   The failing line itself has been executed: `@server.list_tools()` -- the decorator
>   at `mcp_server.py:6804` in `v0.7.0` -- raises `AttributeError: 'Server' object has
>   no attribute 'list_tools'` under `mcp 2.1.1`, and succeeds under `mcp 1.26.0`. So
>   `mcp<2` does restore that line. What is still *not* observed is the whole
>   `verimem mcp` process starting, which needs the full ~2 GB install.
> - **18 commands exist here and not in the package**, `save` among them -- the
>   canonical write of the project's own protocol. Measured 2026-08-26 by reading the
>   published wheel's CLI against `main`: 40 commands in the wheel, 58 here, and the
>   40 are a strict subset. `docs/stato-reale/02e-chi-installa-riceve-il-22-luglio.md`
>   counted 16 on 2026-08-08 with a different ruler (what `verimem --help` prints);
>   both are true, and the gap has not narrowed.
>
> For what this page claims, install from source (`pip install -e ".[dev]"`, see
> Development below). `docs/stato-reale/` is where the gap between this README and
> the published artifact is measured, document by document. Most of those notes are
> dated 2026-08-08 and that does *not* make them stale: they describe the *published*
> package, and the published package has not moved since -- 0.7.0 is still the latest
> on PyPI. Re-measured on 2026-08-26, one of them had drifted only in our favour:
> `02e` counted 16 commands missing from the package, today it is 18.

**What it costs on disk.** Verimem ships a local judge, so the footprint is larger than a
typical library and it is worth knowing before you start:

| step | on disk |
|---|---|
| `pip install verimem` — 74 packages, `torch` is more than half of it | **~1.0 GB** |
| first `verimem warmup` — embedding + reranker + gate models | **~2.3 GB** |
| **total, first run on a clean machine** | **~3.3 GB** |

Measured on Windows with Python 3.13; on Linux the `torch` wheel differs, so the first row
changes. These are *sizes on disk after installation*, not download sizes — the download is
smaller for the packages (221 MB compressed) and roughly the same for the models, though that
last part was not measured.

**How long it takes**: `verimem warmup --no-gate` — everything except the judge — took
**2 minutes and 45 seconds** on a clean cache. The full warmup downloads about three times as
much and was **not timed**, so treat the total as unknown rather than as three times that.

If you only need the deterministic checks and can live without the local judge, `verimem
warmup --no-gate` skips the judge model entirely — it never creates the model directory. That
model is announced as 746 MB and takes 746 MB on disk — the same figure the CLI prints (`verimem warmup --help`). Sizes here are decimal MB (10^6): the directory is 746 058 368 bytes, which a tool reporting MiB (2^20) shows as 711 — same bytes, different unit.

The reranker is a third model, and it is on by default: `warmup` downloads its 470 MB unless
you set `VERIMEM_RECALL_RERANK=0`. It is the stage-2 recall lever, not part of the moat — so
turning it off costs ranking quality on short queries and nothing else.

## Quickstart (Python)

```python
from datetime import datetime

from verimem import Memory

# No llm needed for the moat. Run `verimem warmup` once first: it downloads the
# multilingual gate model (~746 MB, a public release — no account) that judges
# writes; `verimem doctor` verifies the install. Without a judge, writes are
# admitted WITH an explicit L4-skipped advisory (never silently) and the assert
# below would fail — doctor tells you exactly why. And it costs more than the
# missing check: with nothing judging them, the second write retracts the first,
# so the confabulation ends up the only fact left live.
m = Memory("memory.db")

# THE MOAT, live — the reason Verimem exists. Same source, two writes; works
# with NO llm, in any language (the local CE is the judge):
src = "We migrated the analytics store to Postgres last quarter."
m.add("Analytics runs on Postgres.", source=src)   # entailed  -> admitted
r = m.add("Analytics runs on MongoDB.", source=src)  # confab -> QUARANTINED
assert r["status"] == "quarantined"   # stored but OUT of default recall —
                                      # your agent will never repeat it as truth

# Pass an llm for the highest-quality judge (and to extract facts from raw
# conversations); the local CE is the free default when you don't.
m = Memory("memory.db", llm=my_llm)   # any client with .complete(system, messages)

# Gate presets: "balanced" (default), "strict" (reject on contradiction or
# failed source-grounding), "permissive" (creative / low-stakes, no quarantine).
m = Memory("memory.db", preset="strict", grounding_llm=my_llm)

# Store a conversation — facts are extracted atomically and pass the gate.
# Extraction from raw dialogue needs the llm; user_name makes the app-provided
# identity the subject of the facts.
m.add([{"role": "user", "content": "I moved to Berlin in March."}],
      user_name="Alice")

# Attach PROVENANCE to a fact (no LLM needed). `verified_by` records WHERE the
# claim came from — it is shown on every read and cannot be forged into a higher
# trust status (a self-cited receipt never becomes "verified"; the gate's outcome
# + provenance are the trust signal, not a self-asserted badge).
m.add("Deploy pipeline is green", verified_by=["ci:main:green"])

# Search — optionally with history context or as of a past moment
m.search("where does Alice live?")
m.search("where did Alice live?", as_of=datetime(2024, 1, 1).timestamp())

# Ask HOW the system knows: evidence dossier or an explicit abstention
report = m.explain("where does Alice live?")
```

## Quickstart (Claude Code / MCP)

Add to `.mcp.json` in your project (or `~/.claude/.mcp.json`):

```json
{
  "mcpServers": {
    "verimem": {
      "command": "verimem",
      "args": ["mcp"],
      "env": { "VERIMEM_HOSTED": "1", "VERIMEM_TOOL_NAMESPACE": "verimem" }
    }
  }
}
```

This exposes the memory tools (`verimem_remember`, `verimem_facts_recall`,
`verimem_trust_report`, `verimem_document_semantic_search`, …) to any MCP
client. Drop the `VERIMEM_TOOL_NAMESPACE` entry to keep the legacy `hippo_*`
names — both dispatch to the same tools.

Onboarding is automatic: every MCP client receives a usage guide on connect
(the `instructions` field of the initialize response). For any other
integration, `verimem agent-guide` prints the same guide — paste it into a
system prompt or CLAUDE.md.

## CLI

```bash
verimem index contract.pdf              # index a document for semantic search
verimem search-docs "termination clause" # passages with file + offset citations
verimem import conversations.json       # list a ChatGPT/Claude export (imports nothing
                                        # until you pass --ids or --all)
verimem import conversations.json --project verimem --since 2026-06-01 --all-matching
                                        # import a filtered subset (title/date/project)
verimem trust "the deploy is green" --verified-by ci:main:green
verimem save "The rent is 900/month." --asserted-at 2026-03-15
                                        # WHEN the fact is true, distinct from when
                                        # you wrote it — this is what `as_of` travels
                                        # over. Omit it and event time stays unknown.
verimem airgap                          # verify a zero-egress CONFIGURATION
verimem airgap --live                   # PROVE it: audit every socket during a
                                        # real write+search, exit 0 iff no egress
```

## Governance — see and reverse what the memory decides

A fact disappears in TWO ways — retired (superseded) or quarantined — and a
memory that decides silently is a memory you cannot trust. The governance
surface makes every decision visible and the wrong ones reversible, on every
port (SDK, CLI, MCP, HTTP):

```bash
verimem facts retirement-log --counts   # the honest quartet: written / servable /
                                        # retired / quarantined, formula included
verimem facts retirement-log            # who was retired, by whom, why — with the
                                        # undo handle when reversible
verimem facts undo <op_id>              # reverse a retirement: the lost fact comes
                                        # back SERVABLE and the newer one stays alive
```

Write receipts carry the handles too (`superseded_undo_ops` on `add()`), every
retirement emits a `flow.supersession` event, and the Engine Room
(`/ui/engine`) shows the pairs with one-click undo/restore. Full manual:
[docs/GOVERNANCE.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/GOVERNANCE.md).

## See your memory working — the trust console

The visual layer exists at every deployment size — single user, team
server, SaaS — same page, same guarantees:

```bash
verimem console        # your OWN local store: browser opens, no keys, no config
```

`GET /ui` (also served by the team gateway) shows: the **trust ring** (share
of writes admitted clean) with per-day sparklines, the **knowledge graph**
(drag, zoom; grounded edges solid, ungrounded dashed red — declared, never
hidden) where clicking a conclusion lights its **chain of custody** hop by
hop, and the **blocked-claims log** — every unsupported claim the gate
stopped, auditable. The graph is **alive**: nodes the engine touches fire and
new ones grow in as you work, straight from `/v1/events/flow`. It is an honest
window, not the whole store — it shows the most recent entities with the real
edges between them and declares the totals (`total_entities`, `total_edges`,
`isolated_count`), so a node's `isolated` badge means "no relation anywhere",
never "the sample dropped it". Live: gate events stream over SSE (`GET /v1/events`), so
you watch the memory working, not a 30s-old photograph. For the engine itself
there is the **Live Engine Room** (`GET /ui/engine`, stream
`GET /v1/events/flow`): the custody line animated by YOUR store's real events
— each write admitted or quarantined, each recall answered or abstained, with
per-tenant privacy (flow metadata only, never fact content). The events are
emitted by the core, so every surface shows up in one panel — SDK, gateway,
and the MCP server used by Claude Code **or any other vendor's agent** (label
yours with `VERIMEM_ACTOR` in its MCP config). Same feed in a terminal:
`verimem flow tail`. Personal mode binds
127.0.0.1 by default — the **loopback bind is the real defense**; a Host-header
allowlist is a *second* layer against browser DNS-rebinding, but a direct client
(e.g. `curl`) can spoof the Host header, so never expose personal mode on a
non-loopback bind. A presented API key always wins. For agents there is `GET /v1/snapshot` — the whole visible
state (odometer + daily series + quarantine + graph with provenance) in one
structured call: what the console shows a human, shaped for an AI.

## Self-host (team server)

Run Verimem as a shared memory server your team hosts — the data never
leaves your infrastructure:

```bash
verimem gateway keys create --tenant acme --name laptop   # key shown once
verimem gateway serve                                     # 127.0.0.1:8377
```

Each tenant gets an isolated store; the tenant is derived from the API key
alone. Endpoints: `POST /v1/memories`, `GET /v1/search`, `GET /v1/explain`
(TrustReport), `GET /v1/stats` (the tenant's own trust odometer + usage),
`GET /v1/quarantine`, `GET /v1/graph`, `GET /v1/graph/dossier`,
`GET /v1/snapshot`, `GET /v1/events` (SSE),
`DELETE /v1/memories/{id}?purge_history=true`. Open `/ui` in a browser for
the trust console (or `/dashboard` for the legacy minimal odometer) — static,
dependency-free pages; your API key stays in the tab and travels only as an
Authorization header. The gateway binds loopback by default — for remote
access put it behind a TLS reverse proxy (nginx/caddy).

### Many local sessions, one memory (thin client)

Several local agents — Claude Code windows, Cursor, a cron job — should share
ONE memory, not each spin up a model-loading store that fights the same SQLite
file. Point them at a running server and they become **thin clients**: no model
load, just HTTP.

```bash
verimem gateway serve                       # one server owns the models + store
export VERIMEM_SERVER_URL=http://127.0.0.1:8377
export VERIMEM_SERVER_KEY=vm_...            # a tenant key (created above)
```

With those set, the Python SDK (`open_memory()`), the CLI (`verimem remember` /
`recall`), and the MCP tools (`hippo_remember` / `hippo_facts_recall` /
`hippo_facts_search`) all route through the shared server — a session behind it
never loads a model. If the server is unreachable, each falls back to its own
embedded store (fail-soft, never a crash). Writes are idempotent (a retried
cold-start write is de-duplicated). Per-user scoped ops
(`user_id`/`agent_id`/`run_id`) stay local for isolation.

Docker (embedding models baked in — runs fully offline):

```bash
docker compose -f docker-compose.gateway.yml up -d --build
```

TypeScript client ([sdk/typescript](https://github.com/aureliocpr-ctrl/verimem/tree/main/sdk/typescript)) — typed, zero-dependency,
contract-tested against the live gateway from the Python suite:

```ts
const memory = new VerimemClient({ baseUrl, apiKey });
await memory.add("deploy is green", { verifiedBy: ["ci:main:green"] });
```

Consistent hot backups (SQLite online backup API — correct while serving):

```bash
verimem gateway backup ./snap-2026-07-08   # keys + every tenant store + manifest
verimem gateway restore ./snap-2026-07-08 ./new-data-dir
```

## Benchmarks

Measured on [HaluMem](https://github.com/MemTensor/HaluMem) with the full
pipeline (our extraction → gated store → answer), judged by a Claude-based
grader. Full methodology, caveats and raw result files:
[BENCHMARKS.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/BENCHMARKS.md).

| Metric | Verimem | MemOS (self-reported) |
|---|---|---|
| End-to-end QA, same-recipe cluster (7 full runs, n=188) | **0.66–0.68** (mean 0.667, n=3 clean) | 0.672 |
| End-to-end QA, cross-user generalization (never-seen user, n=169) | **0.716** | — |
| Read-path QA (gold store, 3 users) | 0.739 / 0.750 / 0.787 | — |
| Memory-boundary abstention (end-to-end) | **1.000 — seven consecutive full runs** | — |
| …and the other half: abstention on questions that DO have an answer | **0.20** (production default) vs **0.30** plain-RAG baseline — it abstains *less* | — |
| Extraction F1 (58 sessions, replicated ×2) | 0.761–0.768 | 0.797 |

**Where each of our numbers comes from** — the committed artefact and the key
inside it, so you can check any of them without guessing:
`0.667` and `0.716` → [`e2e_crossuser_u2.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/e2e_crossuser_u2.json)
(`u1_mean_3runs`, `accuracy`) · `0.750` → [`qa_gem_k12_u0.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/qa_gem_k12_u0.json)
and `0.787` → [`qa_gem_k12_u2.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/qa_gem_k12_u2.json)
(`accuracy`) · `0.761` → [`extraction_consolidate_u5s6.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/extraction_consolidate_u5s6.json)
and `0.768` → [`halumem_extraction_f1_u10s6_refined_completeness.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/halumem_extraction_f1_u10s6_refined_completeness.json)
(`f1`). ⚠️ **`0.739` is the exception and we say so**: it is reported in
[`BENCHMARKS.md`](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/BENCHMARKS.md)
(as `0.7394`) and **has no committed results file** — the third user's run is
not in `benchmark/results/`, where `u0` and `u2` are.

We describe the end-to-end result as **parity, not a win**: the same-recipe
runs cluster around MemOS's self-reported number and the judges differ
(ours vs theirs). Trust properties hold through the full pipeline. On
[TrustMem-Bench](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/trustmem_bench.py) — six deterministic trust axes
(fabrication under absence, destructive updates, temporal integrity, forget
integrity, provenance honesty, sycophancy resistance) — Verimem scores 60/60;
the bench is offline and seeded, run it yourself in one command.

Scale: recall latency stays ~flat with the optional ANN index
(`pip install "verimem[ann]"`): 1.3 ms at 1M facts vs 81 ms brute-force
([`ann_scale_bench_repro.json`](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/results/ann_scale_bench_repro.json),
which is also where the recall figures below come from). Two caveats a reader
should have: the bench's own docstring points at `ann_scale_bench.json` instead,
and that file covers only 100k/500k and carries no recall column — so following
the pointer does not lead to these numbers; and for the same 100k three tracked
runs report 8.0x, 9.5x and 7.8x, so read the multiplier as machine-dependent
rather than as a constant. With
faiss installed it auto-enables above 100k facts (`VERIMEM_ANN_RECALL=0` opts
out); the default install ships no faiss, so recall is exact brute-force. See
[SCALE.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/SCALE.md) for the table + the honest caveats: the ANN is
*approximate*, and on the random-vector stress bench its recall-in-pool
**degrades with corpus size** — 0.87 @100k, 0.53 @500k, 0.41 @1M (clustered
real-embedding corpora measure far higher — ~1.0 at oversample 8 at prototype
scale — and raising the oversample recovers recall at some latency); the 1M
build also needs a large-RAM box.

## Why the numbers matter

Accuracy benchmarks measure how often a memory system answers correctly.
They do not measure what happens **when it cannot know** — and that failure
mode is exactly what makes memory systems risky in serious applications.
This is where Verimem is structurally different, and every row below is a
measured result with the raw file in the repo, not a design intention:

| Capability | Verimem (measured) | mem0 / Zep / MemOS |
|---|---|---|
| Abstains instead of fabricating when the store can't support an answer | **1.000 across seven consecutive full e2e runs** — and on questions that DO have an answer it abstains **0.20**, against **0.30** for the plain-RAG baseline ([BENCHMARKS](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/BENCHMARKS.md)). A 1.000 alone cannot distinguish "abstains when it should" from "abstains always", so both halves belong together | not measured by their leaderboards |
| Write-path gate (unsupported "it works" claims quarantined — stored, not served) | grounding judge AUROC **0.96–0.97** across models/seeds (0.971 sonnet-4 R10 on SNLI, 0.963 sonnet-5 re-run 2026-07-16, 0.974 pooled multi-model) — ⚠️ those are the **injected LLM judge** (the seeds named are `sonnet-4`/`sonnet-5`); with no LLM injected the write gate still runs, on the **local CE**, which scores **AUROC 0.829** on TruthfulQA heldout (row above). The gate is there either way; the number is not the same one | no write gate |
| Conflicting well-grounded memories resolved by provenance (`answer`, trust-conditioned) ⚠️ **needs an injected LLM**: `answer()` is keyword-only on `llm` and raises `TypeError` without one, so this row is unavailable on a plain install | correct **0.17 → 0.92**; on the 2 truly unresolvable conflicts it did **not** abstain — it picked a side both times ([bench](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/wellgrounded_distractor_bench.py), sonnet-5) | served as-is |
| Trust axes under adversarial pressure ([TrustMem-Bench](https://github.com/aureliocpr-ctrl/verimem/blob/main/benchmark/trustmem_bench.py), deterministic, run it yourself) | **60/60** | mem0: 40/60 (forget-leak reproduced live) |
| Bi-temporal history & time travel (`as_of`, "changed from X to Y on date Z") | shipped, tested | latest-value only |
| True forget (GDPR): deleted data cannot resurface via history or time travel | shipped, probe-tested | mem0 leaked in our probe |
| Provenance on every read (who wrote it, source ref, gate status) | every hit | absent or partial |
| Runs fully air-gapped (local embeddings, injectable LLM, zero egress check) — ⚠️ **not the default**: a stock install is `not offline-pinned` and cold model loads may reach the HF Hub, as `verimem doctor` states; set `VERIMEM_OFFLINE=1` | `verimem airgap` | cloud-first |

Our method is the other differentiator: **every claim in this README links
to a raw result file, negative results are published** (see the declared
regressions and falsified hypotheses in
[BENCHMARKS.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/docs/BENCHMARKS.md)), and the honest framing rule —
"parity, not a win" — is enforced against ourselves. A memory layer asking
for your trust should be able to show its work. This one does.

## What Verimem does not do (yet)

Same rule as the numbers above: measured, not assumed.

**Deletion removes a fact from service, not from the file.**
`Memory.forget(fact_id)` does what it says at the database level — the row is
gone, no table still contains the text, and `recall` no longer returns it
(verified). But the string **remains readable in the raw `.db` bytes**, and
still does after `VACUUM`: SQLite's `secure_delete` is off by default, so
deleted pages are not overwritten. This is standard SQLite behaviour, not a
bug in Verimem — but "forgotten" here means **no longer served**, not
**no longer recoverable**. If you hand the file to someone else, put it in a
backup, or lose the disk, you hand over what you believed you had deleted.

What deletion looks like depends on which door you use, so here it is per door:

- **deletion by subject does not exist anywhere.** "Forget everything about
  this person" is not a tenant scope: unless that person's facts happen to sit
  under their own `user_id`, you are back to one `fact_id` at a time.
- **which door you use decides whether the text is really gone.** Five doors
  delete and they do NOT make the same promise — the table below says which.

Measured in one run, same store, searching every table for the deleted string
afterwards:

| deletion door | after the delete, the text is in |
|---|---|
| `Memory.forget(id)` / `.delete(id, purge_history=True)` (SDK) | no table |
| `hippo_fact_forget` (MCP) — calls the SDK delete | no table |
| `verimem facts forget <id>` (CLI) | **`facts_undo_log`** |
| `hippo_fact_forget_with_undo` (MCP) | **`facts_undo_log`** |
| `hippo_forget_scope` (MCP, bulk by tenant) | **`facts_undo_log`** |

The bottom three keep the proposition **in clear text** for the undo window
(7 days) — that is what makes them reversible. It is a real feature and the
right default for an operator who mistyped an id; it is the wrong default for an
erasure request, and nothing in the output says so: the CLI prints `undoable for
7 days`, which reads as *reversible*, not as *still readable in a table*.

⚠️ Note the shape of it: **the bulk-by-tenant door — the one you would reach for
on a "delete everything about this user" request — is one of the three that keep
it.** For that case use the SDK, or wait out the window and verify, or delete the
`facts_undo_log` rows yourself. (Measured at the level of the functions those
doors call — `semantic.delete_with_undo` vs `Memory.delete` — not through a live
MCP dispatcher.)

We state this because the licence is AGPL-3.0 and an agent memory is exactly
where personal data ends up. If your deployment needs deletion to be
irreversible — GDPR erasure, for instance — treat `forget()` as a first step
and handle the storage layer yourself (`PRAGMA secure_delete=ON` before the
writes, plus a `VACUUM`), or keep the store on encrypted media and destroy the
key. Do not rely on `forget()` alone for that guarantee: it does not make it.

## Architecture

```
conversations / documents / tool results
        │  atomic extraction (subject-named, date-attached)
        ▼
  admission gate  ── quarantines unsupported claims (contradictions: strict mode)
        ▼
  bi-temporal store (SQLite) ── facts + provenance + supersession chains
        │
        ├─ semantic recall (local embeddings + ANN, optional reranker)
        ├─ history / as-of / transition context
        └─ TrustReport: evidence dossier or explicit abstention
```

The Python package is `verimem` — one product, one name (total rename, 0.6.0).
`import engram` and `import hippoagent` still work as compatibility aliases
(same module objects, no duplicated state), and so do all three env prefixes:
every `VERIMEM_X` setting can also be written `ENGRAM_X`/`HIPPO_X` (mirrored at
import, explicit values never overridden). Existing `~/.engram` data stores
keep working untouched; new installs default to `~/.verimem`.

## License

Dual-licensed: **AGPL-3.0** for open source use, with a **commercial license**
available for proprietary or closed-SaaS deployments — see
[LICENSING.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/LICENSING.md). Versions 0.3.x and earlier remain MIT.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](https://github.com/aureliocpr-ctrl/verimem/blob/main/CONTRIBUTING.md). Development
setup:

```bash
git clone https://github.com/aureliocpr-ctrl/verimem && cd verimem
pip install -e ".[dev]"
pytest -q
```
