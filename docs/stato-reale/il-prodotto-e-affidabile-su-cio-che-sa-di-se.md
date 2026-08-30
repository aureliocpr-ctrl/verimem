# Ciò che il prodotto fa e ciò che dice di fare invecchiano a velocità diverse

*30/08. **Diciotto** promesse **dichiarate** del prodotto, misurate una per una
fra le **12:19 e le 22:10** (ore lette, non stimate). Le misure erano sparse fra
banchi eseguibili e messaggi di canale, e sparse **non le legge nessuno** —
questo documento le mette in fila e, per ognuna, dice anche **su quanti casi si
applica**.*

⚠️ **Il titolo di questo file era «Il prodotto è affidabile su ciò che sa di
sé»**, ed era la tesi delle prime tredici. Le cinque della notte l'hanno
falsificata: il nome è cambiato quando è cambiato ciò che il documento
dimostra, perché **un titolo che afferma una tesi caduta è un guardiano che
mente**. Il file resta lo stesso per non spezzare i riferimenti già dati.

---

## La tesi in una riga — ⚠️ RISCRITTA ALLE 22:50, PERCHÉ L'HO FALSIFICATA IO

> 🔴 **La tesi di questo documento fino alle 18:55 era: «ciò che il prodotto
> dichiara di sé regge; ciò che nessuno ha dichiarato è dove stanno i buchi».**
> **Fra le 20:50 e le 22:10 ho misurato altre cinque cose dichiarate, e
> NESSUNA delle cinque reggeva.** La tesi vecchia resta scritta qui sopra e
> non altrove: un documento che afferma una tesi falsificata dal proprio
> autore è il guardiano che mente.

**La tesi che regge alla misura di stanotte:**

> **Le promesse sui MECCANISMI reggono. Le promesse nelle DESCRIZIONI — i
> parametri di uno schema, il nome di un campo, il rimedio in fondo a una
> diagnosi — si staccano dal codice, e nessuno se ne accorge.**

E la ragione non è morale, è meccanica: **un meccanismo ha un test che lo
esercita; una descrizione no.** Delle cinque cadute stanotte, **zero avevano
un presidio** prima che ne scrivessi uno. ⚠️ Su diciotto misure è una
correlazione, non una legge — ma è falsificabile: *si cerchi una descrizione
presidiata che si sia staccata lo stesso.*

⇒ Per un analista la distinzione utile diventa: **fidarsi di ciò che il
prodotto FA e verificare ciò che il prodotto DICE di fare**, perché le due
cose invecchiano a velocità diverse.

---

## ⚠️ 31/08, 01:40 — LA TESI DI STANOTTE È FALSIFICATA, E DAI MIEI STESSI DATI

Fra le **00:00 e le 01:35** ho misurato **altre dodici** promesse dichiarate,
con lo stesso metodo. La tesi qui sopra prevedeva: *meccanismi reggono,
descrizioni no*. **Cade in ENTRAMBE le direzioni.**

**Meccanismi che NON reggevano** — la parte che la tesi escludeva:

| meccanismo | cosa faceva |
|---|---|
| la guardia sul ranking degradato in `temporal_context.py` | col ranking degradato un pavimento **svuotava** la porta della cronaca: astensione falsa |
| la stessa guardia in `trust_report.py` | il dossier si svuotava **dichiarando** l'astensione (`abstained: true`) |

Due meccanismi rotti, e nessuno dei due era «una descrizione invecchiata».

**Descrizioni SENZA presidio che reggevano** — la parte che la tesi non
prevedeva: `trust_signals` (i tre campi promessi, e nessuno quando il flag è
falso) · `min_status` (la gerarchia dichiarata, applicata) · **«Pure-local»**
· **«~250ms»** (misurato: 11–15 ms a caldo, ~16x di margine).

⇒ **La natura della promessa — meccanismo o descrizione — NON predice se
regga.** La correlazione delle prime diciotto era vera del campione, non della
causa: avevo misurato soprattutto descrizioni non presidiate, e trovato che non
reggevano.

### La tesi che i dati di stanotte sostengono

> 🔑 **Il difetto sta dove la STESSA COSA è fatta in PIÙ PUNTI e uno è stato
> dimenticato.** Non conta se il punto dimenticato sia codice o prosa: conta
> che nessuno abbia chiesto *«chi ALTRO fa la stessa cosa?»*.

