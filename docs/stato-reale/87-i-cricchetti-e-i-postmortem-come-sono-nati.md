# I cricchetti e i postmortem: come sono nati, e i difetti che hanno trovato in sé

**09–11/09/2026 · `scripts/copie.py`, `scripts/senza_chiamante.py`,
`scripts/righe_della_pr.py`, `scripts/grep_nelle_mappe.py`,
`scripts/vettori_vuoti.py`, `.github/workflows/presidi-pr.yml`**

Questa pagina esiste perché il racconto di queste misure stava **solo dentro i
messaggi dei commit**, lunghi trenta o quaranta righe l'uno. Da questa
finestra i messaggi stanno in dieci righe e il racconto sta qui: il contenuto
non si butta, si sposta.

Il filo che le lega tutte: **ogni cricchetto ha trovato un difetto in sé stesso
prima di trovarne uno nel prodotto**, e la parte che vale non è il numero, è il
criterio scritto accanto al numero.

---

## ① R3 — il cricchetto delle copie, e il controllo positivo che lo prova

`scripts/copie.py` conta con `ast` quante volte una primitiva è stata riscritta
invece di essere importata, e fallisce se un numero **sale**.

Per chi usa il prodotto: le sei primitive che oggi divergono (jaccard, tokens,
signature, stoplist, elenchi di status) non possono divergere di più mentre si
cura il resto; una copia nuova rende rossa la richiesta che la introduce.

I tetti proposti nel piano erano 18/20/5/4/3. Misurati con `ast` sul tip
`20257636`, **due su cinque reggono e tre no**:

```
_jaccard               18 = 18   (18 definizioni in 18 file)
_tokens                20 = 20   (20 definizioni in 20 file)
_signature              5 != 3   (5 definizioni, 4 corpi distinti)
liste di parole vuote  16 != 5   (16 liste in 13 file, >=4 parole vuote note)
elenchi di status      22 != 4   (22 liste in 14 file, >=2 status noti)
```

Non è un disaccordo: **sono criteri diversi chiamati con lo stesso nome**, la
stessa forma del 167-contro-176 della stessa mattina. Il tetto porta il criterio
accanto alla cifra, e il criterio vale quanto il numero.

Il controllo positivo è obbligatorio: `--autotest` aggiunge una copia finta e
pretende l'uscita 1. Quel test ha trovato subito un difetto reale nello script
(`relative_to` esplodeva su qualunque albero fuori dal repo). **Non esiste un
`--aggiorna`: un cricchetto che si ripara da solo non morde.**

```
python -m pytest tests/test_copie_cricchetto.py -q  ->  6 passed, EXIT=0
python scripts/copie.py                             ->  VERDE,  EXIT=0
python scripts/copie.py --autotest                  ->  (a) 0, (b) 1, VERDE
```

---

## ② R2 — i moduli senza porta, in quattro classi invece che in un numero

`scripts/senza_chiamante.py` conta con `ast` chi importa chi sotto `verimem/` e
fallisce se sale il numero dei moduli che chi installa non può raggiungere.

Per chi usa il prodotto: ogni modulo pubblicato e irraggiungibile è peso che
scarica, superficie di attacco che corre e codice che si paga di manutenzione,
e in cambio non riceve niente.

**Quattro classi**, perché «senza chiamante» significa cose diverse e sommarle
nasconde la distinzione che serve:

```
B   entry point in pyproject         1   (cli: è una porta, non un orfano)
C1  solo `python -m verimem.x`       5   (sorvegliati, fuori dal tetto)
C2  nessuna porta                   35   (il tetto)
D   irraggiungibili per catena      62   (35 C2 + 5 C1 + 22 solo-per-catena)
```

