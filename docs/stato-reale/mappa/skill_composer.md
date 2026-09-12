# `verimem/skill_composer.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_compose_plan
test che nominano il tool     1 file
test che nominano il modulo   2 file
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
| 1 | `verimem/skill_composer.py:26` `_tokens` | funzione: (nessun docstring) | `verimem/analogy.py:66`; `verimem/bm25_rank.py:124`; `verimem/bm25_rank.py:135` (+51) | `tests/test_due_domande_diverse_stessa_risposta.py`; `tests/test_l_oracolo_non_risponde_su_due_preposizioni.py`; `tests/test_le_interrogative_di_quantita_non_sono_contenuto.py` (+2) | - | NON MISURATO | - |
| 2 | `verimem/skill_composer.py:30` `_jaccard` | funzione: (nessun docstring) | `verimem/coherence_check.py:115`; `verimem/cross_agent_consensus.py:51`; `verimem/episode_clusters.py:65` (+20) | `tests/test_il_flip_giapponese_passa_per_quindici_millesimi.py`; `tests/test_l_oracolo_non_risponde_su_due_preposizioni.py` | - | NON MISURATO | - |
| 3 | `verimem/skill_composer.py:38` `compose_plan` | funzione: Return an ordered plan of skill_ids to apply to `task`. | `verimem/chain_visualize.py:3`; `verimem/mcp_server.py:10471`; `verimem/mcp_server.py:10473` (+1) | `tests/test_skill_composer.py` | - | NON MISURATO | - |
| 4 | `verimem/skill_composer.py:114` `compose_plan._visit` | funzione: (nessun docstring) | `verimem/skill_composer.py:122`; `verimem/skill_composer.py:128` | nessuno | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
