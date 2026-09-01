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