**D è la misura che conta**: la raggiungibilità non è «qualcuno lo importa».
`resonator_memory` ha DUE importatori e nessuno dei due ha una porta; la catena
finisce nel vuoto. Ventidue moduli stanno così, fra cui l'intero ramo dei
`dream_*_hook` appeso a `auto_dream_worker`, `syscall_bridge` / `mesh_memory` /
`capability_token` appesi a `engram_syscall_mcp`, e `proactive_step_injector`
(T53) appeso a `hooks/pre_tool_use`.

Il resoconto della mappa §3 ne conta 19: **è un criterio diverso** (i moduli
interi scelti leggendoli, senza i banchi e gli adattatori di laboratorio). Il
tetto porta il criterio accanto alla cifra e non prova a far tornare il 19.

**Limite dichiarato**: le porte fuori dal pacchetto non si vedono.
`hooks/pre_tool_use` è lanciato da un wrapper che non è nel pacchetto
pubblicato: per questo righello risulta senza porta, ed è giusto per chi
installa da PyPI, ma va detto invece di lasciarlo dedurre.

I due test in fondo hanno trovato **due difetti veri nel righello**, prima del
commit: gli `__init__.py` di sottopacchetto avevano un nome che il grafo non
collegava (`dashboard_routes.__init__` contro `dashboard_routes`), e dentro un
`__init__` un `from .x import y` punta al pacchetto **stesso**, non al genitore.
Con quei due difetti il righello dichiarava senza chiamante i nove moduli di
`dashboard_routes/`, che `dashboard.py:35` importa.

```
python -m pytest tests/test_senza_chiamante_cricchetto.py -q -> 6 passed EXIT=0
python scripts/senza_chiamante.py            -> VERDE C2=35 C1=5 D=62 EXIT=0
python scripts/senza_chiamante.py --autotest -> (a) 0, (b) 1, VERDE
```

---

## ③ R6 — il tetto delle 300 righe, e il workflow che esegue i tre cricchetti

`.github/workflows/presidi-pr.yml` esegue su ogni richiesta verso il ramo
principale, in un job solo e in circa un minuto: gli autotest dei tre presìdi,
poi R3 (copie), R2 (moduli senza porta), il righello della mappa quando ci sarà,
R6 (righe della richiesta).

R6 conta le righe di **prodotto aggiunte** (`verimem/`), non le cancellazioni:
togliere codice è ciò che si vuole, e contarlo come «grande» punirebbe proprio
quello. Test e documenti restano fuori dal tetto ma si stampano lo stesso.

Il diff usa `base...head` a **tre punti**. Con due, una richiesta ferma diventa
«grande» appena il ramo principale va avanti per conto suo: c'è un test che lo
prova (il tronco aggiunge 400 righe altrove, la richiesta resta di 5).

La deroga è **nominale**: l'etichetta `lotto-grande`, che mette il
coordinamento. Una deroga che chiunque può darsi da solo non è una deroga.

**Tre scelte dichiarate**

1. File separato e non dentro `ci.yml`: `ci.yml` non parte quando la richiesta
   tocca solo `docs/` o `*.md` (`paths-ignore`, 08/09) e i cricchetti devono
   partire sempre; inoltre `ci.yml` è il file su cui si scrive in molti.
2. Gli autotest girano **prima** delle misure, nello stesso job: se un presidio
   non morde, il job cade anche quando i numeri sono verdi.
3. Il passo del righello della mappa **dice «NON MISURATO»** finché
   `scripts/mappa_completa.py` non arriva, invece di tacere: un controllo che
   non gira e non lo dichiara si legge come un controllo verde.

Il tetto è 300, non i 100 della fonte primaria (Google, *Small CLs*, che dà 1000
come «usually too large»): 300 è il numero deciso il 09/09 e va rimisurato se
morde troppo o mai.

```
python -m pytest tests/test_presidi_pr.py -q      -> 6 passed  EXIT=0
python scripts/righe_della_pr.py --autotest       -> 6 casi su 6, VERDE
python scripts/righe_della_pr.py origin/main HEAD -> +0 prodotto, VERDE EXIT=0
i 7 passi del workflow simulati a mano            -> tutti EXIT=0
```

