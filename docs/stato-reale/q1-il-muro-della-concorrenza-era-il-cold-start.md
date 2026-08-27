# Q1 — «Il muro della concorrenza» non esiste: era il cold start. E il costo vero è 1,2 s per scrittura

*ws3 (Galileo), 27/08 ~20:47, laboratorio «il piccolo chimico». Il numero
sbagliato l'avevo portato io stasera; l'ho rimisurato io. Tre versioni di questa
misura, e le due precedenti erano entrambe mie.*

## Il numero definitivo

`benchmark/concurrency_multiprocess.py --workers 1 --secs 90` — store
temporaneo (`tempfile.mkdtemp`), Windows, PC con otto istanze attive:

    REGIME: 90 secondi · 1 worker · busy_timeout default 60000
    letture 105 · scritture 35 · errori 0

    read_p50      179,6 ms       write_p50    1.213,1 ms
    read_p99      235,3 ms       write_p99   26.084,0 ms
    read_max    2.717,4 ms       write_max   26.084,0 ms

    throughput 1,5 ops/s · ops sopra 5 s: 1 · ops sopra 10 s: 1

## Le tre letture, in ordine, e le prime due erano mie

| | fonte | write | conclusione |
|---|---|---|---|
| ① | test del 21/07, 2 worker, 10 s | 23.914 ms | «0,2 ops/s, non regge un uso massivo» |
| ② | mio run, 1 worker, 10 s, **n=2** | 111 ms | «il costo vero è 111 ms» |
| ③ | **questo**, 1 worker, 90 s, **n=35** | **1.213 ms** | il costo vero è **~1,2 s** |

**① era il cold start travestito da concorrenza. ② era un artefatto di n=2 —
troppo ottimista di dieci volte.** Entrambe le ho consegnate io, e la seconda
l'avevo consegnata *dichiarando* che n=2 non è una mediana. Averlo dichiarato
non l'ha resa meno sbagliata: è di nuovo *un limite dichiarato che non protegge
l'enunciato accanto*.

## Cosa dicono i numeri

**① Il cold start esiste ed è UNO.** `write_p99` = `write_max` = 26.084 ms
significa **un solo valore alto** in tutta la serie: la prima scrittura, quella
che carica i due modelli (`Loading weights` 202 + 394, warmup `moat-judge`
~2 s). Su 140 operazioni, **una sola supera i 10 secondi**.

**② La concorrenza non degrada.** Da 1 a 2 worker le letture passano da
**208 a 221 ms: +6%**. Con contesa su sqlite crollerebbero. E in 90 secondi,
**zero errori** — nessun lock timeout, nessun deadlock.

**③ Ma la scrittura a regime costa 1,2 secondi**, non 111 ms. È il numero con
cui fare i conti, e non è il database: è l'embedding calcolato a ogni scrittura.
Le **letture invece sono buone** — mediana 180 ms, p99 235 ms.

## Il ricalcolo, per la domanda «uno studio legale, uso massivo»

    prima:  0,2 operazioni al secondo, muro invalicabile
    ora:    ~1,5 operazioni al secondo per processo
            ~1,2 s per scrittura · ~0,18 s per lettura
            + ~26 s di avvio, UNA volta per processo

⇒ La domanda non è più «regge?» ma **«il processo resta vivo?»**. In un servizio
persistente i 26 secondi si pagano all'accensione; in un uso CLI usa-e-getta —
**che è come lo usiamo noi** — si pagano ogni volta, e sono il 95% del tempo
percepito.

📌 E il test per il regime giusto **esiste già nel repo**:
`benchmark/concurrency_shared_server.py`. Nessuna di noi lo aveva citato oggi,
me compresa, mentre discutevamo di scalabilità.

⚠️ **Resta vero che 1,2 s per scrittura è lento** per un uso interattivo massivo.
Il muro non è dove lo avevo messo, ma non è che non ci sia niente: c'è un costo
di embedding per fatto che nessuno ha mai provato a ridurre o a rendere
asincrono.

## Il regime dell'utente vero: **nessun muro. 14,3 operazioni al secondo.**

La cella che avevo lasciato aperta l'ho poi misurata:
`benchmark/concurrency_shared_server.py --workers 2 --secs 60` — **un** server
che possiede i modelli e il db una volta sola, due client sottili in processi
loro, server uvicorn in un processo suo.

    2 client · 60 secondi · 654 letture · 217 scritture · ERRORI 0

    read_p50      101,7 ms       write_p50     258,3 ms
    read_p99      185,5 ms       write_p99     575,8 ms
    read_max    1.416,8 ms       write_max   1.188,0 ms

    throughput 14,3 ops/s · ops sopra 5 s: 0 · ops sopra 10 s: 0

### Il confronto

