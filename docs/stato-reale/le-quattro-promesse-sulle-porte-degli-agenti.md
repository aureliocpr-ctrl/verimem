# Le quattro promesse del Summary, sulle porte degli AGENTI

*31/08, misure fra le 02:19 e le 03:00 (ore lette). Le celle qui sotto sono
**mie** (ws3) e riguardano la superficie **MCP** e la **CLI**. Le celle SDK sono
di @ws7 (`LANT-130`) e @ws1: **citate, non rivendicate**.*

La riga del Summary che `pip show verimem` stampa e che apre la pagina PyPI:

> *«Verified memory for AI agents: gated writes, provenance on every read,
> bi-temporal history, abstention instead of hallucination.»*

@ws7 l'ha messa in una **matrice promessa × porta** — la mossa che rende
discutibile ciò che altrimenti si giudica in blocco: *«chi dice "il Summary è
vero" e chi dice "il Summary è falso" hanno entrambi torto»*. Questo documento
riempie le celle delle porte che il prodotto dichiara **primarie per gli
agenti**, e aggiunge due cose che le celle da sole non dicono.

---

## ⚠️ PRIMA DELLA MATRICE: due stati che mancavano, e perché non sono un dettaglio

Una matrice a **due** colori (regge / non regge) fa sparire due situazioni che
qui si presentano entrambe, e le fa sparire **verso il verde**:

| stato | significa | perché serve |
|---|---|---|
| ✅ **regge** | la promessa si verifica alla porta | |
| 🔴 **non regge** | la promessa non si verifica | |
| ⚖️ **diverso per disegno, DICHIARATO** | la porta fa un'altra cosa, e lo dice | marcarlo 🔴 è un'accusa falsa; marcarlo ✅ è una promessa falsa |
| ⚪ **non esercitato** | nessuno ha raggiunto quel meccanismo | **non è verde**: è una cella vuota, e «non misurato» si legge «a posto» |

⇒ **Senza il quarto stato, un contratto di uscita rivendica come verificate
delle porte che nessuno ha provato** — ed è la prima cosa che un analista va a
cercare. *(È la classe già in memoria: «una misura che non c'è si legge come
perfetta».)*

E una **colonna** che manca: **in che FORMA** la garanzia è servita. La stessa
distinzione fra «il corpus è povero» e «l'hai tagliato tu» esiste sulla CLI **in
prosa** e su MCP **in un campo** — e un lettore che cerca il campo sulla CLI non
lo trova, e viceversa.

---

## ① `gated writes` — le porte che scrivono un fatto non sono tre

Criterio scritto prima: una porta è *gated* se **lo stesso testo
auto-affermativo** che `hippo_remember` quarantina viene fermato anche lì.
Controllo retto: `hippo_remember` lo quarantina davvero (`L1`), quindi il testo
è discriminante.

| porta | stato | come stabilito | evidenza |
|---|---|---|---|
| `hippo_remember` | ✅ ferma | misurata alla porta | `quarantined_by=L1` |
| `hippo_transcript_promote` | ⚖️ ammette, dichiarato | misurata alla porta | `status=model_claim`; la nota della porta dichiara che promuovere un turno è *registrare che una cosa è stata detta* |
| `hippo_ingest_conversation` | ⚪ non esercitato | misurata alla porta | `extracted=0`: senza estrattore vivo **il gate non è stato raggiunto** |
| `hippo_import_conversations` | ⚪ non esercitato | misurata alla porta | rifiuta la chiamata: chiede un formato di export **che non ho indovinato — e non lo indovino** |
| `hippo_document_promote_chunk` | ✅ | **presidiato altrove** | `tests/test_il_vanto_entrava_dalla_porta_dei_documenti.py` |

Banco: `banchi/ws3-le-porte-di-scrittura-non-sono-tre.py` · commit `85311512`

---

## ② `provenance on every read` — le porte MCP sono rosse

Criterio scritto prima, e sono **tre cose diverse**:

- **A leggibile** — il TESTO della fonte torna ⇒ si vede *su cosa* si regge il fatto
- **B verificabile** — torna un'impronta/riferimento ⇒ chi ha *già* la fonte la conferma
- **C giudicato** — torna il VERDETTO ⇒ si sa che una fonte è stata pesata, non *quale*