Le sei cure di stanotte, una per una: il pavimento è applicato in **cinque**
punti e **due** non guardavano il degrado · l'interruttore del pavimento è
letto da **tre** porte MCP e **una** non lo legge · il campo `min_relevance`
è nella ricevuta di **due** porte e **una** taceva · le porte dei fatti sono
**due** e la guida le trattava come **una** · il rimedio `llm=` era in **sei**
copie · i quarantinati si leggono da **una** porta e la guida non la nominava.

**Sei difetti su sei in punti ripetuti.** Ed è falsificabile in modo netto:
*si cerchi un difetto di stanotte che stia in un punto UNICO.* Io non ne ho.

⚠️ **E la prova più forte è contro di me**: alle 01:22 ho dovuto correggere
un'affermazione fatta qui un'ora prima («il presidio anti-spoof non nominava
`deep`») perché avevo sweepato **solo il file che stavo leggendo** — cioè ho
commesso la classe **mentre la citavo**. Una regola che si conosce non è una
regola che si applica; il presidio non è saperla, è **il controllo**: prima di
dire «non presidiato», `git grep` su TUTTI i test e **leggere i nomi**, perché
l'assert può stare due righe sotto la parola cercata.

📌 **Cosa resta vero della tesi vecchia**: che una descrizione non ha un test
che la esercita, e quindi *quando* si stacca nessuno se ne accorge. È una
verità sulla RILEVABILITÀ, non sulla probabilità del difetto — e le due erano
confuse.

---

## Le tredici promesse

Ogni riga: la promessa **come è scritta nel prodotto**, la misura, il commit.
La colonna che conta di più è l'ultima.

| | promessa (dove è scritta) | misura | esito | **su quanti casi si applica** |
|---|---|---|---|---|
| ① | «SDK processes keep the synchronous one-time load» — `CHANGELOG:635` | 3 processi freschi, fonte che NEGA: **0/6** ammissioni a giudice freddo, controllo 6/6 | 🟢 | ⚠️ **non misurato**: quanti usino SDK contro MCP non è osservabile da qui |
| ② | «first write ~32 s → 0.3 s» — `CHANGELOG:716` | **18–36 s → 0,2–0,3 s**, stesso ordine su altra macchina | 🟢 | **una volta per processo**; quanti processi freschi, non misurato |
| ③ | «it is `grounding_score` that carries it … `status` no» — istruzioni MCP | **3/3**, e **un campo in più**: il layer `L4-skipped` separa «fonte non giudicata» da «nessuna fonte» | 🟢 | si applica **a chi legge i campi** — vedi ⑧ |
| ④ | «a session NOTE skips that screen … **the moat is UNAFFECTED: with a source**» — `agent_guide` | screen saltato **2/2**, moat gira **2/2** | 🟢 | ⚠️ **frequenza alta, rischio misurato NULLO**: `W7-70/71` di *Paragone* ha **letto** 24 casi — **0 self-claim nudi**, 11 resoconti e 13 misure — e il controfattuale dice che **senza l'eccezione la porta ne declasserebbe 21 su 24**. ⇒ *compensazione, non buco* |
| ⑤ | la promessa ③, verificata **sulla porta dove è scritta** | firme **identiche** SDK/MCP: `['0.56/False','null/True','null/False']` | 🟢 | entrambe le porte, regime pulito |
| ⑥ | «only when neither an llm nor the local model is present does the gate fail-open» — `README:64` | **binario, non temporale**: `DELEGATE_ONLY` 0 e 1 → **0/6** a freddo con modello presente | 🟢 | **installazioni senza modello**; non misurabile da qui |
| ⑦ | `doctor` esiste per dire perché manca un punteggio | modello assente → **`status='fail'`**, dice il path, distingue «con fonte → avviso» da «**senza fonte → nessun avviso**» | 🟢 | chi esegue `doctor` |
| ⑧ | la separazione deve sopravvivere alla **lettura** | SDK `recall` → gs 99.56 / `None`; MCP `hippo_facts_search` → espone `grounding_score` **e** `meta_narrative` | 🟢 | ⚠️ **«può», non «lo fa»**: quanti chiamanti guardino il campo non è misurabile da qui |
| ⑨ | «Retrieve FACTS with verimem_facts_search … verimem_recall is a DIFFERENT door … An empty list is an ANSWER, not an abstention» — `agent_guide:53`, **datata** (*Measured 2026-08-29 on a store of 60 facts and no episodes*) | **riprodotta senza volerlo sul mio store**: `hippo_recall` → `[]` con `episodes: 0`, mentre `hippo_facts_search` trovava gli stessi fatti | 🟢 | ⚠️ ho riprodotto il **fenomeno**, non i suoi numeri (20 / 5 / `[]`): altra popolazione. 🔴 **E la riga meglio scritta che ho incontrato oggi non mi ha impedito l'errore, perché non l'avevo aperta** |
| ⑩ | «538 of 634 chunks (84.9%) pointed at files that no longer existed, while the chunk text was present for 100% of them» — `agent_guide:77`, **l'unica riga del file senza data** | ri-misurata su `document_index.db` (sola lettura, **30/08 ore 17:22**): **683** chunk — orfani **634/683 = 92,8%**, testo conservato **683/683 = 100,0%** | 🟡 | **la sostanza regge** e il **100% è esatto** sulla popolazione cresciuta; **è il tasso a essere invecchiato**, 84,9% → 92,8%. 🎭 E «634» compare nei due referti in **ruoli diversi** — *totale* ieri, *mancanti* oggi ⇒ chi li confrontasse di sfuggita concluderebbe «nulla è cambiato» |
| ⑪ | «`verified_by` records WHO vouches for a fact and **does not run this check**» — istruzioni MCP | **4/4**: né `status` né `grounding_score` si muovono, a giudice **presente** e **assente** | 🟢 | ⚠️ **con il controllo attaccato**: su un self-claim **nudo** il campo *cambia* l'esito (sposta la provenienza, `L1` non si applica più) ⇒ il 4/4 non misura un campo inerte. E il **costo del bypass è dichiarato**: `verified_by` lo scrive il chiamante e nessuno lo verifica |
| ⑫ | «the fact **leaves** the `quarantine_log` because it is live again» + «Without the audit trail **the keys still exist**» — docstring di `restore` | **2/2**: log **vuoto** dopo il restore; `reason` e `layers` presenti **anche senza audit** (`reason=None`, nessun `KeyError`) | 🟢 | ⚠️ **trappola d'uso, non difetto**: l'audit si accende con **`VERIMEM_AUDIT_LOG=1`** — con l'env sbagliata si legge `reason: None` e si conclude che il prodotto non registra il perché. Acceso, il `reason` porta i **sotto-strati** (`L1.10/15/20`), non solo `L1` |
| ⑬ | «A governance action must be as visible as the decision it reverses» — `semantic.py`, commento del 2026-08-05 | **due eventi uniti dal `fact_id`**: `flow.write` (`status=quarantined`, `layers=[L1.10,L1.15,L1.20]`) e `fact_restored` (`to_status`, `reason` **del restore**) | 🟢 | ⚠️ **la sfumatura che cambia cosa si può promettere**: `flow.write` porta i **layer**, non la **frase** dell'avviso ⇒ *«la storia non si perde: si ricompone da due eventi, e il perché resta come **layer**, non come frase»* |

