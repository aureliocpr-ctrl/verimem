# 72 — Un numero perde le sue tre condizioni fra il CHANGELOG e la vetrina, e i due criteri che ho scritto per misurarlo erano tutti e due sbagliati

*ws6/Aldo — 2 settembre 2026, 00:26 (letta, non stimata). Audit su un numero pubblico **non mio**,
scelto perché è l'unico della lista che nessun documento di `stato-reale`
citava.*

## ① Il numero

`README.md:87`, sul judge locale che la banda a due soglie interroga:

> a local **ollama** judge (default `qwen2.5:7b-instruct` — measured **AUROC
> 0.858 vs the CE's 0.829**, **2.3% misconception escape vs ~18%**, fully
> offline)

Un miglioramento di AUROC di **+0,029** (3,5%) accompagnato da un escape che
scende **di 7,8 volte**. Non è una contraddizione — a una soglia ben scelta un
piccolo guadagno di separazione può spostare molto l'escape — **ma è
un'informazione che manca**: *a quale taglio?*

## ② Il CHANGELOG ce l'ha, tutta

`CHANGELOG.md:459` — la stessa misura, con le condizioni:

> **Measured** (`benchmark/local_llm_judge_bench.py`, TruthfulQA heldout
> **n=600**): qwen2.5:7b AUROC **0.858** (> the free CE's 0.829) with **2.3%
> misconception escape at the precision cut** vs the CE's ~18% blind spot,
> 0.32s/pair.

✅ **Banco nominato · campione dichiarato · soglia dichiarata** (*«at the
precision cut»*). Il banco esiste davvero: `benchmark/local_llm_judge_bench.py`,
112 righe.

## ③ Il README no — verificato per lettura, non per criterio

| condizione | nel CHANGELOG | occorrenze nel README |
|---|---|---|
| `n=600` | sì | **0** |
| `local_llm_judge_bench` | sì | **0** |
| «precision cut» | sì | **0** |

⇒ Il confronto **`2,3%` contro `~18%`** arriva alla vetrina **senza il taglio a
cui ciascuno è misurato** — e il `~18%` del CE, dieci righe più su, è dichiarato
*«at the default cut»*. **Due tagli diversi, presentati come un rapporto.**

⚠️ **Non è un errore e non è un'esagerazione**: il numero è vero, misurato, e le
sue condizioni sono scritte — solo in un file che quasi nessuno apre. **È la
forma «il numero perde il regime nel passaggio»**, non «il numero è falso».

## ④ I due criteri che ho scritto per misurarlo, e perché sono caduti entrambi

Volevo dire se questo numero fosse **un'eccezione** o **la norma** della pagina.

**Primo criterio — per RIGA**: «un numero di prestazione deve avere il suo banco
sulla stessa riga».

```
righe con un numero di prestazione : 44
  senza riferimento a un banco     : 33  = 75%
```

⛔ **Falso**: il markdown **avvolge le frasi**, e la fonte finisce spesso sulla
riga dopo. Un criterio per-riga su un testo che va a capo conta a caso.

**Secondo criterio — per PARAGRAFO**: stessa domanda, blocchi separati da riga
vuota.

```
paragrafi con un numero di prestazione : 7
il paragrafo del 2.3% cita un banco?   : SI
```

⛔ **Falso anche questo, nella direzione opposta**: quel paragrafo è lungo e
contiene **altri** numeri; il banco che cita appartiene a uno di quelli. Il
criterio dice «sì» perché nel paragrafo c'è *un* banco, non perché *questo*
numero ce l'abbia.

> 🪞 **Per-riga troppo stretto, per-paragrafo troppo largo — e il fenomeno che
> volevo misurare è semantico: «questa cifra ha la SUA fonte?».** È la forma che
> questo repo documenta da settimane: *un criterio sintattico su un fenomeno
> semantico sbaglia in entrambe le direzioni.* L'ho commessa due volte di
> seguito mentre ne verificavo un'altra.

⇒ **Non do nessun tasso sulla pagina.** Quello che consegno è ciò che ho
verificato **leggendo**: tre `grep` esatti su tre stringhe, e il confronto con la
riga del CHANGELOG.

## ④-bis Il secondo numero che ho guardato ha la stessa forma — e stavolta il costo

Proseguendo **a lettura** (dopo che i criteri automatici sono caduti), il numero
accanto: `README.md:83-85`.

> A two-threshold band … cutting that entity-substitution escape from
> **6.2% → 1.8%** on the moat matrix with **zero** new false-blocks on entailed
> facts (measured)

`CHANGELOG.md:561`, la stessa misura:

> Measured safe (**over-review 1/19 on hard true classes**; entity-substitution
> escape 6.2%→1.8% with 0 new false-blocks)

| | README | CHANGELOG |
|---|---|---|
| il beneficio (`6.2% → 1.8%`) | sì | sì |
| il costo che vale **zero** (false-blocks) | sì | sì |
| il costo che **non** vale zero (`over-review 1/19`) | **0 occorrenze** | sì |
| un banco per questa cifra | **nessuno** | — |

🔑 **La forma è precisa: la vetrina dichiara il costo che è zero e omette quello
che non lo è.** Non è falso — trattenere per revisione **non è** bloccare, e
«zero false-blocks» resta vero. È una **selezione**: dei due costi misurati,
arriva in vetrina solo quello nullo.

⚠️ **Il meccanismo, però, è dichiarato**: «held for review» compare una volta nel
README (riga 89) — ma nella **cascata di escalation**, come fallback quando
l'adjudication fallisce, non come **costo della banda**. Chi legge sa che il
trattenimento esiste; non sa che **un caso vero difficile su diciannove** ci
finisce per effetto della banda accesa di default.

📌 **Due numeri guardati, due volte la stessa forma** — e sono **due su due**,
non «il N% della pagina»: il denominatore è due, e lo dico invece di gonfiarlo.

## ④-ter Il terzo numero: la fonte non l'ho trovata — e dico dove ho cercato

`README.md:81`: *«an entity-substitution contradiction can score mid-range in
some languages — **measured ~7% escape in Spanish**, concentrated in that
shape»*.

Quattro ricerche, tutte a vuoto:

| dove ho cercato | esito |
|---|---|
| `CHANGELOG.md` (`7% escape`, `Spanish`, `spagnol`) | **0 occorrenze** |
| `docs/stato-reale/banchi/` | due file nominano lo spagnolo, ma misurano **altro**: `ws3-l-asimmetria-di-lingua-su-cinque-coppie…` confronta **punteggi** su **5 coppie**, non tassi di escape |
| `benchmark/results/` | **nessun file** nomina lo spagnolo |
| tutto il repo tracciato | «Spanish» compare **solo dentro i dataset esterni** (halueval, squad, truthfulqa) |

⚠️ **«Non l'ho trovata» non è «non esiste»**: può venire da un run non
committato, da un banco che non ho riconosciuto, o essere una stima
dell'autore. **Non affermo che il numero sia inventato.** Affermo che con le
quattro ricerche qui sopra **un lettore non può risalire a come è stato
ottenuto** — ed è tutto ciò che serve a un analista per contestarlo.

📌 **E non è una forma nuova in questa casa**: il registro porta già
`W2-127`/`W2-186`, dove un commento del codice motivava una scelta di prodotto
con *«un 33% che i suoi banchi non contengono, in nessuna lettura»*. **Terzo
numero guardato, terza volta che la condizione sta altrove o non sta da
nessuna parte.**

## ④-quater Altri due, e il denominatore vero della pagina

@ws4 ha rifatto il censimento con un criterio scritto prima: **34 claim
numerici**, non 136 — e l'audit ne aveva coperti **4, il 12%**. Ne restano
trenta. Ne prendo due, sempre **a lettura**.

### `AUROC 0.96–0.97` (riga 53) — ✅ **a posto, e va detto**

> «With an injected llm judge it reaches AUROC **0.96–0.97** (sonnet, on
> **SNLI** held-out; on out-of-distribution TruthfulQA/HaluEval it is
> **~0.81–0.90**, and the free CE ~0.82 — *the honest field numbers*,
> `docs/EVIDENCE-external-2026-07-19.md`)»

Ha il **regime** (`sonnet`, SNLI held-out), dichiara da sé il **degrado fuori
distribuzione**, confronta col default, e **cita il file** — che esiste (113
righe) e **contiene `n=100`**. ⇒ **Il lettore può risalire.** È il numero più
alto della pagina, quindi il più citabile, ed è anche uno dei meglio
circostanziati. **Nessun rilievo.**

### «The residual **~2%**» (riga 95) — ❌ fonte non trovata, e un'ipotesi

> «An air-gapped box with ollama thus gets the full moat with no network. **The
> residual ~2%** scores high and still needs a full llm judge.»

Nessuna condizione, e **non è nel CHANGELOG**. Le occorrenze di «residual» nel
repo sono altre cose (`residual_copies`, `residual_after_filter` in un banco
sulle contraddizioni).

🔎 **Ipotesi, e la dichiaro come tale**: il contesto è la cascata del judge
ollama, il cui escape è **2,3%** — il `~2%` potrebbe essere **quello stesso
numero arrotondato**. Se è così **non è una misura nuova**, e presentarlo con
un'altra parola («residual») fa contare al lettore **due grandezze dove ce n'è
una**. ⚠️ **Non lo affermo**: chi ha scritto la riga lo sa in un secondo, e la
cura è una parentesi.

📌 **Bilancio dell'audit a lettura, cinque numeri**: due con le condizioni
altrove (`2.3%`, `6.2%→1.8%` — **portate in vetrina**, `acbc5800`), uno **a
posto** (`0.96–0.97`), due **senza fonte trovata** (`~7% Spanish`, `~2%
residual`).

## ④-quinquies Altri cinque, e il quadro si capovolge

Undici claim guardati in tutto. Questi cinque, letti in blocco:

| riga | esito |
|---|---|
| **69** | ✅ *«the 2026-07-18 run had **0** numeric escapes … re-running **the same command** on 2026-08-25 reports **4** (one per language) and exits 1. **Run it yourself before trusting either number.**»* |
| **102** | ✅ *«0% false-block (**re-measured 2026-08-25**: still 0.0%, **112/112** entailed admitted)»* — data, denominatore, file citato |
| **106** | ✅ *«AUROC 0.829, and **at the default cut** ~24% … ~18% … (74% of those scoring ≥80, the plausible-inference blind spot)»* — dichiara il **taglio** e scompone il punto cieco |
| **116** | ⚠️ **non è un claim numerico**: `100 €`/`150 €` sono un **esempio d'uso**, non una misura. Da togliere dal censimento |
| **143** | ✅ *«covers **70 of the 171**. The remaining 101 have no syntactic shape»* — numeratore, denominatore e il limite del criterio |

> 🔑 **La riga 69 porta lo standard migliore dell'intera pagina** — due date, due
> valori, *lo stesso comando*, e **l'invito esplicito a rieseguirlo prima di
> fidarsi**. Più forte della 101, che si ferma a mostrare i due numeri.

## ④-sexies Il bilancio, e va detto con la prontezza di un allarme

Su **11 claim numerici guardati** (dei 34 censiti da @ws4):

```
a posto, condizioni in vetrina                       :  6
condizioni SOLO nel CHANGELOG → portate in vetrina   :  2   (acbc5800)
fonte NON trovata                                    :  2   (~7% Spanish · ~2% residual)
non è un claim numerico                              :  1   (l'esempio 100/150 €)
```

⇒ ⛔ **Ritiro l'impressione che i primi due casi davano.** La pagina **non è
uniformemente fragile**: la maggioranza dei claim guardati dichiara regime,
campione o fonte, e **cinque righe** applicano lo standard senza che nessuno
glielo abbia chiesto. **I due numeri senza fonte restano due**, e vanno chiusi —
ma sono l'eccezione, non la regola.

📌 **Denominatore onesto**: 11 su 34, e li ho scelti io fra quelli che il
criterio segnalava. **Restano 23 non guardati.**

## ④-septies I due blocchi più esposti sono i più onesti della pagina

**La tabella delle contraddizioni** (righe 11-26) — il cuore della promessa —
non porta solo i denominatori (`0/10 IT`, `1/10 IT, 2/10 EN`, `8/10–9/10`): le
mette accanto **tre limiti dichiarati**.

- **Length**: misurate su fonti **corte**, e aggiungere frasi non pertinenti alza
  il punteggio del giudice — *«one case went **9.6 → 35.9** against a cut of 40»*.
- **Script**: fuori da IT/EN **degrada** e lo quantifica lingua per lingua — ZH e
  JA come EN, **KO 3, AR 5, HI 7, e Thai fallisce del tutto a 10/10**; la
  negazione fuori IT/EN è *«still unmeasured»*.
- **Figures**: *«the 8/10–9/10 above is an **average over two halves that behave
  in opposite ways**»* — cioè **dichiara che il proprio numero migliore
  nasconde due popolazioni**.

🔑 **È l'opposto di una vetrina che nasconde**: il blocco che vende la garanzia
principale è anche quello che elenca dove la garanzia cade, **con i numeri del
fallimento**.

**`recall@5` e `QA-accuracy`** (righe 40-46) — i numeri più «da leaderboard»
della pagina:

> *«**not** third-party reproduced, and **not** the GPT-4 judge the public
> leaderboards use, so these are **not** a like-for-like ranking against them»* ·
> `recall@5 = 0.87` (**judge-free, full 500 questions**) · `QA-accuracy = 0.81`
> (**n=150**, Claude judge) · metodo in `docs/BENCHMARKS.md`

E chiude ridimensionandosi da sé: *«That's good retrieval — **but the reason to
choose Verimem is the layer above it**»*.

⇒ **Campione, giudice, fonte, non-comparabilità e ridimensionamento**, tutto
sulla stessa riga. **Nessun rilievo.**

📌 **Bilancio aggiornato — ~19 claim guardati, i problemi restano DUE**
(`~7% Spanish`, `~2% residual`). ⇒ Per l'operazione concessionario la frase da
non scrivere è *«i numeri del README non sono tracciabili»*: **su diciannove
guardati, due sono contestabili.**

## ④-octies ⛔ IL `~7% Spanish` HA UNA FONTE, E DICE UN NUMERO **3,5 VOLTE PEGGIORE**

Avevo chiuso quel numero con *«fonte non trovata in quattro ricerche»*,
dichiarando che «non trovata» non è «non esiste». **@ws4 l'ha trovata** e ha
chiuso il vuoto. **Riletta da me prima di toccare la vetrina**,
`docs/EVIDENCE-stress-2026-07-18.md` §D (banco `moat_multilingual_matrix.py`):

```
| EN | 28/28 | 0 |
| IT | 27/28 | 1 |   ← una fuga è ITALIANA
| FR | 28/28 | 0 |
| ES | 21/28 | 7 |   ← 7/28 = 25,0%
| total | 104/112 | 7.1% |
```

⇒ **«~7% escape in Spanish» era falso in due modi**: il 7,1% è il **totale
cross-lingua** (8 su 112, e una fuga è **italiana**), e il tasso **spagnolo** è
**25%**. Chi leggeva capiva «su cento scambi in spagnolo ne sfuggono sette»:
**ne sfuggono venticinque**. **La vetrina rendeva il difetto 3,5 volte più
piccolo della sua stessa fonte.**

✅ **Corretto** (`0c6be55c`): la riga ora porta `25% escape in Spanish (7 of 28)`,
dichiara che il 7,1% è il totale su EN/IT/FR/ES, dice che **una fuga è italiana**
e cita documento e banco.

### La riconciliazione che NON ho fatto, e perché

Tre righe sotto, il README dice *«cutting **that** entity-substitution escape from
**6.2% → 1.8%** on the moat matrix»*. `moat_multilingual_matrix.py` è l'unico
banco «matrix», e l'aritmetica tornava **perfettamente**: `7/112 = 6,25%` (le
sole fughe spagnole sul denominatore intero) e `2/112 = 1,79%`.

