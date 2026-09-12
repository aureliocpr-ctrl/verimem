# `verimem/skill_drafts_list.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_skill_drafts_list
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
| 1 | `verimem/skill_drafts_list.py:26` `list_persisted_drafts` | funzione: List persisted draft batches, newest first. | `verimem/mcp_server.py:10815`; `verimem/mcp_server.py:10816`; `verimem/skill_drafts_list.py:109` | `tests/test_skill_drafts_list.py` | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
