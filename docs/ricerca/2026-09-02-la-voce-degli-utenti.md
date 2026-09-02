# La voce degli utenti sulla memoria per agenti LLM — rilevazione del 02/09/2026

> **Cos'è**: cosa lamentano, chiedono e rompono gli utenti dei sistemi di memoria per
> agenti, letto nelle issue dei concorrenti, su Hacker News e nei forum raggiungibili,
> più i progetti piccoli con la stessa proposta di valore di verimem. Prodotto il
> 02/09/2026 da un ricercatore esterno (Claude Opus, sola lettura) su mandato del lead
> — mandato di Aurelio: «guardare anche sui forum, cosa lamentano gli utenti, i
> problemi degli altri, progettini che non conosciamo».
> **Come leggerla**: ogni conteggio riporta la query così com'è (riproducibile); ogni
> citazione ha URL e data. Reddit e Stack Overflow **non erano raggiungibili** dal
> ricercatore: nessuna citazione di prima mano da lì.
> **Le tre conclusioni** stanno in fondo; la prima cosa da leggere è mem0 #4573.

## Nota metodologica — cosa NON è raggiungibile
**Reddit: non raggiungibile.** Tre canali provati, tre falliti: `WebFetch https://www.reddit.com/...json` → "unable to fetch"; `old.reddit.com` → idem; `WebSearch allowed_domains:["reddit.com"]` → errore 400 esplicito ("domains are not accessible to our user agent"); mirror `redlib.catsarch.com` → HTTP 403; browser MCP → "navigation denied". **Nessuna citazione Reddit in questo report è di prima mano.** Le sezioni B e D si reggono su Hacker News (raggiungibile via API, con punteggi e date verificabili), GitHub Issues/Discussions, e il forum Letta.
Stack Overflow: `api.stackexchange.com` **non raggiungibile** da WebFetch.
Controllo positivo sui conteggi GitHub: la frase-esca `"purple wombat forgets"` restituisce **0**, mentre `"agent forgets"` restituisce risultati che contengono davvero la frase (verificato leggendo 5 snippet). I conteggi phrase-search sono quindi reali, non rumore.

---

# A. GITHUB ISSUES DEI CONCORRENTI

## A.1 Volumi (2026-09-02)

| Repo | Issue aperte | Issue chiuse |
|---|---|---|
| mem0ai/mem0 | 283 | 1863 |
| getzep/graphiti | 277 | 238 |
| letta-ai/letta | 16 | 1276 |
| langchain-ai/langmem | 49 | 34 |
| topoteretes/cognee | 218 | 847 |
| basicmachines-co/basic-memory | 69 | 535 |

Discussions: mem0 **147**, cognee **133**, letta **0**, graphiti **0** (via GraphQL).

## A.2 Conteggi per tema — unione dei 6 repo
Query: `repo:mem0ai/mem0 repo:getzep/graphiti repo:letta-ai/letta repo:langchain-ai/langmem repo:topoteretes/cognee repo:basicmachines-co/basic-memory is:issue <termine>`

| Tema | termine | in body+title | solo `in:title` |
|---|---|---|---|
| Setup locale / LLM locale | `ollama` | 416 | **109** |
| Setup / packaging | `docker` | 677 | **108** |
| Embedding / config | `embedding` | 1047 | 164 |
| Duplicati | `duplicate` | 597 | **53** |
| Recall che non trova | `retrieval` | 420 | 38 |
| Setup | `install` | 1123 | 57 |
| Timeout | `timeout` | 248 | 28 |
| Benchmark | `benchmark` | 150 | 23 |
| Cancellare / dimenticare | `forget` | — | 19 |
| Lentezza | `slow` | 174 | 18 |
| Multilingua | `language` | 171 | 17 |
| Fatti vecchi | `outdated` | 71 | 10 |
| Latenza | `latency` | 162 | 6 |
| Privacy | `privacy` | 60 | **2** |
| Allucinazione | `hallucination` | 24 | **2** |

**Due letture contro-intuitive, e vanno dette:**
1. **Il tema più grosso per volume non è la qualità: è il setup.** `ollama` + `docker` in-title = 217 titoli, contro 53 per `duplicate` e 2 per `hallucination`. Gli utenti aprono issue quando il software **non parte**, non quando ricorda male.
2. **"hallucination" è quasi assente come parola** (2 titoli su ~5.400 issue). Il dolore esiste — la sezione A.3 lo dimostra — ma **gli utenti non lo chiamano così**. Lo chiamano *junk*, *noise*, *indiscriminate storage*, *poisoned*, *garbage*. Chi cerca il mercato con la parola "hallucination" non lo trova.

## A.3 Conteggi GitHub-wide (tutto GitHub, `is:issue created:>2025-06-01`)

| Frase esatta | Issue |
|---|---|
| `"stale memories"` | 1538 |
| `"duplicate memories"` | 1441 |
| `"agent forgets"` | 1380 |
| `"memory bloat" agent` | 1296 |
| `"memory hallucination"` | 689 |
| `"wrong memories"` | 624 |
| `"false memories" agent` | 597 |
| `"forgets everything" agent session` | 162 |

