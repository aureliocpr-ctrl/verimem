# P3 Anchor Recall Latency Bench (cycle #70 turno 5)

> Date: 2026-05-15. Run: `python scripts/bench_p3_anchor.py`. JSON: `cycle-70-p3-anchor-latency.json`.
>
> Corpus sintetico (seed=70): 5 anchor + 50 entity + 100 edge + 200 fact link.
> Anchor configurati con `half_life_days ∈ {1, 3, 7, 14, 30}` e `age_days ∈ {0, 1, 5, 20, 90}` per coprire range decay realistico (1.0, 0.79, 0.61, 0.37, 0.13).

## Summary (50 runs per mode)

| Mode | p50 ms | p95 ms | p99 ms | mean ms |
|---|---|---|---|---|
| `anchor_recall` (decay + ppr_weighted) | **59.7** | 86.0 | 511.5 | 70.1 |
| `ppr()` (uniform pers, no decay) | 46.0 | 55.5 | 80.8 | 47.5 |
| `facts_for_entity` × 5 (baseline) | 10.1 | 11.2 | 12.0 | 10.2 |

## Findings

1. **`anchor_recall` overhead ≈ +14 ms p50** vs `ppr()`: il costo extra
   è dominato da `list_anchors()` (SELECT WHERE type='anchor' + N
   `get_attrs` per ogni anchor) e dal compute decay
   `2^(-age_days/half_life)`.
2. **p99 outlier 511 ms** è il cold-start `nx.DiGraph` construction
   alla prima chiamata `ppr_weighted` (stesso pattern P2.b documentato
   in `cycle-70-p2-load.md`). Mediana stabile a 60 ms.
3. **`ppr()` diretto** è sub-100 ms p99 → buono per regression test
   determinismo e LRU cache.
4. **`facts_for_entity`** (5 SELECT puri) = 10 ms baseline → SQLite WAL
   + index `idx_entity_facts_entity` paga.

## Interpretazione produzione

- SessionStart hook deve essere **sub-100 ms p95** per non rallentare
  il boot. `anchor_recall` p95=86 ms OK al primo run; cold-start 512 ms
  inaccettabile come bloccante.
- **Mitigazione P3-bis**: cache LRU 5-min su `render_anchor_block`
  invalidata da write (`anchor_set`/`add_edge`). Cache hit → 0 ms.
- **Worst case (cache miss + cold)**: 512 ms una volta ogni 5 min,
  accettabile in async/background hook.

## Roadmap perf

- DiGraph caching in `EntityStore` (invalidato su write) → elimina p99
  outlier. Out-of-scope cycle #70 (premature, ma trackato per future).
- `list_anchors` con JOIN su `entity_attrs` (1 query invece di N+1)
  → -5 ms p50. Trackato come optimization low-priority.

## Conclusione

`anchor_recall` è production-ready per uso interattivo (mean 70 ms).
Il p99 cold-start è documentato e mitigabile via cache. SessionStart
hook P3-bis può chiamare `anchor_recall` direttamente in caso di N
piccolo (≤20 anchor) senza degradare l'UX.
