# La prova della scheda — come si falsifica, e perché non possiamo eseguirla noi

**Iris (ws7, Product Owner), 06/09 01:55.** La scheda prodotto dichiara una cosa
verificabile, e finora **nessuno l'ha verificata**. Questo documento non la
verifica: **la rende eseguibile da chi può**, e dice chi può.

---

## La frase che è in gioco

`SCHEDA-PRODOTTO.md` apre con questa, ed è l'unica cosa che la scheda promette
**di sé** invece che del prodotto:

> ✅ **La prova che questa scheda funziona è falsificabile**: un utente che non
> ci conosce arriva in fondo ai dieci minuti **senza aprire le altre 780 righe**.
> Se non ci arriva, la scheda è sbagliata — non l'utente.

⇒ Finché nessuno la esegue, quella riga è **una promessa non mantenuta dentro un
documento che accusa il README di fare lo stesso**. Ed è la ragione per cui
questo protocollo esiste.

---

## Perché non possiamo eseguirla noi otto

**Non per modestia: per costruzione.** Noi sappiamo dove guardare. Sappiamo che
`warmup` va prima, che `doctor` esce 1 per lo store vuoto, che la porta MCP
aspetta, che `Risultati` ha attributi. **Ogni nostra esecuzione parte da un
vantaggio che l'utente non ha**, e quel vantaggio non si toglie decidendo di non
usarlo — le nostre dita conoscono già la strada.

⇒ **Chi esegue deve non aver mai visto questo prodotto.** Un'istanza nuova, un
collega, chiunque — purché la sua prima informazione su verimem sia la scheda.

---

## Il soggetto si può creare — ma è un **surrogato**, e il surrogato è sbilanciato

**Proposta di @ws4 Nadia (`1a0fe70fb1981e16`), e la accetto**: il soggetto adatto
non è nella stanza, ma **si crea** — una CLI Claude **fresca**, senza il nostro
canale, senza il registro, senza il codice. Riceve la scheda e basta. È
l'infrastruttura del playbook, costa dieci minuti, ed è *letteralmente* qualcuno
che non ci conosce.

⚠️ **E non è un utente.** Va detto qui, prima di leggere il risultato, perché
cambia cosa il risultato significa:

| | un umano che non ci conosce | una CLI fresca |
|---|---|---|
| il nostro contesto | non ce l'ha | non ce l'ha ✅ |
| le convenzioni generali (README, Quickstart, Python) | ne ha alcune | **ne ha moltissime** |
| cosa fa davanti a un buco della scheda | **si ferma, o sbaglia** | **lo riempie indovinando** |

⇒ Un modello è **addestrato a colmare l'implicito**. Dove la scheda tace, lui
completa — e completa *bene*, perché ha letto un milione di Quickstart. **Quindi
sottostima sistematicamente i buchi**, ed è per questo che l'esito va letto in un
verso solo:

· 🔴 **un ROSSO vale moltissimo**: se persino chi indovina bene si è fermato,
  **un umano si ferma di sicuro**. Il difetto è reale e sottostimato.
· 🟡 **un VERDE vale poco**: dice «la scheda è sufficiente *per chi sa già
  indovinare*», che non è la promessa. Non chiude la domanda, la sospende.

📌 **La domanda ③ è la protezione contro il verde facile.** Chiedere *«cosa fa
verimem e a chi serve, con parole tue»* non si supera indovinando la sintassi di
un comando: o la scheda ha trasmesso il **prodotto**, o si vede. **Se il verde
arriva con una terza risposta generica — «una memoria per agenti», e basta — è un
rosso mascherato**, e il modo di leggerlo è già scritto: la scheda ha insegnato
una procedura invece di un prodotto.

### Chi lo lancia

**Non io e non Nadia di nostra iniziativa**: apre un processo sulla macchina di
Aurelio, ed è fuori dal perimetro di entrambe. **La decisione è del lead**; il
protocollo, il file da consegnare e il modulo delle tre righe sono pronti qui,
così quando il via arriva costa solo i dieci minuti che deve costare.

⛔ **E una cosa che chi lancia deve NON fare**: dare alla CLI fresca il README, il
registro o questo file. Riceve `SCHEDA-PRODOTTO.md` e il modulo delle tre righe.
**Se le si consegna anche il contesto, si è misurato il contesto.**

---

## Il protocollo, in una pagina

### Cosa riceve chi esegue

**Solo `SCHEDA-PRODOTTO.md`.** Nient'altro: non il README, non `GRAVITA-DIFETTI`,
non `PERCORSI-UTENTE`, non questo file, non il canale. Se chiede aiuto, **la
risposta è «quello che ti serve è nella pagina, o non c'è»**.

### Cosa fa

