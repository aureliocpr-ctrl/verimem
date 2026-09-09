# Mappa — `verimem/resonator_memory.py`

*ws3 Galileo. 16 fra funzioni e metodi: memoria **senza database** via Resonator
Networks (Frady et al. 2020) — un vettore aggregato e un codice, e i fatti si
recuperano **fattorizzando**. Banchi: `ws3-mappa-prova-vettoriali.py` e
`ws3-mappa-prova-risonatore-semi.py` (09/09 13:38-13:40).*

🔴 **Il reperto del file (T-MAP-10, in fondo)**: `recall_tuple` ha reso la tupla
**sbagliata 10 volte su 10** su una memoria che ne conteneva **una sola**, ogni
volta con `ok: True` e `converged: True` — e la sua ricevuta **non porta il
campo `residual`**, che è l'unico modo per accorgersene. La funzione gemella
`recall_tuple_multi_restart` trova quella giusta *e* il residuo.

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/resonator_memory.py:69` `_circular_conv` · `verimem/resonator_memory.py:74` `_circular_corr` | legare e slegare due vettori (FFT) | **FUNZIONA COME PROMESSO** | `corr(a, conv(a, b))` somiglia a `b` con coseno **0,72** — «approssimativamente l'inverso», come dice il docstring: rumoroso, e infatti serve la pulizia |
| 2 | `verimem/resonator_memory.py:81` `_build_alphabet` | «K matrici di codice quasi ortonormali… ogni riga = vettore gaussiano a norma unitaria» | **FUNZIONA COME PROMESSO** | `_build_alphabet(3, 8, 256, 42)` → **3** matrici di forma **(8, 256)**, righe con norma **1.0** |
| 3 | `verimem/resonator_memory.py:101` `_project_to_codebook` | proiezione **argmax duro** sul codice | **FUNZIONA COME PROMESSO** | dato l'atomo numero 3, restituisce **indice 3** con punteggio **1.0**: il caso facile è esatto |
| 4 | `verimem/resonator_memory.py:110` `_soft_project_to_codebook` | «pulizia SOFT: combinazione pesata via softmax… per permettere una discesa graduale» | **FUNZIONA COME PROMESSO** | stesso atomo → **indice 3**, punteggio **1.0**; con `beta=10` la combinazione morbida non sposta l'argmax nel caso pulito |
| 5 | `verimem/resonator_memory.py:132` `_residual_norm` | «‖aggregato − bind(atomi)‖₂. **Più basso = corrispondenza migliore**» | **FUNZIONA COME PROMESSO — ed è il righello del reperto** | tupla giusta `(1,2,3)` → **0.0** · tupla sbagliata `(7,7,7)` → **1.4066**. Separa perfettamente, ed è già dentro il modulo |
| 6 | `verimem/resonator_memory.py:146` `ResonatorMemory` · `verimem/resonator_memory.py:159` `ResonatorMemory.__post_init__` | «memoria senza database… un solo vettore aggregato e un codice fisso. **Nessun byte per fatto**» | **FUNZIONA COME PROMESSO** | `stats()` → `{'n_roles': 3, 'atoms_per_role': 8, 'd': 1024, 'n_facts': 1, 'aggregate_size_bytes': 4096, 'codebook_size_bytes': 98304, 'total_storage_bytes': 102400, 'theoretical_capacity_compositions': 512}`: la dimensione **non** dipende dal numero di fatti |
| 7 | `verimem/resonator_memory.py:168` `ResonatorMemory.remember_tuple` | lega la tupla e la somma all'aggregato | **FUNZIONA COME PROMESSO** | dopo una `remember_tuple((1,2,3))` il residuo di quella tupla è **0.0**: il legame è entrato nell'aggregato |
| 8 | `verimem/resonator_memory.py:311` `ResonatorMemory.recall_tuple` | «fattorizza l'aggregato con la dinamica del Resonator» | 🔴 **NON COME PROMESSO nella RICEVUTA** → **T-MAP-10** | memoria con **una sola** tupla `(1,2,3)`; dieci semi diversi → `(5,5,4)`, `(5,2,7)`, `(4,4,7)`, `(1,5,6)`, `(5,4,3)`, `(3,0,6)`, `(4,2,0)`, `(4,2,0)`, `(5,5,4)`, `(5,1,1)`: **0 giuste su 10**, e tutte con `ok=True` **e** `converged=True`. Campi della ricevuta: `['converged', 'indices', 'iters', 'ok']` — **`residual` non c'è**. Il residuo vero della risposta del seme 1 è **1.4094** contro **0.0** della tupla vera: il dato che smaschera l'errore esiste (riga 5) e non viene servito |
| 9 | `verimem/resonator_memory.py:198` `ResonatorMemory.recall_tuple_multi_restart` | «`n_restarts` fattorizzazioni indipendenti con pulizia SOFT, **restituisce la migliore**» | **FUNZIONA COME PROMESSO — ed è la cura già scritta** | con 5 ripartenze → `{'ok': True, 'indices': (1, 2, 3), 'converged': True, 'residual': 0.0, 'restart': 0, 'n_restarts': 5}`: **la tupla giusta** e il **residuo** nella stessa ricevuta. Con `target_indices=(1,2,3)` compare anche `found_match: True` |
| 10 | `verimem/resonator_memory.py:234` `ResonatorMemory.recall_all_via_matching_pursuit` | «Matching Pursuit (Mallat 1993) + Resonator: fattorizza iterativamente…» | **FUNZIONA COME PROMESSO** | memoria con **due** tuple → `{'ok': True, 'found_facts': [(4, 5, 6), (1, 2, 3)], 'residuals_trail': [0.98, 3.9e-08], 'n_passes': 2, 'final_residual_norm': 3.9e-08}`: **entrambe** ritrovate, e la traccia dei residui mostra il residuo che crolla a ogni passata |
| 11 | `verimem/resonator_memory.py:404` `ResonatorMemory.stats` | introspezione dello stato | **FUNZIONA COME PROMESSO** | vedi riga 6: porta anche `theoretical_capacity_compositions` (512), cioè **dichiara il proprio limite** |
| 12 | `verimem/resonator_memory.py:423` `ResonatorMemory.save` · `verimem/resonator_memory.py:450` `ResonatorMemory.load` | «salva l'aggregato in `.npz` (il codice si ri-deriva dal seme). **Cycle 400 fix: evitare il doppio suffisso `.npz.npz` su Windows**» | **FUNZIONA COME PROMESSO** | `save(tmp/'res.npz')` → il file esiste **con quel nome esatto** (nessun `.npz.npz`), e dopo `load` l'aggregato è **identico** (`np.allclose` → True) |
| 13 | `verimem/resonator_memory.py:475` `text_to_indices` | «mappatura deterministica testo → tupla di indici, via SHA-256 a fette» | **FUNZIONA COME PROMESSO** | `'il canone e 5900 euro'` → `(3, 7, 5)`, e due chiamate danno lo stesso risultato (**True**) |

## T-MAP-10 — la fattorizzazione singola dice «convergiuto» su una risposta sbagliata, e non dà il modo di saperlo

Su una memoria che conteneva **una sola** tupla, `recall_tuple` ha restituito
**dieci risposte sbagliate su dieci semi**, tutte con `ok=True` e
`converged=True`. Che un resonator network cada su punti fissi spuri è atteso —
il modulo cita Frady 2020, e la funzione gemella esiste **proprio** per questo.
Il difetto non è che sbagli: è che **la ricevuta non porta `residual`**, cioè il
solo campo che distingue una fattorizzazione buona da una spuria. Il calcolo è
già nel modulo (`_residual_norm`, riga 132: 0.0 contro 1.4094 sui due casi) e
`recall_tuple_multi_restart` lo restituisce.

⇒ Chi chiama `recall_tuple` e legge `converged: True` non ha **nessun modo**, con
i campi che riceve, di sapere che la risposta è sbagliata. Cura possibile in una
riga (aggiungere `residual` alla ricevuta), **non scritta**: siamo in mappa.

🟢 **E il ridimensionamento, che faccio io prima che lo faccia un altro**: ho
cercato i chiamanti, e **nel prodotto nessuno usa `recall_tuple`**. L'unica
porta è `resonator_cli.py:104`, che chiama
`recall_all_via_matching_pursuit` — la variante che porta i residui e che nel
banco ha ritrovato **entrambe** le tuple. Quindi il difetto **non colpisce
nessun percorso vivo oggi**: colpisce chi userebbe l'API direttamente, e resta
una trappola aperta per il prossimo che la chiama. Priorità bassa, reperto vero.
⚠️ **NON MISURATO**: quanti fatti servono perché la singola cominci a fallire —
qui ne bastava **uno**, quindi il problema non è la saturazione.
