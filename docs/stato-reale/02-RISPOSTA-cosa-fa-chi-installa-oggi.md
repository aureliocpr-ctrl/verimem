# ② — «Se un utente la installa, cosa fa?» — la risposta

> **ws2 «Vega» · 08/08 ore 15:55 · repo SHA `afc6cf73` · tutto misurato sul pacchetto
> `verimem 0.7.0` da PyPI, HOME dedicata, zero variabili `ENGRAM_*`**
> Aurelio ha fatto **una** domanda. La mia fetta è cresciuta a **quattordici file**, che sono un
> archivio e non una risposta. Questa pagina è la risposta; ogni riga ha il file che la prova.

---

## In una riga

**Installa in 10 minuti e 1 GB, il primo fatto che scrive non viene verificato senza che nessuno
glielo dica, il server per gli agenti non parte affatto, e il resto del prodotto fa quello che
promette.**

---

## Minuto per minuto, quello che succede davvero

| quando | cosa vede | verdetto |
|---|---|---|
| **0 → 10 min** | `pip install verimem` — **594 s**, 70 pacchetti, **1,01 GB** (torch 490 MB) | funziona, ma è un'attesa lunga e non annunciata |
| **10 → 12,6 min** | il primo `remember --source` impiega **156 s** e stampa `admitted` | ❌ **il fatto NON è stato verificato**: `grounding_score = NULL` |
| | l'avviso esiste: `warnings[0]` dice *«no grounding judge available — entailment NOT verified»* e come rimediare | ❌ **la CLI non lo stampa** |
| **+ 3 min** | `verimem warmup` — **175 s**, dice cosa scarica e conferma ogni pezzo | ✅ la parte scritta meglio del prodotto |
| **dopo** | `remember --source` → `grounding_score = 96,3` | ✅ da qui in poi verifica davvero |
| **mai** | i due fatti scritti prima restano `NULL` **per sempre** | ❌ nessun comando li rivede |
| **quando serve** | `verimem mcp` — la porta per gli agenti | ❌ **`AttributeError`: non parte** |

⏱️ **Dal nulla al primo fatto verificato: ~13 minuti.**

## Cosa funziona (misurato sul pacchetto, non sul repo)

**Le promesse centrali reggono.** Il gate lessicale quarantina i vanti; con una fonte, il fatto è
ammesso solo se la fonte lo sostiene (94,1 contro 1,1 su una fonte che smentisce); senza fonte entra
come `model_claim` non verificato; i quarantinati **non** escono dal recall; `history()` c'è; la
supersessione non sovrascrive in silenzio; `verified_by` non fa girare il moat.
→ [02h](02h-quali-promesse-reggono-sul-pacchetto.md)

## Cosa non funziona, in ordine di gravità

1. **Il server MCP non parte.** `verimem mcp` → `AttributeError`. Causa: il pacchetto chiede
   `mcp>=1.0.0` senza tetto, `mcp 2.0.0` ha rimosso l'API che il server usa in 11 punti. Tutto il
   resto della CLI funziona: è **solo** la porta degli agenti. Il tetto è nel repo dal 29 luglio e
   non è pubblicato. → [02n](02n-il-server-mcp-e-morto-per-chi-installa.md)
2. **L'astensione è spenta.** A una domanda su cui la memoria non sa nulla, `explain` risponde lo
   stesso: `min_relevance` vale **0.0** nel pacchetto contro **0.8688** su `main`.
   → [02l](02l-l-astensione-e-spenta-nel-pacchetto.md)
3. **`admitted` significa due cose opposte**: un fatto verificato a 93,6 e uno mai giudicato
   stampano la stessa identica riga. → [02c](02c-il-numero-mostrato-e-chi-decide.md)
4. **Mancano 16 comandi su 36**, fra cui `save`, `ignorance`, `correct`, `forget`.
   → [02e](02e-chi-installa-riceve-il-22-luglio.md)
5. **Due dei tre esempi che l'aiuto di `trust` dà non funzionano** (`commit:`, `coverage:`).
   → [02j](02j-trust-il-punto-c.md)

## La causa comune di 1, 2 e 4 — e non è il codice

```
versione installata da PyPI       0.7.0        (pubblicata il 22 luglio)
versione nel pyproject del repo   0.7.0        (stesso numero)
commit sul repo dopo quel bump    375+
```

**Chi installa oggi riceve il codice del 22 luglio con lo stesso numero di versione di oggi.** Non
siamo indietro sul codice: le cure ci sono tutte, in `main`. Siamo indietro sulla **pubblicazione**,
e il numero di versione non distingue i due artefatti. → [02e](02e-chi-installa-riceve-il-22-luglio.md)

**Su `origin/main` le stesse misure danno un esito diverso**: 10 promesse su 10 reggono e
**l'astensione funziona** (2/2, `min_relevance 0.8688`). → [02m](02m-le-promesse-su-origin-main.md)

## Cosa cambierebbe pubblicando la 0.7.5 da `main`

| difetto | lo risolve la pubblicazione? |
|---|---|
| server MCP morto | ✅ il tetto `mcp<2` è già in `main` |
| astensione spenta | ✅ verificato su `origin/main` |
| 16 comandi mancanti | ✅ sono nati dopo il 22/07, arrivano da soli |
| `admitted` ambiguo | ❌ **no** — serve la riga che stampa `warnings` e `confidence_tier` |
| esempi di `trust` sbagliati | ❌ **no** — è una riga di documentazione, presente in entrambi |
| 10 minuti e 1 GB di installazione | ❌ **no** — è torch, ed è una scelta di architettura |

⚠️ E ripara **solo chi aggiorna**: chi ha installato dal 22 luglio ha `mcp 2.0.0` nel proprio
ambiente e ha bisogno di `pip install -U verimem`, non di un riavvio.

## La cura più economica che resta

Una riga in `remember_cmd`: stampare `warnings` e `adjudication.confidence_tier`. L'informazione
**è già nella risposta** — non c'è niente da costruire — e chiude tre difetti insieme (l'utente non
sa che la verifica è spenta, `admitted` ambiguo, la ragione del rifiuto che non arriva).
**Costo misurato: zero rumore** — su 8 scritture sane in 4 lingue, `warnings` è vuoto 8 volte su 8.
→ [02g](02g-il-primo-comando-a-freddo.md)

---

**Come è stato misurato**: pacchetto installato da PyPI in un venv dedicato con HOME finta e ogni
variabile `ENGRAM_*`/`HIPPO_*`/`VERIMEM_*` rimossa; store nuovo per ogni esecuzione; il repo letto
da worktree con `git status` vuoto; il corpus di Aurelio solo in `sqlite mode=ro`.
**Limiti**: una macchina, Windows 11, Python 3.13, una connessione. I tempi (594 s, 156 s, 175 s)
sono misure singole e dipendono dalla rete. Tre volte oggi il difetto era nel mio banco e non nel
prodotto: ogni file porta la correzione dove è successo.
