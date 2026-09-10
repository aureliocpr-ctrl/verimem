# Gravità di T55-T59 e dei 41 comandi senza prova — ws7 «Iris» (10/09)

> Chiesto dal lead (RIPARTENZA 10/09 13:05). Continua
> [GRAVITA-DEI-TICKET-09-09.md](GRAVITA-DEI-TICKET-09-09.md), stesso criterio, e
> ordina `COMANDI-SENZA-PROVA.md` di Marie (ramo `marie/porte-provate`, `ff64e030`)
> che dichiara da sé: *«la gravità la fissa @Iris, questa lista non la ordina»*.

## 0. Il criterio, invariato dal 09/09

Tre domande — **blocca un percorso d'uso? · blocca la promessa centrale? · l'utente
se ne accorge da solo?** — e l'ordinatore fra due P0: **un difetto che SCRIVE batte
un difetto che LEGGE**, perché la cura di una lettura ripara anche il passato e
quella di una scrittura no.

⚠️ **Che cosa ho verificato io e che cosa cito.** Le definizioni vengono dai post
del lead (23:45, mezzanotte) e da `COMANDI-SENZA-PROVA.md` di Marie, che porta i
suoi comandi e i suoi output. **Non ho rieseguito nessuno dei 41 comandi né i RED di
Marie**: la gravità è un giudizio di prodotto, non una misura, e rifarle mi
costerebbe la macchina che Aurelio sta usando. Dove il giudizio dipende da un fatto
che non ho verificato, lo scrivo nella riga.

## 1. La tabella

| # | ticket | owner | 1. percorso | 2. promessa | 3. se ne accorge | **gravità** |
|---|---|---|---|---|---|---|
| 1 | **T56** una scrittura ha due politiche di conservazione secondo la porta (mcp:unbound **0/151** con firma, cli 9716/10964) | ws6 Aldo | no | **sì** | **no** | **P0** |
| 2 | **T58** `facts restore` ABORTITO esce **0** | → ws2 Giano | **sì** | **sì** | **no** | **P0** |
| 3 | **T55** `introspect` non degrada: `EncodeDelegateUnavailable` risale a Typer (~40 righe) | → ws2 Giano | **sì** | no | **sì**, rumoroso | **P1 alto** |
| 4 | **①b GRUPPO** 8 comandi `swarm`/`teams`: il montaggio non è provato da nessuno | ws1 Marie | no (oggi) | no | **no** | **P1** |
| 5 | **T59** la tabella GDPR del README elenca 5 porte, il server ne espone 7 | ws7 Iris | no | **sì** | no | **P2** |
| 6 | **①h AIUTO** 15 comandi provati solo con `--help` | ws1 Marie | no | no | — | **P2** |
| 7 | **CHIEDE ≠ provato** 5 comandi mai partiti (il parser ha chiesto un argomento) | ws1 Marie | no | no | — | **P2 meccanico** |
| 8 | **T57** un presidio che guarda l'output crede all'output | ws7 Iris | no | no | — | **non si chiude: §3** |
| 9 | **APPESO ≠ rotto** 4 server/TUI senza verdetto con questo metodo | ws1 Marie | no | no | — | **P3, altro metodo** |
| — | i **5 non eseguiti** (modelli, o lanciano istanze vere) | ws1 Marie | — | — | — | **NON MISURATI** |

## 2. Le cinque righe che non si leggono dalla tabella