⛔ **L'ho verificata invece di scriverla, e non regge**: il banco stampa **un solo**
escape — `tot['esc']/n_bad`, cioè il **totale** — e **non produce un 6.2%**. ⇒ Il
`6.2%` viene da un'altra misura, e **la relazione fra i due numeri legati da
«that» resta non stabilita.**

🔑 **Un'aritmetica che torna non è una prova.** Aggiungere alla vetrina una
riconciliazione plausibile e non verificata sarebbe la «spiegazione conciliante»
che l'osservatore ci ha già contestato una volta: **si merita guardando i dati,
non facendo tornare i conti.**

### ⛔ E venti minuti dopo i dati sono saltati fuori: avevo ragione, e mi correggo lo stesso

`docs/EVIDENCE-external-2026-07-19.md:20-23`:

> «entailed **112/112** admitted (0.0% false-block) · **confab escape 1.8%**
> (down from **6.2%** with the band OFF): **the residual is a Spanish
> entity-substitution** that scores mid-range»

⇒ ✅ **Il «that» del README è CORRETTO**: `6.2%` (banda OFF) e `1.8%` (banda ON)
vengono **dalla stessa matrice a 112 casi**. La relazione che avevo dichiarato
«non stabilita» **è stabilita**, e la mia aritmetica (`7/112`, `2/112`) era nel
verso giusto — **l'avevo scartata per il motivo sbagliato**: il banco stampa un
solo escape, ma la fonte non è il banco, è il documento di evidenza.

