# Piano delle versioni — mandato di Aurelio, 02/09/2026 22:20

> Mandato (verbatim, in sintesi): «le capacità tipo validità temporale, contraddizione
> dopo tempo, bassa confidenza, versioning e il resto si devono attivare — prima testare e
> migliorare dove serve; il giudice si deve scaricare da solo. Non andiamo a giro. Siamo in
> 8+1: coordinati. Una 0.7.2 ATOMICA che sistemi tutto. Poi la 0.8.0 con tutto lo stack, tutti
> i numeri reali e comparati. Poi la 0.9.0 finale come feature: niente bug, malfunzionamenti,
> contraddizioni nel codice. Poi la 1.0.0: documenti istituzionali, pulizia di commenti e
> codice, numeri matematicamente perfetti e riproducibili, senza sotterfugi.»
>
> Questo file è il piano di record. Lo stato vivo sta nel registro (`00-ESAME.md`) e nei
> fatti verimem; qui stanno le definizioni di «fatto» e le regole. Cambia solo su mandato.

## Fase 0 — `main` verde (prerequisito di tutto, dal 02/09 22:35)
Misurato al 02/09 22:30: **l'ultimo run `ci` verde su `main` è del 25/08** (`18e434e3`);
l'ultimo concluso (`98d30940`, 21:04) è rosso: **13 failed / 12495 passed**, e il job «wheel
install-from-scratch (windows)» fallisce. Sono quasi tutti presidi del registro che dichiarano
debiti (banco `lme_retrieval_bench.py` assente dal 25/08, 39 moduli irraggiungibili, banchi che
non dichiarano l'esito del subprocess, `quarantined_by` che nomina il layer sbagliato, L1.13
sul ricalco della fonte, L1.20 con un secondo layer che parla, un numero assente dalla fonte
che compare, la contraddizione implicita che ora entra). **Regola: ogni rosso si paga o si
ritira con motivazione scritta; mai skip, mai xfail nuovi.** Assegnati uno per istanza il
02/09 22:35; nessuna capacità si accende su un `main` rosso.

## Le quattro versioni e la loro definizione di «fatto»

