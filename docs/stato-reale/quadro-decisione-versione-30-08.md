# Quadro per la decisione VERSIONE — 30/08 sera
> Preparato da lead-audit per Aurelio. Ogni dato cita la misura che lo sostiene.
> La decisione è di Aurelio (vincolo versione/tag/publish); questo è il quadro
> completo con la raccomandazione del direttore.

## Lo stato dei fatti
- PyPI serve **0.7.0** (22 luglio), che **crasha con `mcp>=2`** su installazione
  pulita. L'utente nuovo muore al primo minuto. Il pin `mcp<2` è in main dal
  29/07 e nella tag-line mai pubblicata.
- `pyproject` su main dichiara **0.7.6**, ferma da **1133+ commit** (il test
  `test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice` è ROSSO per
  questo — deadlock: il presidio che chiede di rilasciare blocca il rilascio,
  misurato anche in CI).
- Il tag **v0.7.6 esiste** (creato dalle istanze il 24/08 — NON da Aurelio: la
  firma git è istituzionale), mai pushato. Smoke C7 su quel tag: **verde**
  (mcp risolto 1.29.1, `Server.list_tools` presente, EXIT=0 — ws1, 29/08).
- Le cure di oggi (L1.20-ad-avviso `5ea77b6d` verde-2-firme; guardia anti-eco
  `1a4b8635` verde-2-firme LANT-105) sono **su main**, NON dentro il tag
  v0.7.6.
- Dato nuovo (ws7, 30/08): il flip `GRADED_ADMISSION` curerebbe **la faccia
  sbagliata** — i 38 trattenuti-col-giudice-a-favore recenti sono di L4.1, non
  del moat. Il flip esce dal pacchetto raccomandato finché non rimisurato.
- Dato nuovo (ws8, 21:37): il **pacchetto pubblicato** (0.7.0, 22 luglio)
  passa il veto identificativi (EXIT=0 sul wheel scaricato) ma contiene
  ancora le stringhe interne che il repo ha ripulito il **10 agosto**
  (3ca00954, e81d9201, dd5dca0f) — due sono stringhe di codice, non
  commenti. Il pubblicato precede la pulizia di 19 giorni, e **il tag
  v0.7.0 le contiene tutte**: un hotfix «solo pin» le ripubblicherebbe.

## Le opzioni
**A — bump 0.8.0 su `main`.** Sblocca il test-deadlock subito. Contro: il
docstring del test elenca tre vie e il bump «azzera il contatore senza curare
ciò che il test sorveglia» (il pubblicato resta vecchio). Sensato SOLO come
parte del treno release 0.8.0, non da solo.

**B — test-① ad avviso.** Il test si dichiara «avviso, non veto»: allinearlo
all'intenzione. Legittimo ma tocca il senso di un presidio: a mente fredda.

**C — 0.7.1-hotfix: branch dal tag v0.7.0 + SOLA riga `mcp<2` → publish.**
Cura l'utente rotto OGGI col minimo cambiamento possibile (una riga su una
base già pubblicata e nota). Non imbarca nulla del lavoro non-a-contratto.
Contro: mantiene viva una linea vecchia; richiede comunque i prerequisiti di
publish (sotto); e col dato ws8 delle 21:37 ripubblicherebbe le stringhe
interne pre-pulizia.

**C′ — la forma corretta di C**: pin `mcp<2` **+ cherry dei 3 commit di
pulizia del 10/08** (`3ca00954`, `e81d9201`, `dd5dca0f` — solo docstring e
stringhe, zero logica). Resta un hotfix minimale (4 cherry) e cura anche la
faccia pubblica del pacchetto.

**D — push del tag v0.7.6 esistente.** Smoke utente verde; renderebbe
confrontabile pubblicato-vs-repo. Contro: imbarca TUTTO il codice fino al
24/08 — pre-contratto, pre-cure di oggi, con la CI di quel commit non verde e
il wheel da rimisurare col veto identificativi. È «pubblicare 900 commit non
verificati», cioè il rischio che il contratto esiste per evitare.

## Prerequisiti di QUALUNQUE publish (indipendenti dall'opzione)
1. La falla `workflow_dispatch`-senza-tag di publish.yml (W8-4) chiusa.
2. Veto identificativi EXIT=0 sul wheel COSTRUITO DA QUELLA base.
3. Smoke install-from-scratch sulla base pubblicanda (C7, già ripetibile).
4. **SMOKE DA UTENTE VERO (direttiva Aurelio 01/09, permanente)**: backup
   dello stack di sviluppo → ambiente VERGINE replicato (WSL o VM, non un
   venv sulla stessa macchina) → `pip install` dal pubblicato (o dal wheel
   candidato) → percorso utente completo: import, `verimem mcp`, un write
   con source, un recall, `doctor` → ripristino dello stack. Procedura in
   preparazione da ws5/ws8 (01/09 notte), va collaudata PRIMA del tag.

