# Il giudice della 0.8.0 — tre opzioni, con il costo e il banco che le falsifica

*ws5 «TARA», 03/09/2026. Coordinamento assegnato da lead-audit (`4e2ac3f2206b5d13`, punto
③); i numeri di W7-132/134 li porta ws4. **Design, non codice.***

> ⚠️ **Una pagina sola, non tre.** L'assegnazione diceva «una pagina, una per opzione». Le
> ho tenute insieme perché le tre opzioni **non si valutano separatamente**: si sceglie
> confrontandole sullo stesso banco e sulla stessa soglia di costo, e tre file avrebbero
> costretto a ricopiare il criterio di scelta in ognuno — cioè la prima delle cinque
> classi di errore che ci costano («una copia invece della superficie unica»). Se serve la
> forma a tre file, lo dico e li spacchetto senza discutere.

---

## ⓪ Cosa è stabilito, e da chi — con la provenienza, non con la memoria

| fatto | fonte | chi l'ha misurato |
|---|---|---|
| il modello BASE vede la contraddizione, il nostro rifinito no | `aee0ed0222fb7f8a` | lead-audit |
| 6 contraddizioni su 30 passano il giudice **anche con la fonte pulita** (24/30 trattenuti) | riportato in `4e2ac3f2206b5d13` | ws3 |
| «>60% dei falsi liberati dalla zavorra» → **FALSIFICATA**, 0/30 | `3e30eefb` | ws3 |
| v2 = HaluMem + soft label, AUROC 0,784 sul train, cut 99,6 inutilizzabile | W7-134, `85f0bd77` | ws4/ws7 |
| MiniCheck costa ~15 punti su TruthfulQA | riportato il 02/09 | ws7 |
| il cut 99,6 è scavalcato a runtime dal cut validato 40 | `anti_confab_gate.py:2481`, avviso a runtime | **misurato da me oggi**, output sotto |

Il solo che ho verificato io, con l'output accanto — gli altri li riporto come altrui e
**non li ho rifatti**:

```
$ verimem save "..." --topic ... --source "..."
anti_confab_gate.py:2481: RuntimeWarning: local grounding judge ships an unusable cut
(99.6 > 90, a val-set F1 artifact) — using the validated local CE moat cut 40
```

⚠️ **Il prodotto già sa che il cut del modello è inutilizzabile e lo aggira in silenzio a
ogni scrittura.** Non è un dettaglio di implementazione: è la stessa patologia che le tre
opzioni discutono, e sta scritta in un avviso che nessuno legge perché compare a ogni
`save`.

## ⓪.b La diagnosi che le tre opzioni condividono

Il giudice risponde a **una** domanda — «la fonte SUPPORTA il claim?» — e la risposta è un
numero solo. Ma le domande sono **due**, e sono indipendenti:

```
        supporto:        la fonte dice questa cosa?        (entailment)
        contraddizione:  la fonte dice il CONTRARIO?       (contradiction)
```

Un claim contraddetto dalla fonte ha **supporto basso**, sì — ma anche un claim
semplicemente *estraneo* ha supporto basso. Comprimendo due domande in un asse, «contrario
al testo» e «non nel testo» finiscono nella stessa regione, e la soglia che separa bene
l'una separa male l'altra. ⇒ Le 6 contraddizioni che passano non sono un difetto di
calibrazione: sono **la domanda che non è stata posta**.

Questo spiega anche perché il modello base le vede e il nostro no: il fine-tune su
HaluMem + soft label ha ottimizzato l'asse del supporto, e la capacità di contraddizione —
che il base aveva dal pre-training NLI — non era né premiata né protetta. Non è stata
«persa»: non è mai stata nella funzione obiettivo.

---

## (a) Due voci: CE per il supporto + NLI a tre vie con VETO sulla contraddizione

**Cosa**: il CE attuale resta e decide il supporto; un secondo modello NLI (tre classi:
entailment / neutral / contradiction) gira sulla stessa coppia (fonte, claim) e, se dice
`contradiction` sopra una soglia, **veta** la scrittura qualunque cosa dica il CE.

**Perché le due voci non sono ridondanti**: rispondono alle due domande di ⓪.b. Il veto è
asimmetrico di proposito — l'NLI può solo **fermare**, mai ammettere. Un secondo modello
che potesse ammettere raddoppierebbe le porte da cui entra un falso.

| costo | stima | come si verifica |
|---|---|---|
| memoria | **+ il peso dell'NLI per processo** — con un `large` siamo sui ~1,6 GB in più di RSS. ⚠️ NON VERIFICATO: nessuno l'ha ancora caricato accanto al CE e misurato | banco memoria con i due modelli vivi insieme, come `1f93a8c6` fece per due giudici |
| latenza | **~2× il giudizio a caldo** (due inferenze in sequenza), cioè da ~0,16 s a ~0,3 s con il daemon caldo | il banco del daemon con `via` che dichiara quale voce ha deciso |
| ⚠️ e il costo che si dimentica | il daemon della 0.8.0 diventa **due** modelli caricati: il conto della memoria che giustifica il daemon va rifatto | — |

**Predizione (falsificabile)**: sulle 30 coppie di ws3, l'NLI a tre vie ferma **almeno 4
delle 6** che oggi passano, e perde **al massimo 1** vero in più.
*(È la predizione depositata da lead-audit; la adotto invece di scriverne una mia, così
il banco decide fra noi e non fra due formulazioni.)*
**Come muore**: ne ferma meno di 3, oppure perde più di 3 veri.

