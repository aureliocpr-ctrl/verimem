# Ricerca esterna — le tecniche pubblicate contro i nostri cinque muri (02/09/2026)

> **Cos'è**: rassegna della letteratura e della pratica (2024-2026) sui cinque muri
> MISURATI di verimem, prodotta il 02/09/2026 da un ricercatore esterno (Claude Opus,
> sola lettura, WebSearch/WebFetch) su mandato del lead — mandato di Aurelio:
> «ricerca seria e reale dove abbiamo lacune, abbattere i muri».
> **Come leggerla**: ogni numero ha un URL; «non trovato» è scritto dove il ricercatore
> non ha trovato una fonte primaria; i numeri di fonte secondaria sono marcati.
> Ogni tecnica porta UN esperimento da un giorno con una PREDIZIONE numerica: è
> l'anello ② della catena (baseline → ipotesi → esperimento → falsificazione →
> integrazione). Chi esegue scrive la predizione PRIMA, e ws7 falsifica con un campo
> diverso. Vincolo dichiarato al ricercatore: sistema locale su CPU, nessuna API a
> pagamento, Python.
> **Assegnazioni**: M1 → ws4 · M2 → ws1 · M3 → ws2 · M4 → ws5 · M5 → ws3 · (M6, la
> fonte non conservata, non era nel mandato: ws6 parte dalla baseline).

## M1 — Trade-off del gate (falsità 15,9% / veri persi 29,3%)

