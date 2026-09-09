# Mappa — `verimem/skill_emergence_detector.py`

*ws3 Galileo. 5 funzioni: cerca **skill che stanno emergendo da sole** nel grafo
dei fatti (comunità di Louvain + purezza del topic + coesione). Banco:
`ws3-mappa-prova-skill-moduli.py` (09/09 13:47), su uno store costruito apposta
con 8 fatti in 4 topic.*

🟢 **Un sospetto mio, misurato e SMENTITO — e lo scrivo perché la lezione vale
più del sospetto.** Il docstring di `_embeddings_for_ids` dice «(k, **384**)
float32», la stessa dimensione legacy che in `mesh_memory` fa restituire zero
righe su ogni store attuale (T-MAP-9). Sembrava la stessa forma su un secondo
modulo. **Misurato**: `_embeddings_for_ids` su tre id veri torna
`array (3, 768) float32` — il codice **legge la dimensione dai dati**, è solo la
riga di documentazione a essere rimasta indietro. Nessun secondo T-MAP-9: se
avessi contato le occorrenze di «384» nel sorgente invece di eseguire, avrei
firmato un allarme falso.

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/skill_emergence_detector.py:58` `_embeddings_for_ids` | «prende gli embedding come array (k, 384) float32. **`None`** in caso di errore o di una riga mancante» | **FUNZIONA COME PROMESSO nel comportamento; il docstring è superato nel numero** | tre id veri → `array (3, 768) float32` (la dimensione **vera** dello store, non quella scritta); un id inesistente → **`None`**, cioè il caso di errore è distinto da un array vuoto |
| 2 | `verimem/skill_emergence_detector.py:95` `_topic_for_ids` | il topic di ciascun id | **FUNZIONA COME PROMESSO** | `{'70f24d73ce4b': 'affitti/canoni', '95592b29f9d6': 'affitti/canoni', '9eb6125d3b8e': 'affitti/canoni'}` — un dizionario id→topic, che è ciò che serve per misurare la purezza |
| 3 | `verimem/skill_emergence_detector.py:116` `_cohesion_score` | «coseno medio di ogni riga rispetto al centroide. **Più alto = più coeso**» | **FUNZIONA COME PROMESSO, e distingue** | tre fatti dello **stesso** tema → **0,9878**; tre fatti di temi **diversi** → **0,9485**; il confronto `>` è `True`. ⚠️ La distanza fra i due è **0,039**: il punteggio separa, ma di poco — con soglie tarate male i due casi si confondono, e questo è il numero da tenere davanti quando si sceglie `min_cohesion` |
| 4 | `verimem/skill_emergence_detector.py:130` `_suggest_skill_name` | propone il nome della skill dai topic della comunità | **FUNZIONA COME PROMESSO** | `{'affitti/canoni': 3, 'servizi/manutenzione': 1}` → **`'emerging_skill_canoni'`** (prende il topic dominante e ne usa l'ultimo segmento); con un dizionario **vuoto** → `''`, non un nome inventato |
| 5 | `verimem/skill_emergence_detector.py:142` `detect_emerging_skills` | «rileva le skill candidate emergenti nel grafo dei fatti» (comunità di Louvain, purezza del topic, coesione, seconda passata, partizione stabile, ibrido) | **NON MISURATO nel ramo che produce candidati** | con soglie permissive (`min_community_size=2, min_topic_purity=0.5, min_cohesion=0.1, max_n=5`) su 8 fatti in 4 topic → **`[]`**. Il risultato è **onesto** (nessuna comunità abbastanza grande in un grafo così piccolo) ma **non prova la funzione**: per esercitarla serve un corpus con comunità vere. Lo scrivo come limite della mia misura, non come verdetto sul codice — e i quattro interruttori (`enable_second_pass`, `enable_stable_partition`, `enable_hybrid`, `prior_partition`) restano tutti **non misurati** |