Un fatto scritto **con** `source` **e** `verified_by`. Controllo retto:
`grounding_score = 99.83` ⇒ il moat aveva giudicato, quindi l'assenza a valle
riguarda le porte e non la scrittura.

| porta | A | come stabilito | dettaglio |
|---|---|---|---|
| SDK `Memory.search` | ✅ | misurata (superficie di @ws7, rimisurata da me) | il testo torna in **`grounding_span`** |
| `hippo_facts_recall` | 🔴 | misurata alla porta | nessun campo, e neppure in tutta la risposta |
| `hippo_facts_search` | 🔴 | misurata alla porta | idem |
| `hippo_recall_history` | 🔴 | misurata alla porta | idem |
| `hippo_trust_report` | 🔴 | misurata alla porta | idem; il campo `provenance` vale `[]` |

📌 **Correzione a @ws7**, con i numeri: la loro cella dice *«`search` porta
`source` + `source_signature`»*. Misurato: **`source` è `None`** e
`source_signature` è un `sha256:…`, cioè **B, non A**. Il campo che porta la
fonte è `grounding_span`. La cella resta verde — per un campo diverso da quello
nominato. *(Il reperto è emerso solo perché il banco cerca l'ancora in **tutti**
i campi: cercando `source` per nome avrei scritto «assente» su una porta che
invece la porta.)*

⇒ **Frase difendibile**: *la provenienza è LEGGIBILE sull'SDK e non sulle porte
MCP, dove torna il verdetto del moat e il riferimento che il chiamante ha
fornito* (`verified_by` senza il quale è `[]`).

Banco: `banchi/ws3-la-provenienza-sulle-porte-degli-agenti.py` · commit `93486795`

### 🧮 E quanto pesa, sul corpus VERO — due misure indipendenti che si compongono

Il mio banco dice **come** si comporta il meccanismo; il censimento di @ws2
(03:08, 16781 fatti) dice **quanto spesso** quel meccanismo è l'unico rimasto:

| | |
|---|---|
| porte MCP: provenienza **A leggibile** | mai (misurato, 4 porte su 4) |
| porte MCP: **B riferimento** | solo se il chiamante l'ha passato (misurato) |
| corpus reale: `verified_by = []` | **96,6%** (16209 su 16781 — @ws2) |

🚨 **CORREZIONE, 04:27 — questa riga diceva «per il 96,6% un lettore MCP
ottiene SOLO il verdetto», ed era SBAGLIATA.** Quel 96,6% è la quota **senza
riferimento**, e si divide in due:

| | fatti | % del totale |
|---|---|---|
| senza riferimento, **ma con** verdetto ⇒ ottiene **solo il verdetto** | 10162 | **60,5%** |
| senza riferimento **e senza** verdetto ⇒ **non ottiene niente** | 6054 | **36,1%** |
| *somma di controllo* | *16216* | *96,6%* ✅ |

⇒ **Per il 60,5% dei fatti un lettore MCP ottiene solo il verdetto; per il
36,1% non ottiene nulla.** Sommarli e dire «96,6% solo il verdetto» conta i
secondi due volte — un analista lo falsifica con una query. *La cella resta
rossa, e per una ragione più precisa.* Né il banco né il censimento bastavano
da soli.

### 🔴 E il numero che chiude la riga: **zero provenienza sul 30% dei fatti servibili**

Letto **in sola lettura** sullo store reale (`mode=ro`) alle **03:16 del 31/08**
— l'ora conta, il corpus si muove mentre lo si misura:

| | fatti | % |
|---|---|---|
| totale | 16788 | |
| **vivi** (non superseduti: quelli che il recall può servire) | 14503 | |
| senza **verdetto** (`grounding_score IS NULL`) | 6611 | 39,4% |
| senza **riferimento** (`verified_by` vuoto) | 16216 | 96,6% |
| **né l'uno né l'altro** | **6054** | **36,1%** |
| **né l'uno né l'altro, fra i VIVI** | **4358** | **30,0% dei vivi** |

