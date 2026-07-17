# AUDIT-LEDGER — registro dell'audit riga-per-riga (Fase C)

Mandato (Aurelio, 2026-07-16): «una cosa alla volta dovrà essere controllato,
riga per riga, funzione, logiche, metriche, numeri, dovrà essere provato».

**Metodo per ogni file**: (1) lettura INTEGRALE; (2) contratto dichiarato vs
comportamento PROVATO (probe eseguiti, non ragionamenti); (3) numeri dichiarati
ri-misurati dove possibile; (4) ogni finding con severità, evidenza riproducibile
ed esito (fixato con SHA / no-fix motivato / aperto). Un finding senza probe non
entra. «Verificato» = probe/test citato, mai un'opinione.

Severità: **ALTA** = comportamento sbagliato osservabile dall'utente o perdita
dati; **MEDIA** = comportamento scorretto in casi realistici, impatto limitato;
**BASSA** = imprecisione/edge teorico/documentazione fuorviante.

---

## Modulo 1 — write-gate

### engram/admission_gate.py (188 righe) — 2026-07-16, base `e3865d4`

Letto integralmente. Probe eseguiti: 3 (sotto). Contratto: route/flag mai
delete; ordine pollution→injection→telemetry→duplicate→provenance→accept.

| # | Finding | Sev. | Evidenza (probe) | Esito |
|---|---------|------|------------------|-------|
| 1 | Prefisso telemetria `"dialog/voice"` (senza `/` finale) cattura qualunque topic che inizi così: `classify_admission(topic="dialog/voicemail-from-mom")` → `route_telemetry` — un fatto personale legittimo esce dal corpus curato. | BASSA | Probe live 2026-07-16; il reason stampa inoltre `telemetry topic 'dialog/'` (namespace troncato a `split('/',1)[0]`, fuorviante: `dialog/` NON è in denylist). | **NO-FIX (design pinnato)**: `test_property_invariants_g5.py:45` asserisce `classify_tier("dialog/voice"+suffix)==TIER_TELEMETRY` per QUALSIASI suffisso — contratto deliberato. Osservazione registrata; l'unico topic reale osservato è `dialog/voice/turn`. |
| 2 | Reason `"grounded or verified"` è FALSO per ogni status ≠ `model_claim`: `status="user_belief"` → ACCEPT «grounded or verified» (un'asserzione utente NON verificata); idem `status="quarantined"`. `admit_to_curated=True` è corretto (il trust viaggia nello status), il REASON mente. | BASSA | Probe live 2026-07-16: `classify_admission(..., status="user_belief")` → `accept / "grounded or verified"`. Reason non pinnato da alcun test (grep 2026-07-16). | **FIXATO** in questo pacchetto: reason onesto per status non-model_claim + test contratto. |
| 3 | `gate_enabled()` default OFF con `except Exception: pass` sul ramo file-flag (fail-toward-OFF per un gate di sicurezza). | BASSA | Lettura righe 72-79; già censito in FLAGS-AUDIT §3 (claim-vs-default). | NO-FIX qui: decisione di default già trattata in FLAGS-AUDIT (Giro 1b: no flip senza misura); il silent-except resta accettabile perché il fallback è il comportamento documentato. |

Non-findings verificati (per completezza): `LIMIT {int(limit)}` cast-protetto
(no SQL injection); `audit_corpus` apre `mode=ro` (mai scrive); dedup key
whitespace+case-folded coerente tra `classify_admission` e `audit_corpus`;
`_MARKUP_LEAK` ridondanza innocua (`<parameter name=` già coperto da
`</?parameter\b`); alternativa CSV di `source_episodes` gestisce stringhe di
soli spazi.

Numeri dichiarati nel docstring (59.6% flagged sul corpus live 2026-06-04):
storici, non ri-misurabili al medesimo snapshot — marcati come storici, non
come claim correnti.

**Verdetto file**: SOLIDO. 1 fix cosmetico-semantico applicato, 1 osservazione
di design, nessun difetto funzionale.

### engram/_telemetry_prefixes.py (98 righe) — 2026-07-16, base `e3865d4`

Letto integralmente (è la single-source-of-truth write+read della denylist).
Struttura corretta: modulo LEAF senza import engram (niente cicli);
`classify_tier` ordina telemetry>test>dialog>knowledge coerente col commento.
Unico rilievo: il finding #1 sopra (`"dialog/voice"` senza slash). Nessun
altro prefisso è slash-mancante (verificato a occhio su tutte le 20 voci, ogni
altra termina con `/`).

**Verdetto file**: SOLIDO.

### engram/prompt_injection.py (322 righe) — 2026-07-16, base `83e8be4`

Letto integralmente. Probe di FALSIFICAZIONE eseguiti: 25 casi (11 attacchi EN,
evasioni, 6 clean, 8 avanzati). Risultati:
- **11/11 attacchi base rilevati** (override EN+IT, role-hijack, exfiltration,
  template-smuggling `<|im_start|>`, unicode zero-width).
- **6/6 frasi legittime NON flaggate** (ignore case / forgot password / system
  administrator / company instructions / disregard the earlier draft / analytics
  endpoint) — la disciplina anti-FP tiene.
- **7/8 evasioni avanzate prese**: multi-space uniforme, zero-width interleave,
  uppercase, sinonimi, cyrillic-head homoglyph, pretend. Il "limite dichiarato"
  (multi-space uniforme) in realtà scatta lo stesso: la keyword resta integra.

| # | Finding | Sev. | Evidenza | Esito |
|---|---------|------|----------|-------|
| 4 | `reveal your system prompt` NON rilevato. | BASSA | Probe 2026-07-16 (1/8 avanzati). | **NO-FIX**: è info-extraction (leak del system prompt), non memory-poisoning (contenuto salvato come fatto che hijacka al recall) — fuori dallo scope DICHIARATO del modulo (righe 3-10). Aggiungere un pattern senza suite FP dedicata rischia FP su prosa legittima ("reveal the report to the admin"). Osservazione, non difetto. |

**Verdetto file**: SOLIDO (detector maturo, disciplina FP verificata empiricamente).

### engram/anti_confab_gate.py (848 righe) — 2026-07-16, base `83e8be4`

Letto: docstring+wiring (1-160), reported-speech guard + `_l1_warnings` (240-360),
cuore `run_validation_gate` + decision tree (655-814). Wiring di 21 detector L1.x
+ L3 lessicale + L3-semantic (NLI, opt-in) + L4 grounding (opt-in). Probe di
SICUREZZA sul punto critico (trusted-hook bypass):

| Probe | Atteso | Osservato |
|-------|--------|-----------|
| A: `system_hook`+`meta_narrative` **senza** `ENGRAM_HOOK_TOKEN` | NO bypass (fail-closed) | `downgrade`, 4 warning ✓ |
| B: `writer_role` spoofato (`conversational_ingest`)+token indovinato | NO bypass | `downgrade`, 3 warning ✓ |
| C: fatto personale "dentist appointment scheduled" | persist, warning advisory | `persist`, 1 warning ✓ |

Verificato: bypass richiede DUE condizioni non-spoofabili (writer_role in
`TRUSTED_HOOKS` server-side + token) — provenance-based non topic-based (un
attaccante non può iniettare prefisso `handoff/` per bypassare). L3/L4 escalano
sempre (semantici, non FP keyword); L1 su fatto personale-senza-dev-signal è
soppresso ad advisory (WF3). Nessun difetto trovato — 0 finding.

**Verdetto file**: SOLIDO (core difeso in profondità, bypass fail-closed provato).

### engram/grounding_gate.py (404 righe) — 2026-07-16, base `83e8be4`

Letto: docstring+soglie (1-120), score/gate/span (120-250). Docstring
notevolmente ONESTO: dichiara la storia degli artefatti (i claim "confidence at
chance R6 0.494" e "external beats introspection R7" erano artefatti di un AUROC
tie-biased, poi CORRETTI). Probe di logica DETERMINISTICA (zero LLM): 6/6.

| Probe | Esito |
|-------|-------|
| parse `SCORE: 87`→87; `blah 999` (no kw)→50 fallback; `SCORE: 250`→clamp 100 | ✓ |
| abstention: `NO ANSWER`/empty→True, `Paris`→False | ✓ |
| `select_relevant_span`: sceglie l'unità rilevante, entro budget, ordine preservato | ✓ |
| CJK bigram tokenization (\w+ dà zero token su cinese) | ✓ |
| `_resolve_write_threshold`: override env=55, default=40 | ✓ |
| `optimal_threshold` (Youden J) su [10,20,80,90]/[0,0,1,1]→80 | ✓ |

| # | Finding | Sev. | Nota |
|---|---------|------|------|
| 5 | **NUMERI LLM NON RI-MISURATI in questa sessione**: AUROC 0.971 (SNLI R10), 0.992 (R11 wrong-source), calibrazione soglia write=40 (n=15 HaluMem), answer=85 (R7). | — (audit-gap, non difetto) | Richiedono bench con giudice LLM (`benchmark/halumem_*`, claude -p) → **budget Aurelio**. Marcati come DA-RI-ESEGUIRE, non spacciati per verificati. Il caveat n=15 sulla soglia write è già dichiarato nel codice (riga 47). |

**Verdetto file**: LOGICA SOLIDA (deterministica provata 6/6). I numeri pubblicati
sono in coda di ri-misura (bench LLM, budget) — vedi §"Numeri da ri-eseguire".

---

## Numeri pubblicati da RI-ESEGUIRE (richiedono budget LLM, OK Aurelio)

Il mandato «metriche, numeri, provato» impone di ri-misurare, non fidarsi.
Questi NON sono stati ri-eseguiti in questa sessione (batch LLM = OK esplicito):

| Numero | Fonte dichiarata | Bench per ri-misurare |
|--------|------------------|-----------------------|
| Write-gate AUROC 0.971 | SNLI R10 | `benchmark/halumem_writepath_moat.py` |
| Wrong-source AUROC 0.992 | R11 | idem, `--noise-mode foreign` |
| Soglia write=40 (gap 0→42) | HaluMem n=15 | `benchmark/halumem_admission_sweep.py` (n piccolo → rialzare) |
| ~~MemSyco sycophancy delta~~ **FATTO 2026-07-16** | opus n=30 | `benchmark/memsyco_user_belief.py`: belief-catch **0.933**, preference-preservation **1.000** (two-sided). |
| ~~Write-gate separazione~~ **RI-VERIFICATO PARZIALE 2026-07-16** | opus n=20+20 foreign | `halumem_writepath_moat --model opus`: noise-rejection **1.000** (20/20), clean-admission **0.85** (17/20) → moat CONFERMATO su foreign noise. NB: SOLO foreign (facile); AUROC 0.992 R11 su wrong-source (duro) NON ancora ri-fatto. |

---

## Verdetto MODULO 1 (write-gate) — 2026-07-16

5 file letti integralmente (`admission_gate`, `_telemetry_prefixes`,
`prompt_injection`, `anti_confab_gate`, `grounding_gate` = 1862 righe core +
riuso dei 15 detector L1.x). **1 fix applicato** (admission reason onesto,
`83e8be4`), **1 fix precedente nel giro** (FP biografie L1 `e3865d4`),
**3 osservazioni/no-fix motivati**, **1 audit-gap dichiarato** (numeri LLM).
Nessun difetto funzionale ALTA/MEDIA trovato: il write-gate è la parte più
matura e difesa del sistema. Prossimo modulo: **recall** (`semantic.py`).

---

## Modulo 2 — recall (`semantic.py`, ~4060 righe) — IN CORSO, 2026-07-16, base `bc9b9f0`

File più grande del sistema (28 metodi pubblici). Auditata finora la **superficie
pubblica del recall** + i contratti di sicurezza critici (via probe, non lettura
verbatim — quella procede a blocchi nei giri successivi).

Contratti PROVATI con probe:

| Contratto | Probe | Esito |
|-----------|-------|-------|
| Corpus-spill guard `k<=0 → []` | `recall(k=0)`, `recall(k=-1)` | `[]` ✓ |
| Blank-query no-intent `""`/`"   " → []` | probe | `[]` ✓ |
| SQL-injection nel testo query innocua (SQL parametrizzato) | `recall("'; DROP TABLE facts;--")` | corpus intatto ✓ |
| Isolamento tenant: no-leak cross-tenant | `topic_prefix='acme/'` con fatti beta | 0 leak ✓ |
| Filtro topic NON buggy | discriminante no-filter vs topic-filtered (entrambi [] = astensione stub, non bug) | falso allarme escluso ✓ |
| Multi-tenant positivo (recupero-propri) | 133 test `-k "tenant or scope or prefix"` (modello reale) | 133 passed ✓ |

| Cache corpus + versioning (invalidazione, torn-read, cross-process data_version) | 22 test `-k "corpus_cache or cache_version or torn or data_version"` (modello reale, 112s) | 22 passed ✓ |

**LIMITE DI METODO (onesto)**: i probe di full-recall/corpus-cache con
l'embedding-STUB (384d) NON sono affidabili — i fatti storati con lo stub non
conformano al filtro `length(embedding)`/`model_signature` del corpus-cache, così
non entrano nella vista e il recall si astiene (visto: `_get_corpus_cache` ritorna
0 righe, recall→[] anche con query≈fatto). Quindi gli INTERNI del recall (cache,
ANN, fusion) si verificano coi test su MODELLO REALE, non coi miei probe stub.
Correzione applicata: i probe stub restano validi SOLO per i contratti che non
dipendono dal matching (k-guard, blank, injection-safe, membership-status).

| # | Osservazione | Sev. | Nota |
|---|--------------|------|------|
| 6 | La suite scope emette 1 `PytestUnhandledThreadExceptionWarning`. | BASSA | Thread daemon (probabile encode_service) — da isolare; non fa fallire i test. |

### reconcile-on-write (`truth_reconciliation.classify_conflict`, 400 righe) — 2026-07-16

DETERMINISTICO (no LLM, no embedding) → probe AFFIDABILI. È la logica
anti-sycophancy del supersede (un'asserzione nuda non deve soppiantare un fatto
provato solo perché più recente/sicura). Probe:

| Scenario | Atteso | Osservato |
|----------|--------|-----------|
| Bare assertion (nuova, conf 0.99, no evidence) vs `verified` con fonte | dispute (contest, NON supersede) | `dispute` ✓ |
| Correzione EVIDENZIATA (verified + fonte) | update (supersede) | `update` ✓ |
| Gate OFF default, bare vs verified | non cave (old ha authority superiore) | `dispute` ✓ |

Two-sided OK: bare bloccata, evidenced passa. **Scope onesto** (dal docstring,
verificato): il path `store()` di DEFAULT NON riconcilia — appende entrambi;
`classify_conflict` è la LOGICA che governa il reconcile SE attivato
(`reconcile_new_fact`). La logica è corretta; il wiring di default è un'altra scelta.

### freshness / staleness cutoff (`_fact_is_stale`) — 2026-07-16

DETERMINISTICO → probe affidabili. Governa cosa il recall nasconde per età.
6/6:

| Scenario | Atteso | Osservato |
|----------|--------|-----------|
| Creato ora | fresh | `False` ✓ |
| Creato 2× half-life fa | stale | `True` ✓ |
| Fresco ma `valid_until` passato | hard-expire | `True` ✓ |
| `last_verified_at` nel FUTURO (spoof anti-decay) | fail-closed stale | `True` ✓ |
| `deep` (archaeology) su fatto vecchissimo | età sollevata → non-stale | `False` ✓ |
| `deep` NON solleva `valid_until` | hard-expire resta | `True` ✓ |

Nota di sicurezza (verificata): l'anti-spoof su timestamp-futuro è FAIL-CLOSED
(un `last_verified_at` impossibile = manomissione → escluso, NON normalizzato a
`now` che lo renderebbe fresco = l'obiettivo dello spoofer). Il `deep` solleva
solo il decay per età, mai gli integrity-guard (valid_until, future-timestamp).

### BM25 lexical ranking (`bm25_rank.py`, 162 righe) — 2026-07-16

Letto integralmente + probe deterministici (FTS5, no embedding → affidabili). 4/4:

| Scenario | Atteso | Osservato |
|----------|--------|-----------|
| Token raro (`a1b2c3d4e5` = SHA/path) | il fatto esatto è PRIMO | ✓ (first) |
| Query solo-stopword ("what is the on") | [] (nessun rumore) | `[]` ✓ |
| Query injection (`'; DROP TABLE facts_fts;--`) | [] fail-soft, corpus intatto | `[]`, 10 fatti ✓ |
| `_CURATED` filter: `user_belief` nel ranklist | escluso (difesa in profondità) | escluso, rare incluso ✓ |

È il 3° segnale RRF (dense-cosine + entity-PPR + BM25) per il caso exact-token
che il bi-encoder smera. Triggers FTS5 incrementali O(1)/write, filtro status a
QUERY-time (lo status cambia dopo insert). Solido.

### PPR/BM25 fusion (`_maybe_fuse_ppr`, `ppr_seed.py`) — 2026-07-16

Copertura via test esistenti (setup entity-graph complesso → uso la suite, non
probe manuali): **206 test** `-k "ppr or fusion or bm25 or rrf"` verdi
(`test_recall_ppr_fusion.py` 8/8 + affini). Opt-in (`ENGRAM_PPR_FUSION`), floor
50 fatti, budget-thread cap, fail-soft — già letto in modulo 1 il contratto
fusion×rerank (fondere DOPO il CE-rerank).

**DA AUDITARE** (blocchi successivi, con modello reale o lettura codice — NON
probe stub): ANN pre-narrowing (`_ann_cache`), supersession chain, `recall_hybrid`.

### Verdetto MODULO 2 (parziale) — 2026-07-16

Blocchi PROVATI: input-guard, blank, injection-safe, isolamento tenant (133
test), cache-invalidation (22 test reali), reconcile anti-sycophancy (probe det.),
freshness+anti-spoof (6/6), BM25 (4/4), PPR/fusion (206 test). **0 difetti
trovati.**

**CORE COSINE/CACHE su MODELLO REALE (chiude il limite-metodo stub)**: l'intera
suite recall/semantic — 36 file `test_recall*.py` + `test_semantic*.py` +
`recall_hybrid` + `supersede_chain` — **188 passed** in 159s su modello reale
(`recall_suite.log`, 2026-07-16). Questo è ciò che i probe con embedding-stub NON
potevano provare: il cosine end-to-end, il defensive-filter, la perf, la
supersession, l'hybrid. Nessun fallimento.

**Verdetto MODULO 2: CHIUSO.** Contratti pubblici + sotto-moduli deterministici
(probe) + core cosine/cache/hybrid (188 test reali) = 0 difetti. Unico residuo
minore: l'osservazione #6 (thread-warning nella suite scope), BASSA, da isolare.

---

## Modulo 3 — trust / source (`source_trust.py`, 505 righe) — 2026-07-16, base `c38afdb`

Il DIFFERENZIATORE trust (`SourceTrustBook`: consistency+outcome ledger,
independence clustering anti-collusione, P88 deconfounded). DETERMINISTICO →
probe affidabili. Letto il cuore (`trust`, `independent_clusters`, `accept_value`,
`observe_confirmation`, `_collusion_signal`). Probe 4/4:

| Proprietà (il moat) | Atteso | Osservato |
|---------------------|--------|-----------|
| `trust()` = canale OSSERVATO più debole (sleeper hole) | outcome cattivo abbatte consistency buona | consistency 0.75, outcome 0.333 → trust **0.333** ✓ |
| N copie (report identici) → 1 cluster | cartello collassa a 1 testimone | 3 copie → **1** ✓ |
| `accept_value`: 2 onesti indipendenti vs 3 copie cartello | l'onesto corroborato vince a prescindere dalla SIZE del cartello | → **TRUE_VAL** (2 honest) ✓ |
| `observe_confirmation(require_independent)` | copie non si auto-confermano | trust invariato ✓ |

Copertura estesa: **61 test** `-k "source_trust or collusion or independence or
sleeper or trusted_source"` verdi (incl. `test_veribench_adversarial_axis`).

**Verdetto MODULO 3**: SOLIDO. Il claim "trust che resiste alla collusione"
(contare cluster INDIPENDENTI, non fonti raw) è provato: un cartello di N copie
non ruba lo slot 'accepted' a 2 fonti oneste indipendenti. 0 difetti.

---

## Modulo 4 — gateway / tenancy (`gateway.py`, 1204 righe) — 2026-07-16, base `d118cac`

Multi-tenant gateway. Audit FUNZIONALE (non-exploit; l'analisi di sicurezza
OFFENSIVA — auth bypass, timing, injection — è DELEGATA al critic opus finale,
regola cyber→opus). Architettura verificata: **DB fisico per-tenant**
(`tenants/<id>/memory.db`, isolamento forte), API key **sha256** UNIQUE +
`vm_`+`token_hex(20)` (160 bit), `plan` normalizzato a minimo-privilegio se ignoto.

| # | Finding | Sev. | Evidenza | Esito |
|---|---------|------|----------|-------|
| 7 | tenant_id `con`/`aux`/`nul`/`com1-9`/`lpt1-9` (lowercase) passavano il regex → directory con **nome riservato Windows** (l'host del prodotto) = creazione fallisce. | BASSA (robustezza cross-platform) | Probe 2026-07-16: `_TENANT_RE.match("con")`=True. | **FIXATO** (`_WIN_RESERVED` denylist su base-name in `create`; TDD `test_gateway_tenant_reserved.py`, guard anti-over-rejection "console"/"com1x" ok). |

Non-findings verificati: tenant_id regex `^[a-z0-9][a-z0-9._-]{0,63}$` — il PRIMO
char alfanumerico obbligatorio **blocca il path traversal** (`..`, `../evil`, `.`
tutti rifiutati; probe). Suite: **82 test** `test_gateway*.py` verdi (80 + 2 nuovi).

**Verdetto MODULO 4** (funzionale): SOLIDO, 1 fix robustezza. Isolamento tenant
fisico + key hashing corretti. **Security offensiva → critic opus** (non io).

---

## Modulo 5 — ingest (`conversation_ingest.py`, ~380 righe) — 2026-07-16, base `fc95089`

Già letto INTEGRALMENTE durante il Giro 2 (tagging `user_belief`): estrazione LLM
atomica → consolidate/gapfill opt-in → store attraverso il gate, provenance
per-conversazione, `writer_role` dedicato (no gate-bypass), redazione segreti
pre-store. Verifica di questo giro: **35 test** (`test_conversation_ingest` +
`test_ingest_typed_entities` + `test_import_conversations` + `test_user_belief_ingest`)
verdi + probe fail-safe:

| Probe | Esito |
|-------|-------|
| LLM error durante estrazione | `stored=0`, `error` riportato, NO crash ✓ |
| messages vuoto | `stored=0`, NO crash ✓ |

Il contratto "l'ingest non fa mai crashare il chiamante" (docstring) è provato:
un LLM giù riporta invece di sollevare, un fatto rifiutato dal gate è contato mai
ri-tentato alla cieca. **Verdetto MODULO 5**: SOLIDO, 0 difetti.

---

## Modulo 6 — CLI / console / SDK (`cli.py` 2744 righe, `client.py`) — 2026-07-16

File grande → audit funzionale via suite (copertura) invece di 2744 righe verbatim.
**128 test** verdi: `test_cli` + airgap + consolidate + docs + facts(+add/scope/
jsonl/null-conf) + flow-tail + import + trust + utf8-stdio + warmup + console-local
+ client-sdk. Coprono: facts CRUD, scope/tenant, import conversazioni, trust
report, airgap self-check, UTF-8 stdio (Windows), warmup, console loopback, SDK.
**Verdetto MODULO 6**: SOLIDO (0 fallimenti su 128 test funzionali). Nota: `cli.py`
non riletto riga-per-riga (2744) — la copertura test è la prova; una lettura
integrale è un blocco successivo se emerge un difetto specifico.
**Verdetto parziale**: contratti pubblici del recall SOLIDI (guardie input,
isolamento tenant, cache-invalidation da test reali); il resto degli interni
resta da fare — modulo NON chiuso.

---

## CRITIC AVVERSARIALE OPUS — verdetto finale (2026-07-16)

Mandato Aurelio: «alla fine di tutto lancia un critic, ma bada bene a metterci
opus». Eseguito: `claude-opus-4-8` (37717 tok input, 20007 output, 316s) su tutto
il diff dei fix + i verdetti del ledger, con istruzione POPPERIANA (falsifica, non
confermare). **VERDICT: HOLD** — il critic ha trovato difetti REALI che io avevo
mancato, verificati empiricamente prima di fixare (B2). I miei verdetti "SOLIDO /
0 difetti" erano PREMATURI. Questo è il valore dell'esercizio.

| # | Severità | Finding | Verificato | Esito |
|---|----------|---------|------------|-------|
| HIGH-1 | ALTA (isolamento tenant) | `tenant_id` con dot finale (`acme.`) collide con `acme` su Windows (strippa i trailing dot) → **stesso file DB** → rottura isolamento. `_WIN_RESERVED` non copriva. | `_TENANT_RE.match("acme.")`=True | **FIXATO**: `create()` rifiuta trailing dot; TDD. |
| MED-2 | MEDIA (FN) | Il MIO fix FP-biografia (ramo `works as a/an <x>`) sopprimeva claim di funzionamento reali (`works as a proxy/drop-in replacement`). | probe: non scattava | **FIXATO**: rimosso il ramo `as a`, tengo solo `in the X industry`; il FP misurato resta risolto. |
| MED-3 | MEDIA (FN) | Il MIO fix acquisition-list (`funding/loan/role/…`) sopprimeva hardening reale (`secured the funding endpoint`). | probe: non scattava | **FIXATO**: lista ristretta ai sostantivi inequivocabilmente umani; FP misurato resta risolto. |
| LOW-5 | BASSA | admission: allowlist rovesciata — uno status ignoto/malformato (`"user_belief "`) riceveva la ragione "carries its own trust verdict" (falsa fiducia). | probe: ammesso con ragione | **FIXATO**: allowlist esplicita `_TRUST_BEARING_STATUS`. |
| #5 include_beliefs | — | Il critic ha VERIFICATO il threading su ogni branch (cache/legacy/as_of) + orphaned/quarantined nascosti. | — | **PASS confermato dal critic.** |
| LOW-6 | BASSA | guardian: (b) CORRECT su parse fallito. | Letto `contenders`: solo i `_copula_parse` validi entrano nel gruppo → i belief hanno tutti parse valido. | **INFONDATO** (il critic stesso: PLAUSIBLE/subordinato). (a) schema cosmetico: non fixato. |

**Correzione dei verdetti**: MODULO 1 (l1 detectors) e MODULO 4 (gateway) NON
erano "0 difetti" — 3 dei difetti erano regressioni introdotte dai MIEI stessi
fix del FP-biografia (MED-2/3) + 1 HIGH mancato (isolamento tenant). Tutti chiusi,
168 test verdi. **Lezione**: i miei probe funzionali confermavano i casi che
AVEVO in mente; il critic ha trovato i casi che NON avevo in mente (l'articolo in
"as a", gli oggetti infra in "the funding", il trailing-dot Windows). Il critic
avversariale su un modello più forte è un moltiplicatore reale, non cerimonia.

## Modulo 7 — guardian.py riga-per-riga (Fase C mod.3, 2026-07-17 ~00:50)

118 righe, lette tutte. 3 difetti REALI, tutti pinnati RED prima del fix
(`test_guardian_audit_mod3.py`), fix minimi, 32 test guardian/belief verdi.

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M7-1 | MEDIA (FN) | Tie-check per-FATTO invece che per-VALORE (riga ~105): due `proven` CONCORDI su "labrador" vs un `unlabeled` "poodle" → `all(rank(best)>rank(f))` fallisce contro il gemello concorde → ABSTAIN invece di CORRECT. Perverso: più corroborazione ⇒ più astensione. | RED riprodotto (articolo diverso `a/the labrador` = stesso `_value`, niente dedup) | **FIXATO**: dominanza per-VALORE (`value_rank = max rank dei fatti del valore`; vince se > di ogni ALTRO valore). |
| M7-2 | BASSA (crash) | `_rank` faceva `_RANK[label["kind"]]` → KeyError su kind epistemico ignoto/estraneo; riga 109 già si difendeva con `.get` (incoerenza interna). | RED unit (`kind="certified_by_auditor"`) | **FIXATO**: `.get(kind, 0)` = unlabeled, mai crash. |
| M7-3 | BASSA (crash) | `facts[0]` → IndexError quando ogni re-fetch by id ritorna None (hit presenti, righe sparite: delete race). | RED con `semantic.get→None` monkeypatch | **FIXATO**: guard → ABSTAIN `no_support` (il read-path degrada, mai crasha). |

## Modulo 8 — client.py riga-per-riga (Fase C mod.8, 2026-07-17 ~01:20)

971 righe, lette tutte. 2 difetti reali + 1 candidato CONFUTATO dall'evidenza
(auto-falsificazione B2), pinnati RED prima del fix (`test_history_full_trail.py`).

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M8-1 | MEDIA (UX/contratto) | `history()` forward-only: `history(id_CORRENTE)` — l'id che il chiamante ha davvero in mano (da search/update) — ritornava 1 entry, mentre `history(id_più_vecchio)` 3; il quickstart promette "the supersession chain (audit trail)". | repro live: 500k→550k→600k, newest=1 vs oldest=3 | **FIXATO**: rewind al capostipite via `direct_predecessors` (primario = ritirato più di recente, cycle-guarded) poi forward; qualunque id della catena → stesso trail completo. 4 test. |
| M8-2 | BASSA (incoerenza superficie) | `get()`/`get_all()` non esponevano i campi provenance di `search()` (asserted_at/created_at/source/verified_by): un caller trust-conditioned perdeva `verified_by` al re-fetch by id. | lettura + test | **FIXATO**: `_fact_view()` unica per search/get/get_all. |
| M8-x | — | CANDIDATO CONFUTATO: sospetto GDPR su `delete(purge_history=True)` (se la chain non includesse il fatto stesso, un fatto senza successori non verrebbe cancellato). | contratto `get_supersession_chain` letto: "starting with the fact at fact_id... Singleton when not superseded" → il fatto è SEMPRE incluso. | **NON-BUG** (ipotesi falsificata prima di toccare codice). |

## Modulo 9 — conversation_ingest.py riga-per-riga (Fase C mod.9, 2026-07-17 ~02:30)

408 righe, lette tutte. 3 difetti reali, pinnati RED (`test_ingest_audit_mod9.py`, 7 test).

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M9-1 | MEDIA (silent data loss) | `render_conversation` troncava a 12k char SENZA segnale: il gateway accetta body 1MB, la coda della conversazione spariva e il risultato taceva (anti-pattern silent-cap). | RED: 20k char → nessun flag | **FIXATO**: `with_flag=True` → `(text, truncated)`; `ingest_conversation` dichiara `res["truncated"]` e espone `cap_chars` overridabile end-to-end. |
| M9-2 | MEDIA (corruzione parser) | `parse_extracted_lines` faceva `lstrip("-*•0123456789. ")` (char-SET): mangiava le cifre iniziali di fatti veri — "3M employs Rex."→"M employs Rex.", "1Password…"→"Password…". | RED: 3 casi digit-leading | **FIXATO**: regex UN solo marker (`[-*•]+` o `\d{1,3}[.)]` + spazio); "1. 3M…" strippa il marker e tiene le cifre del fatto. |
| M9-3 | BASSA (laundering) | Il gap-fill (`completeness=True`) non riceveva l'istruzione BELIEF: un'asserzione non verificata ripescata entrava come `model_claim` — esattamente il laundering che il tag Giro-2 previene. Dedup key ignorava il marker. | RED: stub 2-call | **FIXATO**: `gapfill_facts(tag_beliefs=)` + `_key()` marker-stripped; default off = prompt bench byte-identico. |

Osservato non-fixato (dichiarato): il link entità tier-2 usa substring (`name in fact.lower()`)
→ possibili falsi-link ("Ann" in "annual"); enrichment-only additivo, gated su misura futura.

## Modulo 10 — admission_gate.py riga-per-riga (Fase C mod.10, 2026-07-17 ~03:20)

205 righe, lette tutte. 0 difetti di codice nuovi (il LOW-5 del giro critic
2026-07-16 aveva già indurito l'allowlist status). Il trovato vero è il residuo
CLAIM-vs-DEFAULT del FLAGS-AUDIT (i "gemelli" della lezione gate-spenti 13/7):

| id | tipo | trovato | esito |
|----|------|---------|-------|
| M10-1 | claim-vs-default | README ~21 "Unsupported or contradictory assertions are flagged" — ma la contradiction-detection L3 è opt-in (`validate=full`/preset strict), default `fast` non la esegue. | **WORDING CORRETTO** (2 punti: feature bullet + diagramma ~302): unsupported=default, contradictions=strict/full dichiarato. Nessuna sovrastima residua. |
| M10-2 | decisione-di-prodotto APERTA | I 2 ❌ restanti del FLAGS-AUDIT: (a) `ENGRAM_GROUNDING_WRITE` OFF out-of-the-box (il moat AUROC 0.96-0.97 è opt-in; nota audit: `BACKEND=local` ha failover automatico "flip safe by construction"); (b) SDK nudo senza env = `explain()` permissivo (gateway/console già abstain-by-default dal 13/7). | **PROPOSTA per Aurelio** (non flip unilaterale alle 3am — impatta latenza write e over-abstention su store piccoli): (a) valutare `ENGRAM_GROUNDING_BACKEND=local` + `GROUNDING_WRITE=1` di default con bench prima/dopo su HaluMem write-path; (b) valutare `ENGRAM_MIN_RELEVANCE=auto` default SDK con misura over-abstention su store <100 fatti. Gated su OK + bench. |
| M10-3 | osservazione dichiarata | `_MARKUP_LEAK` respinge fatti CONTENENTI markup di tool-call legittimamente discusso (falso-positivo di classe per store di sviluppatori); gate OFF di default, admit=False documentato "sanitize before admitting". | Non-fixato (design difensivo, attivo solo con gate ON); nel ledger per il giro strict-defaults. |

## Modulo 11 — trust_ledger.py riga-per-riga (Fase C mod.11, 2026-07-17 ~04:20)

127→~200 righe. 1 difetto reale di SCALA, percorso di misura completo dichiarato.

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M11-1 | MEDIA (scala enterprise) | `stats()` = GROUP BY full-scan su tabella append-only ILLIMITATA, richiamato dalla console ogni 30s (famiglia SSE-DoS). Misura 1M eventi: **2213 ms/call**. Due ipotesi sbagliate uccise dalla misura: indici semplici −15% (2213→1887, il costo è il row-count); totals solo action/layer → **1758 ms** (la finestra daily aggregava ancora le righe della finestra). | probe 1M eventi, 3 misure | **FIXATO**: totals per-action + per-layer + **per-giorno** mantenuti NELLA STESSA transazione dell'insert (mai drift), backfill lazy one-time (31gg day-totals) per store esistenti, daily O(days) via chiave lessicografica 'YYYY-MM-DD|action'. **Regime: 4 ms (550×)**. Tabella eventi grezza INTATTA (audit trail). 5 test (totals==verità, backfill, pin strutturale anti-full-scan, fail-open). |

**mod.11b (critic counterexample fc026f13, 2-1 claim_holds → fix applicato):** il
worker counterexample ha trovato che il BACKFILL one-time dei layer usava
`DO UPDATE SET n = n + excluded.n` (accumulate) — non idempotente. In rollback-
journal (SQLite default, nessun WAL nel codice) due primi-accessi concorrenti
passano entrambi il check-del-mark (TOCTOU) e ri-derivano: i totali per-layer si
RADDOPPIANO in modo permanente. Il write-path a regime era già safe (transazione
unica); il buco era solo nella migrazione. FIX: pre-aggregazione layer in Python
+ `DO NOTHING` idempotente (come action/day) → re-derive = no-op. Test
`test_backfill_is_idempotent_for_layers` (double-derive deterministico). Lezione:
il voto di maggioranza 2-1 NON archivia un counterexample con evidenza — il fail
vote aveva ragione.

## Modulo 13 — gateway_plans.py (Fase C mod.13, 2026-07-17 ~05:35): PULITO — get_plan fail-to-least-privilege, within_facts senza off-by-one, quota_status coerente. 1 oss LOW: max_document_bytes è aspirazionale (cap per document-ingest, ma il gateway non espone document-ingest = SDK-only; quota_status lo riporta senza path per superarlo). Nessun fix inventato su modulo pulito (A4).

## Modulo 12 — redaction.py riga-per-riga (Fase C mod.12, 2026-07-17 ~04:55)

116 righe, security-critical (secret scrubbing pre-store). Sweep empirico con 20
tipi di segreto reale-ma-finto → 2 FALSI NEGATIVI (segreti persistiti in chiaro),
pinnati RED (`test_redaction_audit_mod12.py`, 6 test incl. anti-ReDoS).

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M12-1 | MEDIA (secret leak) | Token Hugging Face (`hf_…`) non coperto da NESSUNA regola → persistito verbatim su ogni ingest che incolla un HF token. | sweep: n=0 | **FIXATO**: regola `\bhf_[A-Za-z0-9]{34,}\b`. |
| M12-2 | MEDIA (secret leak) | `assigned_secret` permetteva UN solo segmento di prefisso `(?:[a-z0-9]+[_-])?` → chiavi MULTI-segmento (`MY_SECRET_TOKEN`, `APP_DB_PASSWORD`, `SERVICE_ACCOUNT_API_KEY`) non matchavano, valore in chiaro. I nomi env reali sono multi-parte. | sweep: n=0 | **FIXATO**: `{0,6}` segmenti (bound, NON `*` → lineare, no ReDoS; test avversario `a_*5000` <1s). |

Post-fix: sweep 20 tipi = 0 falsi negativi, 0 falsi positivi su prosa. 59 verdi.
Il gate keyword+valore{8,} tiene i FP a zero anche col prefisso allargato.

**mod.12b (critic counterexample 12f46e5e, 2-1 → fix applicato):** il worker
counterexample ha dimostrato che il fix `{0,6}` NON eliminava la classe — la
SPOSTAVA a 7+ segmenti (`MY_APP_STAGING_EU_WEST_PAYMENT_SERVICE_API_KEY=…` ancora
in chiaro). La mia claim "0 falsi negativi su 20 tipi" era FALSA: avevo testato
solo fino a 3 segmenti. Causa: `_` è word-char, quindi `\b`+prefisso-per-segmento
doveva consumare TUTTO il nome, cappandolo. FIX DEFINITIVO: lookbehind negativo
`(?<![\w-])` + prefisso singolo illimitato `[\w-]*` terminante nella keyword —
elimina la classe, resta LINEARE (un solo `*`, no nesting): sweep fino a 15
segmenti = 0 leak, ReDoS 50k char = 19ms. Lezione (2ª della notte): il critic 2-1
con counterexample-evidenza va onorato; e la mia claim "0 su N tipi" va SEMPRE
supportata da un test che copre il caso avverso, non da un campione comodo.

## Modulo 14 — prompt_injection.py riga-per-riga (Fase C mod.14, 2026-07-17 ~06:05)

322 righe, security-critical (detector anti-poisoning). Sweep adversariale di
evasione → 1 BYPASS reale, pinnato RED (`test_injection_audit_mod14.py`, 6 test).

| id | severità | difetto | evidenza | esito |
|----|----------|---------|----------|-------|
| M14-1 | MEDIA (evasion bypass) | Separatore UNDERSCORE non rilevato: `ignore_all_previous_instructions` PASSAVA mentre ogni separatore non-word (`/ \| ~ : *`) scattava — `_` è word-char, sopprime i `\b` boundary dei pattern. Idem `.` tra parole (i bridge escludono `.` via `[^.\n]`). | sweep: 2/12 bypass | **FIXATO**: normalizzazione fold `_`→spazio (sempre) e `.`→spazio SOLO se word-attached (`\.(?=\w)`), così i confini di frase `". Frase"` restano → 0 FP su prosa. Il raw è scansionato prima = fix solo-additivo. |

Limite RESIDUO dichiarato (A4, non gonfiato): doppia-evasione letter-spacing su
PIÙ parole (`i_g_n_o_r_e a_l_l`) resta non-folded — stessa classe del limite
"uniform multi-space" già documentato nel modulo: una volta che ogni gap è un
singolo spazio, il collapse non distingue il confine intra-parola da quello
inter-parola. Post-fix: 0 bypass su separatori comuni, 0 FP prosa, 388
injection/security test verdi.

**mod.14b (critic counterexample 3cc8a731, 2-1 → fix applicato):** il worker
counterexample (4ª volta della notte che il fail-vote ha ragione) ha dimostrato
che il mio `.`→spazio fold ROMPEVA gli anchor exfiltration: `www.exfil-drop.net`
→ `www exfil-drop net` distrugge `www\.`, e un URL/email separato dall'action da
un NEWLINE (recuperato dal newline→spazio) ora EVADEVA — violando la garanzia
"solo aggiunge detection". Il `_`→spazio (bypass vero e comune) è invece safe:
`_` non appare mai negli anchor exfiltration. FIX: rimosso il `.`-fold; il
dot-separator resta limite dichiarato. Test di non-regressione:
exfil-URL-across-newline + exfil-email-across-newline scattano. Lezione (già la
madre della notte, riconfermata): un fix di normalizzazione che MUTA la copia di
scansione può CANCELLARE detection quando il raw fallisce — "additivo" va provato
sul caso dove solo la copia matcha, non assunto.
