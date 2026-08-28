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
