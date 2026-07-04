# Spec P2 — Entity-Centric Knowledge Graph

> Stato: paper-first, ≤300 parole core spec. NO codice ancora.
> Origine: ricerca SOA 2026-05-14
> (`docs/research/entity-memory-state-of-art-2026-05.md` +
> `docs/research/repos-deep-dive-2026-05.md`). Pattern da rubare:
> HippoRAG PPR (igraph prpack, damping=0.5) + OpenIE 2-step (NER →
> triple) senza parser eseguibile su LLM output + AriGraph
> episodic↔semantic edges.

## Obiettivo

Engram oggi indicizza facts per **topic** (stringa libera) e per
embedding semantico globale. Manca la navigazione per **entità**:
"dammi tutto quello che sai su X", "quali fact connettono X e Y?",
"se ti dico A, ricostruisci il sottografo causale".

P2 introduce un secondo livello di indicizzazione: ogni fact diventa
una tripla `(subject, predicate, object)` con subject/object
agganciati a una `entities` table. Retrieval via Personalized
PageRank sul grafo entity-fact-episode.

Sblocca: ricerca conversazionale tipo "cosa abbiamo deciso con
Marco?" o "racconta tutta la storia di cycle #70".

## Schema SQLite (additivo, no breaking)

```
entities       (id PK, canonical_name, type, first_seen_episode, attrs_json)
entity_aliases (entity_id FK, alias)                -- "Tonegawa", "S. Tonegawa"
entity_facts   (fact_id FK, entity_id FK, role)     -- role ∈ {subject, object}
entity_edges   (src_entity FK, dst_entity FK,
                predicate, weight, source_fact_id)  -- weighted, directed
```

Backward-compat: `facts` table invariata. Tutti gli inserimenti
nuovi popolano anche `entity_*`. Migrazione lazy dei facts esistenti
in batch idempotente.

## API MCP proposte (4 tool, no LLM call nel happy-path)

- `hippo_entity_get(name_or_alias) → {entity, facts[], edges[]}`
- `hippo_entity_neighbors(entity_id, k=10, hops=1) → graph subgraph`
- `hippo_ppr_retrieve(query_entities[], damping=0.5, k=20) → ranked
  facts + episodes` (HippoRAG core, igraph prpack)
- `hippo_entity_link(fact_id, entities[]) → ok` (manual override per
  correggere errori NER)

## Pipeline OpenIE (1 tool dedicato, opt-in LLM)

`hippo_extract_entities(text, mode="ner+triple") → {entities[],
triples[]}`. Implementazione 2-step (NER → triple) sul pattern
HippoRAG ma con `json.loads` strict NO parser eseguibile su LLM
output (anti-pattern documentato in HippoRAG
openie_openai.py). Chiamato esplicitamente da `hippo_record_episode`
quando l'episodio passa una soglia di ricchezza testuale.

## Test plan TDD (4 RED test minimi)

- RED: insert fact con subject "Tonegawa" → entity_facts ha 1 riga.
- RED: query `entity_get("Tonegawa")` su corpus con 2 fact → restituisce
  entrambi.
- RED: PPR retrieval su query_entities=[Tonegawa] → ordering
  deterministico, top-k stabile.
- RED: alias lookup ("S. Tonegawa" → stessa entity di "Tonegawa").

## Non-goals (P2)

- NON multi-hop reasoning >2 (P3 farà via plan_strips).
- NON Italian-native NER (gazetteer P4 opzionale).
- NON LLM-based re-ranker (PPR è deterministic enough).
- NON breaking di `facts.topic` (resta come secondo asse).

## Successivi

P2 sblocca recall conversazionale entity-first. Pattern PPR riusabile
da P3 (self_model multi-anchor: ogni anchor identity è un entity-node
con peso temporale).
