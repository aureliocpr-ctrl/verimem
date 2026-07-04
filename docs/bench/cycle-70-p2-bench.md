# P2 Entity-Centric KG — Real Benchmark Results (cycle #70)

> Date: 2026-05-15 (notte tarda → mattina). Run: `python scripts/bench_p2_entity_kg.py`. Raw JSON: `cycle-70-p2-bench.json`.
>
> Zero LLM call, zero API cost. Riproducibile (random seeds fissi).

## Onestà preliminare

I numeri sotto sono **misurazioni empiriche reali**, NON stime. Sono onesto sulle limitazioni:

1. **Bench A**: il corpus produzione `~/.engram` ha **0 entity in entity_kg.db**. Non ho seedato manualmente né eseguito P2.c OpenIE sul corpus. Quindi `hippo_entity_get` hit_rate = 0% è **atteso**, NON è un bug: la tabella è strutturalmente vuota. Quando popolata (via `hippo_entity_link` manuale o `hippo_extract_entities` su episodes), il numero salirà.
2. **Bench B/C**: usano grafi sintetici (random Erdős-Rényi). I numeri valgono per scaling structurale di networkx pagerank, non per il corpus produzione reale.

---

## Bench A — recall@k (corpus reale ~/.engram, 10 query)

Query set: `Tonegawa`, `P2.a`, `critic-orchestrator`, `Müller`, `HippoRAG`, `cycle #70`, `engram`, `self_model`, `entity_kg`, `skill`.

| Modalità | Hit rate | Mean latency |
|---|---|---|
| `entity_get` (P2.a) | **0.0 %** (KG vuoto) | 2.57 ms |
| `facts_search` (SemanticMemory keyword) | **100.0 %** @k=1 | 5.62 ms |
| `episodic_recall` (keyword over `task_text + final_answer`) | **100.0 %** | 13.44 ms |

**Interpretazione onesta**:

- `facts_search` e `episodic_recall` coprono tutte le 10 query → il corpus produzione contiene già fact + episodi per ognuna (è la fonte semantic + episodic, attiva da cycle #51+).
- `entity_get` è **structurally empty**: nessuna entity_kg row in produzione yet. Roadmap: P2.c-bis (script seed retroattivo che chiama `hippo_extract_entities` sugli episodi storici) o popolazione manuale via `hippo_entity_link` durante uso quotidiano.
- Latency entity_get 2.5 ms anche su empty KG → no warm-up cost.

---

## Bench B — PPR determinismo strict (10 run, grafo sintetico 50 nodi/100 edge)

| Metric | Value |
|---|---|
| Run count | 10 |
| `deterministic_byte_identical` | **True** ✅ |
| Discrepancies | 0 |
| Mean latency | 79.41 ms |
| Median latency | ≈ 79 ms |

10 chiamate consecutive con stesso seed `[E000, E001, E002]`, damping=0.5, k=20 → ranking + score sono **byte-identici**. Tie-break su `entity_id` asc + power-iteration con `tol=1e-9, max_iter=200` garantiscono full determinismo. Ottimo per regression test e LRU cache.

---

## Bench C — PPR latency scaling (Erdős-Rényi, density avg-degree 5)

| n_nodes | n_edges | min ms | mean ms | max ms |
|---|---|---|---|---|
| 10 | 50 | 25.65 | 27.47 | 28.97 |
| 100 | 500 | 45.54 | 51.57 | 67.16 |
| 500 | 2 500 | 50.41 | 53.39 | 59.14 |
| 1 000 | 5 000 | 65.27 | 70.16 | 73.99 |

Scaling **sub-linear** in n_nodes (da 10× a 100× crescita: latency × 2.5, non × 10): power-iteration `nx.pagerank` con sparse matrix è O(k·E) dove k = numero iterazioni a convergenza (qui ~30-50 per `tol=1e-9`). Per grafi corpus realistico (qualche centinaio di entity in produzione finale), latency attesa **< 100 ms** anche sul cold path.

---

## Conclusioni cycle #70 P2

1. **PPR è production-ready** per uso interattivo (< 100 ms) e deterministico (byte-identical).
2. **entity_get è bloccato dalla popolazione del KG** — non un bug, una "to-do" architettturale.
3. **facts_search + episodic_recall coprono già il caso d'uso "what do I know about X"** con hit_rate 100% sul corpus attuale → P2.a/b/c sono **complementari**, non sostitutivi, finché il KG non è popolato.
4. **Roadmap immediata**: P2.c-bis seed pipeline retroattiva (LLM call on demand sugli episodi storici) — opt-in costoso, scelta utente.