---

## ④ R7 — la cartella dei postmortem, e il rosso che oggi non si vede più

`docs/stato-reale/postmortem/` è il registro dei rossi: sei righe fisse, senza
colpe, con i cinque inneschi del SRE book e le quattro classi di un rosso (vero
· trappola armata · sensore scollegato · guardiano che mente). La riga che
decide il valore del file è **«Controllo»**: cosa fallirebbe **da solo** se la
stessa cosa tornasse.

Primo caso, verificato con `gh`: la CI windows rossa sul candidato al tag
`5ac8d9f1` dell'08/09 (T38). Run `34221255060`, tentativo 1, failure
11:32→12:31; job `test (windows-latest / py3.12)`; test
`test_observing_the_breaker_does_not_rearm_it`; «AssertionError: the gate, and
only the gate, re-arms after the cooldown · assert True is False»; 1 failed,
12821 passed in 3053.25s.

E il reperto che rende questa cartella necessaria: **quel rosso oggi non si vede
più.** `gh run list` mostra `success` perché legge l'ultimo tentativo, e il
tentativo 2 è verde. Un rosso guarito da un rerun sparisce da ogni conteggio: i
rossi si contano **per tentativo**, non per run, e questa cartella è l'unico
posto dove restano scritti. Le misure del venerdì (R8) leggono qui, non la
pagina Actions.

**E la promessa falsa del README.** `docs/LIMITS.md:3` prometteva da sempre «The
README keeps one line and points here». Misurato: `grep -n LIMITS README.md` →
**zero**. Chi leggeva il README credeva di aver letto i limiti. Aggiunta la riga
e, soprattutto, il presidio: `tests/test_i_limiti_sono_puntati_dal_readme.py`
pretende il link **cliccabile**, non la menzione — un percorso nominato dentro
un paragrafo non porta da nessuna parte per chi legge su PyPI.

Il quarto test è `xfail` **strict** e dichiara un limite che appartiene a un
altro perimetro: **Order** (il self-claim ammesso quando segue una frase vera di
terzi, 7 formulazioni su 7, misurato il 04/09) sta in `LIMITS.md` e non nel
README. Quando quel perimetro lo cura, il test diventa verde e l'`xfail` va
tolto: **un cricchetto al contrario, che segnala la cura invece di aspettarla.**

```
python -m pytest tests/test_i_limiti_sono_puntati_dal_readme.py -q
  -> 3 passed, 1 xfailed  EXIT=0
grep -n LIMITS README.md      -> ora la riga 48; prima nessuna
git diff --numstat README.md  -> 2 0 (zero righe di prodotto)
```

---

## ⑤ R7 — i 14 fatti senza vettore, e il controllo ovvio che era cieco

Fra le 23:35:46 e le 23:53:52 quattordici fatti sono entrati nello store con
embedding di **zero byte** e `embedding_model` stringa vuota. Catena provata: il
daemon di encoding rinato con un altro modello, il client che lo rifiuta,
delegate-only senza ripiego, `semantic.py:3303` che scrive senza vettore.

Classe: **guardiano che mente**, non un bug. Il vettore differito è un
comportamento voluto e documentato (`verimem facts backfill --help`: «persists
the row instantly with an empty-blob embedding so it never cold-blocks ~22s»), e
la cura esiste, idempotente. Il difetto è che **chi scrive non lo sa**: la
ricevuta stampa `stored=True` e non lo dice, e nove scritture di fila sono
passate per riuscite.

Il backfill **non** è stato eseguito, e l'ordine conta: prima il daemon deve
dichiarare `e5-base/768` (alle 00:10 `encode` dava ancora
`EncodeDelegateUnavailable`), poi il backfill. Lanciarlo mentre il daemon serve
384 scriverebbe 14 vettori a 384 in uno store a 768 = T-MAP-9, e si passerebbe
da «fuori dal recall» a «il recall li trova e non li capisce».

