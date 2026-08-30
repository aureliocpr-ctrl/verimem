# I 28 rossi della suite, letti uno per uno

*ws3 «Galileo», 30/08. Risposta a una domanda di Aurelio rimasta aperta quindici
ore: «**sei sicuro che la versione funziona, o è l'ennesima cazzata rotta?**»*

## Il verdetto, con ciò che lo rende un verdetto

`python scripts/suite_a_fette.py --fette 3`, avviata 12:19, letta dai file:

```
fetta 0  EXIT=1  = 16 failed, 3803 passed, 11 skipped, 24 xfailed in 1279.81s =
fetta 1  EXIT=1  =  4 failed, 4670 passed,  6 skipped, 62 xfailed in 1558.04s =
fetta 2  EXIT=1  =  8 failed, 3769 passed,  6 skipped, 40 xfailed in 1162.99s =
EXIT=1        →   28 failed · 12242 passed · 23 skipped · 126 xfailed
```

`EXIT=` **accompagnato dai tre riepiloghi**: è la REGOLA-VERDE v3, e senza i
riepiloghi quel numero sarebbe stato la firma di come è morto il processo, non
un verdetto ([l'EXIT che non è un verdetto](l-exit-che-non-e-un-verdetto.md)).

🔑 **La risposta onesta è in due tempi**: **non è verde** — e **28 rossi non sono
28 difetti**. Contarli avrebbe mentito in entrambe le direzioni.

## Le sei classi

| | classe | n |
|---|---|---|
| ① | **regressione mia** (`29ab5544`, 28/08) | **4** |
| ② | **ambiente — questa macchina** | 10 |
| ③ | **servizio esterno** | 1 |
| ④ | **`XPASS(strict)`: guarigioni non registrate** (1 tolto, 2 a ws7) | 3 |
| ⑤ | **debito di presidio: un numero da aggiornare** | 4 |
| ⑥ | **prezzo di una cura altrui** (`e3ecd7f1`) | 6 |

### ② Ambiente (10) — dipendono da ciò che questa macchina ha

- **4 ricevuta** — `L4-skipped — source provided but the grounding judge was
  still loading`. **Catena completa, cinque anelli, tutti letti**:
  `HIPPO_ENCODE_DELEGATE_ONLY='1'` è **attiva in questo ambiente** e la suite la
  eredita → `_delegate_only()` True (`local_grounding.py:590`) →
  `judge_state()` restituisce `warming` (`:383`) → `_advisory_l4_skipped()`
  (`anti_confab_gate.py:1797`) → **il write è ammesso** con l'avviso, e i test
  che attendono `quarantined` cadono.
  🔑 *Non «la macchina è strana»: **quella riga di env**.*
  🟢 **E le due promesse che circondano il fail-open REGGONO** (banco
  [`ws3-il-giudice-freddo-ammette-e-lo-dichiara.py`](banchi/ws3-il-giudice-freddo-ammette-e-lo-dichiara.py)):
  «*SDK processes keep the synchronous one-time load*» → **0 ammissioni per
  giudice freddo su 6**, 3 processi freschi, controllo 6/6; «*first write ~32 s
  → 0.3 s*» → misurato **34,9-36,3 s → 0,27-0,34 s**, stesso ordine su un'altra
  macchina. *Un limite dichiarato è un debito: questo è pagato, e va detto con
  la stessa forza con cui direi il contrario.*
  ⚠️ **Resta aperto per chi lo possiede**: la suite eredita quella variabile e la
  CI probabilmente no ⇒ **i due regimi non misurano la stessa cosa**. E il test
  non dichiara il regime che richiede: la ricevuta lo spiega benissimo, l'assert
  che cade no.
- **3 daemon** — `ensure_running_spawns_when_unreachable`,
  `ensure_running_cooldown_blocks_double_spawn`,
  `l120_parla_quando_l_encoding_non_costa_un_cold_load`. I test vogliono il
  daemon **morto**; qui è **vivo**.
- **2 dimensioni** — `768d` trovati dove il test attende `384`, e viceversa.
- **1** `offline_embedding_makes_no_external_connection` — encoder `Unavailable`.

⚠️ *Un rosso che non si riproduce non è «instabile»: dipende da ciò che la tua
macchina ha e la loro no.* Per ognuno serve il regime, non l'etichetta.

### ④ I tre `XPASS(strict)`: tre guarigioni non registrate, **zero difetti**

Verificati uno per uno, non dedotti.

**Due sono la stessa cura, di *ws7*** (`test_la_ricetta_del_numero_deve_esistere`
· `test_repro_registry_g4`). Il marcatore diceva «*`benchmark/lme_retrieval_bench.py`
non esiste nel repo: il numero di README:22 è pubblicato e non rigenerabile*».
Il file **davvero non esiste** — ma la premessa del marcatore era sbagliata:
cella `LANT-21`, «*il modulo era **il nome sbagliato**, non un banco mancante*».
Il banco si chiama `longmemeval_runner`, il registro invocava un nome che *non è
mai esistito*, e corretto il comando il presidio passa da sé.

🔑 **E la risposta stava DENTRO il marcatore, marcata «non verificato», per
cinque giorni**: «*OWNER: chiunque ripristini il banco (@ws5 ha indicato
`longmemeval_runner.py`, **non verificato**)*». Era un lavoro da trenta secondi.
⇒ *Un `xfail(strict)` ben scritto documenta il difetto e con ciò gli toglie
l'urgenza: sembra già gestito.* È il costo nascosto del marcatore ben fatto, e
va contro il suo stesso pregio.

**Il terzo era MIO** — `test_il_package_non_porta_identificativi_di_sessione`,
`reason`: «*OWNER: @ws3 (è suo il commento e suo il banco)*». Il package portava
fuori il nome di un banco di sessione, citato da `anti_confab_gate.py`. Curato
da `fa850457` (29/08, *Agent: TARA*) rendendo i riferimenti navigabili per
argomento. Verificato il 30/08: `git grep -E "ws[0-9]-[a-z]" -- verimem/*.py` →
**zero occorrenze**. **Marcatore tolto** (`EXIT=1`, 1 failed → `EXIT=0`,
3 passed), come la sua stessa `reason` prescriveva.

📌 **Gli altri due restano a *ws7***: sono suoi il marcatore e la cura. Misuro e
propongo, non tocco i test altrui.

### ⑤ Debito (4) — presidi che chiedono un numero aggiornato

codice scollegato **39 contro 38** · divergenze **scese a 0** (nota 159) ·
**versione ferma da 1073 commit** (è il bump congelato in attesa di Aurelio) ·
un banco che non dichiara come guarda l'esito del subprocess.

### ⑥ Non era da capire: e' il prezzo di una cura (6)

Tutti i `test_quarantine_restore_public.py` e `test_quarantine_log_*`. Il
fixture disattiva il carve-out di dominio — `ENGRAM_L1_DOMAIN_PRECISION=0` —
per ottenere la quarantena legacy da cui partire, **e non la ottiene piu'**.

**Causa: `e3ecd7f1`** (28/08 23:44, *Agent: Paragone*, cura assegnata da
lead-audit) — «L1.13 non vedeva la fonte, e fermava i verbali d'ufficio che la
ricalcano». Il commit e' lavoro serio: RED→GREEN falsificato tre volte, presidio
nuovo, non-regressione verificata su **«i 6 file di test che toccano il
detector»**.

🔑 **Il fixture non era fra quei sei, e non poteva esserlo: non *testa* il
detector, lo *usa*** per fabbricare il falso positivo da restaurare. ⇒ *«Chi
tocca X» non e' «chi dipende da X».* E' la stessa classe del mio errore di
stamattina, specchiata: li' non ho detto al bivio che aggiungevo una potatura,
qui non si e' chiesto chi si appoggia all'esito.

#### Il reperto che vale piu' dei sei rossi

La cura perdona quando il `matched_text` compare **verbatim nella fonte**. Se la
fonte **e'** il claim, il verbatim c'e' **per costruzione**:

```
REGIME ENGRAM_L1_DOMAIN_PRECISION=0 · fonte = eco del claim
claim          senza fonte      fonte = eco
LEGALE  EN     FERMATO L1.13    passa
VERBALE IT     FERMATO L1.13    passa
AUDIT   EN     FERMATO L1.13    passa
SOFTWARE       FERMATO L1.13    passa
DEPLOY  IT     FERMATO L1.13    passa
controllo (fermati senza fonte) 5/5   ·   scappano con l'eco 5/5
```

Il commit dichiara: «*una self-claim senza fonte non ha nulla da perdonare e
resta fermata*» — **vero alla lettera**, 5/5. Cio' che non nomina e' che **chi
scrive la fonte e' chi scrive il claim**: il perdono diventa una scelta del
chiamante invece che una proprieta' della fonte.
🔑 E' il banco `ef234ae0` di lead-audit (fail-closed anti-auto-sorgente
aggirato **per riformulazione** 3/3) **da un lato nuovo**: qui non serve
riformulare, basta la copia identica. ⇒ La «guardia anti-eco» del voto del 28/08
ha ora una misura che la chiede. Banco:
[`ws3-il-perdono-si-compra-riscrivendo-il-claim-come-fonte.py`](banchi/ws3-il-perdono-si-compra-riscrivendo-il-claim-come-fonte.py).

🔴 **Rettifica, 13:55.** La prima stesura di questa sezione diceva **3/5** e
attribuiva la resistenza al **dominio** («si apre sui verbali, resta chiusa su
software»). **Falso, e il difetto stava nel mio banco**: due claim su cinque — e
solo quei due — contenevano «and **verified**», che sveglia `L1.15`, un detector
diverso che non c'entra col completamento. Tolta la parola, scappano anche
quelli. ⇒ *Un banco che varia due cose insieme non puo' attribuire l'effetto a
una,* ed e' **il secondo difetto nel misuratore in un'ora**.

⚠️ **5/5 non e' un tasso sul corpus**: e' la misura che la condizione del perdono
e' soddisfatta **per costruzione** dalla fonte-eco. Cio' che salva un claim reale
e' che porti *per caso* un'altra parola sorvegliata («verified», «fixed»,
«shipped») — e allora lo ferma un altro strato, per un'altra ragione. **Un
verbale d'ufficio non ne ha nessuno.**
📌 Si compone col banco di *Paragone* `a83d9605` («il perimetro di `L1.13` e' sei
radici»): li' il layer si aggira **cambiando parola** e senza fonte, qui
**passando il claim come fonte** e senza cambiare parola. **Due vie indipendenti
sullo stesso strato.**

#### E un errore mio nel misurare, corretto qui

Avevo prima misurato i tre regimi della leva concludendo «**la variabile non
morde**». **Falso: il difetto era nel mio misuratore** — tutte e tre le celle
avevano `source=CLAIM`, e la fonte-eco domina l'esito, quindi misuravo l'eco e
non la leva. Con la cella mancante: `LEGALE + PREC=0 + senza fonte` → `QUAR:L1`;
`PREC=1` → passa. **La leva morde.** *La prova che un criterio funziona e' che
togliendolo il numero cambi — e non l'avevo tolto.*

⚠️ **Discrepanza aperta**: la nota interna dice «`ENGRAM_L1_DOMAIN_PRECISION`
(oggi OFF)», `anti_confab_gate.py:185` dice «**DEFAULT ON** (flipped
2026-07-22)», e la misura conferma ON. Una delle due e' vecchia; il pavimento e'
di chi mantiene `L1`.


---

## ① I quattro rossi miei — e la diagnosi che ho dovuto ritirare

Il 28/08 ho introdotto `_spans_dei_riferimenti` (`29ab5544`): «*art. 3*» in un
claim è un puntatore a una norma, non la quantità 3. Il commit diceva «RED→GREEN
alla porta» — **TDD su un test mio**. La suite non girava, la CI non gira.

Ieri ho detto al gruppo: *conflitto fra due intenzioni legittime, non lo curo*.
**Falso per tre casi su quattro**, e l'ho scoperto leggendo invece di dedurre.

### Il difetto è la giuntura, e il commento diceva già il numero

`extract_quantities(text, *, come_fonte=False)` ha **un bivio solo**, e la sua
docstring lo dichiarava: «*`come_fonte=True` legge il testo INTERO, saltando le
**due** potature*».

```python
claim = text if come_fonte else _senza_identificatori(claim_span(text))  # il bivio
_date = _spans_delle_date(claim)
_riferimenti = _spans_dei_riferimenti(claim)      # ← la TERZA, due righe SOTTO
```

Misura sugli otto casi del presidio del 07/08, **entrambe le modalità**:

```
frase                     come CLAIM    come FONTE
grad.3                         {3.0}         {3.0}
temp.22                       {22.0}        {22.0}
l'art.15 del codice            set()         set()   ← invisibile anche alla fonte
vedi pag.7                     set()         set()   ←
il n.42 del registro          {42.0}        {42.0}
tot.300 pezzi                {300.0}       {300.0}
fig.3                          set()         set()   ←
Nr.5 im Lager                  {5.0}         {5.0}
                        CLAIM 5/8     FONTE 5/8
```

⇒ **Non era un presidio rimasto indietro: avevo accecato anche il lato fonte**,
dove quel numero è contenuto e non citazione. Il claim che lo cita sembra
inventarselo, e `L4.1` quarantina un fatto vero — **esattamente il difetto che
la modalità `come_fonte` era nata per chiudere il 16/08**.

**Cura, una riga, sul bivio** (`fb2ff485`):

```python
_riferimenti = [] if come_fonte else _spans_dei_riferimenti(claim)
```

RED→GREEN **falsificato e non sul test introdotto con la cura**: riga vecchia
`EXIT=1` (4 failed, 8 passed), riga nuova `EXIT=0` (12 passed). Sweep sui due
riceventi di `come_fonte=True` — `soggetto_valore`, `valore_non_nella_fonte` —
**36 passed, 1 xfailed**.

Il presidio nuovo misura **entrambe le popolazioni**: la fonte torna a vedere
8/8 **e** il claim continua a non affermare il numero del proprio riferimento
3/3. Con una metà sola si sarebbe potuto «curare» cancellando `29ab5544`.

### Il quarto resta rosso, e non lo curo io

`test_un_numero_che_la_fonte_NON_contiene_resta_assente` — il claim «*Il
riepilogo viene stampato alla **riga 999***» contro una fonte priva di 999.
`riga` è una delle parole della potatura, il claim non afferma più nulla, e
**l'assenza non viene più segnalata**. Il docstring di quel test lo aveva
previsto: «*leggere la fonte per intero non deve diventare un lasciapassare*».

Sul lato claim la potatura **è voluta**. Ma un riferimento **inventato** è
comunque una confabulazione: «alla riga 999» quando la riga 999 non esiste è
falso. ⇒ **Questo sì è design** — trattare i riferimenti come una classe a sé,
non ignorarli — e va deciso da chi mantiene il layer, non da me di corsa per far
tornare verde un numero.

---

## Cosa NON dice questo documento

- **Non dice che il prodotto sia rotto.** 12242 test passano. Dei 28 rossi, 18
  sono ambiente, debito o marcatori da togliere; 6 vanno capiti; **4 li ho messi
  io e 3 sono curati qui**.
- **Non dice che sia verde.** Non lo è, e il rosso più fresco è mio.
- **Non dice che `e3ecd7f1` sia una cura sbagliata.** Ha chiuso un difetto vero
  e con metodo. Dice che il suo criterio di non-regressione cercava i riceventi
  per argomento, e che il perdono introdotto e' a comando del chiamante.
- **Non dice quanto sia grave la via dell'eco**: 5 casi miei, 2 lingue, un solo
  sotto-strato. Se un chiamante reale la percorrerebbe, non l'ho misurato.

## Le due lezioni, che valgono oltre questo caso

1. **Un RED→GREEN sul proprio test non è una verifica: è una conferma.** Dice
   che la cura fa ciò che volevo, non che non rompa ciò che altri volevano.
   Senza CI verde il TDD locale non è una rete, è uno specchio.
2. **La lezione era nel commento, e nominava il numero.** «Le due potature»:
   chi aggiunge la terza deve dirlo al bivio, o l'esenzione smette di essere
   completa **senza che nessuna riga diventi rossa**. Contare le porte veniva
   prima di aprirne una nuova — sei moduli leggono quella funzione. *Il
   docstring ora dice TRE, le elenca tutte, e chiede alla quarta di registrarsi.*

**Agent: Galileo**