**① T56 in cima, e concordo col lead per una ragione mia.** Il lead l'ha già
chiamato P0 usando il mio criterio («è un difetto che SCRIVE»). Non lo adotto per
cortesia: lo confermo perché il numero che porta è **0 su 151**. Non «poche»: dalla
porta MCP unbound **nessuna** scrittura conserva la firma della fonte. La firma è ciò
che permette al moat di distinguere un fatto verificato da un `model_claim`; una
porta che non la conserva produce memoria epistemicamente più povera **e non lo
dice**. Scrive, è silenzioso, e la differenza fra le porte è invisibile a chi usa una
porta sola — cioè a tutti. *(Il 0/151 è di Aldo, non l'ho rimisurato.)*

**② T58 è la famiglia peggiore: un'operazione di RECUPERO che mente.** Non scrive
niente — ed è il punto: dichiara `EXIT=0` per un ripristino **non avvenuto**. Chi
chiama `restore` è già dentro un danno; dirgli «fatto» quando non è fatto glielo
raddoppia, e lo scopre quando cerca i dati. Nel mio ordinatore sta con quelli che
scrivono: è un mancato-scrivere che si dichiara riuscito.

**③ T55 è P1 e non P2 per la POPOLAZIONE, non per il danno.** Un traceback di 40
righe è rumoroso: l'utente lo vede e non ci costruisce sopra. Ma Marie ha misurato
che è rotto **solo** con `HIPPO_ENCODE_DELEGATE_ONLY=1` — la configurazione con cui
gira il server MCP, cioè quella di chi usa il prodotto **come agente**, che è il caso
d'uso che il README mette per primo. Un difetto che colpisce solo la configurazione
principale non è un caso limite.

**④ Il reperto di Marie che vale più dei 41 comandi**, e per questo lo metto in
tabella come voce a sé:

> *«Togli `app.add_typer(swarm_app, name="swarm")` (`cli.py:94`) e **otto test
> restano verdi mentre `verimem swarm *` e `verimem teams *` spariscono per
> l'utente**.»*

Otto comandi possono uscire dal prodotto senza che un solo test diventi rosso,
perché i test invocano `swarm_app` **direttamente** invece che attraverso `app`. È
la stessa forma del mio README:505-506 (il presidio guarda un livello più in basso
di quello che la promessa riguarda), e ha la cura più economica di tutta questa
tabella: **un test che invoca `app` con `["swarm", …]`**. Un file, otto comandi
coperti. Se dovessi indicare una cosa sola da fare fra tutte le righe di questa
pagina, è questa.

**⑤ ①h AIUTO non è un difetto e va detto**, perché 15 su 41 è la maggioranza della
lista e leggerla male la gonfia. `tests/test_cli.py:83` invoca ogni comando con
`--help` e il suo docstring dichiara che serve a intercettare gli errori di import.
Come scrive Marie: **«non è un test finto: è un test di un'altra cosa.»** Prova che
il comando esiste e che il modulo si importa — che è esattamente ciò che serve
sapere per un comando che nessuno usa mai. Il debito è reale ma è di secondo grado.

## 3. T57 non si chiude: si istituzionalizza

T57 è il reperto di ieri notte: *il comando stampa «nothing imported yet» mentre ha
importato, e il presidio che guarda l'output resta verde*. Il lead l'ha registrato
come ticket con gravità mia. **La mia gravità è: non è un ticket.**

Un ticket si chiude con una cura. Qui non c'è una cura: c'è un modo sbagliato di
scrivere i presidi, e chiuderlo sul singolo caso (che ho già presidiato, `15f8fc2d`)
lo farebbe sparire lasciando in piedi tutti gli altri presidi della stessa forma.

**Proposta: T57 diventa una riga della DoD**, dove Marie la applica a ogni revisione:

> **Il RED asserisce l'EFFETTO, non il messaggio.** Un test che guarda solo
> `exit_code`, l'output a schermo o il payload di risposta prova che il comando
> *dice* di aver fatto la cosa. Per una promessa di stato — ha scritto? ha
> cancellato? ha ripristinato? — l'asserzione va sullo stato: lo store, il file, la
> tabella.

Vale già su due ticket di questa pagina: **T58** (`EXIT=0` è precisamente un
presidio-che-guarda-l'output istituzionalizzato nel prodotto) e sui **15 ①h AIUTO**.
Chiudere T57 come «fatto» sarebbe la quarta volta che questo progetto scrive una
regola giusta e non la mette in un controllo.

## 4. Che cosa cambia per l'utente, in una riga per ticket

    T56  ciò che scrive da un agente MCP ha la stessa qualità di ciò che scrive dalla CLI
    T58  quando il prodotto dice «ripristinato», i dati ci sono
    T55  un comando che non può parlare col modello lo dice, invece di un traceback
    ①b   otto comandi non possono sparire senza che nessuno se ne accorga
    T59  la pagina che risponde a una richiesta di cancellazione dati elenca TUTTE le porte
    ①h   (nulla oggi: chiude un debito, non un difetto)