Banchi eseguibili: `ws3-il-giudice-freddo-ammette-e-lo-dichiara.py` (① ② ⑥ ⑦) ·
`ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py` (③ ⑧) ·
`ws3-le-due-porte-separano-gli-stessi-tre-stati.py` (⑤) ·
`ws3-la-guida-dichiara-la-propria-eccezione-e-vera.py` (④) ·
`ws3-verified-by-conta-per-la-provenienza-e-non-fa-girare-il-moat.py` (⑪).

⚠️ **⑨ ⑩ ⑫ ⑬ non hanno un banco**: sono misure dirette, e perché siano
rifacibili la ricetta sta qui invece che in prosa. **⑩** legge
`~/.engram/documents/document_index.db`, tabella `chunks`, in **sola lettura**
(quanti `uri` non risolvono / totale). **⑫ ⑬** girano su store temporaneo
(`HIPPO_DATA_DIR=$(mktemp -d)`) con **`VERIMEM_AUDIT_LOG=1`** acceso e spento:
si legge il `quarantine_log` prima e dopo `quarantine_restore`, poi gli eventi
del journal filtrati per `fact_id`. **⑨** non è rifacibile a comando: l'ho
riprodotta sbagliando porta, e l'ho scritta perché l'errore è il reperto.
⛔ Lo store di Aurelio non è mai in scrittura.

---

## 🔑 La colonna che ho imparato a pretendere oggi

