# Mappa di `verimem/stable_partition.py` — 8 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/stable_partition.py:42` `Partition` | classe: A community partition: node-id → community-id mapping. | `verimem/anti_confab_gate.py:708`; `verimem/skill_emergence_detector.py:55`; `verimem/skill_emergence_detector.py:153` (+23) | nessuno | - | NON MISURATO | - |
| 2 | `verimem/stable_partition.py:50` `Partition.values_as_sets` | funzione: Group nodes by community → list of node-id sets. | `verimem/stable_partition.py:190` | `tests/test_stable_partition.py` | - | NON MISURATO | - |
| 3 | `verimem/stable_partition.py:57` `Partition.community_of` | funzione: (nessun docstring) | nessuno trovato | nessuno | - | MAI CHIAMATA (candidata: nessun chiamante ne' test trovato) | - |
| 4 | `verimem/stable_partition.py:61` `_louvain_fresh` | funzione: Run vanilla Louvain on graph, return Partition. | `verimem/stable_partition.py:150` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/stable_partition.py:79` `_extend_with_new_nodes` | funzione: For each new node, assign it to the community of its highest-weight | `verimem/stable_partition.py:167` | nessuno | - | NON MISURATO | - |
| 6 | `verimem/stable_partition.py:111` `stable_partition` | funzione: Compute a stable partition over the semantic graph. | `verimem/auto_dream_worker.py:260`; `verimem/auto_dream_worker.py:268`; `verimem/skill_emergence_detector.py:55` (+7) | `tests/test_auto_dream_stable_partition_envvar.py`; `tests/test_both_cures_interaction.py`; `tests/test_hybrid_mode.py` (+1) | - | NON MISURATO | - |
| 7 | `verimem/stable_partition.py:170` `partition_jaccard` | funzione: Jaccard distance between two partitions over node-pair | `verimem/stable_partition.py:209` | `tests/test_stable_partition.py` | - | NON MISURATO | - |
| 8 | `verimem/stable_partition.py:188` `partition_jaccard.co_pairs` | funzione: (nessun docstring) | `verimem/stable_partition.py:198`; `verimem/stable_partition.py:199` | nessuno | - | NON MISURATO | - |
