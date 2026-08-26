# Release Gate — public single-package readiness

> Owner mandate (2026-07-04): public release requires (a) verified-working
> ("certezza matematica" → translated into the falsifiable criteria below) and
> (b) a single installable package. **No criterion passes without evidence**
> (command + output committed or linked). Declaring "ready" with any row open
> is forbidden (A2/A4).

> ⚠️ **COME SI LEGGE LA COLONNA `Status`** (aggiunto 2026-08-13). Ogni ✅ qui
> dentro dice **«è stato verificato una volta»**, non «vale adesso»: porta la
> data in cui l'evidenza fu prodotta e nessuno la rinnova. Un registro di stato
> si degrada in **una sola direzione** — i ✅ restano fermi e il mondo cambia —
> quindi **una riga verde va letta insieme alla data dell'ultima evidenza VIVA**,
> che non è la stessa cosa della data in cui fu chiusa.
>
> **Misurato il 2026-08-13**, e riguarda proprio le due righe verdi qui sotto che
> dipendono dalla CI: su **100 run consecutivi** di `ci` (05/08 → 13/08) ci sono
> **zero `success`** — 42 `failure`, 55 `cancelled`, 3 in corso — e i job `build`
> e `wheel-install`, che sono il meccanismo con cui G8 e G9 si verificano, sono
> risultati **`skipped` in 17 run su 17** fra quelli esaminati uno per uno
> (dipendono da `test`, che fallisce). **Nessuna evidenza nuova per quei due
> criteri da almeno 201,2 ore**, ed è un limite *inferiore*: la finestra è di
> 100 run, non copre l'intero intervallo dal 06/07.
>
> ⇒ **G8 e G9 restano ✅ come fatti storici** — quel run del 06/07 fu davvero
> verde — **e non sono una misura dello stato di oggi.** Questa nota non ribalta
> nessun verdetto: lo **data**, che è ciò che il mandato in cima chiede
> («no criterion passes without evidence») applicato al passare del tempo.

