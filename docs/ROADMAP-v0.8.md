# Verimem v0.8.0 — "Win both axes, honestly"

Plan of record, 2026-07-22 (sera, post-release 0.7.0). Fonti: ROADMAP-v0.7.md
(gap verificati sul codice), ricerca esterna 2026-07-22 (paper live), numeri
competitivi letti dai result JSON (non a memoria). Ogni numero qui sotto è
misurato o citato con fonte; i target sono PROPOSTE da ricalibrare dopo la
diagnosi baseline — non promesse.

## La tesi one-line
La 0.7.0 ha reso il moat onesto e visibile. La 0.8.0 deve fare due cose:
**(1) chiudere DAVVERO i difetti dichiarati** (non annotarli — risolverli), e
**(2) vincere su entrambi gli assi**: restare unici su grounding/no-confab E
salire nel gruppo di testa sul retrieval, con numeri che chiunque può rifare.

## Stato competitivo VERIFICATO (2026-07-22)
Nostri (result JSON interni, harness nostro):
| bench | noi | leader pubblicati (self-reported, harness LORO) |
|---|---|---|
| LoCoMo | **0.813** | EverOS 93.0 · Eywa 90.19 |
| LongMemEval | **0.790** (recall@k) | Eywa-S 88.2 · Zep 63.8 · Mem0 49.0 |
| HaluMem-extraction | **F1 0.761** | Schema-Grounded F1 97.10 (protocollo diverso) |

Caveat metodologico indelebile: metriche NON omogenee (recall@k ≠ QA-accuracy),
harness e judge diversi, numeri competitor self-reported. Confronto indicativo,
non head-to-head — il head-to-head vero è WS3.

Asse dove siamo davanti (misurato): mem0 `supported_pass_rate 0.25` (serve il
75% di non-supportato); nessun competitor ha write-gate + contraddizione +
astensione + read-path 0-confab. **"Li distruggiamo?" — oggi: sull'asse
grounding/anti-confab sì, nessuno gioca la nostra partita; sul retrieval grezzo
no, siamo nel gruppo (0.79-0.81 vs 88-93 dei leader).** La 0.8.0 attacca
esattamente questo delta, sapendo che Eywa ha PROVATO che la nostra stessa tesi
(evidence-before-belief) è compatibile con LoCoMo 90+: non c'è trade-off
strutturale tra moat e recall — c'è solo lavoro da fare.

