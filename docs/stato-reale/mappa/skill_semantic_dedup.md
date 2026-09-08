# `verimem/skill_semantic_dedup.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

⛔ **NESSUN CHIAMANTE NEL PRODOTTO.** Il righello non trova né un
tool MCP né un'altra porta; l'unica occorrenza del nome in
`verimem/` è un **commento** (`skill_name_dedup.py:19`).

Ha però un file di test dedicato (`tests/test_skill_semantic_dedup.py`): ⇒ **testato e non usato**, e la
suite verde fa credere che il prodotto lo esegua.

📎 Non è nuovo: `docs/MCP_DEAD_SURFACE_AUDIT_2026-05-17.md` — un
audit di quattro mesi fa — misurava «207 tool dichiarati, 83
usati almeno una volta (40%)» e già lo elencava.

**Verdetto: MAI CHIAMATA** per le sue funzioni pubbliche.
Propongo la rimozione **oppure** il cablaggio a un tool; non
decido io e non lo tocco (regola 2 del mandato).

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill_semantic_dedup.py:64` `load_skills_with_embeddings` | funzione: Join ``SkillLibrary.all()`` with the persisted ``trigger_embedding``. | `verimem/skill_semantic_dedup.py:39`; `verimem/skill_semantic_dedup.py:152`; `verimem/skill_semantic_dedup.py:268` | `tests/test_skill_semantic_dedup.py` | - | NON MISURATO | - |
| 2 | `verimem/skill_semantic_dedup.py:96` `load_episode_reference_counts` | funzione: Count how many episodes reference each skill_id via skills_used JSON. | `verimem/skill_semantic_dedup.py:43`; `verimem/skill_semantic_dedup.py:154`; `verimem/skill_semantic_dedup.py:269` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_semantic_dedup.py:123` `_classify_pair` | funzione: Tag a duplicate pair by reference imbalance. | `verimem/skill_semantic_dedup.py:226` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/skill_semantic_dedup.py:140` `find_semantic_duplicate_skills` | funzione: Find pairs of skills whose trigger embeddings are nearly identical. | `verimem/skill_semantic_dedup.py:47`; `verimem/skill_semantic_dedup.py:267` | `tests/test_skill_semantic_dedup.py` | - | NON MISURATO | - |
| 5 | `verimem/skill_semantic_dedup.py:260` `_fitness` | funzione: (nessun docstring) | `verimem/skill_semantic_dedup.py:211`; `verimem/skill_semantic_dedup.py:216`; `verimem/skill_semantic_dedup.py:217` (+1) | nessuno | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
