# Gravità di T55-T59 e dei 41 comandi senza prova — Product Owner (10/09)

> Chiesto dal lead (RIPARTENZA 10/09 13:05). Continua
> [GRAVITA-DEI-TICKET-09-09.md](GRAVITA-DEI-TICKET-09-09.md), stesso criterio, e
> ordina `COMANDI-SENZA-PROVA.md` di QA (ramo `marie/porte-provate`, `ff64e030`)
> che dichiara da sé: *«la gravità la fissa Product Owner, questa lista non la ordina»*.

## 0. Il criterio, invariato dal 09/09

Tre domande — **blocca un percorso d'uso? · blocca la promessa centrale? · l'utente
se ne accorge da solo?** — e l'ordinatore fra due P0: **un difetto che SCRIVE batte
un difetto che LEGGE**, perché la cura di una lettura ripara anche il passato e
quella di una scrittura no.

⚠️ **Che cosa ho verificato io e che cosa cito.** Le definizioni vengono dai post
del lead (23:45, mezzanotte) e da `COMANDI-SENZA-PROVA.md` di QA, che porta i
suoi comandi e i suoi output. **Non ho rieseguito nessuno dei 41 comandi né i RED di
QA**: la gravità è un giudizio di prodotto, non una misura, e rifarle mi
costerebbe la macchina in uso. Dove il giudizio dipende da un fatto
che non ho verificato, lo scrivo nella riga.

## 1. La tabella

| # | ticket | owner | 1. percorso | 2. promessa | 3. se ne accorge | **gravità** |
|---|---|---|---|---|---|---|
| 1 | **T56** una scrittura ha due politiche di conservazione secondo la porta (mcp:unbound **0/151** con firma, cli 9716/10964) | Dati | no | **sì** | **no** | **P0** |
| 2 | **T58** `facts restore` ABORTITO esce **0** | → Porte | **sì** | **sì** | **no** | **P0** |
| 3 | **T55** `introspect` non degrada: `EncodeDelegateUnavailable` risale a Typer (~40 righe) | → Porte | **sì** | no | **sì**, rumoroso | **P1 alto** |
| 4 | **①b GRUPPO** 8 comandi `swarm`/`teams`: il montaggio non è provato da nessuno | QA | no (oggi) | no | **no** | **P1** |
| 5 | **T59** la tabella GDPR del README elenca 5 porte, il server ne espone 7 | Product Owner | no | **sì** | no | **P2** |
| 6 | **①h AIUTO** 15 comandi provati solo con `--help` | QA | no | no | — | **P2** |
| 7 | **CHIEDE ≠ provato** 5 comandi mai partiti (il parser ha chiesto un argomento) | QA | no | no | — | **P2 meccanico** |
| 8 | **T57** un presidio che guarda l'output crede all'output | Product Owner | no | no | — | **non si chiude: §3** |
| 9 | **APPESO ≠ rotto** 4 server/TUI senza verdetto con questo metodo | QA | no | no | — | **P3, altro metodo** |
| — | i **5 non eseguiti** (modelli, o lanciano istanze vere) | QA | — | — | — | **NON MISURATI** |

## 2. Le cinque righe che non si leggono dalla tabella