### T1.1 — Sostituire il giudice NLI generico con un grounding checker addestrato allo scopo
**Cosa fa** — MiniCheck e FactCG non sono NLI generici: sono encoder addestrati su dati sintetici che simulano errori fattuali realistici a livello di documento (l'NLI classico è frase-frase e non regge il ragionamento document-level).

**Numeri** (balanced accuracy media, LLM-AggreFact, 11 dataset):

| modello | size | BAcc media |
|---|---|---|
| Bespoke-MiniCheck-7B | 7B | 77,4 |
| FactCG-DeBERTa-L | 0,4B | 75,6 |
| gpt-4o-2024-05-13 | — | 75,9 |
| MiniCheck-Flan-T5-L | 0,8B | 75,0 |

Fonte leaderboard: https://llm-aggrefact.github.io. Nel paper FactCG, FactCG-DBT 77,2 vs GPT-4o 75,9 vs MiniCheck-FT5 75,5 (https://arxiv.org/html/2501.17144v1). MiniCheck-FT5 74,7 BAcc vs GPT-4 75,3 e **AlignScore 70,4**; costo $0,24 contro $107 sul test set da 13K, calcolato a $0,8/GPU-ora → i «400x» (https://arxiv.org/html/2404.10774v2, https://arxiv.org/abs/2404.10774).

**Applicabilità CPU: sì.** 0,4B encoder-only; in int8 ~440 MB. Nessuna API.
**Costo: medio** (swap del modello + ri-taratura delle soglie + ri-misura del banco).
**Esperimento (1 giorno)** — Passare i ~600 casi già etichettati del banco (veri persi + falsi serviti) attraverso `FactCG-DeBERTa-v3-Large` a soglia 0,5 e confrontare con il giudice attuale. *Predizione: i veri persi scendono sotto il 20% a falsità servita ≤ 18%. Se i veri persi restano sopra il 25%, il collo di bottiglia non è il modello ma la formulazione (→ M5) e la tecnica è falsificata.*

### T1.2 — Soglia per dominio invece di soglia globale
**Cosa fa** — Una soglia sola per tutto il corpus è tarata sul dominio medio.

**Numeri** — Lo stesso modello, stessa soglia, sul leaderboard: FactCG-DeBERTa-L fa **88,4 su REVEAL e 59,1 su ExpertQA** (spread 29,3 punti di BAcc); MiniCheck-Flan-T5-L fa 86,2 / 59,0 (spread 27,2). Non è rumore: è il dominio (https://llm-aggrefact.github.io). Questo replica il nodo aperto «L1 non può calibrarsi sul corpus» (`e00618a933da`).

**Applicabilità CPU: sì**, è aritmetica sulle soglie.
**Costo: piccolo.**
**Esperimento (1 giorno)** — Stratificare il banco per `topic` di primo livello (lessons/ · project/ · decisions/) e ottimizzare una soglia per strato su metà, misurando sull'altra metà. *Predizione: ≥5 punti di veri-persi recuperati a falsità invariata. Se il guadagno cross-validato è <2 punti, gli strati non separano popolazioni diverse e la tecnica è falsificata.*

### T1.3 — NON decomporre i fatti corti (tecnica al negativo, già misurata da altri)
**Cosa fa** — FActScore-like: spezzare il claim in sotto-claim atomici e aggregare. La letteratura 2024-2025 dice che **peggiora i verificatori forti su claim già atomici**.

**Numeri** ("Decomposition Dilemmas", https://arxiv.org/html/2411.02400):
- WiCE, claim-level: MiniCheck baseline BAcc **80,01** → con decomposizione FActScore **71,11 (−8,90)**; VeriScore 74,74 (−5,27); WiCE-decomp 76,81 (−3,20).
- FELM, response-level (claim multipli): MiniCheck 56,84 → VeriScore **58,97 (+2,13)**, F1 48,10 → **67,56 (+19,46)**.
- BingChat: GPT-4o-mini F1 66,67 → FActScore **25,36 (−41,31)**.
- Frase del paper: la decomposizione «generally benefits weaker verifiers, while it tends to negatively affect stronger verification systems».

**Lettura per noi**: la regola O3 «frase con più affermazioni → spezza» è confermata **solo** per il regime response-level; applicarla a un fatto già atomico è nel regime che perde 9 punti.

**Applicabilità CPU: sì** (è una regola, non un modello).
**Costo: piccolo.**
**Esperimento (1 giorno)** — Classificare i fatti del banco in «una affermazione» vs «≥2 affermazioni» e misurare i veri persi nei due strati, con e senza spezzatura. *Predizione: nello strato mono-affermazione la spezzatura peggiora i veri persi di ≥3 punti; nello strato multi migliora di ≥10 punti F1. Se il segno è lo stesso nei due strati, l'euristica è falsificata.*

### T1.4 — Terzo stato («held for review») e verdetto a livello di span
**Cosa fa** — Sostituire ammesso/quarantinato con ammesso / **da rivedere** / quarantinato, e dire *quale pezzo* non è supportato invece di bocciare il fatto intero.

**Numeri** — Conformal factuality (Mohri & Hashimoto, https://arxiv.org/abs/2402.10978): garanzie di correttezza «80-90%» **trattenendo la maggioranza dell'output originale**, con calibrazione su pochi campioni annotati. LettuceDetect (https://arxiv.org/abs/2502.17125): token-classification su ModernBERT, **F1 79,22% example-level su RAGTruth**, +14,8% su Luna (SOTA encoder precedente), **~30x più piccolo** dei migliori modelli, contesto 8.192 token, 30-60 esempi/s su una GPU.

**Applicabilità CPU: parziale.** ModernBERT-base gira su CPU (i 30-60/s sono su GPU; su CPU attendersi ~1 ordine di grandezza in meno). Il conformal è puro post-processing: **sì**.
**Costo: medio** (schema DB + API di recall + UI del verdetto).
**Esperimento (1 giorno)** — Applicare split-conformal sui punteggi di grounding già registrati: calibrare su metà del banco per α=0,10 e misurare copertura e frazione trattenuta sull'altra metà. *Predizione: a falsità servita ≤10% si trattiene ≥80% dei fatti veri (oggi ne perdiamo 29,3%). Se la frazione trattenuta è <70%, il punteggio non è abbastanza discriminante e serve prima T1.1.*

---

## M2 — Recall cross-lingua (IT 9/10, EN 5/10)

### T2.1 — Cambiare embedder, ma scegliendolo su un banco italiano (non sulla media MIRACL)
**Cosa fa** — Embedder multilingue allineato cross-lingua.

**Numeri, e una trappola verificata** — Su MIRACL (media 18 lingue, nDCG@10): BM25 31,9 · mDPR 41,8 · mContriever 43,1 · mE5-large 65,4 · **BGE-M3 dense 67,8** (https://arxiv.org/html/2402.03216v3). Su MIRACL Italiano **non c'è**: l'italiano compare solo in MKQA (Recall@100): M3-dense 76,4 · M3-All 76,5 · mE5-large **76,8** · E5-mistral-7b 77,1 — cioè **l'ordine si inverte**. Confermato su un banco italiano indipendente (IT-RAG-Bench, 3.200 passaggi, 640 query, nDCG@10 / R@10): mE5-L **0,279 / 0,489** · BGE-M3 **0,238 / 0,404** · E5-large 0,262 / 0,439 · LaBSE 0,189 / 0,315 (https://arxiv.org/html/2605.23618v1). Il modello che vince la media perde sull'italiano di 4,1 punti nDCG.
mE5-small: 118M parametri, 384 dim, 12 layer, 512 token, ONNX fp32 448,58 MB → **int8 112,8 MB**; MIRACL medio 60,8 nDCG@10 / 92,4 R@100 contro mE5-base 62,3 / 93,1 e mE5-large 66,5 / 94,3 (https://arxiv.org/html/2402.05672v1, https://huggingface.co/Teradata/multilingual-e5-small).

**Applicabilità CPU: sì.** 118M in int8.
**Costo: medio** (re-embedding di 17.070 fatti + validazione).
**Esperimento (1 giorno)** — Il banco IT/EN 10 fatti × 2 lingue è troppo piccolo: portarlo a 100 fatti × 2 query. Poi confrontare embedder attuale vs mE5-small vs mE5-base. *Predizione: il recall EN sale da 50% a ≥75% con mE5-base; il recall IT non scende sotto il 90%. Se l'EN resta sotto il 65%, il problema non è l'embedder ma la fusione (→ T2.2).*

### T2.2 — Fusione ibrida esplicita e misurata, non implicita
**Cosa fa** — Il «salto lessicale» (serve una parola *del* fatto, il sinonimo esatto fallisce) è la firma di un ranking dominato dal ramo BM25.

**Numeri** — BGE-M3 su MIRACL: dense 67,8 · **sparse 53,9** · multi-vec 69,0 · dense+sparse 68,9 · **tutto 70,0** — la fusione vale +2,2 sul dense da solo e **+16,1 sullo sparse da solo** (https://arxiv.org/html/2402.03216v3). RRF su Elastic: +1,4% nDCG@10 sul solo learned-sparse e **+18% sul solo BM25** (https://www.elastic.co/search-labs/blog/improving-information-retrieval-elastic-stack-hybrid). Contro-evidenza da non ignorare: RRF risulta **3,86% sotto** la fusione score-based su 6 dataset BEIR (fonte secondaria, https://denser.ai/blog/hybrid-search-for-rag/ — non verificata su primaria: **numero da trattare come non confermato**).
Su query expansion classica senza LLM la letteratura è negativa: RM3 su Robust04, sul 20% di topic più difficili, **+0,006 nDCG@10 e +0,008 MAP** — il *query drift* rinforza proprio l'errore da vocabulary gap (https://arxiv.org/html/2608.00452v1).

**Applicabilità CPU: sì**, è aritmetica sui ranghi.
**Costo: piccolo.**
**Esperimento (1 giorno)** — Ablation a una variabile: solo-BM25 / solo-dense / RRF / somma normalizzata, sullo stesso banco 100×2. *Predizione: sulle query EN il ramo dense da solo batte l'ibrido attuale di ≥15 punti di recall@10 — cioè la fusione oggi sta annegando il segnale semantico. Se solo-dense NON batte l'ibrido, la diagnosi «il BM25 domina» è falsa e resta l'embedder.*

### T2.3 — Indicizzare una copia tradotta del fatto (document translation, non query translation)
**Cosa fa** — A scrittura, salvare accanto al fatto un campo `content_en` (o `content_it`) e indicizzare entrambi. Attacca alla radice il language bias: gli embedding multilingui **clusterizzano per lingua** e preferiscono candidati sbagliati nella lingua della query a candidati giusti in un'altra.

**Numeri** — In retrieval accademico EN-FR, «translating documents is generally more effective than translating queries» (https://aclanthology.org/2025.mrl-main.16.pdf). Sul bias di lingua esiste una misura riportata di preferenza same-language (1,29x per embedding OpenAI, 1,64x per M3): **non verificata sulla fonte primaria** (https://www.arxiv.org/pdf/2509.25138 non estraibile) → **non verificato**, non usarla in vetrina.
Contro il costo della traduzione locale: static embeddings danno ~125x su CPU rispetto a mE5-small mantenendo 92,3% su STS e 95,52% su pair classification (https://huggingface.co/blog/static-embeddings) — utile come primo stadio se il doppio indice raddoppia il costo.

**Applicabilità CPU: parziale.** Serve un traduttore locale (NLLB-200-distilled-600M o simile) al momento del `save`, non del recall: costo una-tantum per fatto.
**Costo: medio.**
**Esperimento (1 giorno)** — Prendere 100 fatti italiani, tradurne il testo in inglese con un modello locale, indicizzare la copia, e ri-misurare il recall con query EN. *Predizione: il recall EN sale a ≥85% (oggi 50%), il recall IT resta ≥90%, il corpus cresce del 100% in righe ma l'indice di meno perché i vettori sono già lì. Se il recall EN sale meno di 20 punti, il problema è la formulazione della query, non la lingua dell'indice.*

### T2.4 — Reranker cross-encoder multilingue sul top-50
**Cosa fa** — Il primo stadio recupera largo, un cross-encoder riordina: attacca il «salto» perché il cross-encoder vede query e fatto insieme.
**Numeri** — bge-reranker-v2-m3, 278M-568M parametri, primo su NanoMIRACL fra i cross-encoder multilingui (87,57), ~8 ms/coppia su CPU. **Tutte fonti secondarie** (https://agentset.ai/rerankers/baaibge-reranker-v2-m3, https://medium.com/@Nexumo_/10-vector-db-rerankers-quality-vs-latency-c747611f4c96) — non verificate su paper.
**Applicabilità CPU: parziale** (50 candidati × 8 ms = ~0,4 s per recall: accettabile solo se il recall non è nel loop stretto).
**Costo: piccolo.**
**Esperimento (1 giorno)** — Reranking del top-50 sul banco 100×2. *Predizione: +10 punti di recall@5 EN. Se il fatto giusto non è nel top-50 del primo stadio, il reranker non può nulla — misurare prima recall@50, che è il tetto.*

---

## M3 — Consolidamento che cancella fatti veri (34,3% di supersessioni sbagliate)

### T3.1 — Modello bi-temporale: invalidare, non cancellare (Zep/Graphiti)
**Cosa fa** — Ogni edge porta `valid_at`/`invalid_at` (tempo del mondo) **e** `created_at`/`expired_at` (tempo di sistema). Un fatto superato smette di essere *valido*, non smette di *esistere*: il recall as-of a una data resta possibile.
**Numeri** — DMR: Zep **94,8%** vs MemGPT 93,4%; su LongMemEval fino a **+18,5%** di accuratezza e **−90%** di latenza rispetto al baseline (https://arxiv.org/abs/2501.13956).
**Applicabilità CPU: sì** per lo schema bi-temporale (due colonne + filtro sul recall). **No** per la pipeline Graphiti completa, che estrae entità con chiamate LLM per ogni scrittura.
**Costo: medio** (migrazione schema + il recall deve filtrare su `invalid_at IS NULL`).
**Esperimento (1 giorno)** — Rigiocare le supersessioni storiche già classificate (i 143 ordinari + 70 sospetti) contro uno schema bi-temporale simulato e contare quanti fatti «uccisi» tornerebbero servibili. *Predizione: ≥34% dei fatti attualmente muti per supersessione torna nel recall senza aumentare le contraddizioni servite oltre il 5%. Se le contraddizioni servite superano il 15%, versionare senza un criterio di preferenza sul recente non basta.*

### T3.2 — Version control con rollback semantico (ChronoMem)
**Cosa fa** — Snapshot della memoria a ogni scrittura + selezione della versione tramite retrieval ibrido su richiesta in linguaggio naturale.
**Numeri** (https://arxiv.org/html/2607.27773): LoCoMo Recall@1 **20,5%** vs 12,0% del baseline ibrido, Recall@5 38,9%; MemoryAgentBench Recall@1 **33,4%** vs 24,3%, Recall@5 60,2%; QA rollback-consistent **~+10 punti F1** su LoCoMo e **~+18 punti** di accuratezza su MAB (53,8% con Llama-3.1-8B). Nota onesta: **Recall@1 al 20,5% resta basso in assoluto** — selezionare *quale* versione è il problema aperto, non risolto.
**Applicabilità CPU: parziale** (lo snapshot completo a ogni write è O(corpus); per 17.070 fatti serve un delta-log, non uno snapshot).
**Costo: grande.**
**Esperimento (1 giorno)** — Non fattibile in un giorno nella forma completa. Versione ridotta: implementare `supersede()` come append di una riga versione e misurare la crescita del DB su 90 fatti/36h. *Predizione: crescita <2% del DB, zero fatti persi.*

### T3.3 — Gate sul supersede: entity+attribute match e contraddizione NLI, non similarità
**Cosa fa** — Distinguere «aggiornamento dello stesso oggetto» da «fatto diverso» richiede di confrontare **entità e attributo**, non il coseno. La misura nostra («entità diverse 12/12 contro 6/12») è già la stessa scoperta.
**Numeri** — mem0 decide ADD/UPDATE/DELETE/NOOP con una tool-call LLM sui top-10 memory simili; LOCOMO overall **66,88%** (mem0) e 68,44% (mem0^g) contro full-context 72,90%; p95 search 0,200 s, totale 1,440 s vs 17,117 s del full-context; 1.764 token/conversazione (https://arxiv.org/html/2504.19413v1). **Il paper non contiene alcuna ablation sull'accuratezza della scelta dell'operazione**: nessuno pubblica quel numero.
Il numero che lo pubblica è HaluMem (https://arxiv.org/html/2511.03506v1): su Mem0, Mem0-Graph, Memobase e Supermemory, **tutti i sistemi stanno sotto il 26% di update corretti**, con omissioni sopra il 50%; l'estrazione ha precision 86-92% ma recall <60% e accuratezza complessiva <62%; QA <55%. Sui detector di contraddizione: NLI e LLM sono ad **alta precisione e basso recall**, e l'NLI degrada sui contesti lunghi (https://arxiv.org/pdf/2504.00180).
**Il nostro 34,3% di supersessioni sbagliate va letto contro questo sfondo: è nell'ordine di grandezza del campo, non un'anomalia nostra.**
**Applicabilità CPU: sì** (l'NLI c'è già; l'entity matching è regex+lessico).
**Costo: piccolo.**
**Esperimento (1 giorno)** — Sui 213 casi di supersessione già classificati, misurare precision/recall di tre criteri a una variabile per volta: (a) coseno, (b) entità+attributo uguali, (c) NLI dice *contradiction*. *Predizione: (b) da solo porta le supersessioni sbagliate sotto il 15%; (c) da solo ha precision >80% ma recall <40% (coerente con la letteratura), quindi va usato come veto e non come trigger. Se (c) ha recall >60%, la letteratura non descrive il nostro dominio e vale la pena insistere.*

---

## M4 — Costo del giudice (758 MB × 8 processi)

### T4.1 — Un giudice, N client (servizio condiviso)
**Cosa fa** — Il modello vive in un processo; gli 8 agenti parlano via socket/HTTP locale.
**Numeri** — Aritmetica sul dato nostro: 758 MB × 8 = **6,06 GB → 758 MB**, −87,5%. Evidenza indiretta che la condivisione paga oltre la RAM: MiniCheck con Automatic Prefix Caching passa da **55 a 30 minuti** su 29K claim perché lo stesso documento non viene ricomputato (https://github.com/Liyan06/MiniCheck/blob/main/README.md) — un giudice condiviso è la precondizione per condividere quella cache. **Numero di latenza pubblicato per un'architettura a giudice condiviso in un server MCP: non trovato.**
**Applicabilità CPU: sì.** È la stessa forma di `text-embeddings-inference`.
**Costo: medio** (un daemon + client + gestione del caso «daemon giù»).
**Esperimento (1 giorno)** — Avviare un daemon con il giudice e far passare 200 `save` da 4 processi client, misurando RSS totale e p50/p95 di latenza contro l'attuale. *Predizione: RSS totale ≤1,2 GB (contro ~3 GB con 4 processi) e p95 peggiora di <150 ms. Se p95 peggiora di più di 500 ms, la serializzazione del daemon è il collo di bottiglia e serve un pool.*

### T4.2 — Export ONNX + quantizzazione int8
**Cosa fa** — Stessa architettura, pesi a 8 bit.
**Numeri** — Riferimento diretto e verificabile sulla stessa famiglia di modelli: mE5-small ONNX **fp32 448,58 MB → int8 112,8 MB** (−75%) (https://huggingface.co/Teradata/multilingual-e5-small). Su transformer INT8 dinamico, la letteratura riporta 1,5-3x su CPU con perdita minima; **il numero specifico su un DeBERTa NLI con accuratezza misurata non è stato trovato su fonte primaria** — i valori circolati (2,9x su BERT-base, 3,23x per onnx-qint8 con <0,5% di costo in qualità) provengono da blog e dalla doc sbert, e **la verifica diretta sulla pagina sbert non li ha trovati**: trattarli come non confermati.
**Applicabilità CPU: sì**, è esattamente il caso d'uso.
**Costo: piccolo.**
**Esperimento (1 giorno)** — Esportare il giudice attuale in ONNX int8 e rigiocare l'intero banco del gate. *Predizione: RSS per processo ≤250 MB, throughput ≥1,8x, e la BAcc sul banco cala di ≤1 punto. Se cala di più di 2 punti, l'int8 dinamico non regge su questo modello e va provato QDQ statico con calibrazione.*

### T4.3 — Scendere di taglia, ma misurando quanto costa
**Cosa fa** — xsmall al posto di base/large.
**Numeri** — cross-encoder NLI: `nli-deberta-v3-xsmall` **87,77% MNLI-mismatched / 91,64% SNLI-test** contro `nli-deberta-v3-base` **90,04% / 92,38%** (https://huggingface.co/cross-encoder/nli-deberta-v3-base, https://huggingface.co/navteca/nli-deberta-v3-xsmall) — ~70,8M parametri contro ~184M. Sul compito che conta davvero (grounding, non NLI di frase), il riferimento è il salto di famiglia: FactCG-RoBERTa-L 0,4B fa 75,4 BAcc contro GPT-4o 75,9 (https://arxiv.org/html/2501.17144v1).
**Applicabilità CPU: sì.**
**Costo: piccolo.**
**Esperimento (1 giorno)** — Sostituire il giudice con xsmall e misurare il banco. *Predizione: veri persi peggiorano di ≥4 punti. È un test di conferma della gerarchia: se xsmall pareggia il modello attuale, il giudice non sta usando la sua capacità e va sostituito (T1.1), non rimpicciolito.*

### T4.4 — Cache del verdetto su hash(source, fatto)
**Cosa fa** — Lo stesso `--source` viene rigiudicato molte volte (i lotti di `save` condividono l'output di pytest).
**Numeri** — Evidenza indiretta: **24 quarantene su 154 nel nostro corpus sono testi ritentati identici** (dato nostro, `stato-reale/78`); MiniCheck 55→30 min con prefix caching sullo stesso documento (URL sopra).
**Applicabilità CPU: sì.** Costo: **piccolo.**
**Esperimento (1 giorno)** — Contare nel journal quante coppie (source, fatto) sono duplicate esatte. *Predizione: ≥15% delle chiamate al giudice sono ripetizioni bit-identiche, quindi eliminabili a costo zero in qualità.*

---

## M5 — Il verificatore decide con le parole («otto» vs «8»)

### T5.1 — Canonicalizzazione numerica — e la trappola su *dove* applicarla
**Cosa fa** — Normalizzare numeri, unità, notazione scientifica e comparatori prima del confronto.

**Numeri, dalla fonte più diretta che esista sul nostro muro** (Symbolic Augmentation Closes a Canonical-Equivalence Blind Spot in Neural Fact-Checkers, Genpei Zhang, 19/05/2026, https://arxiv.org/abs/2607.16212 · https://arxiv.org/html/2607.16212v1):
- Un encoder che fa **96,7%** sulle forme originali crolla a **36,5%** su riscritture fisicamente equivalenti (95 °C ↔ 368,15 K; 0,5 mol/L ↔ 500 mmol/L).
- Sullo stesso banco (1.500 item, PMC+arXiv, Krippendorff α=0,882, 94% di accordo su 50 item ricontrollati a mano), macro-F1 dei fact-checker pronti all'uso: **MiniCheck 0,295 · Bespoke-MiniCheck-7B 0,229 · FactCG 0,184 · Granite Guardian 0,155 · ModernBERT-NLI zero-shot 0,275**; un verificatore **simbolico** (UnitGraph) fa **0,537**; ModernBERT fine-tuned 0,899; Claude Opus 4.7 0,973.
- La cura che funziona è **augmentation al training**: probe da 36,5% a **98,2% (+61,7 punti)** con macro-F1 sostanzialmente invariata (0,899 → 0,902); tutte e quattro le famiglie insieme portano ogni probe a ≥96%. Transfer OOD su SciFact-Open: 0,791 → **0,828**.
- 🔴 **Le cure a inference-time sono cadute tutte**: ensemble di logit **−0,004**, filtro di accordo **−0,011**, output simbolico come feature ausiliaria **−0,020**, insegnamento con silver-label **−0,277** e **−0,381**.

**Lettura per noi, e la differenza che conta**: quel «tutto ciò che è bolt-on fallisce» vale per un verificatore **neurale** a cui si attacca un normalizzatore. Il nostro strato numerico è una **regola**, non un modello: lì la canonicalizzazione è al livello giusto (si normalizza l'input della regola). La trappola resta per il *moat* NLI: non aspettarsi che un pre-processore risolva il giudice.

**Applicabilità CPU: sì** (libreria di normalizzazione, zero modelli).
**Costo: piccolo** per la regola numerica, **grande** per la via del fine-tuning.
**Esperimento (1 giorno)** — Costruire 60 coppie source/fatto che differiscono solo per la forma del numero (parola↔cifra, separatore decimale IT/EN, notazione scientifica, unità) e passarle allo strato numerico attuale, poi con canonicalizzazione. *Predizione: oggi passa ≤50% (`stato-reale/80` dice 4/6 sfuggono in parola); con canonicalizzazione ≥95%, e i falsi veri 6/6 in cifra continuano a essere fermati. Se la canonicalizzazione fa passare anche i falsi, si è comprato recall con precisione ed è falsificata.*

### T5.2 — Encoder pre-addestrato ai numeri, a parità di taglia
**Cosa fa** — Non un modello più grande: un modello della **stessa taglia** pre-addestrato sui numeri.
**Numeri** — QuanTemp (15.514 claim reali con quantità ed espressioni temporali, da 45 organizzazioni di fact-checking): miglior baseline **macro-F1 58,32** con FinQA-RoBERTa-Large + claim decomposition; **NumT5-small batte T5-small di 11,8 punti di macro-F1**, e FinQA-RoBERTa-Large batte RoBERTa-Large dello stesso margine (https://arxiv.org/html/2403.17169v3). Sfondo: EQUATE mostra che **7 modelli di entailment pubblicati non superano in media la majority-class baseline** sul ragionamento quantitativo (https://aclanthology.org/K19-1033.pdf). NumPert: anche i sistemi proprietari di punta perdono **fino al 62%** di accuratezza sotto perturbazione numerica (https://arxiv.org/abs/2511.09971).
**Applicabilità CPU: sì** (NumT5-small, FinQA-RoBERTa-large 0,35B).
**Costo: medio.**
**Esperimento (1 giorno)** — Sul sottoinsieme numerico del banco, confrontare il giudice attuale con un modello numericamente pre-addestrato. *Predizione: ≥8 punti di macro-F1 sui soli fatti numerici. Se il guadagno è <3 punti, lo strato lessicale sta già assorbendo il segnale e il collo è altrove.*

### T5.3 — NLI multilingue quando source e fatto sono in lingue diverse
**Cosa fa** — Un giudice che accetta premessa in italiano e ipotesi in inglese (il caso quotidiano: source = output di pytest in inglese, fatto in italiano).
**Numeri** — mDeBERTa-v3-base-mnli-xnli, **0,3B parametri**, XNLI media **0,808**, inglese 0,883, tedesco 0,825, francese 0,834, spagnolo 0,845 — **l'italiano non è in XNLI** (https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli). La variante addestrata su 2,7M coppie in 27 lingue dichiara **fino a 87,1%** su XNLI (https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7, claim della model card, non di un paper). Sul fact-checking multilingue reale il tetto è basso: X-FACT, 31.189 claim in 25 lingue, **miglior baseline ~40% di F1** (https://arxiv.org/abs/2106.09248).
**Un numero di riferimento pubblicato per NLI italiano su fact verification: non trovato.**
**Applicabilità CPU: sì** (0,3B, ~600 MB int8 — meno dell'attuale).
**Costo: medio.**
**Esperimento (1 giorno)** — 80 coppie (source EN, fatto IT) già etichettate, giudice attuale vs mDeBERTa-xnli. *Predizione: i veri persi sul sottoinsieme cross-lingua scendono di ≥10 punti. Se non scendono, la perdita non è dovuta alla lingua ma alla parafrasi, e va misurata separatamente (source IT / fatto IT parafrasato).*

### T5.4 — Strada già falsificata da altri: la tokenizzazione R2L dei numeri
**Cosa fa (e non fa)** — Tokenizzare i numeri da destra a sinistra, che aiuta sull'aritmetica.
**Numeri** — Su QuanTemp (subset inglese, 15.514 claim), macro-F1 di validazione: **R2L short 0,45 · R2L long 0,47** contro **standard short 0,52 · standard long 0,52 · modello sottomesso 0,57**. Conclusione degli autori: «R2L tokenization does not boost NLI of numerical tasks». Gli stessi autori indicano la **normalizzazione di numeri e date come lavoro futuro non testato** (https://arxiv.org/html/2507.06195).
**Da mettere nella lista «NON RITENTARE».**

---

## Classifica valore/costo — le 5 che pagano di più

**1. T5.1 — Canonicalizzazione numerica nello strato a regola (piccolo).**
È l'unico punto dove abbiamo già la misura del buco (4/6 numeri in parola sfuggono, `stato-reale/80`), la cura è deterministica, e la letteratura quantifica il guadagno atteso in **+61,7 punti di probe accuracy** con macro-F1 invariata. Il costo è ore, non giorni. La sua trappola — «a inference-time su un verificatore neurale non funziona» — nel nostro caso non si applica, perché lo strato numerico è una regola: è esattamente il livello dove il paper dice che il simbolico vince (UGV 0,537 contro MiniCheck 0,295).

**2. T1.2 — Soglia per dominio (piccolo).**
29,3 punti di spread di BAcc dello stesso modello fra REVEAL e ExpertQA sono la prova pubblica di ciò che il nodo `e00618a933da` dice già: il pavimento non può calibrarsi sul corpus intero. Nessun modello nuovo, nessuna migrazione, e attacca direttamente il 29,3% di veri persi. Rischio: se gli strati non separano popolazioni diverse il guadagno è nullo — e questo si scopre in un giorno.

**3. T4.1 — Giudice come servizio condiviso (medio).**
−87,5% di RAM per aritmetica diretta sul numero nostro, e abilita T4.4 (cache dei verdetti). Non migliora la qualità di un punto, ma è la precondizione perché tutte le altre cure (T1.1 con un 0,4B, T5.2, T5.3) siano adottabili senza moltiplicare 8 volte l'impronta. Il fatto «l'adozione misura l'ATTRITO» si applica: un giudice più grande in 8 copie non verrà mai acceso.

**4. T3.3 — Gate sul supersede a entità+attributo, con l'NLI come veto (piccolo).**
Il campo pubblica **<26% di update corretti** su quattro sistemi (HaluMem) e mem0 non pubblica affatto l'accuratezza della sua scelta ADD/UPDATE/DELETE: qui non stiamo inseguendo, stiamo misurando ciò che gli altri non misurano. Il criterio a entità l'abbiamo già validato 12/12 contro 6/12. La letteratura aggiunge una cosa che manca: l'NLI di contraddizione è **alta precisione, basso recall**, quindi va usato come veto e non come trigger — e questo evita di ripetere l'errore già catalogato («otto criteri su otto caduti»).

**5. T1.3 — Non decomporre i fatti già atomici (piccolo).**
È una cura al negativo, quindi a costo quasi nullo, e ha il numero più netto della rassegna: **−8,90 BAcc** quando si decompone un claim atomico con un verificatore forte, contro **+19,46 F1** quando il claim ne contiene davvero più d'uno. La regola O3 è giusta a metà: manca il criterio che decide *quale metà*. Un giorno di misura lo fissa.

**Escluse dalla top-5, e perché**: T2.1/T2.3 (cambio embedder e doppio indice) hanno il guadagno atteso più alto sul recall EN, ma costano un re-embedding di 17.070 fatti e vanno fatte **dopo** l'ablation T2.2 a una variabile — altrimenti si cambia embedder e fusione insieme e il confronto mente, che è l'errore ricorrente misurato tre volte il 02/09. T3.2 (ChronoMem) è grande e il suo Recall@1 al 20,5% dice che il problema che risolve non è ancora risolto da nessuno.

**Cinque numeri cercati e NON trovati su fonte primaria**: (a) latenza pubblicata di un'architettura a giudice condiviso per server MCP; (b) accuratezza int8 di un DeBERTa NLI misurata su un banco di grounding; (c) accuratezza dell'operazione ADD/UPDATE/DELETE/NOOP di mem0 (nessuna ablation nel paper); (d) numeri NLI/fact-verification specifici per l'italiano (XNLI non contiene l'italiano; MIRACL nemmeno — l'italiano compare in MKQA, Recall@100, dove mE5-large 76,8 batte BGE-M3-All 76,5, cioè l'ordine si inverte rispetto alla media MIRACL); (e) i moltiplicatori di same-language preference 1,29x/1,64x, riportati dalla ricerca ma non verificabili sul PDF primario.