## Ereditato dalla 0.7.0 (debiti aperti, stato misurato)
| # | debito | stato oggi |
|---|---|---|
| D1 | ~~L1 keyword FP verticale~~ **CHIUSO in 0.7.0** (sera 22/7, ri-misurato: 0/30 = 0% FP, controlli 0/6) | `7bbec4b` chiude i 2 gap subject-extract; `e6589c9` domain-precision **ON default**; hardening evasion `9ba0981`+`cf271db` (GLM+Kimi). G2 ≤3% **soddisfatto**. Resta P0 (la cura strutturale, sotto) |
| D2 | L3 NLI FP soggetto-diverso — **flip fatto**: `6284d07` subject pre-filter **ON default** (SAFE rule convergente) + `12ce9ae` ORG-UNIT fix; banco ri-misurato 22/7 sera: A 8/8, B/C 1.0, D/E 0 | Limite dichiarato: FN alias 35.2% misurato da `wikidata_subject_eval` v2 (cd24376) — la SAFE rule non skippa la classe, il miglioramento è P4 continuo |
| D3 | Tamper anchor-B/C | anchor-A only (in-DB, detection); chiave esterna + anchor esterno unbuilt (task #24) |
| D4 | Intra-tenant authz (gap 13) | zero per-agent roles; receipt visibility = extraction oracle (task #45) |
| D5 | Content-bound receipts (gap 2) | receipts provano resolvability, non contenuto (task #44) |
| D6 | Ingest-path audit + MCP supersession mirror | task #49, #50 |
| D7 | Scale/robustezza | >3k unproven, ~113ms/write CE, SQLite single-node; multi-client lock-wait (#57); "Postgres → v0.8" già dichiarato in ROADMAP-v0.7 §2.3 |
| D8 | GDPR crypto-shred + export Art.15/20; encryption at rest (gap 5, 11) | unbuilt |
| D9 | CE fuori dominio | 0.829 TruthfulQA-free vs 0.96-0.97 SNLI-in-domain (dichiarato nel README) |
| D10 | Numeri "internal runs" | nessuna riproduzione terza (dichiarato nel README) |
| D11 | Gate bypassabile via sqlite diretto (gap 1) | library senza enforcement |
| D12 | Roadmap-0.8 annotati in 0.7 | bench integrity hostile-shaped; dead-prefix lint + dry-run; READ-side denylist audit; connector-tag `purpose` su MCP |
| D13 | Igiene | CodeQL check rosso (12 FP da dismettere o codeql-config), titolo PR#1, sito 9 lingue thin |
| D14 | REMORSE AdaptiveLedger | fase 1 shadow shipped (4c3e79d), raccolta 3-7gg → fase 2 flag per-tenant (task #20) |
| D15 | LLM-judge banda + NLI auto | d95e480/715924c smoke OK; docs+critic+sycophancy re-cert pendenti (task #55) |

## Workstream

### WS1 — GATE-FP ZERO (chiudere il difetto centrale, non annotarlo)
Il write-gate deve smettere di trattare "non abbastanza provato" come "malevolo".
1. **P0 evidence-before-belief per L1** (la cura vera, ROADMAP-v0.7 §P0):
   L1 defersce a grounding indipendente — forma-da-self-claim + sorgente
   INDIPENDENTE confermata da L4 → advisory; self-source/no-source → escala.
   Da inventare: il segnale di INDIPENDENZA della sorgente (self-paraphrase
   la aggira; `source != proposition` non basta).
2. Chiusura dei 2 residui subject-extract (`Dr.`, verbo `meets`).
3. Decisione default L1 (advisory+marker) e L3 coi CANCELLI: G2 wrong-block
   ≤3% verticale · G4 0 FP soggetto-diverso TENENDO banco A 8/8 su Wikidata
   mutation-eval (mai più etichette auto-prodotte) · G1 confab=0 invariante.
4. D15: certificare banda LLM-judge + NLI auto (docs, critic, sycophancy re-cert).

### WS2 — RETRIEVAL WAR (salire nel gruppo di testa senza tradire il moat)
Metodo diagnosi-first, NIENTE fix alla cieca:
1. **Diagnosi per-categoria dei fail** su LoCoMo (0.813) e LongMemEval (0.790):
   temporal? multi-hop? abstention-over-triggered? adversarial? Ogni categoria
   con conteggio fail e causa dominante.
2. Fix mirati per categoria (candidati, da validare in diagnosi: temporal
   reasoning sul retrieve, session-summary index, entity-KG live sul recall
   path, re-ranking, k-adattivo). Un fix per volta, A/B contro baseline.
3. Studio Eywa (2605.30771) e Schema-Grounded (2604.27906): cosa fanno sul
   READ path che noi non facciamo — sono la NOSTRA tesi portata a 90+.
4. Target provvisori (ricalibrare post-diagnosi): LoCoMo ≥0.88,
   LongMemEval ≥0.85, HaluMem-extraction F1 ≥0.85. G5 invariante: il guadagno
   retrieval NON deve costare confab (read-path 0 confab, astensione 3/3).

### WS3 — VERIBENCH + HEAD-TO-HEAD (risolvere D10 davvero)
1. Spin-off `benchmark/veribench/` in repo standalone — trasparenza DICHIARATA
   ("maintained by the Verimem team" nel README, in chiaro), MAI org anonima
   (decisione 2026-07-22: il trucco scoperto distrugge credibilità).
2. Adapter alla pari: verimem, mem0, zep/graphiti, letta — STESSO LLM per
   tutti, stesso judge, seed fissi, un comando. Metrica NET(λ) =
   (correct − λ·wrong)/n: la fabbricazione ha un prezzo, il recall da solo no.
3. Head-to-head sul NOSTRO stack e su LoCoMo/LongMemEval con protocollo
   pubblicato. Criterio di successo: **≥1 riproduzione terza documentata**.
4. Prerequisiti: verifica nome (GitHub/dominio), decisione Aurelio su org
   e preprint (draft esiste: docs/papers/veribench-preprint-DRAFT.md).

### WS4 — TRUST HARD (le promesse crittografiche vere)
Selezione 0.8.0 (il resto scivola a 0.9):
1. **Anchor-B**: firma decisioni con chiave FUORI dal DB (HMAC/Ed25519) +
   anchor esterno periodico (RFC-3161 TSA o transparency log o git remote
   firmato). Attivo di default nel NOSTRO deployment = dogfood della promessa.
2. **Intra-tenant authz** (D4): per-agent identity + scoping della receipt
   visibility (anti extraction-oracle).
3. **Content-bound receipts** (D5): hash dello span citato, sweep di audit,
   `stale` come segnale ortogonale.
4. D6: ingest audit + MCP supersession mirror.

### WS5 — SCALE + ROBUSTEZZA (D7)
1. Bench onesto 50k fact (oggi unproven >3k) + p95 write/read pubblicati.
2. Multi-client: cap lock-wait interattivo + degrado veloce (#57, misura fatta:
   diretto-concorrente 24s vs server-condiviso 262ms).
3. Postgres backend opzionale (dichiarato in 0.7 §2.3) — solo se il bench 50k
   mostra che SQLite non regge i deployment target; altrimenti si dichiara
   il bound e si rimanda (no infra per sport).
4. D14 REMORSE fase 2 dopo la raccolta shadow.

### WS-igiene (giorni, non settimane)
CodeQL green (dismiss 12 FP o codeql-config con esclusione tests/benchmark),
titolo PR#1, enrichment sito 9 lingue, D9 (CE fuori-dominio: hard-negatives da
HaluMem/Wikidata mutation → retrain `local_gate_ce_v3` — questo è in realtà
lavoro WS1-adiacente, non igiene, ma parte dalla stessa misura).

## Definition of Done 0.8.0 (criteri di FATTO, non aggettivi)
| # | criterio | numero |
|---|---|---|
| K1 | FP verticale | wrong-block ≤3% con default definitivo ON |
| K2 | FP semantico | 0 FP soggetto-diverso su Wikidata mutation, banco A 8/8 |
| K3 | anti-confab invariante | confab servite = 0, injection ammesse = 0 (mai regredire) |
| K4 | retrieval | target post-diagnosi raggiunto sul nostro harness (provvisori: LoCoMo ≥0.88, LME ≥0.85) |
| K5 | head-to-head | VeriBench pubblico, ≥3 adapter, ≥1 riproduzione terza |
| K6 | tamper | anchor-B esterno attivo nel nostro deployment |
| K7 | scale | bench 50k pubblicato con p95 |
| K8 | zero silenzi | ogni cap/skip/fallback su ricevuta o log (già norma 0.7) |

## Ordine proposto
1. WS-igiene (subito, giorni) + WS2.1 diagnosi (parte in parallelo, è misura).
2. WS1 (il mandato "risolvere davvero" — prima i difetti dichiarati).
3. WS2 fix + WS3 (la guerra si combatte con harness pubblico E numeri alti).
4. WS4 selezione + WS5.

## Metodo (indelebile, invariato dalla 0.7)
TDD RED→GREEN (exit da file, mai pipe) · kimi/GLM avversari sul design, ogni
finding verificato sul codice · critic-orchestrator pre-commit · observe-first
per ogni default nuovo · numeri FP SOLO da dataset esterni o gold terzi ·
nessun flip di default senza suite intera + A/B + critic · push/merge/tag =
consenso Aurelio · doc aggiornata mano a mano.
