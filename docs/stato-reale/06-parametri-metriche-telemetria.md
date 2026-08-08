# ⑥ Parametri, metriche, telemetria — stato reale

    SHA:      5edc0dfe  (ramo ws6/control-room, worktree ~/Code/HippoAgent-ws6)
    DATA:     2026-08-08, misure prese fra le 12:40 e le 13:10
    AUTORE:   ws7
    VERDETTO: PARZIALE — i parametri esistono e funzionano, ma non sono
              ISPEZIONABILI: chi installa il prodotto non ha modo di sapere
              quali valori sono in vigore, e la superficie che dovrebbe dirlo
              (`verimem doctor`) non ne nomina nessuno.

    COMANDI (copiabili, ognuno riproduce una sezione):
      python -c "from verimem.config import CONFIG; print(len(CONFIG.__dataclass_fields__))"
      python -c "from verimem.grounding_gate import resolve_write_threshold_for as r; print(r('local'), r('claude'))"
      python -c "import verimem.doctor as D; [print(c['status'], c['name']) for c in D.run_doctor()]"
      python -c "from verimem.event_jsonl_log import EVENT_LOG_PATH, _EVENT_LOG_MAX_BYTES; print(EVENT_LOG_PATH, _EVENT_LOG_MAX_BYTES)"

> **Nota sul metodo.** Ogni riga qui sotto è **eseguita**, non letta nel codice.
> Dove non ho eseguito, c'è scritto **NON VERIFICATO** ed è una risposta, non
> una lacuna nascosta.

---

## 1. In una riga

Verimem ha **173 parametri** regolabili da variabile d'ambiente e **194 soglie
numeriche** nel codice. Di questi, **5 parametri** passano dall'oggetto che
sembra la configurazione, **13 soglie** sono cambiabili da fuori, e **zero**
compaiono nella diagnosi che il prodotto stampa. *I parametri ci sono e
funzionano: quello che manca è il modo di vederli.*

---

## 2. I parametri — quanti sono e dove stanno

Misurato analizzando ogni `os.environ.get(...)` del pacchetto:

| | |
|---|---|
| variabili d'ambiente lette dal codice | **173** |
| di cui col nostro prefisso (`VERIMEM_` / `ENGRAM_` / `HIPPO_`) | 166 |
| punti di lettura nel codice | 224 |
| **lette dentro `config.py`** (quindi visibili in `CONFIG`) | **5** |
| lette altrove, sparse in ~40 moduli | **168** |

🔴 **`CONFIG` ha 130 campi e contiene 5 dei 173 parametri.** È l'oggetto che
chiunque ispezionerebbe per sapere «com'è configurato»: risponde per il **3%**.
Gli altri 168 li leggono direttamente i moduli che li usano — `semantic.py` 35,
`mcp_server.py` 23, `cli.py` 12, `anti_confab_gate.py` 10.

### 2a. Quanti sono documentati
Cercati in **116** file `.md` del repo:

| | |
|---|---|
| citati in almeno un documento | 102 (59%) |
| **mai citati da nessuna parte** | **71** |
| col nostro prefisso e mai citati | **69 su 166 (42%)** |

Fra i non documentati ci sono parametri che cambiano il comportamento in modo
sostanziale — per esempio `ENGRAM_GROUNDING_THRESHOLD` (la soglia di
ammissione), `ENGRAM_L1_SEMANTIC_T_HYPE`, `ENGRAM_PPR_FUSION_FLOOR`,
`ENGRAM_RECONCILE_SIM_FALLBACK`.

### 2b. Sette parametri hanno default DIVERSI a seconda di chi li legge
Stessa variabile, letta in due punti, con due valori di ripiego diversi:

    HIPPO_IDE_ORIGIN_ALLOWLIST   ''  (cli.py:1857)   vs  'http://127.0.0.1:8765,…'  (ide.py:143)
    OLLAMA_HOST                  ''  (tools_extra:340) vs 'http://localhost:11434'  (llm.py:1064)
    HIPPO_LLM_PROVIDER           ''  (otto punti)    vs  '(auto)'  (code.py:546)
    VERIMEM_SERVER_URL           ''  (client, mcp)   vs  None      (cli.py:4107)
    HIPPO_MODEL / HIPPO_AUTO_FALLBACK / ENGRAM_SANDBOX_CWD — stessa forma

Non ho misurato se qualcuna di queste divergenze produce un comportamento
sbagliato: **NON VERIFICATO**. Quello che è certo è che il valore di ripiego
dipende da quale strada del codice arriva per prima.

### 2c. Importare il pacchetto SCRIVE nell'ambiente
Eseguito — contando le variabili prima e dopo `import verimem`:

    variabili del prodotto PRIMA dell'import : 8
    variabili del prodotto DOPO l'import     : 21
    CREATE dall'import                        : 13