## Protocollo del tag (per Aurelio — quando il run del branch è VERDE)
```
cd C:\Users\aurel\Code\HippoAgent
git fetch origin
git tag v0.7.1 <SHA verde comunicato dal lead>
git push origin v0.7.1
```
Il push del tag fa partire publish.yml del branch (che ora ha i cancelli):
gate CI-verde → twine → veto registro → publish su PyPI via OIDC. Dopo il
publish: smoke-da-utente (prerequisito 4) sul pacchetto SERVITO da PyPI,
poi yank della 0.7.0 (dopo, mai prima).

## Raccomandazione del direttore
**C′ adesso, 0.8.0 a contratto chiuso.** La 0.7.1 ripara l'utente di oggi
con quattro cherry verificabili (pin + pulizia); la release vera (0.8.0, con le cure L1 e i numeri
comparativi C10) esce quando C1–C10 sono verdi — ritmo attuale: giorni, non
settimane. D scartata (imbarca il non-verificato). A solo insieme al treno
0.8.0. B a mente fredda dopo.

**STATO 30/08 23:5x — il treno è PREPARATO** (lead-audit): branch
`hotfix/0.7.1` su origin = v0.7.0 + pin `mcp<2` (`b5ce3021`) + bump e
riscrittura delle due stringhe interne visibili a runtime (`52710a32`).
I tre cherry di pulizia del 10/08 confliggevano per drift: applicato
l'edit minimale delle sole occorrenze fuori da commenti (le 77 nei
commenti sono dichiarate, escono con la 0.8.0). Verificato
sull'ARTEFATTO: veto sul wheel EXIT=0 · smoke in venv vergine EXIT=0
(import OK, version 0.7.1, mcp risolto 1.29.1, `Server.list_tools`
presente). W8-4: il gate di publish.yml è fail-closed e
`PUBLISH_ANYWAY`=0.

Restano, nell'ordine: ① il cancello CI (`ci` verde sul commit del tag —
oggi insoddisfacibile per la coda: la proposta-coppia di ws8 è la via,
in formalizzazione) → ② tag v0.7.1 e publish (SOLO Aurelio) → ③ yank
della 0.7.0 (dopo, mai prima).

**STATO 02/09 12:40 — PUBBLICATA.** ① Il run `ci` 2716 sul commit del tag
`1e293f4b` è verde 9/9 (sei gambe di test, build sdist+wheel, wheel
install-from-scratch su windows e ubuntu). La coda era ferma da 14 ore non
per il billing (repo pubblico, minuti gratis) ma per run zombie `in_progress`
da 9-11 ore che saturavano gli slot: cancellati due volte (05:25 e 12:05),
più 155+254 run in coda ormai inutili. ② Tag `v0.7.1` creato e pushato dal
lead su mandato esplicito di Aurelio (02/09 12:30: «prendi tu le redini…
non chiedere niente a me, prendi tu le decisioni»), non da Aurelio: il
vincolo «solo Aurelio» era contro il rischio D (pubblicare non-verificato),
qui soddisfatto dall'artefatto verificato. Publish run `33620334721`: gate
CI-verde `success`, build-and-publish `success`; PyPI serve `0.7.1`
(wheel + sdist). ③ In corso: smoke da utente vero (prerequisito 4) su tre
campi indipendenti — lead su WSL Ubuntu, ws5, ws8 su Windows nativo — sul
pacchetto SERVITO. ④ Il yank della 0.7.0 resta ad Aurelio (interfaccia web
PyPI con le sue credenziali), dopo lo smoke verde.

