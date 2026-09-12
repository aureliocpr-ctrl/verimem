# `verimem/skill_signature.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

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

---

## 🔴 T45 — il docstring promette tre insensibilità, il codice ne ha due

Docstring `:3-7`, testuale:

> «Normalize trigger+body to detect literal duplicates **regardless of**:
>   - whitespace
>   - case
>   - **leading/trailing punctuation**»

`_normalize` (`:18-22`) fa:

```python
_WHITESPACE.sub(" ", text.strip().lower())
```

`.strip()` **senza argomenti toglie gli spazi, non la punteggiatura**. Predizione
depositata prima di eseguire: A e B reggono, **C no**. Eseguito:

```
OK  A  spazi multipli e a capo → stessa firma     74b628f5c506 == 74b628f5c506
OK  B  maiuscole → stessa firma                   74b628f5c506 == 74b628f5c506
🔴  C  punteggiatura in coda («risposta.» «conciso!»)   74b628f5c506 != 50cc85557a1a
🔴  C' punteggiatura in testa («- quando serve…»)       74b628f5c506 != f78dc9029511
OK  D  skill DIVERSE → firme diverse              74b628f5c506 != eed720a804b1
```

**D è il controllo che rende leggibile il resto**: senza, una `compute_signature`
che restituisse sempre la stessa stringa avrebbe passato A, B e C a pieni voti.

⇒ **NON COME PROMESSO (T45)**. La cura è **o** completare la normalizzazione
(`strip(string.punctuation + whitespace)`) **o** togliere la terza riga dal
docstring — sono due decisioni diverse e non le prendo io (regola 2). Chi
sceglie deve sapere che la prima cambia le firme già calcolate.

### Perché conta, e come si lega all'altro reperto

Due skill identiche che differiscono **solo per un punto finale** non vengono
viste come duplicate dal dedup **letterale**. Il modulo che le prenderebbe è
`skill_semantic_dedup` — che, come misurato nella sua stessa mappa,
**non è chiamato da nessuna riga del prodotto**.

🔑 I due reperti insieme dicono una cosa che nessuno dei due dice da solo: **la
rete contro i duplicati ha una maglia larga sul letterale e la maglia fine non è
attaccata.**

## E `find_duplicate_skills` funziona — dopo che ho corretto la mia lettura

Il mio primo controllo la dava sbagliata: contavo `len(gruppi)` e ottenevo **2**,
attendendomene 1. Ma la funzione **non restituisce un dizionario di gruppi**:
restituisce `{"duplicate_groups": [...], "n_skills_scanned": 3}` — e il 2 erano
le sue **chiavi**. Letto l'output vero:

```
{'duplicate_groups': [{'signature': '74b628f5c506', 'skill_ids': ['', ''],
                       'n_dupes': 2}], 'n_skills_scanned': 3}
```

**Un gruppo, due duplicati, tre skill esaminate** — esattamente ciò che deve
fare: A e B (stesse parole, spazi e maiuscole diverse) insieme, C fuori.
⇒ **FUNZIONA COME PROMESSO.**

🔑 È la seconda volta stasera che assumo la forma di una struttura dati invece di
leggerla (la prima fu `.get("operable")` su una chiave inesistente). **Un
`len()` su un valore di ritorno che non hai stampato non è una misura.**
