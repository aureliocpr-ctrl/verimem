# Entity-centric Memory for LLM Agents — State of the Art (2026-05-14)

> Documento di ricerca esplorativa, paper-first. NO codice. Obiettivo: capire
> dove sta davvero HippoAgent/Engram nel panorama prima di decidere il
> prossimo investimento.
>
> Tutte le citazioni sono verificate via WebSearch+WebFetch in data 2026-05-14.
> Le correzioni alla memoria interna di Claude sono marcate ⚠.

## 0. Cosa stiamo cercando

Aurelio ha proposto un "knowledge graph stratificato entity-centric" con
metafora "quando dico ciao Marco hai visto Filippo, Marco sblocca tutto
su Filippo a cascata". L'intuizione è che HippoAgent oggi fa retrieval
**query-centric** (cosine flat sul testo), ma per recuperare in modo
naturale serve retrieval **entity-centric** (l'entità menzionata espande
i suoi attributi + relazioni).

Prima di scrivere una riga di codice, ricerca onesta: cosa esiste già?
Cosa funziona davvero? Dove sta HippoAgent rispetto al resto?

## 1. Paper di riferimento (verificati)

### 1.1 HippoRAG — la pietra di paragone diretta
- **Paper**: *HippoRAG: Neurobiologically Inspired Long-Term Memory for
  LLMs*, Gutiérrez et al., **NeurIPS 2024**, arXiv:2405.14831.
- **Origine**: OSU-NLP-Group (Ohio State).
- **Stelle GitHub**: 3.5k. Ultima release: Feb 27, 2025.
- **Meccanica esatta**:
  - **OpenIE schemaless** (NO schema fissato) in 2 step: estrai named
    entities, poi triple noun-phrase guidate dalle entità.
  - **Synonymy edges**: aggiungi edge tra nodi con cosine ≥ τ=0.8 sui
    loro embedding densi.
  - **Personalized PageRank** con damping=0.5, seed = query nodes
    (probabilità uniforme), node specificity locale s_i = |P_i|^(-1).
- **Benchmark**:
  | Dataset | HippoRAG R@5 | ColBERTv2 R@5 | Δ |
  |---|---|---|---|
  | MuSiQue | 51.9% | 49.2% | +2.7 |
  | 2WikiMultiHopQA | 89.1% | 68.2% | **+20.9** |
  | HotpotQA | 77.7% | 79.3% | **−1.6** |
- **Limiti dichiarati dagli autori**:
  - Errori dominanti da NER+OpenIE imperfetta — beneficerebbe da
    fine-tuning diretto.
  - Scalabilità oltre 1k passaggi non empiricamente provata.
  - Senza PPR il sistema collassa (-25 a -33 punti R@5) ⇒ il valore è
    nell'algoritmo di walk, non nel graph.
- **Critique esterna** (graphwise.ai, emergentmind):
  - Co-occurrence + similarity ≠ ontology vera; il graph è "noisy
    highway" finché manca una rule-book.
  - HippoRAG 2 (paper successor arXiv:2502.14802 *From RAG to Memory*)
    aggiunge "triple filtering" perché l'estrazione vanilla sbaglia
    troppo.

**Lettura per Engram**: HippoRAG è **letteralmente la stessa metafora
cognitiva** che dà il nome a Engram. Più maturo, più valutato, più
adottato. Engram così com'è (cosine flat, niente PPR, niente entità
esplicite) è una versione povera della stessa idea.

### 1.2 GraphRAG (Microsoft) — il filone "global summarization"
- **Paper**: *From Local to Global: A Graph RAG Approach to
  Query-Focused Summarization*, Edge et al., aprile 2024,
  arXiv:2404.16130.
- **Approccio**: LLM estrae entity KG dal corpus, calcola community
  summaries gerarchici (Leiden clustering), risponde a query "globali"
  (es. *quali sono i temi principali?*) aggregando community summaries.