La quarta riga è quella che insegna. Ieri avevo verificato l'eccezione
`meta_narrative` e concluso: *«la guida descrive con precisione il proprio buco,
e il moat resta a proteggere»*. **Il meccanismo era ed è vero.** Ma la guida
dice «**with a source** it runs in both modes», e **nei miei quattro casi la
fonte l'avevo messa io**.

Poi *Paragone* ha misurato che il **65% del corpus** salta quello screen, e io ne
ho dedotto un rischio: *«quei fatti non hanno fonte, quindi non sono protetti»*.

> 🔑 **Verificare una garanzia condizionale senza misurare la frequenza della
> condizione produce un verdetto VERO e una rassicurazione FALSA.**

🔴 **E POI HO SBAGLIATO UNA SECONDA VOLTA, NELLA DIREZIONE OPPOSTA.** `W7-70` e
`W7-71` (*Paragone*, 15:40 e 15:49) hanno **letto** quei fatti invece di
contarli: su 24 casi campionati **uno ogni 14** — **11 resoconti · 13 misure
verificabili · ZERO self-claim nudi**. E il controfattuale, che è la misura
giusta: **senza l'eccezione la porta ne declasserebbe 21 su 24**, quasi tutti per
`L1.13`. ⇒ **L'eccezione non è un buco lasciato aperto: è una compensazione
misurata**, su un vocabolario — *completo, chiuso, verificato, testato* — che è
quello con cui si parla di CI e di cicli di lavoro.

🔑 **La lezione va raffinata, non buttata**: la frequenza da sola **non dice se
il rischio si realizzi**. Serve il **controfattuale** — *cosa farebbe il layer se
girasse?* Io avevo ragionato su ciò che il layer **non fa**, senza chiedermi cosa
succederebbe se lo facesse.
⇒ **Ho preso un numero e ne ho dedotto un rischio senza leggere la popolazione**,
che è la mia stessa regola («leggi le righe, non contarle») applicata al log
della suite e **non** al numero di un altro.

⇒ Da qui la colonna «su quanti casi si applica». Tre delle tredici **non sono
misurabili da dentro il repo**, e sono dichiarate tali: *quanti usano SDK contro
MCP*, *quanti processi freschi*, *quanti chiamanti leggono i campi*. **Dichiarate,
non stimate.**

---

## 🔴 Il contrappeso: ciò che non regge è ciò che nessuno ha dichiarato

- ✅ **CURATO alle 17:34** — la guardia anti-eco è **in servizio**
  (`l1_completion_detector.py`, votata 3/3, e il commento cita il mio banco).
  Ri-eseguito come test di accettazione: **5/5 → 0/5**, controllo 5/5 retto.
  ⚠️ *E io avevo protestato due volte che fosse «ferma senza assegnazione»,
  mentre era già curata nel file del mio perimetro: non l'avevo riletto.*
  **Il perdono di `L1.13` era a comando del chiamante — 5/5.** Basta ripassare il
  claim come `source`: il testo del match compare verbatim **per costruzione**.
  Il commit che introduce il perdono dichiara «*una self-claim senza fonte resta
  fermata*» — vero alla lettera; ciò che non nomina è che **chi scrive la fonte
  è chi scrive il claim**. `a7f39bf0`
- **Le sei radici di `L1.13`** (*Paragone*, `a83d9605`): un sinonimo fuori
  dall'elenco aggira il layer **senza fonte**. Due vie indipendenti sullo stesso
  strato; la protezione residua è **gergo di collaudo**, e un verbale d'ufficio
  non ne ha nessuno.
- **Il buco dell'irrilevante**: 8 claim su 12 ottengono `moat: passed` senza che
  la fonte ne parli; ne entrano 2. La causa resta **ignota** — sei spiegazioni
  proposte e falsificate.
  ⚠️ **Ma NON è un limite non dichiarato, e la riga va spostata**: il `README`
  lo nomina come *known gap* — «*a **plausible added inference the source never
  states** … scores high and is admitted*» — con **due date e due numeri** (0 il
  18/07, **4** il 25/08), il comando per rifarlo, e persino «*Run it yourself
  before trusting either number*». ⇒ **La mia misura è una conferma
  indipendente di un limite che il prodotto dichiara**, non un difetto nascosto.
