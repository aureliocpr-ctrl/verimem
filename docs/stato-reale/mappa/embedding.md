# `verimem/embedding.py` — 529 righe, 29 funzioni

**Il file che dichiara il proprio degrado meglio di ogni altro nella superficie — e che
conteneva la causa radice di T26a.** Mappato su `7b9e8ca1`. 16 pubbliche, 13 private.

---

## 1. Il degrado, fatto bene: un'eccezione DEDICATA invece di un `None`

    class EncodeDelegateUnavailable(RuntimeError)        (168)

> *«…so the caller **DEGRADES** instead of blocking ~33s»* (309) · *«…if the daemon is down,
> so the caller DEGRADES»* (355)

🔑 **È il modello da copiare**, e altrove nel prodotto non è copiato: qui l'indisponibilità
ha **un tipo**, non un valore di ritorno ambiguo. Chi chiama non deve indovinare se il
`None` significhi «non c'è vettore» o «non ho potuto chiedere».

📌 E c'è pure il **perché** dell'ultimo rifiuto: `ultimo_rifiuto_del_servizio` (236) —
*«Perché il daemon ha rifiutato l'ultima richiesta, se l'ha detto»*. Un campo che esiste per
non far dedurre una diagnosi a chi legge.

---

## 2. La promessa `delegate-only`, alla lettera

`_delegate_only` (179): *«True in an MCP-server process (`HIPPO_ENCODE_DELEGATE_ONLY=1`):
**NEVER** [cold-load the model here]»*, e `_encode_local` (222) *«Never touches the
service»*: le due strade sono separate per contratto.

