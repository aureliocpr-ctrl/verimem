# Mappa di `verimem/prompt_skeleton.py` — 3 righe, 121 righe di codice (lead, 09/09 00:44)

Letto per intero. Prove: le stesse due di `oracle.md` (pytest del lotto `61 passed in 82.08s`, EXIT=0, sul tip `20257636`; prova alla porta MCP con store isolato). `hippo_prompt_skeleton` con `task` «quale versione di Kubernetes usa il cluster OnlyPaws» → `quarantenato SERVITO=True · vivo servito=True · 585 char`: **il prompt pronto per l'LLM contiene il fatto quarantenato sotto «What we remember»**. Chiamante letto: `verimem/mcp_server.py:10082-10096` (`hippo_prompt_skeleton`), pesca fatti con `list_facts(limit=10000)` senza `hide_low_trust`, episodi con `a.memory.all(limit=5000)` e tutte le skill. Claim README: nessuna riga (grep su skeleton → nessuna).

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/prompt_skeleton.py:21` `_tokens` | token `[A-Za-z0-9_-]+` in minuscolo, senza filtro delle parole vuote | `build_prompt_skeleton` (41, 46, 55, 66) | `tests/test_prompt_skeleton.py` | - | FUNZIONA COME PROMESSO | pytest 61 passed |
| 2 | `verimem/prompt_skeleton.py:25` `_jaccard` | Jaccard, 0 se vuoto (copia n. 13 di 18) | `build_prompt_skeleton` | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 61 passed |
| 3 | `verimem/prompt_skeleton.py:31` `build_prompt_skeleton` | il prompt markdown (Task · What we remember · Past episodes · Skills to consider · Plan) con i top-3 per tier a Jaccard ≥ 0,15, skill ritirate escluse | `verimem/mcp_server.py:10090` (`hippo_prompt_skeleton`) | `tests/test_prompt_skeleton.py` | - | NON COME PROMESSO alla porta: mette nel prompt fatti QUARANTENATI, senza marcarli (T49) | porta MCP 08/09 22:33 + pytest 61 passed |

Reperti: (a) T49, e qui è la forma peggiore: il fatto rifiutato dal gate entra nel prompt di un modello come «what we remember», senza lo status accanto; (b) «Skills to consider» promette «promoted only» nel commento (riga 61) ma esclude solo le `retired`: le skill `draft`/`candidate` passano (letto, non misurato).
