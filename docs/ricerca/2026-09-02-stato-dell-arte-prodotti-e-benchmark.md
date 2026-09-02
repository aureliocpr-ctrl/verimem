# Stato dell'arte — sistemi di memoria per agenti LLM (letture del 02/09/2026)

> **Cos'è**: mappa dei prodotti concorrenti, dei benchmark e dei canali di distribuzione,
> con la domanda centrale «qualcuno verifica un fatto contro la sua fonte prima di
> ammetterlo?». Prodotta il 02/09/2026 da un ricercatore esterno (Claude Opus, sola
> lettura, WebSearch/WebFetch) su mandato del lead. Ogni numero ha un URL; «non trovato»
> dove manca la fonte primaria. Temi di sicurezza esclusi dal mandato.
> **Le tre righe da leggere prima**: (C.1) nessun prodotto su tredici fa un gate di
> entailment al write — esiste solo in tre paper da maggio 2026; (C.3) ConsistencyGate
> pubblica i due assi che pubblichiamo noi e ha rilasciato i suoi banchi: l'esperimento
> che ci rende confrontabili è a portata; (D) il registry MCP per PyPI costa una riga nel
> README, e l'Agent Memory Leaderboard apre il secondo ciclo il 20/09/2026.

---

## A. PRODOTTI

### A.1 Quadro sintetico

Legenda: ✅ implementato e verificabile · ⚠️ parziale / opt-in / solo documentato · ❌ non trovato.

| | dedup | conflitti | validità temporale | supersessione | **verifica vs fonte** | licenza | ⭐ | download/mese | MCP |
|---|---|---|---|---|---|---|---|---|---|
| **mem0** | ❌ | ❌ (rimosso) | ❌ | ❌ «no UPDATE/DELETE» | ❌ | Apache-2.0 | 64,6k | PyPI `mem0ai` **3.598.595** | ✅ hosted |
| **Zep/Graphiti** | ✅ prompt LLM | ✅ edge invalidation | ✅ 4 campi bi-temporali | ✅ invalida, non cancella | ❌ (solo istruzione di prompt) | Apache-2.0 (Zep=cloud) | 30,5k | PyPI `graphiti-core` **1.092.635** | ✅ `mcp_server/` |
| **Letta** | ❌ | ❌ | ❌ | ⚠️ l'agente riscrive i blocchi | ❌ | Apache-2.0 | 24,6k | PyPI `letta` 198.311 ⚠️ | ✅ npm `@letta-ai/memory-mcp` |
| **LangMem** | ❌ | ❌ | ❌ | ⚠️ «consolidates and updates» | ❌ | MIT | 1,6k | PyPI 718.249 (ultimo rilascio 27/10/2025) | ❌ |
| **MCP `server-memory`** | ⚠️ sintattica | ❌ | ❌ | ❌ | ❌ | MIT | (repo 90,0k) | npm **364.588** | ✅ (è il server) |
| **Basic Memory** | ❌ | ⚠️ solo file-sync | ❌ | ❌ | ❌ | AGPL-3.0 | 3,8k | PyPI 49.498 | ✅ |
| **MemOS** | ⚠️ «smart dedup» | ⚠️ feedback in NL | ❌ | ⚠️ correction | ❌ | Apache-2.0 | 11,2k | non trovato | ❌ |
| **Cognee** | ✅ + ⚠️ semantica opt-in | ⚠️ **default OFF** | ⚠️ `valid_from/until` solo in provenance opt-in | ✅ `tag_superseded_edges` | ❌ (provenance + hash chain) | Apache-2.0 | **30.412** | PyPI 191.787 | ✅ |
| **Hindsight** | ✅ multi-livello | ✅ regole esplicite + audit | ✅ `mentioned_at` ≠ ingestione | ✅ tabella `invalidated_memory_units` | ❌ (`source_fact_ids`, retracted grounding) | MIT | **22.133** | non misurato | ✅ + 14 integrazioni |
| **Memori** | ❌ | ❌ | ❌ | ❌ | ❌ | file=Apache-2.0, metadato GitHub=`NOASSERTION` | 16.314 | PyPI 57.499 | ✅ hosted |
| **Memobase** | ⚠️ per slot | ⚠️ prompt `UPDATE` | ⚠️ annotazioni dentro il testo | ⚠️ riscrittura distruttiva | ❌ | Apache-2.0 | 2.877 | PyPI 3.384 | ✅ |
| **MemMachine** | ⚠️ LLM, solo sopra 20 feature | ❌ | ❌ | ⚠️ delete+add, history table **rimossa** | ❌ **prompt impone inferenze** | Apache-2.0 | 3.210 | PyPI `memmachine-server` 651 | ✅ |
| **Supermemory** | ⚠️ solo doc | ⚠️ solo doc | ⚠️ scadenza, solo doc | ⚠️ `updates`+`isLatest` | ❌ ✅ coda revisione **umana** su `isInference` | MIT (motore non OSS) | 29.192 | npm 331.528 · PyPI 597.534 | ✅ hosted |