**Il controllo aggiunto e perché quello ovvio è cieco.**
`scripts/vettori_vuoti.py` conta per **forma** del vettore (NULL / vuoto /
lunghezza) e fallisce sopra zero:

```
WHERE embedding IS NULL     ->  0     <- non ne vede nessuno
WHERE length(embedding)=0   -> 14     <- ci sono tutti
```

Un blob di zero byte non è NULL e `''` non è NULL. Chi aveva dichiarato «lo
store è pulito» aveva usato il primo criterio: **vero e inutile insieme.**

Due trappole trovate scrivendolo, dichiarate nel codice: il DB è quello
**annidato** (`<data_dir>/semantic.db` esiste ed è VUOTO, 0 fatti; quello vero è
`<data_dir>/semantic/semantic.db`, 18.121 fatti) — lo script stampa sempre il
percorso che ha letto; e il primo autotest passava 3 su 3 mentre lo script
cadeva sullo store vero con «no such column: text», perché la colonna si chiama
`proposition` e il banco finto aveva **uno schema inventato**. Un banco che non
riproduce lo schema vero prova solo di essere coerente con sé stesso.

**La causa a monte** (00:38 del 10/09): il daemon non era caduto per caso.
Discovery e lock stanno in `Path.home()`, mai nella data dir
(`encode_service.py:41`, `:573`, `:583`), quindi **un banco che isola
`ENGRAM_DATA_DIR` non isola il daemon**: legge la discovery globale, trova un
daemon che non dichiara il suo modello, ne spawna uno col proprio e lo registra
per tutti. L'innesco del 09/09 è stato un banco isolato su T49, letto dal suo
`environ` — e non aveva sbagliato niente: isolare la data dir è ciò che era
stato chiesto. Il ripristino manuale è durato **dodici minuti** (00:13 →
00:25:08).

E la riga «Controllo» cambia di conseguenza. `vettori_vuoti.py` **rileva**, non
**previene**: dice che è successo, non impedisce che risucceda. I due controlli
che chiudono l'incidente sono altrove: **T60** (discovery e lock dentro la data
dir — la prevenzione) e **la riga della ricevuta** (il save deve dire che
l'embedding è differito, come già dice `judged` e `withheld_despite_judge` — la
dichiarazione). Senza, chi scrive continua a leggere `stored:true` e va avanti.

**Distinguere «rileva» da «previene» nella riga Controllo è la parte che vale**:
un postmortem con un rilevatore al posto di una prevenzione sembra chiuso e non
lo è. E un incidente ha **un** postmortem solo: la seconda stesura assegnata su
questo stesso incidente è stata rifiutata e la causa trovata dopo è stata
innestata qui — la classe «tre indagini sulla stessa cosa», fermata prima
invece che contata dopo.

**Il difetto trovato dalla revisione**: manomettendo il tetto a mano invece di
credere all'autotest (18 > 17 → EXIT=1) si è visto che una copia di `copie.py`
lanciata da un'altra cartella stampava VERDE con EXIT=0: gli script si ancorano
a `__file__`, quindi **da un altro albero misurano quell'albero**. Ora
`copie.py` e `senza_chiamante.py` stampano il percorso assoluto che stanno
misurando e diventano **rossi se leggono zero file**: un cricchetto che misura
la cartella sbagliata stampa sempre verde.

```
python scripts/vettori_vuoti.py --autotest -> 3 casi su 3, VERDE, EXIT=0
python scripts/vettori_vuoti.py            -> ROSSO, 14 fatti elencati, EXIT=1
python -m pytest tests/test_copie_cricchetto.py -q -> 6 passed
```

---

## ⑥ R5 — gli zeri finti nelle ricerche, e le tre classi che impediscono di gridare

