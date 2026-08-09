# ③ Le cose spente — censimento eseguito

    SHA:      544d27bd  (branch ws3/gate-precision, albero pulito)
    COMANDI:  vedi «Come rifare le misure» in fondo — tre script, copiabili
    VERDETTO: PARZIALE — 12 capacità spente misurate, 1 manopola che non è collegata a niente,
              e un criterio che mancava. Copertura dichiarata: 64 interruttori su 151 (42%).

> Scritto per Aurelio. Ogni riga qui sotto viene da un comando **eseguito**, non da codice letto.
> Dove non ho eseguito, c'è scritto **NON VERIFICATO**.

---

## In una riga

Verimem ha **151 interruttori** nascosti nelle variabili d'ambiente. Ne ho interrogati **64
eseguendoli**: **12 sono spenti**, 11 accesi, 41 sono manopole numeriche. Ma la scoperta che conta
è un'altra: **«spento» non è una proprietà del programma, è una proprietà di chi lo lancia** — lo
stesso interruttore è acceso quando Verimem gira dentro Claude e spento quando lo lanci da
terminale. E una manopola (`HIPPO_EXPOSE_TOOLS`) **è impostata sul tuo computer ma nessuna riga
del programma la legge**: gira a vuoto.

---

## ① Il criterio — correggo le tre categorie che mi erano state proposte

ws3 aveva proposto tre categorie. Le confermo e **ne aggiungo una quarta**, più una **dimensione
trasversale** che è la vera risposta alla tua domanda.

| | categoria | cosa vuol dire | che si fa |
|---|---|---|---|
| **(a)** | codice morto | scritto, mai chiamato da nessuno | si cancella |
| **(b)** | capacità dormiente | c'è ed è chiamata, ma un interruttore la tiene ferma | si accende (o si decide di no) |
| **(c)** | effetto che non arriva | gira davvero, ma il risultato non raggiunge mai l'utente | è la peggiore: sembra funzionare |
| **(d)** | **manopola scollegata** ⟵ **nuova** | una configurazione **impostata** che **nessuno legge** | si cancella o si collega |

**Perché (d) non è (a).** Il codice morto è codice che *nessuno chiama*. La manopola scollegata è
il contrario: è **una decisione presa** (qualcuno ha scritto quel valore, apposta, sul tuo
computer) **che il programma ignora**. Il codice morto non fa danni; la manopola scollegata
**fa credere che una cosa sia configurata** quando non lo è. Ne ho trovata una, ed è viva adesso
sulla tua macchina (§3).

### 🔑 E la dimensione che mancava a tutte e quattro: **spento PER CHI**