Fonti stelle/licenze: API GitHub (`api.github.com/repos/…`) e pagine repo, lette 2026-09-02. Download: `pypistats.org` e `api.npmjs.org` (finestra npm 2026-07-31→2026-08-29).
⚠️ **`letta` e `supermemory` su PyPI**: `last_week` 2.301 e 16.598 contro `last_month` 198.311 e 597.534. Rapporto anomalo (×86 e ×36). Riportato come pubblicato.

### A.2 Dettagli che contano

**mem0** — https://github.com/mem0ai/mem0
Il cambio di rotta più importante del 2026. README verbatim:
> «**Single-pass ADD-only extraction** -- one LLM call, no UPDATE/DELETE. Memories accumulate; nothing is overwritten.»

Cioè mem0 ha **tolto** la risoluzione dei conflitti che era il suo tratto distintivo. Le parole `NOOP`, `conflict`, `dedup` non compaiono più nel README.
Numeri (README, «New algorithm, April 2026»): LoCoMo 71.4→**92.5**, LongMemEval 67.8→**94.4**, BEAM 1M **64.1**, BEAM 10M **48.6**; 6,7–7,0K token; p50 0,88–1,09s.
Disclaimer verbatim, sotto la tabella:
> «Scores reflect Mem0's managed platform, which includes proprietary optimizations not available in the open-source SDK; open-source users should expect directionally similar gains but not identical numbers.»

Paper: https://arxiv.org/abs/2504.19413 (28/04/2025) — +26% relativo su LLM-as-a-Judge vs OpenAI su LoCoMo, graph +~2%, p95 −91%, token −90%.
Harness aperto: https://github.com/mem0ai/memory-benchmarks (Apache-2.0, 104⭐) — **valuta solo Mem0 Cloud e Mem0 OSS**, non i concorrenti. E dichiara LoCoMo come «~300 questions across 10 multi-session dialogues».
MCP: OpenMemory MCP dal 13/05/2025 — https://mem0.ai/blog/introducing-openmemory-mcp · https://docs.mem0.ai/platform/mem0-mcp

