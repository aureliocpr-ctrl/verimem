# Le lezioni del ramo di rilascio — 01-02/09, dal treno `0.7.1`

> Cinque forme trovate **misurando**, non ragionando, nella notte in cui `0.7.1` è rimasta
> in coda. Ognuna ha la sua cella nel registro (`00-ESAME.md`) e il comando che la rifà.
> Stanno qui perché le celle sono **cronologiche**: queste sono **tematiche**, e servono la
> prossima volta che si tagga qualcosa.

---

## ① Un hotfix eredita la documentazione e i presidi del suo tag

**È la causa unica di quattro difetti diversi**, e non era scritta da nessuna parte.

`hotfix/0.7.1` riparte da `v0.7.0` (22 luglio). Ne consegue, **tutto misurato**:

| eredità | misura | cella |
|---|---|---|
| il README | **4 avvisi contro 16** di `main`, e 8 numeri pubblicizzati | `W8-50` |
| i presidi | **611 file di test più ricchi** su `main`, **553 assenti** dal branch | `W8-53` |
| le note correttive | quella sul banco mancante è del **28/08** ⇒ **non c'è** | `W8-52` |
| i test del rilascio | `test_il_pacchetto_ha_cio_che_promettiamo` **assente** (0 righe vs 711) | `W8-53` |
| **il comportamento** | **la porta MCP non fa passare dal giudice una fonte data**: `ground_write` in `mcp_server.py` conta **0** a `1e293f4b` e **7** su `main` | `W8-60` |

⚠️ **La riga in grassetto è arrivata dopo, e ha corretto questa stessa sezione.** Per un
giorno e mezzo ho scritto — in `W8-54`, in `W8-56` e qui — che il ramo eredita
«documentazione e presidi», e ne ho concluso che **nulla era bloccante**. L'ultima riga
dice che eredita anche **il comportamento**: la cura `7b8af116` del **29 luglio**
(*«feat(mcp): a source given to the MCP channel is now actually checked»*) non è antenata
di `1e293f4b`, perché il tag `v0.7.0` è del **22 luglio**. ⇒ **La forma era giusta e il
suo perimetro no**, e l'ho ristretto proprio dove costava di più: avevo cercato l'eredità
solo fra i testi, che è dove sapevo già di trovarla. Trovata da @ws2 (`W2-391`),
controfirmata 3/3 da me.

🔑 **Non è un difetto del processo: è una proprietà.** Un ramo di hotfix *deve* riprendere
dal codice in produzione — è ciò che lo rende un hotfix. **Ma va dichiarato**, perché ogni
criterio di rilascio (`G1` «full suite», `G6` «README audit») **cambia di significato** su
quel ramo: «full suite» lì vuol dire **1050 file di test contro 1598**.

    rifallo con:
    for R in <branch> main; do git show "origin/$R:README.md" | grep -ciE '⚠|measured on'; done
    git diff --numstat origin/<branch> origin/main -- tests/ | awk '$1>$2' | wc -l
    # e la riga che mi mancava — l'eredita' del COMPORTAMENTO (eseguita, non proposta):
    git log --format='%H %s' <head-del-ramo>..origin/main -- verimem/ | grep -E ' (feat|fix)\(' | wc -l
    git merge-base --is-ancestor <cura-nota> <head-del-ramo>; echo "EXIT=$?"

🔑 **Il comando che chiude la forma è il terzo, e per un giorno e mezzo non l'ho scritto.**
I primi due contano *testi*; solo l'ultimo chiede **quali cure del prodotto sono nate dopo
il tag**. ⇒ Su un ramo di hotfix, la domanda da fare per prima non è «che cosa dice di
diverso», è **«che cosa ha imparato `main` da allora, e quanto di quello viaggia qui»**.

Eseguito su `1e293f4b` il 02/09 alle 05:10 — **659** commit toccano `verimem/` e non sono nel
treno, **89** sono `feat(`/`fix(`, **84** toccano un file che a `1e293f4b` esiste già (limite
superiore: il filtro esclude solo 5 su 89, quindi **non restringe**). Controllo negativo: senza
il filtro di percorso sono **3401**, quindi il criterio decide qualcosa. Controllo positivo: la
cura nota `7b8af116` **è** fra i candidati — un criterio che non ritrova il caso che l'ha
generato non serve a niente.

⚠️ **Due errori miei in questa riga sola**, perché valgono più del numero: ① la prima versione
usava `--oneline`, che **abbrevia lo SHA**, e il regex ancorato perdeva una riga — davo **88**
invece di **89**; ② avevo scritto qui la ricetta con `v<tag>..origin/main` mentre **avevo
eseguito** `<head-del-ramo>..origin/main`: la **forma ⑤ di questo stesso documento**
(«eseguito a mano» non è «installato»), addosso a chi l'ha scritta. La riga sopra è ora
quella che ho davvero eseguito.

