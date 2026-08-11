# ⑪ — Le chiavi che collassano: due difetti dimostrati sulla funzione, zero collisioni sul corpus

> **Artefatti**: albero `b568b01c` per il codice; per la popolazione
> `C:\Users\aurel\.engram\semantic\semantic.db` (93 544 448 byte) e
> `C:\Users\aurel\.engram\episodes\episodes.db` (17 608 704 byte), entrambi letti in `mode=ro`.
> Nessuna scrittura, nessun giudice caricato.

---

## Perché uno sweep

Due difetti della stessa forma erano stati trovati **per caso**, in punti indipendenti: un alias di
directory che dava a due store la stessa impronta, e una regex che dava a due documenti la stessa
chiave di fonte. Due istanze indipendenti dicono che la forma è ricorrente; nessuno aveva cercato
le altre.

Il perimetro è **lessicale**: le funzioni in `verimem/*.py` che producono una chiave o un'identità
da testo, cercate per nome (`canonical_*`, `*_key`, `*_id`, `*fingerprint`). Otto trovate — è un
limite inferiore, perché una funzione che deriva un'identità senza dirlo nel nome resta fuori.

## Il censimento

| funzione | forma | esito |
|---|---|---|
| `canonical_source` (`source_trust`) | regex `[^:]+` | difetto noto, vivo nel pacchetto pubblicato |
| `_store_fingerprint` (`flow_events`) | alias della data dir | difetto noto, curato |
| **`_verified_by_key`** (`codebase_ingest`) | `",".join(sorted(...))` | **collisione dimostrata** |
| **`_key`** (`episode_dedup`) | tupla + `[:8000]` | **collisione dimostrata** |
| `_content_hash_id` (`mcp_server`) | SHA256 a 12 caratteri | collisione **dichiarata nel docstring** |
| `subject_key` (`composer`) | normalizza | sano, verificato eseguendolo |
| `_key` (`conversation_ingest`) | `casefold` + `strip` | sano, letto |
| `canonical_bytes` (`tamper_evidence`) | — | non esaminata |

### La forma che cade e quella che regge

Non è casuale quale collassa. **Cade la concatenazione con un separatore che può comparire nei
pezzi**: `",".join(...)` in un caso, la regex `[^:]+` che si ferma al primo `:` di `C:` nell'altro.
**Reggono la tupla** — `episode_dedup` restituisce `(a, b, c)`, dove non c'è separatore da
confondere — **e la normalizzazione**.

Ed è onesto dichiarare lo spazio di collisione quando è inevitabile: `_content_hash_id` lo scrive
nel proprio docstring. Non è un difetto nascosto, è una scelta.

> Una chiave composta si fa con una tupla, non concatenando. Se deve essere una stringa, il
> separatore va escluso dai pezzi, o va scelto un carattere che non può comparirvi.

## I due difetti, eseguiti

**`_verified_by_key`** — `['a,b', 'c']` e `['a', 'b,c']` producono entrambi `'a,b,c'`. Un caso
sbagliato su cinque; i quattro controlli tengono, quindi il difetto è circoscritto agli elementi
che contengono una virgola. Quella chiave alimenta `_already_persisted`, la sonda di idempotenza:
una collisione fa scambiare un fatto nuovo per uno già presente, e non viene scritto — senza
errore né avviso.

**`_key` di `episode_dedup`** — la soglia esatta, misurata e non dedotta:

```
differenza al carattere 8000  ->  chiavi diverse
differenza al carattere 8001  ->  stessa chiave
```

Due casi sbagliati su cinque, su due superfici (`task_text` e `final_answer`). Qui il troncamento è
**deliberato**, verosimilmente per costo: il difetto non è il limite, è che il docstring non lo
dichiara e chiama la chiave «strict».

## E la popolazione, che è la metà mancante

Un difetto dimostrato **sulla funzione** non è ancora un difetto **del prodotto**. Misurato sul
corpus:

| | condizione necessaria | collisioni reali |
|---|---|---|
| `_verified_by_key` | **11** righe su **9631** con `verified_by` non vuoto hanno un elemento contenente una virgola | **0** |
| `_key` `episode_dedup` | **8** episodi su **419** superano gli 8000 caratteri (tutti su `final_answer`, nessuno su `task_text`) | **0** |

In entrambi i casi il materiale per la collisione **è già in casa** e la collisione **non si è mai
verificata**. I due difetti sono veri sulla funzione e **latenti** sul corpus: oggi non stanno
perdendo nessun fatto e nessun episodio.

L'esito era stato dichiarato prima della misura, per non adattarlo al risultato: *«se la quota è
zero, i due difetti restano veri sulla funzione e irrilevanti su questo corpus, e va scritto
così»*.

## Una trappola incontrata strada facendo

```
candidato  ~/.engram/episodes/episodes.db   esiste=True  byte=17608704
candidato  ~/.engram/episodes.db            esiste=True  byte=0
```

**Il percorso ovvio esiste ed è vuoto.** È la stessa disposizione già nota per `semantic.db`, dove
il file al percorso diretto ha zero righe e quello annidato le ha tutte. Chi conta gli episodi
puntando al percorso ovvio **legge zero e conclude che il corpus è vuoto**. Il percorso lo dà
`CONFIG`, o la funzione che risolve le due disposizioni (`auto_dream_trigger.py:163`).

---

**Caveat**: un corpus, quello di questa macchina — con altre convenzioni di `verified_by` il conto
cambia. Sono state misurate le **chiavi**, non i loro consumatori: che una collisione porti davvero
a perdere una scrittura (`_already_persisted`) o a raggruppare due episodi
(`find_duplicate_groups`) resta letto nel codice, non eseguito. Le 11 righe con la virgola non sono
state ispezionate una per una.