Verimem viene lanciato in **tre modi diversi**, e ognuno porta con sé un ambiente diverso:

    da terminale (`verimem …`)      → un insieme di variabili
    da programma (l'SDK Python)     → lo stesso del terminale
    dentro Claude (il server MCP)   → un insieme DIVERSO, scritto in ~/.claude.json

**Misurato, non dedotto** — le variabili impostate nei due ambienti **non coincidono**:

| variabile | terminale / SDK | dentro Claude |
|---|---|---|
| `ENGRAM_GROUNDING_WRITE` | **assente → spento** | **= 1 → acceso** |
| `HIPPO_HOSTED` | assente → spento | **= 1 → acceso** |
| `HIPPO_EAGER_PRELOAD` | assente | = 1 |
| `HIPPO_OFFLINE` | assente | = 1 |
| `HIPPO_PRELOAD_TIMEOUT_S` | assente | 180 |
| `ENGRAM_BRIEFING_MIN_MATCHED` | **= 4** | **assente** |
| `ENGRAM_BRIEFING_THRESHOLD` | = 0.40 | assente |
| `ENGRAM_DECAY_ENABLED` | = 1 | assente |
| `HIPPO_EXPOSE_TOOLS` | = 10 nomi | assente |

⇒ **Nessuna delle nove riga coincide.** Non è una svista di una variabile: **sono due
configurazioni separate che nessuno ha mai messo a confronto.**

⇒ **La conseguenza pratica**: se una di noi misura «X è spento» da terminale e un'altra misura
«X è acceso» dentro Claude, **hanno ragione tutte e due** e sembra un litigio. È successo ieri con
il costo del giudice, ed è la stessa causa.

---

## ② Le 12 capacità dormienti — misurate eseguendo l'interruttore

Non ho letto i valori di default nel codice (ieri ho pagato per averlo fatto: quello che è scritto
nella firma di una funzione **non è** quello che il programma usa). Ho fatto il contrario: ho
**chiamato le 64 funzioni che decidono acceso/spento** e ho registrato cosa rispondono.

    ENGRAM_GRADED_ADMISSION           spento   ammissione a gradi invece che sì/no
    ENGRAM_GROUNDING_WRITE            spento   ⚠️ scalda il giudice quando SCRIVI  (acceso dentro Claude)
    ENGRAM_P0_INDEPENDENCE            spento   controllo di indipendenza fra le prove
    ENGRAM_RECONCILE_AUTO_SUPERSEDE   spento   sostituzione automatica quando due fatti si riconciliano
    ENGRAM_RECONCILE_SIM_FALLBACK     spento   ripiego per somiglianza nella riconciliazione
    ENGRAM_SOURCE_AUTO_CONFIRM        spento   conferma automatica dalla fonte
    ENGRAM_CAPABILITY_GATE            "off"    controllo dei permessi sui comandi
    VERIMEM_AUDIT_LOG                 spento   ⚠️ il registro di controllo non scrive
    HIPPO_AUTH_TOKEN                  spento   autenticazione dell'interfaccia
    HIPPO_DASHBOARD_AUTH_DISABLED     spento   (spento = la dashboard CHIEDE le credenziali: qui spento è giusto)
    HIPPO_ENCODE_DELEGATE_ONLY        spento   in due punti diversi
    HIPPO_HOSTED                      spento   (acceso dentro Claude)

**Le due che ti segnalo per prime**, perché non sono dettagli tecnici:

- **`VERIMEM_AUDIT_LOG` spento** — esiste un registro di controllo di tutto ciò che il programma
  fa, ed è **fermo**. Se domani vuoi sapere «chi ha scritto cosa e quando», quel registro non ce
  l'ha. *(Nota: esiste un secondo registro, `HIPPO_MCP_AUDIT_LOG`, che invece ha un percorso
  configurato. Sono due cose diverse e non ho verificato se il secondo scrive davvero →
  **NON VERIFICATO**.)*
- **`ENGRAM_CAPABILITY_GATE = "off"`** — il controllo dei permessi sui comandi è disattivato. **Non
  ho verificato cosa lascerebbe passare o bloccherebbe se acceso** → **NON VERIFICATO**.

**E le 11 accese**, per contrasto: `ENGRAM_ANN_RECALL`, `ENGRAM_ENCODE_SERVICE`,
`ENGRAM_ENTITY_LIVE`, `ENGRAM_L3_SUBJECT_FILTER`, `ENGRAM_PPR_FUSION`, `ENGRAM_PPR_SEED_RESOLVE`,
`ENGRAM_SUPERSEDE_SAME_SOURCE`, `HIPPO_ENABLE_SHELL` (in due punti), `HIPPO_STARTUP_SELFHEAL`,
`VERIMEM_CE_BAND_ENFORCE`.

---

## ③ La manopola scollegata — categoria (d), viva adesso sul tuo computer

Nell'ambiente della sessione c'è:

    HIPPO_EXPOSE_TOOLS = hippo_status, hippo_recall, hippo_remember, hippo_record_episode,
                         hippo_facts_search, hippo_facts_recall, hippo_skills_for,
                         hippo_episode_get, hippo_episode_list, hippo_prepare_task   (10 nomi)

Sembra dire: «di tutti gli strumenti di Verimem, esponine solo questi dieci».

**Cercata in tutto il pacchetto effettivamente caricato** (`C:/Users/aurel/Code/HippoAgent/verimem`,
versione **0.7.0** — ho verificato che sia questo e non una copia installata altrove):

    file del pacchetto importato che leggono HIPPO_EXPOSE_TOOLS: 0

⇒ **Nessuna riga la legge.** L'unico posto del repository dove quel nome compare è un file di
risultati di benchmark; fuori dal repository, solo le trascrizioni delle nostre conversazioni.

