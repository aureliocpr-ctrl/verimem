# `verimem/skill_emergence_detector.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_emerging_skills_register
tool MCP        hippo_emerging_skills_draft
test che nominano il tool     2 file
test che nominano il modulo   5 file
```

⇒ **la catena è completa**: il modulo è esposto e la porta ha
un presidio. È il caso di **42 moduli su 47** — la famiglia
`skill*` è la meglio presidiata della mia parte.

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill_emergence_detector.py:58` `_embeddings_for_ids` | funzione: Fetch embeddings as a (k, 384) float32 array. ``None`` on | `verimem/second_pass_louvain.py:87`; `verimem/second_pass_louvain.py:120`; `verimem/skill_emergence_detector.py:337` | `tests/test_skill_emergence_dim_r3.py` | - | NON MISURATO | - |
| 2 | `verimem/skill_emergence_detector.py:95` `_topic_for_ids` | funzione: (nessun docstring) | `verimem/skill_emergence_detector.py:319` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_emergence_detector.py:116` `_cohesion_score` | funzione: Mean cosine of each row to the centroid. Higher = more cohesive. | `verimem/skill_emergence_detector.py:341` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/skill_emergence_detector.py:130` `_suggest_skill_name` | funzione: (nessun docstring) | `verimem/skill_emergence_detector.py:349` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/skill_emergence_detector.py:142` `detect_emerging_skills` | funzione: Detect emergent skill candidates in the fact graph. | `verimem/auto_dream_worker.py:133`; `verimem/auto_dream_worker.py:140`; `verimem/auto_dream_worker.py:293` (+14) | `tests/test_auto_dream_stable_partition_envvar.py`; `tests/test_both_cures_interaction.py`; `tests/test_hybrid_mode.py` (+3) | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
