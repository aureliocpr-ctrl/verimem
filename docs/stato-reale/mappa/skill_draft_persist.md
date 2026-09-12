# `verimem/skill_draft_persist.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

**Nessun tool MCP** — ma il modulo è **vivo** su un'altra porta:
`auto_dream_worker.py:131` — il worker dei sogni.

🔑 «Non esposto da MCP» non è «non esposto». Misurando solo
`mcp_server.py` avrei consegnato un falso reperto.

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill_draft_persist.py:34` `_sanitize_name` | funzione: Make a filename safe: strip path separators, collapse unsafe runs. | `verimem/skill_draft_persist.py:82`; `verimem/skill_draft_persist.py:93` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/skill_draft_persist.py:47` `persist_drafts` | funzione: Write each draft to a timestamped subdirectory of ``root_dir``. | `verimem/auto_dream_worker.py:127`; `verimem/auto_dream_worker.py:131`; `verimem/auto_dream_worker.py:164` (+3) | `tests/test_auto_dream_drafts_persist.py`; `tests/test_skill_draft_persist.py`; `tests/test_skill_drafts_list.py` | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