⇒ 🔑 **Per il 30,0% dei fatti che il recall può servire, una lettura da MCP non
porta NESSUNA provenienza**: né il testo (mai, su nessuna porta), né il
riferimento, né il verdetto. Non è il livello C: è **niente**.

*(Coerente col censimento di @ws2 delle 03:08 — 16781 totali, 16209 senza
riferimento — a meno dei fatti scritti negli otto minuti fra le due letture.)*

⚠️ **E una distinzione da NON perdere** (@ws2 la segnala per prima):
`verified_by = []` **non** significa «non verificato». Sono due meccanismi
diversi — nel mio banco il fatto aveva `grounding_score = 99.83` **con**
`verified_by` valorizzato. Il 96,6% riguarda **B**; il tasso con cui il gate
giudica riguarda **C**. Nella stessa riga diventerebbero illeggibili entrambi.

---

## ③ `bi-temporal history` — 🔴 UNA DELLE DUE DIMENSIONI NON È MAI POPOLATA

**Aggiornata alle 03:48 su un dato di @ws7 (03:38), verificato da me in
`mode=ro`**: era ⚪, ora è 🔴 — e la formulazione conta.

```
alle 03:47                        alle 04:38 (ricontato)
TOTALE                16805       TOTALE                16839
asserted_at IS NULL   16805       asserted_at IS NULL   16838
valorizzati               0       valorizzati               1   ← b2306dc5eb03
```

🔴 **QUESTO NUMERO È SCADUTO IN CINQUANTA MINUTI, E CHI L'HA FATTO SCADERE
STAVA MISURANDOLO.** Alle 04:13 @ws7 ha scritto il **primo fatto del corpus con
`asserted_at` valorizzato** (`b2306dc5eb03`, topic `vetrina/asserted-at-porta`)
mentre misurava che nessuno lo valorizza. ⇒ **Tre referti di stanotte dicono
«0» — @ws2 0/16779 (03:06), @ws7 0/16796, io 0/16805 (03:47) — e un analista
che riesegue la query oggi trova `1` e conclude che il referto mentiva.** La
frase pubblicabile è: ***1 su 16839, e quell'uno è nostro.***

✅ **E il fatto scaduto vale più del numero che ha rotto**, perché in
quell'unica riga i due tempi sono **diversi**: `asserted_at` 00:00 contro
`created_at` 04:13. **La dimensione non è morta: è inutilizzata.**

⚠️ **La frase da NON scrivere**: *«non c'è storia bi-temporale»*. È
falsificabile in trenta secondi, perché `recall_as_of` fa
`born = asserted_at if asserted_at is not None else created_at`: **con NULL il
ripiego scatta sempre e il viaggio nel tempo FUNZIONA** — misurato alla porta
SDK su tre celle (`92f73123`: versione corrente · era precedente · niente prima
di tutto).

✅ **La frase difendibile**: *delle due dimensioni promesse, **una non è mai
popolata**. Ogni interrogazione temporale ricade sul tempo di **scrittura**. Il
meccanismo regge; la seconda dimensione — quando l'evento è **accaduto**, contro
quando l'abbiamo **saputo** — è vuota nei fatti reali.*

🔑 **Stessa forma della riga ②**: una promessa vera del *meccanismo* e vuota nei
*dati*. Il campo esiste, il codice lo legge, e nessuno lo riempie.

📌 **La domanda che avevo lasciato aperta — ORA HA RISPOSTA, ed è la seconda.**
Chiedevo: *se nessuna porta di scrittura lo accetta → capacità **mai
collegata**; se lo accetta e nessuno lo passa → un campo che il prodotto **non
chiede mai**.* ⇒ **È il secondo caso**: `verimem save --asserted-at` esiste
(`LANT-135`, @ws7) e **funziona end-to-end** — il fatto `b2306dc5eb03` lo prova
con i due tempi distinti nella stessa riga. La cura non è costruire: è **che la
porta principale lo chieda**.

### 🔗 E il costo del campo vuoto non è «una dimensione su due»

**Letto nel sorgente** (`supersession_policy.py:229-252`, non misura mia): il
verdetto `evolution` — che **ritira** il fatto vecchio — richiede stessa fonte
**e** ordine in valid-time, dove valid-time è *«`asserted_at` when present,
else `created_at`»*. Il commento del prodotto dichiara la conseguenza::

    both facts unsourced, no asserted_at   → "evolution"   ← the real-world case

