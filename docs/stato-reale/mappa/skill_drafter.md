# `verimem/skill_drafter.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

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
| 1 | `verimem/skill_drafter.py:86` `_fetch_propositions` | funzione: Return ``{fact_id: proposition}`` for IDs found; missing IDs absent. | `verimem/skill_drafter.py:183` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/skill_drafter.py:108` `_extract_keywords` | funzione: Frequency-rank tokens across propositions; filter stopwords + short. | `verimem/skill_drafter.py:77`; `verimem/skill_drafter.py:188`; `verimem/skill_promote_from_emerging.py:92` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_drafter.py:132` `_truncate` | funzione: Cut text to <= limit chars, append ellipsis if cut. | `verimem/self_model_refresh.py:116`; `verimem/skill_drafter.py:213`; `verimem/trajectory_render.py:62` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/skill_drafter.py:140` `draft_skill_from_community` | funzione: Produce a deterministic text DRAFT of an emergent skill candidate. | `verimem/auto_dream_worker.py:132`; `verimem/auto_dream_worker.py:156`; `verimem/auto_dream_worker.py:292` (+19) | `tests/test_mcp_emerging_skills.py`; `tests/test_parallel_drafter.py`; `tests/test_skill_draft_persist.py` (+1) | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