Quello che la scheda dice di fare, con un cronometro. Nient'altro.

### Cosa si misura — **tre cose, e la terza è quella vera**

| # | domanda | come si risponde |
|---|---|---|
| 1 | **ci è arrivato in fondo?** | il Quickstart passa · sì/no |
| 2 | **in quanto?** | minuti, cronometrati da chi esegue |
| 3 | 🔑 **sa dire a voce cosa fa il prodotto e a chi serve?** | **con parole sue, senza rileggere** |

**La terza è il criterio**, ed è l'unica che la scheda non può falsificare da
sola: le prime due le misura anche un banco (e le abbiamo: 5,9 minuti). Se qualcuno
arriva in fondo in cinque minuti e non sa dire **a chi serve**, **la scheda ha
fallito** — ha insegnato una procedura invece di un prodotto.

### Cosa conta come **passato**

> *In dieci minuti chi non ci conosceva ha visto il prodotto rifiutare una
> falsità, e sa dire con parole sue cosa fa e a chi serve — senza aver aperto
> nient'altro.*

**Tutte e tre le clausole insieme.** Due su tre è un fallimento, e il modo in cui
fallisce dice cosa correggere:
· **non arriva in fondo** → la procedura è sbagliata o incompleta;
· **arriva ma fuori tempo** → la scheda promette dieci minuti che non ci sono;
· **arriva in tempo e non sa dire a chi serve** → **la scheda è scritta per noi**,
  e va riscritta la prima schermata, non i dettagli.

### Cosa NON è un fallimento della scheda

Un difetto del prodotto che la scheda **dichiara già** — `doctor` che esce 1, i
903 s sulla porta MCP, il costo di contesto. Se chi esegue ci inciampa **e la
scheda glielo aveva detto**, la scheda ha funzionato: è il prodotto che deve
migliorare. **Vanno separati nel referto**, o la prova misura due cose insieme e
non se ne capisce nessuna.

---

## Cosa chiedo a chi la esegue: **tre righe, non un rapporto**

```
1. sono arrivato in fondo?          sì / no  (e dove mi sono fermato)
2. quanti minuti?                   __
3. cosa fa verimem, e a chi serve?  (con parole tue, senza rileggere la scheda)
```

E, se ti va, **una riga in più che vale più delle tre**: *«la cosa che ho dovuto
indovinare»*. Quella è il buco della scheda, e non la vede nessun altro.

---

## ⚠️ Il limite di questo protocollo, dichiarato

**Una sola esecuzione non è una misura**: dice che *quella* persona ce l'ha fatta
o no. Serve a **falsificare** («se anche uno solo non ci arriva, la scheda ha un
problema»), non a certificare. Un verde su uno non dimostra che la scheda
funzioni; **un rosso su uno dimostra che non funziona**, ed è per questo che vale
la pena farla anche una volta sola.

📌 **E vale anche al contrario**: se chi esegue trova la scheda chiara ma **il
prodotto** lo blocca, quello è un difetto di prodotto trovato dall'unica persona
che poteva vederlo senza pregiudizio — e va nel registro con la sua gravità,
esattamente come gli altri.

---

## Trovare i presidi da eseguire: le TRE direzioni in cui si sbaglia

*06/09, dalla regola di Aurelio delle 10:03 — «nessun push senza aver eseguito i
test che nominano la cosa toccata, cercandoli per **contenuto** e non per nome».
In una mattina ho sbagliato le prime due e @ws8 Corrado ha trovato la terza, che
è la peggiore.*

| # | il criterio | l'errore | misurato |
|---|---|---|---|
| ① | la parola **e** l'apertura **sulla stessa riga** | **troppo stretto: PERDE** | 15 file invece di 21 |
| ② | la parola **e** l'apertura **ovunque nel file** | **troppo largo: ANNACQUA** | 33, di cui 12 non c'entrano |
| ③ | il **NOME** della cosa invece del suo **USO** | **perde chi la tocca senza nominarla** | il commit di release cambia `__version__`: cercando i sei file per nome ne usciva 21, cercando **chi legge `__version__`** ne uscivano 5, **3 dei quali persi** (@ws8, 10:26) |

**Il criterio giusto non è una formula, è una domanda**: *cosa cambia davvero, e
chi lo legge?* Per il README è **chi apre `README.md`** (21 file). Per un commit
di release è **chi usa la versione** (5), non chi nomina i file che la
contengono.

⚠️ **Come si sa che il criterio ha visto**: un elenco di presidi tutti verdi non
dice niente finché non si rimette **la cosa sbagliata** e si conta quanti si
accendono. Il 06/09, con il banner falso rimesso, **0 su 15** si sono accesi —
ed è così che si è scoperto che il blocco più letto del README non era
presidiato da nulla.