⇒ 🔑 **Con `asserted_at` vuoto il ramo conservativo non scatta mai**: l'ordine
non è *ambiguo→conflitto* ma, parole del sorgente, **INVENTATO** dal tempo di
scrittura. Il campo spento non toglie una lettura: **toglie la guardia che
impedisce a un fatto nuovo di ritirarne uno vecchio che dice altro** — ed è
esattamente ciò che @ws2 ha misurato dal verso opposto (`W2-168`: *con
`asserted_at` valorizzato la sostituzione silenziosa non avviene*).

### 🔀 I DUE INTERRUTTORI ACCANTO, E PUNTANO IN VERSO OPPOSTO

**Misurati alle 04:58 chiamando le due funzioni** (non lette: `env` non li
mostra perché *nessuno dei due è impostato*, ed è il default a decidere):

```
ENGRAM_SUPERSEDE_SAME_SOURCE   True    ← ACCESO   ritira il fatto vecchio
ENGRAM_RECONCILE_ON_WRITE      False   ← SPENTO   «contests, never auto-supersedes»
```

⇒ 🔑🔑 **Il ramo che RITIRA in silenzio è acceso di default; quello che
CONTESTA senza mai ritirare è spento di default.** Non è una svista: entrambe le
scelte sono motivate nei rispettivi docstring — ma **il verso combinato non è
scritto da nessuna parte**, e la riga ③ è il posto dove diventa visibile.

📌 **La condizione di sblocco che il prodotto si è dato è già soddisfatta.**
`semantic.py:1854` spegne la riconciliazione *«until the false-supersede rate is
measured on a real corpus»*. ⚠️ **Quella misura esiste** — è nel corpus di casa,
**non rieseguita stanotte e quindi da rifare prima di usarla**: chi la rifà
chiude una condizione che il sorgente enuncia, non un difetto che ipotizza.

⚠️ **E la premessa del default acceso è falsa PROPRIO QUI.** Il docstring
(`anti_confab_gate.py:596-607`) dice che il default resta ON perché regge
l'ipotesi *un solo scrittore per tenant*, e che con N sessioni dietro una chiave
la premessa *«è falsa per costruzione»*. **Stanotte siamo otto scrittori sullo
stesso store, con `VERIMEM_MULTI_WRITER` non impostata** ⇒ il prodotto ci tratta
come uno solo. ⛔ **Non è una cura da applicare al volo**: spegnerlo ha un costo
già misurato (i legittimi aggiornamenti finiscono in quarantena e il vecchio
resta servito). **Va detto, non toccato.**

---

⚠️ **UNA FRASE DEL PRODOTTO È ORA FALSIFICATA ALLA LETTERA**, e non è nostra:
il commento dice *«no write path fills `asserted_at`»* (misurato 2026-08-26).
Una via di scrittura lo riempie — la CLI — e alle 04:13 è stata usata. 📌 **Non
la correggo io**: `supersession_policy.py` è fuori dal mio perimetro, ed è
segnalata sul canale a chi lo tiene.

*(Dato di @ws7; la precisazione su `NULL` invece di `0`, il ripiego, il
ricalcolo delle 04:38 e la giuntura con la supersessione sono miei.)*

---

### Perché la cella era ⚪ fino alle 03:48 — il banco che non ha concluso

**Il mio banco non è riuscito a misurarla.** Tre controlli caduti, tutti per il
disegno del banco:

1. due scritture a 0,4 s di distanza **oggi** non sono separabili da una data in parole ⇒ retrodatare è obbligatorio;
2. retrodatare di mesi rende i fatti **dormienti** (soglia ~45 giorni) ⇒ serve `deep=True` su entrambe le superfici;
3. «a marzo» **non ancora un punto temporale**, e non è un difetto: `extract_as_of` accetta solo forme con **giorno E anno** e il docstring dichiara *«Pure, conservativa: nessuna àncora inventata»*.

**Ricetta per chi ci riproverà**: due ere separate da mesi · `deep=True` · una
domanda che ancori giorno e anno.

📌 **Quello che resta è LETTURA, non misura** — e va marcato così:

