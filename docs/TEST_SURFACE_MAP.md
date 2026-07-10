# Verimem — full use-surface map (mandate: "testa la più ampia superficie")

Aurelio 2026-07-10: consider EVERY possible use case, stress the widest
surface, no blind corner. This is the systematic backbone: each cell has a
status — ✅ verified / ⚠️ known fall / ⏳ untested — and untested high-risk
cells become the atomic test queue. Legend for source: F1 = tonight's virgin
corpora; prior = shipped+tested before F1.

The product's own claim (verimem.com): a TRUSTED memory engine — it stores,
recalls WITH provenance, and defends the truth (contradictions, staleness,
poisoning, hallucination). So the surface is not just "does recall work" but
"does every PROMISE hold on every INPUT for every USER".

## Axis A — Verticals / personas (WHO)

| vertical | core need | status | note |
|---|---|---|---|
| AI-agent long-term memory | store/recall agent facts across sessions | ✅ prior+F1 | the built-for case; MuSiQue/MSC proxy |
| Personal memory assistant | ingest my past chats, "remember when…" | ⚠️ F1 | MSC hit@1 0.39 weak; cold-start/import untested (S6) |
| Research / knowledge | long PDFs, papers, books | ⚠️→✅ F1 | S2 fixed+proven (chunk); OCR/formatting noise untested |
| Legal | cases, contracts, exact citation | ⏳ | DocumentIndex cites offsets (prior); no legal-corpus stress |
| Customer support / KB | FAQ, tickets, dedup, freshness | ⏳ | dedup+staleness exist; not stressed as a KB |
| Coding assistant | codebase, commits, tech decisions | ⏳ | code as content UNTESTED (tokenizer, symbols) |
| Enterprise multi-tenant | isolated per-customer memory | ⏳ | topic_prefix scoping exists; leak not adversarially tested |
| Compliance / audit | provenance trail, decision-chain | ✅ prior | explain + decision-chain shipped+dogfooded |
| Healthcare / sensitive | PII, precision, redaction | ⏳ | secret redaction ✅; PII policy + precision unstressed |

## Axis B — Content types (WHAT is stored)

| type | status | risk if untested |
|---|---|---|
| short facts | ✅ F1 | — |
| long documents | ⚠️→✅ F1 (S2) | silent truncation (fixed) |
| conversations | ⚠️ F1 (MSC) | weak conversational recall |
| **code** | ⏳ | symbols/camelCase/no-prose break embeddings + gates |
| **structured data / tables / JSON** | ⏳ | row facts, numeric fields — retrieval ≠ lookup |
| **dates / numbers / units** | ⏳ | "in 1998", "$3.2M", "40kg" — embedding is weak on exact numerics |
| multilingual | ✅ F1 (S1 gate) | recall cross-lingual not end-to-end tested |
| PDF/extracted files | ⏳ | file_extract.py exists; extraction noise untested |
| email / transcripts | ⏳ | headers/quoting/speaker turns |
| emoji / unicode edge | ✅ F1 (probe) | safe |

## Axis C — Write path (HOW content gets IN)

| operation | status | note |
|---|---|---|
| single add | ✅ | — |
| batch / bulk import | ⏳ | throughput, partial-failure atomicity |
| document ingest (chunk) | ✅ F1 | chunker proven (S2) |
| **conversation import (cold-start)** | ⏳ (S6) | conversation_ingest.py — never F1-stressed |
| update / versioning | ✅ prior | supersession |
| delete / forget | ✅ prior | forget + undo |
| dedup / near-dup | ⏳ | exact dedup exists; near-dup on real corpus untested |
| **concurrent writers** | ⏳ | multi-process store; SQLite lock behavior |

## Axis D — Query / retrieval (HOW content comes OUT)

| query type | status | risk |
|---|---|---|
| factual | ✅ F1 | — |
| multi-hop | ⚠️ F1 (C3) | bridge hop wall (graph #1 is the lever) |
| **temporal ("what in March?")** | ⏳ | bi-temporal exists; NOT stressed on real timestamps |
| **aggregation / counting ("how many times…")** | ⏳ | HIGH RISK: retrieval returns top-k, does NOT count — likely a universal fall |
| **negation ("what did I NOT say")** | ⏳ | embeddings ignore negation |
| comparative / superlative | ⏳ | "the biggest", "before X" |
| provenance ("how do I know?") | ✅ prior | explain |
| decision ("why did we choose?") | ✅ prior | decision-chain |
| blank / malformed | ✅ F1 (S5) | returns [] |
| cross-lingual query | ✅ F1 (probe) | works on small probe; not measured |

## Axis E — Trust guarantees (the PROMISES)

| promise | status | note |
|---|---|---|
| contradictions / reconcile | ⏳ (S4 NEXT) | reconcile+source-trust behind flags; virgin conflict corpus untested |
| staleness / obsolescence | ✅ prior | valid_until, bi-temporal — not stressed on real churn |
| untrusted sources | ✅ prior (flag) | source-trust mini-world; real multi-source untested |
| memory poisoning | ✅ prior+F1 | red-team 0.9677, unchanged post-C4 |
| sycophancy | ✅ prior | closed on this model |
| hallucination-on-recall | ✅ prior | self-calibrating floor |
| write confabulation | ✅ prior+F1 | gate + provenance router |

## Axis F — Scale / ops

| dimension | status | note |
|---|---|---|
| 10k facts | ✅ F1 (S3) | recall latency flat 388→439ms 1k→10k (encode-dominated), RAM model-bound (+60MB for 9k facts) |
| **100k+ facts** | ⏳ | cosine is brute-force O(N) — the scaling risk |
| concurrent multi-user | ⏳ | — |
| multi-tenant isolation (leak) | ⏳ | topic_prefix; adversarial leak untested |
| RAM footprint | ✅ prior | server 590→108MB (bug fixed) |
| cold-start / persistence / recovery | ⏳ | crash mid-write, WAL recovery |

## Axis G — Integration

| surface | status |
|---|---|
| MCP server | ✅ prior |
| REST gateway (multi-tenant) | ✅ prior |
| Python SDK | ✅ prior |
| embedding model swap | ✅ prior (dim guard) |
| multi-provider answerer | ⏳ (weak-model sycophancy reopen) |

## Axis H — Adversarial / security

| vector | status |
|---|---|
| injection at write | ✅ F1 (red-team) |
| injection in query | ✅ F1 (S5) |
| exfiltration payloads | ✅ prior |
| **cross-tenant leak** | ⏳ |
| PII / secret redaction | ✅ prior (secrets); PII ⏳ |
| homoglyph / unicode smuggle | ✅ F1 (C4 sanitize) |

## Atomic test queue (by risk × universality, highest first)

1. **Aggregation / counting** (D) — likely a universal fall: users expect
   "how many times did I mention X?" and retrieval cannot count. Probe first.
2. **S4 contradictions** (E) — the brand's central promise, on a virgin
   conflicting corpus, reconcile default vs flag.
3. **Temporal queries** (D) — "what in March / before June" on real dates.
4. **Numbers / dates / units as content** (B) — embedding is weak on exact
   numerics; a finance/legal killer.
5. **Code as content** (B) — coding-assistant vertical.
6. **Cross-tenant leak** (F/H) — security, enterprise blocker.
7. **S6 cold-start / conversation import** (C).
8. **100k scale** (F) — brute-force cosine ceiling.

Each is one atom: probe (measure) → if it falls, TDD fix → re-measure. No cell
ships green without a number.
