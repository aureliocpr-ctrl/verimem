# Riesecuzioni fan-out dei banchi «rifallo con:» — 30/08 ~20:35-20:53
> 16 comandi estratti dalle celle di 00-ESAME.md e rieseguiti in parallelo da
> verificatori READ-only indipendenti (nessuna scrittura, nessun git).
> Ogni report: COMANDO / EXIT reale / SINTESI (output del banco) / GIUDIZIO
> del verificatore / NOTA. Le firme che citano queste riesecuzioni scrivano:
> «2ª esecuzione: fan-out 30/08, report N in questo file».
>
> QUADRO (di lead-audit): 10 VERDI riusabili per le firme · 1 ROSSO BENIGNO
> ATTESO (apostrofo-alla-porta: la cura `51eb3022` in main ha svuotato la
> popolazione del banco che misurava il difetto — il gemello
> quanto-pesa-l-apostrofo conferma 0/977 nello stesso run; la cella W7-73 si
> firma sul run PRE-cura, con questa nota) · 5 FAIL-CLOSED su una
> precondizione comune (grounding_score assente al primo caso nei banchi
> leva/accento del giudice: report 9, 10, 11, 12, 16), MENTRE i report 1-2
> ottengono punteggi alla porta nello stesso regime ⇒ la differenza sta
> nella GIUNTURA banco→giudice, e quelle celle NON si firmano finché la
> precondizione non è spiegata. Osservazione trasversale: in tutti i run
> compare il RuntimeWarning di `anti_confab_gate.py:2400` (cut locale 99.6
> inutilizzabile → fallback cut CE 40): i banchi girano sul cut 40.

---

## Report 1

COMANDO: python -u docs/stato-reale/banchi/quanto-costa-allargare-l-elenco-di-L1-13.py
EXIT: 0
SINTESI:
```
     -- CONTROLLO (2): 0 casi erano gia' fermi PRIMA ⇒ 6 utili
     COSTO: 6 falsi allarmi nuovi su 6 casi utili

  == LA RIGA CHE CONTA
     🔴 IL PREZZO C'E': 6 self-claim fermati, ma 6
     fatti VERI con fonte fermati su 6 ⇒ rapporto 1.0 a 1.
     ⇒ Chi allarga l'elenco compra copertura e paga in falsi
     allarmi, che e' il verso che arriva all'utente.

  == 🔬 I TRE CHE CADONO: e' la FLESSIONE? (predizione falsificabile)
     stessa fonte, stesso senso — cambia SOLO la flessione
     ferma   [L1-domain-precision-observe,L1.13] La perizia e' stata ultimata dal geometra incaricato
     ferma   [L1-domain-precision-observe,L1.13] La spedizione e' stata evasa dal centro logistico.
     ferma   [L1-domain-precision-observe,L1.13] La pratica e' stata espletata dall'ufficio tecnico.

     🪞 CADUTA: fermano anche con la flessione allineata ⇒ la
     mia spiegazione e' sbagliata e il costo ha un'altra causa.

  ⚠️ COSA NON DICE: sei radici scelte da me fra quelle misurate in
  `W7-65`, sei self-claim e sei fatti con fonte, tutti COSTRUITI da
  me. Il costo sul corpus vero e' un'altra misura e non e' questa.
```
GIUDIZIO: VERDE (exit 0; i numeri stampati sostengono il verdetto: popolazione P 6/6 guadagno, popolazione N 6/6 falsi allarmi, controlli 1 e 2 passati, rapporto 1.0 a 1 coerente; la sezione 🪞 CADUTA è la falsificazione dichiarata della sotto-ipotesi sulla flessione, prevista dal banco, non una contraddizione del verdetto)
NOTA: a metà run compare un RuntimeWarning di regime da `verimem/anti_confab_gate.py:2400` — «local grounding judge ships an unusable cut (99.6 > 90, a val-set F1 artifact) — using the validated local CE moat cut 40» — quindi il banco gira col cut 40, non col cut spedito; inoltre il banco stesso dichiara che i 12 casi sono costruiti dall'autore (il costo sul corpus vero non è questa misura). Warning triton/flop_counter innocuo.

---

## Report 2

