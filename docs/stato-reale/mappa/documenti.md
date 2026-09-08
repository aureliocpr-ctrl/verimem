# I 287 documenti di `docs/`, classificati

> ws8 (Corrado), 08/09/2026. **Questo file cresce**: ogni riga della tabella è un
> verdetto **letto**, non dedotto. Le righe che mancano non sono documenti sani:
> sono documenti **non ancora guardati**, e il contatore in fondo dice quanti.

## Il metodo, e perché non è automatico

Uno script raccoglie gli **indizi** (`classifica_documenti.py`): chi cita il
documento, quali dei path che nomina non esistono più, quando è stato toccato.
Il **verdetto no**: lo do leggendo.

🪞 **Il primo documento che ho letto mi ha dato ragione di non fidarmi dello
script.** `GRAVITA-DIFETTI.md` nomina `tests/test_due_fonti_dichiarate_non_si_ritirano.py`,
che non esiste: indizio di «contraddice». Letto il contesto, il documento dice
**«287 righe, 11 test, rimosso dal revert»** e racconta di averlo recuperato da
`05c26887^` per rieseguirlo. **Non contraddice il codice: lo racconta, ed è pure
preciso.** Classificarlo dall'indizio sarebbe stata una diffamazione.
⇒ Da lì un secondo strumento (`triage_path_rotti.py`) separa chi **afferma** da
chi **racconta** guardando le due righe attorno alla menzione. Non decide:
ordina la coda.

## I verdetti dati finora

| documento | verdetto | la prova |
|---|---|---|
| `docs/stato-reale/GRAVITA-DIFETTI.md` | **VIVO** | nomina un test inesistente ma dichiara «rimosso dal revert» e spiega di averlo recuperato da `05c26887^`: racconta, non afferma |
| `docs/recipes/corpus-bonifica.md` | **CONTRADDICE IL CODICE** | è una ricetta: alla riga 21 dice `python scripts/engram_bonifica.py`, e quel file non esiste. Chi la segue ottiene un errore |
| `docs/EPISTEMIC_FAILURES_STUDY.md` | **CONTRADDICE IL CODICE** | riga 87: cita `benchmark/semantic_conflict.py` come fonte dello studio sui falsi positivi; il file non esiste |
| `docs/CYCLE134-DESIGN.md` | **MORTO** | riga 65 specifica `tests/test_dashboard_sse_e2e.py` come test da scrivere: il test non è mai stato scritto, il design non è stato realizzato |
| `docs/bench/cycle-71-sampling-stub.md` | **MORTO** | verbale datato 15/05: dichiara «Run: `python scripts/bench_c71_sampling_consolidate.py`», comando sparito. Non inganna — porta la data — ma non si può rieseguire |
| `docs/cycle156_unique_index_cross_process_design.md` | **MORTO** | riga 136: «Step 1 — write failing tests first (~30 righe `tests/test_consolidation_cross_process.py`)»: piano mai realizzato |
| `docs/ricerca/2026-09-02-roadmap-estratto-grezzo.md` | **VIVO** | la tabella elenca `tests/test_llm_providers.py` in colonna «new»: sono test **da creare**, non dichiarati esistenti |
| `docs/archive/2026-05-13_QA_AUDIT.md` | **MORTO** | piano di QA del 13/05 archiviato: la tabella elenca test da scrivere con la copertura «da → a». Mai scritti |
| `docs/archive/2026-05-13_BENCH_VALIDATION.md` | **MORTO** | riga 221: «**Aggiungere** uno script `scripts/bench_active_memory.py`» — proposta archiviata. Cita anche una chiave API esterna e un costo in dollari: superato |
| `docs/stato-reale/i-28-rossi-classificati.md` | **VIVO** | cita `benchmark/lme_retrieval_bench.py` **dentro** la citazione di un marcatore che dice «non esiste nel repo»: racconta l'assenza |
| `docs/SECURITY_AUDIT_2026-07-11.md` | **VIVO**, ma il rimando che lo cita è rotto | `CHANGELOG.md:2344` dice «full report in `SECURITY_AUDIT.md`»: il file esiste col nome `SECURITY_AUDIT_2026-07-11.md`. Chi cerca il nome citato non lo trova |
| `docs/sota/multi-signal-fusion.md` | **VIVO** | citato dal CHANGELOG col percorso giusto (riga 1791) |
| `docs/sota/temporal-evolution-narrative.md` | **VIVO** | citato dal CHANGELOG col percorso giusto |
| `docs/archive/2026-05-13_FORGIA.md` | **VIVO come archivio** | il CHANGELOG lo cita come `FORGIA.md` in voci di versioni passate (righe 1975, 2027): è stato spostato in `archive/` col prefisso della data |
| `docs/archive/2026-05-13_RND_MEMORIE.md` | **VIVO come archivio** | stessa forma: spostato e rinominato, citato dal nome vecchio in voci storiche |
| `docs/stato-reale/README.md` | **VIVO** — ed è già una mappa | indice del corpus (08/08), con una **nota datata dichiarata** in cima: «il numero qui sotto è invecchiato… 375 commit → 994», e la conclusione che *si rafforza* invece di cadere. Dichiara l'età invece di nasconderla |
| `docs/stato-reale/ticket-sigsegv-hang-watchdog.md` | **VIVO** | dichiara la finestra della misura («2026-09-03 17:39 → 2026-09-04 19:54, ultimi 60 run») e conosce il seguito: alla riga 139 registra il `--deselect` entrato in `ci.yml`, che è alla riga 901 del workflow |
| `docs/stato-reale/03-cose-spente.md` | **VIVO** | dichiara in testa `SHA: 544d27bd`, i comandi per rifare le misure, il verdetto e **la copertura** («64 interruttori su 151, 42%»), e scrive «dove non ho eseguito c'è **NON VERIFICATO**». È il modello di come si scrive una misura |
| `docs/stato-reale/23-quanto-spesso-L4-1-ha-ragione.md` | **VIVO** | riga 3: «ws6 · **30/08 ore 16:20** · store in `mode=ro`, sole SELECT». Chiude un limite che il documento 22 aveva **dichiarato** invece di nascondere |
| `docs/stato-reale/39-le-finestre-cieche-della-memoria.md` | **VIVO** | «ws6/Aldo — **30/08, sera**. Perimetro: archivio, memoria, corpus, quarantena»: dichiara data e perimetro |
| `docs/JUSTIFIED_MEMORY.md` | **VIVO** | è la tesi del progetto («the 2027 thesis»), e il codice la cita come riferimento del design: `verimem/justified_memory.py:7` → «See docs/JUSTIFIED_MEMORY.md for the design + the verified SOTA gap». Documento e modulo si rimandano |
| `docs/CYCLE109_HANDOFF.md` | **MORTO (a scadenza)** | handoff del 16/05 per far ripartire una sessione, con `Branch: cycle109-provenance-fact-schema-v3` — e quel ramo **non esiste più** (`git branch -a --list '*cycle109*'` → vuoto). Ha esaurito il suo scopo il giorno dopo |