| cosa | letto in |
|---|---|
| `as_of` è nello schema di **1 porta MCP su 4** | `list_tools()` |
| `extract_as_of` (routing automatico) compare **solo** in `client.py` (SDK) | `git grep` |
| `recall_with_history` **accetta** `as_of`, l'handler MCP non glielo passa | `mcp_server.py:8226` |

⇒ La divergenza SDK/MCP su questa riga è **plausibile e NON dimostrata**.
Chiamarla misurata sarebbe l'errore che questo lavoro esiste per non fare.

✅ **Verificato invece di supposto, a favore del prodotto**: stavo per segnalare
la classe «liste monolingue» su `_MONTHS`. **I mesi italiani ci sono**, aggiunti
il 2026-08-06, col commento che racconta la cura.

Banco: `banchi/ws3-la-stessa-domanda-sul-passato-a-due-porte.py` · commit `e9f13422`

---

## ④ `abstention instead of hallucination` — nessuna porta del richiamo si astiene

🔑 **E questa riga NON è una promessa: sono TRE meccanismi**, e su porte diverse
ne gira uno solo. Una cella verde su una non vale per l'intera riga.

| meccanismo | dove |
|---|---|
| gate cross-encoder | **solo** `hippo_trust_report`, acceso di default |
| pavimento di rilevanza | 3 porte, ma l'interruttore `ENGRAM_MIN_RELEVANCE` ne raggiunge **2** (commit `b0481a07`) |
| pavimento `"auto"` | vale **0.0000** ⇒ zero è falsy, non filtra mai (@ws2/@ws6; riprodotto da me su uno store da **un** fatto) |

| porta | si astiene? | come stabilito | evidenza |
|---|---|---|---|
| `hippo_facts_recall` | 🔴 no | misurata alla porta | **0.757** su una domanda mai sentita, contro 0.857 su una coperta |
| `hippo_facts_search` | 🔴 no* | misurata alla porta | 0 righe fuori corpus, **ma è un MISS LESSICALE**: la porta si dichiara *«Keyword/substring search … (SQL LIKE)»* |
| `hippo_recall_history` | 🔴 no | misurata alla porta | nessuna astensione dichiarata |
| `hippo_trust_report` | ✅ sì | misurata alla porta | `abstained` true/false |
| CLI `verimem recall` | 🔴 no | misurata alla porta (sottoprocessi) | «come si accorda una tromba» → **«La penale del contratto Rossi…»**, best **0.7291** contro 0.8798 |

⚠️ **La cella `facts_search` è la più insidiosa**: dà `[]`, che **sembra**
un'astensione e non lo è. Chi la conta come ✅ mette un verde dove c'è un miss
di parole.

### 🕳️ E lo STESSO `score 0.0` ha DUE cause opposte in questo prodotto

*(Correzione delle 05:36. L'evidenza di questa cella diceva «`score 0.0` anche
**in** corpus». **Non regge da sola**: stanotte ho curato in cinque punti il
fatto che, col ranking **degradato**, il richiamo cade sul ramo a parole e
assegna `0.0` a **tutti** i risultati. Un analista può quindi leggere quello
zero come *degrado di quella esecuzione* e non come *disegno della porta*, e
avrebbe ragione a chiederlo.)*

| lo stesso `0.0` | significa | come si distingue |
|---|---|---|
| su `facts_recall` con ranking degradato | similarità **NON misurata** | la ricevuta ora porta `ranking_degraded` (`c97aa380`, `8333c2a5`) |
| su `facts_search` sempre | **non c'è** similarità da misurare | la porta si dichiara `SQL LIKE`, *«distinct from `hippo_facts_recall` (semantic / cosine)»* |

⇒ 🔑 **Due zeri identici, due significati opposti, e l'unico modo di separarli è
sapere QUALE porta ha risposto.** La prova che regge non è il numero — è la
descrizione della porta. **Ho sostituito l'evidenza con quella**, perché la
prima si falsifica riaprendo la domanda sul degrado e la seconda no.

🤝 **Conferma incrociata su tre superfici**: @ws2 ha misurato 0,79–0,82 sul
corpus reale (parole inventate); io **0.7291** dalla CLI e **0.757** da MCP, su
uno store da **un** fatto. ⇒ Il fenomeno non dipende né dal corpus né dalla
porta.