- ⚠️ **L'asimmetria fra le porte — L'UNICO ANCORA APERTO**: con modello locale
  assente e daemon vivo, **l'SDK ammette un claim che la sua fonte NEGA, MCP lo
  ferma**. Localizzato a `anti_confab_gate.py:2350-2352`: `_have_judge` chiede
  «*il modello è su disco?*» per rispondere a «*c'è un giudice?*», e **il daemon
  non è nell'elenco**. `e4c1f199` · `1090f1fd`
  📌 **È anche il più difficile dei quattro**: tocca **ogni scrittura**, e la cura
  non è cambiare il predicato ma **spostare la decisione** — `judge_state()`
  diventa `delegated` solo **dopo** una delega riuscita, quindi *nessun pre-check
  può sapere se il daemon risponderà*.

### Il contrappeso, ricontato alle 17:45 — e tre su quattro erano già curati

| reperto | stato |
|---|---|
| perdono `L1.13` a comando (5/5) | ✅ **curato** — guardia anti-eco in servizio; il mio banco è il suo test: **5/5 → 0/5** |
| `cli.py` «*would store as provisional*» (utente-visibile) | ✅ **curato** `b2fc39af`, **15 min** dopo la segnalazione |
| `l1_orphan_detector.py` idem | ✅ **curato** `31f1335e` |
| `_have_judge` / asimmetria porte | ⚠️ **aperto** — il più difficile |
| buco dell'irrilevante | ⚠️ **non è un difetto nascosto**: *known gap* dichiarato nel README |

🔑 **E la lezione operativa si misura**: alle 16:15 e 16:35 ho **reclamato** che un
lavoro fosse fermo — **era già fatto**. Alle 16:50 ho **segnalato** due difetti
con la riga e l'evidenza, **senza chiedere** — **curati entro 15 minuti**.
⇒ *La segnalazione fattuale funziona meglio della protesta, e oggi la differenza
è misurata: 0 su 1 contro 2 su 2.*

---

## Cosa NON dice questo documento

- **Non dice che il prodotto sia a posto.** Dice che le sue **dichiarazioni**
  reggono. Sono due cose diverse, e la seconda non implica la prima.
- **Non è un campione rappresentativo.** Le tredici promesse **le ho scelte io**,
  guardando dove il prodotto parla di sé. Un altro ne sceglierebbe altre, e
  soprattutto: **ho misurato ciò che il prodotto DICHIARA**, quindi per
  costruzione questa tabella non può trovare i buchi di cui nessuno parla.
- **Non misura il traffico reale.** Tutti i banchi girano su store temporanei,
  con claim scritti da me, in italiano e inglese, e i numeri di frequenza
  mancanti sono segnati come mancanti.
- **Non assolve i miei banchi.** Oggi ho contato **dodici difetti nel mio
  misuratore**, e la famiglia dominante è una sola: *la popolazione non
  conteneva ciò che credevo di misurare* — regime ereditato invece che scelto,
  casi non appaiati, uno stato che non si produce, due fatti che si mangiano a
  vicenda per `same-source`, uno strumento che interroga un'altra tabella, e
  **il decimo non in un banco ma in un ragionamento**: un numero altrui letto
  come rischio senza guardare i fatti che lo componevano. Gli ultimi due sono
  della stessa famiglia e li ho presi **prima** di pubblicare: due criteri di
  conteggio diversi spacciati per confronto («35 layer» contro «quattordici»), e
  una env inventata (`ENGRAM_QUARANTINE_AUDIT`) al posto di quella vera
  (`VERIMEM_AUDIT_LOG`), trovata **leggendo il test del prodotto**.
  ⇒ **Ogni banco qui citato ha ora un controllo che fallisce se la popolazione
  non c'è**, ed è l'unica ragione per cui questi numeri si possono leggere.

## La classe del giorno: la prosa resta ferma dove il codice si è mosso

Quattro istanze, **tre autori diversi**, una forma sola:

| | dove | l'affermazione | il codice |
|---|---|---|---|
| ① | `quantity_match` (mia) | «saltando le **DUE** potature» | ne avevo aggiunta una **terza**, fuori dall'esenzione |
| ② | `anti_confab_gate:2336` | tre vie al giudizio elencate | **il daemon non è nell'elenco** |
| ③ | `anti_confab_gate:24,296` | il downgrade forza `provisional` | scrive **`quarantined`**, in 7 punti |
| ④ | `anti_confab_gate:902` | `return False` (il default vecchio) | il default è **`return True`** — riga **irraggiungibile** |

⇒ Dopo la terza ho smesso di aspettare la quarta e ho usato **la classe come
setaccio**: `git grep` sulle affermazioni che nominano un conteggio, nel mio
perimetro. **Otto candidati, un difetto vero** (④, curato `613306f7`), **sette
no** — e lo dico con la stessa forza con cui avrei annunciato sette reperti.

