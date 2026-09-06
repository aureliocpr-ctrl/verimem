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

## Le regole di lavoro (valgono per tutte e nove) — ristrutturate il 03/09 su mandato di Aurelio

**Principio (Aurelio, 03/09: «si commettono sempre gli errori su pattern identici, si mette
la mano sul fuoco nonostante ha bruciato già 50 volte»)**: una regola scritta e riletta non
ha mai retto da sola. Qui ogni regola porta il suo **righello** — un test, un gancio, un
comando, o un conteggio nel registro — e la data dell'incidente che l'ha prodotta. Una
regola senza righello compete per i posti in testa (criterio del budget, D-2) e a
saturazione vale zero (fatto `ca3ee11debaf`). Le regole assorbite da un gancio o da un
test escono dalla lista e restano nella memoria delle trappole.

### A. Misurare — come si prova una cosa
| # | regola | righello | nata da |
|---|---|---|---|
| A-1 | **La predizione si deposita prima, in pubblico, con «come muore»**; la cella cita l'ID del messaggio, che precede il commit del banco. | l'ID nella cella; ROI contato nel registro (02/09: 6 predizioni su 8 smentite, 2 hanno cambiato una decisione) | 02/09 |
| A-2 | **Ogni cura a uno strato porta almeno una cella alla PORTA** (`run_validation_gate`, non la funzione dello strato), che stampa e asserisce i `layers`; riga `LIVELLO:` obbligatoria in testa a ogni banco. Il gate alla porta è il MINIMO degli strati, non la somma. Fixture di sessione col giudice caldo (misurato 03/09 da ws3: freddo 30,5 s, caldo 0,3-0,5 s, venti celle ≈ 50 s). | il test sui banchi che pretende `LIVELLO:` | ws3 02/09 (L1.13: 18 verdi sulla funzione, 2 rosse alla porta) |
| A-3 | **La popolazione da misurare è quella che la garanzia PROTEGGEVA, non quella che la cura CAMBIA.** Una cura che toglie o rilassa una trattenuta rilancia i banchi che quella trattenuta faceva passare. | la lista dei banchi da rilanciare, nel registro accanto alla cura | ws3 03/09: `c857752e` misurava «marco per errore delle self-claim?» su 13.662 fatti e liberava «La funzionalità funziona ed è verificata» (15 su 17.428) |
| A-4 | **Ogni dichiarazione di stato porta l'output grezzo del comando NELLO STESSO messaggio, oppure la parola NON VERIFICATO.** «X esiste», «X non capita mai», «X è esposto su tutte le porte», «funziona»: senza output è un'ipotesi e chi legge la tratta da ipotesi. Un'assenza si prova ESEGUENDO la porta, non contando le occorrenze di un nome. | chi legge risponde «output?»; le dichiarazioni smentite da un pari si contano nel registro (03/09 sera: tre del lead in un'ora, tutte smentite in 20 min) | Aurelio 03/09; ws1 03/09 («la CLI non avvisa mai», e avvisava) |
| A-5 | **Ogni banco stampa `verimem.__file__` nella prima riga** e la cella la riporta: uno script lanciato da un worktree o dallo scratchpad può importare l'albero di qualcun altro. | la riga nella cella; righello: `python -c "import verimem; print(verimem.__file__)"` con lo stesso cwd e la stessa forma del banco | ws2 03/09 (un'ora di rosso su un codice in cui la porta non esisteva) |
| A-6 | **Un limite dichiarato è un debito, e lo paga qualcun altro**: «non lo so» scritto con precisione dice dove guardare; riempirlo con l'ipotesi plausibile chiude la domanda. Controllo positivo sempre: un'interrogazione vuota si prova su un caso che DEVE rispondere. | la colonna del controllo positivo nel banco (ws6 03/09: «se anche le scritture sono zero, il numero dice non ho guardato») | 10/08; ws6 03/09 (ottavo e nono falso allarme evitati) |

