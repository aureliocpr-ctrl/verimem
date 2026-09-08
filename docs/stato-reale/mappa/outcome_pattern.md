# Mappa di `verimem/outcome_pattern.py` — 2 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/outcome_pattern.py:47` `_tokens` | funzione: (nessun docstring) | `verimem/analogy.py:66`; `verimem/bm25_rank.py:124`; `verimem/bm25_rank.py:135` (+51) | `tests/test_due_domande_diverse_stessa_risposta.py`; `tests/test_l_oracolo_non_risponde_su_due_preposizioni.py`; `tests/test_le_interrogative_di_quantita_non_sono_contenuto.py` (+2) | - | NON MISURATO | - |
| 2 | `verimem/outcome_pattern.py:54` `find_outcome_patterns` | funzione: Find tokens correlated with success/failure. | `verimem/mcp_server.py:9966`; `verimem/mcp_server.py:9972`; `verimem/outcome_pattern.py:114` | `tests/test_i_segnali_di_outcome_dicono_contro_cosa_sono_misurati.py`; `tests/test_outcome_pattern.py` | - | NON MISURATO | - |