## 🔑 Tre forme che l'indizio non distingue, e che cambiano il verdetto

Leggendo i primi dieci sono uscite tre forme diverse di «nomina un file che non
esiste», e **solo la prima contraddice il codice**:

1. **La ricetta** — dice al lettore *«esegui questo comando»*, e il comando non c'è.
   Chi la segue sbatte contro un errore: **CONTRADDICE IL CODICE**.
2. **Il piano** — elenca file *da scrivere* (« write failing tests first», colonna
   «new», «Aggiungere uno script»). Non afferma che esistano: se non sono mai stati
   scritti il documento è **MORTO**, non bugiardo.
3. **Il racconto** — nomina un file *dicendo* che è stato rimosso, o citando chi lo
   diceva. È **VIVO**, e spesso è il documento più preciso del mucchio.

⇒ Il conteggio «13 documenti nominano un path inesistente» **non è** «13 documenti
sbagliati»: dei primi dieci letti, **uno solo** è una ricetta rotta.


### 🆕 Quarta forma, e un mio righello che ha sbagliato nove volte su dieci

Cercando quali dei 39 documenti citati da README e CHANGELOG non esistono, il mio
grep ne ha dati **dieci**. Verificati uno per uno: **nove erano falsi positivi miei**.

· `multi-signal-fusion.md`, `temporal-evolution-narrative.md` → esistono in `docs/sota/`:
  il grep estraeva il **nome senza il percorso** con cui erano citati.
· `FORGIA.md`, `RND_MEMORIE.md`, `RND_*` → esistono in `docs/archive/` col prefisso della
  data. Il CHANGELOG li cita col nome vecchio **in voci di versioni passate**: racconta.
· `emerging_skill_master-fact.md` → non è un documento del repo: è un file nella cartella
  dati dell'utente (`~/.engram/skill_drafts/…`), dentro un blocco «Disk audit». Il mio
  grep prende qualunque `*.md` nel testo, **anche i file di qualcun altro**.

**Il decimo è vero, ed è una forma nuova: il RIMANDO RINOMINATO.** Il documento esiste, ma
con un nome diverso da quello citato — `CHANGELOG.md:2344` promette «full report in
`SECURITY_AUDIT.md`», e il file si chiama `SECURITY_AUDIT_2026-07-11.md`. Non contraddice
il codice e non è morto: **è un rimando che non arriva**, e si cura con una riga.

🔎 Lezione per questa mappa: **il grep serve a trovare i candidati, mai a contarli.**
Nove su dieci sarebbero stati un allarme falso consegnato come misura.


## 🚨 Una mappa di questo corpus ESISTEVA GIÀ, e avverte delle trappole in cui sono caduto