- **Numeri**: 72–83% comprehensiveness, 62–82% diversity vs RAG
  baseline, 97% fewer tokens per root-level summary.
- **Lettura per Engram**: GraphRAG risolve un problema diverso —
  sense-making globale su corpus grandi. Non è il caso d'uso di
  HippoAgent (memoria personale di sessioni, multi-hop). Da NON
  scimmiottare.

### 1.3 LightRAG — dual-level retrieval (entity + global)
- **Paper**: *LightRAG: Simple and Fast Retrieval-Augmented Generation*,
  Guo et al., arXiv:2410.05779.
- **Origine**: ⚠ **HKUDS (HKU Data Science)**, NON HKUST come avevo in
  memoria.
- **Stelle GitHub**: **35.2k** (più popolare di HippoRAG di 10×).
  Release v1.4.16 a maggio 2026.
- **Architettura**: dual-level retrieval — *low-level* (specific
  entity/relation) + *high-level* (broader topic). Backends Neo4J,
  PostgreSQL, MongoDB, OpenSearch. Embedding raccomandato `BAAI/bge-m3`.
- **Lettura per Engram**: dual-level è esattamente il
  pattern Marco/Filippo. Quando Aurelio dice "Filippo" puoi recuperare
  L1 (sue entità correlate) e/o L2 (topic generali in cui appare).
  LightRAG ha già implementato esattamente questo.

### 1.4 AriGraph — episodic + semantic in un unico graph
- **Paper**: *AriGraph: Learning Knowledge Graph World Models with
  Episodic Memory for LLM Agents*, Anokhin et al., AIRI Institute,
  arXiv:2407.04363.
- **Approccio**: il graph ha **due tipi di vertici** — semantici
  (entità/concetti astratti) ed **episodici** (eventi temporali
  specifici). Edge episodici collegano episodi alle entità menzionate.
  Costruito ground-up esplorando l'ambiente.
- **Validato su**: TextWorld (text-based games).
- **Lettura per Engram**: questo è il pattern **più simile** alla
  struttura dual di Engram (episodes table + facts table). Engram ha
  già il dualismo ma manca il GRAPH che li collega via entità. AriGraph
  fa esattamente la connessione che a Engram manca.

### 1.5 MemGPT / Letta — memory as OS
- **Paper**: *MemGPT: Towards LLMs as Operating Systems*, Packer et al.,
  arXiv:2310.08560 (ottobre 2023, ultimo update feb 2024).
- **Architettura 3 tier**: main context (in-prompt) / recall storage
  (conversation history searchable) / archival storage (vector or graph
  DB long-term).
- **Letta**: framework che eredita MemGPT come pattern, settembre 2024.
- **Lettura per Engram**: il **sleep cycle** + Dream pipeline di Engram
  è concettualmente vicino a "OS-managed memory" — il consolidator è
  ciò che MemGPT chiama "page out from recall to archival". Engram qui
  è ALLINEATO al state-of-art, anche se non lo abbiamo mai dichiarato
  in questi termini.

## 2. Sistemi open-source in produzione (verificati)

| Sistema | Stelle GH | LOCOMO/LongMemEval | Differenziatore |
|---|---|---|---|
| **Mem0** | ~37k (lug 2025) | 66.9% LOCOMO (Mem0); paper rivendica 91.6 su versione recente | flat vector + summary, MCP server `OpenMemory` |
| **LightRAG** | 35.2k | n/d ufficiale | dual-level entity+global, multi-backend |
| **Cognee** | 17.2k, 7170 commit, attivo MAY 2026 | n/d | 4-step pipeline Add→Cognify→Memify→Search, ontology pluggable |
| **HippoRAG** | 3.5k | NeurIPS'24 R@5 su MuSiQue/2Wiki/HotpotQA | PPR su KG ispirato hippocampus |
| **Zep / Graphiti** | n/d (commercial-leaning) | 71.2% LongMemEval (claim Zep team rebuts 75% LOCOMO) | temporal KG, time-anchoring |
| **OMEGA** | n/d | 95.4% LongMemEval (claim) | ? — da verificare |
| **Mastra** | n/d | 94.87% LongMemEval (claim) | ? — da verificare |
| **Engram (HippoAgent)** | **0 stelle pubbliche** | **mai valutato su LOCOMO/LongMemEval** | sleep cycle + self_model + critic-orchestrator + MCP-native |