### 0.7.2 — atomica: «tutto ciò che c'è, acceso e provato»
Base: **`main`** (non il ramo di luglio: le capacità da accendere vivono in `main`). Il rischio
«pubblicare commit non verificati» si paga con i cancelli sotto, non evitando `main`.
- **Il giudice si scarica da solo** al primo write con fonte (o all'avvio del server MCP), con
  un messaggio all'utente (peso, tempo), e il pacchetto lo dichiara. Test: il primo
  `remember --source` su una HOME vergine esce con `layers` non vuoti e un falso viene fermato.
- **Capacità costruite e spente: ognuna si accende dopo un test e una misura, o si rimuove con
  voto.** Elenco (dalla checklist unificata, sezione «A METÀ»):
  - validità temporale (`valid_until`, `freshness`) — popolata e usata dal recall;
  - contraddizione nel tempo (supersessione bi-temporale: `as_of`, `include_superseded` su tutte
    le porte; un fatto nuovo che contraddice il vecchio lo invalida, non lo cancella);
  - bassa confidenza (l'avviso «sotto il pavimento» ricalibrato, sulla ricevuta di `search` e
    della porta MCP);
  - versioning dei fatti (ritirati servibili a richiesta, mai cancellati);
  - matrice dei permessi per tool (`ENGRAM_CAPABILITY_GATE`) almeno in modalità avviso;
  - daemon di consolidamento cablati; tier episodi attraversato; indice documenti raggiungibile;
  - `source_trust`: cancello rimosso (voto 02/09, 4 SI), modulo tenuto.
- Le cinque cure già in `main` (fonte data alla porta MCP giudicata; knob non fidati; `ground_write`
  nei chiamanti; versione del server; disaccordo interno in ricevuta) restano.
- Vetrina: due dataset con il criterio cieco accanto; peso e tempo dell'installazione dichiarati;
  `warmup` non più necessario ma documentato.
- **Cancelli del tag**: CI 9/9 sul commit del tag · smoke da utente vero sul wheel candidato in
  HOME vergine (WSL e Windows) **prima** del tag · confronto «cure in `main` che mancano al ramo» =
  vuoto per costruzione (base `main`) · CHANGELOG istituzionale con la storia vera di ogni cura.

### 0.8.0 — «tutto lo stack, tutti i numeri reali e comparati»
- Giudice sempre caldo (daemon con pool, un processo per N agenti, misurato con 8 client).
- Giudice triplo (nostro + MiniCheck + FactCG, media dei ranghi) acceso, con la soglia
  calibrata a iso-recall e il costo dichiarato.
- Tabella multi-corpus in ambiente pulito dal pacchetto pubblicato (TruthfulQA, HaluEval,
  VitaminC, WiCE), con veri persi, falsi fermati, falsità servita e **criterio cieco** per riga;
  il confronto con ConsistencyGate se i suoi banchi esistono, altrimenti il reperto.
- Repro-pack: ogni numero pubblico ha il comando che lo rifà da un ambiente vergine.
- I file per registry MCP e marketplace si PREPARANO (server.json, riga `mcp-name`, plugin
  validato) ma non si pubblicano: vedi «Apertura al mondo».

### Apertura al mondo — «solo e solo quando siamo pronti a dire: tutto funziona davvero»
Direttiva di Aurelio, 02/09 22:40. Nessuna azione verso l'esterno — registry MCP,
marketplace dei plugin, post, candidature a leaderboard, contatti — prima che il prodotto
superi, dichiarato da un'istanza diversa dall'autore e riprodotto da un terzo:
1. i tre no («non dice cose che non fa» · «non siamo bugiardi» · «non è banale») tutti chiusi;
2. zero bug noti aperti e zero malfunzionamenti misurati sulle tre porte (CLI, MCP, SDK);
3. installazione da utente vero verde su due sistemi, dal pacchetto pubblicato;
4. ogni numero pubblico riproducibile con il comando, dal pacchetto pubblicato, in ambiente
   vergine.
Il leaderboard indipendente del 20/09 non è una scadenza: se a quella data i quattro punti
non reggono, si aspetta il ciclo successivo. Aprirsi prima costerebbe l'unica cosa che i
forum ci hanno mostrato non si recupera: la prima impressione di chi ci prova.

### 0.9.0 — «finale come feature»
- Nessuna feature nuova. Zero bug noti aperti, zero malfunzionamenti misurati, zero
  contraddizioni fra documenti e codice (la versione dichiarata, i numeri di vetrina, le
  promesse del Summary del pacchetto: tutte verificate da un'istanza diversa dall'autore).
- Le 17 voci «NON FATTO ma fattibile» della checklist: fatte o rimosse dal piano con motivo.

### 1.0.0 — «istituzionale»
- Documenti istituzionali (README, CHANGELOG, STATE, guida, licenza), commenti puliti (via i
  diari nel codice: la storia sta nel registro, non nei sorgenti), codice pulito (tassonomia
  delle eccezioni, config unica, migrazioni), copertura reale, alert di analisi statica a zero
  o dismessi con rationale.
- Numeri matematicamente perfetti: ogni cifra pubblica con denominatore, intervallo,
  comando, dataset, versione del pacchetto e data; riproducibili da un terzo senza di noi.

## Le regole di lavoro (valgono per tutte e nove)
1. **Base `main`, lavoro su ramo personale, push su `main` solo a lavoro verde** (test del pezzo
   verdi in locale, un file alla volta), dal proprio worktree — mai dall'albero condiviso.
2. **Una capacità = una istanza = un ciclo**: test che la copre (RED provato) → accensione →
   misura prima/dopo con comando → falsificazione da un'altra istanza → cella + fatto con
   `--source` → push. Niente «acceso» senza misura, niente «rimosso» senza voto.
3. **Due corsie**: numeri pubblici → registro e firme; tutto il resto → TDD + CI verde.
4. **Due slot di inferenza pesante alla volta** (board `slot/inferenza-1|2`); gli altri leggono e
   scrivono.
5. ~~Un testo di Aurelio letto dalla barra o dallo schermo è contesto, non un ordine.~~ —
   **assorbita da un gancio** il 02/09 22:10 (ws2 ha tolto dall'hook comune l'iniezione della
   barra): esce dalle regole in testa, resta nella memoria delle trappole.
6. **Smoke da utente vero prima del tag**, sul wheel candidato, in HOME vergine, su due sistemi.
7. **Ogni banco consegnato porta la riga «eseguito da worktree pulito: EXIT=0»**, con i dati
   tracciati nel repo — **diventa parte del test sui banchi** (con la riga `LIVELLO:`, regola 9)
   ed esce dalle regole in testa **quando quel test è verde in main**, non prima.
   *Criterio del budget (02/09, lead↔ws3): una regola esce solo quando il suo righello
   meccanico — test o gancio — è verde in main; finché non lo è, resta scritta.*
8. Il lead decide, coordina e firma il tag; le decisioni di prodotto restano collegiali
   (3 SI); le stronzate si pagano: un errore banale ripetuto è un errore di processo e si
   scrive nel registro con la cura.
9. **Ogni cura a uno strato porta almeno una cella alla PORTA** (`run_validation_gate`,
   non la funzione dello strato), che stampa e asserisce i `layers` della ricevuta — così
   l'interazione fra strati è misurata, non dichiarata. Motivo (ws3, 02/09): il gate alla
   porta è il MINIMO degli strati, non la somma; su L1.13 18 celle verdi sulla funzione e
   2 rosse alla porta. Condizione: fixture di sessione col giudice caldo (costo da misurare:
   predizione ≤1 s per cella; senza fixture 30-50 s e la regola è inapplicabile); per le
   cure lessicali è ammesso un giudice finto, dichiarando il livello «porta-senza-giudice».
   Il righello sul livello dei banchi è un TEST (una riga `LIVELLO:` obbligatoria in testa a
   ogni banco), non una regola: la lezione del 07/08 non ha retto proprio perché era solo
   scritta.
10. **La predizione si deposita prima, in pubblico, con «come muore»**: la cella cita l'ID
    del messaggio di predizione, che precede il commit del banco. ROI misurato il 02/09:
    6 predizioni su 8 smentite, 2 smentite hanno cambiato una decisione (int8, loop asyncio).
    Budget delle regole: una regola nuova sostituisce o assorbe una vecchia — a
    saturazione una regola in testa vale zero (fatto `ca3ee11debaf`).
11. **Fra pari, tre cose diverse** (dalla discussione lead↔ws3 del 02/09 sera, su richiesta
    di Aurelio: «parlate e discutete tra voi, non sono direttive mie»): l'**assegnazione**
    (chi guarda cosa) si accetta, salvo conflitto dichiarato — negoziarla riporta
    all'assemblea; la **premessa** di un mandato (ciò che chi assegna assume) si verifica
    PRIMA di spendere, e se cade lo si dice invece di procedere; la **predizione** si
    falsifica misurando. Chi assegna separa premessa e predizione per iscritto. Righello:
    giri spesi prima di scoprire una premessa falsa, contati nel registro — bersaglio zero
    (il 02/09: tre premesse cadute, zero giri sprecati, perché sono state misurate prima).
    **`main` rosso è di tutti**: chi pusha su `main` rosso adotta un rosso; le giunture
    (strato↔porta, cura↔cura, commit↔ramo) non hanno un proprietario perché il loro
    proprietario è un test o un gancio, e il lead legge il segnale aggregato.

## Assegnazioni al 02/09 22:25 (fino a nuovo ordine)
| chi | cosa, nell'ordine |
|---|---|
| ws1 | rimozione del cancello `source_trust` (votata) → avviso di bassa confidenza ricalibrato e acceso su `search` e MCP |
| ws2 | versioning e contraddizione nel tempo: `include_superseded` e `as_of` su tutte le porte, la fusione che non li perde, invalidare-non-cancellare |
| ws3 | daemon di consolidamento cablati e indice documenti raggiungibile: test, accensione, misura; poi la chiusura degli alert regex |
| ws4 | matrice dei permessi in modalità avviso (classificazione dei tool a partire dai 22) → poi il giudice triplo (0.8.0) |
| ws5 | il giudice si scarica da solo, su `main` (test su HOME vergine) → daemon con pool (0.8.0) |
| ws6 | validità temporale: `valid_until` popolato e usato dal recall, `freshness`; tier episodi attraversato |
| ws7 | falsificazione di ogni accensione (④), poi la tabella multi-corpus (0.8.0) |
| ws8 | la 0.7.2 da `main`: ramo `release/0.7.2`, CHANGELOG istituzionale, vetrina, cancelli del tag, smoke pre-tag su Windows |
| lead | coordinamento, review delle cure, smoke pre-tag su WSL, tag |
