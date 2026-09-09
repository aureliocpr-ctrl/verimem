# Mappa — `verimem/holographic_memory.py`

*ws3 Galileo. 21 fra funzioni, classi e metodi: memoria **senza database** in
stile Plate 1995 (HRR) — un vettore aggregato, un filtro di Bloom, un file
binario. Banco: `ws3-mappa-prova-vettoriali.py` (09/09 13:38).*

🔵 **Il fatto che riguarda tutto il file, e va detto prima delle righe**: il
codice **funziona** — l'ho misurato — ma **nessuna porta del prodotto lo
chiama**. `grep -rn "holographic" verimem/ -i` fuori dal suo modulo (CLI e
server MCP inclusi) → **zero righe**. Ha due file di test
(`test_holographic_memory.py`, `test_holographic_forget_scan68.py`), quindi è
esercitato; ma dall'SDK, dalla CLI, dalla porta HTTP e da quella MCP non ci si
arriva. Verdetto di raggiungibilità per l'intera classe: **MAI CHIAMATA**
(dal prodotto), e le righe qui sotto dicono cosa fa *quando* la si chiama.

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/holographic_memory.py:64` `_seed_from_text` | «seme intero deterministico dal testo via prefisso SHA-256» | **FUNZIONA COME PROMESSO** | stesso testo → stesso seme (**True**); testi diversi → semi diversi (**True**) |
| 2 | `verimem/holographic_memory.py:70` `_filler` | «vettore casuale a norma unitaria, deterministico per `text`… ortogonali in attesa, in alta dimensione» | **FUNZIONA COME PROMESSO** | stesso testo → stesso vettore (`np.allclose` **True**) · norma **1.0** esatta · prodotto scalare con un altro testo **0,0229**, cioè quasi ortogonale come promette la teoria citata |
| 3 | `verimem/holographic_memory.py:82` `_circular_conv` · `verimem/holographic_memory.py:93` `_circular_corr` | legare e slegare (Plate 1995); «`corr(a, conv(a, b)) ≈ b` (rumoroso). Serve la pulizia via Hopfield» | **FUNZIONA COME PROMESSO, col rumore che il docstring dichiara** | coseno fra `corr(a, conv(a,b))` e `b` = **0,72**: somiglia, non coincide — ed è esattamente ciò che il commento annuncia |
| 4 | `verimem/holographic_memory.py:104` `_circular_shift` | «sposta il filler di k posizioni (codifica della profondità nella catena)» | **FUNZIONA COME PROMESSO** | con `k=1` il vettore **cambia** (`allclose` False) e la **norma resta 1.0**: uno spostamento, non una deformazione |
| 5 | `verimem/holographic_memory.py:113` `_BloomFilter` · `verimem/holographic_memory.py:116` `_BloomFilter.__init__` · `verimem/holographic_memory.py:122` `_BloomFilter._idx` · `verimem/holographic_memory.py:130` `_BloomFilter.add` · `verimem/holographic_memory.py:134` `_BloomFilter.__contains__` | «filtro di Bloom minimo: k hash da fette del prefisso SHA-256» | **FUNZIONA COME PROMESSO** | dopo `add('uno')` e `add('due')`: `'uno' in bf` → **True**, `'tre' in bf` → **False**. Il lato che conta di un Bloom è il **False**, ed è quello provato |
| 6 | `verimem/holographic_memory.py:137` `_BloomFilter.to_bytes` · `verimem/holographic_memory.py:141` `_BloomFilter.from_bytes` | serializzazione del filtro | **FUNZIONA COME PROMESSO** | `to_bytes()` → **1024 byte**; ricostruito con `from_bytes`, `'uno'` è ancora dentro (**True**) |
| 7 | `verimem/holographic_memory.py:149` `HolographicMemory` · `verimem/holographic_memory.py:166` `HolographicMemory.__post_init__` | «memoria per agenti **senza database**: 1 vettore aggregato + 1 Bloom, persistiti in un solo file binario» | **FUNZIONA COME PROMESSO** · raggiungibilità: **MAI CHIAMATA** dal prodotto | `stats()` → `{'d': 1024, 'n_facts': 3, 'aggregate_size_bytes': 4096, 'bloom_size_bytes': 80000, 'cleanup_pool_size': 3, 'cleanup_pool_cap': 2048, 'aggregate_norm': 1.76}`. La struttura c'è tutta; ciò che non c'è è un chiamante |
| 8 | `verimem/holographic_memory.py:173` `HolographicMemory.remember` | lega `(topic, proposition)` e somma all'aggregato, aggiornando Bloom e pool di pulizia | **FUNZIONA COME PROMESSO** | tre coppie scritte → `n_facts: 3`, `cleanup_pool_size: 3`, norma dell'aggregato cresciuta a 1,76 |
| 9 | `verimem/holographic_memory.py:204` `HolographicMemory.recall` | «decodifica l'aggregato per trovare la proposizione di un topic» | **FUNZIONA COME PROMESSO — tre su tre** | `recall('canone')` → `[{'topic': 'canone', 'proposition': '5900 euro', 'lineage_depth': 0, …}]`; idem `'consegna'` → `'3 marzo'` e `'indirizzo'` → `'via Roma'`. ⚠️ Restituisce **dizionari**, non stringhe: il mio primo confronto (`r[0] == p`) diceva «0 su 3» ed era il confronto a essere sbagliato, non il richiamo. Letto il campo `proposition`: **3 su 3** |
| 10 | `verimem/holographic_memory.py:252` `HolographicMemory.contains` | «controllo di esistenza sul Bloom. **False = certamente assente. True = probabilmente presente**» | **FUNZIONA COME PROMESSO** | coppia scritta → **True**; coppia mai scritta → **False**. Il verso forte (il False) è quello misurato |
| 11 | `verimem/holographic_memory.py:257` `HolographicMemory.forget` | «oblio morbido: sottrae il vettore legato e toglie la voce dal pool. **L'oblio HRR è approssimato. Il Bloom non si può azzerare senza ricostruirlo (lo lasciamo; falsi positivi)**» | **FUNZIONA COME PROMESSO, col limite dichiarato** | dopo `forget('canone', '5900 euro')` il richiamo su quel topic **non** restituisce più quella coppia (torna la successiva del pool). Il limite del Bloom è scritto nel docstring e resta vero: `contains` continuerebbe a dire True |
| 12 | `verimem/holographic_memory.py:283` `HolographicMemory.stats` | introspezione | **FUNZIONA COME PROMESSO** | vedi riga 7 — dichiara anche il tetto del pool di pulizia (`cleanup_pool_cap: 2048`) |
| 13 | `verimem/holographic_memory.py:296` `HolographicMemory.save` · `verimem/holographic_memory.py:323` `HolographicMemory.load` | «persiste in un solo file binario: header(20B) + aggregato(D*4B) + bloom + cleanup» | **FUNZIONA COME PROMESSO** | `save` → `{'ok': True, 'bytes_written': 84172, 'path': '…/olo.bin'}`; dopo `load` le statistiche coincidono (`n_cleanup` uguale): il giro su disco conserva lo stato |
