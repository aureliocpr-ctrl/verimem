# `verimem/skill_diff_render.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

```
tool MCP        hippo_skill_diff_render
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
| 1 | `verimem/skill_diff_render.py:11` `_list_diff` | funzione: Compact representation of two list values. | nessuno trovato | nessuno | - | MAI CHIAMATA (candidata: nessun chiamante ne' test trovato) | - |
| 2 | `verimem/skill_diff_render.py:16` `_fmt` | funzione: (nessun docstring) | `verimem/skill_diff_render.py:38`; `verimem/skill_diff_render.py:39` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/skill_diff_render.py:22` `render_skill_diff` | funzione: Render a markdown side-by-side of two skills. | `verimem/mcp_server.py:11717`; `verimem/mcp_server.py:11733`; `verimem/skill_diff_render.py:79` | `tests/test_skill_diff_render.py` | - | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».

---

## Confermato eseguendo: `_list_diff` (:11) è codice morto

La bozza la segnalava come «MAI CHIAMATA (candidato)». **Confermata**, ed è il
caso più netto della famiglia — non è chiamata **nemmeno dal proprio modulo**:

```
grep -n "_list_diff" verimem/skill_diff_render.py
   11:def _list_diff(a: list[str], b: list[str]) -> str:      ← solo la def

grep -rn "_list_diff" verimem/ tests/  (escluso il file stesso)
   (nessun risultato)
```

⇒ **MAI CHIAMATA**: propongo la rimozione. Non la tocco (regola 2).

📌 Il modulo nel suo insieme è vivo e presidiato — la catena sopra lo mostra
esposto come tool con il suo test. **Le due cose convivono**: un file
raggiungibile può contenere una funzione che nessuno raggiunge, e il verdetto
per FUNZIONE è la ragione per cui la mappa si fa riga per riga e non per file.