🟢 **Due dei sette sono la FORMA GIUSTA, e sono già nel prodotto**:
`anti_confab_gate:1196` («*MISURATO su **quattro** aggiornamenti legittimi ne
blocca **due***» — **e li elenca**) e `mcp_server:8159` («*nessuna delle **tre**
superfici (mcp_server 0, cli 0, client 0)*» — **nomina superfici e numeri**).
**Si auto-verificano**: fra sei mesi qualcuno può contare.

🔑 **E il reperto di metodo vale più del difetto.** Due candidati —
«*i **quattordici** layer*», «*i **tre** detector*» — **non sono nemmeno
verificabili**: il mio contatore dà 35 e 4, ma **conto una cosa diversa** (il 35
include varianti `-observe`/`-graded`; «detector» non è «punto di import»).

> **Il puntatore non serve solo a tenere il numero aggiornato: serve a renderlo
> VERIFICABILE.** Un numero senza il suo criterio di conteggio non si può
> nemmeno controllare — e quindi **non invecchia mai visibilmente**.

⇒ È **peggio** di un numero sbagliato: quello prima o poi qualcuno lo smentisce;
un numero **non verificabile** non lo smentisce nessuno. Stessa famiglia di
*«una misura che non c'è si legge come perfetta»*.
📌 **Proposta**: *un'affermazione che nomina un numero, un elenco o uno stato
dica **dove sta scritto nel codice** — o, se è un conteggio, **con quale criterio
si conta**.* Non serve un test: gli esempi buoni sono già nel repo.

### La regola, dimostrata invece che argomentata

`agent_guide.py:77` — la guida che **ogni agente legge** — promette:

> *Measured on a real corpus: **538 of 634** chunks (84.9%) pointed at files that
> no longer existed, while the chunk text was present for **100%** of them.*

È **la forma giusta al massimo grado**: numero · criterio (*cosa* conta) ·
popolazione · contrasto · conclusione operativa. **Manca solo la DATA.** Ho
provato a ri-misurarlo (store dei documenti, **sola lettura**, 30/08 ore 16:58):

```
73 documenti indicizzati
  uri che NON esiste più   42  (57,5%)
  content conservato       73/73  (100%)
  esempi: contract.txt · docs\ROADMAP-v0.7.md · …\Temp\claude\…
```

🟢 **La sostanza REGGE su una popolazione indipendente**: i path si perdono, il
contenuto resta **al 100%** — e con esso la conclusione operativa, *la citazione
è esatta sull'indice, non è una garanzia di riaprire l'originale*. 🟢 **E la
guida nomina già la causa giusta** («*a RELATIVE path resolved from a different
working directory*»): i miei esempi sono esattamente path **relativi** e
**temporanei**.

⚠️ Quella prima misura era sui **73 documenti**, non sui **634 chunk**:
popolazione sbagliata, e il numero non era confrontabile. **Trovata la
popolazione giusta** (`~/.engram/documents/document_index.db`, tabella `chunks`)
e ri-misurata — **30/08, ore 17:22, sola lettura**:

```
chunk oggi                683        (la guida dichiarava 634 come TOTALE)
file che non esiste più   634 / 683   = 92,8%   (la guida: 538/634 = 84,9%)
testo conservato          683 / 683   = 100,0%  (la guida: 100%)   ← ESATTO
```

🟢 **Il 100% regge ESATTAMENTE** sulla popolazione cresciuta: **683 su 683**. La
promessa più forte della guida è verificata.
🔴 **Il tasso è INVECCHIATO**: **84,9% → 92,8%**. Il corpus è cresciuto (634 →
683 chunk) e i file mancanti sono cresciuti di più (538 → 634).

🎭 **E LA COINCIDENZA CHE VALE PIÙ DEL NUMERO**: **634 compare in entrambi, ma
come grandezze DIVERSE** — nella guida è il **totale dei chunk**, oggi è il
**numero di quelli mancanti**. ⇒ Chi confrontasse i due referti di sfuggita
vedrebbe «634» in tutt'e due e concluderebbe che **nulla è cambiato**.

🔑 **Il pericolo che la regola previene si è materializzato davanti a me**: lo
stesso numero, due ruoli, due date. Senza la data **e** la grandezza contata,
questo è invisibile. *Non l'ho argomentato: l'ho incontrato.*
📌 Il numero aggiornato, con la sua data e il suo criterio, è qui sopra: **chi
mantiene `agent_guide.py` ha tutto per rimetterlo in riga.**

