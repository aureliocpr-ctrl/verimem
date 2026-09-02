# Checklist unificata delle roadmap — HippoAgent → Engram → Verimem (02/09/2026)

> ## ✍️ Controfirma ws6 — 02/09/2026 19:51
>
> **30 righe verificate, 1 stato corretto, 9 evidenze rafforzate.** Ogni verifica
> è stata rifatta sul repo (`git grep`, `git log -S`, `wc -l`, lettura del
> codice), non sui piani.
>
> **① Le 5 righe che lo spot-check del lead segnava come dubbie: 4 danno ragione
> al ricercatore.** `G20` (il «1 commit» erano **i due commit della checklist
> stessa** — la stringa esiste solo nei documenti scritti oggi), `C4` (le 6
> `version INTEGER` sono in `migrations/`, `self_model.py`, `skill.py`: **nessuna
> nello schema `facts`**), `A18` (l'unica occorrenza di `opentelemetry` è un
> **commento**), `Q9` (**679** con tre criteri indipendenti; il 653 non si
> riproduce). Su `R5` hanno ragione entrambi: il commit citato è sbagliato, ma il
> codice marcato `REFUTED` **esiste** ed è `semantic.py:4278`.
>
> **② Una sola correzione di stato: `S6`**, da *MAI GUARDATO* ad *A METÀ*. Esiste
> `verimem/schema_abstraction.py` **con** `tests/test_schema_abstraction.py` (7
> test) — ma la funzione raggruppa per firma sintattica (prima parola + numero di
> token), **non** fa trasferimento fra domini: il meccanismo c'è, la capacità no.
>
> **③ Le altre 6 MAI GUARDATE e tutte le 5 ABBANDONATE reggono**, con l'evidenza
> ora scritta per esteso. Su `A8` ho evitato una trappola che avevo io: `git grep`
> dava 2 file e `git log -S` 5 commit, ma **erano tutti documenti** — la roadmap
> che la chiede e la checklist stessa.
>
> **④ Campione sulle FATTO**: 11 file dichiarati esistono tutti; i 4 conteggi di
> righe citati (670, 375, 289, 16) sono **esatti**; i 3 flag dichiarati «default
> ON» lo sono davvero (`v not in ("0","false","off","no")` con default vuoto, e
> `getenv("ENGRAM_PPR_FUSION","on")` a `semantic.py:2534`). Ho controllato i due
> file più piccoli perché *file esiste ≠ feature funziona*: `ann_index.py` (90
> righe) fa davvero faiss HNSW con `add` incrementale, `trusted_writer.py` (46) è
> una verifica `hmac.compare_digest`. **Nessuno dei due è uno stub.**
>
> ⚠️ **Cosa questa controfirma NON dice**: ho verificato **30 righe su 113**. Le
> restanti 83 non sono state ricontrollate, e su di esse questa firma non dice
> nulla. Non ho verificato le date né le attribuzioni a roadmap; e la regola
> «FATTO solo con evidenza fuori dai piani» l'ho applicata al mio campione, non
> all'intera tabella.


> **Mandato di Aurelio (02/09 19:30)**: «una checklist di tutte le roadmap, tutto quello che
> contengono senza le ripetizioni — da tante voci se ne faccia una — per capire di quello che
> ho chiesto cosa abbiamo fatto, cosa è irrealizzabile, cosa non abbiamo mai guardato, e
> paragonarlo con il nostro livello attuale».
> **Chi l'ha scritta**: un archivista esterno (Claude Opus, sola lettura, 67 letture/comandi in
> 15 minuti) su 12 roadmap e piani da maggio ad agosto, con verifica di ogni stato su codice,
> commit, test e registro — non sui piani stessi.
> **Spot-check del lead (02/09 19:45), 14 evidenze rifatte a mano su codice e git**: 10 esatte
> (251 `Tool(`; `--cov-fail-under=46`; `ENGRAM_GRADED_ADMISSION` default OFF; 33 riferimenti
> `tenants` in `gateway.py`; `pip-audit` in security.yml; `valid_until` nello schema; LANT-109 nel
> registro; `pydantic-settings` solo dipendenza; sqlcipher assente; 330 righe di `os.environ`/`getenv`)
> e **4 imprecise da chiarire**: G20 «`git log -S anti_trigger` vuoto» → trovato **1 commit**; Q9 «653
> `except Exception`» → contati **679**; A18 «0 occorrenze di opentelemetry» → **1**; C4 «nessuna
> colonna `version INTEGER`» → **6 occorrenze** in `verimem/` (da vedere se nello schema `facts` o
> altrove); e l'attribuzione di `3f01065` come «codice marcato REFUTED» va riletta (il commit è un
> fix del centered cosine). **Nessuna sostanza ribaltata, ma la tabella non è ancora controfirmata**:
> ws6 (istanza vera) sta verificando a campione ≥30 righe, a partire da queste, e firma o corregge.

---

## Legenda delle roadmap (sigle)

| sigla | documento | data |
|---|---|---|
| **M0-05-11** | `docs/MILESTONE_0.md` — paper design (4 layer, 20 tool, claim B2) | 11/05 |
| **R05-12** | `.claude/worktrees/goofy-wright-be4f6b/PRODUCTION_ROADMAP.md` — Sprint 1-8 | 12/05 (data interna 07/05) |
| **R05-13** | `docs/archive/2026-05-13_PRODUCTION_ROADMAP.md` — R05-12 + Sprint 7 «Hippo Dreams» | 13/05 |
| **R05-19** | `docs/ROADMAP-2026-05-19.md` — adapter di benchmark, cycle 158/159 | 19/05 |
| **R05-27** | `docs/ROADMAP-2026-05-27.md` — 11 fasi P0→P5 + N | 27/05 |
| **R06-02L** | `ENGRAM-LAB-ROADMAP.md` — i 3 buchi del gate | 02/06 |
| **R06-02P** | `ENGRAM-PRODUCTION-PLAN.md` (744 righe) — il piano-madre di giugno | 02/06→16/06 |
| **R06-06E** | `ENGRAM-ENTERPRISE-ROADMAP.md` — brick B0-B6 | 05-06/06 |
| **R06-09A** | `ENGRAM-ATTACK-PLAN-2026-06-09.md` — P0-P3 retrieval | 09/06 |
| **R07-18** | `docs/ROADMAP-v0.7.md` — Fase 0/1/2, gap 1-13 | 18/07→22/07 |
| **R07-22** | `docs/ROADMAP-v0.8.md` — WS1-WS5, debiti D1-D15, DoD K1-K8 | 22/07 |
| **R08-16** | `piano-settembre-2026.md` + `operazione-concessionario-16-08.md` — 3 ondate, W1-W8 | 16/08 |

---

## A · LA TABELLA

