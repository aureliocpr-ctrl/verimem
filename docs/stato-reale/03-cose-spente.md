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
- **La categoria (c) — «gira ma l'effetto non arriva all'utente» — non l'ho misurata in questo
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
