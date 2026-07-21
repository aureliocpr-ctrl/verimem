# Verimem v0.7.0 — "Nothing silent, nothing mislabeled"

Plan of record, 2026-07-18. Born from a 3-round external adversarial review
(kimi-k3 + glm-5.2 via VeriAgent, effort=high) **cross-checked against the source
code**. Both models independently scored the product **6/10**; both converged on
the same #1 risk and the same roadmap; the cross-examination round then corrected
both roadmaps. Every model claim below was verified against code — refuted ones
are marked so we don't build fixes for non-problems.

## The one-line truth
The engine is real and the thesis is differentiated, but the word **"verified"**
currently over-promises: it is applied to the CE default tier (a ~92-93% probabilistic
filter with a measured 7% Spanish entity-substitution escape) and to receipts that
only prove a path **resolves** (not that its content **supports** the fact). The
default tier's failures are **silent**. v0.7.0 makes the label honest and nothing
the gate decides silent. This is a "secure-defaults + honest-labels" pass, NOT a
re-architecture.

## STATUS — 2026-07-19 (in progress)
- **Phase 0.1/0.2 SHIPPED** (branch `rename/verimem-total`, CI green all platforms):
  every write returns an `adjudication` receipt {disposition, evidence_class, judge,
  score, threshold, margin, reason, confidence_tier}; GateResult carries the
  judge-of-record + threshold (previously discarded); quarantine is a visible,
  reasoned verdict (incl. the store-time injection screen). Commits 57a392c ·
  6fb2565 · ba772f1. Reviewed by kimi-k3 + glm-5.2 (7/10 both); every finding
  verified against code — 3 refuted (interactive=Claude-LLM; judge⇔score invariant
  holds; modal case already has advice), 3 fixed, 3 → roadmap (below).
- **Phase 0.3 (CE band) — code done, default OFF** (3da25b2 · 6434e86, pre-push):
  `confidence_tier` {grounded/review/ungrounded/unverified}; two-threshold CE band
  (tau_lo=40, tau_hi=80) behind `VERIMEM_CE_BAND_ENFORCE`. CALIBRATED on the real
  CE: true entailments (incl. abstractive/paraphrase) score ≥90 (n=14, min 90.3);
  the entity-substitution escape is bimodal (65/68 catchable, one at 96 not).
  MOAT-BENCHMARK proof: enforce OFF escape 6.2% → ON 1.8%, with 112/112 entailed
  still admitted (0 false-block). Honest bound: the ~96 escape + plausible-inference
  confabs (97-99) still need the llm judge — the band is a REAL but PARTIAL fix.
- **Realness ladder (honest).** External review = 6/10 today. Phase 0+1 (code) → a
  defensible 8–8.5. A REAL 9 is NOT a code sprint: it needs third-party-reproduced
  benchmarks, external anchoring in production, and months of measured judge drift.
  Build the harnesses that make 9 reachable; do not claim 9 until earned.

## STATUS — 2026-07-19 (continuation: Phase 1.1 + 0.2b + tamper foundation)
12 commits on `rename/verimem-total` (HEAD `d525d97`), all TDD, 3 opus critics (2 FIX
applied, 1 HOLD). Every new behaviour is **opt-in / default-off / observe-first** —
nothing risky is on by default.

- **Write-path contradiction moat, subscription-free (gap 12 → now ON the write path).**
  The dormant `semantic_conflict` NLI check runs llm-free on the local cross-encoder
  (`fd416f0`), over a bounded, live-only sibling query excluding superseded/quarantined
  facts (`0a05108`). New `observe` mode surfaces without quarantining; advisories are
  excluded from the receipt reason + trust ledger (`e461084`); certified on labeled cases
  (`3336d56`). **Measured limit:** the local CE ignores the `[timestamp]` prefix → it
  over-flags *evolving* facts; fixed in observe by a deterministic evolution-vs-conflict
  policy (`supersession_policy`, `9dad221` · `d525d97`) — same-source+newer =
  `L3-supersession-observe` (evolution), else contradiction. Enforce unchanged.