⇒ **Quindi la limitazione non è in vigore.** Chi l'ha scritta pensava di ridurre gli strumenti
esposti; il programma non se ne accorge.
⚠️ **Il limite di questa misura**: ho verificato che *il pacchetto Verimem* non la legge. **Non ho
verificato se la legge Claude Code** (che è chi costruisce l'elenco degli strumenti) →
**NON VERIFICATO**, ed è la prossima riga da eseguire per chiudere il caso.

---

## ④ Cosa NON ho coperto — dichiarato, non nascosto

- **87 interruttori su 151 (58%) non li ho misurati.** Il mio metodo interroga solo le funzioni
  senza argomenti che decidono acceso/spento; gli altri interruttori vengono letti dentro funzioni
  più grandi e per misurarli va costruito un caso ciascuno. **NON VERIFICATO.**
- ~~La categoria (c) non l'ho misurata~~ → **misurata dopo il primo commit, vedi §⑥ qui sotto.**
- **(riga originale, tenuta per onestà) La categoria (c) — «gira ma l'effetto non arriva» — non l'ho misurata in questo
  giro.** È quella che tu intendi quando dici «cose spente» ed è la più importante. L'unico caso
  noto è quello che abbiamo trovato ieri (un conflitto viene *rilevato* e il programma tiene
  entrambi i fatti invece di aggiornare), **e non l'ho ri-misurato oggi.** **NON VERIFICATO.**
- **Non ho contato quanti strumenti Verimem espone in totale.** Il conteggio automatico ha dato
  zero perché non sono definiti dove li cercavo. **NON VERIFICATO.**
- Un dettaglio che segnalo perché è già noto e ora è confermato: `ENGRAM_BRIEFING_MIN_MATCHED=4`
  è impostata nell'ambiente **ma non compare in nessun file di configurazione** — non si sa chi
  la mette.

---

## ⑤ Un errore mio, in questo stesso documento

La prima versione di questa misura diceva **«solo 3 strumenti esposti su 75»**. Era falso: il mio
script tagliava i valori a 40 caratteri e ne mostrava tre invece di dieci. **Il numero sbagliato
non veniva dal programma, veniva dal mio modo di stamparlo.**
⇒ Lo scrivo qui perché è la stessa forma di errore che questo documento censisce: **una manopola
che sembra dire una cosa e ne fa un'altra.** Vale per il programma e vale per chi lo misura.

---

## Come rifare le misure

```bash
python docs/stato-reale/banchi/q_spenti.py     # esegue i 64 interruttori e stampa spenti / accesi / soglie
python docs/stato-reale/banchi/q_ambiente.py   # confronta l'ambiente del terminale con quello di Claude
python docs/stato-reale/banchi/q_quale.py      # verifica QUALE pacchetto stai misurando + cerca la manopola scollegata
```

Gli script sono committati qui accanto e sono di sola lettura: non scrivono niente, non caricano modelli,
non toccano il database.

---

## ⑥ La categoria (c), misurata — e va riformulata

Dopo il primo commit ho misurato anche la categoria (c), quella che ti sfugge sempre: *«gira, ma
l'effetto non arriva mai all'utente»*. Il caso di riferimento è quello trovato ieri — un conflitto
fra due fatti viene **rilevato** e il programma **tiene entrambi** invece di aggiornare.

**Prima ipotesi, mia, ed era sbagliata.** Avevo concluso che quel caso fosse *invisibile per
disegno*: la registrazione degli eventi annota le sostituzioni **avvenute**, non quelle **non
avvenute**. Poi ho guardato le righe invece di fidarmi dell'elenco dei nomi, e ho trovato che
**la traccia esiste**:

    coherence_warning   kind=numeric_clash    details="numbers=[150.0] vs [100.0] sim=0.75"
    coherence_warning   kind=near_duplicate   details="jaccard=0.75"

⇒ **Il programma segnala l'incoerenza anche quando non aggiorna.** La mia conclusione sarebbe stata
falsa e l'ho evitata solo guardando due righe.

**Il conto vero:**

    scritture registrate in totale                      8672
    segnalazioni di incoerenza (coherence_warning)        24     ← lo 0,28%
        di cui  numeri in conflitto (numeric_clash)       13
        di cui  quasi-duplicati (near_duplicate)          11
    segnalazioni SENZA nessuna sostituzione dei due fatti 12
        ma 11 delle 12 sono LO STESSO caso ripetuto (topic research/rag, jaccard 0.75)
        una sola è un conflitto numerico vero:  topic lab/m, numbers=[42.0] vs [88.0] sim=0.92

### 🔑 Cosa cambia questo per la tua domanda

La categoria (c) come l'avevamo formulata — *«l'effetto non arriva»* — **non è quello che i dati
mostrano**. Quello che mostrano è più semplice e più serio:

> **il rilevatore di incoerenze si accende 24 volte su 8672 scritture: lo 0,28%.**

Non è che trova e poi non agisce. **È che quasi non trova.** E i pochi casi registrati vengono da
argomenti di prova (`research/rag`, `lab/m`, `t`), non da uso reale.

⇒ ⚠️ **Il limite, dichiarato**: 24 casi sono troppo pochi per dire se in uso reale il rilevatore
sia tarato male o se davvero le incoerenze siano rare. **Su questo resta NON VERIFICATO**, e la
misura che lo chiuderebbe è confrontare le incoerenze *segnalate* con quelle *presenti* nel corpus
— che è la fetta di chi misura la qualità del rilevamento, non la mia.

⇒ 📌 **E una nota utile a chi legge la telemetria dopo di me**: l'evento della sostituzione ha un
campo chiamato `branch`, che sembra dire *quale ramo di codice ha deciso*. **Non lo dice**: su
**197 eventi su 197** contiene esattamente la stessa stringa del campo `reason`, cioè il testo che
l'utente ha passato. È un campo diagnostico che ripete l'input — se ci costruisci sopra un'analisi
dei rami, misuri le parole di chi ha scritto, non il comportamento del programma.

---

## ⑦ La sottocategoria che mancava: **(c-bis) l'effetto annullato da un'altra porta**

Dopo aver consegnato la categoria (c) sono andato a verificare una promessa della fetta ① — *«un
fatto messo in quarantena resta fuori da ciò che ti viene restituito»* — e ho trovato il caso che
completa il criterio di questo documento.

**La quarantena funziona su quattro porte e cade sulla quinta:**

    search    → non lo restituisce   ✅        recall   → non lo restituisce   ✅
    ask       → non lo restituisce   ✅        explain  → non lo restituisce   ✅
    **briefing → LO RESTITUISCE**    🔴  (il testo che il prodotto inietta da solo a inizio sessione)

**Con una variabile sola:**

    numero di fatti chiesti al briefing:   8 → 0 quarantinati      ← valore di fabbrica
                                          **10 → 1**              ← basta questo
                                           30 → 6      40 → 9

Il primo fatto servito è `f9b216379a1b`, punteggio 11,42: **è il fatto che il gate aveva respinto
ieri sera** perché la sua fonte non lo sosteneva. Il programma lo ha giudicato inaffidabile, lo ha
nascosto dalle ricerche, **e poi me lo ha messo nel contesto senza che lo chiedessi.**

E non serve cambiare configurazione: in `verimem/mcp_server.py:8820` il numero di fatti arriva
dagli argomenti dello strumento (`arguments.get("n_facts", 8)`). **Qualunque agente collegato che
ne chieda dieci invece di otto riceve un quarantinato.**

### Perché questo cambia il criterio

Le quattro categorie di questo documento presumono che una capacità sia *accesa* o *spenta*. Questo
caso è una quinta forma:

| | | |
|---|---|---|
| **(c-bis)** | **effetto annullato da un'altra porta** | la protezione funziona **e** un percorso diverso la scavalca |

**Non è (c)** — l'effetto arriva eccome. **Non è (b)** — nessun interruttore è spento. È che **due
percorsi dello stesso prodotto danno risposte opposte sullo stesso fatto**, ed è la stessa forma
del punto ① di questo documento: *lo stesso interruttore è acceso da una parte e spento
dall'altra*. Lì erano due ambienti, qui sono due porte.

⇒ **La regola generale che ne esce, ed è la risposta più utile alla tua domanda «ci sono cose
spente?»**: una protezione non è una proprietà del programma, **è una proprietà di ogni singolo
percorso che porta al dato**. Verificarla su un percorso non dice niente sugli altri — e a noi
serve verificarla su tutti quelli che l'utente può imboccare, **compresi quelli che non imbocca
lui ma il prodotto per lui.**

⚠️ **NON VERIFICATO**: non ho guardato se accanto ai fatti serviti dal briefing compaia
l'etichetta «quarantinato». Se ci fosse, il danno sarebbe molto minore.
