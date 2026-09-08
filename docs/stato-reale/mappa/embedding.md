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
**Non ho verificato** che tutti i chiamanti li usino — è il genere di cosa che non emette
segnale.

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
  confronto fra due spazi. **Non ho verificato se i due si incontrino mai**, e questa è la
  domanda giusta (è la stessa forma di CVE-008: nessuno dei due lati sbaglia, il rischio sta
  dove si toccano).
- **Non ho misurato il timeout di `_MODEL_LOCK`** sotto contesa reale: so che esiste ed è 90 s
  di default, non cosa succede a chi ci finisce dentro.
- **`_cached_encode` è un LRU**: non ho controllato la sua dimensione né se la cache possa
  servire un vettore del modello *precedente* dopo un cambio (`vettore_compatibile` esiste,
  ma non so se la cache passi da lì).

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. La misura del trascinamento in §2 è mia, dell'08/09;
la verifica della cura è di @ws1, attribuita.*
