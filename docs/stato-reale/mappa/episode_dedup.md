# Mappa di `verimem/episode_dedup.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/episode_dedup.py:33` `_key` | funzione: Strict dedup key. None / NULL normalised to empty string. | `verimem/conversation_ingest.py:451`; `verimem/conversation_ingest.py:465`; `verimem/episode_dedup.py:69` (+3) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/episode_dedup.py:42` `find_duplicate_groups` | funzione: Ritorna i gruppi di episodi con chiave dedup duplicata. | `verimem/episode_dedup.py:20`; `verimem/episode_dedup.py:116`; `verimem/episode_dedup.py:160` (+2) | `tests/test_episode_dedup.py` | - | NON MISURATO | - |
| 3 | `verimem/episode_dedup.py:92` `dedup_episodes` | funzione: Esegue (o simula) il dedup degli episodi. | `verimem/episode_dedup.py:21`; `verimem/episode_dedup.py:160`; `verimem/mcp_server.py:11381` (+1) | `tests/test_episode_dedup.py` | - | NON MISURATO | - |