| # | Criterion | Evidence required | Status |
|---|-----------|-------------------|--------|
| G1 | **Full test suite green** on a clean run | pytest output, count, date | ⏳ 2026-07-04 full run: **5937 passed**, 5 failed → 3 were REAL regressions from the 2026-07-02 interactive-judge work (bare subprocess callsites + tests patching the pre-_ex API), all FIXED same day; 2 remaining are the known environmental pair (provider smoke without API key by policy; SLO test flaky under load — it ran while claude -p benches saturated the box). Final clean re-run at gate close |
| G2 | **Install-from-scratch**: virgin venv → wheel install → `import engram` → SDK smoke (add/search/recall) → `engram` CLI entrypoint → MCP server starts | transcript in `docs/release/G2_install.md` | ✅ 2026-07-04 — PASS, and it caught a real bug: `engram mcp` logged on stdout breaking JSON-RPC purity (fixed, `tests/test_mcp_stdout_purity_g2.py`) |
| G3 | **Crash durability**: crash-injection test over the write paths | `tests/test_crash_injection_g3.py` (3 tests: kill mid-burst = zero committed loss + integrity ok, reopen+write, journal replay after kill; anti-vacuity guard). Residual: OS-crash/power-loss window under default NORMAL is BY DESIGN, closed by `ENGRAM_SQLITE_SYNCHRONOUS=FULL` — declared, not testable in userspace | ✅ 2026-07-04 (knob + replay-checkpoint pre-existed from the data-loss hunt) |
| G4 | **Benchmarks reproducible by one command** (seeded): every README number regenerable | `benchmark/repro_all.py` + doc | ⏳ 2026-07-04 entrypoint shipped: registry claim→command→artifact, `--verify` 6/6 backed, guarded by `tests/test_repro_registry_g4.py` (artifact drift breaks the suite). 2026-08-25: `--verify` was counting ONE property and printing `8/8 backed` with exit 0, while `benchmark/lme_retrieval_bench.py` did not exist -- the artifact was there, the recipe was not. It now counts the two apart: 8/8 backed by artifacts, **7/8 regenerable by their command**, exit 1. The number itself (README:22, LongMemEval recall@5 0.87) stays backed: `lme_s_fusionON_n500_clean.json` reports recall_at_k 0.8745 over n_questions 500 at k 5. Remaining: restore the missing bench (2 reds hold that place) + seed audit per command + registry coverage of remaining README numbers |
| G5 | **Property-based invariants** on core paths via hypothesis | `tests/test_property_invariants_g5.py` + `tests/test_property_gate_admission_g5.py` | ✅ 3/3 2026-07-04 — tier totality/prefix-stability; supersession no-delete/no-cycle (hypothesis found the A→B→A cycle bug, fixed); gate-admission monotone in score + decision flips exactly at the PER-JUDGE resolved threshold + env override wins (locks the 2026-07-02 critic finding about scale-mismatched cuts) |
| G6 | **README claim audit**: zero unverified claims, every number sourced to a results file | audit note in PR | ⏳ policy already; final pass at gate close |
| G7 | **Name / PyPI identity** + LICENSE/attribution check of bundled models (e5, NLI, distilled CE weights) | pyproject rename + license notes | ✅ 2026-07-06: **verimem 0.3.0 LIVE on PyPI** (https://pypi.org/project/verimem/ — real engine, not a placeholder; install verified from a clean venv; wheel ships only engram/verimem/hippoagent). GitHub repo renamed + public + pushed (history purged first, Via A). Remaining (non-blocking): formal EUIPO/USPTO search, bundled-model license audit ⚠️ **DATATO 2026-08-26 (ws7)** — il ✅ vale per il 06/07 e per **0.3.0**, non come proprietà continuativa né per ciò che PyPI serve oggi. Misurato: `pip index versions verimem` → l'ultima è **0.7.0** (22 luglio) e `origin/main` le è **994 commit** avanti. La clausola qui accanto — *«install verified from a clean venv»* — oggi non reggerebbe sul **server MCP**: v0.7.0 dichiara `mcp>=1.0.0` senza tetto in tre punti, PyPI serve `mcp 2.1.1`, e nel wheel 2.1.1 `mcp/server/lowlevel/server.py` non ha più `list_tools`, `call_tool` né `list_resources`, che `verimem/mcp_server.py` chiama in 11 punti (A/B nella stessa esecuzione contro la 1.26.0, dove ci sono tutte e tre; `Requires-Python >=3.10` su entrambi, quindi pip non ripiega sulla 1.x). Il tetto `<2` è nel repo dal 29/07 (`bd4ff5ba`, che diagnosticava già esattamente questo) e non è nel pacchetto: **28 giorni**. 🔑 **È la stessa asimmetria di G8, un passo più in là**: lì un job `skipped` non lasciava traccia; qui **il pacchetto pubblicato non è nel perimetro di nessun presidio** — la suite gira sull'albero, e l'albero è sano. Il presidio che più si avvicina (`test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice`) misura la distanza dal **bump** di pyproject: **131 su soglia 150, verde**, mentre la grandezza che il suo docstring nomina («nessuno può accorgersi che il pacchetto PUBBLICATO è vecchio») vale **994** — il bump a 0.7.6 del 21/08 ha azzerato il contatore senza che nulla venisse pubblicato. ⇒ Dichiarato nel README in `6e645cfb`, che è la terza delle tre uscite che quel presidio nomina; le altre due (pubblicare, alzare la versione) sono del CEO. |
| G8 | **Fresh-environment model download**: first-run UX when HF cache is empty | CI `wheel-install` job (runner cache is empty → e5 first-run download exercised on every push, both OSes) | ✅ 2026-07-06: FIRST GREEN RUN in repo history (run 28800008230, HEAD 900962a) — repo public unblocked Actions (billing diagnosis confirmed); 4 layers of accumulated gate debt fixed forward same day (lint 21 findings, hypothesis dev-dep, hardcoded Windows cwd in 2 subprocess tests, real-model guard on the packaging probe). wheel-install job green = fresh-env model download exercised. ⚠️ **DATATO 2026-08-15 (ws7), su segnalazione di ws1 — il ✅ vale per il 06/07 e NON come proprietà continuativa.** La colonna «evidence» qui accanto dice *«exercised on every push, both OSes»*: **misurato oggi, `wheel-install` è `skipped` e lo è da oltre 200 ore**, perché `needs: build` → `needs: test` e nessun run di `ci` passa (19 conclusi oggi, 19 failure, zero verdi). Un job `skipped` non lascia questo criterio «da riverificare»: **lo lascia senza alcun modo di verificarsi**, mentre il ✅ resta leggibile come se il meccanismo girasse. 🔑 **E la ragione per cui G9 è stato scoperto e questo no è la stessa asimmetria**: G9 poggiava su run ROSSI, che si contano e si guardano; G8 poggia su un job SALTATO, e **uno skip non compare fra i failure** — `gh run list` lo conta come run, non come rosso. *Un rosso si vede, un'assenza no* (formulazione di ws1). ⇒ Curato alla radice in `dcc41bc8`: `build` ora ha `if: !cancelled()`, così il gate riparte anche col cuore rosso. **Predizione dichiarata, non ancora verificata**: nel primo run concluso che contiene quel commit, `build` non sarà `skipped`. Finché quella misura non c'è, questa riga va letta come «vero al 06/07, sospeso da allora», non come ✅. ⇒ ✅ **PREDIZIONE VERIFICATA 2026-08-24 23:29 — G8 NON È PIÙ SOSPESO.** Sui 6 run di `ci` conclusi oggi su main `build` è `success` 6 su 6 **e `wheel-install` — che è il meccanismo dichiarato di G8, non `build` — è `success` 6 su 6**, su entrambi gli OS (sono DUE job: windows-latest + ubuntu-latest, cioè il «both OSes» della colonna evidence), e gira **con i test rossi 6/6**, che era esattamente lo scopo della cura `dcc41bc8`. ⚠️ E non si è guardato solo il colore, perché `success` è un proxy: log del job 97557119331 (run 32756978949, windows), riga 131 → `SDK smoke OK: model_claim quarantined 1` ⇒ dal wheel installato in un venv vergine il gate di ammissione SPARA (il claim «everything works perfectly and is fully verified» finisce `quarantined`) e la ricerca restituisce 1 hit con provenienza; riga 126 `_adopt_observed_dim(model.get_sentence_embedding_dimension())` ⇒ un modello sentence-transformers viene caricato per davvero. Sulla clausola «runner cache is empty», che dal log NON è osservabile: gli step del job sono checkout / setup-python / venv / pip install / smoke — **nessuno step di cache e nessun `actions/cache` per HF** ⇒ la cache è vuota per COSTRUZIONE, non per fortuna. 🔑 Riconfermato su un run **verde**: `32764736605` (HEAD `76fb5221`) `completed/success`, 9 job su 9 |
| G9 | **Cross-platform CI**: suite matrix existed; G2-from-wheel added (`wheel-install` job: virgin venv, SDK gate smoke, MCP stdout-purity handshake, win+ubuntu) | `.github/workflows/ci.yml` + green run | ⏳ **REGRESSED — was ✅ 2026-07-06** (full matrix green, 6 jobs ubuntu py3.10-3.13 + windows + macos, run 28800008230). **Measured 2026-08-14 18:03 CEST, `gh run list --workflow=ci --limit 30`: 24 failure, 0 success, 3 in_progress, 3 queued** over the window 2026-08-13 11:35 → 2026-08-14 16:02 UTC. An independent count by another session over the previous window (2026-08-12 15:38 → 2026-08-13 16:00) gave 58 failure + 2 cancelled out of 60, also zero green. ⚠️ **The ✅ above stood for 38 days while the pipeline was red**, and that is the failure this row now records: a stale ✅ does not merely go unread, it AUTHORISES — anyone consulting the gate concluded CI was fine. Re-green it with a run id and a date, not by editing this cell. ⇒ ✅ **RUN ID E DATA, 2026-08-24 23:29**: run `32764736605` su HEAD `76fb5221`, `completed/success`, **9 job su 9** — la matrice completa è verde (ubuntu py3.10/3.11/3.12/3.13 + windows py3.12 + macos py3.12, 6 celle su 6) più `build` più i due `wheel install-from-scratch`. Ed è il primo di CINQUE: `gh run list --workflow=ci --branch main --limit 20` dà `success=5` (`32767355445` `ffd9b7f4`, `32766932505` `8a82d4d6`, `32766117358` `f853f7c3`, `32765385962` `2a91ef6f`, `32764736605` `76fb5221`), dove la misura precedente su 100 run consecutivi ne dava **zero**. ⚠️ Ciò che questa riga NON dice, e va letto insieme al resto: un run verde non è un rilascio verde — `publish.yml` ha un veto separato (`scripts/controlla_registro.py`) che il wheel deve passare, e va misurato a parte |

| G10 | **Multilingual validation** (the product claims memory for AI agents, not for English agents): smoke zh/ru/fi in CI; L1 unsupported-claim patterns beyond EN; NLI/CE multilingual options (mDeBERTa-xnli, mmarco-mMiniLM) benchmarked before swap; re-run en→fi cross-lingual search on an idle machine | smoke script + model A/Bs | ⏳ opened 2026-07-04 — measured: retrieval IS multilingual (zh→zh 0.909, it→zh 0.843, multilingual-e5); span-selection regex fixed (was [a-z0-9]+ = blind prefix on non-Latin, `tests/test_span_multilingual_g10.py`); L1 screen is EN-only (RU unsupported claim passed); the two cross-encoders degrade silently and are DIFFERENT models — moat judge = cross-encoder/nli-deberta-v3-base (EN, the one this row calls "NLI"; `gate_config.json`, vocab_size 128100), retrieval rerank = cross-encoder/ms-marco-MiniLM-L-12-v2 (EN, the one this row calls "CE"; `cross_encoder_rerank.py`). Disambiguated 2026-08-25 (ws3): `local_grounding.py` uses "CE" for the JUDGE, so this row read as a contradiction of it for weeks when it was simply naming the other component — it has been right since 2026-07-04 |

## Adversarial review findings (2026-07-04, 3 Opus agents read-only)

**Critic (write-path moat):** S1 the entailment gate was unreachable from
`add()` — FIXED (`ground=True`/`gate_mode` per-call, honest claim). S2
reject-mode unreachable — FIXED. S3 supersede cycle-check hop-cap escape
(70-ring) — FIXED. **Open:** S4 local-uncalibrated score vs claude-scale cut
(warn, not prevent) — needs the shipped CE score distribution to size impact;
S5 interactive-judge trusts the sister's scale with no cross-check.

**Security/privacy sweep:** C1 personal-corpus dumps + H1 real email in
tracked files — FIXED (git rm --cached + scrub; history purge DONE 2026-07-06 (filter-repo Via A: 10 corpus files + fake test key wiped, push protection passed clean)). **Open, security:** H2 `sandbox_exec` behind
`HIPPO_ENABLE_SHELL` — FIXED (disabled by default, opt-in like run_task,
`tests/test_sandbox_exec_shell_gate_h2.py`);
H3 strict-mode pytest-arg escape — FIXED (`-p`/`--pyargs`/`--import-mode`/`-c`/`-o` blocked, `tests/test_sandbox_strict_pytest_args_h3.py`; the `git config` write vector it named was already closed 2026-06-05); M3 IDE symlink TOCTOU +
uncapped subprocess stdout. CLEAN (verified): no tracked secrets, SSRF guard
solid, dashboard loopback-only + token, workflows least-privilege OIDC, MIT
license + runtime-downloaded models (no redistribution obligation).

**DX review:** README numbers reconciled (tests badge, 231 MCP tools), 2
broken audit links fixed, `hippoagent/static` path fixed, plugin.json +
workflows renamed hippoagent→verimem (was release-blocking). **Open:** README
is ~1156 lines with duplicated install/demo sections — a ~40% cut + move the
cycle-log history to CHANGELOG is the highest-leverage launch task; a few
Italian lines + a HippoAgent code sample remain.

## Non-goals of this gate (declared)
- ANN wiring >100k and cold-tiering: performance roadmap, not release blockers
  (single-node honesty is already documented in STATE/README).
- Third-party leaderboard placement: the 3-slice HaluMem + LME-S table ships
  with the release as *self-run, reproducible, asterisked* numbers.

## Order of execution
1. G2 (in progress) → G8 right after (same harness, empty HF_HOME).
2. G3 (the only real known reliability hole) — TDD.
3. G5 → G4 → G1 full rerun → G6 → G9.
4. G7 whenever the owner picks the name (independent of 1-3).
