# La vetrina è stata corretta quattordici volte in tre ore, e la quindicesima è già pronta

*ws3 (Galileo), 27/08 poco dopo mezzanotte — perimetro «il gate e ciò che dice».*

Non è un rimprovero a nessuno: metà di quelle correzioni sono mie. È un numero
che nessuno aveva contato e che riguarda una decisione aperta — se pubblicare
adesso.

## Il conteggio

`git log -- README.md`, commit del 26/08: **quattordici**, di cui uno è un
merge ⇒ **tredici correzioni sostanziali**, fra le **19:51 e le 23:08**. Tre ore
e diciassette minuti. Il file è di 738 righe.

| ora | cosa dice il messaggio di commit |
|---|---|
| 19:51 | la pagina descrive main, chi installa riceve il 22 luglio |
| 19:56 | il divario dei comandi è 18, non 16, e non si è ristretto |
| 20:10 | il limite che avevo dichiarato è stato chiuso, di due gradi |
| 20:40 | la mia nota di oggi diventerebbe la vetrina PyPI, e falsa |
| 20:46 | due mie frasi erano false da mezz'ora, e la misura c'era già |
| 20:51 | la vetrina prometteva l'astensione, e il gate ammette |
| 20:57 | la pagina diceva «nessuno l'ha eseguito», ed era stato eseguito |
| 21:14 | la riga che avevo scritto io un'ora fa era troppo severa |
| 21:46 | la contraddizione implicita passa 3/10 in italiano, e la vetrina lo dice |
| 21:56 | i documenti che ho appena linkato sono dell'8 agosto, e va detto perché |
| 22:57 | i numeri erano misurati su fonti brevi, e la riga non lo diceva |
| 23:06 | quattro correzioni giuste avevano prodotto un muro di caveat |
| 23:08 | la mia riga di stamattina generalizzava, e per due documenti è falsa |

E la **quattordicesima** è trovata e consegnata, non ancora applicata:
`README.md:22-23` dichiara «the other classes are **unmeasured** outside IT/EN
except in Thai», mentre due delle tre altre classi sono state misurate stasera
su cinque scritture. L'avevo scritta io stamattina; l'hanno resa falsa i miei
stessi banchi di stanotte.

## La classe che ricorre — e non è «disattenzione»

Almeno **cinque** delle quattordici hanno la stessa forma:

> **la vetrina dichiara un'assenza o un limite che i nostri stessi dati hanno
> già smentito.**

«nessuno l'ha eseguito» — era stato eseguito. «due mie frasi erano false da
mezz'ora, e la misura c'era già». «il limite che avevo dichiarato è stato
chiuso, di due gradi». E la mia di adesso, «unmeasured», su una cosa misurata.

Il meccanismo è strutturale, non caratteriale: **chi misura guarda il banco,
non la vetrina.** Una misura nuova non fa rumore sul testo che la contraddice,
perché sono due file diversi e nessuno li lega. Il difetto non nasce dallo
scrivere male: nasce dal **misurare bene, in fretta, e in otto.**

## Il gemello: curare produce il difetto opposto

Il commit delle 23:06 dice, da solo, la cosa più utile della giornata: «quattro
correzioni giuste avevano prodotto un muro di caveat». Ogni qualificazione era
esatta; **sommate**, rendevano la pagina illeggibile. È la stessa forma che ho
misurato io stasera sulla riga «8/10 IT, 9/10 EN»: un numero vero che, letto
com'è scritto, porta a una conclusione falsa.

⚖️ Da cui la distinzione che mi sono data e che vale per tutte: **una regola che
vieta di impilare caveat non vieta di correggere ciò che è falso.** Sono due
operazioni diverse — la prima AGGIUNGE, la seconda SOSTITUISCE. La riga che ho
consegnato stanotte è più corta di quella che rimpiazza.

## Cosa NON dice questo documento

⚠️ **Non dice che il ritmo stia accelerando o rallentando.** La tentazione c'è
(sei correzioni nella prima ora, tre in undici minuti alla fine), ma tre commit
ravvicinati possono essere **una** istanza che spezza un lavoro solo, e un
rapporto senza la finestra e l'istante non è una misura. Il conteggio e la
classe reggono; il trend, da qui, non lo so misurare e non lo affermo.

⚠️ **Non dice che la vetrina sia inaffidabile.** Il contrario, in un senso
preciso: tredici difetti su tredici sono stati trovati e corretti da noi, in
giornata, quasi sempre dall'istanza che li aveva introdotti. Nessuno è stato
trovato da fuori. La pagina di adesso è più vera di quella di stamattina.

## La quindicesima, trovata mezz'ora dopo — e dice PERCHÉ succede

Rileggendo la tabella di apertura ho trovato un terzo difetto, sempre mio,
sempre nella pagina che un lettore vede per prima:

> `| contradiction stated outright (**three falsehood classes**, IT and EN) | 0/10, 1/10, 2/10 |`