**Benchmark standard**: **LOCOMO** (Maharana et al., ACL 2024,
arXiv:2402.17753) — 300 turns × 9k token × 35 sessioni × 5 categorie
(single-hop, multi-hop, open-domain, temporal). Lo usano tutti. Engram
non è mai stato benchmarkato lì.

## 3. CLI vs MCP — stato del dibattito

### 3.1 La tesi "MCP context bloat"
- **Milvus blog "Is MCP Dead?"** (URL: `milvus.io/blog/is-mcp-dead-cli-and-skills-for-ai-agents.md`)
  — 3 server MCP su modello 200k context consumano **>70%** del budget
  prima che l'agent agisca. CLI+Skills riducono drasticamente.
- ⚠ **Anthropic Skills**: release **ottobre 2025** (NON 2026 come avevo
  in memoria). Open standard pubblicato **18 dicembre 2025** su
  agentskills.io.
- **Pattern Skill**: cartella con `SKILL.md` (YAML frontmatter +
  istruzioni), progressive disclosure — pochi token nel context base,
  full content caricato on-demand.

### 3.2 Il contro-argomento (Charles Chen, chrlschn.dev, mar 2026)
- CLI personalizzati hanno LO STESSO problema MCP: serve documentazione.
- Senza schema upfront, accuratezza CALA (Vercel data).
- **MCP over streamable HTTP** (non stdio) sblocca observability,
  auth centralizzato, OpenTelemetry, dynamic resources.
- **Verdetto**: MCP per enterprise/team, CLI+Skills per solo dev. Né
  dead né winner-takes-all.

### 3.3 Lettura per Engram
La memoria di Engram contiene già 14 fact dettagliati su "CLI-refactor
design": architettura ibrida tripla (core + MCP hot + CLI full),
vincolo subscription, matrice provider. **Questo perimetro è
allineato al SOA**. La decisione è solo se eseguirlo o no.

## 4. NER italiano per entity registry (verificato)

- **WikiNEuRal** (Tedeschi et al., Findings EMNLP 2021, Sapienza
  Babelscape): dataset multilingua + modello `Babelscape/wikineural-multilingual-ner`
  su Hugging Face. mBERT 0.2B params, 9 lingue (it inclusa), 1.03M
  esempi. F1 specifico per italiano **non recuperato da search** —
  va misurato direttamente.
- **spaCy `it_core_news_lg/sm/md`**: WikiNER come training set. Numeri
  ufficiali su `spacy.io/models/it` ma scoreboard non caricata.
- **tint** (UniTN/FBK): toolkit italiano consolidato. Da valutare.
- ⚠ **Limite onesto**: F1 effettivo su entità custom (es. "Nexus",
  "HippoAgent", "Aurelio") sarà sotto-ottimale per QUALSIASI modello
  pre-trained — nessuno conosce questi nomi. Serve **gazetteer locale**
  (lista manuale) per il caso d'uso reale di Engram, NER come
  fallback per testo libero generico.

## 5. Fondamenti neuroscientifici (verificati + correzioni)

- **Tulving 1972** *Episodic and Semantic Memory*. Distinzione
  fondante che Engram USA implicitamente (episodes table vs facts
  table). Citato >500 volte entro 1983. ✓ Solido.
- **Marr 1971** *Simple memory: a theory for archicortex*. Foundational
  per il modello sparse-coding dell'hippocampus. ✓ Solido.
