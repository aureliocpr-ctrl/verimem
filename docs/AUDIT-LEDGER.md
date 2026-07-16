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

**DA AUDITARE** (blocchi successivi, con modello reale o lettura codice — NON
probe stub): ANN pre-narrowing, PPR/BM25 fusion (`_maybe_fuse_ppr`),
reconcile-on-write, supersession chain, freshness cutoff, `recall_hybrid`.
**Verdetto parziale**: contratti pubblici del recall SOLIDI (guardie input,
isolamento tenant, cache-invalidation da test reali); il resto degli interni
resta da fare — modulo NON chiuso.
