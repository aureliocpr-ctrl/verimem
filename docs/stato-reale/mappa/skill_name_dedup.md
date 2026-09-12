# `verimem/skill_name_dedup.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

**Nessun tool MCP** — ma il modulo è **vivo** su un'altra porta:
`cli.py:2968` — la CLI, non MCP.

🔑 «Non esposto da MCP» non è «non esposto». Misurando solo
`mcp_server.py` avrei consegnato un falso reperto.

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill_name_dedup.py:30` `find_name_duplicate_groups` | funzione: Ritorna gruppi di skill con (name, status) identici, sorted by count desc. | `verimem/skill_name_dedup.py:99`; `verimem/skill_name_dedup.py:152` | `tests/test_skill_name_dedup.py` | - | NON MISURATO | - |
| 2 | `verimem/skill_name_dedup.py:67` `dedup_skills_by_name` | funzione: Retire skill duplicate per nome. | `verimem/cli.py:2968`; `verimem/cli.py:2970`; `verimem/skill_name_dedup.py:152` | `tests/test_skill_name_dedup.py`; `tests/test_skill_name_dedup_store_failure.py` | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
