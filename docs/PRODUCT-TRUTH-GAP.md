# PRODUCT-TRUTH-GAP — diventare il prodotto che dichiariamo

Mandato Aurelio (2026-07-16): «dobbiamo diventare il prodotto che dichiariamo…
la memoria che non si inquina, non confabula, non hallucina, non fa sycophancy…
apri le vedute, considera la superficie, concatena tutto». Questo registro tiene
i CLAIM del prodotto accanto ai NUMERI REALI e ai GAP, con la leva per chiuderli.
Regola: nessun claim sul sito senza un numero riproducibile qui accanto.

## I 4 assi del trust — stato REALE (non aspirazionale)

| Asse | Claim | Numero reale (fonte) | Verdetto | Leva per chiudere il gap |
|------|-------|----------------------|----------|--------------------------|
| **non si inquina** | admission gate tiene fuori telemetria/dup/injection | write-gate separazione noise-reject **1.0** / clean-admit **0.85** (opus foreign, 2026-07-16); 44% quarantena = curation che funziona (LAUNCH_READINESS) | ✅ SOLIDO | mantenere; sweep injection multilingua |
| **non confabula** | L1 anti-confab (21 detector) + grounding | write-gate AUROC **0.971** (SNLI R10, DA ri-fare full); L1 FP-biografia 2.7%→0% | ✅ forte (numero full da ri-eseguire) | ri-eseguire R10/R11 su opus |
| **non hallucina** | «non hallucina» | **Hallucination 0.167** (LongMemEval strict, «moderate, NOT very-low»); QA-Correct **0.433**; recall@30 **0.96** | ⚠️ **GAP REALE** — trova il fatto ma l'answerer cade sui distrattori | **provenance-conditioned answering** (proof end-to-end `grounding_conditioned_qa_real.py`: condizionare sul grounding uccide l'hallucination) — NON shippato nel prodotto |
| **non sycophancy** | anti-sycophancy sul write-path | belief-catch **0.933** / preference-preservation **1.000** (MemSyco opus n=30); reconcile bare→dispute | ✅ MISURATO | estendere multi-turn (`external_sycophancy_multiturn`) |

## L'anello mancante che CONCATENA tutto (il moonshot già proof-ato)

SCOPERTA EMPIRICA 2026-07-16 (A2): il `grounding_score` memorizzato è **0%**
popolato sul corpus reale (write-grounding opt-in, mai attivo) e lo `status` è
uniforme nel flusso reale → condizionare sul segnale MEMORIZZATO era su sabbia.
L'asse madre si divide in DUE pezzi:

**PEZZO 1 — SHIPPATO (`4074fd0`/`a1aa1cc`)**: `Memory.answer(query, llm, k)` =
grounding-verified answering. L'LLM risponde dai fatti, poi il **CE locale
(no LLM)** verifica che la risposta sia entailed da un fatto recuperato; se no →
astiene (NO ANSWER). Probe: il CE separa 91-94 (vero) vs 1-3 (inventato). TDD 5/5.
SCOPE ONESTO (pinnato come test): becca l'hallucination-OLTRE-i-fatti (il modello
inventa), NON il distrattore-IN-memoria (un fatto sbagliato già stored: il CE lo
trova come supporto, verificato — serve "Rex is a labrador" con support 92).

**PEZZO 2 — APERTO (il grosso del gap 0.167)**: separare vero da distrattore IN
memoria. BENCHMARKS: il gap è dominato dai *distractor facts*. Leva: **popolare
`grounding_score` al write-time col CE LOCALE** (`try_local_score(source_dialogo,
fatto_estratto)`, no LLM, economico — l'ingest HA il source) → ogni fatto porta il
suo grounding → l'answer scarta i distrattori mal-fondati. Concatena
grounding-gate + reconcile/supersession + trust(vivarium). Questo rende
"non hallucina" VERO end-to-end. Prossimo passo dell'asse madre.

## Isolamento multi-tenant — adversarial opus 2026-07-16: **PASS core + 6 da chiudere**

Invariante core REGGE (DB-per-tenant, tenant SOLO da `keys.resolve`, nessun
endpoint prende il tenant da input; trailing-dot/windows-reserved già fixati).
Nessun HIGH cross-tenant. Difetti da chiudere prima dell'online:
1. MED — personal-mode `Host` header spoofabile da `curl` se bind ≠ loopback (il commento sovrastima la difesa).
2. MED — `local_tenant` provisionabile come tenant normale → risolve sulla memoria personale dell'operatore. Fix: rifiutare `tenant_id == local_tenant`.
3. MED — SSE `/v1/events/flow` rilegge tutto `events.jsonl` ogni 0.5s/conn → DoS cross-tenant. Fix: incrementale + cap per-chiave.
4. MED — quota TOCTOU (evasione cap fatti in concorrenza, intra-tenant).
5. LOW — `_TENANT_RE` usa `$` (accetta trailing `\n`) invece di `\Z`.
6. LOW — parsing Host rompe IPv6 loopback senza porta (fail-closed).

## GOAL (concatenato, misurabile) — ordine di attacco

1. **"Non hallucina" VERO**: shippare provenance-conditioned answering nel
   prodotto (usa grounding_score+status+trust già esposti) → misurare
   Hallucination prima/dopo su LongMemEval/HaluMem reale. Target: H ↓ senza
   crollo di Correct. [asse madre — concatena grounding+trust+belief]
2. **Isolamento tenant online-ready**: chiudere i 6 difetti (2+5 subito, 1+3+4
   poi) con test adversariali che li pinnano.
3. **Numeri moat freschi**: ri-eseguire R10/R11 write-gate AUROC full su opus.
4. **Sito allineato**: ogni claim = numero riproducibile qui. Nessuna eccezione.

Fonti lab da concatenare: cortex (leggi verificate sul futuro, TDD-legge),
vivarium (independence/anti-collusione P66/P88, già in `source_trust`).