`docs/stato-reale/README.md` non è un documento qualunque: è **l'indice del corpus**,
scritto il 26/08, e in cima porta tre avvertimenti che ho ritrovato stasera **sulla mia
pelle invece che leggendoli**:

> *«un criterio sintattico su una proprietà semantica sbaglia in **entrambe** le direzioni»*
> — e ne dà i due casi, visti «nello stesso censimento, a un'ora di distanza»: un titolo
> segnato «contiene un numero» perché `L4.1` ha dentro un 4 e un 1, e tre file dati per
> «senza SHA» perché lo dichiaravano in un blocco intestato invece che fra backtick.

> ⛔ *«**E aprite anche i casi che il righello non ha segnalato.**»*

> ⛔ *«Un documento che ha per contenuto un'assenza fallisce ogni `grep` che cerchi una
> presenza»* — l'esempio è `03-cose-spente.md`, che cita una variabile assente dal codice:
> l'assenza **è il suo finding**, e marcarlo scaduto sarebbe stato l'errore.

🔑 **I due allarmi falsi che ho fermato stasera sono la stessa forma, ed erano già scritti.**
Non ho cercato in casa prima di partire: è la regola O1, e non l'ho applicata. Da qui in
avanti questa mappa **continua quella**, non la rifà — e il prossimo giro apre i documenti
che il mio righello **non** ha segnalato, come quella pagina chiede.


## 🔍 La zona cieca, aperta — e non era cieca

L'indice del corpus chiede di **aprire i casi che il righello non ha segnalato**. In
`docs/stato-reale/` sono **62**: nessun path rotto, nessuno che li citi.

Ho cercato quelli che **non dichiarano né SHA né data in testa** — perché una misura
senza data letta come attuale è la forma più dannosa in questa cartella. Primo giro:
**24**. Ne ho letti due, e **tutti e due la dichiaravano nella seconda riga**:
«ws6 · **30/08** ore 16:20», «ws6/Aldo — **30/08**, sera». Il mio regex conosceva
`2026-08-30` e non `30/08` — **il formato che questa casa usa davvero**.

```
  PRIMA (regex senza «30/08»):  38 con data · 24 senza
  DOPO  (formato di casa):      62 con data ·  0 senza
  controllo positivo: un testo senza alcuna data risulta «senza»  ✅
```

⇒ **62 documenti su 62 dichiarano quando sono stati scritti.** La classe più grossa di
`stato-reale/` non inganna sul tempo: si legge come fotografia, e la fotografia porta la
sua data.
⚠️ **Dichiarare la data non è essere veri**: dice solo che il documento non si spaccia per
attuale. Il verdetto su ciascuno resta da dare leggendolo.

🪞 **Terzo criterio mio sbagliato in un'ora** — e stavolta l'avviso era scritto nero su
bianco nell'indice del corpus: *«un criterio sintattico su una proprietà semantica sbaglia
in entrambe le direzioni»*. L'ho verificato inciampandoci invece che leggendolo.


### 🆕 Quinta forma: il documento A SCADENZA

Un **handoff** nasce per un uso singolo — far ripartire una sessione — ed è **morto per
costruzione** quando quell'uso è finito. Non è un difetto: è la sua natura. Ma occupa
spazio nella ricerca, e chi lo trova può crederlo attuale.

In `docs/` alla radice ce ne sono **7** col ciclo o l'handoff nel nome:
`CYCLE109_HANDOFF` · `CYCLE113-HANDOFF` · `CYCLE134-DESIGN` ·
`cycle156_unique_index_cross_process_design` · `cycle159_scaling_experiment` (×2) · …

⇒ **Non vanno cancellati e non vanno letti come attuali**: vanno riconosciuti per quello
che sono. Il segnale più forte non è la data — che c'è — ma il **riferimento a un ramo che
non esiste più**: `cycle109-provenance-fact-schema-v3` è sparito, e il documento lo nomina
come se ci si potesse tornare.

## Quello che gli indizi dicono di tutti e 287

```
  documenti totali                                 287
  citati da README, CHANGELOG, codice, test o
    da un altro documento                          187
  che nominano un path .py INESISTENTE              13   <- la coda dei candidati
     di cui «probabile racconto» (triage)            5
     di cui «probabile affermazione»                18   (un documento puo' averne piu' d'uno)
```
Dove stanno: `docs/stato-reale/` **164** · `docs/` (radice) ~67 · `docs/ricerca/` 16 ·
`docs/archive/` 11 (tutti citati) · `docs/sota/` 9 · `docs/specs/` 8 · il resto sparso.

## Contatore

**Classificati con verdetto letto: 22 su 287.** Con gli indizi raccolti: 287 su 287.
Triati sui path rotti: 13 su 13, e **dei dieci letti uno solo contraddice davvero**.
*Il numero che conta è il primo: gli indizi non sono un verdetto, e non li conto come tale.*
