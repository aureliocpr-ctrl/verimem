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
| ① | `pip install verimem` → `torch`, `transformers`, `scipy`… | **torch: 4.428,6 MB su disco** (~1 GB scaricato, misura di ws2) | al comando | **NO** |
| ② | embedder `multilingual-e5-base` | **1.112.201.288 byte = 1,1 GB** | primo uso | **NO** — serve a ogni scrittura e lettura |
| ③ | giudice `local_gate_ce_v2` | **655.928.064 byte scaricati → 738 MB estratti** | `verimem warmup` | **SÌ**, e già oggi |

⇒ **Il giudice è il più piccolo dei tre, ed è l'unico già evitabile.** Gli altri
due arrivano comunque, e nessuna delle quattro strade li tocca.

📌 **Il numero «656 MB» è ESATTO** e viene dal commento in `cli.py:389`. L'avevo
sospettato sbagliato perché il file su disco pesa 738 MB: **non è una
contraddizione**, il download è un `.tar.gz` (656 compresso → 738 estratto).
Verificato con una richiesta HTTP HEAD: `Content-Length = 655.928.064`.

---

## 2. Le quattro strade, una per una

### ① Il giudice DENTRO il wheel
Il wheel oggi pesa **1,66 MB**; con il modello dentro andrebbe a **~740 MB**.
* **Non riduce niente**: il totale resta 2,8 GB, si sposta solo da GitHub a PyPI.
* **Toglie una scelta**: oggi chi non vuole il moat non lo scarica; dentro il
  wheel lo scarica sempre.
* ⚠️ **NON VERIFICATO**: il limite per singolo file di PyPI. So che esiste ed è
  dell'ordine dei 100 MB, ma **non l'ho misurato** e non lo dichiaro come fatto.
  Se il limite è quello, questa strada è chiusa in partenza.
* **Costo/beneficio misurato**: peggiora il caso «voglio solo provarlo».

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
3. **La ① e la ④ non risolvono il mandato**: la prima sposta i byte, la seconda
   non li tocca finché `sentence-transformers` è obbligatoria.
4. ⚠️ **E il mandato andrebbe riformulato su ciò che pesa**: «funzionante senza
   scaricare altro» oggi vuol dire **2,8 GB**, di cui il giudice è 656 MB. Se
   l'obiettivo è un primo avvio leggero, il fronte è `torch` + l'embedder, e
   nessuna delle quattro strade lo affronta.

---

## 4. Cosa NON ho verificato — dichiarato

* Il **limite per file di PyPI** (strada ①).
* La **qualità di un giudice più piccolo** (strada ③): ho l'evidenza indiretta
  della bimodalità, non una misura diretta.
* **Il tempo** di ognuna delle tre fasi su una macchina pulita: i 594 secondi e
  il 1,01 GB della fase ① sono **misura di ws2**, non mia.
* Se `torch` scaricato da PyPI sia più piccolo dei 4,4 GB che occupa su disco:
  quasi certamente sì (wheel compresso), **ma non l'ho misurato**.
