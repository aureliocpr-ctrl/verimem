# ② octies — `warmup` risolve per il futuro; i fatti dei primi minuti restano non verificati per sempre

> **ws2 «Vega» · 08/08 ore 14:50–14:56 · repo SHA `332a2f73`, `git status` pulito ·
> pacchetto `verimem 0.7.0`, HOME fredda, cache modelli vuota**
> Completa il passo che [02g](02g-il-primo-comando-a-freddo.md) dichiarava **non fatto**:
> *«non ho verificato se `warmup` a freddo risolva davvero»*. Risolve — ma non all'indietro.

---

## 1. `warmup` funziona, ed è la parte del prodotto scritta meglio che ho incontrato

L'utente segue il consiglio che il prodotto stesso dà in `warnings[0].advice`:

```
$ verimem warmup
Warming embedding model intfloat/multilingual-e5-base (dim 768) — first run downloads ~440 MB, please wait…
✓ model ready in 27.5s (vector dim 768)
Warming cross-encoder reranker (R@1 lever) — first run downloads…
✓ reranker ready in 58.4s
Fetching the local gate model (the moat's judge-less judge)…
✓ moat gate model ready — gate model installed at …/.engram/models/local_gate_ce_v2
· shared encode daemon spawning in the background (warms from cache in ~20s; all MCP servers then share it)
Warmup complete — Verimem recall will be instant.
```

**175 secondi** (14:50:24 → 14:53:19). Dice cosa scarica, quanto pesa, quanto ci mette, e conferma
ogni pezzo per nome. Nessuna reticenza.

## 2. E dopo, il prodotto verifica davvero

```
$ verimem remember "Il modulo delta ha 55 test." --source "Rapporto: modulo delta, 55 test, tutti verdi."
admitted id=0bf2ecdbe007
```
→ nel DB: **`grounding_score = 96.3`**. Il moat gira.

## 3. 🔴 Ma i fatti scritti prima restano `NULL` per sempre

Stesso store, tutti e tre i fatti che quell'utente ha scritto:

| proposizione | status | grounding | quando |
|---|---|---|---|
| Il modulo alfa ha 12 test. | `model_claim` | **NULL** | prima del warmup |
| Il modulo beta ha 30 test. | `model_claim` | **NULL** | prima del warmup |
| Il modulo delta ha 55 test. | `model_claim` | **96,3** | dopo il warmup |

**2 fatti su 3 mai giudicati**, e nessuno li rivede più. Non sono fatti qualsiasi: sono **i primi
che l'utente scrive**, quelli con cui prova il prodotto per capire se fa quello che promette. Restano
nella sua memoria con la stessa etichetta `model_claim` di tutti gli altri — indistinguibili senza
guardare `grounding_score`.

## 4. La cura esiste per l'altra popolazione, e non è collegata a questa

Il repo ha `verimem facts requalify-quarantined` → `admission_cleanup.requalify_quarantined`
([`admission_cleanup.py:230`](../../verimem/admission_cleanup.py)), che *«re-evaluate quarantined
facts with the CURRENT gate and promote to `model_claim` the ones no detector trips anymore»*.

Ma:

| | quarantinati | **mai giudicati** |
|---|---|---|
| esiste un comando che li rivede | ✅ `requalify-quarantined` | ❌ **nessuno** |
| cosa rivaluta | screen L1 + injection + admission gate | — |
| **ricalcola `grounding_score`** | ❌ **no** — promuove lo stato, non giudica la fonte | — |

E in tutto `verimem/` la stringa `grounding_score IS NULL` **non compare mai**: nessun codice cerca
i fatti che il moat non ha mai visto.

🔑 **È la classe «la cura c'era, mancava il collegamento»** — e la popolazione scoperta da ws3 oggi
(*«nessuno rivede mai la quarantena», 20 quarantinati su 20 riammessi dal gate di oggi*) e questa
sono **due facce dello stesso buco**: il prodotto non ha un momento in cui torna sui fatti già
scritti. Lì per un gate che è migliorato, qui per un giudice che non c'era ancora.

