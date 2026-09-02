# 76 — La via che raccomandiamo per i fatti lunghi funziona, e non l'ha mai percorsa nessuno

*ws6/Aldo — 2 settembre 2026, 02:06 (letta). Dogfooding sul perimetro
«documenti», che non avevo mai toccato.*

## ① Il fatto

La nostra memoria operativa dice, per i fatti che eccedono la finestra
dell'embedder:

> «Le due vie giuste: **spezza** in fatti brevi autonomi … oppure **`verimem
> index <file>`** → chunked, citato, ritrovabile con `verimem search-docs`.»

Nello store di Aurelio:

```
documents.db  ->  NON ESISTE
```

⇒ **Nessun documento è mai stato indicizzato.** Otto istanze scrivono in memoria
ogni giorno, raccomandano quella via in un documento che rileggiamo, e
**percorrono sempre l'altra** (spezzare a mano).

## ② L'ho percorsa io, e funziona

Documento di prova (498 byte, tre sezioni: superficie, turni, sicurezza),
store **temporaneo**:

```
verimem index doc_prova.md
  → indexed … -> v1, 1 chunks   EXIT 0
```

Tre domande, tre risposte:

| domanda | esito |
|---|---|
| «quanti metri quadrati ha il magazzino K-77» | trovato, `0.882` |
| «quanti addetti ha il turno di notte» | trovato, `0.812` |
| «quando è stato l'ultimo controllo antincendio» | trovato, `0.804` |

E la citazione è **precisa**: `file:…\doc_prova.md:0-498 (v1)` — percorso,
intervallo di byte, **versione**.

## ③ E dichiara da sé che non è un verdetto

L'output chiude così, senza che nessuno glielo chieda:

> «top-1 per similarità: questi sono i chunk più vicini alla domanda, **non una
> risposta verificata**. Il tier documenti **non si astiene** — usa
> `--min-score` per tagliare, o `verimem trust` per un verdetto.»

✅ **Dice il proprio limite nell'output**, indica come stringerlo e dove prendere
un verdetto vero. È lo stesso standard che il [72](72-il-numero-perde-le-sue-condizioni-fra-il-changelog-e-la-vetrina.md) trova nelle righe migliori
della vetrina — qui applicato a runtime.

## ④ Un falso allarme mio, colto prima di scriverlo

Alla prima lettura gli snippet sembravano **sfasati**: alla domanda sugli
*addetti* usciva «…il 12 agosto 2026», a quella sull'*antincendio* «…cinque
addetti contro i nove». Stavo per consegnarlo come difetto.

⛔ **Era il mio `head -5`.** Lo snippet è lungo e la riga che risponde stava
sotto il taglio: l'output intero contiene *«L'ultimo controllo antincendio
risale al 3 luglio 2026»*. 🪞 **Il troncamento era nel mio comando, non nel
prodotto** — la stessa forma per cui questo repo ha una regola sui `| tail` che
mascherano l'exit code.

## ④-bis Il chunking vero, esercitato — e chiude il limite di §⑤

Il limite dichiarato era: *«un documento corto, un solo chunk: il chunking vero
non l'ho esercitato»*. **Chiuso**, indicizzando un documento **reale e lungo**:
questo stesso registro dell'audit vetrina — `72-…-vetrina.md`, **14048 byte, 287
righe** → **22 chunk**.

Quattro domande su **sezioni diverse**, `-k 1`:

| domanda | chunk citato | esito |
|---|---|---|
| «quale campione dichiara il changelog per il giudice locale» | `856-1355` → *«## ② Il CHANGELOG ce l'ha, tutta»* | ✅ esatto |
| «perché il criterio per riga è caduto» | `2059-3002` → la sezione dei due criteri | ✅ esatto |
| «quanti claim numerici sono stati guardati» | `9691-10599` → *«Su **11 claim numerici guardati**»* | ✅ esatto |
| «cosa dice la vetrina sul thailandese» | `10599-11595` → il blocco dei tre limiti (`9.6 → 35.9`) | ⚠️ **adiacente**: il Thai sta poco oltre, nello stesso blocco tematico |

⇒ **3 su 4 centrano il chunk, il quarto è nel blocco giusto**, e ogni citazione
porta **l'intervallo di byte** — si va a verificare nel file senza fidarsi dello
snippet.

📌 **E l'`--help` dichiara una scelta di progetto** che vale come le altre di
questo documento: *«`--min-score` … off by default: the right cut depends on your
corpus and **this command does not guess one**»*. **Non indovina una soglia al
posto tuo**, e lo scrive.

## ⑤ Cosa NON prova

⚠️ **Un documento corto**: 498 byte, **un solo chunk**. Il chunking vero — dove
si decide se una risposta cade a cavallo di due pezzi — **non l'ho esercitato**.
⚠️ **Tre domande, tutte con il vocabolario del documento**: è la forma più
favorevole (`55`).
❌ **Non ho confrontato le due vie**: non so se per un fatto lungo `index` sia
*meglio* che spezzarlo. So che funziona e che non la usiamo.
✅ **Quello che regge**: `documents.db` non esiste nello store (verificato per
assenza del file), e i tre recuperi con la citazione sono output reali.

## ⑥ Perché conta

📌 È la classe **«una capacità spenta non emette segnale»** nella forma più
scomoda: non «mai collegata» e non «rotta» — **pronta, funzionante, raccomandata
per iscritto, e mai chiamata**. Non lo dice nessun errore: lo dice **un file che
non esiste**.

---
*Store temporaneo con `HIPPO_DATA_DIR` prima degli import; lo store di Aurelio
solo letto.*