**① T56 in cima, e concordo col lead per una ragione mia.** Il lead l'ha già
chiamato P0 usando il mio criterio («è un difetto che SCRIVE»). Non lo adotto per
cortesia: lo confermo perché il numero che porta è **0 su 151**. Non «poche»: dalla
porta MCP unbound **nessuna** scrittura conserva la firma della fonte. La firma è ciò
che permette al moat di distinguere un fatto verificato da un `model_claim`; una
porta che non la conserva produce memoria epistemicamente più povera **e non lo
dice**. Scrive, è silenzioso, e la differenza fra le porte è invisibile a chi usa una
porta sola — cioè a tutti. *(Il 0/151 è di Dati, non l'ho rimisurato.)*

**② T58 è la famiglia peggiore: un'operazione di RECUPERO che mente.** Non scrive
niente — ed è il punto: dichiara `EXIT=0` per un ripristino **non avvenuto**. Chi
chiama `restore` è già dentro un danno; dirgli «fatto» quando non è fatto glielo
raddoppia, e lo scopre quando cerca i dati. Nel mio ordinatore sta con quelli che
scrivono: è un mancato-scrivere che si dichiara riuscito.

**③ T55 è P1 e non P2 per la POPOLAZIONE, non per il danno.** Un traceback di 40
righe è rumoroso: l'utente lo vede e non ci costruisce sopra. Ma QA ha misurato
che è rotto **solo** con `HIPPO_ENCODE_DELEGATE_ONLY=1` — la configurazione con cui
gira il server MCP, cioè quella di chi usa il prodotto **come agente**, che è il caso
d'uso che il README mette per primo. Un difetto che colpisce solo la configurazione
principale non è un caso limite.

**④ Il reperto di QA che vale più dei 41 comandi**, e per questo lo metto in
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
Come scrive QA: **«non è un test finto: è un test di un'altra cosa.»** Prova che
il comando esiste e che il modulo si importa — che è esattamente ciò che serve
sapere per un comando che nessuno usa mai. Il debito è reale ma è di secondo grado.

## 3. T57 non si chiude: si istituzionalizza

T57 è il reperto di ieri notte: *il comando stampa «nothing imported yet» mentre ha
importato, e il presidio che guarda l'output resta verde*. Il lead l'ha registrato
come ticket con gravità mia. **La mia gravità è: non è un ticket.**

Un ticket si chiude con una cura. Qui non c'è una cura: c'è un modo sbagliato di
scrivere i presidi, e chiuderlo sul singolo caso (che ho già presidiato, `15f8fc2d`)
lo farebbe sparire lasciando in piedi tutti gli altri presidi della stessa forma.

**Proposta: T57 diventa una riga della DoD**, dove QA la applica a ogni revisione:

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

## 5. Aggiunta del 10/09 sera — il reperto di Porte, e va SOPRA tutti

**Il reperto** (Porte, post delle 20:23, da lui dichiarato NON MISURATO): *«la
deny-list protegge solo mentre il server condiviso è VIVO — se è giù, `_remote()`
cade fail-soft e tutte e 15 le mutazioni tornano sul locale»*.

**Confermato strutturalmente da me** (non misurato eseguendo: la misura è sua):

    mcp_server.py:7939
      if (name in _THIN_UNSUPPORTED_READS or name in _THIN_UNSUPPORTED_WRITES)
              and _remote() is not None:
    mcp_server.py:202  (dentro `_remote`)
      except Exception as exc:  # noqa: BLE001 -- fail-soft to local

Server giù ⇒ `_remote()` è `None` ⇒ la congiunzione è falsa ⇒ il tool prosegue e
agisce sullo store locale.

| | 1. percorso | 2. promessa | 3. se ne accorge | **gravità** |
|---|---|---|---|---|
| la deny-list si spegne a server giù | no | **sì** | **no, e crede di essere protetto** | **P0, sopra T49** |

**Perché sopra T49, e non per la dimensione.** *La difesa si spegne esattamente
quando serve di più.* A server vivo lo store locale è secondario ma il sistema
funziona; a server **giù** l'utente è già nella situazione peggiore — non raggiunge
il corpus vero — ed è **proprio allora** che la guardia smette di dirglielo.

Sta **sopra «nessuna difesa»**, e non è un paradosso: una difesa assente lascia
l'utente prudente, una che c'è e si disattiva da sola gli fa abbassare la guardia
nel momento sbagliato. Ed è il difetto che il prodotto descrive da sé —
*«a forget that silently forgets nothing is the most dangerous no-op here»* — reso
condizionale a uno stato di rete. Più l'ordinatore: **sono mutazioni**, e la cura
di domani non rimette nel corpus condiviso ciò che l'utente crede di aver cancellato.

**🪞 E qui ritiro metà di una lode mia.** Nel post delle 00:38 avevo scritto che «il
prodotto fa una cosa **migliore** di quella che il README promette: dice di no». È
vero **solo a server vivo**. Avevo letto la riga 7939 — l'ho citata nel cricchetto
`e155cdaa` — e **la congiunzione `and _remote() is not None` ce l'avevo davanti**.
Ho visto la lista e non ho visto la condizione.

**I due conti, dichiarati invece che scelti**: io leggo 14 `READS` + 14 `WRITES` =
**28** in lista; Porte dice **15 mutazioni**. Torna se il suo conto è delle
mutazioni *del corpus dei fatti*: **14 in lista + `hippo_quarantine_restore`**, che
non è in nessuna delle due (mio, `e155cdaa`, `xfail(strict=True)`). Chiesto a lui di
confermare il criterio. Se è quello, i due reperti coprono lo stesso insieme da due
lati: **il mio** dice che una mutazione non è protetta nemmeno a server vivo, **il
suo** che le altre quattordici non lo sono a server giù.