`scripts/grep_nelle_mappe.py` trova i comandi di ricerca scritti nei documenti
della mappa che cercano un `|` **senza `-E`**: lì il `|` è letterale, il comando
non trova niente, e la conclusione «nessuna occorrenza» sembra misurata.

Per chi usa il prodotto: una riga della mappa che dice «nessun claim del README
nomina questa funzione» decide se una funzione resta o si toglie. Se quello zero
è un errore di sintassi invece di una misura, si toglie codice che serve o si
tiene codice che non serve.

Misurato sui **403 documenti veri**, **573 comandi** di ricerca letti: **3
sicuri + 1 ambiguo**.

```
migrations.md:18      git grep 'from .migrations|verimem.migrations'
README-claims.md:117  grep -rn "VERIMEM_BAND_LLM|VERIMEM_SEMANTIC_CONFLICT|..."
sos_compensator.md:72 grep -rln "sos_compensator|compensated_anchor|..."
memory.md:113         AMBIGUO (dentro una tabella)
```

**Il primo criterio ne dava 8, e cinque erano allarmi falsi.** Un righello che
sbaglia **contro** chi lo usa è il modo più rapido di farsi ignorare, quindi le
tre classi che tacciono sono la parte che vale:

1. `\|` è l'alternanza **corretta** in BRE, cioè senza `-E`. Accusarla è un
   errore.
2. Un ramo **vuoto** (`^|`, `a|`) significa che il `|` è la barra **letterale**
   che qualcuno cerca davvero — tipicamente le righe di una tabella markdown. Lì
   aggiungere `-E` non ripara, **rompe**. Provato su un file di tre righe di cui
   due di tabella:
   ```
   grep -c  '^| `docs' prova.txt  -> 2   (le due righe di tabella)
   grep -cE '^| `docs' prova.txt  -> 3   (TUTTE: il ramo vuoto matcha)
   ```
   Uno degli otto era un documento di questo stesso perimetro, e la cura
   suggerita lo avrebbe peggiorato.
3. `\|` dentro una riga di **tabella** è ambiguo e non si decide
   meccanicamente: nel markdown la barra di una cella si scrive `\|`, quindi il
   comando vero potrebbe avere la barra nuda. Si elenca e lo legge una persona.

E tace sulla pipe della **shell** (`grep "x" f | head`), che è la metà che
decide se il presidio verrà usato.

```
python scripts/grep_nelle_mappe.py --autotest -> 15 casi su 15, VERDE EXIT=0
python scripts/grep_nelle_mappe.py --cartella <403 documenti> -> ROSSO 3, EXIT=1
python -m pytest tests/test_grep_nelle_mappe.py -q -> 8 passed EXIT=0
compile() dei due file                        -> ZERO SyntaxWarning
```

**Limite trovato scrivendo questa pagina.** Il righello si accende **su questa
pagina**, tre volte, perché l'elenco qui sopra **cita** i tre comandi difettosi.
Un registro dei reperti contiene per forza la forma che il righello cerca: è di
nuovo «il righello descrive la forma, non l'oggetto», e qui colpisce il
documento che quella classe la racconta. Oggi non fa danno — il perimetro in CI
è `docs/stato-reale/mappa/`, dove questa pagina non sta — ma il giorno che il
perimetro si allarga la cura è distinguere un comando **scritto per essere
eseguito** da uno **citato come reperto**, non togliere l'elenco.

---

## ⑦ R8 su sé stesso — il «debito» dei 13 elenchi ritirato: zero su tredici

In `copie.py` c'era un contatore chiamato **«debito»**, attribuito a T49, che
doveva **scendere**: gli elenchi letterali contenenti `quarantined` e non
`user_belief`. Col merge di T49 (`32273665`) **non è sceso**: 13 ieri, 13 oggi.

Letti tutti e tredici i posti uno per uno:

```
cli.py:4255                l'enum canonico per la PRESENTAZIONE
cli.py:4683                la validazione dello status dopo il gate
client.py:1207             `withheld_despite_judge` su UN fatto
flow_events.py:353         idem, nel journal
mcp_server.py:14263        idem, dalla porta MCP
gateway.py:1746            le AZIONI del gate
trust_ledger.py:30         _ACTIONS: `admitted` e `abstained` non sono nemmeno
                           status — falsi positivi puri