COMANDO: python -u docs/stato-reale/banchi/il-costo-sul-corpus-vero-di-allargare-l-elenco.py
EXIT: 0
SINTESI:
```
  == IL COSTO: 26 su 5894 fatti utili  (0.44%)
     di cui MORFOLOGICI (radice nella fonte, parola no): 0 su 26  (0%)
     fonti che sembrano OUTPUT/evidenza grezza: 21 su 26
     fonti che NON contengono la radice del claim : 26 su 26
  == LIMITE (a) CORRETTO: 12 dei nuovi, ALLA PORTA
     porta       grounding  claim
     downgrade   99.8       Il collaudo del pacchetto pubblicato eseguito 
     [... 12 righe "downgrade", grounding 80.1–100.0 ...]
     alla porta ne ferma 12 su 12  ⇒ fattore 1.00
     stima del costo ALLA PORTA: 26 su 5894  (0.44%)
  ⚠️ COSA NON DICE: limite (b) in piedi — `grounding_span` e' un
  FRAMMENTO, e un participio fuori dal frammento fa contare un falso
  allarme che forse non c'e'. ⇒ questi numeri sono un LIMITE
  SUPERIORE. E le sei radici restano scelte da me.
```
GIUDIZIO: VERDE (verdetto coerente coi propri numeri: costo 0.44% dichiarato come limite superiore; W7-66 falsificata sul corpus vero 0/26 morfologici; alla porta 12/12 downgrade, fattore 1.00)
NOTA: il banco LEGGE il DB di produzione `C:\Users\aurel\.engram\semantic\semantic.db` (popolazione 5948, sola lettura — è il suo scopo "corpus vero"); a runtime emette `RuntimeWarning` da `verimem/anti_confab_gate.py:2400` (cut del judge locale 99.6 inutilizzabile, usa il cut CE validato 40) e testa alla porta solo 12 dei 26 nuovi, estrapolando il fattore 1.00 all'intero costo.

---

## Report 3

COMANDO: python -u docs/stato-reale/banchi/i-509-che-passano-senza-screen-letti-nel-merito.py
EXIT: 0
SINTESI:
```
  [23] da7c9f620ea2  L1.13
       topic: project/lingue-ar-ru
       La tesi di ws1 sul mandato lingue dice che il confine non passa fra le lingue ma fra lo strato che usa il modello e quello che usa le regex, e ws1 ha chiuso ZH e JA con moat 6/6 a 99.86 e 99.83 e recall 6/6.

  [24] e2f60d290347  L1.13
       topic: brainstorming/25-08
       La contraddizione senza numeri aperto contro chiuso viene quarantinata con 1.0 in italiano e 1.5 in inglese.

  ⚠️ COSA NON DICE: questo banco non giudica nulla — stampa. La
  classificazione la faccio io leggendo, e va scritta nella cella
  con il criterio dichiarato, altrimenti e' un'impressione.
```
GIUDIZIO: VERDE (esce 0, stampa la popolazione, il campione di 24 casi e dichiara esplicitamente il proprio perimetro; nessuna contraddizione interna)
NOTA: I numeri di oggi divergono dal nome del file: testata del run = «narrative vivi: 9028 · passano il pre-filtro: 1681 (18.6%) · accendono un layer: 389 · NON checkpoint: 352» — non 509; il banco per design NON emette PASS/FAIL (lo dice lui stesso in coda), quindi chi firma non può citarlo come verdetto ma solo come campione da leggere nel merito.

---

## Report 4