Il banco che produce quei numeri (`ws3-l-entita-a-batteria-l-ultima-delle-tre.py`)
li tiene in una tabella di **tre righe e tre colonne**:

    negazione            la fonte CONTRADDICE      0/10    0/10
    entita' sostituita   la fonte CONTRADDICE      1/10    2/10
    dettaglio aggiunto   la fonte TACE             8/10    9/10

Le classi sono tre, ma **solo due sono contraddizioni**: la terza *tace*, vale
8/10 e 9/10, e sta due righe più sotto nella stessa tabella di vetrina. La riga
annuncia tre classi e mostra i numeri di due. E quei tre numeri sono i valori
distinti di **quattro celle** — un lettore che vede tre classi e tre cifre le
mappa una a una, e conclude che esiste una terza classe di contraddizione con
esito 2/10.

⚖️ Ho verificato l'ipotesi che salverebbe la riga — che «entità sostituita»
conti come due classi, attributo e nome proprio, dato che il banco le tratta
come due forme. **È falsa, e la falsificano i numeri stessi**: quelle due forme
valgono 0/5 e 0/5, 1/5 e 2/5. Se fossero classi a sé, le cifre in vetrina
sarebbero su cinque, non su dieci.

✂️ Testo pronto, che **sostituisce** una riga con due e non aggiunge caveat:

    | outright contradiction — a negation        | **0/10 IT, 0/10 EN** |
    | outright contradiction — a swapped entity  | **1/10 IT, 2/10 EN** |

### 🔑 La causa, e vale oltre questa riga

Nel commit di quella riscrittura avevo scritto, in buona fede:

> «Verificato dopo la riscrittura che tutte e **sei le cifre** siano ancora nel
> file.»

Ho verificato che le **cifre** ci fossero. Non che l'**etichetta** sopra di esse
fosse ancora vera. Comprimendo tre righe in una ho tenuto i numeri e ho perso
la **colonna di mezzo** — *contraddice* contro *tace* — che è precisamente ciò
che rende quei numeri interpretabili.

> **Quando si comprime una tabella in una riga, sopravvivono i numeri e muoiono
> le colonne che li qualificano. E il controllo naturale — "ci sono ancora
> tutte le cifre?" — è cieco esattamente su ciò che è morto.**

È la stessa forma degli altri due difetti trovati stanotte: il tasso «8/10 IT,
9/10 EN» che aggrega due popolazioni opposte, e «unmeasured» rimasto su classi
ormai misurate. **Tre difetti diversi, una causa sola.** ⇒ Il presidio giusto
non è contare le cifre: è **rileggere la riga accanto alla tabella del banco
da cui viene**, colonne comprese.

## La sedicesima — stesso numero, due popolazioni diverse (27/08)

Il giorno dopo, applicando lo stesso presidio alle cifre più in basso nella
pagina, ne è uscita una quarta. Non è mia — la riga è di *Varco* (commit
«readme: la gap piu' grande era l'unica senza un numero», 25/08) — quindi la
consegno e non la tocco. Ma è **esattamente la stessa forma**, il che la rende
più interessante di un errore singolo.

`README.md:73-76`:

> «**25 of 48** such unsupported claims were admitted — IT 54.2%, EN 50.0%, and
> **8 of the 48 cases** get the OPPOSITE verdict in the two languages»

Il numero **48 compare due volte nella stessa frase con due significati
diversi**, e l'articolo determinativo di «the 48» dice al lettore che sono gli
stessi.

**Primo 48** — i claim non sostenuti. L'aritmetica lo conferma: 54,2% di 24 = 13,
50,0% di 24 = 12, totale **25 su 48** ✓. Sono 24 coppie IT/EN di falsi.

**Secondo 48** — le coppie totali del banco. Si legge nel codice, senza eseguirlo
(`banco-osservatore-il-tasso.py:239-247`):

    n_dis = 0
    for i in range(0, len(righe), 2):      # tutte le righe, a passo 2
        it, en = righe[i], righe[i + 1]
        if it[4] != en[4]:
            n_dis += 1
    print(f"totale casi con esito DIVERSO fra le due lingue: {n_dis}/{len(righe)//2}")

Il ciclo scorre **tutte** le righe e **non filtra i falsi**: con `len(righe)` = 96
(la riga 200 lo stampa: «n=96 casi»), il denominatore `len(righe)//2` vale 48 e
sono **le coppie totali, veri compresi**.

⇒ Due insiemi diversi con lo stesso cardinale. Il lettore conclude che 8 dei
claim *non sostenuti* divergono; il banco misura la divergenza su **tutta** la
popolazione, e quante delle 8 cadano sui falsi **non è scritto da nessuna
parte**. Se cadessero tutte lì il tasso sui falsi sarebbe 8/24 = 33%.

✂️ Testo pronto, sostituisce:

    «…and **8 of the 48 IT/EN pairs** — true and false alike — get the OPPOSITE
     verdict in the two languages, in both directions.»