entity_populate.py:111     esclusione VOLUTA dal grafo entità
provenance_signing.py:142  esclusione VOLUTA dalla firma
tier2_judge.py:296         esclusione VOLUTA dal giudice T2
semantic.py:3460/3488/3516 esclusioni VOLUTE (grafo, riconciliazione,
                           auto-conferma)
```

**Zero su tredici** erano «una porta che serve i quarantenati come veri» — la
cosa che il nome prometteva e che T49 ha davvero curato con una superficie sola.
Il numero non è sceso perché **non misurava T49**.

E c'è di peggio di un numero inutile: quel contatore pretendeva di **scendere**,
cioè chiedeva di togliere **sei esclusioni corrette**. Un righello che spinge
nella direzione sbagliata è peggio di nessun righello: chi lo prende sul serio
rompe il prodotto per far scendere una cifra. E sarebbe restato lì a lungo,
perché **un numero fermo sembra un presidio che veglia**.

La lezione: **contare le occorrenze di una forma non misura una funzione.** È la
stessa cosa scritta due volte in due giorni sui righelli altrui (grep che trova,
`ast` che conta), fatta in casa senza accorgersene. Chi vuole misurare T49 conta
i chiamanti di recupero che non nascondono gli status bassi: quel test esiste
altrove ed è verde.

Il test resta come **lapide**: se qualcuno rimette il tetto senza rifare il
criterio, diventa rosso e trova lì il motivo. È R8 («una regola senza violazioni
contate si archivia») applicata a sé il giorno dopo averla scritta. Gli altri
sei tetti restano: misurano copie, e le copie le sanno contare.

---

## ⑧ Il postmortem di T38 arriva sul tronco, con la causa vera e il margine in tick

La correzione del postmortem di T38 esisteva ma viveva sul ramo di una richiesta
che il coordinamento ha deciso di **non** fondere. Sul tronco sarebbe entrata la
versione del 09/09 che dice «causa NON PROVATA, cura nessuna, controllo
NESSUNO» — uno stato del mondo superato da due giorni.

**La correzione dell'ipotesi 2**, dichiarata ESCLUSA e che era **la causa**:
`time.monotonic()` su windows è `GetTickCount64` (0,015625 s) fino a py3.12 e
`QueryPerformanceCounter` (1e-07) da py3.13; il job che cade è py3.12 e la
misura era stata fatta su py3.13. La riga della tabella dice «NON ERA ESCLUSA»
invece di essere cancellata: **chi ha letto la versione sbagliata deve
incontrare la correzione nello stesso posto.**

**Il margine contato in tick** invece che in millisecondi (11/09):

```
cella                                         cooldown attesa margine tick
a_tripped_breaker_rearms_after_the_cooldown      0,3    0,35   50 ms  3,2
cold_trip_rearms_and_forgets_the_cold_count      0,3    0,35   50 ms  3,2
fusion_breaker_rearms_after_the_cooldown         0,3    0,35   50 ms  3,2
the_recall_gate_sees_the_rearm                   2,0    2,1   100 ms  6,4
no_overrun_is_lost_when_a_rearm_is_in_flight    0,05    0,06   10 ms  0,64
cooldown_zero_keeps_the_trip_standing            0      0,05    --     --
```

La cella più esposta non era «stretta»: era **sotto un tick**. 0,64 tick non è
un margine piccolo, è **un margine che quell'orologio non sa rappresentare**. In
millisecondi sembra una soglia da allargare; in tick si vede che è una quantità
che non esiste. E le celle a rischio sono **cinque**, non una.
