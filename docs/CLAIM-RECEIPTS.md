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
| 6 | «cartel 0.90→0.20, honest 0.95, HaluEval 3/3 seeds» | 🔬 | `independence_validation.py`/`source_trust_realcorpus.py` — ricevuta esiste, DA ri-eseguire oggi |
| 7 | «Trust odometer `m.trust_stats()`» | 🔬 | verificare che il metodo esista e ritorni i contatori |
| 8 | «read-path guardian ACCEPT/CORRECT/ABSTAIN» | ✅ | `guardian.correct_read` 8/8 test (belief-aware `48ea661`) |
| 9 | «air-gapped `verimem airgap` zero-egress» | ✅ | airgap urlsplit-exact (`4015241`), `test_cli_airgap` |
| 10 | «127.0.0.1 only, Host-header checked vs DNS rebinding» | ⚠️ | VERO per il default loopback + browser-rebinding; ma opus tenant-pass: `Host: localhost` è spoofabile da `curl` se il gateway è bindato ≠ loopback → il wording NON deve implicare difesa contro un attaccante diretto. Correggere. |
| 11 | «each tenant an isolated store, derived from API key» | ✅core | adversarial opus: **PASS** sull'invariante (DB-per-tenant, tenant da key). 6 difetti MED/LOW aperti (personal-mode config, SSE DoS, quota TOCTOU) — non-HIGH ma da chiudere prima di spingere il claim "enterprise-ready". |
| 12 | «recall 1.3 ms @ 1M facts (ANN) vs 81 ms brute» | ✅ (corretto) | Numero REALE (`ann_scale_bench_repro.json`: 1.306/81.424 ms). 2 difetti di RICEVUTA chiusi 2026-07-16: (a) `SCALE.md` ora HA la tabella ANN 1M (prima solo brute 300k → "see SCALE.md" era monco); (b) recall ANN 0.844 (random worst-case) + OOM-riproducibilità + opt-in ora DICHIARATI in README+SCALE.md. Recheck oggi: 100k confermato 7.8×/1.12ms; 500k/1M OOM sulla mia macchina (serve ~32GB). |
| 13 | write-gate AUROC 0.971 (moat anti-confab) | 🔬 | ri-verificato PARZIALE su opus: noise-reject 1.0/clean-admit 0.85 su FOREIGN; R10/R11 full (SNLI/wrong-source) DA rifare |

## Azioni immediate (perché è online)
1. Ri-eseguire i 🔬 numerici (12 in corso; poi 6, 13) — budget opus aperto.
2. Correggere i ⚠️ #4 e #10 nel README (wording che non sovrastima).
3. Chiudere i 6 difetti tenant prima di rafforzare il claim #11 "enterprise".
4. Verificare #7 (`trust_stats` esiste).

Nessun ❌ FALSO trovato finora — ma 2 ⚠️ (sovrastima) e 5 🔬 (ricevute da rinfrescare).
Il claim non si dice finché la cella non è ✅.
