# `verimem/skill_exposure_audit.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_skill_exposure_audit
tool MCP        hippo_skill_retire_invisible
test che nominano il tool     1 file
test che nominano il modulo   3 file
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
| 1 | `verimem/skill_exposure_audit.py:54` `CandidateExposure` | classe: Per-skill exposure metric. | `verimem/skill_exposure_audit.py:112`; `verimem/skill_exposure_audit.py:129`; `verimem/skill_exposure_audit.py:183` (+1) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/skill_exposure_audit.py:66` `_cosine_matrix` | funzione: Cosine matrix between rows of a [n×d] and rows of b [m×d]. | `verimem/skill_exposure_audit.py:154`; `verimem/topic_cleanup_suggestions.py:85` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_exposure_audit.py:84` `audit_candidate_exposure` | funzione: Misura quante volte ogni candidate sarebbe entrata nel top-k semantico. | `verimem/mcp_server.py:11392`; `verimem/mcp_server.py:11398`; `verimem/mcp_server.py:11415` (+6) | `tests/test_skill_exposure_audit.py`; `tests/test_skill_exposure_audit_invisible_all_scan68.py` | - | NON MISURATO | - |
| 4 | `verimem/skill_exposure_audit.py:231` `select_invisible_for_retire` | funzione: Seleziona candidate "morte alla nascita" pronte per retire. | `verimem/mcp_server.py:11417`; `verimem/mcp_server.py:11429`; `verimem/skill_exposure_audit.py:365` | `tests/test_skill_exposure_audit.py`; `tests/test_skill_exposure_audit_invisible_all_scan68.py` | - | NON MISURATO | - |
| 5 | `verimem/skill_exposure_audit.py:285` `load_audit_inputs_from_agent` | funzione: Adapter: carica candidate + episodi recenti per audit_candidate_exposure. | `verimem/mcp_server.py:11393`; `verimem/mcp_server.py:11397`; `verimem/mcp_server.py:11416` (+2) | nessuno | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
