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

⇒ **Per il 96,6% dei fatti reali, un lettore MCP ottiene SOLO il verdetto** —
il livello **C**, il più debole dei tre. 🔑 *La cella non è rossa in teoria: è
rossa sul 96,6% del corpus.* Né il banco né il censimento bastavano da soli.

⚠️ **E una distinzione da NON perdere** (@ws2 la segnala per prima):
`verified_by = []` **non** significa «non verificato». Sono due meccanismi
diversi — nel mio banco il fatto aveva `grounding_score = 99.83` **con**
`verified_by` valorizzato. Il 96,6% riguarda **B**; il tasso con cui il gate
giudica riguarda **C**. Nella stessa riga diventerebbero illeggibili entrambi.

---

## ③ `bi-temporal history` — ⚪ NON ESERCITATA, e lo dichiaro

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
| `hippo_facts_search` | 🔴 no* | misurata alla porta | 0 righe fuori corpus, **ma è un MISS LESSICALE**: `score 0.0` anche *in* corpus |
| `hippo_recall_history` | 🔴 no | misurata alla porta | nessuna astensione dichiarata |
| `hippo_trust_report` | ✅ sì | misurata alla porta | `abstained` true/false |
| CLI `verimem recall` | 🔴 no | misurata alla porta (sottoprocessi) | «come si accorda una tromba» → **«La penale del contratto Rossi…»**, best **0.7291** contro 0.8798 |

⚠️ **La cella `facts_search` è la più insidiosa**: dà `[]`, che **sembra**
un'astensione e non lo è. Chi la conta come ✅ mette un verde dove c'è un miss
di parole.

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

## Come leggere questo documento

- **misurata alla porta** = un banco eseguibile, con il suo controllo e la sua popolazione opposta, citato per nome;
- **letta dal codice** = non è una misura, ed è marcata così ovunque compaia;
- **⚪ non esercitato** = nessuno ha raggiunto quel meccanismo: **non contarlo come verde**;
- le celle **SDK** sono di @ws7/@ws1 e sono citate, non rivendicate. Dove ho rimisurato, l'ho detto.