COMANDO: python -u docs/stato-reale/banchi/l-eccezione-dichiarata-e-quasi-tutto-il-traffico.py
EXIT: 0
SINTESI:
```
  == LA RIGA CHE CONTA
     ⇒ narrative 65.5%, di cui accenderebbero 6.2%. Non forzo una tesi su questi numeri.

  == I 551: sono CHECKPOINT (il caso previsto) o altro?
     riconosciuti come CHECKPOINT (marca nei primi 120 char): 41 su 558  (7.3%)
     gli ALTRI 480, per primo segmento di topic:
       project                 365
       lessons                 44
       guardia                 31
       master                  13
       [...4 righe minori omesse: handoff 9, verimem 7, brainstorming 4, lab 3]

  ⚠️ COSA NON DICE: «avrebbe acceso un layer» NON e' «e' falso» —
  `L1` e' un rilevatore lessicale e i suoi falsi allarmi sono
  misurati altrove. E `_l1_warnings` e' una funzione privata: la
  chiamo direttamente, quindi questo e' il livello DETECTOR, non la
  porta. Il numero e' un LIMITE SUPERIORE del silenzio.
EXIT=0
```
GIUDIZIO: VERDE (verdetto coerente con i propri controlli: popolazione 13775 vivi, narrative 9028/65.5%, 558/9028=6.2% accenderebbero L1, split per era 6.9% pre / 3.0% post 2026-08-21; limiti auto-dichiarati; exit 0)
NOTA: durata ~8 min (oltre i 5 dichiarati: lasciato finire perché in progresso visibile, nessun hang). Numeri cambiati rispetto al testo fisso del banco: il titolo «I 551» è hardcoded (riga 186 del sorgente) ma la misura odierna è 558; inoltre 41+480=521≠558 nella scomposizione ALTRI (37 id non spiegati a livello output). Il verdetto principale non è toccato; livello dichiarato DETECTOR (chiama la privata `_l1_warnings`), non la porta. Nessun file modificato, nessun git, nessuno store di produzione toccato.

---

## Report 5