## A.4 Le issue che contano (lette per intero)

### ① Il documento più importante trovato in tutta la ricerca
[**mem0ai/mem0 #4573 — "What we found after auditing 10,134 mem0 entries: 97.8% were junk"**](https://github.com/mem0ai/mem0/issues/4573) — 2026-03-27, chiusa, **23 commenti, 6 reazioni**.
32 giorni di produzione, un agente, un umano, Qdrant. Audit manuale di 10.134 entry: **224 sopravvissute, di cui solo 38 utilizzabili senza riscrittura.**

- Il movente: *«the agent kept "remembering" things it had never been told»*.
- La diagnosi centrale, parola per parola: *«there's nothing between extraction and storage that checks whether a fact is grounded»*.
- L'amplificazione: **808 entry** che affermano *«User prefers Vim»* — nessuno usa Vim. Un modello 2B l'ha allucinato **una volta**; il fatto è entrato in recall, è stato ri-estratto come ground truth, e si è moltiplicato. *«Any hallucination that gets stored once will be re-extracted indefinitely»*.
- **Il modello migliore non ha risolto**: passando da gemma2:2b a Sonnet il junk rate è sceso da ~97,5% a 89,6%, non a zero. Sonnet ha smesso di inventare e ha cominciato a **memorizzare tutto fedelmente**. *«The extraction prompt is the bottleneck, not the model»*.
- Composizione del junk: boot/system-prompt restating **52,7%**, rumore cron/heartbeat 11,5%, dump di architettura 8,2%, task transitori 7,4%, **profili utente allucinati 5,2%**, confusione d'identità 3,3%.
- Le 5 cose chieste, in ordine di impatto dichiarato dall'autore: (1) impedire il feedback loop marcando i ricordi richiamati; (2) **«A quality gate between extraction and storage»**; (3) negative few-shot; (4) **una quinta azione `REJECT`** nel prompt di update; (5) extraction identity-aware.
- Citano Harvard D3: *«indiscriminate memory storage performs worse than using no memory at all»*.

Nei commenti, due utenti indipendenti (`farrrr`, `jamebobob`) hanno pubblicato **fork correttivi** e discutono per 4 giorni. `farrrr`, 2026-03-30: *«if what goes in is wrong, nothing downstream can fix it»*. `jwade83`, 2026-03-29, riassume il cambio di default che chiedono: *«nothing persists unless promoted»*.

### ② Il gate chiesto da un utente, senza sapere che si chiama così
[**getzep/graphiti #760 — "[BUG] Hallucinations"**](https://github.com/getzep/graphiti/issues/760) — 2025-07-24, **aperta da 13 mesi**, 10 commenti.
Nel thread, `onestardao` (2025-08-28) propone spontaneamente a un altro utente esattamente l'architettura di verimem: *«source-bound contract»* per ogni nodo (`source_doc_id`, `span_start/end`, `raw_text_checksum`, match vettoriale+span, rifiuto se sim < τ), *«semantic firewall before write»*, e in caso di violazione *«send to a quarantine queue instead of committing»*. È la nostra scheda prodotto, scritta da un utente in un commento a un bug altrui.

### ③ Il write che ratifica l'input come fatto
[**topoteretes/cognee #4296**](https://github.com/topoteretes/cognee/issues/4296) — 2026-07-31, **aperta**.
`recall` interrogato con frasi affermative non risponde dal contesto: **ratifica la query come fatto e la rinforza**. Caso documentato: la nota ingerita diceva "PR #67157 added to the PRS watch list", la risposta dice "PR 67157 **merged**". La parola "merged" non compare né nella query né in alcun documento; il PR era `merged=false` lo stesso giorno. L'autore lo qualifica: *«converts unverified caller statements into "confirmed" facts»*, ed è *«the worst failure mode for an agent-memory use case, because it produces no error»*.

### ④ Cancellare non cancella
[**topoteretes/cognee #3526**](https://github.com/topoteretes/cognee/issues/3526) — 2026-06-27, chiusa. `forget()` rimuove il dato dalla lista e dal grafo, ma `recall()` **continua a servire il fatto cancellato, «sometimes indefinitely»**. Riproduzione completa con curl nel body.
[**getzep/graphiti #864 — "How to forget knowledge?"**](https://github.com/getzep/graphiti/issues/864) — 2025-08-26, 7 commenti.
[**letta-ai/letta #3116 — "Archival Memory Deduplication and Consolidation"**](https://github.com/letta-ai/letta/issues/3116) — 2025-12-22, aperta, 8 commenti.

### ⑤ Duplicati: bug reali, non teorici
[mem0 #6531](https://github.com/mem0ai/mem0/issues/6531) — race TOCTOU nella hash-dedup del SDK TypeScript: due `add()` concorrenti con fatti identici passano entrambi il gate e inseriscono duplicati permanenti, **senza errore**. Stessa classe già trovata in Python.
[graphiti #963 "Duplicate Entities in Neo4j"](https://github.com/getzep/graphiti/issues/963) (2025-10-02, aperta) · [graphiti #1672](https://github.com/getzep/graphiti/issues/1672) · [cognee #2510](https://github.com/topoteretes/cognee/issues/2510) · [basic-memory #1275](https://github.com/basicmachines-co/basic-memory/issues/1275) (NFC/NFD macOS → entità duplicate).

### ⑥ Il benchmark che nessuno riesce a rifare
[**mem0ai/mem0 #2800 — "Unable to reproduce locomo eval scores locally"**](https://github.com/mem0ai/mem0/issues/2800) — 2025-05-26, **24 reazioni, 25 commenti**, almeno **7 utenti distinti** che riportano numeri più bassi tra maggio e novembre 2025.
`dohooo`, 2025-06-15: *«we are unable to reproduce the accuracy you mentioned»*, e chiede *«Do you plan to release verifiable accurate information»*. `keranlee`: "+1". `LevinFaber`, 2025-11-08, nota che questi risultati sono *«a big part of the methods "claim to fame"»*. La risposta del maintainer: gli score alti sono della **piattaforma cloud**, non dell'OSS.
Correlate: [mem0 #5286 "Standardized memory recall benchmark"](https://github.com/mem0ai/mem0/issues/5286) · [mem0 #5235 "evaluation toolkit for agent memory quality"](https://github.com/mem0ai/mem0/issues/5235) · [mem0 #5614 "Eval metrics — retrieval relevance, staleness detection"](https://github.com/mem0ai/mem0/issues/5614) · [cognee #2913](https://github.com/topoteretes/cognee/issues/2913).

### ⑦ Multilingua
[**mem0 #4884 — "BM25 keyword search and entity extraction are hardcoded to English"**](https://github.com/mem0ai/mem0/issues/4884) — 2026-04-18, **aperta, 5 reazioni, 10 commenti**. È la seconda issue aperta più votata di mem0.

### ⑧ Il server memory ufficiale MCP — il tema è *dove sta il file*
Query `repo:modelcontextprotocol/servers is:issue memory`:
- [#1018 "Environment variables not respected in @modelcontextprotocol/server-memory"](https://github.com/modelcontextprotocol/servers/issues/1018) — 2025-03-23, **aperta, 23 reazioni**
- [#692 "Memory MCP ignores custom storage path setting"](https://github.com/modelcontextprotocol/servers/issues/692) — 2025-02-27, **aperta, 15 reazioni**
- [#220 "MCP memory server NO persistent memory.json location!"](https://github.com/modelcontextprotocol/servers/issues/220) — 2024-12-04, 13 reazioni
- [#4117 "memory: safer persistence defaults, atomic writes, quotas, redaction"](https://github.com/modelcontextprotocol/servers/issues/4117) — 2026-05-06, aperta, 21 commenti

**51 reazioni su tre issue, la più vecchia aperta da 18 mesi, tutte sullo stesso punto: non riesco a decidere dove il server scrive.** Zero issue sulla qualità dei fatti.

### ⑨ Claude Code (`anthropics/claude-code`) — la popolazione più vicina a noi
Attenzione a un artefatto: la parola "memory" nel tracker di Claude Code significa **quasi sempre RAM**, non memoria dell'agente. Le 4 issue "memory" più votate sono OOM leak (92r, 75r, 71r, 57r). Filtrando, il dolore *agent-memory* è:

| Reazioni | Issue |
|---|---|
| 50 | [#14228 Accedere alla memoria di claude.ai da Claude Code](https://github.com/anthropics/claude-code/issues/14228) (aperta) |
| 45 | [#87 "Advanced Memory Tool for Claude Code"](https://github.com/anthropics/claude-code/issues/87) (chiusa) |
| 39 | [#25739 Project memory portabile fra macchine](https://github.com/anthropics/claude-code/issues/25739) (aperta) |
| 38 | [#25947 Memory files in `.claude` locale al progetto](https://github.com/anthropics/claude-code/issues/25947) (aperta) |
| 24 | [#28276 `memoryDirectory` configurabile](https://github.com/anthropics/claude-code/issues/28276) |
| 19 | [#24382 Auto-memory condivisa fra git worktree](https://github.com/anthropics/claude-code/issues/24382) |
| 16 | [#16600 Memory traversal rispetti i confini worktree](https://github.com/anthropics/claude-code/issues/16600) |
| 14 | [#33603 "CLAUDE.md hard rules ... consistently ignored"](https://github.com/anthropics/claude-code/issues/33603) (aperta, 19 commenti) |

**Somma: 245 reazioni. Tema dominante = portabilità e posizione del file (156 reazioni su 245, cioè il 64%). Qualità dei fatti: 14 reazioni.**

## A.5 Discussions rilevanti (mem0)
- [**#4289 "mem0 memory storage working too indiscriminately in OpenClaw"**](https://github.com/mem0ai/mem0/discussions/4289) — 2026-03-10, 4 risposte. Da 26 memorie a 95 dopo pochi prompt: *«it essentially had stored everything from the conversation»*, incluse date e orari. Passando a un modello di decisione migliore: **~2 minuti di attesa anche per "What is 30+15?"**, senza differenza nella selettività.
- [**#4787 "How does Mem0 handle memory deduplication and contradiction resolution at scale?"**](https://github.com/mem0ai/mem0/discussions/4787) — 2026-04-11, 5 risposte. Risposta tecnica (`yashwanth123`, 2026-07-24): la dedup **non** è per soglia coseno, è **solo hash MD5 esatto**; le contraddizioni **sono tenute entrambe by design**, collegate da `linked_memory_ids`. Un altro utente (`RemanenetSpy`) risponde descrivendo `superseded_by` esplicito come alternativa. Un altro (`simon9679`) ha scritto **un auditor esterno read-only** con ground truth sintetica per misurare il costo di questa scelta.
- [#4730 "MemGuard — memory validation layer for Mem0"](https://github.com/mem0ai/mem0/discussions/4730) · [#6682 "GovernedMemory adapter"](https://github.com/mem0ai/mem0/discussions/6682) · [#7071 "Don't let failed web-tool results become agent memory"](https://github.com/mem0ai/mem0/discussions/7071) · [#7120 "decision-gate layer for agent memory"](https://github.com/mem0ai/mem0/discussions/7120) · [#6373 "Fact check request for Mem0's regulated-memory evaluation results"](https://github.com/mem0ai/mem0/discussions/6373).
**Cinque discussioni distinte, tra aprile e agosto 2026, che propongono tutte un layer di validazione/gate sopra mem0.** Nessuna è di mem0.

---

# B. FORUM

## B.1 Hacker News (unica fonte forum di prima mano)

### [Agent memory as a file format](https://news.ycombinator.com/item?id=49508317) — 2026-08-31, **190 punti, 93 commenti**
Il thread più grosso e più recente sul tema. Citazioni verbatim verificate:
- **JohnMakin** (2026-08-31): *«"harness managed" memory is utter garbage, I am convinced, and I disable it immediately.»*
- **iamflimflam1** (2026-08-31): Claude *«...later in treats the comments as gospel truth»* — scrive quello che ha "scoperto" nei commenti e poi lo tratta da verità.
- **docheinestages** (2026-08-31): *«The Achilles' heel of this approach is the RAG.»* e *«Nothing beats curated data.»*
- **dataviz1000** (2026-08-31): *«once there is one poisoned line of text it negatively affects everything else»*.
- **Avijit_Thawani** (2026-08-31): *«there's lots of "memory" ... that should be suppressed and forgotten because they were ... proven wrong»*.

### [Show HN: Total Recall – write-gated memory for Claude Code](https://news.ycombinator.com/item?id=46907183) — 2026-02-05, **67 punti, 32 commenti**
Il concetto "write gate" ha già avuto la sua vetrina HN. Le critiche non hanno colpito l'idea, hanno colpito **il README e l'usabilità**: `rco8786` (2026-02-10): *«It's clearly an LLM dump ... missing a very, very important section: How to use»*. `Terretta` critica il nome come confusivo. Richieste: rimozione proattiva (`4b11b4`: chiedere "non lo usi da due settimane, serve ancora?"), memoria cross-project (`andershaig`), concorrenza fra sessioni Claude Code simultanee (`ejae_dev`).

### [Show HN: MCP Memory – OKF + SQLite FTS5](https://news.ycombinator.com/item?id=49286073) — 2026-08-13, **70 punti, 36 commenti**
- `schainks`: *«At hundreds of notes you blow a lot of tokens just to find one thing.»*
- `jrflo`: gli MCP *«waste tokens more than they end up helping»*.
- `esafak`: scettico sul *«recording facts, which may soon become stale, about a constantly changing code base»*.
- `bravura`: memoria su git = *«a lot of merge conflicts»*.
- `0c3ca83`: la memoria di Claude non funziona *«across agents»*.

### [Universal Memory Protocol](https://news.ycombinator.com/item?id=48428796) — 2026-06-06, **41 punti, 38 commenti**
Il thread è una lezione su cosa uccide un progetto di memoria su HN, e riguarda noi direttamente:
- `nullc`: *«I would expect to see tables or figures showing task success rates»* con e senza.
- `aogaili`: *«none of the methods seems to have observable, measured improvements over the basics»*.
- `bryanlarsen`: *«How about just a memory dir in your project's git folder?»*
- `avaer`: *«Agents are perfectly capable of discovering memories on the FS»*.
- `up2isomorphism`: *«I don't even want a shared agent memory»*.

### [Everyone's trying vectors and graphs for AI memory. We went back to SQL](https://news.ycombinator.com/item?id=45329322) — 2025-09-22, **136 punti, 63 commenti**
- `muzani` (2025-09-24), multilingua: *«The more languages you support, the more false hits you get»*.
- `shepardrtc` (2025-09-24): la negazione rompe tutto — "I hate espresso" e "I love black coffee" convivono e il retrieval ne prende una sola.
- `mynti`: quanto si può memorizzare *«before it will spam the context with irrelevant "memories"»*.
- `sdesol` (2025-09-25): usare un LLM per generare query è *«6-8 orders of magnitude slower»* di una lookup diretta.

### Commenti HN sparsi (via Algolia, `tags=comment&query=mem0`)
- `Varun_shodh` (2026-02-28): *«every AI memory system I tried (mem0, Cognee, Zep) makes 2-3 LLM API calls»* per salvare **una** memoria.
- `endymi0n` (2026-04-14): *«Facts are an incredibly dull and far too rigid tool»*; l'ironia produce estrazioni false ("scherza su un sixpack" → "interessato alla forma atletica"); i fatti binari falliscono sul cambiamento ("volo per Parigi" → poi NYC).
- `psyduck123` (2026-04-02): *«I don't trust any model to extract the right structure at write time»*.
- `bozbuilds` (2026-04-08): mem0/Letta/Zep *«all target memory as "personalization" ... None ... designed for multi-agent memory sharing»*.

### [Ask HN: Mem0 stores memories, but doesn't learn user patterns](https://news.ycombinator.com/item?id=46891715) — 2026-02-04, 9 punti, 7 commenti
`fliellerjulian` (YC W23): il gap non è memorizzare, è **imparare dalle correzioni**. Sul perché non basta lasciar curare all'utente: *«most users did not maintain their own system memory themself properly»*. `solarkraft` (2026-02-05): *«user corrections are the highest-signal data»* — e non capisce come mai nessuno le sfrutti.

## B.2 Forum Letta (Discourse, raggiungibile)
31 topic totali visibili; il più discusso è ["Dynamic tools and error handling"](https://forum.letta.com/t/72) con 29 risposte. Il thread comparativo ["Agent memory: Letta vs Mem0 vs Zep vs Cognee"](https://forum.letta.com/t/agent-memory-letta-vs-mem0-vs-zep-vs-cognee/88) (2025-10-29) **non contiene lamentele** — è didattico, 2 risposte del maintainer. Limite dichiarato dal maintainer: *«Memory context may be slightly behind the most recent conversation turns»*, e l'AI Memory SDK richiede Letta Cloud, non self-hostabile.
**Volume troppo basso per estrarne conteggi: il forum Letta non è dove vive il dolore.**

## B.3 Italiano
Cercato in italiano ("si dimentica", "ricorda cose sbagliate"): **i risultati sono tutti blog editoriali, nessun forum con voce utente.** L'unico che formula il dolore in modo non promozionale è [manager.it, "Memory stack: il mito pericoloso dell'agente AI che ricorda tutto"](https://manager.it/memory-stack-mito-dellagente-che-ricorda-tutto/). **Non è stata trovata una comunità italofona di utenti su questo tema.**

---

# C. PROGETTI PICCOLI E SCONOSCIUTI

## C.1 Il dato di contesto, sgradevole ma necessario
- **PulseMCP indicizza 766 server MCP** che matchano "memory" ([pulsemcp.com/servers?q=memory](https://www.pulsemcp.com/servers?q=memory), letto 2026-09-02).
- Cercando su GitHub `provenance`, `citation`, `contradiction`, `temporal validity`, `verification`, `quarantine` + memory/agent con `stars:<200`, il ricercatore ha trovato **oltre 25 repo distinti con la stessa identica proposta di valore di verimem**, quasi tutti creati fra luglio e agosto 2026, la maggior parte con 0-3 stelle, molti con `pushed_at` = 2026-09-02 (oggi).
- **In una di queste query è comparso `aureliocpr-ctrl/verimem` (2★).** Siamo dentro il campione, indistinguibili dagli altri dall'esterno.

**Conseguenza operativa: il concetto "memoria verificata con gate sulla source" non è un'idea rara nel 2026. È affollato. Ciò che non è affollato è la MISURA** — nessuno dei 25 repo mostra un numero riproducibile, ed è esattamente ciò che HN chiede (`nullc`, `aogaili`, sezione B).

## C.2 Tabella
| Progetto | ★ | Creato / ultimo push | Idea in una riga | Cosa fa che noi non facciamo |
|---|---|---|---|---|
| [agentic-box/memora](https://github.com/agentic-box/memora) | 713 | 2025-09-19 / 2026-09-02 | Memoria collettiva MCP con *deduplicating absorb* e **supersession lineage** | Grafo/UI di visualizzazione della lineage; memoria *collettiva* multi-agente come default |
| [EXXETA/exxperts](https://github.com/EXXETA/exxperts) | 352 | 2026-07-07 / 2026-08-31 | Agenti local-first con **memoria approvata dall'utente** prima della scrittura | Il gate è **umano e interattivo**, non entailment automatico |
| [davegoldblatt/total-recall](https://github.com/davegoldblatt/total-recall) | 202 | 2026-02-05 / **2026-02-12** | **Write gate** + *correction propagation* per Claude Code | Propagazione delle correzioni a valle; **fermo da 7 mesi** dopo 67 punti HN |
| [teolex2020/aura-memory](https://github.com/teolex2020/aura-memory) | 73 | 2026-02-23 / 2026-08-30 | Runtime Rust offline: versioning temporale, provenance, *contradiction governance* | Zero LLM richiesto, storage cifrato portabile |
| [yantrikos/yantrikdb](https://github.com/yantrikos/yantrikdb) | 56 | 2026-02-23 / 2026-09-02 | Motore Rust: decay temporale, contradiction detection, consolidamento autonomo, HNSW | Cluster openraft; libreria embeddable con binding Python |
| [arc-labs-ai/brain-db](https://github.com/arc-labs-ai/brain-db) | 29 | 2026-05-10 / 2026-08-03 | Memorie **tipate** con provenance, confidence e validità **bi-temporale** | Tipizzazione forte (fact/preference/event/entity/relation) + fusione semantic+lexical+graph+temporal |
| [openminion/sophiagraph](https://github.com/openminion/sophiagraph) | 9 | 2026-05-23 / 2026-09-01 | Knowledge graph con provenance, **trust**, namespace, snapshot portabili | Snapshot esportabili/importabili come artefatto |
| [billy12151/memory-arbiter-mcp](https://github.com/billy12151/memory-arbiter-mcp) | 7 | 2026-07-04 / 2026-09-02 | Un solo SQLite locale, **tutti i tool di coding leggono gli stessi fatti verificati** | L'arbitraggio cross-tool (Claude Code + Cursor + Codex sullo stesso DB) |
| [GiulioDER/RE-call](https://github.com/GiulioDER/RE-call) | 3 | 2026-07-07 / 2026-09-02 | *«Memory that abstains instead of guessing»*: verdetto + confidence + provenance su ogni hit | **Rifiuto calibrato al READ** (noi quarantiniamo al write, lui si astiene al read) |
| [Quarktex/citegate](https://github.com/Quarktex/citegate) | 1 | 2026-08-02 / 2026-08-02 | **Cite-or-refuse imposto dal motore**: verifica deterministica della citazione a query time | Verifica della citazione **al momento della lettura**, non solo della scrittura |

**Menzioni con un'idea che vale, sotto le 3 stelle:**
[aayushman-singh/hydraclaim](https://github.com/aayushman-singh/hydraclaim) (0★) — ogni fatto è un **claim con validity window**; contraddizioni e overwrite sono struttura di grafo di prima classe; il router **si astiene** se il grafo non regge la risposta.
[Nas01010101/tenet](https://github.com/Nas01010101/tenet) (0★) — bi-temporale con **keyed supersession**, time-travel recall, e una `P(still valid)` appresa; **letture senza LLM**.
[memvara/memvara](https://github.com/memvara/memvara) (1★) e [davccavalcante/gaptime](https://github.com/davccavalcante/gaptime) (2★) — bi-temporale (valid time + transaction time), risoluzione deterministica delle contraddizioni.
[troybrandonc-bit/Omem](https://github.com/troybrandonc-bit/Omem) (0★) — *append-only beliefs with evidence*, **le contraddizioni si tengono**, non si risolvono.
[poudelsubhan/engram](https://github.com/poudelsubhan/engram) (0★) — le memorie sono claim con ciclo di vita; il ranking è *similarity × earned trust*; **la quarantena si propaga a cascata** sul grafo di provenance.
[vtino17/context-quarantine](https://github.com/vtino17/context-quarantine) (0★) e [leonardoeverling-spec/governed-context](https://github.com/leonardoeverling-spec/governed-context) (0★) — "admission firewall" / "quarantine-only writes".
[Die-Namic-Systems/Nestor](https://github.com/Die-Namic-Systems/Nestor) (1★) — la domanda in copertina è *«Has a human checked this?»*.
[emeraldleaf/okl](https://github.com/emeraldleaf/okl) (0★) — lezioni di ingegneria **trattate come test, non come note**, con A/B receipt nel repo.

---

# D. LE DOMANDE CHE GLI UTENTI FANNO, E LE RISPOSTE CHE RICEVONO

| Domanda (come la pongono) | Dove | Risposta ricevuta |
|---|---|---|
| "Come rendo la memoria meno indiscriminata?" | [mem0 disc #4289](https://github.com/mem0ai/mem0/discussions/4289), 2026-03-10 | **Nessuna risposta dal progetto.** 4 utenti rispondono con workaround: spegni AutoCapture; tagga i blocchi del prompt con ruoli semantici; classifica al write in tier con TTL; pota a mano. Un quinto propone il proprio adapter di governance. |
| "Come gestite dedup e contraddizioni?" | [mem0 disc #4787](https://github.com/mem0ai/mem0/discussions/4787), 2026-04-11 | Risposta dalla community, non dal progetto: dedup = **solo hash MD5**; contraddizioni **tenute entrambe by design**. Due utenti propongono supersession esplicita come alternativa. |
| "Come si dimentica una conoscenza?" | [graphiti #864](https://github.com/getzep/graphiti/issues/864), 2025-08-26 | 7 commenti, issue chiusa. |
| "Perché non riproduco i vostri numeri?" | [mem0 #2800](https://github.com/mem0ai/mem0/issues/2800), da 2025-05-26 | "Gli score sono della piattaforma cloud". **7 utenti in 6 mesi non si accontentano.** |
| "Come vedo *perché* ha restituito questo?" | [basic-memory #1155](https://github.com/basicmachines-co/basic-memory/issues/1155), 2026-07-26 | Feature request per un *retrieval inspector* con chunk, score e **match provenance**. Chiusa. |
| "Come misuro la qualità del recall?" | [cognee disc #3698](https://github.com/orgs/topoteretes/discussions/3698), 2026-06-29 | 1 risposta. |
| "Memoria condivisa fra agenti / macchine?" | claude-code [#25739](https://github.com/anthropics/claude-code/issues/25739), [#24382](https://github.com/anthropics/claude-code/issues/24382), [#16600](https://github.com/anthropics/claude-code/issues/16600) | Tutte **aperte**. 74 reazioni combinate, nessuna soluzione. |
| "Dove diavolo scrive il file?" | MCP servers [#1018](https://github.com/modelcontextprotocol/servers/issues/1018), [#692](https://github.com/modelcontextprotocol/servers/issues/692) | **Aperte da 17-18 mesi**, 38 reazioni combinate. |
| "Serve davvero un memory server MCP?" | HN 48428796, 2026-06-06 | Le risposte più votate sono **no**: *«How about just a memory dir in your project's git folder?»*, *«I don't even want a shared agent memory»*. |
| "Come impedisco che ricordi cose sbagliate?" (in questa formulazione) | — | **Formulazione non trovata.** Gli utenti non chiedono di *impedire*: chiedono di *ripulire dopo*. |

---

# I 10 DOLORI PIÙ FREQUENTI

Conteggio: *T* = thread/issue/discussion distinti in cui è stato visto (su ~40 aperti e letti); *R* = reazioni/upvote sommati dove disponibili; *K* = conteggio keyword riproducibile.

**1. Si memorizza tutto, e la maggior parte è spazzatura.** T=9 · il caso misurato è **97,8% junk su 10.134 entry** ([mem0 #4573](https://github.com/mem0ai/mem0/issues/4573)).
> *«it essentially had stored everything from the conversation»* — [mem0 disc #4289](https://github.com/mem0ai/mem0/discussions/4289), 2026-03-10
> *«"harness managed" memory is utter garbage»* — JohnMakin, [HN](https://news.ycombinator.com/item?id=49508317), 2026-08-31

**2. Un fatto falso, una volta entrato, si auto-rinforza.** T=6.
> *«Any hallucination that gets stored once will be re-extracted indefinitely»* — mem0 #4573 (808 copie di "User prefers Vim")
> *«once there is one poisoned line of text it negatively affects everything else»* — dataviz1000, HN, 2026-08-31
> *«later in treats the comments as gospel truth»* — iamflimflam1, HN, 2026-08-31

**3. Duplicati e quasi-duplicati.** T=11 · K=**53** titoli nei 6 repo · K=**1441** issue GitHub-wide con `"duplicate memories"`. Nel corpus mem0 auditato: **37,6% di near-duplicate** dopo la prima pulizia.

**4. Fatti vecchi che non muoiono, e cancellazioni che non cancellano.** T=8 · K=`"stale memories"` **1538** GitHub-wide.
> `forget()` rimuove i nodi ma `recall()` serve il fatto *«sometimes indefinitely»* — [cognee #3526](https://github.com/topoteretes/cognee/issues/3526)
> *«facts, which may soon become stale, about a constantly changing code base»* — esafak, HN, 2026-08-13

**5. Il recall trova cose plausibili e sbagliate.** T=9 · K=38 titoli.
> *«there's lots of "memory" ... that should be suppressed and forgotten»* — Avijit_Thawani, HN
> Negazione rotta: "I hate espresso" + "I love black coffee" → il retrieval ne prende una sola (shepardrtc, HN, 2025-09-24)

**6. Costo e latenza della scrittura.** T=7.
> *«every AI memory system I tried (mem0, Cognee, Zep) makes 2-3 LLM API calls»* — Varun_shodh, HN, 2026-02-28
> *«At hundreds of notes you blow a lot of tokens just to find one thing.»* — schainks, HN, 2026-08-13
> *«waste tokens more than they end up helping»* — jrflo, HN, 2026-08-13
> ~2 minuti per "What is 30+15?" — mem0 disc #4289

**7. Setup che non parte.** K=**109** titoli con `ollama`, **108** con `docker`, **57** con `install` nei 6 repo. È **il tema numericamente più grosso di tutti**, di gran lunga. [graphiti #868 "Cannot get minimal example to work with Ollama"](https://github.com/getzep/graphiti/issues/868) (13 commenti), [mem0 #3391](https://github.com/mem0ai/mem0/issues/3391) (28 commenti).

**8. Non so dove scrive, non posso spostarlo, non è portabile.** R=**38** (MCP servers #1018+#692) + **156** (claude-code #25739+#25947+#28276+#24382+#16600) = **194 reazioni**, tutte su issue **ancora aperte**.

**9. I numeri pubblicati non si riproducono.** T=4 · [mem0 #2800](https://github.com/mem0ai/mem0/issues/2800): **24 reazioni, 25 commenti, ≥7 utenti, 6 mesi**.
> *«we are unable to reproduce the accuracy you mentioned»* — dohooo, 2025-06-15
> *«none of the methods seems to have observable, measured improvements over the basics»* — aogaili, HN, 2026-06-06

**10. Multilingua.** T=3 · K=`non-english` **10**, `language` in-title **17**. [mem0 #4884](https://github.com/mem0ai/mem0/issues/4884) è la **2ª issue aperta più votata di mem0** (5 reazioni).
> *«The more languages you support, the more false hits you get»* — muzani, HN, 2025-09-24

---

# COSA CHIEDONO CHE NESSUNO DÀ

Ordinati per forza dell'evidenza. Segno ✅ = verimem lo fa; ⚠️ = parziale; ❌ = non lo facciamo.

1. **⚠️ Un gate di qualità PRIMA della scrittura, con un `REJECT` esplicito.** Chiesto come punti 2 e 4 su 5 in [mem0 #4573](https://github.com/mem0ai/mem0/issues/4573); riproposto in 5 discussion mem0 distinte (#4730, #6682, #7071, #7120, #4289) fra aprile e agosto 2026; disegnato da zero da un utente in [graphiti #760](https://github.com/getzep/graphiti/issues/760) con le parole *«source-bound contract»* e *«quarantine queue»*. **È il nostro prodotto** — ma nessuna di queste persone lo cerca con la parola "verified memory".
2. **❌ Prevenzione del feedback loop: marcare i ricordi richiamati perché non vengano ri-estratti.** È il **punto 1 su 5** per impatto dichiarato in mem0 #4573, e la causa delle 808 copie di "Vim". Un gate sulla source **non lo copre**: un fatto ri-estratto dal recall È supportato dalla sua source (la source è il recall). Questo è un buco reale, e nessuno dei 25 progetti trovati lo affronta.
3. **❌ Imparare dalle correzioni dell'utente.** [Ask HN 46891715](https://news.ycombinator.com/item?id=46891715), 2026-02-04: *«user corrections are the highest-signal data»*, e nessuno le usa. Il motivo per cui non basta la cura manuale, dalla stessa fonte: *«most users did not maintain their own system memory themself properly»*.
4. **❌ Un retrieval inspector: chunk, punteggi, provenienza del match, mostrati.** [basic-memory #1155](https://github.com/basicmachines-co/basic-memory/issues/1155). Non "il fatto ha una source", ma *«perché questo risultato è arrivato al primo posto»*.
5. **❌ Portabilità: stesso corpus fra macchine, fra worktree, fra tool.** 194 reazioni su 7 issue aperte, alcune da 18 mesi. **È il dolore con più reazioni dell'intera ricerca** e nessuno lo risolve. [memory-arbiter-mcp](https://github.com/billy12151/memory-arbiter-mcp) (7★) ci prova.
6. **❌ Scrivere senza pagare 2-3 chiamate LLM.** Nessun prodotto mainstream lo offre; `tenet` lo mette in copertina come *LLM-free reads*.
7. **⚠️ Numeri riproducibili da terzi, sull'OSS e non sul cloud.** [mem0 #2800](https://github.com/mem0ai/mem0/issues/2800) è il precedente: 6 mesi di "+1" e nessuna risposta ha chiuso la questione. Su HN, la prima domanda a un progetto di memoria è *«tables or figures showing task success rates»*. Se pubblichiamo, questo è il primo colpo che prendiamo.
8. **❌ Potatura assistita e revisione periodica.** *«Memory should be regularly reviewed, compacted, and cleaned up»* (docheinestages, HN); *«you haven't referenced this in two weeks, still relevant?»* (4b11b4, HN).
9. **❌ Multilingua che non sia inglese hard-coded.**
10. **⚠️ Una risposta all'obiezione "basta una cartella con dei file".** Sollevata da 3 commentatori su HN nello stesso thread. Non è un requisito tecnico: è **l'obiezione commerciale** che va risposta con un numero, non con un'architettura.

---

# TRE COSE CHE CAMBIANO LA POSIZIONE DI VERIMEM

**① Il problema che risolviamo è reale e documentato con numeri di produzione** — il 97,8% di [mem0 #4573](https://github.com/mem0ai/mem0/issues/4573), le 808 copie di un'allucinazione, il `recall` di cognee che promuove la query a fatto. Su questo non c'è dubbio.

**② Ma non è il dolore più *frequente*, ed è il meno *nominato*.** Per volume, gli utenti soffrono di setup (217 titoli), di posizione del file (194 reazioni), di token bruciati. La qualità dei fatti compare in **2 titoli su ~5.400** con la parola "hallucination". Chi ha il problema **lo scopre solo dopo un audit manuale** — cioè quasi mai. **Il collo di bottiglia non è la cura, è la diagnosi.** Uno strumento che *mostra all'utente quanta spazzatura ha già in memoria* (come ha fatto a mano l'autore di #4573, e come ha fatto `simon9679` col suo auditor read-only) trova più utenti del gate stesso.

**③ Il concetto è affollato.** ≥25 repo con la stessa pitch, quasi tutti 2026, quasi tutti sotto le 3 stelle — verimem incluso. E il precedente più visibile ([total-recall](https://github.com/davegoldblatt/total-recall), 202★, 67 punti HN) è **fermo dal 2026-02-12**, sette giorni dopo il lancio. Ciò che manca a tutti e 25, e che HN chiede per primo, è **un numero riproducibile**: *«none of the methods seems to have observable, measured improvements over the basics»*.