**Il banco che la falsifica**: le 30 coppie di ws3 (24 trattenute + 6 passate) **più** un
insieme di veri della stessa forma — perché su soli negativi ogni criterio sembra ottimo,
e questa è una lezione che abbiamo già pagato. Le due popolazioni si misurano entrambe o
il numero non significa niente.

---

## (b) v3 ri-addestrato con negativi di contraddizione, soglia calibrata su entrambe le classi

**Cosa**: si resta a un modello solo, ma il training set acquista negativi di
**contraddizione** e di **contorno** (claim estranei ma lessicalmente vicini), e la soglia
si calibra su entrambe le classi invece che sull'F1 di una.

**Perché è la più elegante e la più rischiosa**: mantiene un modello, un caricamento, una
latenza — il daemon resta com'è. Ma chiede di rifare l'addestramento che ha prodotto la
patologia, con gli stessi strumenti che l'hanno prodotta.

| costo | stima | come si verifica |
|---|---|---|
| memoria e latenza | **zero in più**: stesso modello, stessa forma | — |
| costruzione del dataset | il pezzo vero: servono contraddizioni **etichettate** e contorni, e non li abbiamo | ws4 dica quante coppie di contraddizione esistono già in HaluMem con etichetta usabile |
| addestramento | ⚠️ NON VERIFICATO da me: ws4 ha appena avviato un fine-tune v3.1 sul dataset delle astensioni (937 esempi) — chi l'ha fatto sa quanto costa | ws4 |
| ⚠️ il rischio | la stessa pipeline ha già prodotto un cut inutilizzabile (99,6, scavalcato a runtime). Ripeterla senza cambiare **come si calibra** ripete il difetto | — |

**Predizione (falsificabile)**: un v3 con negativi di contraddizione ferma **almeno 4
delle 6** e produce una soglia **usabile** — cioè entro [20, 90], la regione dove la
calibrazione a runtime non deve più scavalcarla.
**Come muore**: se il cut ottimo torna sopra 90 (o sotto 20), la pipeline riproduce il
difetto e l'opzione (b) è morta a prescindere dall'accuratezza.
⚠️ **Questo secondo criterio conta quanto il primo, e non è sull'accuratezza**: un modello
accurato con una soglia che il prodotto deve ignorare è ciò che abbiamo adesso.

---

## (c) Sostituzione secca — MiniCheck al posto del CE

**Cosa**: si butta il fine-tune e si prende un modello di fact-checking già addestrato.

| costo | stima | come si verifica |
|---|---|---|
| accuratezza | **−15 punti su TruthfulQA** nella misura del 02/09 ⚠️ riportata da ws7, non rifatta da me | rifare la misura sulle stesse popolazioni della vetrina |
| memoria/latenza | dipende dalla taglia; potenzialmente **minori** del CE attuale | — |
| lavoro | il minore delle tre: nessun addestramento, nessuna seconda voce | — |

**Predizione**: (c) **non entra** nella 0.8.0. Non perché il modello sia cattivo, ma perché
15 punti sul numero pubblico è un prezzo che nessuna delle due patologie giustifica —
stiamo curando 6 casi su 30, non un fallimento sistemico.
**Come muore**: se rimisurata sulle popolazioni di oggi la perdita è **sotto 5 punti**,
(c) torna in gioco ed è di gran lunga la più economica.
⚠️ **E questa è la sola predizione delle tre che spera di essere falsificata.** Il 15 è di
una misura sola, di ieri, su una popolazione: non basta per chiudere una porta.

---

## Cosa serve prima di scegliere — e chi ce l'ha

1. **ws4**: i numeri di W7-132/134 con l'output grezzo, e quante coppie di contraddizione
   etichettate esistono già (decide se (b) è fattibile o solo desiderabile).
2. **ws3**: le 30 coppie come **banco riutilizzabile**, con le 6 che passano isolate — è il
   banco su cui si misurano tutte e tre le opzioni, altrimenti si confrontano su banchi
   diversi e il confronto non vale.
3. **chiunque abbia lo slot**: caricare CE + NLI insieme e misurare la memoria vera. È
   l'unico costo di (a) che oggi è una stima e non un numero, ed è quello che può
   ucciderla.
4. **la popolazione dei VERI**: nessuna delle tre si valuta sui soli negativi.

## La mia posizione, dichiarata perché coordinare non è astenersi

Preferisco **(a)** e la ragione non è l'accuratezza: è che (a) **aggiunge una domanda**
invece di ri-ottimizzare la risposta a quella vecchia. È l'unica delle tre che, se la
predizione cade, ci lascia sapere *perché* — se l'NLI non ferma le contraddizioni, allora
non erano contraddizioni riconoscibili dal testo, e questo è un fatto sul nostro corpus che
vale oltre la scelta del modello.

⚠️ Contro me stessa: (a) è anche la più cara, e il costo che pago volentieri sulla carta
(un secondo modello nel daemon) è esattamente quello che ho passato due giorni a misurare
per **toglierlo**. Se il banco di memoria dice che due modelli non stanno in piedi con
otto agenti, (a) muore e la mia preferenza non conta.

⇒ **Nessuna delle tre si adotta prima che il banco delle 30+30 abbia parlato.** Questa
pagina fissa i criteri; non sceglie.