⚠️ **Ma la promessa vale per il MODELLO, non per gli IMPORT** — ed è esattamente lì che si
è rotta: fino a `cd644eff` (oggi) `_load_model` (50) importava `sentence_transformers`
**solo** sotto `_MODEL_LOCK`, mentre il giudice importa `transformers` sotto `_import_lock`.
E `sentence_transformers` **trascina** `transformers` (misurato l'08/09: `PRIMA False →
DOPO True`, 43,8 s). ⇒ due lock diversi sullo stesso import, e il warm del giudice falliva
3 volte su 3 senza daemon.

📌 **Curato oggi**: l'import ora passa da `lock_import()` **dentro** `_MODEL_LOCK`, solo
l'import. Provato da @ws1: 3 giri su 3 giudicati, `moat_judge_failed` 0 su 6.

---

## 3. `_MODEL_LOCK` avvolge anche il LAVORO — dichiarato, non curato

`_MODEL_LOCK.acquire(timeout=_MODEL_LOCK_TIMEOUT_S)` (87) copre `_load_model()` **e** il
caricamento del modello. È il contrario della regola di `_import_lock`, e il file lo sa:

> riga 42: *«a stall under `_MODEL_LOCK` **wedges all embedding for hours**»*
> riga 65: *«under `_MODEL_LOCK` -> a stall wedges EVERY embedding for hours. **NEVER** …»*

La difesa non è togliere il lock ma **limitarlo nel tempo**: l'acquisizione ha un
**timeout (90 s di default)** e fallisce in fretta invece di aspettare per sempre —
*«degraded-but-responsive > the 4h infinite hang»*, con la data dell'incidente (2026-06-05).

⇒ **Reperto**: il prodotto ha due strategie diverse per lo stesso rischio — `_import_lock`
lo evita **per struttura** (solo import sotto il lock), `_MODEL_LOCK` lo tollera **con un
timeout**. Nessuna delle due è sbagliata, ma **non sono scritte in un posto solo**, e chi
legge un file non sa dell'altro.

---

## 4. Le guardie contro il fallimento silenzioso — tre, e tutte nominate

| funzione | cosa impedisce |
|---|---|
| `_adopt_observed_dim` (101) | *«kill the **silent-empty-recall trap**»*: dimensione dichiarata ≠ dimensione reale ⇒ il recall tornava vuoto senza dirlo |
| `vettore_compatibile` (460) | *«Il vettore è di questo modello, o di uno che non c'è più?»* — un embedding orfano dopo un cambio modello |
| `verify_model_dim` (494) | *«**Falsification guard**: load the encoder and compare its real output dim»* |

🔑 Tutte e tre curano la stessa classe: **un numero che non torna e che nessuno controlla
produce un vuoto, non un errore.** È la forma che sui nostri appunti si chiama *«una misura
che non c'è si legge come perfetta»*.

---

## 5. I prefissi e5 — `as_query` / `as_passage` (436, 442)

`_needs_e5_prefix` (429): i modelli e5 sono addestrati con `query: ` / `passage: `. ⚠️ Se
questi prefissi venissero applicati al contrario, o dimenticati da un chiamante, **il
retrieval peggiorerebbe senza errori**: nessuna eccezione, solo risultati un po' peggiori.

⇒ **Ma la domanda «tutti i chiamanti li usano?» è posta male**, e il §7 lo mostra: sono
**due convenzioni dichiarate**, una per sottosistema, e `memory.py` vieta di allinearle. Il
rischio vero è la **giuntura**, ed è ristretto (due store distinti) ma non escluso: vedi §7.

---

## 6. Le 29 funzioni

**Pubbliche (16)**: `is_loaded` · `service_would_encode` · `ultimo_rifiuto_del_servizio` ·
`encode` · `encode_cache_clear` · `encode_cache_info` · `model_signature` · `as_query` ·
`as_passage` · `expected_embedding_bytes` · `vettore_compatibile` · `verify_model_dim` ·
`cosine` · `cosine_matrix` · `serialize` · `deserialize`.
**Private (13)**: `_offline` · `_load_model` · `_model` · `_adopt_observed_dim` ·
`_adopt_true_dim` · `_reset_model_for_tests` · `_delegate_only` · `_service_enabled` ·
`_encode_local` · `_encode_via_service` · `_encode_one` · `_cached_encode` ·
`_needs_e5_prefix`.

---

## 7. Quello che questa mappa NON dice — dichiarato

- ~~Non ho verificato che i prefissi e5 siano applicati da tutti i chiamanti~~ →
  **VERIFICATO, e la domanda era posta male.** Non è una dimenticanza: **sono due
  convenzioni, entrambe dichiarate.**

      semantic.py    li APPLICA      as_passage in store (175, 184, 3270, 3592)
                                     as_query in recall (4089)
      memory.py:76   NON li applica  «store(), _raw_cosine_recall and compute_salience
                                     are ALL as_passage-free and INTERNALLY CONSISTENT,
                                     so … do NOT "align" it with semantic's as_passage»

  ⇒ Ogni sottosistema è coerente **al suo interno**, e `memory.py` avverte esplicitamente di
  **non** allinearlo. ⚠️ **Il rischio non è il chiamante distratto: è la GIUNTURA** — un
  vettore prodotto senza prefisso confrontato con uno prodotto con prefisso sarebbe un
  confronto fra due spazi (stessa forma di CVE-008: nessuno dei due lati sbaglia, il rischio
  sta dove si toccano).

  📌 **QUANTO HO POTUTO VERIFICARE, e dove mi sono fermata.** Il rischio è **ristretto**, non
  escluso:

      memory.py    → episodes.db   tabelle: episodes · traces · causal_edges
      semantic.py  → semantic.db   tabella:  facts

  **Due store distinti, tabelle distinte**, e il commento vieta l'allineamento. Perché i due
  spazi si incontrino servirebbe una funzione che passa a `cosine()` **un vettore di episodio
  e uno di fatto insieme**.

  ⛔ **Questo NON l'ho verificato, e non si chiude con un comando.** Quattordici file
  importano entrambi i sottosistemi, ma *importarli* non è *confrontarne i vettori*: servirebbe
  seguire i tipi attraverso i chiamanti, e il grep **trova, non decide**. Contare le
  occorrenze di `cosine` in quei file darebbe un numero che non risponde alla domanda —
  sarebbe il righello sbagliato, quello che stasera mi ha già prodotto 20 falsi positivi su 21.

  ⇒ **Resta aperto, con la ragione**: serve una lettura dei tipi, non una ricerca testuale.
- **Non ho misurato il timeout di `_MODEL_LOCK`** sotto contesa reale: so che esiste ed è 90 s
  di default, non cosa succede a chi ci finisce dentro.
- **`_cached_encode` è un LRU**: non ho controllato la sua dimensione né se la cache possa
  servire un vettore del modello *precedente* dopo un cambio (`vettore_compatibile` esiste,
  ma non so se la cache passi da lì).

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`. La misura del trascinamento in §2 è mia, dell'08/09;
la verifica della cura è di @ws1, attribuita.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/embedding.py` — 30 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/embedding.py:39` `_offline` | funzione: True if any offline flag forbids network model loads (the production | `verimem/embedding.py`; `verimem/semantic.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/embedding.py:50` `_load_model` | funzione | `verimem/embedding.py` | `tests/test_embedding_load_no_hang.py`; `tests/test_embedding_load_offline.py` | NON MISURATO |
| 3 | `verimem/embedding.py:74` `_model` | funzione: Return the process-wide SentenceTransformer, loading it exactly once. | `verimem/cli.py`; `verimem/embedding.py` | `tests/perf/bench.py`; `tests/test_embedding_preload.py` | NON MISURATO |
| 4 | `verimem/embedding.py:101` `_adopt_observed_dim` | funzione: iter 31/32 — kill the silent-empty-recall trap: when CONFIG.embedding_dim | `verimem/embedding.py` | **nessuno** | NON MISURATO |
| 5 | `verimem/embedding.py:132` `_adopt_true_dim` | funzione: Load-time adoption: ask the loaded model for its true dimension. | `verimem/embedding.py` | `tests/test_embedding_dim_autodetect.py` | NON MISURATO |
| 6 | `verimem/embedding.py:141` `is_loaded` | funzione: True if the in-process model is already resident — PURE, never loads it. | `verimem/embedding.py`; `verimem/mcp_server.py` (+1) | `tests/test_cold_start_warmup.py` | NON MISURATO |
| 7 | `verimem/embedding.py:151` `_reset_model_for_tests` | funzione: Test-only: drop the cached model and the single-text encode cache. | **nessuno** | `tests/test_embedding_preload.py`; `tests/test_encode_batch_delegate_only.py` (+1) | NON MISURATO |
| 8 | `verimem/embedding.py:168` `EncodeDelegateUnavailable` | classe: Raised by encode() in DELEGATE-ONLY mode when the shared encode daemon is | `verimem/embedding.py`; `verimem/memory.py` (+1) | `tests/test_encode_batch_delegate_only.py`; `tests/test_encode_delegate_only.py` (+3) | NON MISURATO |
| 9 | `verimem/embedding.py:179` `_delegate_only` | funzione: True in an MCP-server process (``HIPPO_ENCODE_DELEGATE_ONLY=1``): NEVER | `verimem/embedding.py`; `verimem/local_grounding.py` (+2) | **nessuno** | NON MISURATO |
| 10 | `verimem/embedding.py:193` `_service_enabled` | funzione: True unless ``ENGRAM_ENCODE_SERVICE`` switches the shared service off. | `verimem/embedding.py`; `verimem/preload.py` | **nessuno** | NON MISURATO |
| 11 | `verimem/embedding.py:207` `service_would_encode` | funzione: True iff a vector is obtainable from the shared daemon WITHOUT a | `verimem/embedding.py`; `verimem/semantic_selfclaim.py` | **nessuno** | NON MISURATO |
| 12 | `verimem/embedding.py:222` `_encode_local` | funzione: In-process encode (loads the model once). Never touches the service — | `verimem/embedding.py`; `verimem/encode_service.py` | **nessuno** | NON MISURATO |
| 13 | `verimem/embedding.py:236` `ultimo_rifiuto_del_servizio` | funzione: Perché il daemon ha rifiutato l'ultima richiesta, se l'ha detto. | `verimem/embedding.py` | `tests/test_il_daemon_dice_perche_e_il_prodotto_lo_ripete.py` | NON MISURATO |
| 14 | `verimem/embedding.py:247` `_encode_via_service` | funzione: Encode via the shared service. Returns None if unavailable so the | `verimem/embedding.py` | `tests/test_encode_service.py`; `tests/test_encode_service_model_guard_scan68b.py` (+1) | NON MISURATO |
| 15 | `verimem/embedding.py:305` `_encode_one` | funzione: Single-text encode: shared service first, in-process fallback. | `verimem/embedding.py` | `tests/test_il_daemon_dice_perche_e_il_prodotto_lo_ripete.py` | NON MISURATO |
| 16 | `verimem/embedding.py:338` `_cached_encode` | funzione: LRU-cached single-text encode. Returns bytes for hashable storage. | `verimem/embedding.py` | **nessuno** | NON MISURATO |
| 17 | `verimem/embedding.py:343` `encode` | funzione: Encode text(s) to L2-normalized float32 vectors. | `verimem/backup.py`; `verimem/capability_token.py` (+37) | `tests/conftest.py`; `tests/perf/bench.py` (+36) | NON MISURATO |
| 18 | `verimem/embedding.py:400` `encode_cache_clear` | funzione: Drop all cached single-text embeddings. | **nessuno** | `tests/conftest.py`; `tests/test_encode_delegate_only.py` (+1) | NON MISURATO |
| 19 | `verimem/embedding.py:408` `encode_cache_info` | funzione: Return functools.lru_cache CacheInfo (hits, misses, maxsize, currsize). | **nessuno** | **nessuno** | MAI CHIAMATA |
| 20 | `verimem/embedding.py:420` `model_signature` | funzione: Version tag of the active encoder (``CONFIG.embedding_model``). | `verimem/corpus_health_metrics.py`; `verimem/memory.py` (+3) | `tests/test_conversational_not_laundered.py`; `tests/test_corpus_health_metrics.py` (+7) | NON MISURATO |
| 21 | `verimem/embedding.py:429` `_needs_e5_prefix` | funzione: e5 models (intfloat/*e5*) sono addestrati coi prefissi ``query: ``/``passage: ``; | `verimem/embedding.py` | **nessuno** | NON MISURATO |
| 22 | `verimem/embedding.py:436` `as_query` | funzione: Testo come QUERY per il modello attivo: e5 -> ``query: ``+text; altri -> invariato. | `verimem/semantic.py` | `tests/test_recall_cold_fallback_bm25.py` | NON MISURATO |
| 23 | `verimem/embedding.py:442` `as_passage` | funzione: Testo come PASSAGE per il modello attivo: e5 -> ``passage: ``+text; altri -> invariato. | `verimem/semantic.py` | **nessuno** | NON MISURATO |
| 24 | `verimem/embedding.py:448` `expected_embedding_bytes` | funzione: Serialized byte length of one embedding for the active model. | `verimem/corpus_health_metrics.py`; `verimem/embedding.py` (+4) | `tests/test_embedding_model_versioning.py`; `tests/test_il_sonno_moriva_su_un_modello_che_non_ce_piu.py` (+4) | NON MISURATO |
| 25 | `verimem/embedding.py:460` `vettore_compatibile` | funzione: Il vettore è di questo modello, o di uno che non c'è più? | `verimem/cli.py`; `verimem/skill.py` | `tests/test_il_sonno_moriva_su_un_modello_che_non_ce_piu.py`; `tests/test_lo_sweep_384_768_fuori_da_skill.py` | NON MISURATO |
| 26 | `verimem/embedding.py:494` `verify_model_dim` | funzione: Falsification guard: load the encoder and compare its real output dim | **nessuno** | `tests/test_embedding_model_versioning.py` | NON MISURATO |
| 27 | `verimem/embedding.py:511` `cosine` | funzione: Cosine similarity between two L2-normalized vectors. | `verimem/cli.py`; `verimem/embedding.py` (+1) | `tests/test_facts_conflict.py` | NON MISURATO |
| 28 | `verimem/embedding.py:516` `cosine_matrix` | funzione: Cosine similarity of one query vector against a (N, D) corpus matrix. | `verimem/semantic.py`; `verimem/skill.py` (+1) | **nessuno** | NON MISURATO |
| 29 | `verimem/embedding.py:523` `serialize` | funzione | `verimem/memory.py`; `verimem/semantic.py` (+2) | `tests/test_conversational_not_laundered.py`; `tests/test_episode_recall_nonfinite.py` (+6) | NON MISURATO |
| 30 | `verimem/embedding.py:527` `deserialize` | funzione | `verimem/freshness_check.py`; `verimem/memory.py` (+6) | `tests/test_hebbian.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





