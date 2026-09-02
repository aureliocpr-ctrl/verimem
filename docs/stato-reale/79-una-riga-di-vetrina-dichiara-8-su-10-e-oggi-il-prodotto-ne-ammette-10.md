# Una riga di vetrina dichiara `8/10` e oggi il prodotto ne ammette `10/10`

**02/09/2026, 04:09 · ws6/Aldo · A/B fra il prodotto del 26/08 e quello di oggi**

La vetrina ha quattro righe che dichiarano quanto il gate **lascia passare** su
altrettante classi di falsità. Nessuno le aveva **rieseguite**: @ws3 aveva
scritto, correttamente, *«ho letto, non ho eseguito»*, e aveva aggiunto un
argomento giusto — *un numero diverso oggi non distinguerebbe «il banco non
torna» da «il prodotto è cambiato»*.

**L'A/B che separa le due cause si può fare** (vedi in fondo), e questo è il suo
risultato.

## Tre righe su quattro reggono. La quarta no

Stesso identico file di banco, unica variabile il prodotto:

| riga di vetrina | dichiara | **prodotto di oggi** | esito |
|---|---|---|---|
| negazione | 0/10 IT · 0/10 EN | **0/10 · 0/10** | ✅ regge |
| entità scambiata | 1/10 IT · 2/10 EN | **1/10 · 2/10** | ✅ regge |
| contraddizione implicita | 3/10 IT · 0/10 EN | **3/10 · 0/10** | ✅ regge |
| **non menzionata** | **8/10 IT** · 9/10 EN | **10/10 IT** · 9/10 EN | ⚠️ **due in più** |

Per la riga che differisce, il terzo braccio attribuisce la causa:

```
                        IT      EN
dichiarato nel docstring        8/10    9/10
prodotto del 26/08, rieseguito  9/10    9/10     <- il banco e' lo STESSO file
prodotto di oggi               10/10    9/10
```

⚠️ **La differenza `9 → 10` è del prodotto**, ed è attribuita a un tipo preciso:

```
tipi che passano in IT, prodotto 26/08:  mezzo luogo causa autore modalita tempo destinatario        strumento esito
tipi che passano in IT, prodotto oggi:   mezzo luogo causa autore modalita tempo destinatario stato  strumento esito
```

⇒ **`stato` è la falsità che allora il gate fermava e oggi ammette.** Fra i due
commit ci sono **11 commit** su `verimem/anti_confab_gate.py`.

## Perché conta più di due punti percentuali

Questa riga di vetrina descrive **un limite dichiarato del prodotto**: dice
quante contraddizioni «non menzionate» il gate lascia passare. Se oggi ne passano
**dieci su dieci** e la vetrina ne dichiara **otto**, la vetrina **descrive il
prodotto come migliore di com'è**.

🔑 È la forma esatta che l'operazione concessionario deve impedire — *nessun
analista deve poter dire «afferma cose che non fa»* — con l'aggravante che qui
**il numero non è stato gonfiato da nessuno**: era vero quando fu scritto, e il
prodotto gli si è mosso sotto. **Un limite dichiarato invecchia come una
promessa**, e nessuno se ne accorge perché il documento non cambia.

## Cosa NON prova

⚠️ **La differenza `8 → 9` non è spiegata.** Il banco è **identico** nelle due
copie (`diff` pulito) e l'`8/10` è un risultato registrato nel docstring alla
riga 36. La mia ipotesi è che il docstring sia stato scritto contro un commit
**diverso** da quello che ho scelto — io ho preso l'ultimo commit prima del
27/08, che può essere **successivo** all'esecuzione originale. **Non l'ho
verificato**: si verifica rieseguendo su commit precedenti finché il numero non
torna 8, ed è mezz'ora.
⚠️ **Il risultato principale non dipende da quella ipotesi**: `9 → 10` confronta
due prodotti con **lo stesso banco nella stessa forma**, e il tipo che cambia è
nominato.
❌ **Non ho stabilito QUALE degli 11 commit abbia cambiato l'esito su `stato`**,
né se sia stato un effetto voluto di una cura o una regressione. Serve una
bisezione, che è il passo naturale successivo e non l'ho fatto.
⚠️ **Le tre righe che reggono sono verificate su un'esecuzione ciascuna**, non su
ripetizioni: se il banco avesse una variabilità come quella che l'`8 → 9`
suggerisce, un singolo passaggio non la vedrebbe.

## L'A/B «allora contro oggi» è praticabile — e la trappola che nasconde

`git worktree add --detach <tempdir> <commit>` ha un **indice proprio** e **non
tocca l'albero condiviso**: verificato, `3 file modificati, HEAD ee04f8f6`
identico prima e dopo. Costa **89 secondi a banco**.

⛔ **Ma `PYTHONPATH=<worktree>` NON basta**, e questo è il punto pericoloso:

```
senza PYTHONPATH               -> C:\Users\aurel\Code\HippoAgent\verimem
con PYTHONPATH sul worktree    -> C:\Users\aurel\Code\HippoAgent\verimem   <- !!
```

**L'import non fallisce**: il banco gira, stampa numeri, e sono del prodotto **di
oggi**. Un A/B fatto così misura **oggi contro oggi** e conclude «il banco è
stabile». Quello che funziona, isolato cambiando una cosa per volta, è
`sys.path.insert(0, <radice>)`; togliere i finder editable **non** serve, e il
perché `PYTHONPATH` perda **non l'ho stabilito**.

🔑 **Il lanciatore deve stampare la provenienza effettiva di `verimem` e fermarsi
se non viene dalla radice chiesta** — senza quel controllo positivo avrebbe lo
stesso difetto silenzioso che evita.

**Firme su questo documento**: ws6.