**Zep / Graphiti** — https://github.com/getzep/graphiti · https://help.getzep.com/facts
L'unico con bi-temporalità vera: `created_at` (quando Zep l'ha saputo), `valid_at` (quando il fatto è diventato vero), `invalid_at` (quando ha smesso), `expired_at` (quando Zep l'ha saputo). README: «old facts are invalidated — not deleted».
Il codice mostra dove si ferma. Prompt di dedup (`graphiti_core/prompts/dedupe_nodes.py`): «You are an entity deduplication assistant. NEVER fabricate entity names or mark distinct entities as duplicates.» Prompt di estrazione (`extract_edges.py`): «Only extract facts that: involve two DISTINCT ENTITIES from the ENTITIES list, **are clearly stated or unambiguously implied in the CURRENT MESSAGE**». È un'istruzione dentro il prompt, non un controllo separato: nessuna decisione ammetti/rifiuta.
Trappola: `add_episode_bulk` «should only be used when edge invalidation is not required» — in modalità bulk l'invalidazione non gira (https://help.getzep.com/graphiti/core-concepts/adding-episodes).
`getzep/zep` è **solo esempi**: «This repository is not Zep's product or service.» Il prodotto è cloud.
Numeri: paper https://arxiv.org/abs/2501.13956 (20/01/2025) DMR 94,8% vs MemGPT 93,4%; LongMemEval fino a +18,5% accuracy, −90% latenza. Pagina https://www.getzep.com/research/ (letta 02/09/2026, **senza data di pubblicazione**): LoCoMo **94,7%** (1459/1540), LongMemEval **90,2%** (451/500), reader e judge gpt-5.4.

**Letta** — https://github.com/letta-ai/letta
Memory blocks + archival + sleep-time agents che riscrivono i blocchi in background (https://docs.letta.com/guides/agents/architectures/sleeptime/). Nessun dedup, conflitto, validità temporale o verifica documentati: la qualità è demandata al giudizio dell'agente.
Il loro risultato più interessante è negativo per la categoria: **Letta filesystem 74,0% su LoCoMo con gpt-4o-mini, contro Mem0 graph 68,5%** — cioè mettere la conversazione in un file batte una libreria di memoria (https://www.letta.com/blog/benchmarking-ai-agent-memory/, 12/08/2025).
MCP: Letta è client MCP (https://docs.letta.com/guides/mcp/overview) **e** pubblica `@letta-ai/memory-mcp` v2.0.2 su npm, presente nel registry ufficiale come «Letta Memory MCP». ⚠️ Il repo `github.com/letta-ai/memory-mcp` dichiarato nel registry risponde **404** (02/09/2026).

**LangMem** — https://github.com/langchain-ai/langmem · https://www.langchain.com/blog/langmem-sdk-launch (18/02/2025)
Tre tipi (semantic/procedural/episodic), «Background memory manager … automatically extracts, consolidates, and updates agent knowledge». Nessun dettaglio pubblicato su come si risolve una contraddizione. **Nessun numero di benchmark pubblicato dal vendor: non trovato.** Ultimo rilascio PyPI 0.0.30 del 27/10/2025 (https://pypi.org/pypi/langmem/json) — dieci mesi fermo, con 718k download/mese (quasi certamente traffico transitivo).
⚠️ Terzi danno a LangMem due numeri LoCoMo diversi: **58,10** nella tabella Memobase e **78,05** in quella Memori.

**Server MCP «memory» ufficiale** — https://github.com/modelcontextprotocol/servers/tree/main/src/memory
Ancora uno dei 7 reference server (Everything, Fetch, Filesystem, Git, **Memory**, Sequential Thinking, Time). Knowledge graph in JSONL. Dedup solo sintattica: «Ignores entities with existing names», «Skips duplicate relations». Zero conflitti, zero temporale, zero verifica. **364.588 download npm/mese** — è il più installato di tutti in assoluto per singolo pacchetto MCP di memoria.

**MemMachine** — il caso limite. Il prompt di produzione (`semantic_memory/util/semantic_prompt_template.py`) dice l'opposto di un gate:
> «Not everything you ought to record will be explicitly stated. **Make inferences.**» · «If you are **less confident** … you should **still include it**» · «Do not delete anything unless a user asks you to»

Il «ground-truth-preserving» del titolo del paper (https://arxiv.org/abs/2604.04853, 06/04/2026, MemVerge) significa **conservare l'episodio grezzo e ridurre l'estrazione LLM**, non verificare il fatto derivato. LoCoMo 0,9169 con gpt-4.1-mini; LongMemEval-S 93,0%.

**Hindsight** (fuori dalla lista, ma con più stelle di Memori e MemMachine insieme) — https://github.com/vectorize-io/hindsight, MIT, **22.133⭐**, push 2026-09-02.
È il più avanzato sulle quattro domande non-verifica. Prompt di consolidamento: «PREFER UPDATE OVER CREATE», «**NO COMPUTATION: you do not have the full picture — never calculate, derive, or adjust numeric values**», `deletes` ammesso «only when an observation is directly superseded or contradicted by new facts», ogni operazione richiede un `reason` che «is audited to catch duplicate creates». `mentioned_at` = «when the source material that states this fact **was written** … NOT when it was added to memory».
Il pezzo più vicino a noi è `engine/reflect/retractions.py` (retracted grounding): quando un fatto citato sparisce, «the row simply stops existing … **but the document keeps stating it and keeps citing it**. Nothing in the pipeline notices … A retraction is the absence of a row, so it raises no watermark and reaches no prompt. **This module turns that absence into a value.**»
Numeri: https://benchmarks.hindsight.vectorize.io/ — LongMemEvalS 94,6%, LoComo10 92%, BEAM10M 64,1%. ⚠️ **Il banco (Agent Memory Benchmark) è della stessa azienda che fa Hindsight** (vectorize.io), e la pagina non pubblica i punteggi dei concorrenti né i modelli usati.

---

## B. BENCHMARK

| Banco | Cosa misura | Dimensione | Metrica | Miglior risultato pubblicato | Critica verificata |
|---|---|---|---|---|---|
| **LoCoMo** ([2402.17753](https://arxiv.org/abs/2402.17753), 27/02/2024) | QA su conversazioni lunghissime + event summarization + dialogo multimodale | **10 conversazioni**, 300 turni e 9K token in media, fino a 35 sessioni ([repo](https://github.com/snap-research/locomo), 1,1k⭐; il README **non dichiara** il n. di domande) | LLM-as-a-Judge (varia) | Zep 94,7% (gpt-5.4) · MemMachine 91,69% · mem0 92,5 (managed) | vedi sotto — è il banco più contestato |
| **LongMemEval** ([2410.10813](https://arxiv.org/abs/2410.10813), ICLR 2025) | 5 abilità: extraction, multi-session, temporal, knowledge update, **abstention** | 500 istanze; -S ~115k token/~40 sessioni, -M ~500 sessioni; **30 domande di abstention** (id `_abs`); MIT | accuracy autoeval GPT-4o | Hindsight 94,6% · mem0 94,4 (managed) · MemMachine 93,0 · Zep 90,2% | i breakdown pubblicati dai vendor elencano **6 categorie e saltano l'abstention** |
| **BEAM** ([2510.27246](https://arxiv.org/pdf/2510.27246), ICLR 2026) | 10 abilità su 128K–10M token | 100 conversazioni, ~2.000 domande; dataset su HF, [repo](https://github.com/mohammadtavakoli78/BEAM) | accuracy | mem0 64,1 (1M) / 48,6 (10M) · Hindsight 64,1 (10M) · Cognee 0,67 (10M) | Cognee dichiara che il proprio 10M è «exploratory» perché «selection and reporting use the same question set», su **20 domande** |
| **MemBench** ([2506.21605](https://arxiv.org/abs/2506.21605), ACL Findings 2025) | effectiveness / efficiency / capacity; factual e reflective; participation e observation | 7 meccanismi valutati; [repo](https://github.com/import-myself/Membench) | multiple | non trovato in fonte primaria | poco adottato dai vendor |
| **MemoryAgentBench** ([2507.05257](https://arxiv.org/abs/2507.05257), v4 28/06/2026) | 4 competenze: Accurate Retrieval, Test-Time Learning, Long-Range Understanding, **Selective Forgetting** | 12 dataset, contesti 103K–1,44M token | accuracy per competenza | AR GPT-4o 58,1% · TTL Claude-3.7 53,9% · LRU GPT-5-mini 66,2% · **SF GPT-5-mini 53,0% single-hop, picco 28% multi-hop** | ⚠️ la quarta competenza è *selective forgetting*, **non** «conflict resolution»: il caso contraddittorio è coperto solo con la regola «prioritize later information» |
| **HaluMem** ([2511.03506](https://arxiv.org/abs/2511.03506), v3 05/01/2026) | **allucinazioni a livello di operazione**: extraction, updating, QA | ~15k memory point, ~3,5k domande, 1,5k e 2,6k turni, >1M token; CC-BY-NC-ND-4.0 | Memory Recall, **Target Memory Precision**, FMR, F1 | vedi tabella C.2 | ⚠️ [il repo](https://github.com/MemTensor/HaluMem) è sotto l'org **MemTensor**, la stessa di **MemOS**, che vince su quasi tutte le celle |
| **Agent Memory Leaderboard** ([agentmemoryleaderboard.ai](https://agentmemoryleaderboard.ai/), [repo](https://github.com/AML-memory/agent-memory-leaderboard)) | 7 capacità testuali + traccia coding | >10 dataset (PersonaMem, LoCoMo-Refined, CLBench, BEAM, LongMemEval, ScriptMem), >1.500 storie, ~5.000 domande | 0–100, `public_suite_v3` | vedi sotto | ⚠️ la mappatura lettere A–H → nomi delle capacità **non è pubblicata** nel README |

### B.1 Agent Memory Leaderboard — dati letti dall'API pubblica il 2026-09-02
Lanciato **29/07/2026** da «researchers from more than twenty universities and research organizations»; primo ciclo chiuso il 07/08, leaderboard il 12/08; **secondo ciclo il 20/09/2026**. Due tracce (Textual, Coding) × due categorie (open-source methods, commercial products). Requisito d'ingresso: esporre due endpoint pubblici **Add** e **Search**, superare uno smoke test, pagarsi la propria infrastruttura.

| Traccia | Rank | Sistema | Score (0–100) |
|---|---|---|---|
| industry / textual | 1 | **MemoraX** | 58,02 |
| industry / textual | 2 | MemOS | 45,89 |
| industry / textual | 3 | NTES-MEMORY-SMART | 44,21 |
| academic / textual (50 voci) | 1 | InvMem | 45,06 |
| academic / textual | 2 | Refind | 44,97 |
| academic / textual | 3 | ActiveMemoryIndex | 44,84 |
| academic / textual | **19** | **Mem0** | **42,07** |
| academic / textual | 32 | mem0-BQE | 39,83 |

Il dato più informativo è una colonna: la capacità **«G»** vale **29,99** per il primo classificato e **9,82** per il secondo — la più bassa di entrambi, con foglie a **9,0** (G4, MemoraX) e **0,0** (G4, MemOS). Il README elenca sette capacità di cui l'ultima è «**Epistemic safety and privacy**», ma non pubblica la mappatura lettera→nome, quindi **non si può affermare che G sia quella**: solo che una capacità su sette sta a un quinto delle altre per tutti.

### B.2 Le critiche a LoCoMo, in ordine di durezza

1. **Audit indipendente, aprile 2026** — [dev.to/penfieldlabs](https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg), 04/04/2026, codice su [github.com/dial481/locomo-audit](https://github.com/dial481/locomo-audit): su 1.540 domande, **6,4% della answer key è sbagliata** (99 errori documentati, di cui 24 di attribuzione dello speaker) e il giudice gpt-4o-mini **accetta il 62,81% di risposte volutamente sbagliate ma topicamente adiacenti**. Gli errori fattuali secchi (nome sbagliato, data sbagliata) vengono presi ~89% delle volte; le risposte vaghe passano quasi due volte su tre.
2. **Zep, maggio 2025** — [blog.getzep.com](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/), 06/05/2025: conversazioni da 16.000–26.000 token (dentro la finestra di contesto), **il full-context batte Mem0 (~73% vs ~68%)**, categoria 5 senza ground truth, errori multimodali, attribuzione sbagliata, domande sottospecificate, **nessun test di knowledge update**.
3. **La contro-contestazione** — [getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5), aperta dal CTO di Mem0 l'08/05/2025: l'84% di Zep sarebbe in realtà **58,44% ±0,20**, per domande della categoria adversarial contate al numeratore ma non al denominatore (~25,56 punti), prompt di sistema modificato solo per Zep, e una sola run contro le 10 richieste. **Nessuna risposta dei manutentori Zep nell'issue.**
4. **LoCoMo-Plus** ([2602.10715](https://arxiv.org/html/2602.10715v1), 11/02/2026): task-disclosure bias e dipendenza dalla lunghezza delle metriche string-matching. Passando a LoCoMo-Plus: GPT-4o 62,99→41,94, Gemini-2.5-Pro 71,78→45,72.
5. **Il denominatore si muove.** Per lo stesso banco pubblico si leggono quattro conteggi diversi di domande: **1.540** (mem0, Zep, audit Penfield), **1.813** (Synthius-Mem), **«~300»** (harness ufficiale di mem0), e il repo originale che **non lo dichiara affatto**. E almeno due vendor (Mem0, Memori) escludono la categoria adversarial.

### B.3 MemDelta: quanto sopravvive dei guadagni pubblicati
[arXiv 2606.29914](https://arxiv.org/abs/2606.29914), 29/06/2026 — protocollo controllato, una variabile per volta, su LongMemEval-S (500 domande, 50+ sessioni, tre famiglie di modelli). Abstract verbatim, i quattro risultati:
- RAG verbatim pareggia il full-context su GPT-4o-mini (**47,2% vs 49,8%, p = 0,34**), ma il ranking **si ribalta** tra modelli: Gemini guadagna +14pp dal full context, Sonnet +31pp dal RAG, «partly because it **refuses 63%** of full-context queries»;
- cambiare **solo** l'embedding model sposta **+6,2pp** (p = 0,004): Mem0 batte MiniLM-RAG di +11pp ma perde contro cloud-RAG di 1,2pp — «**one variable flips the conclusion**»;
- la self-memory dell'agente (**42%**) sta sotto al retrieval di base (**47%**);
- su 2 tipi di domanda su 6 (n = 88) Mem0 pareggia il cloud RAG (**72,7% vs 73,9%, p = 1,0**) **a 50× il costo**.

Corollario: **MemTrace** ([2606.17328](https://arxiv.org/abs/2606.17328), 15/06/2026) misura per *knowledge point* invece che per domanda e trova che «when systems fail, the evidence was **retrievable 10 times more often** than it was missing»: il collo di bottiglia è l'uso dell'evidenza, non il retrieval.

---

## C. VERIFICA — la domanda centrale

### C.1 Esiste un sistema che ammette/rifiuta un fatto con un controllo di entailment contro la fonte?

**Nei prodotti: no. Zero su tredici.** Controllati mem0, Zep/Graphiti, Letta, LangMem, il server MCP `memory` ufficiale, Basic Memory, MemOS, Cognee, Memobase, Supermemory, Memori, MemMachine, Hindsight — leggendo prompt e codice dove disponibile, non solo i README. Nessuno esegue un controllo di supporto testuale con esito ammetti/rifiuta.

Quello che c'è al posto suo, in quattro classi distinte e tutte più deboli:

| Surrogato | Chi | Cosa fa davvero |
|---|---|---|
| **Tracciabilità** | Cognee (`source_quote`, `source_ref_key`), MemMachine (`add_citations`), Hindsight (`source_fact_ids`, `proof_count`) | conserva il puntatore alla fonte; **nessuno controlla che la fonte sostenga il fatto** |
| **Istruzione di prompt** | Graphiti («clearly stated or unambiguously implied»), Memobase («Never make up content not mentioned in the input») | è una richiesta al modello, non un controllo sull'output |
| **Anti-manomissione** | Cognee (`provenance/integrity.py`, catena di hash), `verifiedstate-mcp` (firma Ed25519, [Glama](https://glama.ai/mcp/servers/verifiedstate/verified-memory)) | prova che il fatto non è stato alterato, non che sia vero |
| **Revisione umana** | Supermemory (`isInference: true`, down-weighted, coda approve/decline), VerificAgent ([2506.02539](https://arxiv.org/abs/2506.02539): «a post-hoc **human** fact-checking pass») | funziona, ma non scala e copre solo le inferenze |

E c'è il caso opposto: **MemMachine istruisce esplicitamente il modello a inferire ciò che non è stato detto e a registrare anche ciò di cui è meno sicuro.**

**Nei paper del 2026: sì, tre, tutti usciti dopo maggio.**

| | Data | Meccanismo | Fatto rifiutato |
|---|---|---|---|
| **ConsistencyGate** [2607.22962](https://arxiv.org/html/2607.22962v1) | 25/07/2026 | gate al write-time: K=5 campioni di «How strongly is this candidate fact supported by the source context?» su [0,1], ammette se la media ≥ **τ=0,7** | **scartato** (non conservato) |
| **Eywa** [2605.30771](https://arxiv.org/abs/2605.30771) | 29/05/2026 | «stores immutable source evidence **before** deriving canonical facts, **validates extracted memories against typed signals and source support**» | flag per revisione |
| **MemTX** [2607.23929](https://arxiv.org/html/2607.23929v2) | 28/07/2026 | validate-and-commit a 4 controlli: confidence ≥0,6 (o authority ≥0,9), validity interval, semantic-conflict, dependency stability. **Non è entailment contro la fonte** | «equal authority from different sources is **quarantined for user review**» |

Fuori dal write-path c'è **ProvenanceGuard** ([2606.18037](https://arxiv.org/html/2606.18037), v3 27/08/2026): entailment vero (DeBERTa-v3-base-mnli-fever-anli) su agenti MCP, ma **a tempo di risposta**, non di scrittura. Reject/block F1 **0,802**, contro MiniCheck 0,783, RAGAS Faithfulness 0,758, AlignScore 0,662, SummaC-ZS 0,436 (40 tracce, 361 claim).

### C.2 Chi misura la precisione dei fatti *memorizzati*, non il QA downstream?

**Solo HaluMem, ed è di terzi.** Metriche definite: Memory Recall, **Target Memory Precision** («whether the extracted memories are factual and free from hallucination»), **False Memory Resistance** (resistenza a contenuto distrattore che l'AI menziona ma l'utente non conferma), F1.

Task *memory extraction*, giudice e answerer GPT-4o:

| Sistema | Recall (Med) | **Target Precision (Med)** | FMR (Med) | Recall (Long) | Target P (Long) |
|---|---|---|---|---|---|
| Mem0 | 42,91% | 86,26% | 56,80% | **3,23%** | 88,01% |
| Mem0-Graph | 43,28% | 87,20% | 55,70% | 2,24% | 87,32% |
| Memobase | 14,55% | 92,24% | 80,78% | 6,18% | 88,56% |
| MemOS | 74,07% | 86,25% | 44,94% | 81,90% | 82,32% |
| Supermemory | 41,53% | 90,32% | 51,77% | 53,02% | 85,82% |
| Zep | n/d — «does not provide a Get Dialogue Memory API» | | | | |

Task *memory updating*, accuracy: Mem0 25,50% → 1,45% (Long), Memobase 5,20% → 4,10%, Supermemory 16,37% → 17,01%, Zep 47,28% → 37,35%, MemOS 62,11% → 65,25%.
Conclusione del paper, verbatim: «existing memory systems tend to generate and accumulate hallucinations **during the extraction and updating stages**, which subsequently propagate errors to the question answering stage».

Il resto del campo misura cose adiacenti ma diverse:
- **PrecisionMemBench** ([2605.11325](https://arxiv.org/abs/2605.11325), v4 29/07/2026) misura la precisione del **retrieval**, non la verità del fatto: «a system that dumps its entire belief store can achieve perfect recall and mask severe precision failures»; le baseline stanno a «0,22 and below» su 89 casi. ⚠️ preprint di un solo autore che introduce anche il proprio sistema.
- **LongMemEval** ha 30 domande di abstention, che nessun vendor riporta nei propri breakdown.
- **Cognee** riporta, nel proprio report BEAM, `abstention 0.500` e `contradiction resolution 0.875` — **su 2 domande ciascuna**.

**Nessuno misura la «falsità servita al recall» con quel nome.** Il più vicino è ConsistencyGate: `contamination rate ρ` = «the fraction of incorrect facts among **all admitted facts**», con `admission precision = 1 − ρ`.

### C.3 Il nostro numero, messo accanto all'unico comparabile

ConsistencyGate riporta esattamente i due assi che riportiamo noi, sugli stessi ordini di grandezza:

| dataset | falsità (baseline → dopo il gate) | fatti veri persi | dimensione |
|---|---|---|---|
| MemContam (sintetico) | 50,0% → **1,2%** | 0% (recall 1,00) | 1.000 veri + 1.000 falsi, 600 QA |
| **LoCoMo-Contam** (conversazioni reali) | 50,0% → **34,1%** | **42%** (admission recall 0,58) | **50 probe pair** |
| MSC-Contam | 50,0% → **36,7%** | 7% (recall 0,93) | **41 probe pair** |
| *verimem (C10)* | *50,0% → 15,9%* | *29,3%* | *dataset non nominato al ricercatore* |

Tre cose da tenere ferme:
1. **Il 50,0% di partenza è una proprietà del dataset, non un risultato**: in ConsistencyGate è per costruzione (metà fatti corrotti). Se anche il nostro lo è, il baseline non è un merito né un demerito — è la definizione del banco.
2. **Non siamo confrontabili finché non giriamo sugli stessi dati.** Sulla carta 15,9% con −29,3% batte 34,1% con −42% su entrambi gli assi. Ma è un confronto tra dataset diversi, e quindi non regge.
3. **L'esperimento che lo renderebbe vero esiste ed è a portata**: il paper dichiara «We release all three benchmarks together with the gate implementation». I due banchi su conversazioni reali sono però minuscoli (50 e 41 coppie) — il che è a sua volta una critica pubblicabile, e un'occasione: un banco più grande sullo stesso disegno non esiste ancora.

Nota di metodo, sul costo del gate: ConsistencyGate misura anche **cosa perde su dati puliti** (LoCoMo non contaminato: QA F1 0,267 contro 0,271 di «scrivi tutto»). È il controllo che nessun vendor fa e che vale la pena copiare: un gate va misurato *anche* dove non c'è niente da fermare.

---

## D. DISTRIBUZIONE

### D.1 Registry MCP ufficiale — **è ancora in preview**
Nota testuale nei docs: «The MCP Registry is currently in preview. Breaking changes or data resets may occur before general availability.» (https://modelcontextprotocol.io/registry/quickstart)

Catena di pubblicazione, verbatim dai docs:
1. Il registry **ospita solo metadata, non artefatti** → il pacchetto va pubblicato **prima** su npm/PyPI/NuGet/crates.io/OCI.
2. Prova di proprietà, **diversa per ecosistema** (https://modelcontextprotocol.io/registry/package-types):
   - npm → campo `"mcpName": "io.github.user/nome"` in `package.json`;
   - **PyPI → la stringa `mcp-name: <server name>` nel README** (che diventa la description su PyPI); può stare in un commento HTML: `<!-- mcp-name: io.github.user/nome -->`;
   - NuGet → uguale a PyPI; **cargo → uguale ma il commento HTML NON funziona** («crates.io strips HTML comments»): deve essere testo visibile;
   - OCI → `LABEL io.modelcontextprotocol.server.name=…`; MCPB → URL contenente «mcp» + `fileSha256`.
3. `mcp-publisher init` → `server.json` (schema `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`, campi `name`, `description`, `repository`, `version`, `packages[]` con `registryType`/`identifier`/`transport`).
4. `mcp-publisher login github` (device flow) → il nome **deve** iniziare con `io.github.<username>/`. Alternative: DNS authentication per un dominio proprio.
5. `mcp-publisher publish`.

⚠️ **Il numero di server nel registry non è leggibile dall'API**: `registry.modelcontextprotocol.io/v0/servers?limit=1` restituisce `metadata: {count: 1, nextCursor: …}` — un cursore, non un totale. **Non trovato.** La ricerca funziona però bene: `?search=memory&limit=30` restituisce 30 server di memoria, fra cui «Letta Memory MCP» v2.0.2 e una lunga coda di prodotti sconosciuti.

### D.2 Marketplace plugin di Claude Code
(https://code.claude.com/docs/en/plugin-marketplaces · https://code.claude.com/docs/en/plugins-reference)
- Marketplace: `.claude-plugin/marketplace.json` nella root del repo. Obbligatori: `name` (kebab-case), `owner{name}`, `plugins[]` con `name` + `source`.
- Installazione: `/plugin marketplace add owner/repo` (anche `owner/repo@v2.0`, URL git, marketplace.json remoto, path locale), poi `/plugin install nome@marketplace`.
- Plugin: `.claude-plugin/plugin.json`, **solo `name` obbligatorio**. ⚠️ vincolo secco: tutte le directory dei componenti (`skills/`, `commands/`, `agents/`, `hooks/`, `.mcp.json`) stanno nella **root del plugin, non dentro `.claude-plugin/`**.
- Un server MCP si distribuisce dentro un plugin con `.mcp.json` (o il campo `mcpServers`), usando `${CLAUDE_PLUGIN_ROOT}` per i path.
- **Marketplace ufficiale Anthropic**: esiste — i nomi `claude-code-marketplace`, `claude-plugins-official`, `anthropic-plugins` sono riservati — ma **la procedura per esserci non è documentata: non trovato**. La doc raccomanda GitHub come hosting proprio.

### D.3 Directory di terze parti
- **Glama** (https://glama.ai/mcp/servers, letto 02/09/2026): **81.661 server indicizzati**, di cui **5.144 «Official»** e **3.512 «Claimed»**. Esiste un bottone «Add Server» e un meccanismo di claim; il metodo di scoperta non è documentato nella pagina.
- **Smithery** (https://smithery.ai/docs/build/publish): due vie — URL pubblico HTTPS da `smithery.ai/new` (requisiti: «Streamable HTTP transport», «OAuth support (if auth required)») oppure bundle `.mcpb`. Scansione automatica dei server pubblici; metadata manuale via `/.well-known/mcp/server-card.json`. **Nessuno step di review documentato.** Totale server: non trovato.

### D.4 Trazione misurabile — la sola classifica con numeri veri

| Pacchetto | Download/mese | Fonte |
|---|---|---|
| PyPI `mem0ai` | **3.598.595** | pypistats.org/packages/mem0ai |
| PyPI `graphiti-core` | **1.092.635** | pypistats.org/api/packages/graphiti-core/recent |
| PyPI `langmem` | 718.249 | pypistats.org/packages/langmem |
| PyPI `supermemory` | 597.534 ⚠️ | pypistats.org/packages/supermemory |
| npm `@modelcontextprotocol/server-memory` | **364.588** (2026-07-31→08-29) | api.npmjs.org |
| npm `supermemory` | 331.528 | api.npmjs.org |
| PyPI `letta` | 198.311 ⚠️ | pypistats.org/api/packages/letta/recent |
| PyPI `cognee` | 191.787 | pypistats.org/api/packages/cognee/recent |
| PyPI `memori` | 57.499 | pypistats.org |
| PyPI `basic-memory` | 49.498 | pypistats.org/packages/basic-memory |
| PyPI `memobase` | 3.384 | pypistats.org |
| PyPI `memmachine-server` | 651 | pypistats.org |
| npm `@memorilabs/memori` | 332 | api.npmjs.org |

**Quale canale porta più installazioni nel 2026: non trovato.** Non esiste un dato pubblico che attribuisca installazioni per canale (registry vs marketplace vs npm/PyPI vs directory). Quello che è verificabile: il registry ufficiale è in preview e non espone un totale; Glama indicizza 81.661 server; i download di pacchetto sono l'unico segnale numerico con una fonte interrogabile. Le cifre tipo «10.000+ server MCP pubblici, 97M download SDK/mese» che circolano nei post comparativi **non sono state ricondotte a una fonte primaria** e non vengono riportate come dato.

---

## Cosa nessuno fa

1. **Verificare il fatto contro la sua fonte prima di ammetterlo.** Tredici prodotti controllati leggendo prompt e codice, zero gate di entailment al write. Esiste solo in tre paper, tutti da maggio 2026 in poi (ConsistencyGate, Eywa, MemTX), nessuno dei quali è un prodotto installabile.
2. **Mettere in quarantena invece di scartare.** ConsistencyGate droppa il fatto rifiutato; nei prodotti un fatto o entra o non nasce. L'unico «quarantined» trovato in letteratura è in MemTX, e solo per il pareggio di authority tra due fonti — non per mancanza di supporto testuale.
3. **Pubblicare il costo del filtro.** Nessun vendor dichiara quanti fatti **veri** perde. L'unico numero esistente al mondo su questo asse è l'`admission recall = 0,58` di ConsistencyGate su LoCoMo-Contam (42% dei fatti corretti rifiutati) — e non è un prodotto.
4. **Riportare l'abstention.** LongMemEval ne ha 30 domande dal 2024. I breakdown per categoria pubblicati da Zep, Supermemory e mem0 ne elencano sei e la saltano tutti e tre.
5. **Farsi misurare da qualcuno che non sia sé stessi.** Il pattern si ripete tre volte: HaluMem è di MemTensor e MemOS vince; l'Agent Memory Benchmark è di vectorize.io e Hindsight vince; l'harness `memory-benchmarks` è di mem0 e valuta solo Mem0. L'unica eccezione strutturale è l'Agent Memory Leaderboard, aperta il 29/07/2026.

## Cosa fanno tutti e noi no

*(misurato sui concorrenti; su verimem il ricercatore si è basato solo sulla descrizione ricevuta — non l'ha ispezionato)*

1. **Un numero su un banco pubblico nominabile.** Tutti pubblicano LoCoMo, LongMemEval o BEAM, per quanto quei banchi siano rotti. «Un dataset pubblico» senza nome non è citabile da nessuno.
2. **Un harness riproducibile pubblicato.** `mem0ai/memory-benchmarks` (Apache-2.0), `supermemoryai/memorybench` (MIT, 312⭐), `cognee/eval_framework/beam/REPORT.md` con deviazioni standard e numero di round. Anche quando i numeri sono discutibili, il modo di ottenerli è pubblico.
3. **Presenza nei canali di scoperta.** Registry MCP ufficiale, Glama (81.661 server, 5.144 «official», 3.512 «claimed»), Smithery, e un pacchetto con download misurabili. Per PyPI il costo d'ingresso al registry è **una riga nel README**: `<!-- mcp-name: io.github.<user>/<nome> -->`.
4. **Un ciclo di valutazione indipendente a cui iscriversi.** Mem0 è nella classifica AML (rank 19, 42,07). Il secondo ciclo apre il **20/09/2026** e chiede solo due endpoint pubblici `Add` e `Search`: è la finestra più concreta dei prossimi trenta giorni.
5. **Un endpoint MCP hosted oltre al pacchetto locale.** `mcp.mem0.ai`, `mcp.supermemory.ai`, `api.memorilabs.ai/mcp/`, più i server MCP in-repo di Graphiti, Cognee, Memobase, MemMachine e Hindsight. Il pacchetto locale è il canale degli sviluppatori; l'endpoint hosted è quello che finisce nei client altrui.

---

**Due note di onestà del ricercatore.** (a) I punteggi per-sistema dell'Agent Memory Leaderboard sono letti dall'API JSON del sito, non da una tabella renderizzata: se il sito cambia formato, il numero va riletto. (b) Il secondo filone sulla distribuzione non ha chiuso in tempo: la sezione D è interamente da fonti primarie lette direttamente, ma senza una seconda lettura indipendente su Smithery e sui canali di trazione — le tre righe «non trovato» in D restano tali finché qualcuno non le chiude.