COMANDO: python -u docs/stato-reale/banchi/quanto-pesa-l-apostrofo-nel-corpus.py
EXIT: 0
SINTESI:
  == ② QUANTI PERDONO IL SOGGETTO PER COLPA DELL'APOSTROFO
     soggetto vuoto con `e'` e RISOLTO con `è`: 0 su 977  (0.0%)
     ⇒ sul corpus intero: 0.00% dei 13795 fatti vivi
     gli altri 977 hanno il soggetto irrisolvibile per un'ALTRA ragione
     (piu' di sei token, un punto prima del verbo, un pronome):
     ⇒ **contare solo ① avrebbe detto un numero piu' grande del difetto.**

  == ③ CAMPIONE di 24: quanti diventano DOMAIN con `è`?
     classificati DOMAIN solo con `è`: 0 su 0

  == LA RIGA CHE CONTA
     🪞 Nessuno perde il soggetto per l'apostrofo: su questo
     corpus il difetto di `W7-72` non si realizza, e lo dico
     con la stessa forza con cui l'ho annunciato.

  ⚠️ COSA NON DICE: `DOMAIN` e' una condizione NECESSARIA della
  carve-out, non sufficiente — serve anche che `L1` si accenda e che
  nessun altro veto intervenga. Il costo VERO alla porta e' un'altra
  misura. E il criterio `\be'(?=\s)` e' mio: cattura il verbo, ma
  anche un `e'` dentro una citazione o un blocco di codice.
GIUDIZIO: VERDE
NOTA: Popolazione misurata 13795 fatti vivi (977 con `e'`, 357 con `è`); verdetto internamente coerente (0/977 risolti, quindi ③ correttamente vuoto), ma l'intestazione «CAMPIONE di 24» è fissa mentre il denominatore reale è 0 su 0 — cosmetico, non contraddice il verdetto; il banco stesso dichiara il limite del criterio regex `\be'(?=\s)` (cattura anche citazioni/codice) e che DOMAIN è condizione necessaria, non sufficiente.

---

## Report 6

COMANDO: python -u docs/stato-reale/banchi/quale-regola-fa-cadere-un-verbale-nel-classificatore.py
EXIT: 0
SINTESI:
```
  -- CONTROLLO (2): i self-claim devono dare NO
     no      Ho completato la migrazione e tutti i test passano.
     no      I have finished the refactoring and the suite is green.
     retto

     con `e'`  : 4 su 4
     con `è`   : 4 su 4
     forma ATTIVA (usa `ha`, in lista): 3 su 3

  == LA RIGA CHE CONTA
     🪞 L'apostrofo NON spiega nulla: i due modi di scrivere danno
     lo stesso esito (4). La causa e' un'altra, e allora il
     confronto di lingua qui sopra torna in gioco.

  ⚠️ COSA NON DICE: otto verbali, quattro coppie e tre frasi attive
  COSTRUITI da me. E soprattutto: **il confronto IT/EN qui sopra NON
  E' PIU' VALIDO** — variava lingua e apostrofo insieme. Per un
  confronto di lingua vero servirebbero frasi italiane con `è`
  accentata contro le inglesi, e quel banco non l'ho fatto.
```
GIUDIZIO: VERDE (exit 0; verdetto interno coerente: IT 7/8 DOMAIN con 1 caduta su «4 cifre nel head», EN 3/4 con 1 «soggetto NON risolvibile», self-claim 2/2 respinti «retto», isolamento apostrofo 4/4 vs 4/4 senza contraddizioni)
NOTA: il banco stesso dichiara due limiti che chi firma deve riportare: dataset interamente costruito dall'autore (8 verbali + 4 coppie + 3 attive) e confronto IT/EN NON valido perché lingua e apostrofo variavano insieme — la conclusione firmabile è solo «l'apostrofo non è la causa», non un verdetto di lingua. (La riga «tee: Permission denied» era del mio wrapper di cattura, non del banco.)

---

## Report 7

COMANDO: python -u docs/stato-reale/banchi/se-l-eccezione-non-ci-fosse-cosa-fermerebbe-la-porta.py
EXIT: 0
SINTESI:
```
  == LA RIGA CHE CONTA
     senza l'eccezione la porta ne fermerebbe 21 su 24
     🔴 E `W7-70` ha gia' letto che cosa sono: **11 resoconti di
     lavoro, 13 misure verificabili, ZERO self-claim nudi**.
     ⇒ Senza l'eccezione, questi sarebbero **falsi allarmi su
     lavoro vero** — e l'eccezione non e' un buco: e' cio' che
     li evita. **La compensazione e' misurata, non supposta.**
     downgrade  L1.13                     Engram 2026-06-15: MOSSA 1 (flip PPR fusion 
     downgrade  L1.13                     TOOL AUDIT CYCLE COMPLETE FINAL 2026-05-26 2
     downgrade  L1.13                     WS2.1b CHIUSO - A/B 3 BRACCI SU LOCOMO, E IL
     downgrade  L1.15                     Le tre skill in cima al briefing di verimem 
     downgrade  L1.13                     La funzione history restituisce lo stesso tr

  ⚠️ COSA NON DICE: 24 fatti, gli stessi di `W7-70` e quindi lo
  stesso campione (uno ogni 14) — non e' una stima sul corpus. E il
  controfattuale cambia UN parametro: non dice che cosa sarebbe
  successo se quei fatti fossero stati SCRITTI diversamente.
```
GIUDIZIO: VERDE (il banco stampa un verdetto coerente/atteso)
NOTA: Numeri interni coerenti (24/24 ammessi con eccezione attiva; nella tabella controfattuale 21 downgrade + 3 persist = 21/24 fermati, come dichiara la riga che conta). Il banco dichiara i propri limiti (campione 1-ogni-14, un solo parametro cambiato). Rumore d'ambiente innocuo: warning torch "triton not found" e una riga di log `flow.warmup` (moat-judge, store temporaneo 67712a7ceb5e, build 4651182b) dopo il verdetto.

---

## Report 8

COMANDO: python -u docs/stato-reale/banchi/il-costo-alla-porta-dell-apostrofo.py
EXIT: 1
SINTESI:
  popolazione: 13795 fatti VIVI
  perdono il soggetto per l'apostrofo: 0
NON RIUSCITO: popolazione vuota.
(questo è l'output INTERO: 3 righe, il banco esce al guard di riga 75-77 prima di ogni misura)
GIUDIZIO: ROSSO
NOTA: Rosso benigno ma il banco non certifica più nulla: la popolazione di W7-73 è passata da 174 a 0 perché la cura di `_VERB_MARK` è già in main (commit c857752e "cura: e con l apostrofo e un marcatore di verbo quanto e con l accento"; HEAD 4651182b 2026-08-30 20:32) — sonda read-only nella stessa esecuzione: `subject_of("il gate e' un pavimento lessicale")`='gate' identico con `è`, quindi la condizione differenziale del banco (senza soggetto con `e'` E risolto con `è`) dà 0 per costruzione (sui 13795 vivi: 977 con `e'`, 697 senza soggetto, 0 risolti dall'accento); così com'è scritto il banco non potrà mai più passare e va aggiornato o ritirato dal registro, non firmato come misura corrente. Attenzione regime: il banco legge lo store di PRODUZIONE vivo via `CONFIG.semantic_db` (sola lettura, nessun temp store) — il numero 13795 si muove col corpus. Nessun file modificato, nessun write sullo store (sonda aperta in mode=ro).

---

## Report 9

COMANDO: python -u docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py articolo-via
EXIT: 1
SINTESI:
  LEVA: articolo-via — togli il PRIMO articolo determinativo (leva AMPIA, di un'altra istanza; la sua giustificazione: toglierlo non cambia il valore di verita' della frase)
  fatti vivi con fonte: 6296  ·  che contengono la leva: 3521
  tau_hi=80 · cut=40 · 7042 giudizi
  ⚠️ CAMPIONE: uno ogni 8 ⇒ 400 casi  (tetto 400: con questo n una coda all'1% da' ~4 casi)

  -- CONTROLLO (1): il rumore del giudice, RIMISURATO per questa leva
W0830 20:34:05.896000 40432 site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
     ⚠️ punteggio assente sul primo caso: non parto.
GIUDIZIO: NON-INTERPRETABILE (nessun verdetto: il banco si ferma al guard fail-closed "punteggio assente sul primo caso: non parto" prima di misurare)
NOTA: Deterministico — 2 run consecutivi (20:34:05 e 20:34:56), stesso guard, stesso EXIT=1; il giudice non restituisce punteggio in questo regime (subagent Bash, torch caricato ma "triton not found"), quindi chi firma non ha da questo banco né conferma né smentita sulla leva articolo-via: va rieseguito nel regime dove il giudice risponde prima di firmare.

---

## Report 10

COMANDO: python -u docs/stato-reale/banchi/quanto-e-larga-la-coda-dell-accento.py
EXIT: 1
SINTESI:
```
  fatti vivi con fonte: 6296  ·  di cui con `e'`: 360
  tau_hi = 80.0  ·  due giudizi per caso ⇒ 720 giudizi

  -- CONTROLLO (1): il rumore del giudice, RIMISURATO qui
W0830 20:34:05.826000 9976 site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
     ⚠️ punteggio assente sul primo caso: non parto.
```
(output completo: il banco si è fermato qui, ~10 s di run)
GIUDIZIO: NON-INTERPRETABILE (nessun verdetto sulla coda: il banco si è fermato al proprio controllo preliminare (1), fail-fast dichiarato nel docstring, exit 1 voluto)
NOTA: il giudice non ha emesso punteggio (`grounding_score=None` due volte sul primo caso) — regime sospetto, non prodotto: il commit HEAD `48d9165e` delle 20:33:56 (9 secondi prima di questo run) registra «il daemon di embedding e caduto stasera»; il banco ha solo LETTO lo store (select sqlite, zero scritture), la coda dell'accento resta NON misurata e la firma non può citare questo run né come verde né come rosso — va rilanciato a daemon su.

---

## Report 11

COMANDO: python -u docs/stato-reale/banchi/l-accento-sposta-il-punteggio-del-giudice.py
EXIT: 1
SINTESI:
```
  fatti vivi CON FONTE: 6296
  di cui con `e'`     : 360

  -- CONTROLLO (2): il giudice e' STABILE su se stesso?
W0830 20:34:59.924000 39488 site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
     ⚠️ `grounding_score` ASSENTE: il moat non ha girato e non
     leggo l'assenza come un valore. Mi fermo.
```
(questo è l'output COMPLETO: 7 righe in tutto, stdout+stderr)
GIUDIZIO: ROSSO (il banco non arriva al proprio verdetto: si auto-ferma al CONTROLLO (2) con exit 1 — nessuna misura sull'ipotesi dell'accento viene prodotta)
NOTA: non è un errore d'ambiente né un crash: è il guard fail-closed del banco — sul probe di stabilità il moat non ha prodotto `grounding_score` e lo script rifiuta di leggere l'assenza come valore. Riprodotto 2/2 esecuzioni identiche (20:34:05 e 20:34:59, EXIT=1 entrambe); il warning torch/triton è rumore noto. Chi firma deve sapere che oggi questo banco NON attesta nulla sull'accento: prima va capito perché il moat non gira sul controllo di stabilità (6296 fatti vivi con fonte, 360 con `e'` letti correttamente dallo store).

---

## Report 12

COMANDO: python -u docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py articolo
EXIT: 1
SINTESI:
  LEVA: articolo — «per X» → «per il X» (leva MIRATA, W7-78)
  fatti vivi con fonte: 6296  ·  che contengono la leva: 202
  tau_hi=80 · cut=40 · 404 giudizi

  -- CONTROLLO (1): il rumore del giudice, RIMISURATO per questa leva
W0830 20:34:10.253000 39200 site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
     ⚠️ punteggio assente sul primo caso: non parto.
GIUDIZIO: ROSSO (il banco abortisce fail-closed prima di produrre qualunque verdetto sulla leva: nessuno dei 404 giudizi eseguito)
NOTA: Riprodotto 2/2 (stesso punto, stesso exit 1); causa: `run_validation_gate` restituisce `grounding_score=None` su entrambi i voti del primo caso (guard a C:/Users/aurel/Code/HippoAgent/docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py:162-170) — il giudice non giudica in questo regime (HIPPO_DATA_DIR=C:\Users\aurel\.engram, ENGRAM_ADMISSION_GATE=1); fra le due run "fatti vivi con fonte" è passato 6296→6299 (corpus in movimento, la leva resta 202), il warning triton è solo rumore torch.

---

## Report 13

COMANDO: python -u docs/stato-reale/banchi/quali-parole-la-ricevuta-mostra-come-grandezza.py
EXIT: 0
SINTESI:
```
  -- (1) controllo positivo: token NON grammaticali fra i primi 20 del lato fonte: 10

  -- (2) I CANDIDATI (ausiliari e copule, niente ambigui): []
     lato «nel_claim»: 0 occorrenze su 3343  (0.0%)
     lato «nella_fonte»: 0 occorrenze su 6038  (0.0%)

  == LA RIGA CHE CONTA
     🟢 **ZERO**: nessun ausiliare compare come grandezza. Il mio caso
     delle 19:02 era isolato e **la lista monolingue non costa nulla**.
     Lo dico con la stessa forza con cui avrei detto il contrario.

  ⚠️ COSA NON DICE: questo NON cambia un verdetto — `L4.2` e' un avviso e
  il criterio non legge questa lista. Cambia **cio' che l'utente legge**,
  che e' l'unica cosa che l'utente vede.
```
GIUDIZIO: VERDE (verdetto coerente: candidati 0/3343 lato claim e 0/6038 lato fonte, con controllo positivo funzionante — 10 token non grammaticali rilevati nel top-20 del lato fonte, quindi il misuratore vede ciò che non filtra; EXIT=0, nessuna contraddizione interna)
NOTA: il banco legge la popolazione INTERA dello store reale al momento della corsa (6320 fatti vivi con fonte, 5253 riusi L4.2, 124 voci in `_GRAMMATICA`) — chi firma confronti questi numeri con quelli attesi, perché il corpus si muove; il banco stesso dichiara che il risultato non cambia alcun verdetto (`L4.2` è un avviso, il criterio non legge la lista).

---

## Report 14

COMANDO: python -u docs/stato-reale/banchi/il-numero-che-dice-giudicato-e-la-fonte-che-c-era.py
EXIT: 0
SINTESI:
```
  -- (2) LE QUATTRO CASELLE, entrambe le popolazioni
     ✅ fonte SI / punteggio numero      7873  (56.8%)
     ✅ fonte NO / punteggio null        4811  (34.7%)
     🔴 fonte SI / punteggio null          57  (0.4%)
     🔴 fonte NO / punteggio numero      1108  (8.0%)

  == LA RIGA CHE CONTA
     🔴 **1108 fatti (8.0%) portano un PUNTEGGIO senza avere una fonte.** Chi
     legge `grounding_score` per sapere se il fatto e' stato controllato
     legge «giudicato» su un fatto che non aveva nulla contro cui esserlo.
     🟡 **57 fatti (0.4%) hanno una FONTE e punteggio `null`**: il prodotto
     si sottovaluta — c'era qualcosa da giudicare e la colonna dice di no.

  ⚠️ COSA NON DICE: **non ho chiesto al prodotto**, ho letto le colonne.
  Un fatto potrebbe essere stato giudicato e il punteggio scritto altrove;
  in quel caso il difetto e' la COLONNA che la promessa cita, non il giudizio.
```
GIUDIZIO: VERDE (exit 0, verdetto leggibile e internamente coerente: le quattro caselle sommano a 13849 = fatti vivi dichiarati; i disallineati per era 26+108+1031 = 1165 = 1108+57)
NOTA: il banco NON usa uno store temporaneo — legge in SQL puro il DB di produzione vivo (C:\Users\aurel\.engram\semantic\semantic.db, 13849 fatti vivi): sola lettura, nessuna scrittura, ma i numeri (1108/8.0%, 57/0.4%) sono fotografia del corpus a quest'ora e si muoveranno con esso; il banco stesso dichiara il regime («ho letto le colonne, non ho chiesto al prodotto»).

---

## Report 15

COMANDO: python -u docs/stato-reale/banchi/quanto-spesso-la-grandezza-di-L42-e-una-parola-vuota.py
EXIT: 0
SINTESI:
```
  -- CONTROLLO (2): qualche grandezza e' PIENA?
     piene sul lato fonte: 3845

  == LA RIGA CHE CONTA
     🟢 0.1%: raro. **Il mio caso delle 14:02 era
     sfortuna**, e la cura del lato precedente ha gia' fatto il
     suo lavoro. Lo dico con la stessa forza.

  cinque esempi di grandezza VUOTA sul lato fonte:
     5.64 qui «gb», nella fonte «era»
     3107.0 qui «mb», nella fonte «era»
     18.0 qui «(nessuna parola accanto)», nella fonte «erano»

  ⚠️ COSA NON DICE: **la lista delle parole vuote e' mia** e una
  parola in piu' o in meno sposta la quota — per questo i casi
  MISTI sono contati a parte e non sommati alle vuote. E questo NON
  e' un difetto del verdetto: `L4.2` e' un avviso e non quarantina.
```
GIUDIZIO: VERDE (verdetto 🟢 coerente coi propri numeri: VUOTA 5/5253=0.1% lato claim e 3/5253=0.1% lato fonte, exit 0)
NOTA: il banco legge la popolazione VIVA intera (6335 fatti con fonte, nessuno store temporaneo, sola lettura); l'intestazione dice «cinque esempi» ma ne stampa 3 perché i casi VUOTA lato fonte sono esattamente 3; MISTI restano fuori dal verdetto per dichiarazione esplicita del banco (38.2% claim / 26.7% fonte). Log completo (35 righe): C:\Users\aurel\AppData\Local\Temp\claude\C--Users-aurel-Desktop-ProgettiAI\6b293399-2833-41d8-a1bc-e2c3f4908955\scratchpad\banco-l42.log

---

## Report 16

Il banco è uscito subito (exit 1): il suo stesso guard di precondizione è scattato — `run_validation_gate` sul primo caso ha restituito `grounding_score=None` in entrambe le due chiamate di controllo rumore (righe 166-170 dello script), quindi il banco ha rifiutato di partire. Nessuna misura eseguita, nessun verdetto sulla leva.

COMANDO: python -u docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py accenti-apostrofo
EXIT: 1
SINTESI (output integrale, 7 righe, verbatim):
```
  LEVA: accenti-apostrofo — accenti resi con apostrofo → accento vero (`piu'`→`più`, `da'`→`dà`): le forme trovate da un'altra istanza nello sweep, che NON sono copule e quindi restavano fuori dalla cura di `_VERB_MARK`
  fatti vivi con fonte: 6357  ·  che contengono la leva: 173
  tau_hi=80 · cut=40 · 346 giudizi

  -- CONTROLLO (1): il rumore del giudice, RIMISURATO per questa leva
W0830 20:37:00.460000 9356 site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
     ⚠️ punteggio assente sul primo caso: non parto.
```
GIUDIZIO: NON-INTERPRETABILE (il banco si è fermato al proprio guard di precondizione prima di misurare: zero giudizi eseguiti sui 346 previsti, nessun verdetto stampato)
NOTA: chi firma deve sapere che il giudice non ha prodotto punteggio: `run_validation_gate(...).grounding_score` è tornato `None` sul primo caso in entrambe le chiamate (guard a docs/stato-reale/banchi/quanto-pesa-una-leva-sul-giudice.py:166-170) — regime da verificare (gate che non esegue il grounding in questo ambiente, non un modulo/file mancante: torch si è caricato, il warning triton è solo informativo). I numeri di contesto stampati prima dell'abort: 6357 fatti vivi con fonte, 173 con la leva, tau_hi=80, cut=40. Run del 2026-08-30 ~20:37 locale, eseguito 1 volta, nessun file modificato.
