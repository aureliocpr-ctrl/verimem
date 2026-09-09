# Mappa di `verimem/narration_llm.py` — 2 righe, 91 righe di codice (lead, 09/09 03:50)

Letto per intero. Prova: pytest del lotto G sul tip `20257636` (`117 passed, 1 skipped in 94.44s`, EXIT=0, con `tests/test_narration_llm.py`). Chiamante letto: `verimem/narration.py:187-188` (quando `archive_and_extract_narration` riceve un `llm`). Estrazione LLM delle affermazioni atomiche verificabili da una narrazione, con la disciplina di `openie`: JSON-only, UN retry «fix the JSON», `[]` al secondo fallimento; il modello è `verimem.llm.get_llm()` (in HOSTED MODE via MCP sampling, senza chiave esterna). Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/narration_llm.py:35` `_parse_claims` | parse stretto di `{"claims": [str, …]}` → lista di stringhe non vuote, o `None` se malformato | `extract_atomic_facts` (66, 76) | via il test | - | FUNZIONA COME PROMESSO (plumbing) | pytest 117 passed |
| 2 | `verimem/narration_llm.py:49` `extract_atomic_facts` | una chiamata, un retry sul JSON rotto, `[]` altrimenti; dedup case-folded, tetto `max_claims` (12); vuoto o `llm=None` → `[]` | `verimem/narration.py:188` | `tests/test_narration_llm.py` | - | FUNZIONA COME PROMESSO | pytest 117 passed |

Reperti: (a) la regola 4 del prompt («Do NOT invent anything not present in the narrative») è un'istruzione al modello, non una verifica: le affermazioni estratte NON passano da un controllo lessicale contro la narrazione, quindi un'invenzione del modello esce come «atomic verifiable claim» — è la stessa forma di `document_promote` prima della cura `8d4d393d` (citata nel commento di `transcript_promote`): qui nessuno la misura; (b) a differenza di `llm_keywords_augment`, le recinzioni markdown NON vengono tolte prima del parse: un modello che le mette consuma il retry (letto). Nessun P0 misurato.
