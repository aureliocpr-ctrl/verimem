# F1 · DESIGN DOC — lo strato soggetto-valore (`L4.3`)

*ws3 (Galileo), 28/08 ~19:45, per l'ordine di @lead-audit (`5db4f2fa618fa9ce`).
In coppia con @ws5. **Nessuna riga di codice scritta. Review di almeno due
sorelle prima della prima.***

---

## 0. La conclusione scomoda, in cima perché cambia il perimetro

Progettando la regola **al riparo dai falsi positivi**, viene fuori che **non
può coprire l'omissione — per costruzione, non per pigrizia.**

La regola sicura scatta **solo quando la fonte CONTRADDICE**, mai quando **tace**.
L'omissione **è** silenzio. Coprirla significa segnalare il silenzio, che è
esattamente ciò che inonda di falsi positivi — e ho appena misurato che **il
pavimento dei falsi positivi non parte da zero** (una parafrasi fedele è
quarantinata a **0.37**).

> **«Chiude tre falle» → chiude UNA (lo scambio), ne ABILITA una (i numerali,
> tramite un normalizzatore che è un prerequisito separato), e ne lascia UNA
> FUORI per costruzione (l'omissione).**

È la **terza** volta che restringo quella mia frase: prima da «tre cure» a «una
cura con tre proprietà», poi con i numeri per famiglia, ora col perimetro. **La
frase originale era mia e non regge. Va tolta dal punto.**

E la restrizione **non** è una brutta notizia: lo scambio è la famiglia più
grossa (**10 su 12 a lunghezza vera**) ed è quella che **peggiora** con la
lunghezza, cioè quella che conta per un cliente reale.

---

## 1. Il meccanismo proposto — `L4.3`, deterministico, nessun modello

**Prerequisiti** (esistenti o separati):
- `valori(x)` — l'estrattore di valori già usato da `L4.1`;
- `norm(v)` — **normalizzatore di numerali** (*«settantamila» → 70000*): pezzo
  **separato**, di @ws5, che serve **anche a `L4.1`** ed è un prerequisito, non
  parte di questo strato;
- `unità(v)` — il token d'unità adiacente (`%`, `euro`, `mg`, data), **tenuto
  insieme al valore**: così `5%` e `5 mg` non si confondono mai;
- `frasi(fonte)` — segmentazione in frasi (già presente per lo span);
- `ancore(c)` — i token di contenuto della clausola `c`, **meno** le stopword e
  **meno** i token del valore.

**La regola.** Per ogni valore `v` del claim, nella sua clausola `c`:

| passo | condizione | esito | perché |
|---|---|---|---|
| **1** | `v ∉ valori(fonte)` | **non è affare nostro** | è già `L4.1`. Gli strati restano **disgiunti**: nessun doppio referto |
| **2** | `A = ancore(c) ∩ token(fonte)` è **vuoto** | **astieniti** | il soggetto del claim non esiste nella fonte: non possiamo identificarlo |
| **3** | `A ∩ ancore(frasi_con_v) ≠ ∅` | **OK** | il valore è attribuito a un soggetto che il claim nomina davvero |
| **4** | esiste una frase con un token di `A` che porta un valore `v' ≠ v` **con la stessa unità** | 🔴 **SEGNALA** | **la fonte lega quel soggetto a un valore DIVERSO**: è una contraddizione, non un silenzio |
| **5** | altrimenti | **astieniti** | la fonte **tace** sul valore di quel soggetto, e il silenzio non è contraddizione |

**Il passo 5 è il cuore.** È ciò che tiene lo strato dentro il contratto
dichiarato del prodotto — *il gate distingue ciò che la fonte contraddice, non
ciò su cui tace* — ed è ciò che impedisce l'inondazione di falsi positivi.

### Verifica a mano sui casi noti

    fonte: «...penale per il RITARDO ... 2% ...»  «...penale per DIFFORMITA' ... 5% ...»
    claim: «La penale per il ritardo e' pari al 5%»
      v=5% e' NELLA fonte (passo 1 non scatta) · A={penale, ritardo} non vuoto
      frasi con 5% portano {difformita', qualitativa} · A non le tocca (passo 3 no)
      la frase con «ritardo» porta 2%, stessa unita' (%) e 2% != 5%   → SEGNALA ✅

    claim VERO: «La penale per il ritardo e' pari al 2%»
      la frase con 2% contiene «ritardo» → passo 3 → OK ✅

    fonte: «Il paziente assume metformina. Il dosaggio e' 850 mg.»
    claim VERO: «Il paziente assume metformina 850 mg»
      frasi con 850 portano {dosaggio}; A={paziente, metformina} non le tocca;
      ma nessuna frase con «metformina» porta un valore in mg  → passo 5, ASTIENITI ✅
      (e' il falso positivo che la regola ingenua avrebbe prodotto)

---

## 2. Predizione falsificabile, scritta **contro la baseline misurata**

Baseline pubblica e committata (`1e7c79fb`), quindi ogni numero qui è
verificabile e la predizione **non è riscrivibile a posteriori**.

| cella | oggi | previsto **con `L4.3` da solo** | se sbaglio |
|---|---|---|---|
| **SCAMBIO** 930ch | 10/12 entrano | **≤ 3/12** (segnalati ≥ 7 dei 10) | sotto i 7 segnalati, il meccanismo non fa ciò che dico |
| **SCAMBIO** 453ch | 7/12 | **≤ 3/12** | idem |
| **NUMERALE** | 1/3 · 2/3 | **INVARIATO** — `L4.3` da solo non tocca i numerali | se migliora, la mia descrizione del passo 1 è sbagliata |
| **OMISSIONE** | 3/3 · 2/3 | **INVARIATO, 0 segnalazioni** | **se ne segnala anche UNA, il passo 5 non fa ciò che dico e il design va rivisto** |
| **cifra assente** (controllo di @ws4, 8/8 fino a 3516ch) | verde | **verde, 0 regressioni** | qualunque regressione **respinge** la cura |
| **popolazione B** (@ws5) | da misurare | **≤ 1 nuovo falso positivo** | **> 1 ⇒ il design è RESPINTO così com'è** |

🔑 **La riga che può uccidere il design è l'ultima, e non la controllo io.** È
per questo che la popolazione B la scrive @ws5 e **non voglio vederla prima**:
*il banco lo scriva chi non ha in mente la cura.*

🔑 **E la riga «OMISSIONE invariato» è una predizione VOLUTA, non una rinuncia**:
è il modo di provare che il passo 5 funziona. **Uno strato che si mettesse a
segnalare omissioni sarebbe la prova che sto segnalando il silenzio.**

---

## 3. Il banco pre-registrato

**3 zone di lunghezza × 3 falle + il controllo negativo di @ws4.**

    zona A   ~450 caratteri     la fonte «da manuale» — dove il giudice ancora protegge
    zona B   ~930 caratteri     la SOGLIA misurata: qui il giudice ha gia' ceduto
    zona C  ~1400+ caratteri    la fonte realistica (e resta POCO: un fascicolo
                                vero sta sulle decine di migliaia)

    falle     SCAMBIO (12 casi) · NUMERALE (3) · OMISSIONE (3)
    controllo CIFRA ASSENTE (3 casi) — @ws4 lo tiene verde 8/8 fino a 3516ch:
              DEVE restare verde in tutte e tre le zone
    veri      i controlli di stabilita' gia' nel banco + la popolazione B di @ws5

Base già in `banchi/ws3-F1-la-baseline-regge-su-una-fonte-vera.py` (matrice a 4
lunghezze, zavorra **senza alcuna cifra**, verificata da un controllo
automatico). **Va esteso con una colonna sola: cosa dice `L4.3`.** Il file
attuale **non cambia**, così il confronto prima/dopo è sullo stesso oggetto.

---

## 4. Perimetro — **cosa questo strato NON tocca**

⛔ **Non tocca il giudice**, né i suoi pesi, né le soglie (`local` 40 / `claude`
70). `L4.3` è un layer **accanto**, non **dentro**.
⛔ **Non tocca `L4.1`.** Il passo 1 rende i due **disgiunti** per costruzione: se
il valore non è nella fonte, `L4.3` si ferma e parla `L4.1`. **Nessun doppio
referto sulla stessa ricevuta.**
⛔ **Non gira senza `source`.** Nessuna fonte, nessun confronto: identico a oggi.
⛔ **Non tocca l'omissione** (§0) né la normalizzazione dei numerali (di @ws5,
prerequisito separato).
⛔ **Non tocca lo store, la supersessione, la CI, il README, il pacchetto.**

### 🔴 E una richiesta di cautela che nasce da una misura mia

**`L4.3` deve nascere come AVVISO, non come VETO**, finché non è misurato su un
corpus vero. Ragione, misurata il 26/08 e riprodotta da @ws4: **nello stesso
topic un fatto nuovo NON si limita a entrare — CANCELLA il precedente**
(`flow.supersession branch='same-source evolution'`). ⇒ **un veto nuovo su uno
store da 14.000 fatti non è reversibile nei suoi effetti**: quarantinare per
errore non «rimanda», **toglie**. Un avviso si può promuovere a veto dopo la
misura; un veto sbagliato ha già cancellato.

---

## 5. Cosa serve prima della prima riga di codice

1. **Review di almeno due sorelle** sul canale — @ws5 e una fra @ws4 (che ha il
   contorno e i regimi) e @ws2 (che ha la ricevuta, dove il referto uscirebbe).
2. **La popolazione B di @ws5**, che io **non devo vedere**.
3. **Una risposta secca a due domande aperte che NON so risolvere da solo**:
   · **`ancore` = quali stopword?** La lista italiana del prodotto è
     **incompleta** (misurato: `query_intent._STOP`), e una stoplist monolingue
     in un prodotto mondiale è la **classe ③** dei nostri errori ricorrenti.
   · **la segmentazione in frasi**: su un contratto vero le «frasi» sono
     **articoli**, e un articolo può contenere due valori legati a due soggetti.
     **Se la finestra è la frase sbagliata, il passo 3 dice OK a uno scambio.**
     ⚠️ **Non ho misurato quanto spesso accade, e non lo stimo.**

## Limiti, dichiarati

⚠️ **La regola è progettata sui casi che ho in mano** (12 scambi, 2 domini, IT).
Il rischio strutturale è che sia **cucita addosso al banco**: è precisamente il
motivo per cui la popolazione B è di @ws5 e la review è doppia.
⚠️ **Non ho scritto una riga**: le verifiche del §1 sono **fatte a mano su
carta**, non eseguite. **Possono essere sbagliate**, ed è il primo posto dove
guardare in review.
⚠️ **Zona C = 1424 caratteri**, ancora lontana da un fascicolo vero.
⚠️ Il passo 4 confronta valori **con la stessa unità**: due date, due
percentuali. **Su unità diverse o assenti non ho una regola**, e non la invento.

---

# ⑥ Aggiornamento: **la domanda ② misurata, la predizione caduta, e una cura del passo 3**

*ws3, 28/08 ~20:00. Banco `banchi/ws3-F1-la-finestra-e-la-frase-o-l-articolo.py`.*

Il §5 dichiarava non misurata la domanda ②: *la finestra giusta per il passo 3 è
la frase o l'articolo?* Misurata sui `grounding_span` dello store reale, in
**sola lettura** (`mode=ro`), percorso chiesto al prodotto
(`CONFIG.semantic_db` → `~/.engram/semantic/semantic.db`).

    frammenti con span non nullo ......... 5576
    frasi totali ......................... 20118
    frasi con almeno un valore ...........   891   (4,4%)
    ► con ≥2 valori della STESSA unità ...   256   (28,7% di quelle con valore)
      con ≥2 valori di unità diverse .....     5   (0,6%)
    unità: %=1366, g=173, giorni=59, valuta=49, data=33, kg=8

**Predizione falsificata**: avevo scritto «sotto il 10%», misurato **28,7%**.

## ⚠️ Ma la popolazione non risponde alla domanda che avevo posto

Gli esempi che il banco stampa sono **i nostri stessi output di benchmark**:

    === flow.* CON store / SENZA store ===  flow.write con= 1839 senza= 1961 → 51,6%
    08/08 14:06 ← inizio della finestra …  399 con fonte, 237 con span = 59,4%

E **l'81% dei valori del corpus sono percentuali** (1366 su 1694). **Il corpus
che verimem possiede oggi non è fatto di documenti: è fatto di otto istanze che
salvano tabelle di misure tutto il giorno.**

⇒ La domanda era «*su un **contratto** vero le frasi sono articoli?*», e **questo
corpus non contiene contratti**. Il numero è vero, la domanda **resta aperta**:
**non dico di averla misurata.** *(È la lezione «la popolazione a cui misuri
decide il verdetto», e stavolta l'ho presa io.)*

## Cosa il numero dice davvero, ed è utile lo stesso

Sul corpus che verimem possiede oggi, **una frase su 3,5 fra quelle che portano
un valore ne porta due della stessa unità**. Le **fonti a tabella** esistono e
non sono rare — e uno studio legale ne ha: piani di pagamento, scadenzari,
prospetti. **Il caso patologico non è teorico.**

## 🔧 La cura del passo 3, che nasce dalla predizione caduta

> **Se la frase che contiene il valore porta ≥2 valori della STESSA unità, quella
> frase NON è una finestra utilizzabile: non si restituisce `OK`, si cade nei
> passi 4/5.**

Il caso patologico passa da **falso-OK** ad **astensione-o-segnalazione**:
**fallisce in sicurezza**. È una riga di *regola*, non di codice, e sostituisce
il passo 3 del §1.

| | prima | dopo |
|---|---|---|
| frase con un solo valore | OK | OK |
| frase con ≥2 valori stessa unità | **OK — e assolve lo scambio** | **cade ai passi 4/5** |

## Limiti, dichiarati

⚠️ Lo span è **troncato a 400 caratteri** dal prodotto ⇒ le frasi lunghe sono
tagliate e **la quota è verosimilmente una sottostima**.
⚠️ La segmentazione è una **regex su punteggiatura**: un «Art. 3» la spezza dove
non dovrebbe, e questo **gonfia** il numero di frasi (denominatore) mentre
**spezza** le finestre lunghe.
⚠️ **Un corpus solo**, quello di Aurelio, in un solo istante.
⚠️ **La domanda sui contratti resta aperta**: servirebbe un corpus di documenti
veri, che non abbiamo.

---

# ⑦ Le verifiche «a mano su carta» ESEGUITE: **erano sbagliate su metà dei casi**, e ne esce il passo 2-bis

*ws3, 28/08 ~20:10. Banco
`banchi/ws3-F1-simulazione-del-predicato-fuori-dal-prodotto.py`.*
⚠️ **Simulazione FUORI dal prodotto**: nessun file di `verimem/` toccato, nessun
layer registrato, nessuna ricevuta cambiata. **La modifica al prodotto resta
bloccata dalla review doppia.**

Al §5 avevo scritto che le verifiche del meccanismo erano **fatte a mano su
carta** e che erano **«il primo posto dove guardare in review»**. Le ho eseguite
invece di far rivedere a due sorelle un ragionamento non controllato.

## Prima esecuzione: **16 su 22, e 6 scambi su 12 assolti**

    SCAMBIO  «penale per il RITARDO ... 5%»   → OK   condivide {penale, importo, contrattuale}
    SCAMBIO  «termine di CONSEGNA ... 30 apr» → OK   condivide {termine, fissato}
    SCAMBIO  «acido acetilsalicilico ... 5mg» → OK   condivide {prescritto}

**Il motivo è strutturale, non un dettaglio**: quelle ancore stanno in
**entrambe** le frasi candidate. Ciò che distingue è `ritardo` contro
`difformità`, `consegna` contro `contestazione`, il **nome del farmaco** contro
`prescritto`. Il passo 3 accettava su **una qualsiasi** ancora condivisa.

> 🔑 **Un'ancora presente in più frasi candidate non identifica niente.**
> Contano solo le ancore **DISCRIMINANTI**: quelle che compaiono in **una sola**
> delle frasi che portano un valore di quell'unità.

## Il **passo 2-bis**, che nasce da lì

    cand   = le frasi della fonte che portano un valore dell'unita' in esame
    A_disc = le ancore del claim che compaiono in UNA SOLA frase di cand
    se A_disc e' vuoto  ->  ASTIENITI (non so distinguere i soggetti)
    i passi 3 e 4 usano A_disc, non A

## Seconda esecuzione: **22 su 22 · 12 scambi su 12 · 0 falsi positivi**

    SCAMBIO   12/12 segnalati        CIFRA     3/3 → «e' L4.1» (passo 1)
    PAROLE     2/2 astensione        OMISSIONE 1/1 astensione
    VERI       3/3 OK                VERO-p5   astensione ✅ (il test del passo 5)

## ⚠️ E ADESSO LA CONDIZIONE, che vale più del numero

**Ho corretto la regola DOPO aver visto quali casi fallivano.** Il 12 su 12 è
sul **set su cui ho tarato**: è **precisamente il rischio «cucita addosso al
banco»** che avevo dichiarato al §5, e **non conta come validazione**.

| cosa è | cosa **non** è |
|---|---|
| l'**intuizione** (ancore discriminanti) è **generale** e spiega *perché* la versione ingenua falliva — questo regge | il **12/12** è sul set di taratura e **non è evidenza di generalità** |
| la regola **sa esprimere** la distinzione | non è provato che la **azzecchi** su casi mai visti |

⇒ **La validazione richiede la popolazione B di @ws5 e casi che non ho visto.**
Il numero qui dice solo che **il meccanismo è esprimibile**, non che funzioni.
🔑 *Una cura che funziona per una ragione che non sai spiegare non si consegna* —
qui la ragione **so** spiegarla, ed è il motivo per cui vale la pena continuare.
Ma *il banco lo scriva chi non ha in mente la cura*, e quel banco non è mio.

## Limiti, dichiarati

⚠️ È una **simulazione del predicato**, non il prodotto: il gate vero ha
clausole, span **troncati a 400 caratteri**, normalizzazioni che qui non ci sono.
⚠️ Le **omissioni danno 0 segnalazioni anche solo perché i loro claim non
contengono numeri** ⇒ **quel test è vuoto** e non prova niente sul passo 5.
L'unico test vero del passo 5 è `VERO-p5`, ed è **uno solo**.
⚠️ La lista di **stopword è minima e dichiaratamente incompleta**: è la domanda
① del §5, **aperta**, e di @ws5.
⚠️ I veri qui sono **solo quelli già nei miei file**. **Questo banco non può
approvare niente.**

---

# ⑧ Risposte alle R di @ws5, misurate — **regola v2**

*ws3, 28/08 ~20:25. Banco `banchi/ws3-F1-regola-v2-le-risposte-alle-R-misurate.py`.*
Validazione cieca di @ws5 (`a75ced2f`, 32 casi mai visti da me): **15 scambi su
16 colti** — e **tutti col termine di testa condiviso**, il caso difficile — ma
**3 falsi positivi su 16**, poi **2** col suo regime di segmentazione B.
**Il mio criterio pre-registrato («>1 ⇒ RESPINTO») è scattato.**

## R1 — **accettata integralmente, senza discussione**

Avevo scritto che una finestra ambigua «*cade ai passi 4/5, fallendo in
sicurezza*». **È falso, e la sua diagnosi è esatta**: il **passo 4 è proprio
quello che trova l'altro valore della stessa frase**, quindi su un claim **vero**
cadere lì significa fallire **verso** il falso positivo.

> «*Cade ai passi 4/5*» nasconde **due esiti opposti**, uno sicuro e uno no. Se
> la finestra è inutilizzabile, l'esito sicuro è **l'astensione**.

⇒ **v2: finestra ambigua ⇒ ASTIENITI, senza passare dal passo 4.**
⚠️ E non è un caso di bordo: **la cura l'avevo introdotta proprio perché il
28,7% delle frasi con un valore ne portano due** — la stessa popolazione che
produceva i falsi positivi.

## R2 — accettata, e **la cura era già in casa**

`vicinato_del_valore.py:36-37`: «*la distinzione è **posizionale, non
lessicale**: un identificativo **SEGUE** il suo sostantivo («ordine 77»), una
quantità lo **PRECEDE** («3 anni»)*», dichiarata su IT/EN/DE/FR/ES.
**Classe ricorrente nostra: «esiste già e non è collegato?».**
⚠️ **Implementata in v2 ma NON esercitata**: nel mio banco il caso «ordine 77»
esce come `L4.1` in **entrambe** le versioni — l'estrattore non trova quel
valore nella fonte e il passo 1 cortocircuita prima. **L'esito è giusto per una
ragione diversa da quella che mi attribuirei. R2 resta da provare.**

## R3 — adottata: **segmentazione regime B**

Il suo A/B sul corpus vero: split anche su **newline** e **`;`** ⇒ falsi allarmi
**65,7% → 31,2%**, e **gli scambi colti restano 15/16**. **Curare la
segmentazione non costa sensibilità**, ed è la risposta *numerica* alla domanda
② che avevo girato a @ws4.

## Le tre guardie del corpus vero (`3f961371`, 3030 giudicabili)

| | guardia | prezzo misurato |
|---|---|---|
| **G1** | valore **senza unità** ⇒ il passo 4 non accoppia | **−61,8%** |
| **G2** | il claim cita **anche** l'altro valore ⇒ non è uno scambio | **−27,6%** |
| **G3** | stesso numero a **precisione diversa** (97.6 / 97.5968) | **−2,5%** |

**65,7% → 5,3%.** 📌 **G1 cura anche il MIO falso positivo** di `8157a777` (il
vero «penale = 2%»): percentuali `('', 2.0)` e numeri d'articolo `('', 3.0)`
stanno nello stesso secchio.
🔴 **Costo dichiarato**: con G1 **le percentuali diventano intrattabili per
costruzione**. Sparisce **solo** curando `extract_quantities`. **Non è un bug: è
il prezzo, ed è il motivo per cui l'estrattore viene prima dello strato.**

## Il vincolo pavimento di @ws6 — **non è più cautelativo, è misurato**

Coda di revisione a **1057 contro soglia 500**, in ingresso **5×** rispetto
all'uscita (365 contro 70 in 13 giorni). Il prodotto stesso avvisa
(`review_queue.py:190`): «*a queue nobody drains turns 'held for review' into
'silently dropped'*».
⇒ **`L4.3` nasce AVVISO, non veto.** La cautela del §4 ha ora un numero dietro.

## La misura: **v1 contro v2**

    scambi SEGNALATI     v1  8/8       v2  8/8
    FALSI POSITIVI       v1  2/6       v2  0/6
    esiti attesi         v1 13/16      v2 15/16

**v2 azzera i falsi positivi senza perdere un solo scambio.**

## ⚠️ E la condizione, che vale più del numero

**v2 è tarata sui casi che l'hanno rotta.** Un 0/6 sui casi che hanno prodotto
la correzione **non è una validazione**: è la verifica che la correzione fa ciò
che dice. **Serve una SECONDA cieca, su casi nuovi, da chi non ha visto la v2.**

⇒ **Chiedo la firma esterna a @ws4 o @ws6** (@ws5 è co-owner, la sua vale come
validazione interna), e chiedo che sia **una cieca vera**: casi che io non ho
visto, in due lingue, **con la popolazione dei veri decisa da voi**.

## Limiti, dichiarati

⚠️ **16 casi noti** (i miei + i due falsi positivi di @ws5): popolazione piccola
e **non indipendente**.
⚠️ **R2 implementata ma non esercitata** (sopra).
⚠️ **Le percentuali sono fuori perimetro** finché `extract_quantities` non dà
loro un'unità.
⚠️ Simulazione **fuori dal prodotto**: il gate vero ha clausole, span troncati a
400 caratteri e un ordine dei layer che qui non c'è.

---

# ⑨ Correzione: **la «disgiunzione per costruzione» che avevo promesso non è quella che ho scritto**

*ws3, 28/08 ~22:05. Banco `banchi/ws3-due-nomi-per-la-stessa-unita-nascondono-una-contraddizione.py`, commit `07194829`.*

Al §1 e al §4 avevo scritto, due volte:

> «**Non tocca `L4.1`.** Il passo 1 rende i due **disgiunti per costruzione**: se
> il valore non è nella fonte, `L4.3` si ferma e parla `L4.1`. **Nessun doppio
> referto sulla stessa ricevuta.**»

**È imprecisa, e la correggo.**

## Il fatto

`L4.1` confronta **i valori**, non le coppie `(unità, valore)` — e non è una
svista: è **dichiarato** in `valore_non_nella_fonte.py:244`:

> «*Si confrontano i **VALORI** e non le coppie (unità, valore): «l'ordine 77» e
> «77 pezzi» portano lo stesso numero con unità diverse, e l'unità in un testo
> libero è la parola che segue — **troppo fragile per farci poggiare un veto**.*»

Il mio passo ① confronta invece le **coppie**:

    if (unita, num) not in v_fonte:   continue

⇒ **i due criteri non sono complementari: sono DIVERSI**, e fra loro resta una
banda in cui **nessuno dei due parla** — *valore presente nella fonte, unità
diversa*.

## Misurato

    claim  «Il file wake.py pesa 100 kb»
    fonte  «Il file wake.py conta 100 righe di codice.»

    L4.1   TACE   (il 100 c'e' nella fonte)
    L4.3   TACE   (la coppia ('kb', 100) no)
    esito  QUARANTINATO lo stesso — da L4.2, ground 31.2

⇒ **La banda esiste. Non è un buco del prodotto: `L4.2` la copre.** Ma la mia
frase prometteva una proprietà — *complementarità* — che il codice non ha.

## La formulazione corretta

> `L4.3` **non produce un doppio referto con `L4.1`** sui casi in cui `L4.1`
> parla: quando il valore è **assente** dalla fonte, `L4.1` parla e `L4.3` si
> ferma al passo ①. **Ma i due criteri non coprono insieme tutto lo spazio**:
> dove il valore è **presente con un'unità diversa**, tacciono entrambi, e a
> rispondere è `L4.2`. **La copertura è dei TRE strati insieme, non dei due.**

🔑 **La lezione, e vale oltre questo doc**: avevo dedotto la complementarità
**dalla forma del mio codice**, non dalla lettura di quello dell'altro layer.
*«Disgiunti per costruzione» è un'affermazione su DUE componenti, e per
sostenerla bisogna aver letto entrambi.*

## Limiti

⚠️ La banda l'ho provata su **un caso solo**. Che `L4.2` la copra **sempre** non
è misurato — è misurato **lì**.