### A.1 — Il gate (il differenziatore)

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| G1 | Gate anti-confabulazione a strati lessicali (L1.x) su ogni scrittura | R05-19, R05-27, R06-02L, R06-02P, R07-18, R07-22, R08-16 | **FATTO** | `verimem/anti_confab_gate.py`, `anti_confabulation.py`, `l1_*_detector.py`; 18 detector al 27/05 | Acceso, ma è il difetto centrale dichiarato: «decide con le parole e sbaglia nei due versi» (REPORT-30-08 §2) |
| G2 | Moat: un fatto è ammesso solo se la FONTE lo sostiene (entailment source⊢fact) | R06-02L, R07-18, R07-22, R08-16 | **FATTO** | `verimem/grounding_gate.py` (670 righe); copertura agosto 9587/9768 = 98,1% | È l'unica cosa che nessun altro fa: 0 su 13 prodotti censiti il 02/09 (`docs/ricerca/2026-09-02-stato-dell-arte…` §A.1) |
| G3 | Verificare l'ESISTENZA della prova, non solo il suo formato | R06-02L (buco #2) | **FATTO** | `verimem/provenance_validator.py` (375 righe), cycle#111, attivo via `agent.py` | Il residuo reale era il mismatch di formato fra i due gate: chiuso in giugno |
| G4 | Impedire di spacciarsi per un writer fidato (token HMAC fail-closed) | R06-02L (buco #1), R06-02P §8 | **FATTO** | `verimem/trusted_writer.py`; wiring `45e78de`·`95ce5ef`·`5893ff8` | Chiuso; resta un problema di *design*: `verimem save` etichetta `writer_role='user'` le parole dell'agente → L1 spento sul 65,1% dei fatti vivi (W7-69) |
| G5 | Validità temporale dei fatti (scadenza / decay) | R06-02L (buco #3), R06-06E, R07-18 | **A METÀ** | `verimem/freshness.py`; colonna `valid_until` schema v10 (`ab6535c`) — popolata su **0 fatti su 17098** (doc 77) | La capacità c'è e nessuno la usa: classe «sa fare la cosa e non la fa» |
| G6 | Ricevuta di aggiudicazione su ogni scrittura (quarantena visibile, non muta) | R07-18 §0.1 | **FATTO** | `57a392c`·`6fb2565`·`ba772f1`; `verimem/adjudication_log.py` | Ogni write torna `{disposition, evidence_class, judge, score, threshold, margin}` |
| G7 | Giudice-di-record persistito per ogni decisione | R07-18 §0.2 (gap 3) | **FATTO** | riga `gate_decisions` + `judge_backend/model/threshold` sulla ricevuta | Chiude la deriva silenziosa di provider |
| G8 | Nomi di tier onesti + banda a due soglie sul cross-encoder | R07-18 §0.3 | **A METÀ** | `VERIMEM_CE_BAND_ENFORCE` default `"1"` (`grounding_gate.py:582`) | La banda esiste ma «si riempie di rumore posizionale, non di incertezza»; il ramo review costa 141× e fallisce muto (REPORT-30-08 §2) |
| G9 | Ricevute legate al CONTENUTO citato (hash dello span) | R07-18 §0.4, R07-22 D5, R08-16 2.4 | **A METÀ** | `grounding_span` presente sul 99,7% dei giudicati (1949/1955, W2-123), corretto 17/20 | Lo span c'è; lo snapshot content-addressed dei documenti indicizzati (R08-16 2.4) non trovato |
| G10 | `source_trust` acceso prima in osservazione, poi come gate | R07-18 §0.5 (gap 7) | **A METÀ** | `verimem/source_trust.py`; `ENGRAM_SOURCE_TRUST` non impostata → `False` (`source_trust.py:70`) | Costruito e mai acceso |
| G11 | Contraddizione sul write path + supersessione bi-temporale | R06-02P, R07-18 §1.1, R07-22 D2 | **FATTO** | `supersession_policy.py` (289 righe); NLI su CE locale (`fd416f0`), sibling query bounded (`0a05108`) | |
| G12 | L1 da veto ad avviso (chiudere i falsi positivi sui corpus verticali) | R07-18 P3, R07-22 WS1.3, R08-16 2.2 | **FATTO** | `ENGRAM_L1_DOMAIN_PRECISION` **default ON** dal 22/07 (`e6589c9`); L1.20-ad-avviso `5ea77b6d` | FP verticale 86,7% → 0,0% su `l1_business_corpus`; obiettivo G2 (≤3%) soddisfatto |
| G13 | Pre-filtro del soggetto su L3 (falsi positivi soggetto-diverso) | R07-18 P2, R07-22 D2 | **FATTO** | `ENGRAM_L3_SUBJECT_FILTER` default ON (`6284d07`), ORG-UNIT fix `12ce9ae` | Limite dichiarato: falsi negativi alias 35,2% (`wikidata_subject_eval`) |
| G14 | Ammissione graduata (sotto-soglia → low-confidence invece di quarantena) | R07-18 P1 (`912862f`) | **ABBANDONATO** | `ENGRAM_GRADED_ADMISSION` default OFF; misura ws7 30/08: falsità ammesse 13,3% → **98,7%** | Il codice resta, il flip è chiuso: «veleno misurato». E curerebbe la faccia sbagliata (i trattenuti recenti sono di L4.1, non del moat) |
| G15 | Banco anti-circolarità su gold di terzi (Wikidata mutation) | R07-18 P4, R07-22 K2 | **FATTO** | `benchmark/wikidata_subject_eval.py` | Nessun numero di FP viene più da etichette nostre |
| G16 | Persistere il PERCHÉ di ogni rifiuto (`quarantined_by`) | R08-16 2.2 | **FATTO** | doc `74-chi-ha-fermato-un-fatto-adesso-si-sa-sempre…` (02/09) | Il 71% vuoto è tutto debito storico, il flusso corrente è coperto |
| G17 | Consegnare al chiamante il disaccordo interno (`withheld_despite_judge`) | R08-16 (F3) | **A METÀ** | 150/4648 = 3,2% contato nel journal (doc 77); ricevuta sulle 2 porte dal 31/08 | Manca sulla CLI |
| G18 | Difese contro le iniezioni dentro la fonte citata, multilingue | R07-18 §2.1, R08-16 3.4 | **A METÀ** | `verimem/prompt_injection.py`; `benchmark/redteam_judge_injection.py`, `gate_redteam.py` | Lo screen «ferma E spiega» è il modello comunicativo migliore del prodotto (W2-69); il red-team completo del write path era ancora assegnato |
| G19 | Il gate è aggirabile con un `INSERT` sqlite diretto | R07-18 gap 1, R07-22 D11 | **NON FATTO ma fattibile** | evidenza di enforcement **non trovata** | È una libreria; il `gateway.py` (HTTP) è la porta che lo chiuderebbe, ma il file resta scrivibile |
| G20 | Anti-trigger sulle skill + banco FSM col cancello **ΔF1 ≥ 15pp** | M0-05-11 §4-§6 | **MAI GUARDATO** ⚠️ | ✅ **ws6**: `git log -S"anti_trigger" --all` → **2 commit, ed entrambi sono la checklist stessa** (`b73f51ab`, `3b10bafb`): la stringa esiste solo nei documenti scritti oggi, **non nel codice**. Il ricercatore aveva ragione. Nessun file FSM nel repo | La claim falsificabile centrale del paper di maggio non è mai stata costruita né falsificata. Era il gate go/no-go della 0.2.0 |

### A.2 — Recall e qualità del retrieval

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| R1 | Passare a un embedding multilingue | R06-02P, R06-09A P0.5 | **FATTO** | `multilingual-e5-base` live dal 04/06 (`config.py:64`) | Recall IT MRR 0,466 → 0,710 |
| R2 | Reranker cross-encoder sul top-k | R06-02P, R06-09A P0.2b/P0.4 | **A METÀ** | `ENGRAM_RECALL_RERANK` default ON (`9ca0c75`) + length-guard `_rerank_max_doc_chars` | Sulle query lunghe restituisce `"rerank": "skipped_long_query"` — «il rerank che quasi non gira» (doc 40); e il 02/09 ws1 ha misurato che il suo breaker scatta a metà banco e cambia l'esito (IT 20% ↔ 60%) |
| R3 | Recall ibrido vettore+parole (BM25) | R06-09A P0.3 | **FATTO** | `verimem/bm25_rank.py` + fusion RRF | |
| R4 | Fusione a 3 segnali (PPR sul grafo) accesa di default | R06-02P MOSSA 1 | **FATTO** | `ENGRAM_PPR_FUSION` default `"on"` (`semantic.py:2534`, flip `1d58be9`) | +7,5pp recall@5 a +40 ms; due leak di isolamento trovati dalla CI e chiusi (`e81392e`, `14b8a1c`) |
| R5 | De-anisotropia (mean-centering) | R06-09A P0.2 | **ABBANDONATO** ⚠️ | refutato a n=300, McNemar p=0,0003 (R@10 0,777→0,697); ⚖️ **ws6**: il lead ha ragione sul commit (`3f01065` è «fix(recall): true centered cosine», 09/06) e il ricercatore sulla sostanza — **il codice marcato REFUTED esiste ed è `semantic.py:4278`**: «⚠ REFUTED at n=300 … the n=25 'win' was NOISE … R@10 0.777->0.697, p=0.0003 … DEFAULT OFF, do NOT enable». Citazione corretta: il file, non il commit | Il «win» a n=25 era rumore |
| R6 | Selezione diversificata (MMR) per recuperare in profondità | R07-22 WS2 | **ABBANDONATO/SOSPESO** | `verimem/diversify.py` esiste, testato, **non cablato** — parere avversariale convergente 2/2 (glm-5.2 + deepseek-v4-pro) | Le domande temporali vogliono chunk quasi identici: MMR li tratterebbe come ridondanti |
| R7 | Indice approssimato (ANN) per la scala | R07-18 gap 6, R07-22 WS5.1 | **FATTO** | `verimem/ann_index.py` (faiss HNSW, `add` incrementale, gating `should_use_ann`), extra `verimem[ann]` | Dormiente sotto soglia; brute-force esatto 0,6/5,9/28,4 ms @10k/100k/500k (SCALE.md) |
| R8 | Banco onesto a 50k fatti + p95 pubblicati | R07-22 WS5.1, K7 | **A METÀ** | `SCALE.md` + `bench_scale_recall.py` fino a 100k (10/06), `benchmark/ann_recall_scale_bench.py` | I numeri ci sono, la pubblicazione col p95 come chiede K7 no |
| R9 | Entity-KG vero, o tagliare la promessa | R06-09A P2.1 | **A METÀ** | `verimem/entity_kg.py` (1384 righe) + PPR fusion sul recall path (default ON) | Da «morto, bench 0 recall» (09/06) a canale attivo del ranking. Non è un KG bi-temporale alla Graphiti |
| R10 | Astensione invece di allucinazione | R07-18/R07-22 G5, R08-16 | **A METÀ** | doc `36-la-promessa-di-astensione-esiste-funziona-ed-e-spenta` (31/08); promessa 🔴 su `search` (LANT-131) | Funziona end-to-end (1.000 su 7 run) e sulla porta MCP è **spenta di default** |
| R11 | Latenza recall p50 warm sotto 1 s | R08-16 2.3 | **FATTO** | p50 warm **3,478 ms** misurato in-process il 16/08 (fatto `latenza-recall-cli-16-08`) | Obiettivo superato di 280×; ma il sito dichiarava 166–237 ms — è il caso aperto V1; e da CLI una scrittura costa 22 s (ws8, 02/09) perché ogni comando ricarica il modello |
| R12 | Recall che attraversa lingue e sinonimi (muro M2) | R07-22 WS2, ricerca 02/09 | **NON FATTO ma fattibile** | doc 57 «attraversa le lingue e non attraversa i sinonimi», doc 58; `docs/ricerca/2026-09-02-muri-e-cure-letteratura.md` M2 | Assegnato a ws1 con esperimenti e predizioni già scritti |

### A.3 — Benchmark e prove pubbliche

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| B1 | Adapter HaluMem | R05-19 #1, R06-02L, R07-22, R08-16 3.1 | **FATTO** | 16 script `benchmark/halumem_*.py` + `docs/HALUMEM_OFFICIAL_PROTOCOL.md` | Extraction F1 **0,761**; il protocollo ufficiale contro MemOS 67,2 era il P0 fermo dal 20/06, riaperto il 16/08 |
| B2 | Adapter LongMemEval | R05-19 #2, R06-02P, R07-22, R08-16 3.2 | **FATTO** | `benchmark/longmemeval_runner.py` | recall@5 **0,8745** su n=500 (25/07) — il target 0,85 era già superato; il `0,790` che circolava era un sotto-campione |
| B3 | LoCoMo | R06-09A P1.1, R07-22 | **FATTO** | `benchmark/locomo_runner.py`, `qa_locomo_strict` | **0,8267** (n=150); target K4 0,88 non raggiunto. 46% dei fail sono astensioni, non errori |
| B4 | Confronto affiancato con mem0 / Zep / Letta | R06-02P build_next #8, R06-06E, R06-09A P1.1, R07-22 WS3.2 | **A METÀ** | `mem0_adapter.py`, `c10_lato_mem0.py`, `competitor_probe_mem0.py`, `memory_systems_comparison.py` | mem0 sì (con la discrepanza adapter dichiarata invece di pubblicare un numero falso, `e2d8314`); **zep e letta: adapter non trovati** |
| B5 | VeriBench come repo standalone + ≥1 riproduzione di terzi | R07-22 WS3, K5 | **NON FATTO** | `benchmark/veribench/` esiste **dentro** il repo (PREREGISTRATION.md, run_all.py, scoring.py); nessun repo standalone in `C:/Users/aurel/Code/` | La decisione (trasparenza dichiarata, mai org anonima) è presa; lo scorporo no |
| B6 | Comparativo su ground truth esterna umana (C10) | R08-16 | **FATTO** | TruthfulQA heldout, n=600, LANT-109: falsità servite **15,9%** (40/252) contro **50,0%** senza gate; falsi ammessi 13,3% IC95 [9,9–17,6]; veri persi 29,3% IC95 [24,5–34,7]; replica disgiunta 16,0% | L'unica riga il cui metro non è il giudice del prodotto |
| B7 | Paper arXiv «Write-time Confabulation Gates» | R05-19 #3 | **NON FATTO** | `docs/papers/write-time-confabulation-gates-DRAFT.md` — ancora DRAFT | Era «~2 giorni per finalizzare + submit» il 19/05 |
| B8 | Preprint VeriBench | R07-22 WS3.4 | **NON FATTO** | `docs/papers/veribench-preprint-DRAFT.md` — DRAFT | Subordinato alla decisione di Aurelio su org e pubblicazione |
| B9 | Posizionamento vs ConsistencyGate (arXiv 2607.22962) | R08-16 3.3 | **A METÀ** | commit `180deefa` «i banchi di ConsistencyGate sono dichiarati rilasciati e non hanno un indirizzo» | L'accademia è arrivata al write-time admission; il confronto empirico è bloccato sulla reperibilità dei loro banchi |
| B10 | Target di retrieval K4 (LoCoMo ≥0,88 · LongMemEval ≥0,85) | R07-22 K4 | **A METÀ** | LME 0,8745 ✔ · LoCoMo 0,8267 ✘ | Metà obiettivo. Il collo è cat2-temporal (10 errori) e cat1-multi-hop (5/15) |

### A.4 — Architettura, piattaforma, impresa

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| A1 | Architettura a 4 layer (core / learning / query / façade MCP) | M0-05-11 §2 | **NON FATTO** | package piatto `verimem/` con ~400 moduli; nessun `core/`, `learning/`, `query/`, `mcp/` | L'invariante «nessun handler MCP tocca L1/L2» non esiste |
| A2 | Ridurre la superficie MCP a 20 tool | M0-05-11 §3; ripreso come «profilo curato ~15» in R06-02P | **ABBANDONATO** | **251** `Tool(` in `mcp_server.py` (era 170+ a maggio, 215 il 27/05, 229 a giugno, 245 nella 0.7.5) — 251 confermato dal lead | La superficie è cresciuta di 12× rispetto al numero deciso. Il perché non è mai stato dichiarato: dedotto = ogni ciclo aggiungeva tool e nessuno li toglieva |
| A3 | Spezzare `dashboard.py` (2338 righe) in route | R05-12/13 §4.1 | **FATTO** | `verimem/dashboard_routes/` — 12 moduli (auth, chat, episodes, events, health, layout, lineage, memory_map, settings, skills, welcome, active_memory) | |
| A4 | Config in `pydantic-settings`, via i 65 `os.environ` sparsi | R05-12/13 §4.2 | **NON FATTO** | `pydantic-settings` è solo una dipendenza (`pyproject.toml:71`); la config resta dataclass + `os.environ` diffusi (330 righe di `os.environ`/`getenv` in `verimem/*.py`, conteggio del lead) | 11 env censite nel README + decine di `getenv` nei moduli |
| A5 | Registro dei provider in YAML + comando diagnostico | R05-12/13 §4.3, R06-02P Fronte A | **FATTO** | `providers.yaml` + `provider_registry`; fix prefissi Groq `aa20eb8`; `verimem providers` | Il doppio registro divergente è chiuso |
| A6 | Migrazioni versionate (Alembic) sui DB SQLite | R05-12/13 §4.5, R06-06E B4 | **NON FATTO** | nessuna cartella `migrations/`, nessun alembic | Lo schema si versiona a mano (`ensure_schema_version`, v6→v13+): funziona, ma non è quello che chiedevano |
| A7 | Modelli tipizzati su ogni body FastAPI e su ogni `inputSchema` MCP | R05-12/13 §4.6, R06-02P §8 | **NON FATTO** | quantificato il 05/06: `_SCHEMAS_BY_TOOL` copre **11 / 227 tool = 4%**; 203 hanno uno schema ma non è applicato → gap 192 | Il fix (auto-derivare dagli inputSchema) è pianificato e mai eseguito |
| A8 | Atomicità dello storage skill + `rebuild_index_from_files()` | R05-12/13 §4.4 | **MAI GUARDATO** | ✅ **ws6 conferma, con una trappola evitata**: `git grep` dà 2 file e `git log -S` 5 commit, ma **sono tutti DOCUMENTI** — la roadmap che la chiede e la checklist stessa; i «5 commit» sono due release e la checklist. **Nel codice non esiste**, e nessun test la nomina | |
| A9 | Backend Postgres | R07-18 §2.3, R07-22 WS5.3 | **NON FATTO** | nessun modulo postgres/psycopg | Era esplicitamente condizionale («solo se il bench 50k mostra che SQLite non regge»): la condizione non è stata verificata |
| A10 | Backup/restore ufficiale del DB | R05-27 P0b | **FATTO** | `verimem/backup.py` (545 righe), 11/11 test; CLI `backup-all` | VACUUM INTO atomico + rotazione |
| A11 | Rollback transazionale su forget/supersede | R05-27 P0c | **FATTO** | `verimem/undo_log.py` (334 righe), schema v7, CLI `facts forget --undoable / undo / undo-list` | Limite dichiarato nel CHANGELOG 0.7.5: tiene il testo in chiaro 7 giorni |
| A12 | Sandbox della shell deny-by-default | R05-27 P1 | **FATTO** | `verimem/sandbox.py` (953 righe), 44/44 test; `git config` write chiuso `7d23a72` | |
| A13 | Ricarica a caldo del server MCP | R05-27 P2a | **FATTO** | `verimem/hot_reload.py` (216 righe), 9/9 test | |
| A14 | Freno su CPU/RAM | R05-27 P2b | **FATTO** | `verimem/resource_monitor.py` (220 righe), 9/9 test | |
| A15 | Matrice dei permessi per ogni tool, applicata a runtime | R05-27 P0.5a (X1) | **A METÀ** | `verimem/tool_registry.py` cablato in `_capability_gate` (`mcp_server.py:7807`), fail-closed sugli sconosciuti — ma **`ENGRAM_CAPABILITY_GATE` default `off`** e **22 tool classificati su 251** | Il meccanismo è giusto e spento |
| A16 | Vista TUI dello stato del gate (tool / effetti / rollback / quarantene) | R05-27 P0.5b (X2) | **NON FATTO** | `verimem/tui.py` esiste ma i pane sono `ChatPane / SkillsPane / EpisodesPane / SettingsPane` — nessuno dei quattro richiesti | |
| A17 | Dashboard operatore «cosa sta facendo l'agente adesso» | R05-27 P3 | **A METÀ** | dashboard + `memory_map.py` + SSE `events.py` esistono; il pane real-time delle chiamate colorato per rischio non trovato | |
| A18 | Tracciamento standard OpenTelemetry → SIEM | R05-27 P4a, R06-06E B5 | **NON FATTO** ⚠️ | ✅ **ws6**: l'unica occorrenza è un **commento** (`l1_evidence.py:20`, che cita 'opentelemetry' come esempio di nome), non codice. Nessun export OTLP. Il ricercatore aveva ragione nella sostanza | Esistono `observability.py` e log JSON, ma non l'export OTLP che serve a entrare in azienda |
| A19 | Replay di un'intera sessione | R05-27 P4b, R06-02P | **A METÀ** | `verimem/episode_replay.py` — episodio singolo, non sessione con timeline | |
| A20 | Astrazione del provider di embedding + comando di migrazione | R05-27 P5 | **NON FATTO** | `embedding.py` singolo, modello via env; nessuna ABC `EmbeddingProvider`, nessun `embedding-migrate` | Il cambio di modello si è fatto lo stesso (04/06), a mano |
| A21 | Multi-tenant con isolamento forte | R05-27 I1 (posticipato), R06-06E B3, R06-02P R1#3 | **FATTO** | `verimem/gateway.py` — **un DB per tenant** (`tenants/<id>/memory.db`), API key hashate, `gateway_audit.py`, `gateway_backup.py`; 9 test di isolamento | Da «esplicitamente posticipato» il 27/05 a costruito. Il leak trovato dalla CI col flip fusion è chiuso (`e81392e`) |
| A22 | Cifratura a riposo + chiavi gestite dal cliente | R06-06E B3, R07-18 gap 5, R07-22 D8 | **NON FATTO** | nessun sqlcipher in `verimem/` (confermato dal lead) | Table-stakes enterprise mancante |
| A23 | SSO SAML/OIDC + RBAC | R06-06E B1/B2 | **NON FATTO** | `grep -i "saml\|oidc"` in `verimem/` → **0** | Restano session-token + API key: sufficiente per self-host, non per un review aziendale |
| A24 | Autorizzazione per-agente DENTRO un tenant | R07-18 gap 13/§1.3, R07-22 D4 | **NON FATTO** | evidenza non trovata | Conseguenza dichiarata: la visibilità della ricevuta è un oracolo di estrazione |
| A25 | GDPR: cancellazione crittografica + export art. 15/20 | R07-18 §2.2, R07-22 D8 | **A METÀ** | `verimem/facts_export.py` esiste; crypto-shred **non trovato**; il CHANGELOG 0.7.5 dichiara che l'undo log tiene la proposizione in chiaro 7 giorni | Il limite è scritto, non curato |
| A26 | Immagine Docker Linux headless | R06-06E B4 | **FATTO** | `Dockerfile` multi-stage (builder + slim runtime), extra `[headless]`, bind loopback di default | |
| A27 | Catena a prova di manomissione dell'audit (rilevazione) | R07-18 gap 4 | **FATTO** | `verimem/tamper_evidence.py` + catena su `adjudications.db` (`5d8214d`), `audit_verify()` / `audit_head()` | Onesto sul suo limite: dentro un DB scrivibile è solo rilevazione |
| A28 | Àncora esterna con chiave FUORI dal DB | R07-18 §1.2, R07-22 WS4.1/K6 | **A METÀ** | `verimem/audit_anchor.py` (215 righe): ricevuta firmata **ed25519** su ENTRAMBE le catene con head + conteggi + timestamp (task #24 step 2) | La firma esiste; l'ancoraggio periodico su un servizio esterno (TSA/transparency log) non trovato |
| A29 | Audit del percorso di ingestione (task #49) | R07-22 D6 | **NON FATTO** | evidenza non trovata | |
| A30 | Modo locale / air-gap con auto-verifica | R06-06E B6 | **FATTO** | `verimem/airgap.py` (`airgap_status()`), CLI `verimem airgap`, prova no-egress `c3aa874` (0 connessioni non-locali), keep_alive Ollama `d207d4a` | Nessun competitor si auto-verifica l'air-gap |
| A31 | Un solo interruttore di modo (`subscription \| byok \| local`) | R06-06E B2/B6 | **FATTO** | `verimem/mode.py` — `ENGRAM_MODE` deriva le env di basso livello senza sovrascrivere | |

### A.5 — Robustezza, qualità e rilascio
*(le voci storiche marcate «security/hardening» sono qui, riportate per ciò che chiedevano)*

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| Q1 | Esecuzione shell dell'IDE dietro autenticazione e controllo d'origine | R05-12/13 Sprint 1 (1.1/1.5/1.6) | **FATTO** | `Depends(_require_session_auth)` su tutti gli endpoint IDE; `cdc9d29`; `555a17f` chiude il DELETE su `/` | |
| Q2 | Filesystem ristretto di default + lista di negazione dei file sensibili | R05-12/13 1.2 | **FATTO** | `_is_sensitive` esteso alla classe dotenv `d3edeb7`; `bd3a427` per list/search | |
| Q3 | Le chiavi non compaiono mai nelle risposte HTTP | R05-12/13 1.3 | **FATTO** | Sprint 2 CVE-009 + redazione tracce `3e67a3a` | |
| Q4 | Ascolto su interfaccia non-loopback solo con opt-in esplicito | R05-12/13 1.4 | **FATTO** | `Dockerfile` + `--insecure-bind` + `HIPPO_TRUSTED_NETWORK` | |
| Q5 | Blocco delle richieste verso le reti interne (fetch e vision) | R05-12/13 1.7 | **FATTO** | `f479038` sul path immagine di vision; `test_ssrf.py` | |
| Q6 | Esecuzione Python isolata in container | R05-12/13 Sprint 5.1 | **FATTO** | `DockerPythonExecutor` + factory con fallback, 8 test | |
| Q7 | Chiavi nel portachiavi del sistema operativo | R05-12/13 5.4 | **MAI GUARDATO** | ✅ **ws6 conferma**: `git grep -i keyring -- 'verimem/*.py'` → **0**. Le chiavi passano da `user_settings.json` (`dashboard_routes/settings.py`, `welcome.py`) | Le chiavi restano in `user_settings.json` (incoerenza già segnalata il 10/06) |
| Q8 | Registro concatenato di ogni esecuzione di tool | R05-12/13 5.6 | **A METÀ** | catena completa sul write path (`adjudication_log` + `tamper_evidence`); sui tool MCP c'è `_audit_capability_call` ma il gate è default off | |
| Q9 | Tassonomia delle eccezioni + eliminare i `except` generici | R05-12/13 3.1/3.2/3.5 | **NON FATTO** | `verimem/errors.py` **non esiste** (confermato); `except Exception` nel package: ✅ **ws6 conta 679** con tre criteri indipendenti (`git grep` sui soli file tracciati, `grep -r` su `verimem/`, e `grep -r` escludendo `build/`) — **tutti e tre danno 679**, e `build/` non esiste nemmeno, quindi non è quella la differenza. **Il 653 non si riproduce**; obiettivo v1.0: 0 | |
| Q10 | WAL + timeout su ogni connessione SQLite | R05-12/13 3.3 | **FATTO** | `verimem/_sqlite_pragma.py` | |
| Q11 | CI su 3 sistemi × 4 versioni di Python + soglia di copertura 85% | R05-12/13 6.1 | **A METÀ** | matrice confermata (run `ci` 2716 verde 9/9 su win/ubuntu, py3.10-3.13); ma `ci.yml` → **`--cov-fail-under=46`** (confermato dal lead) | La matrice c'è, la soglia è ferma al valore di partenza di maggio (46%), non a 85% né al 90% della v1.0 |
| Q12 | Prova d'installazione da ambiente vergine | R05-12/13 6.2, R08-16 W2/W7 | **FATTO** | smoke `EXIT=0` su wheel + WSL Ubuntu 24.04 con `pip install verimem==0.7.1` (02/09 12:47-13:11) | Reso direttiva permanente da Aurelio il 01/09 |
| Q13 | Controllo delle dipendenze vulnerabili in CI | R05-12/13 6.3 | **FATTO** | `.github/workflows/security.yml` contiene `pip-audit` (confermato) | |
| Q14 | Eseguibile Windows autonomo (PyInstaller) | R05-12/13 6.6 | **MAI GUARDATO** | ✅ **ws6 conferma**: 0 occorrenze di `pyinstaller` o `.spec` in `verimem/` e `pyproject.toml` | |
| Q15 | Extra pip `[headless]` `[mcp-only]` `[full]` | R05-12/13 6.5 | **FATTO** | `pyproject.toml:86-106` (+ `[audit]`, `[ann]`) | Ma `sentence-transformers` (→ torch) sta nelle dipendenze di base: l'install pesa 3,4 GB e 22 minuti (smoke 02/09) |
| Q16 | Pubblicazione su PyPI | R05-12/13 6.7, R06-09A P3.1, R08-16 1.1/W7 | **FATTO** | tag `v0.7.1` su `1e293f4b`, publish run `33620334721`, PyPI serve 0.7.1 (wheel+sdist), 02/09 12:40 | Da «PyPI non pubblicato, 0 utenti esterni» (09/06) a pacchetto installabile e verificato dall'utente |
| Q17 | ADR per i meccanismi di memoria attiva | R05-12/13 7.1 | **MAI GUARDATO** | ✅ **ws6 conferma**: nessuna cartella ADR nel repo. L'unico file che un grep su «decision-record» pesca è `docs/stato-reale/quadro-decisione-versione-30-08.md`, che è un quadro di rilascio, non un ADR | |
| Q18 | Riferimento API Sphinx + tutorial da 30 minuti | R05-12/13 7.2 | **NON FATTO** | nessun `conf.py`, nessun commit «sphinx» | Sostituito di fatto da README + `agent_guide` |
| Q19 | `SECURITY.md`, `SUPPORTED_DEPLOYMENT.md`, `THREAT_MODEL.md` | R05-12/13 7.3 | **A METÀ** | `SECURITY.md` ✔, `docs/SAAS_DEPLOY.md` ✔, `docs/SECURITY_AUDIT_2026-07-11.md` ✔; `THREAT_MODEL.md` **non trovato** | |
| Q20 | CHANGELOG completo + guida di migrazione | R05-12/13 7.4/7.5 | **A METÀ** | `CHANGELOG.md` esiste ed è dettagliato; nessuna guida di migrazione | |
| Q21 | Tag v1.0.0 | R05-12/13 7.7 | **NON FATTO** | ultimo tag pubblicato `v0.7.1`; `pyproject` dichiara 0.7.6 | |

### A.6 — Sonno, sogno, skill (il cuore «neuro»)

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| S1 | Consolidamento via `dream_*` senza chiave API esterna | R05-13 Sprint 7 (direttiva Aurelio `d4dd857b1eea`) | **FATTO** | `verimem/dream.py` (908 righe); tool `hippo_dream_create_shadow/propose/submit_result/status/diff/adopt` | Il vincolo «solo subscription» regge da maggio |
| S2 | Cancelli dello Sprint 7: salute corpus ≥70 · promossi ≥10% · derivazione ≥0,5 | R05-13 exit criterion | **NON FATTO** | ultima misura trovata (09/06): **8 promossi su 326 = 2,5%**; nessuna misura più recente | Il cancello che doveva chiudere lo Sprint 7 non è mai stato riverificato |
| S3 | Capire e alzare il tasso di promozione delle skill | R06-09A P2.2 | **NON FATTO** | come sopra | |
| S4 | Daemon di sogno/consolidamento/GC cablati | R06-02P build_next #5 | **A METÀ** | `auto_dream_trigger.py`, `auto_dream_worker.py` esistono | doc 48: «ventitré minuti senza daemon hanno spento una promessa del README» |
| S5 | Consapevolezza: «so cosa so e cosa non so» (B1) | M0-05-11 §3 | **FATTO** | `hippo_assess_confidence`, `hippo_ignorance_map`, CLI `ignorance` | |
| S6 | Trasferimento fra domini (B3) | M0-05-11 §10 | **A METÀ** ⇐ *corretto da ws6* | ✅ **ws6**: non è «mai guardato» — esiste `verimem/schema_abstraction.py` con `find_cross_domain_schemas()` **e** `tests/test_schema_abstraction.py` (7 test, 127 righe, incluso `test_find_cross_domain_schemas`). ⚠️ **Ma non fa quello che il nome promette**: raggruppa i corpi delle skill per template condiviso, con bucket per *prima parola + numero di token* — è una firma **sintattica**, non un trasferimento semantico fra domini | Il meccanismo c'è ed è testato; la capacità che la roadmap chiedeva no. Era esplicitamente differito a M4+ |
| S7 | Il tier degli episodi vivo e usato | R05-27, R06-02P | **A METÀ** | 479 episodi, **ultima scrittura 31/08, ultimo accesso 29/08, 80% è di maggio** (doc 77) | Costruito, quasi non attraversato |

### A.7 — Continuità e uso reale della memoria

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| C1 | Handoff automatico al compact su file, non nel DB | R06-02P Fronte B | **FATTO** | hook pre-compact + session-start; anti-pollution verificato (delta DB = 0, `7123800`) | |
| C2 | Bonifica e recupero dei quarantinati, zero cancellazioni | R06-02P Fronte C, §9 | **FATTO** | 740 fatti veri recuperati (14/06); retro-cleanup 284 spostati / 7 saltati / 2347 contraddizioni orfane potate (20/07), backup `semantic-pre-retro-cleanup-2026-07-20.db` | Corpus curato 84,4% → 89,8% |
| C3 | Registro delle capacità interrogabile da un agente esterno | R06-02P backlog 05/06 (mandato Aurelio) | **A METÀ** | `verimem/agent_guide.py` + CLI `agent-guide` | L'idea (un agente non-Claude scopre, usa e si auto-vincola) è realizzata come guida, non come registro namespaced separato dai fatti |
| C4 | **Versionare invece di ritirare** (`SemanticMemory.supersede()`) | R08-16 2.1 (decisione del 05/08, `62c2a8610c99`) | **NON FATTO ma fattibile** ⚠️ | ✅ **ws6**: le **6 occorrenze di `version INTEGER`** stanno in `migrations/__init__.py:37`, `self_model.py:20/26/81/87`, `skill.py:135` — **nessuna nello schema `facts`**. Il ricercatore aveva ragione. `supersede()` (`semantic.py:5664`) resta un ritiro per campo. Il commit `c8aaa889` (02/09) è la **misura** del costo, non l'innesto: 0,21% di costo, +448 fatti (2,6 punti) — ws2 lo sta implementando dal 02/09 sera | 28 giorni dalla decisione, zero innesti fino a oggi. È l'esempio che il piano settembre cita come prova che «il sistema premia la diagnosi e non la cura» |
| C5 | Indice dei documenti come via per i fatti lunghi | R08-16 (implicito), doc 76 | **A METÀ** | `verimem index` + `search-docs` funzionano (22 chunk, citazione al byte) — ma `documents.db` **non esiste** nello store, pur essendo la via raccomandata per iscritto | La capacità c'è, la nostra stessa memoria la raccomanda, e nessuno l'ha mai percorsa |

### A.8 — Vetrina e onestà pubblica

| ID | Voce | Roadmap | STATO | Evidenza | Livello attuale |
|---|---|---|---|---|---|
| V1 | Ogni numero pubblico porta il righello e il comando che lo riproduce | R08-16 1.2 / W5 | **A METÀ** | doc 72 «il numero perde le sue condizioni fra il changelog e la vetrina»; doc 68 «il numero pubblico non si riproduce»; caso 166–237 ms vs 3,478 ms aperto dal 16/08 | Il criterio è scritto, l'audit completo non è chiuso |
| V2 | Togliere «100% certain / verified» e pubblicare la banda d'errore | R07-18 §0.6 | **FATTO** | README pubblicato dichiara i propri default (11 env censite, zero capacità nascoste — LANT-127); AUROC riportato con l'avvertenza che un `0.974` non ha artefatto committato | Il primo numero della vetrina è a nostro sfavore ed è scritto lo stesso |
| V3 | Le 4 promesse del Summary del pacchetto reggono | R08-16 (verifica 31/08) | **A METÀ** | `gated writes` 🟢 (3 porte, LANT-33) · `provenance on every read` 🟡 (3 porte su 4) · `bi-temporal history` 🔴 (una dimensione mai popolata, LANT-133) · `abstention` 🔴 (non su `search`, LANT-131) | Una regge piena, una con eccezione, due no |
| V4 | Sito in 9 lingue non superficiale | R07-22 D13 | **A METÀ** | `docs/site-update/` con `PATCH-HOMEPAGE.md`, `llms.txt`, `sitemap.xml`, `faq-jsonld.html` | Il sito pubblicato non è stato verificato |
| V5 | CodeQL verde | R07-22 D13 | **A METÀ** (corretto dal lead 02/09 20:10) | Il job ESISTE: `.github/workflows/security.yml` job `codeql` (init/autobuild/analyze con `config-file: ./.github/codeql/codeql-config.yml`, su push/PR a main + settimanale); ultima analisi 02/09 17:41Z, **462 risultati**; **404 alert aperti**: 180 `py/empty-except`, 51 `py/implicit-string-concatenation-in-list`, 37 `py/cyclic-import`, 26 `py/file-not-closed`, 23+23 unused import/global, 12 `py/path-injection`, 8 `py/polynomial-redos`; per severità 291 note · 91 warning · 20 high · 2 medium; per cartella **252 in `verimem/`, 152 in `docs/`** | Non «il job no»: **il job c'è e non è verde**. 152 alert (37,6%) sono su banchi Python in `docs/` che non spediscono: aggiunto `docs` a `paths-ignore` (02/09). I 180 `empty-except` sono la voce Q9. I 12 `path-injection` su `ide.py` hanno la rationale scritta nella config e vanno dismessi via API, non ignorati |
| V6 | I 4 punti del preprint (dispersione, `Source:`, concessione §5.2, prezzo del TCE) | R08-16 1.3 | **non verificato** | evidenza non trovata nel repo | |
| V7 | Il lettore ostile esterno | R08-16 3.5 | **FATTO (primo giro)** | GLM-5.3, 24 finding sul solo testo del report (30/08), 8 convertiti in correzioni — fra cui LANT-105, la firma dichiarata e mai scritta | Il gesto finale previsto (un'istanza che scrive «perché verimem non regge» usando solo superfici pubbliche) non risulta eseguito |

---

## B · CONTEGGI

**113 voci deduplicate.**

| STATO | n. | % |
|---|---|---|
| **FATTO** | 49 | 43% |
| **A METÀ** | 33 | 29% |
| **NON FATTO ma fattibile** | 17 | 15% |
| **ABBANDONATO / IRREALIZZABILE** | 5 | 4% |
| **MAI GUARDATO** | 6 | 5% | ⇐ *era 7: `S6` corretta da ws6 in A METÀ*
| **non verificabile da qui** | 2 | 2% |

**Le 5 abbandonate, col perché:**
- **A2** superficie MCP a 20 tool — *dedotto*: nessuna decisione scritta, la superficie è cresciuta 12× e nessuno l'ha mai potata.
- **G14** ammissione graduata — *dichiarato e misurato*: falsità ammesse 13,3%→98,7%.
- **R5** mean-centering — *dichiarato*: refutato a n=300, p=0,0003 (attribuzione del commit da rileggere).
- **R6** MMR/diversify — *dichiarato*: parere avversariale convergente 2/2, selection on the dependent variable, zero dati sul danno collaterale.
- **A9** Postgres — *dichiarato condizionale*: «solo se il bench 50k mostra che SQLite non regge», condizione mai verificata → non è un abbandono per fallimento, è un rinvio motivato.

**Le 7 mai guardate:** G20 (anti-trigger + banco FSM ΔF1≥15pp — con la riserva del commit trovato dal lead), A8 (atomicità storage skill), Q7 (portachiavi OS), Q14 (eseguibile Windows), Q17 (ADR), S6 (transfer cross-domain), + **A29** (audit ingestione, contato come NON FATTO perché è a registro come task #49 e quindi guardato).

### Per roadmap — introdotte / ereditate

| roadmap | voci introdotte | voci ereditate (ripetute da prima) |
|---|---|---|
| M0-05-11 | 5 (A1, A2, G20, S5, S6) | 0 |
| R05-12 / R05-13 | 27 (A3-A8, A10 parziale, Q1-Q21) | 0 |
| R05-19 | 3 (B1, B2, B7) | 1 |
| R05-27 | 13 (A10-A20, A15, A16) | 4 |
| R06-02L | 3 (G3, G4, G5) | 3 |
| R06-02P | 8 (R1, R4, C1, C2, C3, A5, S4, B4) | 21 |
| R06-06E | 8 (A21-A26, A30, A31) | 6 |
| R06-09A | 6 (R2, R3, R5, R9, S3, B3) | 8 |
| R07-18 | 13 (G6-G11, G15, G18, G19, R7, A27, A28, A25) | 12 |
| R07-22 | 6 (R6, B5, B8, B10, R8, A29) | 24 |
| R08-16 | 6 (G16, G17, C4, V1, V3, V7) | 22 |

**La forma della curva**: le prime due roadmap introducono 32 voci di *piattaforma* (architettura, packaging, documentazione, qualità del codice) di cui oggi ne reggono 14. Le ultime tre introducono 25 voci di *prova* (banchi, ricevute, numeri pubblici) di cui ne reggono 17. Il prodotto ha smesso di costruire piattaforma e ha iniziato a costruire evidenza — che è la scelta giusta per la tesi, ma spiega perché A4, A6, A18, A20, Q9, Q17, Q18 sono ferme da maggio.

---

## C · LE PIÙ PROMESSE — le 15 voci che ricorrono in più roadmap

| # | voce | n. roadmap | STATO |
|---|---|---|---|
| 1 | **G1** gate anti-confabulazione lessicale | 7 | FATTO (ed è il difetto centrale) |
| 2 | **G2** moat entailment source⊢fact | 5 | **FATTO** — è la cosa che ci distingue |
| 3 | **B2** LongMemEval | 5 | FATTO (0,8745) |
| 4 | **A21** multi-tenant | 4 | FATTO |
| 5 | **B4** confronto affiancato coi competitor | 4 | A METÀ (mem0 sì, zep/letta no) |
| 6 | **G12** L1 da veto ad avviso | 4 | FATTO |
| 7 | **B1** HaluMem | 4 | FATTO (F1 0,761) |
| 8 | **Q16** pubblicazione su PyPI | 4 | **FATTO il 02/09** |
| 9 | **G11** contraddizione sul write path | 4 | FATTO |
| 10 | **R10** astensione invece di allucinazione | 4 | A METÀ (spenta di default sulla porta MCP) |
| 11 | **A2** ridurre la superficie MCP | 3 | ABBANDONATO (251 tool) |
| 12 | **G9** ricevute legate al contenuto | 3 | A METÀ |
| 13 | **A25** GDPR (cancellazione + export) | 3 | A METÀ |
| 14 | **A22** cifratura a riposo + chiavi del cliente | 3 | **NON FATTO** |
| 15 | **A23** SSO + RBAC | 2 (ma è table-stakes in 3 doc) | **NON FATTO** |

**La lettura**: le promesse più ripetute che riguardano il *moat* sono quasi tutte mantenute. Le promesse più ripetute che riguardano l'*ingresso in azienda* (A22, A23, A24, A18) non sono mai state iniziate — e sono le uniche quattro voci con questo pattern.

---

## D · LE VOCI CHE I DOCUMENTI ATTRIBUISCONO ESPLICITAMENTE AD AURELIO

| voce | dove | citazione | STATO |
|---|---|---|---|
| **Solo subscription Claude Code, zero chiave API esterna** | R05-13 Sprint 7 (fact `d4dd857b1eea`), R05-27 vincoli HARD | «HippoAgent deve usare la subscription Claude Code come base sempre e comunque» | **FATTO e mantenuto** — `ENGRAM_MODE=subscription`, moat su CE locale senza LLM |
| **Zero cancellazioni sulla memoria — solo ri-classificazione reversibile** | R06-02P §9 | «Tieni quello che serve, non incasinare peggio eliminando cose che servono» + campione prima di ogni bulk | **FATTO** — 740 recuperati, backup + restore-map ogni volta |
| **Niente marketing, niente fuffa** | R06-02L, R05-27, R06-02P | «ZERO fuffa: niente doc marketing/pitch/whitepaper» | **FATTO** — `docs/proposal/` rimosso (`fb0d5e2`, 12 file) |
| **Livello produzione e vendibile alle aziende** | R06-06E | «lavoriamo lenti e costanti sempre» | **A METÀ** — self-host sì (Docker, gateway, piani); il review aziendale no (A22/A23/A24) |
| **Serve anche il modo LOCALE sovrano, zero egress** | R06-06E B6 | «terzo modo, non dettaglio» | **FATTO** — `airgap.py` + prova no-egress |
| **Istanze reali, non subagenti, per la ricerca** | R06-02L, memoria feedback | «Aurelio lo VIETA per ricerca» | rispettato nei loop di giugno; il 02/09 ridiscusso: subagent solo in lettura, dichiarati prima, con spot-check del lead |
| **Ridurre i falsi positivi del write-gate a una soglia accettabile** | R07-18 (21/07) | «verimem funziona sotto ogni punto di vista» | **FATTO su L1** (86,7%→0,0% verticale); **aperto sul complesso**: ~1 fatto vivo su 5 non ripasserebbe la porta di oggi (18,4%, W7-89) |
| **«Macchina appena uscita dal concessionario»** | R08-16 operazione-concessionario | «ogni santissima riga di codice maniacalmente funzionante» | **A METÀ** — W1 (CI) ✔, W2/W4/W7 (ambiente pulito, artefatto, release) ✔; W3 (ogni tool MCP esercitato), W5 (vetrina), W6 (sensori scollegati) non chiusi |
| **Il test dei tre no del 05/09** (non dice cose che non fa · non siamo bugiardi · non è banale) | R08-16 | criterio di accettazione di Aurelio | «bugiardi» chiuso in gran parte (righelli e correzioni dentro il registro) · «cose che non fa» **aperto** (2 promesse su 4 del Summary non reggono; e il moat parte spento sul pacchetto servito) · «banale» chiuso dal C10 e dal censimento 0/13 |
| **«Prendi tu le redini, non chiedere niente a me»** | 02/09 12:30 | mandato esplicito che ha sbloccato il tag | **eseguito** — v0.7.1 pubblicata lo stesso giorno |
| **Yank della 0.7.0 da PyPI** | R08-16 / quadro-versione ③ | resta ad Aurelio (credenziali web PyPI) | **APERTO — è di Aurelio** |

---

## E · IL LIVELLO ATTUALE IN DIECI RIGHE
*(dalle fonti di stato, non dai piani)*

1. **La 0.7.1 è su PyPI dal 02/09** (tag `v0.7.1` su `1e293f4b`, run ci 2716 verde 9/9, publish `33620334721`), e uno sconosciuto che fa `pip install verimem` in un ambiente vergine ottiene un pacchetto che importa, scrive, legge e apre la porta MCP — smoke verificato su WSL Ubuntu 24.04 e su Windows (ws5, ws8).
2. **Il gate a più strati è acceso di default**: L1 lessicale con carve-out di dominio, screen delle iniezioni, L3 con pre-filtro del soggetto, e sopra tutti il **moat** che confronta il fatto con la sua fonte — con copertura **98,1%** ad agosto quando la fonte c'è (9587/9768) e **59,6%** sul corpus intero, perché i mesi pre-moat non sono giudicati. **Ma sul pacchetto servito il giudice va scaricato a mano (`verimem warmup`): finché non lo si fa, il moat è spento** (tre smoke indipendenti, 02/09).
3. **Il numero che vale**: su ground truth umana esterna (TruthfulQA heldout, n=600), di ciò che verimem serve è falso il **15,9%** contro il **50,0%** dello stesso corpus senza gate. Prezzo dichiarato: veri persi **29,3%** [24,5–34,7] — e l'83,6% di quei veri persi ha punteggio del giudice sotto 5 (ws4, 02/09): non si recuperano con la soglia.
4. **Nessuno dei 13 prodotti concorrenti censiti il 02/09 fa un gate di entailment al write** — mem0, Zep/Graphiti, Letta, LangMem, MemOS, Cognee, Hindsight, Supermemory: tutti ❌ su quella colonna. Esiste solo in tre paper da maggio 2026.
5. **Sul retrieval siamo nel gruppo, non in testa**: LongMemEval recall@5 **0,8745**, LoCoMo **0,8267**, HaluMem-extraction F1 **0,761** — contro leader auto-dichiarati a 88-93 con harness loro.
6. **Ogni scrittura torna una ricevuta** con verdetto, classe di evidenza, giudice, punteggio, soglia e margine; ogni rifiuto dice ora chi l'ha fermato (`quarantined_by`); la prova del passaggio (`grounding_span`) è allegata al **99,7%** dei giudicati.
7. **L'audit è concatenato e firmato**: catena hash su mutazioni e aggiudicazioni, più una ricevuta ed25519 che copre le teste di entrambe le catene con i conteggi — che rileva anche la riscrittura completa e il troncamento della coda.
8. **La piattaforma self-host c'è**: gateway REST multi-tenant con un DB per tenant, chiavi API hashate, piani e quote, backup, Docker headless, modo air-gap con prova no-egress. **Non c'è** cifratura a riposo, SSO, RBAC, né OpenTelemetry.
9. **Il difetto centrale è misurato e non curato**: la famiglia L1 decide con le parole e sbaglia nei due versi; **~1 fatto vivo su 5 non ripasserebbe la porta di oggi** (18,4% su 228 fatti appaiati); e nessuna cura di un lato solo libera la coda — 5/88 li boccia solo il moat, 15/88 solo un layer, **68/88 entrambi**.
10. **La classe di difetto più grande non è un bug**: sei capacità pronte che nessun uso reale esercita (indice documenti, tier episodi, `withheld_despite_judge`, `worked_example` 1/17098, `derives_from` 1/17098, `digest`), **11 interruttori a default OFF e nessuno acceso**, e `valid_until` popolato su **0 fatti**. Il prodotto sa fare cose che non fa, e nulla segnala che non le sta facendo.

---

## F · NOTE DI ONESTÀ (dell'archivista, integrate dal lead)

**Cosa non è stato verificato** (sette voci):
- Il **sito verimem.com** e il preprint pubblicato: letti solo `docs/site-update/` e i draft nel repo (V4, V6).
- Se la **dashboard operatore** abbia davvero il pane real-time delle chiamate colorate per rischio (A17): visti i moduli SSE, non il comportamento.
- Se l'**anchor esterno periodico** (TSA / transparency log) sia attivo nel nostro deployment (A28): letto solo il codice della firma.
- **Non è stata eseguita la suite** (1556 file di test) né alcun benchmark: vincolo operativo dichiarato — Aurelio usa il PC. Ogni «FATTO» poggia su file, commit o misure già registrate, mai su un run dell'archivista.
- Il **tasso di promozione delle skill** (S2/S3): l'ultima misura trovata è del 09/06 (8/326 = 2,5%). Il cancello dello Sprint 7 è NON FATTO per assenza di misura, non per misura negativa.
- **A29** (audit del path di ingestione, task #49): a registro come debito, evidenza di chiusura non trovata.
- Il **conteggio dei tool MCP**: 251 è il numero di occorrenze `Tool(` in `mcp_server.py` (confermato dal lead), non un'enumerazione a runtime del server. Coerente con i 245 dichiarati nel CHANGELOG 0.7.5.

**Dove i documenti si contraddicono:**
1. **La versione, tre volte diversa nello stesso momento**: `pyproject.toml` su main dichiara **0.7.6**; il CHANGELOG ha una voce **[0.7.5] - 2026-08-09** che dice testualmente «*0.7.1 through 0.7.4 were never published*»; PyPI serve **0.7.1**, pubblicata il 02/09 come hotfix ramificato da `v0.7.0`. Tre numeri, tre verità parziali, e nessun documento le riconcilia. Il test `test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice` è rosso proprio per questo, ed è un deadlock dichiarato: il presidio che chiede di rilasciare blocca il rilascio.
2. **STATE.md si dichiara la fonte unica ed è congelato al 04/07** — l'audit del 07/08 lo marca «FROZEN ARCHIVE… un *single source of truth* vecchio di 34 giorni è una trappola, non una fonte». Chi lo apre oggi legge numeri di luglio come se fossero attuali.
3. **La latenza di lettura**: il sito dichiara 166–237 ms, la misura in-process del 16/08 dà **p50 warm 3,478 ms**. Il piano settembre dice esplicitamente che «si risolve in uno dei due sensi, non si lascia» — al 02/09 è ancora aperto.
4. **Il «33% di clean-rejection» del gate** attribuito al default in R07-18 è stato corretto la stessa notte: valeva per la configurazione col giudice LLM, non per il CE che il prodotto usa di default (che fa 97–100%). La roadmap porta dentro sia il claim sbagliato sia la sua correzione, in due sezioni successive.
5. **Il flip embedding «R@10 0,32→0,80»** era già dichiarato inconsistente col baseline 0,84 nel piano d'attacco del 09/06 e mai riconciliato; il modello era già stato cambiato il 04/06 e chi scriveva il piano non lo sapeva.
6. **R05-12 e R05-13 sono lo stesso documento** — il secondo è il primo più lo Sprint 7. Contati come una roadmap sola per le voci ereditate.

**Voci scartate come non-memoria: 41.** Estratte e messe da parte, non contate nella tabella:
- **EngramOS** (`ENGRAMOS_ROADMAP.md`, 26/05) — 9 voci: una distro Linux con login account Claude, window manager, launcher a voce. Unico aggancio memoria: «memory daemon in avvio» e «Engram recall nella barra».
- **syn / Singularity** (`SYN-BACKLOG-2026-05-31`, `clp/docs/SYN-ROADMAP`, `ROADMAP-SYN`, `SYN-FEATURE-ROADMAP`) — 21 voci: una CLI agentica di coding multi-provider. Le tre voci con aggancio memoria («semantic recall: embedding scritti ma mai letti», «stale-recall: un recall low-confidence conta come grounding pieno», «memoria durevole auto-derivata dalle conversazioni») sono di syn, non di verimem.
- **AgentOS** (`AGENTOS-FOUNDATION-PLAN`, `AGENTOS-HARDENING-PLAN`, 11/06) — 6 voci: lo strato di automazione desktop. Zero voci di memoria.
- **ops-plan / VeriAgent** (`00-PIANO-INDUSTRIALE`, `01-VISION`, 18/07) — 5 voci: una CLI agentica in Rust dove **verimem è la dipendenza esterna ammessa** (D6) e il pilastro P1. È il progetto che *consuma* la memoria. Nome mai deciso (A1 aperta), licenza mai decisa (A2 aperta), M0 mai iniziato.
- **PLAN-2027** (23/06): syn come agente autonomo per giorni. La memoria compare come asset già posseduto, non come voce da fare.

**Un'ultima cosa che il conteggio non dice.** Le 33 voci «A METÀ» non sono tutte uguali. Almeno **nove** di esse sono della stessa forma, e non è la forma di un lavoro incompiuto: G5, G10, R2, R10, A15, S4, S7, C5 e V5 sono *costruite, testate, e spente o non attraversate*. È esattamente la classe che ws6 ha nominato il 30/08 — «il prodotto possiede la capacità, la implementa correttamente, la misura anche, e poi non la usa; e nulla segnala che non la sta usando». Se si cerca la leva col rapporto migliore fra costo e risultato in questa tabella, non è fra le 17 «NON FATTO»: è accendere e misurare quelle nove.