### B. `main` e CI — come si consegna
| # | regola | righello | nata da |
|---|---|---|---|
| B-1 | **Base `main`, lavoro su ramo personale dal proprio worktree, push su `main` solo a lavoro verde** (test del pezzo verdi in locale, un file alla volta). Mai dall'albero condiviso, che resta su `main` pulito. | gancio `.githooks/pre-push` (blocca il push su main dall'albero principale su ramo ≠ main) | 02/09 21:18 (`71034ec1`), 03/09 18:50 |
| B-2 | **Una capacità = una istanza = un ciclo**: test che la copre (RED provato) → accensione → misura prima/dopo con comando → falsificazione da un'altra istanza → cella + fatto con `--source` → push. Niente «acceso» senza misura, niente «rimosso» senza voto. | la cella con RED/GREEN e l'ID della falsificazione | 02/09 |
| B-3 | **Due corsie**: numeri pubblici → registro e firme; tutto il resto → TDD + CI verde. | — | 02/09 |
| B-4 | **Silenzio sui push a `main` deciso dallo STATO DEL RUN, non dall'orologio**: i push sono liberi finché il run del commit più recente è ancora `queued` (un push lo sostituisce, costo zero) e VIETATI da quando è `in_progress` fino alla sua conclusione; il lead annuncia apertura e chiusura sul canale e le cure pronte entrano in blocco nella finestra. `cancel-in-progress: false` protegge solo il run che gira: un run pendente viene sostituito. **Un solo cancellatore (il lead), e mai un run in corso**: i queued superati si sostituiscono, i run in corso arrivano in fondo (03/09 sera: tre `ci` in corso cancellati dal lead e zero verdetti completi da nove giorni; `security` ha gruppo per ref e viene sostituito dalla concurrency, `ci` ha gruppo per sha ed è solo intasato). Cura strutturale in arrivo: un run superato esce da solo in pochi secondi (primo step di ci.yml, ws8). | `gh run list --branch main --workflow ci.yml --limit 3` letto PRIMA di ogni push; i run cancellati a zero job contati nel registro | ci.yml 10/08 e 12/08 (26 run cancellati su 40); 03/09 sera (8 run sostituiti in 20 minuti, zero verdetti) |
| B-5 | **Smoke da utente vero PRIMA del tag**, sul wheel candidato, in HOME vergine, su due sistemi (Windows e WSL); il registro dello smoke ha per ogni campo nome, esito leggibile a macchina e data, e si scrive DOPO aver eseguito, mai prima. | `scripts/cancelli_del_tag.py` (EXIT 0/1/2) + il test del registro (ws8 03/09: un registro con i campi ma senza esito → NO) | 02/09 (0.7.1 taggata con il moat spento); ws8 03/09 |
| B-6 | **`main` rosso è di tutti**: chi pusha su `main` rosso adotta un rosso; ogni rosso si paga o si ritira con motivazione scritta, mai skip, mai xfail nuovi — una regressione della promessa del prodotto sta su `main` come cella ROSSA, non come xfail (03/09, c857752e). Le giunture (strato↔porta, cura↔cura, commit↔ramo) non hanno un proprietario: il loro proprietario è un test o un gancio, e il lead legge il segnale aggregato. | i FAILED letti da TUTTI i job del run, non da uno (03/09: rossi solo-windows invisibili da ubuntu) | 02/09-03/09 (fase 0: 13 rossi non letti per 8 giorni) |
| B-6 bis | chi cura un difetto cerca PRIMA della finestra gli `xfail` nei test che lo nominano (`grep -rn xfail tests/ | grep <modulo|campo|layer>`): una cella rossa dichiarata che la cura fa passare è un verde da promuovere nel pezzo, non un rosso da scoprire in CI (run 34002525998: XPASS(strict) su 5 gambe dopo la cura ④). E il diff di un ramo si legge dal merge-base (`git diff $(git merge-base origin/main <ramo>)..<ramo>`), mai da `origin/main..<ramo>`: su una base vecchia il secondo mostra la cancellazione di tutto ciò che è entrato dopo. |
| B-7 | ~~Niente identificativi di sessione (`ws1`-`ws8`) dentro `verimem/`, nemmeno nei commenti: il pacchetto si spedisce.~~ — **assorbita dal gancio** pre-commit (`publish.yml:218`); esce dalle regole in testa. | gancio | 03/09 19:38 |

### C. Parlare — come si comunica fra istanze
| # | regola | righello | nata da |
|---|---|---|---|
| C-1 | **Il canale A2A è la sede** di rapporti, misure, verdetti e voti; `send_message` al lead SOLO per una riga in due casi: «sono ferma senza riarmo» o un'urgenza che non può aspettare il tick (10 min). Mai rapporti, mai tabelle: Aurelio li vede nella chat del lead. | il conteggio dei `send_message` non urgenti nel registro | Aurelio 03/09 19:43 («chi te li sta mandando, e come mai») |
| C-2 | **Fra pari, tre cose diverse**: l'**assegnazione** si accetta, salvo conflitto dichiarato; la **premessa** di un mandato si verifica PRIMA di spendere, e se cade lo si dice; la **predizione** si falsifica misurando. Chi assegna separa premessa e predizione per iscritto. Un verdetto «regge la cura, non regge la dichiarazione» è un verdetto legittimo e va accolto per iscritto da chi ha dichiarato. | giri spesi prima di scoprire una premessa falsa, contati nel registro (bersaglio zero) | lead↔ws3 02/09; ws7↔lead 03/09 (D1 e D2 ritirate) |
| C-3 | **Due slot di inferenza pesante alla volta** (board `slot/inferenza-1|2`), prenotati con nome, ora, banco e DURATA ATTESA, rilasciati a fine banco con l'esito; una prenotazione scaduta si può prendere dichiarandolo. `verimem save --source` è inferenza (carica il giudice): si accoda, non si fa mentre un banco gira. | il valore sul board, con la scadenza | 02/09; ws5 03/09 (una prenotazione di 20 ore rilasciata solo per attenzione di un'altra) |
| C-4 | **Chi si ferma senza riarmare il loop lo scrive**; il lead controlla le otto a ogni tick e sveglia chi è fermo da più di 10 minuti. Il testo per Aurelio è l'ULTIMA cosa del turno. | `list_sessions` nel tick del lead | 02/09 (quattro risposte perse); 03/09 |

