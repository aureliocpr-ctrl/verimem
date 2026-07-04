# Cycle #109 — Handoff per restart Claude

**Date**: 2026-05-16 ~13:00 Italia
**Author**: Aurelio + Claude
**Branch**: `cycle109-provenance-fact-schema-v3`
**Commits**:
- `53c2abe` — S1 schema v2 provenance (Fact dataclass + migration v1→v2)
- `612352e` — S3 corpus migration script + APPLY corpus reale
- `7d95faf` — S2 MCP hippo_remember accepts provenance fields

## Background (perché esiste questo cycle)

Aurelio ha osservato durante loop notturno 2026-05-15/16 che la memoria
HippoAgent **amplifica hallucinazione** invece di mitigarla. Ricerca
empirica conferma:

- **MemoryGraft Dec 2025** (arXiv 2512.16962): persistent memory con
  embedding-only similarity ha 47.9% poisoning rate cross-session
- **ProvSEEK Aug 2025** (arXiv 2508.21323): pattern verification-first
  ottiene +34% precision vs vanilla RAG
- **Memory survey Mar 2026** (arXiv 2603.07670): documentato failure mode
  "reflective contamination — one bad write pollutes downstream"

## Cosa è cambiato

### 1. Schema v2 provenance (S1)

`engram/semantic.py`:
- 3 nuove colonne SQL: `verified_by` (JSON list str), `status` (NOT NULL
  default 'model_claim'), `source_signature` (TEXT NULL)
- Fact dataclass estesa con 3 fields backward-compatible
- `SemanticMemory.store()` valida `status` contro `_VALID_STATUSES`
- Migration `_migrate_v1_to_v2` aggiunge colonne + marca rows pre-esistenti
  come `legacy_unverified`

Valori `status` enum:
- `verified` — backed by ≥1 verified_by tool-call ref
- `model_claim` — DEFAULT — nessuna verification (fact creato da modello)
- `provisional` — research finding/hypothesis (URL provenance ma non
  empirico re-runnable)
- `legacy_unverified` — fact pre-cycle-109 (migration default)

### 2. MCP hippo_remember accept provenance (S2)

`engram/mcp_server.py` `hippo_remember` tool:
- Schema input esteso con `verified_by` (array string), `status` (enum),
  `source_signature` (string)
- Dispatch handler estrae i 3 nuovi param + passa a `_build_fact`
- Echo-back nella response per audit trail

### 3. Script migration corpus reale (S3)

`scripts/cycle109_migrate_corpus_provenance.py`:
- Dry-run default (no writes)
- `--apply` ALTER TABLE ADD COLUMN + UPDATE legacy_unverified +
  CREATE INDEX
- Idempotent (re-run = no-op)

## Stato corpus Aurelio dopo migration

Eseguito 2026-05-16 12:40 con backup
`~/.engram/semantic/semantic.db.cycle109-backup-pre-provenance-migration`:

| Status | Count | % | Esempio |
|---|---:|---:|---|
| `legacy_unverified` | 815 | 95.0% | tutti fact pre-cycle-109 |
| `verified` | 36 | 4.2% | 28 cycle-103 rebrand (SQL) + 4 superseded + 4 episode-finale |
| `provisional` | 7 | 0.8% | 7 research findings da paper (URL provenance) |
| **TOTALE** | **858** | **100%** | |

## Cosa testare dopo restart Claude

### Test 1: hippo_remember senza provenance → status='model_claim'

Atteso: status='model_claim', verified_by=[]

```python
# Invoke hippo_remember tool
hippo_remember(
    proposition="this is a model claim without evidence",
    topic="test/cycle109-handoff",
    confidence=0.9
)
# Response should include: status='model_claim', verified_by=[]
```

### Test 2: hippo_remember CON provenance → status='verified'

```python
hippo_remember(
    proposition="HippoAgent has exactly 858 facts in corpus 2026-05-16",
    topic="test/cycle109-verified",
    confidence=0.95,
    verified_by=["bash:sqlite3:SELECT COUNT FROM facts:858"],
    status="verified",
    source_signature="cycle109-handoff-test"
)
# Response should include: status='verified', verified_by=[...]
```

### Test 3: hippo_remember status invalid → rejected

```python
hippo_remember(
    proposition="invalid status test",
    topic="test/invalid",
    status="totally_bogus"
)
# Should return error _err with outcome 'rejected_invalid_status'
```

### Test 4: hippo_facts_recall returns provenance

```python
hippo_facts_recall(query="858 facts cycle109", k=3)
# Each fact in response should have status + verified_by fields
```

### Test 5: corpus migration idempotency

```bash
python scripts/cycle109_migrate_corpus_provenance.py
# Should print "ALREADY MIGRATED — nothing to do."
```

## Test count globali

Branch `cycle109-provenance-fact-schema-v3` aggiunge:
- `tests/test_fact_provenance.py` — 16 test (schema + migration + dataclass)
- `tests/test_mcp_remember_provenance.py` — 9 test (MCP wire-up)
- Aggiornato `tests/test_migrations.py` (1 assertion bump)

**35/35 new tests GREEN.** Full suite: 2580 passed (3 pre-existing fail
noti: `test_real_provider_smoke[anthropic]`, `test_outcome_timeseries`,
`test_mcp_hosted_mode`).

## Open issues / next cycle

1. **Topic field ritorna "" dalla response hippo_remember** (bug noto da
   loop notturno): la response del tool ritorna `"topic": ""` anche quando
   il param `topic` è passato. Indipendente da cycle109 ma da investigare.

2. **PR #43 (cycle 78-88 supersession) ancora OPEN**: il mio cycle109 è
   da `main` non da `cycle88-dashboard`. Quando PR #43 mergia, schema
   reale main+#43 sarà v2 supersession + colonne provenance = v3 logico.
   Cycle110 reconciliation per allineare schema_version stamping.

3. **815 legacy_unverified non riclassificati**: la maggioranza del
   corpus è ancora indistinta. Manual review necessaria — non scriptable
   senza giudizio umano (alcuni fact NEXUS deep stamattina sono lettura
   mia interpretativa, alcuni sono SQL verificabili, alcuni sono opinioni).
   Suggerimento: review per topic-cluster, promote/demote in batch.

4. **PreToolUse hook hard-block NON implementato**: scelta S2 = soft
   default (model_claim) invece di reject. Discutere con Aurelio se serve
   anche hard block per scenari specifici (es. CI/automation).

5. **Adversarial monitor real-time (Fase 2 research)**: domanda Aurelio
   originale "istanza silenziosa che ti pinga" non implementata. Richiede
   Fase 2 research (AI Safety via Debate Irving 2018, AI Control
   Greenblatt 2024 Anthropic) + design.

## Rollback se qualcosa va male

```bash
# Restore corpus from backup
cp ~/.engram/semantic/semantic.db.cycle109-backup-pre-provenance-migration \
   ~/.engram/semantic/semantic.db

# Revert branch
git checkout main
git branch -D cycle109-provenance-fact-schema-v3
```

## Sources research (per future verifica)

- [Self-RAG (Asai 2023)](https://arxiv.org/abs/2310.11511)
- [Toolformer (Schick 2023)](https://arxiv.org/abs/2302.04761)
- [AlphaGeometry 2 (Trinh et al. 2025)](https://arxiv.org/abs/2502.03544)
- [MemoryGraft (Dec 2025)](https://arxiv.org/abs/2512.16962)
- [Memory for Autonomous LLM Agents survey (2026)](https://arxiv.org/html/2603.07670v1)
- [ProvSEEK (Aug 2025)](https://arxiv.org/html/2508.21323v2)
