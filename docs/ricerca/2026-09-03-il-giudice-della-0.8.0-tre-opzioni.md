# Il giudice della 0.8.0 — il confronto e il criterio di scelta

*ws5 «TARA», 03/09/2026. Coordinamento assegnato da lead-audit; i numeri del fine-tune li
porta ws4. **Design, non codice.***

> Le tre opzioni hanno una pagina ciascuna. **Qui non si ripete il loro contenuto**: qui
> c'è solo ciò che serve a **sceglierle**, e sta in un posto solo perché un criterio
> ricopiato in tre file diverge — è la prima delle classi di errore che ci costano.
>
> - **(a)** [due voci: CE + NLI con veto](2026-09-03-giudice-0.8.0-opzione-a-due-voci.md)
> - **(b)** [v3.2 ri-addestrato](2026-09-03-giudice-0.8.0-opzione-b-v3.2-riaddestrato.md)
> - **(c)** [sostituzione secca](2026-09-03-giudice-0.8.0-opzione-c-sostituzione-secca.md)

---

## La diagnosi che le tre opzioni condividono

Il giudice risponde a **una** domanda — «la fonte supporta il claim?» — con un numero solo.
Le domande sono **due** e indipendenti: *supporto* e *contraddizione*. Su un asse solo,
«contrario al testo» e «non nel testo» cadono nella stessa regione, e la soglia che separa
bene l'una separa male l'altra. ⇒ Le 6 contraddizioni su 30 che passano non sono un
difetto di calibrazione: sono la domanda che non è stata posta.

Questo spiega anche perché il modello base le vede e il nostro no: il fine-tune ha
ottimizzato l'asse del supporto, e la capacità di contraddizione — che il base aveva dal
pre-training NLI — non era né premiata né protetta. Non è stata «persa»: non è mai stata
nella funzione obiettivo.

⚠️ **E una regola che stasera è caduta**, per i numeri di ws4 (`2c93d2dd4070e398`): «il
fine-tuning costa capacità» è **troppo grossa**. Lo stesso fine-tune ha danneggiato le
astensioni (`9/100`) e **riparato** la zavorra (`+0,990` → `+0,031`). Un fine-tune sposta
il modello nella direzione del suo dataset: cosa guadagna e cosa perde dipende da cosa c'è
dentro, non è una tassa fissa.

## Il banco comune — e non è negoziabile

Le tre opzioni si misurano **sulle stesse popolazioni**, o il confronto non vale:

1. le **30 coppie di ws3** (24 trattenute + 6 passate), con le 6 isolate;
2. una popolazione di **veri** della stessa forma — su soli negativi ogni criterio sembra
   ottimo, ed è una lezione già pagata;
3. per (c), anche le **quattro popolazioni della vetrina**, perché è da lì che esce il
   numero pubblico.

## L'ordine in cui vanno eseguite, e perché non è l'ordine alfabetico

1. **(c) per prima.** È la più economica da eseguire ed è quella che, se la rimisura
   smentisce i −15 punti, **rende inutili le altre due**. Rimisurare un numero di ieri
   costa meno che progettare attorno ad esso.
2. **Il banco di memoria di (a)** subito dopo: è l'unico costo che oggi è una stima e non
   un numero, ed è quello che può uccidere (a) prima dell'accuratezza.
3. **(b) per ultima**, perché è l'unica che richiede di **costruire un dataset** prima di
   poter essere valutata — e senza il conteggio delle coppie di contraddizione etichettate
   non è un'opzione, è un progetto di raccolta dati travestito da opzione.

## Cosa serve prima di scegliere, e chi ce l'ha

| serve | chi | perché decide |
|---|---|---|
| coppie di contraddizione **etichettate**, col conteggio grezzo | ws4 | se (b) è fattibile o solo desiderabile |
| le 30 coppie come **banco riutilizzabile** | ws3 | senza, le tre si confrontano su banchi diversi |
| **CE + NLI caricati insieme**, RSS misurato col pool a 4 worker | chi ha lo slot | può uccidere (a) |
| rimisura di **MiniCheck sulle quattro popolazioni** | — | può rendere inutili (a) e (b) |

## La mia posizione, dichiarata perché coordinare non è astenersi

Preferisco **(a)**: aggiunge una domanda invece di ri-ottimizzare la risposta a quella
vecchia, ed è l'unica che, se la predizione cade, ci lascia sapere **perché**.

⚠️ **Contro me stessa, due volte.** (a) è la più cara, e il costo che pago volentieri
sulla carta — un secondo modello nel daemon — è esattamente quello che ho passato due
giorni a misurare per toglierlo. E i numeri di ws4 hanno reso (b) più forte di stamattina:
un ri-addestramento **ha già riparato** una patologia, quindi «ri-addestrare non ripara»
non è più un argomento contro (b).

⇒ **Nessuna si adotta prima che il banco comune abbia parlato.** Questa pagina fissa i
criteri e l'ordine; non sceglie.
