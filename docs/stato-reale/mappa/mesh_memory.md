# Mappa — `verimem/mesh_memory.py`

*ws3 Ricerca. 8 funzioni: la **memoria condivisa fra istanze** — pubblicare una
domanda su un canale, ricevere i top-k degli altri **senza mai scambiare il
testo**, fondere i due campi. Banchi: `ws3-mappa-prova-quattro-moduli.py`,
`ws3-mappa-prova-mesh-e-briefing.py`, `ws3-mappa-prova-mesh-dimensione.py`
(09/09 12:21-12:28).*

🔴 **IL REPERTO DI QUESTO FILE, in una riga**: il modulo è tarato su embedding da
**384 dimensioni** (`EMBED_DIM = 384`, riga 70) e filtra le righe con
`length(embedding) = 1536`; lo store scrive embedding da **768** (3072 byte,
modello `intfloat/multilingual-e5-base`). Il modello a 384 è quello che
`config.py:66` chiama `_LEGACY_EMBEDDING_MODEL`. Risultato: la selezione non
trova **mai** una riga, e non lo dice a nessuno — restituisce una lista vuota,
che è indistinguibile da «non ho trovato niente di simile». Dettagli e ticket in
fondo (**T-MAP-9**).

| # | funzione (file:riga) | cosa promette | verdetto | prova (comando e esito) |
|---|---|---|---|---|
| 1 | `verimem/mesh_memory.py:82` `_cosine` | «coseno fra due blob float32 normalizzati **a 384 dimensioni**» | **FUNZIONA COME PROMESSO** (ed è coerente col proprio docstring) | uguali → `1.0` · ortogonali → `0.0` · a 45 gradi → `0.7071`. Con blob di dimensione diversa da 1536 byte torna 0.0 per costruzione (riga 84) |
| 2 | `verimem/mesh_memory.py:73` `_vec_bus` | «import pigro di `vec_bus` per non avere una dipendenza dura all'import» | **FUNZIONA COME PROMESSO** | `_vec_bus().__name__` → `clp.agentos.vec_bus`: il bus si risolve solo quando serve |
| 3 | `verimem/mesh_memory.py:91` `local_topk_embeddings` | «i top-k locali `(fact_id, embedding, coseno)`… **la primitiva che preserva la privacy**: il testo NON viene restituito» | 🔴 **NON COME PROMESSO sugli store reali** → **T-MAP-9** | store appena creato dal prodotto, 2 fatti, **entrambi con embedding non nullo** (misurato: `SELECT COUNT(*) … embedding IS NOT NULL` → 2, blob **3072 byte = 768 float32**, modello `intfloat/multilingual-e5-base`): `local_topk_embeddings(db, vettore, 3)` → **0 righe**. La causa è **letta**, non dedotta: la query filtra `length(embedding) = EMBED_DIM*4` = **1536** (righe 118-121), e nessuna riga la soddisfa |
| 4 | `verimem/mesh_memory.py:278` `mesh_resonant_merge` | «completamento di Hopfield sul campo locale+remoto» | 🔴 **NON COME PROMESSO, stessa radice** | con embedding a 384 costruiti a mano → `{'ok': False, 'error': 'no valid embeddings'}`; il filtro di riga 340 (`len(emb) != EMBED_DIM * 4`) scarta ogni embedding che non sia a 384. Su uno store vero scarterebbe **tutto** |
| 5 | `verimem/mesh_memory.py:192` `mesh_fuse_local_remote` | «recall di rete completo: pubblica la domanda, aspetta le risposte, fonde» | **NON MISURATO** (serve il bus dei vettori vivo) — **ma la sua metà locale è già decisa** | non l'ho eseguita: richiede `clp.agentos.vec_bus` con due istanze che si rispondono. ⚠️ **Letta, riga 227**: chiama `local_topk_embeddings(semantic_db, query_vec_bytes, k=k)` — cioè la funzione della riga 3, che su uno store reale rende sempre `[]`. Il contributo locale alla fusione sarebbe vuoto anche col bus perfettamente funzionante |
| 6 | `verimem/mesh_memory.py:132` `mesh_publish_query` | pubblica la domanda come vettore sul canale | **NON MISURATO** (serve il bus) | non eseguita: pubblicherebbe su un canale reale condiviso con le altre istanze, e non è un effetto che mi prendo durante una mappa |
| 7 | `verimem/mesh_memory.py:149` `mesh_fetch_recent` | legge i messaggi recenti del canale, «filtra i propri per non rispondersi da sola» | **NON MISURATO** (serve il bus) | come sopra |
| 8 | `verimem/mesh_memory.py:383` `mesh_respond_topk` | «demone: ascolta sul canale delle richieste e risponde coi top-k locali» | **NON MISURATO** (è un demone) — **e risponderebbe il vuoto** | non eseguito: gira finché non scadono i secondi dati. Per ogni richiesta calcola i top-k locali con la funzione della riga 3 |

## T-MAP-9 — la memoria condivisa fra istanze è ferma sul modello LEGACY

**Tre misure indipendenti, tutte nello stesso giro:**

1. **store nuovo, creato dal prodotto senza nessuna mia configurazione** →
   `embedding_model = 'intfloat/multilingual-e5-base'`, embedding **3072 byte =
   768 float32**;
2. **`config.py:66`** chiama `sentence-transformers/all-MiniLM-L6-v2` (che
   `config.py:88` dichiara a **384**) `_LEGACY_EMBEDDING_MODEL` — il 384 è il
   modello **superato**, non il corrente;
3. **lo store vivo** (sola lettura, `mode=ro`): **18.092 fatti**, tutti
   `intfloat/multilingual-e5-base` a **3072 byte**. Zero righe a 1536.

⇒ Su questo store `local_topk_embeddings` non può selezionare nulla, e non lo
dice: **nessun errore, nessun log, una lista vuota**. È la forma che abbiamo già
in casa — *«una capacità spenta non emette segnale»* — con in più la giuntura:
il modulo e lo store hanno due dimensioni diverse e nessuno dei due sa dell'altro.

**Si propaga**, e i chiamanti sono **letti**: `mesh_memory.py:227`
(`mesh_fuse_local_remote`) e **`syscall_bridge.py:107` e `:123`**, che importano
la funzione e ne usano gli `hits`.

**Perché i test non lo vedono**: `tests/test_mesh_memory.py` (4 prove) costruisce
gli embedding **a mano a 384** (`EMBED_DIM = 384` alla riga 25 del test,
`assert len(emb) == EMBED_DIM * 4` alla 89). Il banco conferma il codice contro
sé stesso; **nessuna delle quattro prove passa da uno store scritto dal
prodotto**. È il controllo positivo che manca, non il codice che sbaglia il conto.

**Non curato** (siamo in mappa). Le due vie sono di chi possiede il write path:
leggere la dimensione dallo store invece di fissarla, oppure dichiarare il mesh
fuori servizio finché non lo si aggiorna. La differenza non è di stile: oggi
**una lista vuota dice «non c'è niente di simile»** quando la verità è «non ho
guardato».
