# I 656 MB — le quattro strade, misurate

    SHA:      63eab6f4 (ramo ws6/control-room)
    DATA:     2026-08-09, misure fra le 17:40 e le 18:05
    AUTORE:   ws7
    MANDATO:  Aurelio — «con il download la persona deve avere il programma
              FUNZIONANTE senza scaricare altro»
    VERDETTO: 🔴 **CURARE I 656 MB RISOLVE IL TERZO PIÙ PICCOLO DEL PROBLEMA.**
              Il peso vero è `torch` (4,4 GB su disco, obbligatorio) e
              l'embedder (1,1 GB). Il giudice è il pezzo che si può già evitare.

    COMANDI (ognuno riproduce una riga):
      python -c "import urllib.request as u; r=u.Request('https://github.com/aureliocpr-ctrl/verimem/releases/download/gate-ce-v2/verimem-gate-ce-v2.tar.gz',method='HEAD'); print(u.urlopen(r).headers['Content-Length'])"
      du -sh ~/.engram/models/local_gate_ce_v2
      python -c "import importlib.util,pathlib;d=pathlib.Path(importlib.util.find_spec('torch').origin).parent;print(sum(f.stat().st_size for f in d.rglob('*') if f.is_file())/1e6)"
      python -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['dependencies'])"

---

## 1. 🔴 Prima di scegliere una strada: il 656 non è il problema

Un utente che vuole verimem **funzionante** scarica in **tre fasi distinte**:

| fase | cosa | quanto | quando | si può evitare? |
|---|---|---|---|---|
| ① | `pip install verimem` → `torch`, `transformers`, `scipy`… | **torch: 116,4 MB** (wheel Windows) · **502,2 MB** (Linux) | al comando | **NO** |
| ② | embedder `multilingual-e5-base` | **1.112.201.288 byte = 1,1 GB** | primo uso | **NO** — serve a ogni scrittura e lettura |
| ③ | giudice `local_gate_ce_v2` | **655.928.064 byte scaricati → 738 MB estratti** | `verimem warmup` | **SÌ**, e già oggi |