- **Per-write audit trail (gap 9 partial: quarantines recorded + queryable).** Opt-in
  `VERIMEM_AUDIT_LOG`: every single-proposition `add()` verdict → append-only
  `adjudications.db`, read via `Memory.audit_log()` (`b720867` · `d602f26`). Critic-fixed:
  store-screen layer attribution, a false "below threshold" reason, silent drops
  (`b85e14c`). Ingest-path audit is a filed follow-up (task #49).
- **Tamper-evidence (gap 4: anchor-A WIRED, honestly scoped).** Pure hash-chain
  primitives (`a8ecf57`) now chain the audit trail (`5d8214d`): every row stores
  `entry_hash` (computed under `BEGIN IMMEDIATE`, no fork), `Memory.audit_verify()`
  finds the first edited/deleted/reordered row, `Memory.audit_head()` returns the head
  to **archive off-box** (anchor-A). Honest: the in-DB chain is DETECTION only; the
  external key / transparency service (anchor-B/C, `d9e7246`) stays unbuilt.
- **`source_trust` observe (gap 7).** `ENGRAM_SOURCE_TRUST=observe` measures the
  false-block rate before enforcing (`7b29c4f`).

- **Same-source evolution supersession — SHIPPED, opt-in (task #48, `27c8df6` + critic
  fixes).** `ENGRAM_SUPERSEDE_SAME_SOURCE=enforce` (default off): a newer same-source
  write admits and retires the old value (`superseded_by`) instead of quarantining the
  new; cross-source never supersedes (griefing guard); backfills use valid-time
  (`asserted_at`) so an old re-assertion can't retire the current value; the old is
  retired only when the new is admitted (no data-loss). **No source authentication
  exists** (verified) — safety is default-off + tenancy isolation + a single-agent-per-
  tenant assumption, stated honestly in code + CHANGELOG, not a fake crypto gate.

**Pending (do NOT rush):** the tamper EXTERNAL anchor B/C (task #24, needs infra decision);
ingest-path audit (task #49); intra-tenant per-agent auth (gap 13) would be the real fix
to let multi-agent tenants enable supersession safely.

## VERIFIED-REAL gaps (build these)
1. Gate is bypassable — a direct `sqlite3` INSERT skips the moat (library, no enforcement).
2. Receipts verify RESOLVABILITY, not content — no content hash; file edit silently invalidates.
3. Judge not recorded per decision — only `grounding_score`; no model/version/temp → silent provider drift.
4. ~~No tamper-evident chain~~ **PARTIAL (`5d8214d`)**: the audit trail is now hash-chained with `Memory.audit_verify()`/`audit_head()` (anchor-A: DETECTION + a head to archive off-box). A hash chain INSIDE the writable DB is still theater ON ITS OWN (owner rewrites+re-hashes) — the honest fix is archiving the head externally; a key OUTSIDE the DB + an EXTERNAL anchor (B/C) remains unbuilt. Shipped with that scope stated, not over-claimed.
5. No encryption at rest.
6. Scale unproven >3k facts; single-node SQLite; ~113 ms/write (CE) = swarm serialization point.
7. `source_trust` EXISTS but OFF by default (poisoning exposure out-of-box).
8. Moat evidence coverage-limited (only NUMERIC contradictions) + self-reported (no public harness).
9. Quarantine is SILENT (caller never told what was blocked) → memory-DoS "griefing" is possible.
10. Judge prompt-injection — cited SOURCE text is attacker-influenceable.
11. GDPR forget incomplete — physical bytes + EMBEDDINGS + WAL + backups; no crypto-shred; no export (Art.15/20).
12. Cross-fact contradiction NOT on the write path (gate is source⊢fact only). `ContradictionStore`+scan exist but unwired.
13. **NEW (cross-exam, verified): no access-control WITHIN a tenant** — `key = tenant`, no per-agent roles. Any "show the conflicting fact" visibility fix becomes an **extraction oracle** unless scoped.

## REFUTED by code (do NOT build)
- "Consolidation/dream/rollup mint facts that bypass the gate / poison-laundering" — FALSE. They operate on **skills/episodes/topic-clustering**, not fact-minting. (Both models repeated this; code refutes it.)
- "source_trust default-ON silently mass-quarantines new users" — FALSE. Unknown source gets neutral prior **0.5** > floor **0.25** → admitted. (The "measure cold-start first" caution is still sound.)
- Already-exists (round-1 false "missing"): consolidation, metrics/dashboard, decay + quarantine rehabilitation, source_trust/corroboration, per-tenant DB isolation, ContradictionStore.

## PHASE 0 — days ("nothing silent, nothing mislabeled"). START HERE.
0.1 **Adjudication receipt on every write** → return `{disposition, evidence_class, judge_id, score, margin}` to the caller. Quarantine becomes a visible verdict, not silent exclusion. (`verimem quarantine list/review/resolve`.)
0.2 **Judge-of-record**: persist `judge_backend, model, version, temperature, threshold, margin` on every gate decision (new `gate_decisions` row + FK from facts).
0.3 **Honest tier names + the DECISION MATH, not just the label.** Reserve `verified` for judge-attested + content-bound receipt. CE tier → `plausibility_gated`. Ship a **two-threshold band** on the CE: `≥τ_hi admit / ≤τ_lo reject / middle → review-quarantine (or escalate to llm if configured)`. **Renaming without the band still leaves the 7% poison — fix the math.** Expose `confidence_tier` on every recalled fact; `verimem stats` shows tier distribution.
0.4 **Content-bound receipts (start)**: hash the MINIMAL cited span (line range), store it; on audit/sweep (NOT per-recall — read-path I/O) compare → `stale` is a SEPARATE orthogonal signal, tier stays a static historical claim. (Full auto-repair/provisional-upgrade → Phase 1; honest effort = 2-3 weeks total, split it.)
0.5 **`source_trust` ON in observe/log-only first**, measure false-block on fresh tenants, THEN promote to gating.
0.6 README/brand: kill "100% certain / verified" for the default; publish the CE error band (7% ES + overlapping distributions). (Partly done this session; finish it.)

## PHASE 1 — weeks ("wire the moat")
1.1 Contradiction check ON the write path via **bi-temporal supersession**: same-source contradiction → **supersede** (tombstone old, keep valid-time) NOT quarantine-both; cross-source → quarantine the LOWER-tier one for review. Candidate recall needs an entity+predicate **pre-filter** and a **bounded k** against the 113 ms budget. Griefing detector (per-source contradiction-rate alert); quarantine-under-dispute EXEMPT from decay.
1.2 **Tamper-evidence done right**: coverage-audit (facts lacking a valid gate_decision → auto-quarantine + alert) with the decision signed by an **HMAC/Ed25519 key held OUTSIDE the DB**; daily external anchor (RFC-3161 TSA / transparency log / signed git remote). Chain-without-external-key/anchor = do not ship.
1.3 **Intra-tenant authz**: per-agent identity + RBAC on write/read/forget; scope the adjudication-receipt visibility so `conflict_reason` is NOT an extraction oracle.
1.4 Public reproduction harness + HARD contradiction classes (temporal / hedged / coreferential / conditional) + messy-query abstention benchmark + measured agent-level cost of over-abstention.

## PHASE 2 — weeks ("adversarial + compliance")
2.1 Judge prompt-injection hardening: pass judge only the **minimal evidence window**, structured/constrained output, delimiters as defense-in-depth, **multilingual** injection pre-scan (NOT English-only), dual-judge on flagged sources, injection red-team corpus. (CE-as-classifier is more injection-resistant than the LLM tier — honest selling point, but ONLY for source-verification, not contradiction-detection where an input is attacker-controlled.)
2.2 GDPR (unconditional, not "if EU"): crypto-shredding envelope (per-subject KEK → forget = destroy key). Honest open problems to state, not hide: ANN search over encrypted vectors (rebuild-on-forget), key custody NOT on the same FS as the DB, WAL entries written pre-shred, receipt `source_excerpt` + audit log are NEW PII copies that MUST be in the forget path. Art.15/20 export.
2.3 Encryption at rest (SQLCipher / per-tenant key). Honest scale bound published (~9 w/s per tenant; swarms parallelize across tenants; hot-tenant is the real limit); write-queue batching. Postgres → v0.8.

## Score trajectory
NOW 6/10 (external, verified). After Phase 0+1 → credible 8–8.5. 9+ needs
third-party-reproduced benchmarks, external anchoring in production, and a year of
measured judge drift.

## Discipline (unchanged)
TDD RED→GREEN; atomic commits (env-watcher reverts .py between tool calls);
ruff clean + full CI green before declaring; merge/tag/PyPI = Aurelio's call after
he tests. Branch `rename/verimem-total` (also carries the unfinished source-brand
rename debt — 225 "Engram/HippoAgent" in docstrings + the `HippoAgent` class →
`VerimemAgent` w/ alias; see spawn_task chip).

## 2026-07-20 (sera) — Ingest telemetry: decision record chiuso
Metodo: misura live → packet unico <3KB → GLM-5.2 + Kimi-K3 avversari in
parallelo (2 giri: design, poi diff) → implementazione TDD → retro-pulizia.
- **SHIPPED (commit 1eaa7ad + 157b2b3)**: admission gate ON by default
  (era opt-in dal 2026-06-04, mai flippato = classe "feature fatta ma mai
  puntata sulla realtà"); migration warning una-tantum robusto (post-route,
  latch-after-delivery, Lock, table-aware, env-garbage dedicato); cleanup
  retro referenze-aware ESEGUITO live: 284 moved / 7 skipped (target di
  supersession: mai spezzare catene) / 2347 contradictions orfane potate /
  FTS coerente. Backup: `~/.engram/backups/semantic-pre-retro-cleanup-2026-07-20.db`.
  Corpus live: curated_clean 84.4% → 89.8%; route_telemetry residui = 7 (tutti
  supersession-target, deliberati). 1 dangling superseded_by PRE-esistente
  (19985ba64bed → 1c6791113327, presente anche nel backup: non nostro).
- **REJECTED (2/2 reviewer, convergenti e indipendenti)**: classificatore
  content-based (JSON-shape) — falsi positivi silenziosi senza undo
  (`{"event_type":"dentist"}` = calendario, non exhaust); residuo misurato
  qui: 2/4790 = 0.04%. Candidato 0.8.0 SOLO con dati field (shadow-first,
  criterio congiunto provenance+soglia+type-check).
- **Nota onesta**: il "75% quarantined / 94% telemetria" pre-compact era il
  backup PRE-gate (traiettoria di un deployment non protetto — ora il claim
  di default vale anche per i clienti); il live era già protetto dal gate
  attivato via env/flag-file. I 508 quarantined del MOAT (10.6%) sono
  fase separata (evidence-anchor + riconciliazione, già pianificata).

### Correzione post-bench (stessa sera, giro 3 del metodo in 3)
Il bench esterno (`scripts/bench_admission_external_corpora.py`) ha FALSIFICATO
il flip del routing: su 2 corpus foreign-domain ~10% FP knowledge (upper bound,
CI95 4-23%, generatori avversari informati) e recall 0.0 strutturale (Kimi: per
chi non è noi la lista può solo far danni). Verdetto 2/2 convergente → SPLIT:
integrity ON default (0/500 FP misurato, con limite dichiarato: manca il bench
hostile-shaped-legitimate → roadmap), routing SOLO dichiarativo
(`ENGRAM_TELEMETRY_PREFIXES`, keyword `builtin` componibile) + origin-tag
`add(purpose="telemetry")` (GLM+Kimi convergenti: l'intento lo dichiara il
chiamante, mai il pattern). Il nostro deployment dichiara `builtin` via env.
Roadmap 0.8: bench integrity hostile-shaped (ticket con quote ostili, API docs
con markup, import bulk); dead-prefix lint + dry-run mode (Kimi); stesso audit
name-based sul READ-side denylist (stessa lista, stesso rischio FP sul recall
generico di corpus altrui); connector-tag MCP (purpose sul tool hippo_remember).

---

# 2026-07-21 — IL BLOCCO CENTRALE 0.7.0: false-positive del write-gate

Punto della situazione dopo la sessione notturna (mandato Aurelio: "verimem
funziona sotto ogni punto di vista" + "ridurre i falsi positivi a una soglia
accettabile"). Questa sezione è il **piano di record indelebile** per chiudere
la 0.7.0: obiettivi con criteri di FATTO numerici, non aggettivi.

## Cosa FUNZIONA, misurato più volte (non regredire)
- **Read-path**: 0 confabulazioni servite (e2e + bench confab, LLM reali);
  astensione 3/3 sull'impossibile; contraddizione presa. `answer()` 4/5.
- **Moat noise-rejection**: 60/60 (100%) del rumore foreign su HaluMem esterno.
- **Suite** 7632/0; multi-tenant isolato; concorrenza server-condiviso 262ms;
  ricevute + audit hash-chain (anchor-A).

## Il DIFETTO, localizzato con precisione (il lavoro della 0.7.0)
Il write-gate **sovra-respinge i fatti legittimi**. Tre sorgenti, misurate:
1. **L1 keyword**: 46% del corpus verticale (legale/clinico/ingegneria)
   quarantenato; opt-in advisory → 11% residuo.
2. **CE grounding**: al cut shippato 40, clean-admission 66.7% su HaluMem
   esterno (respinge 1/3 dei fatti puliti groundati) con noise-rej 100%.
3. **L3-semantic NLI**: falsi positivi su coppie di soggetto diverso
   (out-of-distribution); il pre-filtro coseno 0.7 è INERTE (595/595 passano).

Causa unificante: **il write-path tratta "non abbastanza provato" come
"malevolo"** — stessa quarantena per un fatto pulito sotto-soglia e per
un'injection. Il read-path ha già la cura giusta (astensione graduata); il
write-path deve fare lo stesso (ammissione graduata).

## FATTO in questa sessione (commit su `rename/verimem-total`)
- `ffbebb9` REVERT di una regressione critica (il flip L1 `d15e4ca`/Fable
  aveva spento l'anti-confab **di default** — 122 test rossi; suite ripristinata
  7632/0). Lezione: un flip di default sul gate senza suite intera è vietato.
- `bf35c9b` la modalità advisory L1 **lascia traccia** sulla ricevuta
  (`L1-domain-advisory-observe`) — critic 3-0-0.
- `912862f` **AMMISSIONE GRADUATA** (`ENGRAM_GRADED_ADMISSION`, default OFF):
  shortfall di grounding con source → ammesso low-confidence invece di
  quarantena; critic 2-1, il voto FAIL ha trovato una perdita-dati reale
  (write graded sbloccava la supersession) CURATA nello stesso commit.
- `bf5d322` decisione di design convergente (io + GLM indipendenti; Kimi giù).
- UD English-EWT gold scaricato + estrattore-soggetto tier-1 certificato
  (wrong 20.7% su testo wild, 0% sul corpus KB).

## OBIETTIVI 0.7.0 — criteri di FATTO numerici (Definition of Done)
La 0.7.0 è "funzionante" quando, su config di default e misurato:

| # | obiettivo | criterio di FATTO (numerico) |
|---|---|---|
| G1 | anti-confab non regredisce | confab servite = 0; banco caso A ≥ 8/8; injection ammesse = 0; Rossi-contraddizione catturata |
| G2 | FP verticale accettabile | wrong-block ≤ 3% sul corpus 35-fatti (oggi 11–46%) |
| G3 | FP grounding accettabile | clean-admission ≥ 90% CON noise-rejection ≥ 95% su HaluMem A/B (oggi 66.7/100) |
| G4 | FP semantico accettabile | banco semantic-conflict: caso F* (soggetto-diverso) → 0 FP TENENDO A ≥ 8/8, E = 0 |
| G5 | nessun FP nascosto | i FP NON migrano dalla scrittura alla risposta: A/B read-path con fatti low-conf → confab ancora 0 |
| G6 | tutto tracciato | ogni stand-down / ammissione-graduata sulla ricevuta + audit (fatto per L1 e CE) |

## SEQUENZA (giorni, observe-first, ogni passo con il suo cancello)
Ordine per guadagno-FP / rischio (deciso io + GLM):

- **P1 — CE graded admission** [codice FATTO, default OFF].
  Cancello per il flip di default: **A/B a 3 bracci** su HaluMem
  (OFF vs hard-reject vs graded) che dimostra G3 **e** G5 insieme
  (clean-admission sale, confab resta 0, il read-path pesa i low-conf).
  → poi flip default + critic + suite. *Prossimo passo immediato.*
- **P2 — L3 subject pre-filter** [prototipo misurato, NON cablato].
  Matcher **head-noun + modifier agreement** (non overlap-token), certificato
  su UD gold. Wiring observe-first dietro env, ricevuta `-observe`.
  Cancello: G4 sul banco + Wikidata mutation-eval (anti-circolarità).
- **P3 — L1 default** [advisory+marker esiste].
  Decisione default advisory-con-marker + `ENGRAM_L1_STRICT` per agenti +
  **suite anti-confab riscritta deliberatamente** (non zittita).
  Cancello: G1 + G2 su corpus verticale, critic, suite intera.
- **P4 — eval anti-circolarità permanente**: harness Wikidata (triple reali,
  mutazione di uno slot) come bench di regressione del conflict-gate, così G4
  non poggia mai più su etichette auto-prodotte.

## Vincoli di metodo (indelebili)
- Nessun flip di default sul gate senza: suite intera verde (exit da file, mai
  pipe) + A/B benchmark prima/dopo + critic pre-commit + `git stash list`
  controllato.
- Ogni numero di FP deve venire da un dataset ESTERNO o da gold di terzi, mai
  da un corpus etichettato da noi (lezione caso-F, 2026-07-21).
- Kimi+GLM avversari sul design; critic-orchestrator sul codice; ogni finding
  verificato sul codice prima di adottarlo.
- Push/merge/tag = decisione di Aurelio, dopo che testa.

---

## CORREZIONE 2026-07-21 (tarda notte) — G3 grounding: NON è un difetto del default

Misura pari-pari (stessi 50 fatti HaluMem identici, CE vs giudice claude,
`fact_grounding_score(None,·)` vs `fact_grounding_score(claude,·)`; verificato su
`grounding_gate.py:383`):

| config | clean-admission | noise-rejection |
|---|---|---|
| **CE (default prodotto, `Memory` senza llm)** | **97–100%** | 95–100% |
| giudice claude (opt-in `Memory(llm=…)`) | 66.7–76% | 100% |

Sui 6 fatti dove divergono: **CE 99.8–100** (entailment forte) **e giudice 0.0** —
è il *giudice* che sbaglia su clean chiaramente entailed, non il gate.

**Conseguenze (onestà A3, correzione di un mio claim precedente):**
- Il "33% di clean-rejection" attribuito al gate era la config **con giudice
  LLM**, non il default. Stesso errore di classe del flip L1: misurare l'asse
  sbagliato. Il bench `halumem_writepath_moat` inietta `llm=claude`, quindi
  misura il giudice, NON il CE che il prodotto usa di default.
- **G3 sul default è GIÀ soddisfatto dal CE** (≥90 clean / ≥95 noise). Declassato
  da difetto a proprietà verificata.
- La **graded admission** (`912862f`) resta shipped e utile *solo* per la config
  llm-judge; NON è più "il passo 1 a massimo guadagno sul default".
- **I FP veri della 0.7.0 restano DUE**: L1 keyword (46% verticale) e L3-NLI
  (soggetto-diverso). La priorità P1 diventa **P3 (L1)** e **P2 (L3)**; il
  grounding esce dalla lista dei difetti-default.
- Difetto secondario NUOVO (priorità bassa): il giudice claude dà 0.0 su clean
  entailed (6/25) — chi usa `Memory(llm=claude)` per il grounding ha un judge
  inaffidabile su una frazione. Da indagare quando si tocca la config llm.

**Priorità 0.7.0 aggiornata**: 1) L1 keyword advisory+marker (corpus verticale
46%→≤3%, G2/G1); 2) L3 subject pre-filter head-noun (G4); 3) harness Wikidata
(anti-circolarità permanente). Il grounding-CE è a posto sul default.

---

## 2026-07-22 — L1 precision leak chiuso + ricerca esterna 2026 (concatenamento)

### P3/L1 avanzato (commit `85bcc19`, branch, NON pushato)
Carve-out per-fatto `ENGRAM_L1_DOMAIN_PRECISION` (default OFF) cablato +
classificatore soggetto (`subject_extract`). Critic-orchestrator job `8f6d0ec5`
claim_holds 2-1: il voto FAIL (counterexample) ha provato che `SOFTWARE_HEADS`
era una denylist non-esaustiva — `'the algorithm was tested'` (self-claim
agente) leggeva domain e sopprimeva L1 con env ON. Verificato sul codice, chiuso
TDD (registro software/ML/web aggiunto, teste dual-use lasciate fuori di
proposito). **Misura onesta su `l1_business_corpus` (30 fatti reali): ENV OFF
86.7% FP → ENV ON 6.7%**; i 2 residui sono gap di estrazione soggetto (`Dr.`,
verbo `meets`) che falliscono SAFE (over-quarantena recuperabile). Blast 461
test verdi. **Tetto provato**: la classificazione lessicale del soggetto non può
disambiguare "self-claim agente" da "fatto dominio" dal solo testo (la stessa
frase è confab o legittima a seconda di CHI la scrive).

### Ricerca esterna 2026 (WebSearch/WebFetch live 2026-07-22)
Due paper convergono sulla NOSTRA tesi, pubblicati:
- **Eywa — Provenance-Grounded LTM** (arXiv 2605.30771): principio **"evidence
  before belief"** (evidenza-sorgente immutabile PRIMA del fatto canonico).
  LoCoMo 90.19, LongMemEval-S 88.2, BEAM 81.45.
- **Schema-Grounded Memory** (arXiv 2604.27906): write-path validation gate a 3
  stadi, "unknown ≠ not mentioned", **F1 97.10** vs competitor 80-87. Critica al
  cross-encoder: "euristica di scoring post-hoc" vs "contratti-schema".
- **HaluMem**: benchmark di allucinazione nelle OPERAZIONI di memoria (confab a
  ingest) — bersaglio esatto del nostro anti-confab.
- Competitor: Zep 63.8 / Mem0 49.0 (LongMemEval); EverOS LoCoMo 93.0.

**Nostro stato competitivo verificato (letto dai result JSON, non a memoria)**:
LoCoMo 0.813, LongMemEval recall@k 0.790, HaluMem-extraction F1 0.761 → **nel
gruppo sul retrieval, non in testa**. Vantaggio REALE sull'asse-promessa: mem0
`supported_pass_rate 0.25` (serve non-supportati 75%), niente contraddizione né
count-API; verimem gate-grounding + contraddizione + astensione + read-path 0
confab. *"Meglio di chiunque" è onesto sull'asse grounding/no-confab, NON sul
retrieval grezzo.*

## CANDIDATA 0.8.0 — spin-off VeriBench come benchmark standalone (proposta GLM 2026-07-22, valutata, NON eseguire in 0.7.0)

Proposta GLM (via Aurelio): scorporare `benchmark/veribench/` in un repo/org
dedicato (nome candidato "AdmitBench", da verificare disponibilità), verimem
come UN adapter alla pari di mem0, pip-installabile, README autonomo sulla
metrica NET(λ) = (correct − λ·wrong)/n. Premessa fattuale VERIFICATA:
`benchmark/veribench/` esiste (PREREGISTRATION.md, run_all.py, mem0_adapter.py,
competitors.py); preprint draft in docs/papers/veribench-preprint-DRAFT.md.

**ADOTTARE (regge):** (a) lo scorporo — convergente con la NOSTRA critica a
MemTensor/HaluMem ("leaderboard self-reported dal vendor del vincitore =
conflitto d'interesse", HALUMEM_OFFICIAL_PROTOCOL.md): vale anche per noi;
(b) NET(λ) come standard pubblico sposta la gara sull'asse dove siamo forti
(fabbricazione prezzata vs recall@k); (c) adapter + CONTRIBUTING per PR terzi.

**CORREGGERE (GLM sbaglia qui):** la neutralità NON si ottiene nascondendo il
vendor — un'org "terza" creata da noi coi numeri prodotti da noi è il conflitto
MemTensor con un livello di trucco in più, e se scoperto DISTRUGGE credibilità.
Cura vera: **trasparenza dichiarata** ("maintained by the Verimem team" nel
README, in chiaro) + **riproducibilità totale** (dati pubblici, seed fissi,
harness a un comando, adapter competitor fair) + puntare a run RIPRODOTTI DA
TERZI come criterio di successo. La differenza dai MemTensor = chiunque rifà i
numeri, non l'anonimato.

**Timing:** DOPO la 0.7.0 (mandato: prima verimem funziona sotto ogni punto di
vista). Prerequisiti: 0.7.0 chiusa; verifica nome (GitHub/arXiv/dominio);
decisione Aurelio su org + eventuale pubblicazione preprint.

---

### P0 (NUOVO, robusto) — evidence-before-belief per L1
La cura vera del leak L1 NON è una wordlist più grande né un flag di modo: è
**L1 defersce a grounding indipendente**. Un fatto con forma-da-self-claim ma
con sorgente INDIPENDENTE (≠ il fatto, che L4 conferma) → advisory/ammesso; un
claim auto-asserito (self-source o senza sorgente) → escala. Zero tetto
lessicale; convergente con Eywa + schema-grounded. **Sottigliezza da inventare**:
l'INDIPENDENZA della sorgente (self-paraphrase la aggira → serve un segnale di
provenienza, non solo `source != proposition`). Subsume la wordlist (fast-path).
Cancello: G1 + G2 su corpus verticale con sorgenti indipendenti, critic, suite.
