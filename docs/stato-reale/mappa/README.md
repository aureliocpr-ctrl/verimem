# Mappa della superficie — parte ws5 · 15 file · 11.115 righe · 309 funzioni

Mappata su `7b9e8ca1` (l'08/09 sera). Il conteggio è con `ast`, non con grep, e combacia
esatto con l'indice del mandato.

**Il taglio**: non «quali funzioni ci sono» (lo genera uno script) ma **chi fa cosa, e dove
la promessa scritta non combacia col codice**. Ogni file chiude con una sezione *«quello che
questa mappa NON dice»*: i limiti sono parte della mappa, non una nota in fondo.

---

## I quindici file

| file | righe | fn | il pezzo che conta |
|---|---|---|---|
| [anti_confab_gate](anti_confab_gate.md) | 3380 | 42 | tre famiglie di layer; **solo L4 legge la fonte** |
| [wake](wake.md) | 1725 | 58 | l'esecutore; si apre con **otto difese anti-injection** |
| [encode_service](encode_service.md) | 974 | 37 | il daemon serve **tre** modelli e il nome ne dice uno |
| [local_grounding](local_grounding.md) | 970 | 33 | le quattro vie al giudizio e i **35,4 s** che nessuna prevede |
| [grounding_gate](grounding_gate.md) | 671 | 22 | lo span troncato **due volte**: solo il secondo costa |
| [config](config_e_resonator.md) | 561 | 5 | 112 righe per funzione: sono **scelte**, non logica |
| [embedding](embedding.md) | 529 | 29 | il degrado dichiarato con un **tipo**, non un `None` |
| [wake_strategy](wake_strategy.md) | 439 | 22 | il pattern strategy vero: **due encoding, un algoritmo** |
| [preload](preload.md) | 387 | 11 | una funzione pubblica su 11, **fino a quattro thread** |
| [flow_events](flow_events.md) | 362 | 11 | ogni evento porta **impronta, non percorso** |
| [admission_gate](admission_gate.md) | 339 | 6 | **«scritto» non vuol dire «servibile»** |
| [observability](observability.md) | 310 | 22 | log su **stderr**, perché stdout è il protocollo |
| [_hang_watchdog](_hang_watchdog.md) | 232 | 4 | non previene gli hang: li rende **diagnosticabili** |
| [resonator_text_bridge](config_e_resonator.md) | 150 | 5 | un fallback **deterministico e senza modello** |
| [_import_lock](_import_lock.md) | 86 | 2 | **la regola più facile da violare**, e l'ho violata io |

---

## I reperti TRASVERSALI — quello che un file solo non può dire

### ① La cura che arriva a una copia e non all'altra
`make_finetuned_scorer` era sotto lock e la sua gemella `make_nli_classifier` no ·
`_tokenizzatore` scoperto · `embedding._load_model` sotto **un altro** lock. Tre volte lo
stesso difetto, e la terza era **la causa radice di T26a**.
⚠️ **E una quarta volta ho creduto di trovarla e mi sbagliavo** (i due pruner di `wake`):
vedi ⑥.

### ② Il nome che non dice cosa fa
`encode_service` serve **encoder + reranker + giudice del moat** · `anti_confab_gate` e
`anti_confabulation` sono due file diversi · **`L2` in una ricevuta non esiste**: quel nome
è un «reconciler» nell'altro file. ⇒ Chi cerca il moat, o il gradino 2 di una scala, cerca
nel posto sbagliato.

### ③ La difesa con una scorciatoia intorno
**CVE-008**: la guardia anti-injection stava sul percorso lento (il loop dell'LLM) e **non**
sul macro compilato. Nessuno dei due percorsi era sbagliato: mancava il controllo **dove si
incontravano**. ⇒ **Ogni fast-path del prodotto è un candidato per la stessa domanda.**

### ④ Un valore parziale deve DICHIARARE di esserlo
Il prodotto lo fa bene in tre punti — `confidence_tier` (*«NOT a truth claim»*), `_estratto`
(taglia senza mutilare il grafema, e il nome dice che è un estratto), `judged` nella ricevuta
MCP (aggiunto oggi) — e la stessa disciplina manca dove un `None` deve essere interpretato.
**Il modello da copiare è `EncodeDelegateUnavailable`**: l'indisponibilità ha un *tipo*.

### ⑤ Due strategie per lo stesso rischio, in posti che non si parlano
Il blocco da import/carico è evitato **per struttura** in `_import_lock` (solo `import` sotto
il lock) e **tollerato con un timeout** in `embedding._MODEL_LOCK` (90 s, dopo un hang di
quattro ore). Nessuna è sbagliata; **la divergenza è costata T26a**.
📌 Nel prodotto convivono **tre** lock sugli import: l'ordine li rende non-deadlockabili, e
quella proprietà è tenuta in piedi da **una cella sola**.

### ⑥ Il metodo: contare le righe NON dice se una logica è duplicata
`_prune_working_memory` (22 righe) e `_prune_working_memory_react` (21), col docstring *«same
algorithm, different encoding»*, sembravano la quarta copia di ①. **Misurati**: tre
istruzioni ciascuno, algoritmo unico in `working_memory.prune_messages`, differenze quasi
tutte nei docstring. **Il sospetto è caduto prima di diventare un ticket.**
⇒ In questa mappa, ogni limite che si chiudeva con un comando è stato **eseguito** invece
che scritto: tre volte, e due hanno cambiato la conclusione.

---

## I limiti aperti di TUTTA la mappa

Raccolti dalle sezioni finali dei quindici file. **Nessuno è stato misurato.**

- `L1.21`, `L1.5`, `L1.7`: sigle trovate, **contenuto non letto**.
- **Nessuna precisione per singolo detector L1** (esiste un dato complessivo, ~40%).
- **Nessuna prova che i 28 layer siano raggiungibili** su un input reale.
- **Nessuna difesa di `encode_service` è stata esercitata** — la prima da provare è
  `_owner_is_zombie`, perché la sua assenza è già costata (25/07).
- ~~`_safe_tar_extract`: ha un test?~~ → **SÌ**, `tests/test_gate_model_tarslip.py`. Il
  presidio porta il nome dell'attacco. **Chiuso in positivo.**
- `_default_gate_fn` (il percorso per cui il daemon giudica): **ha un test?**
- ~~**I prefissi e5**: applicati da tutti i chiamanti?~~ → **La domanda era posta male.** Non
  è una dimenticanza: `semantic.py` li applica, `memory.py:76` dichiara di **non** applicarli
  ed è *«internally consistent»*, con l'avvertenza esplicita di **non allinearlo**. ⇒ **Due
  convenzioni volute.** Il rischio vero è la **giuntura** — un vettore senza prefisso
  confrontato con uno con prefisso — e **quello resta da verificare**. Stessa forma di ③.
- La **cache LRU** di `embedding`: può servire un vettore del modello precedente?
- **Quanti fast-path saltano il loop dell'LLM** (la domanda di ③).
- `_dispatch_native` (5 righe) contro `_dispatch` (18): asimmetria **plausibile ma non
  misurata**.
- `observability.history`: lo storico ha un limite?
- `config._load_env`: **quali** file `.env`, e **in che ordine**?
- `admission_gate`: quanti fatti del corpus reale sono stati instradati a telemetria.

---

## Ticket che nascono da questa mappa

- **T40** (mio): il tokenizer da 35,4 s sul thread della richiesta — la cura è **non fare il
  secondo troncamento** in delegate-only, ma serve **un A/B che provi che i due span sono
  equivalenti**, prima.
- **Debito mio**: il commento di `preload` ~374 dichiara come *virtù* i «lock diversi»
  dall'embedder — era la causa di T26a.
- **Debito mio**: `time.sleep(0)` morto in
  `tests/test_l_import_del_giudice_non_tiene_il_lock.py:119`.

---

*ws5 (Tara), 08/09. I numeri con un comando accanto sono miei; gli altri sono attribuiti a
chi li ha misurati.*
