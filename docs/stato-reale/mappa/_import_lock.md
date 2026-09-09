# `verimem/_import_lock.py` — 86 righe, 2 funzioni

**Il file più piccolo della superficie, e quello con la regola più facile da violare.**
Mappato su `7b9e8ca1`. Due funzioni, entrambe pubbliche.

---

## 1. A cosa serve: due difetti misurati, una causa sola

Il docstring porta i due casi che l'hanno prodotto, misurati il 06/09:

    T1b (bloccante)     due create_module in parallelo, entrambi FERMI
                        (scipy.linalg._fblas e numpy.random._bounded_integers)
                        banco end-to-end su main pulito: 0 giri su 3

    P0 (fallimentare)   «cannot import name 'AutoModelForSequenceClassification'»
                        con warm su thread; warm sincrono -> grounding 98.37, judged True

⇒ **non sono due bug**: un import pesante eseguito su un thread mentre lo stesso pacchetto
si inizializza altrove **o si blocca o fallisce**.

---

## 2. 🔑 LA REGOLA, e il fatto che è stata violata due volte

> **IL LOCK SI TIENE SOLO ATTORNO ALL'IMPORT, MAI ATTORNO AL LAVORO.**

Il perché è un numero: i pesi del giudice sono **746 MB e 19,1 s**; sotto il lock, una
richiesta che arriva nel frattempo aspetterebbe diciannove secondi.

**Violata due volte, entrambe trovate l'08/09:**

| dove | cosa c'era sotto il lock | esito |
|---|---|---|
| `wake.py:307` | `self._rng = rng or np.random.default_rng()` — **lavoro** | curato in `cd644eff`: import esplicito dentro, costruzione fuori |
| — | *(la seconda l'ha trovata il presidio, non io)* | |

📌 La riga di `wake.py` **l'avevo scritta io il 06/09** creando questo stesso lock, e l'ha
trovata `test_sotto_il_lock_ci_vanno_SOLO_import`, non io. **Chi scrive la regola non è
esente dal violarla**, e per questo la regola ora è presidiata da una cella invece che da un
docstring.

---

## 3. La rientranza, e perché non è un dettaglio

`_LOCK = threading.RLock()` — **rientrante di proposito**: un import ne innesca altri, e con
un lock semplice il primo import annidato nello stesso thread **si autobloccherebbe**. Il
docstring lo dice così: *«un deadlock introdotto dalla cura, che è il modo peggiore di
curare»*.

## 4. `e_tenuto_da_un_altro_thread` (68) — il nome che dichiara il proprio limite

Si chiamava `e_tenuto()`. **Su un RLock mentiva**: `acquire(blocking=False)` chiamata dal
thread che già lo tiene **riesce**, quindi rispondeva `False` su un lock tenuto. Rinominata
perché *«un misuratore che risponde a una domanda diversa da quella che sembra è peggio di
nessun misuratore»*.

⚠️ Il docstring dice anche **come NON usarla**: *«Solo per i banchi… Non usarla per decidere
— fra la risposta e l'azione lo stato può cambiare»*. È una funzione che documenta di essere
inaffidabile per il controllo di flusso: raro e giusto.

## 5. `lock_import()` (58) — torna sempre lo STESSO oggetto

E il docstring spiega il modo silenzioso in cui una cura così può essere inutile: se
tornasse un lock nuovo a ogni chiamata, *«due chiamanti si serializzerebbero ognuno con sé
stesso e con nessun altro — un lock che non protegge niente e non lo dice»*. Presidiato da
`test_il_lock_e_UNO_solo`.

---

## 6. ⚠️ Il limite del modulo, e non è nel docstring

**Un lock serializza solo chi lo prende.** Al 08/09 mattina erano scoperti
`local_grounding.py:450`, `local_relation.py:90-91` (curati in `b3adfc74`) e —
la causa vera di T26a — **`embedding.py`, che usava solo il proprio `_MODEL_LOCK`** mentre
`sentence_transformers` **trascina** `transformers` (misurato: `PRIMA False → DOPO True`).
Curato in `cd644eff`.

📌 ⇒ **Nel prodotto convivono TRE lock** che avvolgono import pesanti: `_import_lock._LOCK`,
`embedding._MODEL_LOCK`, `semantic._RERANKER_LOCK`. L'ordine è sempre lo stesso — quelli dei
modelli **fuori**, questo **dentro**, mai l'inverso — e ciò rende il deadlock **non
esprimibile** finché sotto `lock_import` ci sono solo `import`. **Questa proprietà è
l'unica cosa che tiene in piedi la sicurezza dei tre lock, ed è presidiata da una cella
sola.** Se qualcuno la toglie, il ciclo torna possibile.

---

## 7. Quello che questa mappa NON dice — dichiarato

- **Il perché due `create_module` in parallelo si blocchino resta un'IPOTESI** (il loader
  lock di Windows) e **non è osservabile da Python**: il file lo dichiara, e la cura non ne
  dipende.
- **Non ho verificato** che i tre lock siano gli unici: ho cercato quelli che avvolgono
  `torch`/`transformers`/`sentence_transformers`, non ogni lock del prodotto.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. I numeri del §1 sono nel docstring del modulo; quelli
del §6 sono miei, misurati l'08/09.*

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


### `verimem/_import_lock.py` — 2 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/_import_lock.py:58` `lock_import` | funzione: Il lock degli import pesanti. Da usare come context manager. | `verimem/local_grounding.py`; `verimem/preload.py` (+1) | `tests/test_gli_import_pesanti_si_mettono_in_fila.py` | NON MISURATO |
| 2 | `verimem/_import_lock.py:68` `e_tenuto_da_un_altro_thread` | funzione: True se il lock e' preso da un THREAD DIVERSO da chi chiama. | **nessuno** | `tests/test_gli_import_pesanti_si_mettono_in_fila.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





