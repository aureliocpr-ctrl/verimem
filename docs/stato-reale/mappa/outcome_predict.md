# Mappa di `verimem/outcome_predict.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/outcome_predict.py:19` `_tokens` | funzione: (nessun docstring) | `verimem/analogy.py:66`; `verimem/bm25_rank.py:124`; `verimem/bm25_rank.py:135` (+51) | `tests/test_due_domande_diverse_stessa_risposta.py`; `tests/test_l_oracolo_non_risponde_su_due_preposizioni.py`; `tests/test_le_interrogative_di_quantita_non_sono_contenuto.py` (+2) | - | NON MISURATO | - |
| 2 | `verimem/outcome_predict.py:23` `_jaccard` | funzione: (nessun docstring) | `verimem/coherence_check.py:115`; `verimem/cross_agent_consensus.py:51`; `verimem/episode_clusters.py:65` (+20) | `tests/test_il_flip_giapponese_passa_per_quindici_millesimi.py`; `tests/test_l_oracolo_non_risponde_su_due_preposizioni.py` | - | NON MISURATO | - |
| 3 | `verimem/outcome_predict.py:30` `predict_outcome` | funzione: Estimate p(success) for `task` from similar past episodes. | `verimem/mcp_server.py:11320`; `verimem/mcp_server.py:11328`; `verimem/outcome_predict.py:95` (+4) | `tests/test_outcome_predict.py`; `tests/test_risk_guard.py` | - | NON MISURATO | - |
