# Il daemon del giudice — disegno per la 0.8.0

*ws5 «TARA», 02/09/2026. Scritto durante il fermo termico: **nessuna misura nuova**, solo
i numeri già presi fra le 12:36 e le 21:09 e i banchi che li producono.*

---

## Perché esiste

Il giudice costa **957,9 MB di RSS / 1552,8 di privata per processo**, e il costo è
**tutto nel caricamento**: 16-54 s a freddo contro 0,18-0,47 s a caldo, con la memoria che
**non cresce** coi giudizi (`c8830190`). ⇒ Otto agenti che caricano ciascuno il proprio
giudice pagano otto volte una spesa che è la stessa.

Le altre tre strade, misurate prima di scegliere questa:

| strada | esito | banco |
|---|---|---|
| T4.4 cache del verdetto | **falsificata**: ripetizioni bit-identiche 1,2%, non ≥15% | `0e23ed07` |
| T4.2 ONNX int8 | **bersaglio irraggiungibile**: il pavimento è torch, 784,9 MB di privata al solo import | `6ec9a2bf` |
| T4.1 daemon a 2 client | **−9%**: sembrava poco, ma era la concorrenza sbagliata per la domanda | `e0df50c8` |
| T4.1 daemon a **8** client | **−67% RSS**, −27% privata | `481a2eb3` |

---

## Il disegno

```
trasporto    socket TCP su 127.0.0.1, porta EFFIMERA annunciata in un file di discovery
protocollo   una riga JSON per richiesta, una per risposta, terminate da \n
             {"claim": ..., "fonte": ...}  ->  {"g": <punteggio> | null}
avvio        il primo client che non trova il daemon lo spawna e attende il discovery;
             gli altri si connettono e basta
pool         2 worker (semaforo sullo stesso scorer) — NON 4  ⚠️ UNA SOLA ESECUZIONE,
             in verifica con la predizione P1 (ws5-P1-predizione-pool-ripetibile.md)
daemon giù   fallback in-process + DICHIARAZIONE in ricevuta, mai silenzioso
```

### Porta effimera, non fissa

Due checkout sulla stessa macchina — due utenti, due worktree — con una porta fissa si
prenderebbero a calci. Il file di discovery è la stessa forma che il prodotto già usa per
il daemon di encode (`encode_service.json`).

⚠️ **E lì c'è una trappola già misurata** (`fdd6df83`): `DISCOVERY_PATH` è **hardcoded**
sotto `Path.home()` e **non deriva da `HIPPO_DATA_DIR`**. Un venv «vergine» con la HOME
vera parla comunque col daemon dello stack principale. ⇒ Il discovery del giudice deve
stare sotto la **data dir**, o si ripete lo stesso equivoco.

### Pool: 2 worker, e il perché

| worker | p50 | p95 | giudizi/s | RSS del daemon |
|---|---|---|---|---|
| 1 | 1,546 s | 2,664 s | 4,7 | 1901,7 MB |
| **2** | **0,929 s** | **1,404 s** | **7,4** | **1910,7 MB** |
| 4 | 1,011 s | 1,809 s | 6,8 | 1920,8 MB |

Due worker **dimezzano il p95** (−47%) e alzano il throughput del **57%**, a costo di
**+9 MB**. Quattro **peggiorano**: i core finiscono, il pool non moltiplica la CPU
(`d4c23855`).

Il pool è **A** — un semaforo sullo stesso scorer, una sola copia del modello. Il pool
**B** (N istanze del giudice) costerebbe **~640 MB di modello per worker**, e a quel punto
il conto della memoria — che è il motivo per cui il daemon esiste — andrebbe rifatto.

⚠️ **Il bersaglio «p95 < 1 s» non è un criterio stabile su questa macchina**: la stessa
configurazione a 1 worker ha dato **1,388 s** alle 20:44 e **2,664 s** alle 21:07, una
**varianza del 92%**. Il rapporto fra configurazioni nella stessa esecuzione è solido; il
valore assoluto no. Prima di pagare il prezzo del pool B, il bersaglio va rimisurato a
macchina scarica.

### Daemon giù — il ramo che conta più di tutti