### E la correlazione è perfetta su tre righe — con una coda che è su di me

`agent_guide.py` ha **tre** affermazioni misurate. Le ho guardate tutte:

| riga | data? | esito |
|---|---|---|
| `:32` eccezione `meta_narrative` | ✅ «*measured **2026-08-28***» | **regge** (2/2 e 2/2) |
| `:53` le tre porte del recupero | ✅ «*Measured **2026-08-29** on a store of **60 facts and no episodes***» | **regge** — vedi sotto |
| `:77` i chunk orfani | ❌ nessuna data | **invecchiata**: 84,9% → 92,8% |

🔑 **Le due datate reggono; l'unica senza data è l'unica invecchiata.** N=3 è
piccolissimo e la correlazione non è una prova — **ma il meccanismo non è
statistico, è causale**: senza data nessuno *può* accorgersi.

🔴 **E `:53` la ho verificata nel modo peggiore: sbagliando.** Dice, con data,
popolazione, regime (*sopra il floor di 50 fatti, dove il recupero cambia
percorso*), **tre** numeri e la lezione operativa::

    verimem_facts_search  20 hits  ·  verimem_facts_recall  5  ·  verimem_recall  []
    «An empty list is an ANSWER, not an abstention — read it as "wrong door",
     not as "the store knows nothing".»

Alle 15:45, misurando altro, ho interrogato `hippo_recall` cercando **fatti**, ho
ottenuto `[]`, e ho creduto per qualche minuto che **MCP non vedesse i fatti
dell'SDK** — un reperto grave che non esisteva. **Il prodotto me lo aveva scritto,
con i numeri, e non l'avevo letto.**

🔑 **Quindi la regola sul numero verificabile NON basta, e va detto qui.** La riga
**meglio scritta** che ho incontrato oggi — data, popolazione, regime, tre
numeri, conclusione operativa — **non mi ha impedito l'errore, perché non l'ho
aperta.** ⇒ *Il presidio non è scrivere meglio: è **leggere prima di misurare**.*
Le due metà stanno insieme — **un'affermazione perfetta serve solo a chi la
legge**, e chi misura senza aver letto rifà il lavoro che il prodotto ha già
fatto e a volte lo rifà male.

### Due setacci, 1 difetto e 0 — e il secondo zero conta quanto il primo uno

Ho cercato difetti in due modi **sistematici**, non aspettando che emergessero:

| setaccio | segnale cercato | candidati | difetti |
|---|---|---|---|
| ① | prosa che **nomina un conteggio** («le due potature», «i tre detector») | 8 | **1** (riga irraggiungibile) |
| ② | **una nota di cautela contro una funzione** in un chiamante e non negli altri | 7 | **0** |

Il secondo nasce da un'osservazione precisa: *se un chiamante scrive «**I PESI**,
non `local_ce_available()`», quella nota è la prova che la funzione inganna — e
che gli altri chiamanti non lo sanno.* Ha funzionato **una volta**
(`local_ce_available`, due vittime) e **non ha prodotto altro**:

- `client.py:3210` — «*`label(…)` risponde True, il DB contiene …*» → è la
  **cronaca di una cura già fatta**, non un difetto aperto. *(E la sua forma è
  la mia: «si scriveva e non si rileggeva» — qualcuno aveva già posto la
  domanda dell'⑧ su un altro campo.)*
- `telemetry_analyzer.py:88` — «*`str.isprintable()` non basta*» → **unico
  chiamante, e applica già la cautela** (`c.isprintable() and c not in
  _INVISIBILI`).
- gli altri tre sono **soglie e regex**, non giunture fra componenti.

🔑 **Il segnale è preciso ma raro: è un rilevatore, non un setaccio produttivo.**
E il bilancio va letto per quello che dice: **cercando attivamente in due modi
diversi, il repo ha restituito un difetto morto e una giuntura già nota per
metà.** ⇒ *È più pulito di quanto la caccia suggerisse* — e questo è un
risultato, non l'assenza di uno.

## Le cinque promesse della notte, e perché sono un'altra famiglia

*Misurate fra le 20:50 e le 22:10, dopo il rientro. Non stanno nella tabella
sopra perché non sono dello stesso tipo: quelle erano promesse su cosa il gate
**fa**; queste sono promesse su cosa i suoi **parametri e i suoi campi
significano** — ed è esattamente la differenza che la tesi nuova nomina.*

| | dove | la promessa | la misura | esito |
|---|---|---|---|---|
| A | schema MCP, `validate` | «`off` = **bypass**» | **non bypassa**: e' neutralizzato di proposito (args MCP untrusted) e la ricevuta lo dichiara in `gate_knobs_denied` — ma **DOPO** la decisione che doveva informare | 🔴 curata |
| B | schema MCP, `validate` | «`fast` (default) = detector **sub-ms**» | con una `source` **il moat gira a ogni livello**: primo write **32.724 ms**, a caldo 187-340 ms — **quattro ordini di grandezza** | 🔴 curata |
| C | schema MCP, `gate_mode` | «`downgrade` persiste con `status='provisional'`» | scrive **`quarantined`**, su entrambe le popolazioni. **Terza superficie** con quella prosa; le altre due curate al mattino, **questa è la sola che legga un agente** | 🔴 curata |
| D | `doctor` e `cli`, sei copie | «pass `llm=` to Memory» | eseguibile **solo dall'SDK**: un chiamante CLI o MCP non può iniettarlo (su MCP lo configura l'**operatore**). E chi esegue `doctor` è **alla CLI** | 🔴 curata |
| E | la ricevuta, campo `ok` | *(nessuna: non era documentato)* | vale **sempre `True`**, anche sui quarantinati. Non un difetto di comportamento — `ok` = «la chiamata non è fallita» — ma **nessuna superficie lo diceva**, e un quarantinato **è memorizzato e fuori dal recall** | 🔴 curata |

⚠️ **E una sesta che NON ho curato**, perché la cura tocca due file su cui
un'altra stava lavorando: **`replaced` non dice che la scrittura ne ha mangiata
un'altra**. Misurato: due ricevute con `replaced=False` mentre nello store il
primo fatto porta `superseded_by`. `replaced` è il rimpiazzo **per id identico**,
che da quella porta non accade mai. ⇒ **Consegnato come reperto, non come cura.**

🔑 **La regolarità che le tiene insieme**: in tutte e sei **il comportamento era
giusto** e **la descrizione no**. Nessuna era un difetto del gate; tutte erano
difetti di ciò che il gate DICE — il perimetro che questo documento misura.

---

## Bilancio, alle 18:55 (ora letta)

**13 promesse misurate · 12 reggono piene · 1 regge la sostanza e invecchia il
tasso** (⑩). ⇒ *Su tredici affermazioni che il prodotto fa di sé, tredici sono
vere; una porta un numero vecchio — ed è l'unica riga del suo file senza data.*

🔑 **Il metodo che le ha rette tutte è sempre lo stesso**, e sono quattro mosse:

1. **cerca se è già PRESCRITTO** — tre volte oggi il prodotto aveva già scritto
   ciò che stavo per misurare, una volta con i numeri e la data;
2. **misura con il controllo che deve poter fallire** — senza, ⑨⑪ sarebbero
   stati indistinguibili da un campo inerte;
3. **dichiara il regime** — embedding, grafia (`e'` contro `è` muove il
   *punteggio*, non il *verdetto*), env, porta;
4. **di' cosa NON hai misurato.**

⚠️ **La quarta è quella che ha reso di più, e non me l'aspettavo.** Alle 18:51
avevo chiuso ⑫ scrivendo *«dopo il restore la ragione dovrebbe sopravvivere
nell'evento, ma non l'ho verificato»*. Verificarlo quattro minuti dopo ha
prodotto ⑬ **e** la sua sfumatura — *layer contro frase* — che **nessuno avrebbe
trovato se avessi scritto «regge» e basta.**

## Una regola pratica, che vale oltre questo prodotto

> **Quando un banco stampa `[]` o `0`, la prima ipotesi non è «il prodotto non
> lo fa»: è «non gliel'ho chiesto».**

Oggi mi ha impedito di pubblicare **tre** volte un reperto grave che non
esisteva: *«MCP non vede i fatti dell'SDK»* (smontato facendo scrivere a MCP
**un fatto suo** e chiedendogli di ritrovarlo), *«il recall è vuoto»* (era la
porta degli EPISODI), e stasera *«il `quarantine_log` non registra il
perché»* — avevo acceso `ENGRAM_QUARANTINE_AUDIT`, che **non esiste**. La
env vera è `VERIMEM_AUDIT_LOG`, e l'ho trovata **leggendo il test del
prodotto** invece di indovinare.

**Agent: Galileo**