Il pacchetto specchia ogni `ENGRAM_X` in `HIPPO_X` e `VERIMEM_X` (compatibilità
fra i tre nomi che il prodotto ha avuto). **È voluto**, ma va saputo: chiunque
guardi l'ambiente *dopo* aver importato verimem vede nomi che non ha mai
impostato, e uno strumento di diagnosi che legga `os.environ` non distingue ciò
che ha scelto l'utente da ciò che ha aggiunto la libreria.

---

## 3. 🔴 LA SOGLIA CHE DECIDE COSA ENTRA IN MEMORIA — ce ne sono quattro

Questa è la domanda più importante del prodotto: *a che punteggio un fatto viene
accettato come verificato invece che messo in quarantena?* Il codice dichiara
**quattro numeri diversi**, e il modello installato ne porta un quinto:

    DEFAULT_THRESHOLD        85.0   usata in LETTURA
    WRITE_DEFAULT_THRESHOLD  70.0   usata in SCRITTURA
    LOCAL_CE_MOAT_THRESHOLD  40.0   ripiego per il giudice locale
    CE_BAND_TAU_HI_DEFAULT   80.0   confine della banda incerta
    (il modello installato dichiara 99.64 — scartata a runtime come artefatto)

**La soglia EFFETTIVA, risolta eseguendo il codice del prodotto:**

    backend = local     ->  40.0
    backend = claude    ->  70.0
    backend = ollama    ->  70.0
    backend = openai    ->  70.0

⇒ 🔑 **Lo stesso fatto, con la stessa fonte, entra come verificato se gira il
giudice locale e finisce in quarantena se gira Claude.** Trenta punti di
differenza su una scala 0-100, decisi da *quale giudice è disponibile in quel
momento*, non da una scelta dell'utente.

Il codice **lo sa e lo dichiara** (c'è un avviso a runtime: «*local grounding
judge ships an unusable cut (99.6 > 90, a val-set F1 artifact) — using the
validated local CE moat cut 40*»), e la ragione è documentata e misurata. Non è
un bug nascosto. **Ma non è scritto in nessun posto che un utente legga**, e la
diagnosi non lo riporta (§6).

---

## 4. Le soglie numeriche — 194, e 181 non sono toccabili

| | |
|---|---|
| costanti numeriche a livello di modulo | **194** |
| cambiabili da variabile d'ambiente | **13** |
| **fisse nel sorgente** | **181** |

Chi installa il prodotto può regolare **il 7%** dei numeri che ne decidono il
comportamento. Alcune delle fisse governano decisioni pesanti:

    _MOAT_MIN_RECOVER   70.0   sotto questo, un fatto in quarantena NON si recupera
    _VERDETTO_VERO      90.0   sopra questo, «la fonte lo sostiene»
    _VERDETTO_FALSO     40.0   sotto questo, «la fonte NON lo sostiene»
    _BANDA_CONTESA_ALTA 70.0   fra 40 e 70: l'esito dipendeva da quale giudice girava

**Non sto dicendo che vadano esposte tutte** — 194 manopole sarebbero peggio di
nessuna. Sto dicendo che oggi non c'è modo di sapere quali esistono.

---

## 5. Le metriche — cosa misuriamo davvero

### 5a. Il registro in memoria
Esiste un registro `METRICS` con contatori, istogrammi e misuratori
(`inc` / `observe` / `gauge` / `snapshot`). **A processo appena avviato è
vuoto** e si popola durante l'uso; **muore col processo** — nessuna
persistenza, nessuna aggregazione fra sessioni.

### 5b. Il registro su disco (la telemetria vera)

    percorso : ~/.engram/events.jsonl
    ora      : 2.86 MB, 14.881 eventi, 49 tipi diversi
    tetto    : 5 MB, poi ruota in un solo file `.1` -> massimo ~10 MB in tutto

🔴 **La telemetria è una finestra scorrevole, non un archivio.** Su questa
macchina `events.jsonl.1` è del **4 agosto**: tutto ciò che è successo prima è
già stato buttato. Chi volesse rispondere a «come si è comportata la memoria il
mese scorso» **non può**.

### 5c. Cosa registra un evento di scrittura, e cosa NON registra
`flow.write` (8660 righe nel journal) può portare 12 campi, ma solo **6** ci
sono sempre:

    sempre presenti : surface · stored · status · fact_id · topic · layers
    quasi mai       : grounding_score 1,5% · judged 1,5% · store 0,4% · build 0,1%

Il campo che manca è proprio **il verdetto del giudice** — cioè il dato che
distingue una memoria verificata da un archivio qualsiasi.
⚠️ **Ma il numero grezzo si legge male, e la separazione è questa** (marcatore:
il campo `store`, introdotto il 07/08):

    righe scritte da un build RECENTE :   37   col verdetto:   37   (100%)
    righe scritte da un build VECCHIO : 8623   col verdetto:   91   (1%)

