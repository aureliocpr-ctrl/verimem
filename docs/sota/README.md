# SOTA gap-analysis docs — HippoAgent

This directory collects state-of-the-art gap-analysis documents that
compare HippoAgent's current primitives against established literature
and propose concrete follow-up cycles. Each doc follows the same
template: motivation → existing primitives → SOTA candidates →
recommended design → gap analysis with follow-up cycles + falsifiable
hypothesis → caveats → references.

## Quick index

| # | File | Cycle | Closes | Companion impl |
|---|------|-------|--------|----------------|
| 1 | [L0-L3 anti-confab layers](L0-L3-anti-confab-layers.md) | 180 | task #66 | cycles 181 (L1 orphan detector), 183 (FIX family), 184 (gate wire) |
| 2 | [Community detection (Louvain / channels)](community-detection-channel-pattern.md) | 185 | task #67 | cycle 186 (`detect_communities`), 187 (dream hook) |
| 3 | [Highway nodes + PageRank cache](highway-nodes-pagerank-cache.md) | 188 | task #68 | cycles 189 (`get_highway_nodes`), 198 (cache) |
| 4 | [Multi-signal fusion (RRF / LTR)](multi-signal-fusion.md) | 190 | task #69 | cycles 191 (`rrf_fuse`), 196 (rank builders), 197 (`fuse_recall`), 199 (bench), 202 (vs hybrid) |
| 5 | [Temporal evolution + narrative](temporal-evolution-narrative.md) | 192 | task #70 | cycles 193 (`reconstruct_narrative`), 194 (`snapshot_at_time`), 195 (`decay_score`) |
| 6 | [Cross-encoder reranking](cross-encoder-reranking.md) | 203 | (new) | cycle 204 (`rerank_candidates`) |

## Cross-references between primitives

The implementations naturally compose. Suggested wiring:

```
                                                                           
  query                                                                    
    │                                                                      
    ▼                                                                      
  ┌──────────────────────┐    cosine                                       
  │  recall_hybrid       │ ────────┐                                       
  │  (cycle #161)        │         │                                       
  └──────────────────────┘         │                                       
                                   ▼                                       
                            ┌─────────────────┐                            
                            │  rrf_fuse       │ ←─ rank_list_builders      
                            │  (cycle 191)    │    (cycle 196):            
                            └─────────────────┘    recency / confidence /  
                                   │                recency_decayed        
                                   ▼                                       
                            ┌─────────────────┐                            
                            │  rerank_        │ ←─ ms-marco-MiniLM         
                            │  candidates     │    (cycle 204)             
                            │  (cycle 204)    │                            
                            └─────────────────┘                            
                                   │                                       
                                   ▼                                       
                            top-N final result                             
                                                                           
  Aside (Auto-Dream cycle every 30min):                                    
                                                                           
  ┌──────────────────────┐                                                 
  │ active_learning      │ → stuck_hook ─┐                                 
  │ select_stuck_cand    │   (cycle 175.1)│                                
  │ (cycle 175)          │                ▼                                
  └──────────────────────┘     ┌──────────────────────┐                    
                                │ _propose_via_engram  │                    
  ┌──────────────────────┐     │ Auto-Dream worker    │                    
  │ community_detector   │ →   │ (cycle 175.1 + 187)  │                    
  │ (cycle 186)          │     └──────────────────────┘                    
  └──────────────────────┘                                                 
        │                                                                  
        ▼                                                                  
  highway_nodes (cycle 189) → betweenness_cache (cycle 198)                
```

## Falsifiable hypotheses summary

The docs propose 6 falsifiable hypotheses that future pilot cycles
should test:

- **H1 (cycle 175 / 175.1)**: stuck-list retry lifts candidate→
  promoted conversion from 4.3% → > 10% in 20 Auto-Dream cycles.
- **H2 (cycle 185)**: community-aware skill synthesis produces higher
  Bayesian fitness than greedy-pairwise consolidate.
- **H3 (cycle 188)**: PPR-cache recall fast-path improves recall@5 ≥
  10% absolute vs hybrid.
- **H4 (cycle 190)**: RRF-4-signal recall improves recall@5 ≥ 5%
  absolute vs cycle-161 hybrid.
- **H5 (cycle 192)**: time-decay (half-life=14d) improves recall@5 on
  recent subset ≥ 8% without degrading older subset > 3%.
- **H6 (cycle 203)**: cross-encoder rerank on top-20 hybrid
  candidates improves recall@5 ≥ 8% absolute.

**Common blocker**: all hypotheses except H1 require a 50-query
held-out benchmark with ground-truth labels. Not built yet (cycle
200+ scope).

## Authoring guidelines for new SOTA docs

When you add `docs/sota/<topic>.md`:

1. Start with a §1 motivation rooted in a specific HippoAgent
   limitation (NOT generic).
2. §2 must list existing primitives BY FILE PATH so future cycles
   can grep.
3. §3 SOTA candidates → table with model size / params / pros / cons.
4. §4 design — API sketch with concrete signature.
5. §5 gap analysis table + acceptance criteria + at least 1
   falsifiable hypothesis with PASS/FAIL threshold.
6. §6 Caveat A1 — what's NOT empirically verified yet.
7. §7 references — both code paths and external papers.

Update this README's "Quick index" + the cross-references diagram.