⚠️ **Limite dichiarato**: non ho eseguito il banco, quindi **non so** come le 8
si distribuiscano fra veri e falsi. Ciò che è certo per lettura è solo questo:
la frase attribuisce le 8 a una popolazione che il banco non usa come
denominatore.

### Il presidio ha ora quattro casi, e uno era di un'altra istanza

Le prime tre erano mie e potevano essere una mia abitudine. La quarta è di
un'altra mano, sullo stesso file, con la stessa forma: **un numero corretto
sotto un'etichetta che nomina la popolazione sbagliata**. ⇒ Non è
disattenzione individuale, è ciò che succede quando **una tabella diventa una
frase**: la frase conserva la cifra e perde la definizione del denominatore.

📌 E un limite del metodo, trovato usandolo: `git grep` su una **cifra nuda**
trova omonimi. `54.2` compare anche in `benchmark/results/exp7b_concurrency_light.json`,
dove però è `"wall_s": 54.2` — secondi di wall-clock. **La cifra da sola non è
evidenza: serve il contesto.** L'avevo dato per scontato ieri; oggi mi ha
prodotto un falso allarme, ritirato prima di consegnarlo.

## La diciassettesima — «producibile, non leggibile» è una classe, non un caso

Applicando il presidio alle cifre più in basso (`README.md:635`, la riga degli
AUROC del giudice), **due su tre reggono e una no**. E stavolta ho cercato col
**contesto**, non con la cifra nuda — la lezione del falso allarme di ieri.

| cifra in vetrina | artefatto | esito |
|---|---|---|
| `0.971 sonnet-4 R10 on SNLI` | `benchmark/local_gate_eval.py:32,355` — «SNLI AUROC 0.971» | ✅ |
| `0.963 sonnet-5 re-run 2026-07-16` | `benchmark/results/fact_grounding_r10_sonnet5_2026-07-16.json:7` — `"auroc_faithful_vs_confab": 0.963` | ✅ **anche la data combacia** |
| `0.974 pooled multi-model` | — | 🔴 **non ricondotto** |

Il `0.974` compare in due posti, e **nessuno dei due è quello che la riga
promette**:

- `benchmark/qa_eval.py:80` → «l'abstention canary 0.897 → **0.974**» — è un
  *canary di astensione*, non un AUROC;
- `benchmark/results/exp3_routing_u0.json` → `"accuracy": 0.9744` — è
  *accuracy*, non AUROC.

**Omonimi.** È esattamente la trappola che avevo nominato ieri, e con la cifra
nuda avrei scritto «verificata».

E la macchina che produrrebbe il numero giusto **esiste**:
`benchmark/epistemic_harness.py:53` calcola `pooled_auroc`, ed è il concetto
esatto della riga. Ma:

    git grep -ln "pooled_auroc" | grep -v epistemic_harness   →  nulla
    file che contengano insieme "0.974" e "auroc"             →  nessuno

⇒ **Il `0.974 pooled multi-model` non è leggibile in nessun artefatto del
repo.** Non è inventato: è **producibile e non leggibile** — la stessa forma del
banco della zavorra trovata ieri (`9.6 → 35.9`, banco allora nemmeno
committato).

🔑 **Due occorrenze indipendenti fanno una classe, non un incidente.** E la
regola che avevo proposto ieri per un caso singolo vale come regola:

> **una cifra in vetrina dev'essere LEGGIBILE in un artefatto, non solo
> PRODUCIBILE da uno.** Un harness che la calcola e non la salva lascia in
> pagina un numero che nessun lettore esterno può rileggere.

⚠️ **Limiti**: `git grep` vede solo i file tracciati; e `0.9744` arrotondato
darebbe `0.974`, ma quello è *accuracy* su un altro esperimento, quindi non
salva la riga. Chi ha eseguito quel pooled ha il numero: basta salvare il json
accanto agli altri due e la riga torna intera.

## La domanda che resta aperta, ed è di Aurelio

Il criterio dato è «macchina appena uscita dal concessionario». Il conteggio
qui sopra non risponde sì o no: dice che **la vetrina è ancora in movimento**,
al ritmo di circa quattro correzioni all'ora, e che il meccanismo che le
produce — misure che corrono più veloci del testo — **non si è fermato**,
perché stanotte stiamo ancora misurando.

Le due letture sono entrambe difendibili e la scelta non è mia:

1. **Si pubblica** — i difetti li abbiamo trovati tutti noi, nessuno da fuori, e
   una pagina che si corregge tredici volte in un giorno è una pagina
   sorvegliata, non una pagina sbagliata.
2. **Si aspetta** che le misure si fermino, perché finché misuriamo produciamo
   righe false, e pubblicare fissa il testo nel momento in cui è più mobile —
   su PyPI la vetrina è la pagina del pacchetto, e resta lì.

📌 Una terza via, se serve una decisione a costo basso: **congelare le misure
sulla vetrina** (non i banchi — quelli continuino) per il tempo necessario a
fare un giro di rilettura, e pubblicare a valle di quello. Il costo è un'ora;
il beneficio è che la pagina non cambia mentre la si controlla.
