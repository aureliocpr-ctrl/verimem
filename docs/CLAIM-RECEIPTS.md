# CLAIM-RECEIPTS — ogni claim pubblico ha una ricevuta (o non lo diciamo)

Il prodotto è ONLINE. Regola dura (Aurelio 2026-07-16): nessun claim sul
README/sito senza una RICEVUTA verificabile (numero misurato + path + SHA/test).
Un claim senza ricevuta o con ricevuta stantia = **fuffa da correggere subito**.

Stato: ✅ VERO (ricevuta fresca) · 🔬 DA-RI-ESEGUIRE (ricevuta esiste ma non
ri-verificata oggi) · ⚠️ SOVRASTIMATO (wording da correggere) · ❌ FALSO (rimuovi).

| # | Claim (README) | Stato | Ricevuta |
|---|----------------|-------|----------|
| 1 | «anti-confabulation gate» sui write | ✅ | L1 21 detector; FP-biografia 2.7%→0% (`e3865d4`, `test_l1_biography_fp` 17); AUDIT-LEDGER mod.1 |
| 2 | «stored with their sources» | ✅ | provenance per-conversazione (`conversation_ingest.py`, `conversation:<id>`) |
| 3 | «supersession, never silent overwrites» | ✅ | `classify_conflict` bare→dispute/evidenced→update (probe det. + 61 test) |
| 4 | «answered with citations — or an abstention» | ⚠️→✅ | `Memory.answer` shippato (`4074fd0`), ritorna `support_fact`+astiene. LIMITE pinnato: non becca il distrattore-in-memoria (`a1aa1cc`). Il claim regge SOLO se il wording dice "verified against retrieved facts", non "no hallucination". |
| 5 | «anti-sycophancy on the write path» | ✅ | MemSyco belief-catch **0.933**/preserve **1.000** opus n=30 (`memsyco_user_belief.py`) |
| 6 | «cartel 0.90→0.20, honest 0.95, HaluEval 3/3 seeds» | ✅ CONFERMATO ALLA CIFRA | `source_trust_realcorpus --seed 11` (HaluEval REALE) ri-eseguito 2026-07-16 (`source_trust_realcorpus_seed11_2026-07-16.json`): cartel_consistency **0.9 (naive) → 0.2 (deconfounded)**, honest **0.9524** = ESATTAMENTE il claim 0.90→0.20/0.95. Verdict pre-registrato C1 (independence denies cartel) + C2 (no inversion) = **PASS**. NB: riprodotto seed 11 (1 dei 3 "seeds"); deterministico. |
| 7 | «Trust odometer `m.trust_stats()`» | ✅ | verificato live (SDK) + **console /ui viva 2026-07-16**: server reale acceso, 1 write vero → odometro "1 screened / 1 admitted / 0 quarantined" letto dalla pagina. NB fix `a2efe40` nello stesso giro: personal mode ora UNCAPPED (prima 402 sul proprio store >1000 fatti — trovato dall'e2e live, non dai test). |
| 8 | «read-path guardian ACCEPT/CORRECT/ABSTAIN» | ✅ (era ⚠️ sovrastimato) | Il critic mod.3 (2026-07-17, caller-verification) ha trovato che `correct_read` aveva **ZERO caller di produzione** — "read-path" era SDK/test/doc soltanto. FIX: wired `GET /v1/correct` sul gateway (deterministico, no LLM, anche console personale) + evento flow `kind=correct`. + audit riga-per-riga mod.7: 3 difetti reali fixati TDD (dominanza per-VALORE — più corroborazione produceva PIÙ astensione —, 2 crash guards; `5b4249e`, critic 2-1 claim_holds con RED→GREEN verificato dal falsification worker). 32+3 test verdi. |
| 9 | «air-gapped `verimem airgap` zero-egress» | ✅ | airgap urlsplit-exact (`4015241`), `test_cli_airgap` |
| 10 | «127.0.0.1 only, Host-header checked vs DNS rebinding» | ✅ (corretto) | Wording README corretto 2026-07-16: il bind loopback è la difesa PRIMARIA, il Host-check è secondo layer anti browser-rebinding, e dichiarato esplicitamente che `curl` può spoofare il Host → mai esporre personal-mode su bind non-loopback. Non sovrastima più. |
| 11 | «each tenant an isolated store, derived from API key» | ✅ core + difetti chiusi + **LIVE** | adversarial opus: **PASS** sull'invariante (DB-per-tenant, tenant da key). I 6 difetti MED/LOW sono ora **6/6 gestiti**: local_tenant collision (`fca0e15`), `_TENANT_RE` trailing-dot (`\Z`), IPv6 Host parse (`c246522`) — chiusi TDD; **SSE `/v1/events/flow` DoS** → tail incrementale a byte-offset (`f221e87`, 7 test); **quota TOCTOU** → reserve-counter atomico (`3761b69`, 6 test incl. 40-thread race); host-spoofing via `curl` = mitigato dal bind loopback (scelta di design documentata, #10). Nessun HIGH residuo. **E2E LIVE 2026-07-17** (`gateway serve` reale, HTTP vero): 12/12 — isolamento cross-tenant (il segreto di acme invisibile a globex), 401 su no-key/key-inventata/admin-senza-key, quota free 1000, `/v1/correct` e `/v1/answer`(400) per-tenant, **rate-limit del piano ESATTO alla cifra: 70 richieste → 60×200 + 10×429 con `Retry-After`**. |
| 12 | «recall 1.3 ms @ 1M facts (ANN) vs 81 ms brute» | ✅ (corretto) | Numero REALE (`ann_scale_bench_repro.json`: 1.306/81.424 ms). 2 difetti di RICEVUTA chiusi 2026-07-16: (a) `SCALE.md` ora HA la tabella ANN 1M (prima solo brute 300k → "see SCALE.md" era monco); (b) recall ANN 0.844 (random worst-case) + OOM-riproducibilità + opt-in ora DICHIARATI in README+SCALE.md. Recheck oggi: 100k confermato 7.8×/1.12ms; 500k/1M OOM sulla mia macchina (serve ~32GB). |
| 13 | write-gate AUROC 0.96–0.97 (moat anti-confab) | ✅ | RI-MISURATO 2026-07-16 col modello corrente: R10 SNLI n=150 seed 0 **AUROC 0.963** sonnet-5 (`fact_grounding_r10_sonnet5_2026-07-16.json`; entail 85.2 / neutral 28.5 / contra 6.4, Youden 55) — nella banda dello storico (0.971 R10 sonnet-4, 0.974 pooled multi-model, 0.992 R11). + same-topic gate-discrimination fresca **1.0/1.0** (`writepath_moat_sametopic_opus_2026-07-16.json`). README aggiornato al range onesto "0.96–0.97 across models/seeds". |
| 14 | «conflicting well-grounded memories resolved by provenance, or honest abstention» (answer trust-conditioned) | ✅ nuovo | MISURATO PRIMA, WIRED DOPO (2026-07-16, `wellgrounded_distractor_bench.py` sonnet-5): 12 casi CASO-B (distrattore BEN-groundato, gate 76–100 su entrambi i lati → il grounding NON può separare) — flat C=0.42/H=0.58; **answer() v1 C=0.17/H=0.33/O=0.50** (limite pinnato quantificato: `ce_served≈97` sul distrattore); **trust-conditioned C=0.92/H=0.08**, astiene **2/2** sui conflitti stesso-metadato (contatore v1 del bench diceva "fabricated": era un bug del CONTATORE — le pred reali erano `NO ANSWER` secco; fixato, la regola verbosa di tie regrediva ed è stata scartata). Wired in `Memory.answer(trust_conditioning=True)` default ON (`client.py`, 5 test + non-regressione 33). RESIDUO ONESTO pinnato: un distrattore i cui metadati DOMINANO (più recente E verified ma falso) resta indistinguibile senza audit. 1 fail residuo su 12 (b3_version). |

## Azioni immediate (perché è online)
1. Ri-eseguire i 🔬 numerici (12 in corso; poi 6, 13) — budget opus aperto.
2. Correggere i ⚠️ #4 e #10 nel README (wording che non sovrastima).
3. Chiudere i 6 difetti tenant prima di rafforzare il claim #11 "enterprise".
4. Verificare #7 (`trust_stats` esiste).

Nessun ❌ FALSO trovato finora — ma 2 ⚠️ (sovrastima) e 5 🔬 (ricevute da rinfrescare).
Il claim non si dice finché la cella non è ✅.