### 🪞 CORREZIONE (2026-08-09 sera, misura di ws8) — avevo scritto 4,4 GB
La prima versione di questa tabella diceva «**torch: 4.428,6 MB su disco,
obbligatorio**» e ne traeva la conclusione che il giudice fosse un problema
marginale. **È sbagliato, e l'errore è mio.**
I 4,4 GB sono il torch **di questa macchina di sviluppo**:
`torch-2.12.0.dev20260405+cu128` — una **nightly con CUDA 12.8** che arriva da
`download.pytorch.org`, **non da PyPI**. Chi fa `pip install verimem` riceve il
wheel pubblico: **122.057.313 byte = 116,4 MB** su Windows, 502,2 MB su Linux
(misurato da ws8 sull'API di PyPI).
⇒ **Ho misurato l'ambiente di sviluppo credendo di misurare il prodotto** — la
stessa forma per cui ieri sette istanze hanno misurato il repo invece del
pacchetto. Due volte in tre giorni, e la regola che ne esce è più stretta di
quella che avevo scritto: non basta dire *quale prodotto*, bisogna dire *quale
artefatto*, perché anche una dipendenza può essere installata da una sorgente
diversa da quella che riceve l'utente.

⇒ **CONCLUSIONE RIBALTATA**: il pezzo più grosso **non è torch, è l'EMBEDDER**
(1,1 GB), e il giudice (656 MB) è il **secondo**. Su Windows, torch è un decimo
dell'embedder.
⇒ Il giudice resta **l'unico già evitabile** dei tre, ma non è più «il terzo più
piccolo di un problema dominato da torch»: è **il secondo peso, e il primo su
cui si può agire**.

📌 **Il numero «656 MB» è ESATTO** e viene dal commento in `cli.py:389`. L'avevo
sospettato sbagliato perché il file su disco pesa 738 MB: **non è una
contraddizione**, il download è un `.tar.gz` (656 compresso → 738 estratto).
Verificato con una richiesta HTTP HEAD: `Content-Length = 655.928.064`.

---

## 2. Le quattro strade, una per una

### ① Il giudice DENTRO il wheel — 🔴 **STRADA MORTA, chiusa da un numero**
Il wheel oggi pesa **1,66 MB**; con il modello dentro andrebbe a **~740 MB**.
* 🔴 **Il limite di PyPI è ESATTAMENTE 100,0 MB per file** (10,0 GB per
  progetto) — documentazione ufficiale, verificato da ws8. **740 MB è 7,4 volte
  il limite: l'upload viene rifiutato.**
* Esiste una procedura per chiedere un aumento, ma è **la decisione di un
  terzo con tempi non nostri**: non è una strada che possiamo scegliere, è una
  che possiamo chiedere.
* ⇒ **Toglietela dall'elenco. Restano tre.**
* (Reggeva comunque poco: non riduce niente — sposta i byte da GitHub a PyPI —
  e toglie la scelta a chi il moat non lo vuole.)

### ② Al primo uso, DICHIARATO PRIMA
**È già così, e va detto perché cambia il lavoro da fare.** `verimem warmup`
(`cli.py:388-412`) annuncia *prima* di scaricare — «*Fetching the local gate
model (the moat's judge-less judge)…*» — e se fallisce **lo dice invece di
fingere**, riusando la stessa frase del `doctor` (`AVVISO_SENZA_GIUDICE`) con
un commento che spiega perché non è riscritta a mano: due copie divergono.
* ✅ **Fatto**: l'annuncio, l'esito onesto, il degrado dichiarato.
* 🔴 **Il buco**: vale solo per chi lancia `warmup`. Chi installa e scrive
  subito ottiene fatti `model_claim` non giudicati **senza che nessuno glielo
  dica al momento della scrittura** — lo scopre solo aprendo `verimem doctor`.
* ⇒ **Il lavoro residuo non è scaricare prima: è dirlo alla PRIMA SCRITTURA.**

### ③ Un giudice PICCOLO di default
* ⚠️ **NON MISURATO**: non ho un modello alternativo né un banco di qualità, e
  senza quelli qualunque numero sarebbe inventato.
* 📊 **Ma ho un'evidenza a favore, misurata ieri** sui 2514 fatti giudicati del
  corpus: la distribuzione dei voti è **fortemente bimodale** — 82,74% sopra 99,
  8,29% sotto 10, e solo **1,15%** nella fascia 40-70 dove la soglia decide.
  ⇒ **Su questo corpus la discriminazione è un compito facile**, e un modello
  più piccolo potrebbe bastare. **È un'ipotesi, non un verdetto.**
* 👉 **Cosa la deciderebbe**: prendere i 2514 fatti già giudicati come banco,
  far girare un CE più piccolo, e confrontare i verdetti — non la media, ma
  **quanti fatti cambiano lato**. Mezza giornata, e il banco esiste già.

### ④ `verimem[full]` + un base che DICE cosa gli manca
* ✅ **Gli extra ESISTONO GIÀ**: ne sono dichiarati **undici** in
  `pyproject.toml` — `audit`, `headless`, `mcp-only`, `server`, `byok`, `ann`,
  `documents`, `tui`, `vision`, `full`, `dev`. E il `doctor` già dichiara lo
  stato del giudice.
* 🔴 **MA NON RIDUCE IL DOWNLOAD, e questa è la misura che conta**:
  `sentence-transformers>=2.7.0` sta nelle dipendenze **OBBLIGATORIE**, e
  richiede `torch>=1.11.0` (verificato con `importlib.metadata.requires`).
  **Quindi anche un'installazione «base» tira torch: 4,4 GB su disco.**
* ⇒ Per far funzionare questa strada bisognerebbe spostare
  `sentence-transformers` in un extra — **ma allora il base non sa più
  calcolare i vettori, cioè non è più una memoria.** Non è un dettaglio di
  packaging: è la domanda «cosa è verimem senza embedding».

---

## 3. Quello che direi io, se decidessi (non decido)

1. **La strada ② completata** è l'unica che costa poco e migliora il caso reale:
   dire alla **prima scrittura** che il moat non è installato, non solo in
   `warmup` e in `doctor`. Chi installa e prova NON passa da lì.
2. **La ③ vale la misura**, e il banco c'è già: 2514 verdetti su cui confrontare
   un modello più piccolo. Se regge, taglia 656 MB **per davvero**.
3. **La ① è MORTA** (limite PyPI) e **la ④ non riduce niente** finché
   `sentence-transformers` è obbligatoria.
4. ⚠️ **E il mandato va letto sul peso vero, che dopo la correzione è un
   altro**: «funzionante senza scaricare altro» oggi vuol dire **~1,9 GB su
   Windows** — embedder **1,1 GB**, giudice **656 MB**, torch **116 MB**.
   ⇒ **Il fronte non è torch: è l'embedder**, che è il pezzo più grosso e
   l'unico dei tre che nessuna delle strade proposte tocca. Se un giorno si
   vuole un primo avvio davvero leggero, la domanda è **«serve
   `multilingual-e5-base` o basta un embedder più piccolo?»** — la stessa
   domanda della strada ③, su un modello diverso e più pesante.

---

## 4. Cosa NON ho verificato — dichiarato

* ✅ ~~Il **limite per file di PyPI**~~ → **CHIUSO da ws8**: 100,0 MB. Strada ① morta.
* ✅ ~~Se `torch` scaricato da PyPI sia più piccolo dei 4,4 GB su disco~~ →
  **CHIUSO da ws8**: 116,4 MB su Windows, 502,2 MB su Linux. E la ragione dello
  scarto ha ribaltato la mia conclusione (vedi §1).
* ❌ La **qualità di un giudice più piccolo** (strada ③): ho l'evidenza indiretta
  della bimodalità, non una misura diretta. **Resta aperto.**
* ❌ **Il tempo** di ognuna delle tre fasi su una macchina pulita: i 594 secondi e
  il 1,01 GB sono **misura di ws2**, non mia. **Resta aperto.**
* ❌ **NUOVO, ed esce dalla correzione**: se un embedder più piccolo basti. È il
  pezzo più grosso dei tre e nessuno l'ha ancora guardato.