🟢 **E una buona notizia, sulla FORMA**: col pavimento alto la CLI stampa *«no
facts above the floor»* — distingue «il corpus è povero» da «l'hai tagliato tu».
La stessa garanzia su MCP mancava e l'ho aggiunta come **campo** (`e24d25d5`).

⏱️ **Una misura sull'astensione va DATATA**: fino alle 01:0x di stanotte
`hippo_trust_report` si asteneva **per la ragione sbagliata** (col ranking
degradato il pavimento svuotava il dossier e la ricevuta diceva
`abstained: true`) — curato in `8333c2a5`. Prima di quel commit la stessa cella
dava un verde che significava un'altra cosa.

Banchi: `banchi/ws3-la-riga-dell-astensione-sulla-porta-della-riga-di-comando.py`
· commit `db309dbd`, `6614d56f`, `b0481a07`

---

## 🚫 Una domanda che NON si può rispondere con i dati che abbiamo

Per pesare le celle sulle letture reali servirebbe sapere **quante letture
passano da quale porta**. La telemetria non lo permette, e la ragione è
**misurata**, non supposta — `events.jsonl` **+ `events.jsonl.1`** (il journal
ruota: leggere solo il primo misura la coda), 40.007 righe, lette alle **03:21
del 31/08**:

| superficie, sui soli `flow.recall` | eventi | % |
|---|---|---|
| `unknown` | 2468 | **52,3%** |
| `gateway` | 2199 | 46,6% |
| `cli` | 47 | 1,0% |
| `sdk` | 2 | 0,04% |
| **`mcp`** | **0** | **mai** |

⇒ 🔑 **Più di metà delle letture non ha una superficie attribuita, e la porta
MCP non compare MAI fra le letture** — pur comparendo **1373** volte sugli altri
eventi, quindi la superficie *è* tracciata altrove. ⚠️ **Conseguenza per il
contratto di uscita**: nessuna affermazione del tipo *«la maggior parte delle
letture passa da X»* è sostenibile con questi dati, e una percentuale calcolata
su questo denominatore parlerebbe soprattutto di `unknown`.

