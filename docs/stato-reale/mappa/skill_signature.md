# `verimem/skill_signature.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_find_duplicate_skills
test che nominano il tool     1 file
test che nominano il modulo   1 file
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
| 1 | `verimem/skill_signature.py:18` `_normalize` | funzione: (nessun docstring) | `verimem/dentate_gyrus.py:101`; `verimem/hippo_pagerank.py:116`; `verimem/hippo_pagerank.py:124` (+8) | `tests/test_context_engine.py`; `tests/test_dentate_gyrus.py`; `tests/test_recall_by_context.py` (+2) | - | NON MISURATO | - |
| 2 | `verimem/skill_signature.py:24` `compute_signature` | funzione: SHA1 of normalized trigger+body. 8-char prefix. | `verimem/skill_signature.py:37`; `verimem/skill_signature.py:55` | `tests/test_skill_signature.py` | - | NON MISURATO | - |
| 3 | `verimem/skill_signature.py:33` `find_duplicate_skills` | funzione: Group skills by signature; return groups with size >= 2. | `verimem/curate_pipeline.py:6`; `verimem/curate_pipeline.py:20`; `verimem/curate_pipeline.py:40` (+10) | `tests/test_curate_pipeline.py`; `tests/test_find_duplicate_facts.py`; `tests/test_find_duplicates.py` (+2) | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