🔑 **E chiude l'ULTIMO numero senza fonte**: il «**residual ~2%**» della riga 95
**è lo stesso 1.8%** citato dieci righe sopra — **non una seconda misura**. La
vetrina contava **due volte la stessa grandezza** con due nomi diversi, e con la
tilde sembrava una terza cifra. 📌 **E il residuo è una sostituzione SPAGNOLA**,
esattamente la classe che il §④-octies ha appena corretto da 7% a 25%.

✅ **Corretto in vetrina**: la riga ora dice *«That residual — the same **1.8%**
above, **not a second measurement**, and it is a Spanish entity-substitution»*
con il file citato.

🪞 **La forma dell'errore mio**: avevo cercato la fonte **nel banco** e concluso
«non la produce». La fonte era **nel documento di evidenza che il README cita
dieci righe sopra**, per un altro numero. ⇒ *Quando un numero non ha fonte, guarda
anche le fonti dei numeri che gli stanno accanto.*

## ⑤ La cura, e il precedente

La forma esiste già nel README, dieci righe più su: il numero dell'escape
esterno porta con sé *«(1.8% was the 2026-07-18 run; the same command today
reports 5.4%)»* — valore, data, e che il comando è lo stesso.

📌 **Basterebbe portare in vetrina le tre parole che il CHANGELOG ha già**: *«at
the precision cut, TruthfulQA heldout n=600»*. Non toglie niente al numero, e lo
rende confrontabile con il `~18%` che gli sta accanto.

## ⑥ Cosa NON prova

❌ **Non ho eseguito `local_llm_judge_bench.py`**: richiede un server ollama e il
modello scaricato, e non l'ho verificato disponibile. **Non ho quindi
riprodotto né `0.858` né `2.3%`** — dico dove sono dichiarati e cosa manca in
vetrina, non che siano giusti o sbagliati.
❌ **Non ho stabilito se sia un'eccezione o la norma** del README: i due criteri
che ho scritto per deciderlo sono caduti entrambi (§④), e non ne ho scritto un
terzo.
✅ **Quello che regge**: i tre `grep` di §③ e la riga del CHANGELOG. Sono
letture, non inferenze.

---
*Nessun banco: questo documento è tre `grep` e due file letti. Il costo
dell'audit è stato interamente nei due criteri sbagliati.*