📌 *(Il file avverte anche di essere «inquinato all'88% dal dogfooding». **Quel
numero non l'ho verificato e non lo riporto come mio.**)*

---

## ⚠️ E un errore che il registro invita a fare: contare gli EVENTI DI SICUREZZA

Censiti i nomi di evento **emessi nel sorgente** contro quelli **presenti nel
registro** (03:35). Fra quelli mai presenti c'è **`prompt_injection_blocked`:
zero occorrenze**. La tentazione è leggerlo come *«nessuna injection è mai stata
bloccata»* — e da lì come *«il presidio non è collegato»* **oppure** come
*«nessun attacco»*. **Uno zero non distingue le due cose**, e servono due
letture per farlo:

| domanda | risposta, per questo evento |
|---|---|
| **chi lo emette, e a quale condizione?** | `wake.py:1439`, dentro il loop agentico: un tool pericoloso chiamato **dopo** che la traiettoria ha incluso contenuto esterno (`web_fetch` / `vision_describe` / `web_search`) |
| **quella condizione è esercitata dai test?** | **sì**, `_injection_review_blocks_call` è asserito in **quattro** file (`test_prompt_injection_defense.py` — 16 celle —, `test_pentest_validation.py`, `test_wake_extra.py`, `test_wake_macro_injection_guard_scan68.py`) |

⇒ 🔑 **Il presidio è collegato ed esercitato: lo zero significa «mai accaduto»,
non «mai collegato».** Ed è coerente col nostro uso — quel percorso richiede un
episodio agentico con contenuto esterno, che il dogfooding di memoria non fa.

⚠️ **Per il contratto di uscita**: *contare gli eventi di sicurezza nel registro
per affermare «nessun attacco» è un errore* — quello zero è compatibile con
«nessun attacco» **e** con «nessuna misura», e solo la lettura del codice li
separa.

### La regola che ne esce: **quando uno zero è leggibile e quando non lo è**

Tre eventi mai presenti nel registro, tre situazioni diverse — e il conteggio
le rende identiche:

| evento | chi lo emette | test che lo esercitano | lo zero è… |
|---|---|---|---|
| `prompt_injection_blocked` | `wake.py:1439`, loop agentico | **4 file** | ✅ **LEGGIBILE**: «mai accaduto» |
| `session_token_persist_failed` | `dashboard_routes/auth.py:80` | **nessuno** | ⚪ **ILLEGGIBILE** |
| `ide_ws_origin_blocked` | `ide.py:486` | **nessuno** | ⚪ **ILLEGGIBILE** |

⇒ 🔑 **Un evento di sicurezza o di errore SENZA un test che ne accenda il
percorso ha uno zero che non significa niente**: non si distingue «non è mai
successo» da «non si accenderebbe comunque». Con un test, lo zero diventa un
dato. *(I due illeggibili stanno su superfici che non sono le mie — dashboard e
IDE: li segnalo, non li curo.)*

📌 *(Il censimento ha prodotto 27 nomi mai presenti, ma la maggior parte sono
**falsi positivi del mio grep**: `click`, `mousemove`, `resize`, `wheel` sono
eventi DOM del webui, non del registro — e uno, `token_budget_exceeded`, viveva
in un **documento d'archivio**: il grep leggeva anche i `.md`. **Il perimetro
del censimento non era dichiarato**, ed è un difetto quanto un numero sbagliato.
Il conto onesto: **101** nomi di evento emessi dentro il package, **107** in
tutto il repo. Il numero grezzo non è un inventario: va letto voce per voce.)*

---

## 📓 Cosa dice il registro, e cosa NON può dire

Letto da `events.jsonl` **più il ruotato `.1`** (leggere solo il primo misura la
coda) alle **04:05 del 31/08**, in sola lettura.

### ⚠️ Le tre cautele — e ora stanno DAVVERO prima del numero

*(Correzione delle 05:15: il titolo diceva già «vanno lette PRIMA del numero» e
il blocco stava **dopo**. Un analista lo vede in un colpo d'occhio, e la frase
che dichiara l'ordine giusto mentre lo viola vale meno di zero.)*

1. **Non sono 407 errori.** Il gate trattiene anche per ragioni che il giudice
   non copre (auto-affermazione, iniezione, forma del numero). È la
   **popolazione da esaminare**, non un conteggio di falsi positivi. Il team lo
   sa in forma qualitativa (`anti_confab_gate.py:2512` cita casi con grounding
   99,3–99,9 trattenuti da un layer); **mancava l'aggregato**.
2. **Il denominatore giusto sono i GIUDICATI**, non tutte le scritture: un fatto
   senza `grounding_score` non può essere «trattenuto nonostante il giudice».
3. **L'ora fa parte del dato**: il registro cresce mentre lo si legge — e
   **quanto**, è misurato due righe più sotto invece che dichiarato.

### Il numero: **13,1% delle quarantene colpisce fatti che il giudice aveva validato**

| | 04:05 | 05:14 |
|---|---|---|
| `flow.write` totali | 11415 | 11451 |
| di cui **giudicati** (`grounding_score` non nullo) | 7375 | 7411 |
| di cui **quarantinati / rifiutati** | 3102 | 3107 |
| **trattenuti NONOSTANTE il giudice** | **404** | **407** |
| — sui giudicati | 5,5% | 5,5% |
| — sui quarantinati | **13,0%** | **13,1%** |

**Chi li ha trattenuti** (05:14): `L4.1` **274 (67%)** · `L4.2` 139 · `L1.15` 49 ·
`L1.16` 36 · `L1.10` 28 · `L1.20` 26 · `store-screen` 14 · `L4-relazione` 12.

🔑 **Il campo è DERIVATO, non dichiarabile dal chiamante** — `flow_events.py:305`:
`withheld_despite_judge = status in (quarantined, rejected) AND judged_true(grounding_score)`,
col commento *«se una porta potesse dichiarare `judged=True` senza un punteggio,
il campo mentirebbe — ed è il campo su cui questo prodotto si vende»*. Il numero
non è auto-riportato: esce dall'incrocio di due fatti indipendenti.

### 🕐 QUALE dei miei numeri scade, e quale no — misurato, non supposto

Due numeri di questo documento, stessa notte, **destini opposti**:

```
asserted_at valorizzati    0 / 16805  (03:47)  →  1 / 16839  (04:38)   SCADUTO in 50 min
trattenuti / quarantene    404 (13,0%) (04:05) →  407 (13,1%) (05:14)  STABILE in 69 min
```

⇒ Primo tentativo di regola: *«è il numeratore — uno a zero cade al primo
evento»*. **Vera ma incompleta**, e il terzo numero la corregge:

```
letture MCP nel registro   0 / 4716  (03:21)  →  0 / 4761  (05:40)   ZERO STABILE in 2h19
```

🔑🔑 **DUE numeratori a zero, destini opposti — e la differenza NON è la
dimensione, è la RAGIONE dello zero:**

| zero | perché | scade? |
|---|---|---|
| `asserted_at` 0/16805 | **per disuso**: la via esiste (`--asserted-at`) e nessuno la usava | ✅ **al primo utente** — 50 minuti |
| letture MCP 0/4716 | **per costruzione**: gli handler di lettura non emettono l'evento | ❌ **mai**, finché non si aggiunge l'emit |

⇒ 🔑 **Uno zero per disuso è una promessa a scadenza; uno zero per costruzione è
un fatto strutturale.** E si distinguono **leggendo il codice**, non aspettando:
la domanda giusta non è «quanto è piccolo il numeratore» ma **«esiste un modo
perché diventi diverso da zero?»**. *(Raffinata alle 05:41 dopo il terzo
ricalcolo: la prima formulazione avrebbe fatto ricontare in eterno un numero
che non può muoversi.)*

### 🪞 E il ricalcolo ha trovato un difetto nel MIO righello, non nel numero

Ricalcolando a mano ho ottenuto **1904 trattenuti (61,3%)** invece di 407.
**Il salto era impossibile**: il numeratore quadruplicava mentre il denominatore
cresceva dello 0,3% (11415 → 11451). ⇒ **Il righello era cambiato, non il
mondo.** La causa: avevo scritto `grounding_score is not None`, che è `judged`;
il prodotto usa `_judged_true(_gs)` — *giudicato* non è *validato*, e un fatto
con grounding 0,33 è il primo dei due e non il secondo (`flow_events.py:300-308`).

⚠️ **La cura è che quel campo NON va ricalcolato**: `withheld_despite_judge` è
**già nel payload di ogni `flow.write`**, derivato dal prodotto. Ricalcolarlo
significa reimplementare una definizione che esiste — e sbagliarla.
🔑 **Il rilevatore che mi ha fermato costa zero: un rapporto numeratore /
denominatore che si muove in modo implausibile accusa il righello, non i dati.**

### 🚫 E i limiti del registro, misurati stanotte

| limite | 03:21 | 05:40 |
|---|---|---|
| **letture (`flow.recall`) totali** — il denominatore | **4716** | **4761** |
| di cui **senza superficie attribuita** | 52,3% (`unknown`) | **52,8%** (2513) |
| di cui attribuite alla porta **MCP** | **0** | **0** — mai, pur essendo `mcp` su **1377** eventi complessivi |
| «inquinato all'88% dal dogfooding» (dichiarato nel file) | **non verificato da me — non lo riporto come mio** | |

*(Il denominatore mancava: la riga diceva «0 letture MCP» senza dire **su
quante**. Aggiunto alle 05:40 insieme al ricalcolo — un numeratore senza
denominatore è la prima cosa che questo documento rimprovera altrove.)*

⇒ **Nessuna affermazione del tipo «la maggior parte delle letture passa da X» è
sostenibile con questo registro.**

---

## Come leggere questo documento

- **misurata alla porta** = un banco eseguibile, con il suo controllo e la sua popolazione opposta, citato per nome;
- **letta dal codice** = non è una misura, ed è marcata così ovunque compaia;
- **⚪ non esercitato** = nessuno ha raggiunto quel meccanismo: **non contarlo come verde**;
- le celle **SDK** sono di @ws7/@ws1 e sono citate, non rivendicate. Dove ho rimisurato, l'ho detto.
