# Fetta ② — L'UTENTE CHE INSTALLA: dal nulla al primo fatto

**Autore**: ws2 «Vega» · **Data**: 2026-08-08, ore 12:40–13:05
**Metodo**: venv nuovo, `HOME`/`USERPROFILE` finti, nessun `~/.engram`, variabili
`ENGRAM_*`/`HIPPO_*`/`VERIMEM_*` rimosse dall'ambiente. **Ogni riga qui sotto è ESEGUITA**: dove
non ho eseguito, lo dico.
**Pacchetto misurato**: `verimem 0.7.0` **da PyPI** (non dal repo) — è ciò che installa un utente.

---

## 1. I NUMERI DELL'INSTALLAZIONE

| cosa | misura |
|---|---|
| `python -m venv venv` | **16 s** |
| `pip install verimem` | **594 s (9 min 54 s)** |
| pacchetti installati | **70** |
| peso su disco del venv | **1,01 GB** |
| pacchetto più pesante | **torch 490 MB** (poi scipy 108, transformers 94, sympy 66) |
| primo `verimem --help` | 8 s |
| primo `verimem doctor` | 8 s |
| **primo `verimem remember`** | **133 s** (scarica il modello di embedding) |
| secondo `remember` (a caldo) | 25 s |
| `recall` | 4 s |
| `trust` | 3 s |

**Il primo fatto costa a un utente ~12 minuti** (10 di installazione + 2 al primo comando che
scarica il modello), su una connessione veloce e senza contare il download del giudice.

---

## 2. COSA VEDE SULLO SCHERMO — i cinque attriti, in ordine di gravità

### ⚠️ ① `verimem save` NON ESISTE nel pacchetto pubblicato
```
$ verimem save "..." --topic magazzino
Error: No such command 'save'.
```
Il comando che il nostro protocollo interno prescrive (**O3**: `verimem save … --lineage-to auto
--source …`) **non è nella 0.7.0**. Confronto eseguito:

* **PyPI 0.7.0** (26 comandi): status health backup-all warmup doctor airgap index search-docs
  console import **remember** recall stats trust mcp reset metrics dashboard introspect
  agent-guide skills episodes providers facts consolidate gateway flow agent
* **repo locale** (37): gli stessi **+ ask correct ignorance telemetry save tip recent digest
  chain handoff audit**

⇒ Chi legge la nostra documentazione interna e usa il pacchetto pubblicato **sbatte contro un
errore al primo comando**. Il comando equivalente esistente è `remember`, ma non lo dice nessuno.

### ⚠️ ② Il `doctor` dice che il moat è SPENTO, e ha ragione
Su installazione vergine:
```
✗ moat-judge  NO grounding judge: local CE model missing … and no llm provider detected
              — writes are admitted with an L4-skipped advisory (moat OFF)
     fix: run `verimem warmup` … (~656 MB, no account needed)
```
⇒ **La promessa di punta del prodotto — "un fatto che la fonte non sostiene viene quarantinato" —
è INATTIVA appena installato.** Serve un secondo download da 656 MB che nessuno annuncia prima.
Il doctor lo dice chiaramente: è il pezzo di onestà migliore che ho visto oggi.

### 🔴 ③ `trust` risponde TRUSTED a una domanda a cui non può rispondere
```
$ verimem trust "qual e' il fatturato del 2025?"      # nessun fatto in memoria sul fatturato
  Anti-confab trust check   TRUSTED ✓
  provenance:  (none)
  no anti-confab flags — adequate evidence / not a risky assertion
```
**Provenance «(none)» e verdetto «TRUSTED».** Su uno store con 2 fatti, nessuno dei quali parla di
fatturato. La riga che il prodotto vende («abstention over hallucination») qui **dice il
contrario**: un utente che chiede una cosa che la memoria non sa si sente rispondere che è
attendibile. Stesso esito sulla domanda a cui invece *può* rispondere: **le due situazioni sono
indistinguibili sullo schermo.**
⚠️ Da verificare da chi ha il perimetro: sospetto che senza giudice (punto ②) `trust` non abbia
nulla con cui decidere e degradi a «nessun flag». Non l'ho verificato nel codice — è la fetta di
un'altra.

### ⚠️ ④ Il `recall` funziona ma degrada, e lo dice in gergo
```
$ verimem recall "quanti pallet ci sono a Verona?"
encode exceeded 2.0s budget → degrading (save defers / recall falls back to keyword);
kicking the encode daemon awake
- Il magazzino di Verona contiene 480 pallet [0.00]
```
Il fatto giusto esce. Ma con **rilevanza `[0.00]`** e un messaggio che un utente non può
interpretare. Chi non ha letto il codice conclude «ha trovato qualcosa ma con punteggio zero,
quindi non è sicuro» — mentre è la risposta esatta.

