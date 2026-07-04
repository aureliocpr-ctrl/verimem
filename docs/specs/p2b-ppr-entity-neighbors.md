# Spec P2.b — PPR Retrieval + Entity Edges + Neighbors

> Stato: paper-first, ≤300 parole core. NO implementazione finché RED.
> Build on P2.a (commit 12fa4ff): `entities` + `entity_aliases` +
> `entity_facts` con UNIQUE INDEX Unicode-safe su name_norm.
> Pattern HippoRAG: igraph prpack damping=0.5; usiamo `networkx`
> (già in pyproject, prpack-equivalent via `nx.pagerank`).

## Obiettivo

P2.a espone solo lookup atomico entity-by-name. Manca navigazione
multi-hop: "entity vicine di X" e ranking PPR (Personalized
PageRank) da un set di query entity. P2.b chiude questa modalità.

## Schema delta (additivo, migration v5)

```
entity_edges
  src_entity     TEXT NOT NULL  FK entities.id  (cascade delete)
  dst_entity     TEXT NOT NULL  FK entities.id  (cascade delete)
  predicate      TEXT NOT NULL  (es. "co-occurs", "authored", ...)
  weight         REAL NOT NULL DEFAULT 1.0
  source_fact_id TEXT NULL      (FK semantic.facts — soft, no FK
                                  cross-DB, solo tracking)
  created_at     REAL NOT NULL
  PRIMARY KEY (src_entity, dst_entity, predicate)
```

Indexes: `idx_edges_src`, `idx_edges_dst`. Backward-compat: nessuna
tabella esistente modificata.

## API MCP nuove (3 tool, no LLM nel happy path)

- `hippo_entity_link(src, dst, predicate, weight=1.0, source_fact_id=None)`
  → `{ok, edge_id}`. Manual override / seed pipeline.
- `hippo_entity_neighbors(entity_id|name, k=10, hops=1)`
  → `{entity, neighbors: [{entity, predicate, weight, distance}]}`.
  BFS bounded hops (k limita risultato finale).
- `hippo_ppr_retrieve(query_entities: list[str|id], damping=0.5,
  k=20)` → `{ranked: [{entity_id, score}], facts: [fact_id], graph_size}`.
  `nx.pagerank(G, alpha=damping, personalization=dict.fromkeys(seed,1.0))`,
  top-k entity + fact_id aggregati da `entity_facts`.

## TDD plan (5 RED test minimi)

1. RED — `add_edge` (src,dst,predicate) idempotente; UNIQUE
   constraint su tripletta.
2. RED — `neighbors(X, hops=1)` ritorna i diretti adiacenti, con
   distance=1.
3. RED — `neighbors(X, hops=2)` esplora 2 hop; cap k limita output.
4. RED — `ppr_retrieve([X])` su grafo `X→Y` con weight 1.0:
   ranking `[X, Y]` (X più alto: own-mass personalization).
5. RED — `ppr_retrieve` determinismo: stesso input → stesso ranking
   in 3 chiamate consecutive.

## Non-goals (P2.b)

- NON OpenIE/auto-extraction (P2.c).
- NON skill .md (rimandato a P2.d-bis post-merge).
- NON multi-hop reasoning >2 hop nel happy path (P3 plan_strips).
- NON Italian-native NER (P4 opzionale).

## Critic gate plan

Round adversariale con critic-orchestrator v0.3.0 (debiased,
commit 03ed212) PRIMA del commit:
- falsification: i 5 RED test isolano davvero la feature?
- caller_verification: i 3 nuovi tool MCP sono raggiungibili da
  dispatch + visibili in `_EXPECTED_TOOLS`?
- counterexample: race su add_edge concorrenti, cicli nel grafo,
  query_entities con id sconosciuto, damping fuori range [0,1].