- **McClelland, McNaughton, O'Reilly 1995** *Why there are
  Complementary Learning Systems in the hippocampus and neocortex*.
  **QUESTO È il modello teorico del sleep cycle di Engram**: hippocampus
  = sparse pattern-separated rapid encoding; neocortex = distributed
  slow integration. **Engram dovrebbe citarlo come modello di
  riferimento esplicito**. ✓ Solido.
- **Tonegawa engram cells**: paper 2012 Nature ("Optogenetic stimulation
  of a hippocampal engram", Liu et al.); 2013 Science ("Creating a
  false memory"); 2014 Nature (Redondo et al. bidirectional switch).
  ⚠ **CORREZIONE CRITICA**: il **Premio Nobel di Tonegawa è 1987**, per
  **diversità genetica anticorpi (immunologia)**, NON per gli engram.
  Il mio fact in memoria su "Tonegawa 2014 Nobel" era confabulazione
  mascherata da neuroscienza. Da correggere.

## 6. Posizione spietata di Engram nel panorama (2026-05-14)

### 6.1 Cosa Engram NON è
- Non è state-of-the-art accademico: zero validation su LOCOMO o
  LongMemEval, mentre Mem0/Zep/OMEGA si misurano lì.
- Non è entity-centric: cosine similarity flat, nessun KG explicit,
  nessun PPR/walk algorithm. HippoRAG/LightRAG/Cognee fanno tutti
  l'entity-level che a Engram manca.
- Non è adottato: 0 stars pubbliche vs 35k LightRAG, 37k Mem0, 17k
  Cognee, 3.5k HippoRAG. È un sistema **privato** di Aurelio.

### 6.2 Cosa Engram È, davvero, di unico
- **Sleep cycle + Dream pipeline** esplicito ispirato a CLS
  (McClelland 1995) — più "neuroscientificamente coerente" di quello
  che fa Mem0 (che è essenzialmente vector + summary).
- **self_model continuity layer** (cycle #67-68) — nessuno degli altri
  ha un modello esplicito di "stato dell'agent stesso" che sopravvive
  alle sessioni.
- **critic-orchestrator integration** (cycle #69) — adversarial review
  prima del commit. Pattern unico.
- **MCP-native** — gli altri sono SDK/library da integrare. Engram
  parte come tool MCP, quindi "just works" dentro Claude Code.
- **Subscription-only path** — Aurelio vincolo: niente API key. Tutti
  gli altri assumono ANTHROPIC_API_KEY/OPENAI_API_KEY. Pattern di
  nicchia ma onesto.
- **Italiano nativo** — gli altri sono multilingua ma non ottimizzati
  per IT (recall@1 IT in Engram benchmarkato).

### 6.3 Il gap concreto (la proposta di Aurelio)
La metafora "Marco sblocca Filippo" è una richiesta di:
1. **Estrarre entità** dai testi (NER + gazetteer).
2. **Tenere un'entity table** persistente (registry).
3. **Camminare il graph** quando l'entità è menzionata (lateral
   expansion).
4. **Synthesis pass** per ricomporre la risposta (LLM su contesto
   espanso).

Tutto questo è **esattamente cosa fa HippoRAG/AriGraph/LightRAG**. La
proposta NON è una novità di Aurelio nel mondo — è la **convergenza**
necessaria di Engram al state-of-the-art.

## 7. Tre opzioni concrete per il prossimo cycle

### Opzione A — Adottare HippoRAG dentro Engram
- Copiare l'algoritmo OpenIE+synonymy+PPR su episodes+facts esistenti.
- Aggiungere `entities` table con `(id, name, aliases[], type)`.
- Mantenere sleep cycle e self_model (differenziatori unici).
- **Costo**: 4-6 cycle TDD strict. PPR su SQLite via NetworkX.
- **Rischio**: reinventare quando esiste già una libreria (HippoRAG
  open source AGPL).

### Opzione B — Wrappare HippoRAG o LightRAG
- Aggiungere LightRAG come backend opzionale (`HIPPO_RAG_BACKEND=lightrag`).
- Engram resta orchestratore (sleep cycle + self_model + MCP), delega
  retrieval a una libreria mature.
- **Costo**: 2-3 cycle. Dependency add + adapter.
- **Rischio**: dipendenza esterna pesante, possibile conflict con
  vincolo subscription-only.

### Opzione C — Differenziarsi: doppia memoria + benchmark
- NON inseguire HippoRAG/LightRAG. Investire su:
  1. Validare Engram su **LOCOMO** (anche se score basso) — dare
     credibilità.
  2. Italian-first NER + gazetteer hand-curated.
  3. Open-source release pubblico aureliocpr-ctrl/hippoagent con
     README, demo, paper bianco di 4 pagine.
- **Costo**: 5-7 cycle. Più lavoro di adoption che di codice.
- **Rischio**: senza KG entity-level Engram resta indietro sui task
  multi-hop; la differenziazione "sleep cycle italiano" potrebbe non
  bastare per attrarre community.

## 8. Domanda da decidere PRIMA del prossimo codice

> Engram vuole essere **convergenza al SOA** (Opzione A o B), o
> **divergenza differenziata** (Opzione C)?

Onestamente: senza una risposta a questa, l'implementazione del
"knowledge graph stratificato" rischia di essere o (i) una copia
povera di HippoRAG, o (ii) un differenziatore senza utenti.

## 9. Riferimenti (verificabili)

- [HippoRAG paper](https://arxiv.org/abs/2405.14831) — Gutiérrez et al., NeurIPS'24
- [HippoRAG repo](https://github.com/OSU-NLP-Group/HippoRAG) — 3.5k ⭐
- [GraphRAG paper](https://arxiv.org/abs/2404.16130) — Edge et al., Microsoft
- [LightRAG paper](https://arxiv.org/abs/2410.05779) — Guo et al., HKUDS
- [LightRAG repo](https://github.com/HKUDS/LightRAG) — 35.2k ⭐
- [AriGraph paper](https://arxiv.org/abs/2407.04363) — Anokhin et al., AIRI
- [Cognee repo](https://github.com/topoteretes/cognee) — 17.2k ⭐
- [MemGPT paper](https://arxiv.org/abs/2310.08560) — Packer et al.
- [LOCOMO paper](https://arxiv.org/abs/2402.17753) — Maharana et al., ACL'24
- [Mem0 LOCOMO claims](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Milvus "Is MCP Dead?"](https://milvus.io/blog/is-mcp-dead-cli-and-skills-for-ai-agents.md)
- [Anthropic Agent Skills (Engineering blog)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Anthropic Skills GitHub repo](https://github.com/anthropics/skills)
- [chrlschn "MCP is Dead; Long Live MCP"](https://chrlschn.dev/blog/2026/03/mcp-is-dead-long-live-mcp/)
- [WikiNEuRal paper](https://aclanthology.org/2021.findings-emnlp.215/) — Tedeschi et al., EMNLP 2021
- [Babelscape/wikineural-multilingual-ner](https://huggingface.co/Babelscape/wikineural-multilingual-ner)
- [McClelland CLS 1995](https://stanford.edu/~jlmcc/papers/McCMcNaughtonOReilly95.pdf)
- [Tonegawa 2012 Nature engram](https://www.nature.com/articles/nature11028)
- [Tonegawa Nobel 1987 (immunologia, non engram)](https://www.nobelprize.org/prizes/medicine/1987/tonegawa/facts/)
- [Tulving Episodic and Semantic Memory 1972](https://psycnet.apa.org/record/1973-08477-007)
- [Agent Memory Techniques (30 notebooks)](https://github.com/NirDiamant/Agent_Memory_Techniques)