### ⚠️ ⑤ Rumore di libreria al primo comando
Il primo `remember` stampa: warning symlink di HuggingFace (5 righe con link a docs Microsoft
sull'attivazione della Developer Mode), «You are sending unauthenticated requests to the HF Hub»,
una barra di avanzamento, e un `FutureWarning` interno di verimem
(`get_sentence_embedding_dimension` rinominato). **Poi**, in fondo, la riga utile:
```
admitted id=4150c1733111 topic=user
```

---

## 3. COSA FUNZIONA DAVVERO, appena installato

| capacità | stato | prova |
|---|---|---|
| installazione da PyPI | ✅ | `verimem 0.7.0` installato, 70 pacchetti |
| scrittura di un fatto | ✅ | `admitted id=4150c1733111` |
| lettura per parola chiave | ✅ | il fatto giusto esce |
| lettura semantica | ⚠️ degradata | budget encode superato al primo giro, fallback keyword |
| **gate anti-confabulazione** | ❌ **spento** | `moat-judge: NO grounding judge … (moat OFF)` |
| **astensione** | ❌ **non osservata** | `TRUSTED ✓` su domanda senza risposta |
| documenti / RAG | non provato | fuori dalla mia fetta (`index`/`search-docs` esistono) |

---

## 4. LA RISPOSTA ALLA DOMANDA DI AURELIO

> «se un utente la installa cosa fa?»

Aspetta dieci minuti, ne aspetta altri due al primo comando, e ottiene **una memoria che scrive e
rilegge**. Ma le due cose che distinguono Verimem da un file di testo — **il gate che rifiuta i
fatti non sostenuti** e **l'astensione invece dell'invenzione** — **non sono attive**: la prima è
dichiarata spenta dal doctor, la seconda risponde `TRUSTED` a una domanda su cui non ha dati.

Il percorso onesto per un utente sarebbe: `pip install` → **`verimem warmup`** (il doctor lo dice)
→ *poi* i primi comandi. Ma `warmup` non compare da nessuna parte prima che l'utente esegua
`doctor` di sua iniziativa, e nulla nel primo comando lo suggerisce.

**Cura a costo zero suggerita** (decisione di chi ha il perimetro, io misuro): far stampare al
primo `remember` su store vuoto la riga che il doctor già sa dire — *«il giudice non è installato:
questo fatto entra senza verifica. `verimem warmup` per attivarlo»*.

---

## 5. LIMITI DI QUESTA MISURA (dichiarati)

* Una sola macchina, Windows 11, Python 3.13.12, connessione domestica. I 594 s di `pip install`
  dipendono dalla rete: **il numero riproducibile è 70 pacchetti / 1,01 GB**, non i secondi.
* Non ho eseguito `verimem warmup` (656 MB): quindi **non ho verificato che dopo il warmup il moat
  si accenda davvero.** È il primo controllo che chiederei a chi riprende questa fetta.
* Non ho provato `index`/`search-docs` (documenti), `console`, `gateway`, `mcp`: fuori fetta.
* Il primo `doctor` che ho eseguito ha letto il **data-dir di produzione** perché la mia shell
  aveva `ENGRAM_DATA_DIR` esportata: **contaminazione mia, corretta rilanciando con `env -u`.**
  Segnalo la trappola perché chiunque di noi misuri "da utente" su questa macchina la incontra.

---

## 6. IL BUCO CHE AVEVO DICHIARATO — CHIUSO (ore 13:30-13:35)

Nella §5 avevo scritto: «non ho eseguito `verimem warmup`, quindi **non ho verificato che dopo il
warmup il moat si accenda davvero**». Eseguito adesso. **Si accende, e il prodotto mantiene la
promessa.**

### 6.1 Il warmup
```
$ verimem warmup
✓ model ready in 35.2s (vector dim 768)
✓ reranker ready in 59.1s
✓ moat gate model ready — gate model installed at …\home\.engram\models\local_gate_ce_v2
✓ shared encode daemon already running
Warmup complete — Verimem recall will be instant.
```
**190 secondi.** Il doctor dopo: `✓ moat-judge  local CE gate model installed — the grounding
moat is ON`.

### 6.2 Il gate FUNZIONA — quattro prove
| prova | esito | layer |
|---|---|---|
| vanto senza fonte («ho verificato che… tutti i test passano») | **quarantined** | `L1.15` |
| fatto NON sostenuto dalla fonte (dico 900, la fonte dice 250) | **quarantined** | `L4-grounding` |
| fatto sostenuto dalla fonte (dico 250, la fonte dice 250) | **admitted** | — |
| fatto neutro senza fonte | admitted `model_claim` | — |

⇒ **Dopo il warmup, le due promesse centrali sono VERE**: lo screening lessicale ferma i vanti, e
il moat dell'entailment quarantina un numero che la fonte non sostiene ammettendo quello che
sostiene. Il controllo positivo c'è: non è un gate che blocca tutto.

### 6.3 Ma `trust` risponde ancora `TRUSTED` — il punto ③ NON è causato dal moat spento
```
$ verimem trust "qual e' il fatturato del 2025?"     # moat ON, store con 4 fatti, nessuno sul fatturato
  Anti-confab trust check   TRUSTED ✓
  provenance:  (none)
```
**Identico a prima del warmup.** Quindi la mia ipotesi della §2③ («senza giudice `trust` non ha con
cosa decidere») **è falsificata**: il giudice c'è, e `trust` risponde lo stesso `TRUSTED` con
`provenance: (none)` su una domanda che la memoria non può sostenere.
⇒ Il difetto è di `trust`, non del moat. Resta il candidato più serio della mia fetta.

### 6.4 Il costo reale, aggiornato
| | |
|---|---|
| installazione | 594 s |
| warmup (necessario perché il prodotto mantenga le promesse) | **190 s** |
| primo `remember` (dopo warmup: niente download) | ~2 s |
| **totale dal nulla al primo fatto verificato** | **~13 minuti** |

### 6.5 Una nota di coerenza dei percorsi
Il data-dir su installazione pulita è `…\home\.verimem`, ma il modello del gate viene scritto in
`…\home\.engram\models\`. **Due cartelle diverse nella stessa installazione vergine.** Non è un
difetto funzionale (funziona), ma un utente che volesse cancellare tutto ne troverebbe una sola.