### D. Decidere
| # | regola | righello | nata da |
|---|---|---|---|
| D-1 | **Il lead decide, coordina e firma il tag; le decisioni di prodotto restano collegiali (3 SÌ)**; le stronzate si pagano: un errore banale ripetuto è un errore di processo e si scrive nel registro con la cura. | la cella dell'errore ripetuto | Aurelio 02/09 |
| D-2 | **Criterio del budget**: una regola in testa esce solo quando il suo righello meccanico — test o gancio — è verde in `main`; una regola che diventa test o gancio costa zero; una che non può diventarlo compete per i posti e va pesata contro chi c'è già. Una regola nuova sostituisce o assorbe una vecchia. | questa tabella: la colonna «righello» non può essere vuota per una regola in testa | lead↔ws3 02/09-03/09 |
| D-3 | **Non si butta: si prova il limite.** Zero righe non provano che una capacità non funzioni: provano che non l'abbiamo accesa. Nella scelta togliere/alimentare la risposta di default è PROVARE, anche contro chi ha già votato per togliere. | la misura prima del voto di rimozione (ws5 03/09: «il pool a 2 non è "non ripetibile", non è mai stato ripetuto») | Aurelio 02/09 |

**Uscite dalle regole in testa** (assorbite): la lettura della barra (gancio, 02/09 22:10); «eseguito da worktree pulito: EXIT=0» (diventa parte del test sui banchi con `LIVELLO:`, A-2); le sigle nel pacchetto (gancio, B-7).

## Assegnazioni al 03/09 20:00 (fino a nuovo ordine; le precedenti del 02/09 22:25 restano nella storia git)
| chi | cosa, nell'ordine |
|---|---|
| ws1 | presidio «tre porte, una risposta» (ramo `ws1/avviso-ricalibrato`, `32ff3f12`) → cura della terza forma (SDK e MCP dichiarano l'ORIGINE della soglia come la CLI) → push nella finestra |
| ws2 | `f3393c6f` (quarantined_by nomina chi ha trattenuto) su `main` nella finestra → il reperto «fatto a 99,95 quarantinato da `L3-coexistence`» (3fec40e1ab53) → versioning e contraddizione nel tempo (`ws2/versioning-m3`) |
| ws3 | cella ROSSA su `main` per `c857752e` (le self-claim impersonali entrano) → banco «contraddizione + frase estranea» esteso a 30 coppie con/senza zavorra (slot) → daemon di consolidamento e indice documenti |
| ws4 | i 23 tool del bypass classificati e portati nel registro (riga dell'handler come prova) → lista bypass DERIVATA dal registro → il giudice triplo NON si rifà (W7-132 è la misura di record) |
| ws5 | daemon con pool, P1 depositata: tre bracci ripetuti due volte, RSS e latenza prima scrittura → il giudice che si scarica da solo è su `main` (b5f8f2d5) |
| ws6 | porta CLI `save --valid-until` + riga «N fatti esclusi perché scaduti» nel recall di tutte e tre le porte + README; niente deduzione automatica e niente `valid_from` nella 0.7.x → conta delle porte che raggiungono il tier episodi, poi voto |
| ws7 | cura di `c857752e` (autrice della cura votata) appena chiude WiCE, misurata sulla popolazione PROTETTA (le 15 liberate tornano fermate, le 132 DOMAIN restano) → ④ su `93bc28f6` (advisory_eligible) |
| ws8 | voto (A): il tag locale `v0.7.6` si cancella una volta al momento del tag; CHANGELOG `[0.7.6]` con il numero pubblico come RANGE (15,9-35,7 su quattro corpora, LANT-171); registro dello smoke con esito e data DOPO lo smoke Windows |
| lead | finestra dei push e lettura dei run (B-4); `93bc28f6` su `main` nella finestra; review delle cure; smoke WSL; tag; regole ristrutturate (questa sezione) |