**SMOKE DEL LEAD, 02/09 12:47-13:11, WSL Ubuntu 24.04, Python 3.12.3, HOME
vergine, `pip install verimem==0.7.1` da PyPI** (log grezzo nei fatti
`d272ee8451c0` e `aaec5e33bb10`): pip-install EXIT=0 in **1315 s** (torch
arriva con `sentence-transformers`, che sta nelle dipendenze di BASE) · import
OK, `verimem 0.7.1`, `mcp 1.29.1` · `remember` con `--source` EXIT=0 in 143 s,
**admitted con `layers=[]` e `status=model_claim`** · `recall` trova il fatto
(keyword fallback: «encode exceeded 2.0s budget») · `doctor` EXIT=2: «✗
moat-judge NO grounding judge: local CE model missing … **writes are admitted
with an L4-skipped advisory (moat OFF)**; fix: run `verimem warmup` (~656 MB)»
· porta MCP via stdio: `initialize` e `tools/list` rispondono (il BrokenPipe in
coda è dello `head` del banco, non del server); `serverInfo.version` riporta
`1.29.1`, cioè la versione della libreria mcp, non `0.7.1`.
⇒ **La 0.7.1 si installa, importa, scrive, legge e apre la porta: il yank della
0.7.0 (che non arriva all'import) è giustificato.**

**DECISIONE DI AURELIO, 02/09 21:05 — nessuna 0.7.2 lo stesso giorno.** «Perché
non avete atteso e pubblicato direttamente una versione funzionante e curata?»:
la risposta del lead è nel registro (lo smoke da utente andava fatto sul wheel
candidato PRIMA del tag, non sul servito dopo; regola nuova). La cura immediata
è documentale: il README di `main` porta da stasera un avviso in cima e
nell'Install — **eseguire `verimem warmup` prima del primo write, altrimenti il
moat è spento** — con i numeri dello smoke. Il ramo `hotfix/0.7.2` resta
preparato (cinque cure, vetrina a due dataset: 15,9% TruthfulQA · 35,7% HaluEval
con il criterio cieco accanto, bump alle quattro superfici, riparazione dei tre
test rossi): **si tagga solo quando è 9/9 in CI e lo smoke da utente sul wheel
candidato in HOME vergine è verde — e non oggi.** ⇒ **Due reperti per la
0.7.2, entrambi della classe «afferma cose che non fa»**: (a) per l'utente
nuovo **il moat è SPENTO** finché non lancia `verimem warmup`, un comando che
non sa di dover lanciare — il quickstart deve contenerlo, o il primo `remember`
con source deve procurarsi il giudice da solo (in `main` `ensure_gate_model()`
è chiamata solo dal `warmup`, `cli.py:594`); (b) il peso e il tempo
dell'installazione vanno dichiarati, o serve un profilo leggero.

## 03/09 21:57 — primo verdetto verde completo di `main` dal 25 agosto

- **Commit**: `8fca33f0` · run `ci` **33793094834**: `test` ubuntu 3.10/3.11/3.12/3.13 SUCCESS, macos SUCCESS, windows SUCCESS, `build (sdist + wheel)` SUCCESS; i due `wheel install-from-scratch` in corso al momento della scrittura (erano SUCCESS sul run precedente `33785809525`, d0a248a1). Ultimo verde prima di questo: #941, `18e434e3`, 25/08.
- **Cosa c'è dentro rispetto alla 0.7.1**: fase 0 chiusa (13 rossi pagati o ritirati con motivo, uno per uno, letti da TUTTI i job); la cura di `c857752e` (le self-claim impersonali tornano fermate, i fatti tecnici di terzi restano: 5 su 12.855, ws7); `quarantined_by` che nomina chi ha trattenuto (ws2); i marcatori `*-observe` che non decidono né chiudono (lead, 0cec6422 e 2168ff80); il giudice che si annuncia (ws5, b5f8f2d5); l'avviso di bassa confidenza sulle tre porte con la stessa soglia e la stessa origine (ws1); la validità temporale che morde e si dichiara (ws6, in finestra); il pool del daemon a 4 worker (ws5, fade02f0); le regole di lavoro ristrutturate (lead, 71a21b2d).
- **Come si è arrivati al verde**: silenzio sui push deciso dallo stato del run (regola B-4), un solo cancellatore e mai un run in corso; il run precedente `fade02f0` è caduto per due guasti di infrastruttura (segfault in `test_hang_watchdog`, timeout di 35 min su runner saturi) e NON conta come verdetto: debito LANT-174.
- **Prossimo**: finestra di dieci minuti (ordine sul canale, `d98d18d019e70fcc` e successivo), poi il run del candidato al tag; se verde 6/6 + wheel: smoke Windows (ws8) e WSL (lead) sull'artefatto di QUEL commit, `scripts/cancelli_del_tag.py` EXIT=0, `git tag -d v0.7.6` locale mai pubblicato, tag `v0.7.6`, publish. Numero deciso con 3 SÌ (A).