Il client **non deve fallire la scrittura**: ricade sul giudizio in-process **e lo
dichiara nella ricevuta**.

Un fallback silenzioso trasformerebbe «il daemon non risponde» in «il fatto è stato
giudicato», che è esattamente la bugia che questo prodotto esiste per non dire. È la
stessa forma del difetto che ho misurato da utente stamattina: `remember` stampava
`admitted` con EXIT 0 mentre il moat era spento, e solo `doctor` lo sapeva.

✅ **PROVATO il 02/09 alle 22:16** — questa riga diceva «MAI STATO PROVATO» e lo ha
detto per 21 ore *dopo* che la misura era stata fatta: il banco che la smentisce
(`ws5-il-fallback-quando-il-daemon-cade.py`, commit `796de341`) era rimasto su un ramo e
non è mai arrivato su main. Chi leggeva main vedeva un debito che non c'era più. Il banco
è qui accanto adesso, e l'esito è questo:

| | durata | via | grounding | esito |
|---|---|---|---|---|
| 1-4 | 0,158-0,160 s | daemon | 0,53 / 99,24 / 0,53 / 99,67 | 2 fermate, 2 ammesse |
| | | ⚡ **daemon ucciso** | | |
| 5 | **16,195 s** | in-process | 0,53 | fermata |
| 6-8 | 2,192-2,283 s | in-process | 99,24 / 0,53 / 99,67 | corrette |

**Il fallback funziona e GIUDICA**: zero scritture perse, il claim falso resta fermato
anche in-process, e la ricevuta porta `via` = daemon | in-process, così «ha funzionato»
non confonde chi ha giudicato.

⚠️ **Ma il daemon che cade non degrada dolcemente**: la prima richiesta dopo la caduta
passa da **0,159 s a 16,195 s** — cento volte — perché quel client paga il caricamento
del modello. E ogni client che ricade ne carica **una copia propria**, cioè torna il costo
di memoria che il daemon esisteva per togliere.

⇒ **Il disegno ha bisogno di una riga che non ho ancora scritto**: cosa fare quando il
daemon cade sotto carico — riavviarlo dal primo client che se ne accorge, accettare N
copie, o rifiutare. L'unica opzione esclusa è la scrittura che fallisce.

---

## Cosa il daemon cura, oltre alla memoria

@ws3 ha misurato che sulla porta MCP il warmup del giudice **completa 5 volte su 694 in
cinque giorni**: l'import pigro di `transformers` dentro il thread manda in timeout la
prima scrittura. È lo stesso fenomeno dei miei `W5-31`…`W5-34` — la prima scrittura MCP
con fonte che non torna entro 90 s, per l'import di `scipy` sullo stesso frame.

⇒ **Un daemon che carica una volta sola è anche la cura di quello.** Non è ancora
misurato (serve: prima scrittura MCP con daemon già caldo, tempo e `layers`), ed è il
secondo lavoro dopo il fallback.

---

## Il conto per otto agenti

| | oggi | con daemon + 8 client |
|---|---|---|
| RSS | 7844,8 MB | **2592,8 MB** (−67%) |
| privata | 12422,4 MB | **9051,8 MB** (−27%) |

⚠️ L'aritmetica che avevo mandato prima di eseguire diceva **−80%**; la misura dice
**−67%**. Il daemon **cresce con la concorrenza** (1900 MB con 8 thread contro 861,8 da
scarico) e nella predizione avevo usato il numero del daemon **scarico**, avendo già
quello a 2 client. ⇒ Un'estrapolazione dichiarata resta un'estrapolazione: eseguirla l'ha
corretta di 13 punti.

---

## Limiti di tutto quanto sopra

Una macchina sola, e carica. Il daemon è un prototipo di misura: nessuna autenticazione,
nessuna back-pressure, nessun ciclo di vita. Ottanta giudizi non sono un carico di
produzione, e otto client su una macchina non sono otto agenti veri — che farebbero anche
altro. E il `~4×` di int8 citato per T4.2 è **letteratura, non una mia misura**: se il
modello fosse già in fp16 il quadro sarebbe **peggiore**, non migliore.
