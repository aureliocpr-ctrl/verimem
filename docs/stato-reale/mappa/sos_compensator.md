# `verimem/sos_compensator.py` — 241 righe, 4 funzioni

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **08/09**.

> ⚠️ **Questo file è nella parte del lead** (indice: 241 righe, 4 funzioni,
> owner `lead`). L'ho mappato io perché il mio righello lo segnalava fra i **tre
> file di `verimem/` interamente non nominati da nessun test**, e la verifica di
> quel reperto è il mio pezzo. Annunciato sul canale prima di cominciare.
> **Il ticket T43 che ne esce ha owner il lead**, non io: non ho scritto la cura
> e non la scriverei su un file altrui.

## Che cosa promette

Il modulo si dichiara (`:11`) «GENUINE B4 NUCLEAR **singolarità candidate**»:
quando l'agente decide dove attaccare un fatto nuovo (l'anchor di `lineage_to`),
**scegliere l'anchor che minimizza lo scostamento atteso della partizione**
(`ΔJ`, Jaccard fra la partizione di Louvain prima e dopo).

Claim falsificabile, `:20-25`, testuale:

> «At fixed k=50 writes, vanilla-random-anchor inject produces ΔJ_random, while
> compensated-anchor inject produces ΔJ_compensated, and **ΔJ_compensated <
> ΔJ_random / 2** on production-scale corpus. If the bench shows
> ΔJ_compensated >= ΔJ_random → FALSIFIED.»

E `:42`:

> «WILL it work? **Falsifiable bench in `tests/test_sos_compensator.py`**.
> Negative result is acceptable per Popperian discipline.»

## 🔴 T43 — il modulo fa l'**opposto** di ciò che il suo docstring dichiara

### Le righe, che si contraddicono fra loro

| riga | codice / testo | conseguenza |
|---|---|---|
| `:96` | `"score": alpha / max(size, 1)` | **score = 1/size** |
| `:98` | `"relative_growth": 1.0 / max(size, 1)` | **identico allo score** |
| `:199` | `if best is None or s["score"] > best["score"]:` | prende il **massimo** |
| `:122` | «Return the best-scored anchor (**LARGEST community**)» | dichiara il contrario di ciò che il codice fa |
| `:127` | «Partition Jaccard is dominated by relative growth, so **minimizing relative growth minimizes ΔJ**» | e il codice la **massimizza** |

Massimizzare `1/size` è **minimizzare `size`**: si sceglie la comunità **più
piccola**. E siccome `score == relative_growth`, si sta **massimizzando la
relative_growth** — l'opposto esatto della riga 127.

### Misurato

Partizione con una comunità da **2** e una da **100**, chiamata reale a
`score_anchor_for_compensation`:

```
compute_community_sizes([{p1,p2}, {g0..g99}]) → {0: 2, 1: 100}     ✅ come promesso

anchor nella comunità da   2 → {'score': 0.5,  'relative_growth': 0.5,  'community_size': 2}
anchor nella comunità da 100 → {'score': 0.01, 'relative_growth': 0.01, 'community_size': 100}
```

Con il `>` della riga 199 vince **0.5**, cioè la comunità da 2, cioè quella che
**perturba di più**.

📌 **Che cosa è eseguito e che cosa è letto**, perché il verdetto sia pesabile:
gli score sopra sono **eseguiti**; il collegamento score → scelta è la riga 199,
**letta**. `select_compensated_anchor` richiede un `semantic.db` e **non l'ho
chiamata**: per chiudere del tutto serve quella esecuzione, e la lascio
all'owner.

### Perché nessuno se n'era accorto

```
ls tests/test_sos_compensator.py                                   → No such file (exit 2)
grep -rln "sos_compensator|compensated_anchor|score_anchor_..." tests/  → nessun risultato
grep -rn "sos_compensator" verimem/                                → nessun chiamante nel prodotto
```

Il banco falsificabile che il modulo **promette a `:42`** non esiste. L'unico
consumatore in tutto il repo è `scripts/bench_sos_compensator.py:126`.

🔑 La disciplina popperiana era **dichiarata e non esercitata**: senza il banco
il modulo non poteva essere falsificato, e infatti non lo è stato. È la stessa
forma del reperto di `ide.py` (un docstring che promette una misura che non
c'è) — ma qui la misura mancante **nascondeva un'inversione di segno**.

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | test | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `verimem/sos_compensator.py:65` `compute_community_sizes` | `{indice: dimensione}` per una lista di insiemi | `select_compensated_anchor` | **nessuno** | **FUNZIONA COME PROMESSO** | eseguita: `{0: 2, 1: 100}` sulla partizione di prova |
| 2 | `verimem/sos_compensator.py:72` `score_anchor_for_compensation` | «higher = better anchor (less expected ΔJ)» | `:199` | **nessuno** | 🔴 **NON COME PROMESSO (T43)** | score 0.5 per la comunità da 2 contro 0.01 per quella da 100: premia chi perturba di più |
| 3 | `verimem/sos_compensator.py:110` `select_compensated_anchor` | l'anchor che minimizza lo scostamento atteso; «LARGEST community» (:122) | nessun chiamante nel prodotto | **nessuno** | 🔴 **NON COME PROMESSO (T43)** | riga 199 prende il massimo di uno score che vale `1/size` (riga 96) ⇒ la comunità più piccola |
| 4 | `verimem/sos_compensator.py:216` `select_vanilla_anchor` | la linea di base: un anchor a caso, per il confronto | nessun chiamante nel prodotto | **nessuno** | **NON MISURATO** | richiede un `semantic.db`; non chiamata |

## Il verdetto, e che cosa NON va fatto

**T43 · NON COME PROMESSO · owner: lead.**

⚠️ **La cura non è invertire `>` in `<`.** Le due frasi del docstring dicono cose
diverse **e una delle due è sbagliata anche come teoria**: va deciso *prima* se
l'anchor buono sta nella comunità grande (che assorbe il fatto nuovo con una
crescita relativa minore, come dice `:127`) o in quella piccola (come implica
`score = 1/size` con «higher = better», `:47`). Il codice oggi non implementa
in modo coerente né l'una né l'altra, e **senza il banco promesso non c'è modo
di dirimere**: il primo passo è scrivere `tests/test_sos_compensator.py`, che il
modulo stesso dichiara di avere.

## Che cosa NON ho misurato

- `select_compensated_anchor` e `select_vanilla_anchor` **eseguite** su un
  `semantic.db` vero: è la prova che chiuderebbe il ticket.
- Il claim quantitativo `ΔJ_compensated < ΔJ_random / 2`: **mai misurato da
  nessuno**, per quanto risulta da `tests/` e da `verimem/`.
