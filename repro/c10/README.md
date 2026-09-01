# REPRO-PACK v1 — C10, «che tasso di falsità serviamo»

**A cosa serve**: rendere i numeri del C10 verificabili **da terzi**, non solo
citabili. `reproduce.sh` non stampa numeri da interpretare: **confronta il run
nuovo con l'artefatto versionato e dice PASS o FAIL**.

```bash
bash repro/c10/reproduce.sh          # ~70 min, esce 0 solo se riproduce
OUT=/tmp/x.json TOLL=0.5 bash repro/c10/reproduce.sh    # tolleranza più stretta
```

| pezzo | stato |
|---|---|
| `MANIFEST.sha256` | ✅ **hash reali, calcolati e verificati** (3/3 OK) |
| `reproduce.sh` — sintassi | ✅ `bash -n` passa e **tutti e 3 i blocchi Python compilano** (02/09 01:29) |
| `reproduce.sh` — esecuzione | ✅ step **0, 1, 2 provati**; step 3-4 no (costano 70 min) |
| `Dockerfile` | ⚠️ **scritto ma mai costruito né eseguito** |
| `requirements.lock` | ✅ generato da `genera_lock.py`, che legge il codice **eseguito** e non i metadati |
| seeds | ✅ **non servono**, e non è una scorciatoia: vedi sotto |

⚠️ **`bash -n` dice che lo script PUÒ girare, non che FUNZIONI**: è il controllo
minimo che separa «scritto» da «eseguibile», e prima del 02/09 non era stato
fatto — un pack con un errore di sintassi sarebbe stato inutile senza che
nessuno lo sapesse, perché il primo a scoprirlo sarebbe stato chi prova a
riprodurre, cioè esattamente la persona che non deve inciampare.

---

## Perché i «seeds» della spec non ci sono

Il banco **non importa `random`** — verificato leggendo gli import — e con
`--n 300` prende la **popolazione heldout intera** (300 veri + 300 falsi):
nessun campionamento, quindi **niente da seminare**.

⚠️ **Vale solo per `--n 300`.** Con `--n 100` il banco sceglie 100 su 300, e lì
la domanda del seed torna: **non l'ho verificata**, perché i numeri pubblicati
sono quelli a 300.

## Il lock che non c'è, e cosa ci vuole al suo posto

Il banco è std-lib puro; l'unica dipendenza è **`verimem`**, che a sua volta
carica `torch`/`transformers` pigramente per il giudice. Un `pip freeze`
dell'ambiente in cui i numeri sono nati **non l'ho prodotto** — sarebbe stato
un file plausibile e non verificato.

⇒ Nel Dockerfile la versione è **pinnata a `verimem==0.7.6`**, che è la
versione da cui i numeri provengono (`pyproject.toml`, invariata dal 21/08).
**Un lock vero va aggiunto**: è il debito più concreto di questo pack.

## 🔴 Il pezzo che decide se un terzo può riprodurre: il giudice

Il moat non usa un modello scaricato per nome da HuggingFace: usa un
**cross-encoder locale**, `local_gate_ce_v2`, che `verimem warmup` scarica.

⚠️ **Correzione del 02/09 00:36, contro quello che avevo scritto io.** Avevo
messo «~746 MB» come se fosse il costo del warmup: **è solo il gate**.
`verimem warmup --help` lo dichiara — *«WITH NO OPTIONS THIS TAKES THREE
MODELS, not one»* — e la tabella in `verimem/cli.py` (misurata 19/08) dà
embedder **1082**, gate **746**, reranker stage-2 **470** ⇒ **il default sfiora
i 2,3 GB, tre volte quello che avevo scritto.**

🔑 **E il numero non lo ricablo qui**: il codice porta già la lezione che ho
appena ripetuto — *«un numero cablato in una frase invecchia da solo: il 21/08
la descrizione diceva ~1.1 GB, il solo embedder, mentre il comando ne prendeva
TRE»*. ⇒ **chi vuole il totale lo legge da `_WARMUP_DI_DEFAULT` in `cli.py`,
oppure lo fa stampare al comando** (l'help dice che il totale esce prima che
qualcosa venga scaricato). ⚠️ **E quel totale somma due metodi di misura
diversi**: i due modelli HF sono download cronometrati su cache vuota, il gate
è la **cartella su disco** — lo dichiara `cli.py` e lo ripeto qui perché chi
rifà il conto deve saperlo.

⇒ Per il solo C10 **basterebbe il gate**: `--no-gate` lo salta (e non è quello
che vogliamo), ma l'embedder e il reranker il banco non li esercita. Non ho
verificato se `warmup` permetta di prendere **solo** il gate: se serve
risparmiare 1,5 GB in CI, è la prima cosa da guardare.

**Senza quel modello il gate parte in stato `warming` e AMMETTE TUTTO**: si
ottengono `0/300` veri fermati e `0/300` falsi fermati in 26 secondi — numeri
puliti e **privi di qualsiasi significato** (registro `W7-87`, scoperto
sbattendoci contro). ⇒ `reproduce.sh` **si ferma allo step 2** invece di
produrli.

🪞 **E qui il controllo ha morso il suo autore.** La prima versione dello step 2
guardava `DEFAULT_MODEL_DIR` (`~/.cache/verimem/models/…`) e stampava
**ASSENTE** su questa macchina — dove il gate funziona benissimo, perché il
modello sta nel percorso **legacy** (`~/.engram/models/…`) e il codice ha un
fallback. ⇒ Il pack avrebbe detto «manca il modello» **proprio a chi ce l'ha**.
Curato usando `_resolve_model_dir(None)`, che applica env → default → legacy.
**Prima: ASSENTE. Dopo: presente.**

## Cosa NON ho fatto, e chi deve

- ⚠️ **Il Dockerfile non è stato costruito né eseguito.** Il flag di `verimem
  warmup` per scaricare il modello del moat **va confermato** con
  `verimem warmup --help`: ho lasciato una riga da correggere invece di
  inventarne una che sembra giusta.
- ⚠️ **Non ho rieseguito il C10**: 70 minuti e ~758 MB di RAM per processo,
  con otto istanze sulla stessa macchina.
- ⚠️ **Non ho la spec originale.** L'ordine diceva «sulla spec di Luna»:
  «Luna» è la versione di GPT con cui Aurelio ha chattato (`gpt 5.6 luna`,
  che lui stesso circoscrive come «versione free, paragonabile ad haiku»), e
  **quel resoconto non è nel repo né sul canale**. Ho costruito sui cinque
  componenti elencati da @lead-audit — Dockerfile, lock, seeds, hashes,
  `reproduce.sh` con output automatico — **non sulla spec**, che non ho letto.

## Come si verifica che questo pack non menta

```bash
sha256sum -c repro/c10/MANIFEST.sha256    # gli ingressi sono quelli dichiarati
```

Se qualcuno cambia il banco, il dataset o l'artefatto atteso, **il MANIFEST
fallisce e `reproduce.sh` si ferma al primo passo**. I valori attesi non sono
scritti nello script: si leggono dall'artefatto, che è sotto hash — quindi
**non si può ritoccare il numero atteso senza che il pack se ne accorga**.