⇒ **L'emettitore attuale registra il verdetto sempre.** L'1,5% complessivo
misura *l'età del journal*, non un difetto del codice di oggi. Verificato
eseguendo una scrittura vera col giudice acceso: `grounding_score
98.59367370605469`, `judged True`.
📌 Lo scrivo per esteso perché ieri **io stesso** ho letto quel numero come un
difetto del prodotto e l'ho consegnato sbagliato: la telemetria di un archivio
con più versioni dentro va sempre separata per versione prima di trarne
conclusioni.

---

## 6. `verimem doctor` — cosa dice, cosa non dice, e se dice il vero

Eseguito: **11 controlli**, ~6 secondi, nessun modello caricato.

| esito | controllo | cosa risponde |
|---|---|---|
| ok | `version` | versione, cartella e revisione del codice in esecuzione |
| ok | `data-dir` | dove stanno i dati, se è scrivibile, quanto pesano i tre archivi |
| ok | `daemon` | se il servizio che calcola i vettori è acceso e con che modello |
| **warn** | `moat-judge` | **2384 fatti su 7171 (33%) hanno un verdetto**; dei restanti, 4752 non avevano una fonte da controllare e 35 ce l'avevano e non hanno verdetto |
| ok | `embedding-model` | tutti i 8999 vettori sono coerenti col motore in uso |
| **warn** | `undo-window` | 113 ritiri in 7 giorni: 3 annullabili · 0 già annullati · 0 scaduti · **110 senza copia di sicurezza** |
| **warn** | `trust-rank-coverage` | 2540 fatti vivi hanno uno stato che la tabella di fiducia non conosce |
| **warn** | `offline` | nessun blocco offline: un avvio a freddo può contattare internet |
| **warn** | `llm` | nessun fornitore di modelli configurato |
| ok | `gateway` | nessuna chiave per il server di squadra (serve solo se lo usi) |
| **warn** | `confidence-vs-verifica` | **il campo «confidenza» ordina AL CONTRARIO della verifica**: i fatti giudicati stanno a 0,516 di media, i mai giudicati a 0,865 |

**Dice il vero?** Ho verificato tre affermazioni contro il database, e reggono:
il conteggio dei giudicati, quello dei ritiri annullabili e quello degli stati
senza rango. L'ultima riga (confidenza al contrario) è la più utile del gruppo:
dice a un utente di non fidarsi di un campo che *sembra* un punteggio di
fiducia.

### 🔴 Cosa NON dice — ed è la parte che manca
Eseguito, cercando le parole nella risposta completa di `doctor`:

1. **Non nomina la soglia di ammissione in vigore.** Le parole `soglia`,
   `threshold`, `cut` non compaiono, e nemmeno il valore `70.0`. Il numero che
   decide cosa entra in memoria (§3) non è ispezionabile da nessuna superficie.
2. **Non nomina NESSUNA delle variabili d'ambiente impostate.** Provato
   impostando `ENGRAM_SUPERSEDE_SAME_SOURCE=0` — che secondo il nostro archivio
   fa smettere la memoria di aggiornarsi — ed eseguendo `doctor`: la variabile
   non compare, e non compare nessuna delle altre. Un utente con un parametro
   pericoloso attivo non ha modo di accorgersene.
3. **Non dice dove finisce la telemetria né che ruota.** Chi cerca «i log»
   deve sapere già dove guardare.
4. **Non dice quale giudice sta usando** — e visto il §3, è quello che decide
   la soglia.

---

## 7. Cose che NON ho verificato — dichiarate

* **Se le 7 divergenze di default (§2b) producano un comportamento sbagliato.**
  Ho misurato che esistono, non che facciano danno.
* **Se le 181 soglie fisse siano tarate bene.** Ho contato quante sono e chi
  può cambiarle, non se i valori siano giusti.
* **Il comportamento delle metriche sotto carico** (`METRICS` con molti eventi):
  ho verificato la forma a freddo, non la tenuta.
* **La telemetria del gateway HTTP**: 48 righe nel journal, non l'ho esercitata
  io.

---

## 8. Le tre cose che secondo me vanno decise (non le ho fatte)

1. **Un comando che stampa i parametri in vigore.** Oggi la risposta a «com'è
   configurata questa installazione» richiede di leggere 40 moduli. La forma
   minima: `doctor` che aggiunge una riga con la soglia effettiva, il giudice in
   uso e le variabili del prodotto impostate. È piccola e chiude i punti 1-2-4
   del §6.
2. **Decidere se la soglia doppia (40 locale / 70 remoto) è voluta.** Se lo è,
   va detta all'utente; se non lo è, è la differenza fra «verificato» e
   «quarantinato» su una parte del corpus.
3. **Decidere quanto deve durare la telemetria.** Oggi ~10 MB e circa quattro
   giorni. Se serve rispondere a domande sul passato, non basta; se non serve,
   va detto che non è un archivio.