---

## ② Una cura viaggia col codice, il suo presidio no

`0.7.1` porta il pin `mcp<2` — verificato nel `METADATA` del wheel, **su tutti e tre i rami**
(base, `mcp-only`, `full`). **Ma non porta `test_le_dipendenze_che_pubblichiamo_hanno_un_tetto_dove_serve`**,
che è il test **nato da questo stesso incidente**. Il suo docstring su `main` dice:

    """Una dipendenza senza tetto pubblica un prodotto che si romperà da solo.
    Il caso vero, e non è ipotetico: `verimem 0.7.0` su PyPI chiede `mcp>=1.0.0` senza
    limite superiore..."""

⇒ **Se domani il tetto sparisse dal branch, nessun test lo fermerebbe**, e il prossimo
hotfix ripartirebbe da lì con la stessa dinamica.
🔑 **Quando si porta una cura su un ramo vecchio, si porta anche il test che la protegge** —
altrimenti si ripara una volta sola. **Costa un file, e non tocca il prodotto.**

---

## ③ Un numero vero, letto al livello sbagliato

**Vista tre volte in una notte**, ogni volta con un verdetto diverso a seconda del livello:

| numero | livello sbagliato | livello giusto |
|---|---|---|
| `in_progress` | **al RUN**: dice `5` | **ai JOB**: uno dei cinque ha tutti i job conclusi ⇒ sono `4` |
| il pin delle dipendenze | **`pyproject.toml`**: ciò che dichiariamo | **`METADATA` del wheel**: ciò che `pip` legge |
| il veto sul registro | **wheel che costruisco io** | **artefatto `dist` della CI**, quello che va su PyPI |

🔑 **Nessuno di questi numeri era falso.** Erano tutti veri **al loro livello**, e tutti
fuorvianti a quello che serviva. ⇒ **Prima di usare un numero, chiedersi a quale livello è
misurato e a quale serve.** Se non coincidono, il numero non risponde alla domanda.

---

## ④ Il run è pulito perché nessuno guarda

`#2557` sul branch ha dato **`1 failed, 7686 passed`** — sembrava dire «tutto a posto tranne
la versione». **Non era vero**: il numero di copertina del README (`recall@5 = 0.87`) punta a
un banco **che non esiste**, e nessun test l'ha rilevato perché sul branch
`test_repro_registry_g4.py` è la versione del 22 luglio — **21 righe contro 33** — e
**controlla la FORMA delle voci del registro, non l'esistenza di ciò che nominano.**

🔑 **Un verde garantisce quanto i presidi che quel ramo CONTIENE**, non quanti ne abbiamo
scritti da allora. ⇒ Prima di leggere un run come rassicurazione, **contare i presidi di quel
ramo**, non quelli del repo.

---

## ⑤ «Eseguito a mano» non è «installato nel workflow»

Due casi, a poche ore di distanza:

- **Il veto sul branch** (`W8-35`): il `publish.yml` del ramo era quello del **4 luglio** —
  45 righe contro 294, **zero** occorrenze di `controlla_registro`. Il veto era stato
  *eseguito a mano* sul wheel, e funzionava; **ma il workflow del ramo non lo conteneva.**
- **Il `CHANGELOG`** (`W8-49`): «*verified by an install-from-scratch smoke (resolves `mcp`
  1.29.1, `Server.list_tools` present)*». Il job CI verifica **`MCP stdout protocol-pure`**;
  quelle due stringhe **non sono nel log**. La prova esiste — **fatta a mano** — ma il
  documento la attribuisce all'automatismo.

🔑 **Le due frasi non sono equivalenti**: la prima vale una volta, la seconda vale ogni volta.
**Quando si scrive «verificato», dire da chi e da cosa** — chi va a cercarlo nel log deve
trovarcelo.

---

## 🪞 E una che riguarda chi misura, non ciò che è misurato

Delle sette correzioni che ho dovuto pubblicare quella notte, **tutte e sette erano nel
misuratore**, non nel prodotto: un fuso confuso, un regex che tagliava le cifre, un grep che
leggeva 6 nomi su 39, una finestra scambiata per un regime, un conteggio di superfici
sbagliato di uno.

🔑 **La regola che ne è uscita**: *un limite dichiarato non è una postilla — è la lista dei
comandi da eseguire*, **e va eseguita prima di alzare la voce, non dopo**. Due volte quella
lista conteneva la falsificazione della mia stessa tesi.
