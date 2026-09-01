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
| `reproduce.sh` | ✅ scritto, **step 1 e 2 provati**; step 3-4 no (costano 70 min) |
| `Dockerfile` | ⚠️ **scritto ma mai costruito né eseguito** |
| lock delle dipendenze | ⚠️ **assente**: vedi «il lock che non c'è» |
| seeds | ✅ **non servono**, e non è una scorciatoia: vedi sotto |

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
**cross-encoder locale**, `local_gate_ce_v2`, **~746 MB** (`model.safetensors`
737,7 + `tokenizer.json` 8,3), che `verimem warmup` scarica.

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
