# Mappa di `verimem/trajectory_render.py` — 3 righe, 96 righe di codice (lead, 09/09 03:26)

Letto per intero. Prova: pytest del lotto F sul tip `20257636` (`105 passed in 31.36s`, EXIT=0, con `tests/test_trajectory_render.py`). Chiamanti letti: `trajectory_to_markdown` ← `verimem/mcp_server.py:9794,9802` (`hippo_trajectory_render`); `trajectory_summary_line` ← `verimem/mcp_server.py:9861,9868` (`hippo_trajectory_summary`, nome dall'elenco dei tool); `scripts/trajectory_demo.py:26`. La bozza attribuiva a `_truncate` chiamanti in `self_model_refresh.py` e `skill_drafter.py`: **falsi positivi del nome**. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/trajectory_render.py:25` `_truncate` | taglia a `n` con la coda «[truncated K chars]» | `trajectory_to_markdown` (62) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 105 passed |
| 2 | `verimem/trajectory_render.py:33` `trajectory_to_markdown` | un `### Step` per passo con il marcatore del tipo, il ramo, il tool con args (300 caratteri) e il risultato troncato (1000) | `verimem/mcp_server.py:9802` | `tests/test_trajectory_render.py` | - | FUNZIONA COME PROMESSO | pytest 105 passed |
| 3 | `verimem/trajectory_render.py:71` `trajectory_summary_line` | «N steps (aT/bA/cO/dD) branches=[…]» | `verimem/mcp_server.py:9868` | nessun test la nomina | - | FUNZIONA COME PROMESSO (per lettura: nessun test diretto) | pytest 105 passed |

Reperti: (a) `trajectory_summary_line` non ordina i passi (`trajectory_to_markdown` sì): conta soltanto, quindi va bene; (b) `_truncate` è una copia locale di un'idea che vive in tre moduli con lo stesso nome (classe ①). Nessun P0.