| | N processi (anti-pattern) | **server condiviso** | fattore |
|---|---|---|---|
| write p50 | 1.213 ms · *(23.914 nel test di luglio)* | **258 ms** | 4,7× · *93×* |
| write max | 26.084 ms | **1.188 ms** | **22×** |
| read p50 | 179,6 ms | **101,7 ms** | 1,8× |
| throughput | 1,5 ops/s | **14,3 ops/s** | **9,5×** |
| ops sopra 10 s | 1 | **0** | — |
| operazioni totali | 140 | **871** | 6,2× |

**La predizione del docstring era esatta**: «*if the architecture is the cure,
writes stay in the hundreds-of-ms range instead of tens of seconds*» → **258 ms**.

⇒ **Il muro non esiste.** Lo «0,2 ops/s» con cui ho allarmato tutti era la
misura di un **anti-pattern che il repo dichiara tale**. Nel regime che userebbe
davvero un cliente — un servizio che tiene i modelli caricati — il sistema fa
**14,3 operazioni al secondo, zero errori, e nessuna operazione sopra i cinque
secondi**.

⚠️ **Il limite che conta**: sono **2 client**, non venti. Fra 2 e 20 c'è una
curva che nessuno ha misurato, ed è lì che vive la domanda «uso massivo». Questo
risultato sposta l'onere della prova, non lo chiude.

## La curva 2→20 client: **si piega fra 5 e 10, e la mediana mente**

L'ultima cella aperta, misurata: `--workers 2 5 10 20 --secs 30`, stesso
regime servizio.

| client | letture | scritture | errori | read p50 | **read p99** | write p50 | **ops/s** | >5 s | >10 s |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 311 | 102 | 0 | 103,3 | 590,5 | 245,6 | **13,4** | 0 | 0 |
| 5 | 440 | 145 | 0 | 96,1 | **3.364,2** | 587,6 | **18,7** | 0 | 0 |
| 10 | 417 | 136 | 0 | 156,6 | **8.378,2** | 1.115,1 | 17,5 | **10** | 0 |
| 20 | 255 | 83 | 0 | 368,5 | **17.618,4** | 2.291,4 | **10,4** | **20** | **20** |

**① Il throughput ha un picco a 5 client (18,7 ops/s) e poi cala.** A 20 client
il sistema fa **meno** di quanto facesse con 2. Il punto di saturazione sta
**fra 5 e 10**.

**② La coda esplode molto prima del throughput, e la mediana lo nasconde.** A 5
client `read_p50` è **96 ms** — sembra perfetto — ma `read_p99` è già **3,4
secondi**. Chi guardasse solo la mediana concluderebbe «regge fino a 20», e
sbaglierebbe: a 10 client dieci operazioni superano i 5 s, a 20 client **venti
operazioni superano i 10 s**.

**③ Zero errori in tutte e quattro le configurazioni.** Il sistema non si
rompe: **rallenta**. Nessun lock timeout, nessun deadlock, nemmeno a 20 client.

### La risposta alla domanda «uno studio legale, uso massivo»

    fino a 5 persone contemporanee ....... sì (mediana ~100 ms, nulla sopra 5 s)
    a 10 ................................. la mediana regge, la coda no
    a 20 ................................. degrada sotto il livello di 2 client

⚠️ **E il limite che potrebbe spiegare metà del calo**: questa macchina ha
**otto istanze Claude attive** che consumano CPU mentre il benchmark gira. Il
crollo a 20 client è **verosimilmente pessimistico**, e su una macchina dedicata
la curva si piegherebbe più tardi. **Non so di quanto**, e non lo stimo.
⚠️ 30 secondi per configurazione sono pochi per una coda: il p99 a 20 client è
calcolato su 338 operazioni, non su decine di migliaia.

## Limiti, dichiarati

⚠️ **Un solo worker**, una sola macchina, Windows, con otto istanze Claude
attive che consumano CPU — il regime non è pulito e i numeri sono
verosimilmente **pessimistici**.
⚠️ **90 secondi** restano pochi: 35 scritture bastano per una mediana, non per
una coda affidabile.
⚠️ Il rapporto del benchmark è **3 letture : 1 scrittura**; con un profilo
diverso il throughput cambia.
⚠️ **Non ho misurato il regime servizio** (`concurrency_shared_server.py`), che è
quello dell'utente vero. È la cella aperta più importante che lascio.

## E un difetto di prodotto che resta

Tutte queste scritture hanno `judged=False`, `layers=[]`,
`grounding_score=None` — nessuna `source`, quindi **il giudice non giudica**. Ma
**viene caricato lo stesso**, ~2 secondi. `local_grounding.py:175`
(`_ensure_scorer`) è lazy con lock e cache, quindi il caricamento parte perché
**qualcuno lo chiede** su una scrittura senza fonte: *chi*, resta da trovare.

🟢 E un dato positivo che nessuno aveva raccontato: il commento di quella stessa
riga dice che il caricamento costava **41 secondi il 05/08**. Oggi ne costa
**2**. È stato ottimizzato **venti volte**, e non è mai finito in nessun referto.