📌 Nota che rende la cosa più stretta: anche `requalify` promuove a `model_claim`, **la stessa
etichetta dei mai-giudicati**. Dopo un recupero riuscito, un fatto recuperato e uno mai verificato
sono di nuovo indistinguibili — è il difetto di [02c §4](02c-il-numero-mostrato-e-chi-decide.md)
che ritorna sulla via del recupero.

---

**Cosa propongo** (a ws3, che è l'unica che scrive — io non tocco codice): la controparte di
`requalify-quarantined` per i mai-giudicati, cioè un passaggio che rigiudichi i fatti con
`grounding_score IS NULL` **che hanno una fonte**. La popolazione da misurare prima di scriverlo:
quanti fatti con fonte hanno `grounding_score NULL` su un corpus vero — non l'ho misurata.

**Caveat**: un'installazione, un OS, 3 fatti in tutto nello store freddo; i 175 s del warmup sono una
misura sola e includono ~440 MB di download su questa rete. Che `requalify` non ricalcoli il
grounding l'ho letto nel docstring e nella firma, **non l'ho eseguito**.


---

# ⚠️ CORREZIONE (ore 14:58) — la misura regge, **la cura che ne avevo dedotto no**

Avevo proposto a ws3 «la controparte di `requalify-quarantined` per i mai-giudicati», offrendomi di
misurarne la popolazione. **Misurata, e la proposta si sgonfia.**

**Corpus vero, denominatore 9097 fatti, ore 14:56, `sqlite mode=ro`:**

| | | |
|---|---|---|
| mai giudicati (`grounding_score IS NULL`) | **6485** | 71,3% |
| giudicati dal moat | 2612 | 28,7% |
| **di cui con un'impronta di fonte** | **35** | 0,5% dei mai giudicati — **0,4% del corpus** |
| *(controllo)* giudicati **e** con fonte | 1453 | |

E **quattro righe di ciò che ho contato**, come vuole la regola di casa:

```
638f34262c5f quarantined sig=cycle103-reb «HippoAgent status @ 2026-05-11 00:15: 82 tool MCP…»
ade9b68c2d11 quarantined sig=cycle103-reb «HippoAgent status @ 2026-05-11 00:30: 85 tool MCP…»
3226c10c0edf quarantined sig=cycle103-reb «HippoAgent @ 2026-05-11 00:50: 87 tool MCP…»
e2b8c3bd8fa9 quarantined sig=cycle103-reb «HippoAgent @ 2026-05-11 01:00: 88 tool MCP…»
```

Telemetria di un ciclo dell'11 maggio, **già quarantinata**. Non sono «l'utente aveva dato la fonte
e nessuno l'ha giudicata»: il caso che immaginavo non c'è nemmeno in quei 35.

## Cosa resta e cosa cade

* ✅ **Resta**: a freddo 2 fatti su 3 restano `NULL` per sempre, e nessun comando li rivede. La
  misura di §3 e §4 è corretta.
* ❌ **Cade**: la cura che ne avevo dedotto. Un comando di riqualificazione retroattiva varrebbe per
  lo **0,4%** del corpus, e per righe che non lo meritano.
* 🔑 **La cura giusta è impedire che nascano**: l'avviso al primo comando
  ([02g](02g-il-primo-comando-a-freddo.md), una riga) o il warmup automatico. Il difetto è reale per
  **l'utente nuovo**, non per il corpus esistente — perché il nostro corpus lo hanno scritto istanze
  che il moat ce l'avevano già.

## E il 71,3% non è un difetto — attenzione al denominatore

I 6485 mai giudicati sono in larga parte fatti scritti **senza fonte**, ed è esattamente ciò che P19
e P23 promettono (*«without a source… stored as an unverified `model_claim`»*, *«null = NEVER
JUDGED»*). Chi citasse quel 71,3% come «il moat non gira quasi mai» userebbe il denominatore
sbagliato: **sui fatti con fonte, giudicati 1453 su 1488 = 97,6%.**
