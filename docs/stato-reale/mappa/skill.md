# `verimem/skill.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 Marie (QA) · **08/09**.

## La catena: modulo → tool MCP → test

Misurata per tutti e 47 i moduli `skill*` in un colpo solo
(`catena_skill.py`): il nome del tool si legge dal ramo del
dispatcher (`if name == "hippo_…":` in `mcp_server.py`), **non**
da una funzione `tool_*` — quelle non esistono, e cercarle dava
**0 tool su 47** mentre 43 moduli erano importati.

**Nessun tool MCP** — ma il modulo è **vivo** su un'altra porta:
`_skill_from_dict` — è il modello base, non un tool.

🔑 «Non esposto da MCP» non è «non esposto». Misurando solo
`mcp_server.py` avrei consegnato un falso reperto.

## La tabella

⚠️ Bozza da `scripts/mappa_bozza.py`: la colonna «chiamata da» viene
da `git grep` **per nome**, e nel progetto **589 funzioni su 2.973
(19,8%) condividono il nome** con un'altra. Le righe con un omonimo
plausibile vanno lette prima di essere usate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/skill.py:42` `Skill` | classe: (nessun docstring) | `verimem/active_learning.py:40`; `verimem/active_learning.py:43`; `verimem/active_learning.py:52` (+228) | `tests/perf/bench.py`; `tests/test_active_learning.py`; `tests/test_active_memory_integration.py` (+130) | - | NON MISURATO | - |
| 2 | `verimem/skill.py:86` `Skill.fitness_mean` | funzione: Posterior mean of Beta(alpha+s, beta+f). Robust for small trials. | `verimem/active_learning.py:40`; `verimem/active_learning.py:43`; `verimem/active_learning.py:52` (+115) | `tests/test_bayesian_gates.py`; `tests/test_briefing.py`; `tests/test_corpus_diff.py` (+20) | - | NON MISURATO | - |
| 3 | `verimem/skill.py:93` `Skill.fitness_lower_bound` | funzione: Lower 5% quantile of the Beta posterior — pessimistic estimate. | `verimem/config.py:386`; `verimem/hippo_pagerank.py:25`; `verimem/hippo_pagerank.py:80` (+10) | `tests/test_bayesian_gates.py`; `tests/test_hippo_pagerank.py`; `tests/test_selection.py` (+1) | - | NON MISURATO | - |
| 4 | `verimem/skill.py:101` `Skill.fitness_variance` | funzione: Beta(a, b) variance: a*b / ((a+b)^2 * (a+b+1)). | `verimem/recommend_actions.py:11`; `verimem/recommend_actions.py:64`; `verimem/selection.py:19` (+6) | `tests/test_rnd_active_memory.py`; `tests/test_skill_health.py` | - | NON MISURATO | - |
| 5 | `verimem/skill.py:112` `Skill.to_dict` | funzione: (nessun docstring) | `verimem/cli.py:2274`; `verimem/compilation.py:68`; `verimem/dashboard_routes/settings.py:338` (+9) | `tests/test_bayesian_gates.py`; `tests/test_compilation.py`; `tests/test_composer.py` (+14) | - | NON MISURATO | - |
| 6 | `verimem/skill.py:116` `Skill.from_dict` | funzione: (nessun docstring) | `verimem/compilation.py:77`; `verimem/compilation.py:201`; `verimem/mcp_server.py:682` (+7) | `tests/test_compilation.py`; `tests/test_mcp_export_import_test_audit.py`; `tests/test_settings.py` (+6) | - | NON MISURATO | - |
| 7 | `verimem/skill.py:124` `Skill.render` | funzione: (nessun docstring) | `verimem/cli.py:5046`; `verimem/code.py:358`; `verimem/engram_syscall_mcp.py:17` (+33) | `tests/perf/seed_data.py`; `tests/security/test_hook_banner_containment.py`; `tests/security/test_saas_atomic.py` (+21) | - | NON MISURATO | - |
| 8 | `verimem/skill.py:170` `_migrate_skills_v0_to_v1` | funzione: No-op: lo schema skills v1 e' creato da _SCHEMA (CREATE TABLE IF NOT | `verimem/skill.py:240` | nessuno | - | NON MISURATO | - |
| 9 | `verimem/skill.py:176` `_migrate_skills_v1_to_v2` | funzione: 2026-06-03 — colonna ``embedding_model`` per-riga (parallela a semantic.py | `verimem/skill.py:241` | nessuno | - | NON MISURATO | - |
| 10 | `verimem/skill.py:198` `_screen_skill_text` | funzione: Audit A2 (2026-06-08): redact secrets + defang injection in skill text | `verimem/skill.py:289` | nessuno | - | NON MISURATO | - |
| 11 | `verimem/skill.py:228` `SkillLibrary` | classe: (nessun docstring) | `verimem/agent.py:14`; `verimem/agent.py:49`; `verimem/agent.py:63` (+48) | `tests/perf/bench.py`; `tests/perf/e2e_cycle51_54_chain.py`; `tests/perf/seed_data.py` (+84) | - | NON MISURATO | - |
| 12 | `verimem/skill.py:229` `SkillLibrary.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | NON MISURATO | - |
| 13 | `verimem/skill.py:250` `SkillLibrary._connect` | funzione: (nessun docstring) | `verimem/_sqlite_pragma.py:47`; `verimem/cli.py:3140`; `verimem/cli.py:3189` (+185) | `tests/swarm/test_bridge.py`; `tests/swarm/test_integration_haiku.py`; `tests/swarm/test_lifecycle.py` (+44) | - | NON MISURATO | - |
| 14 | `verimem/skill.py:269` `SkillLibrary._path` | funzione: (nessun docstring) | `verimem/skill.py:319`; `verimem/skill.py:354` | `tests/test_active_memory_integration.py`; `tests/test_lo_store_di_una_skill_non_lascia_due_verita.py`; `tests/test_rotten_hop.py` | - | NON MISURATO | - |
| 15 | `verimem/skill.py:272` `SkillLibrary.store` | funzione: Insert or replace a skill. Backwards-compatible default returns None. | `verimem/_call_telemetry.py:5`; `verimem/_compat.py:85`; `verimem/_compat.py:156` (+1013) | `tests/conftest.py`; `tests/perf/e2e_cycle51_54_chain.py`; `tests/perf/seed_data.py` (+658) | `README.md:199`; `README.md:245`; `README.md:254` | NON MISURATO | - |
| 16 | `verimem/skill.py:351` `SkillLibrary.get` | funzione: (nessun docstring) | `verimem/_compat.py:24`; `verimem/_compat.py:185`; `verimem/_hang_watchdog.py:48` (+2547) | `tests/conftest.py`; `tests/perf/bench_briefing_proactive.py`; `tests/perf/bench_briefing_proactive_v2.py` (+630) | `README.md:68`; `README.md:134`; `README.md:381` | NON MISURATO | - |
| 17 | `verimem/skill.py:375` `SkillLibrary.all` | funzione: (nessun docstring) | `verimem/__init__.py:16`; `verimem/__init__.py:21`; `verimem/_compat.py:31` (+696) | `tests/_esito.py`; `tests/causal_fixture_helper.py`; `tests/conftest.py` (+540) | `README.md:81`; `README.md:93`; `README.md:125` | NON MISURATO | - |
| 18 | `verimem/skill.py:382` `SkillLibrary.search_skills` | funzione: FORGIA pezzo #203: keyword/substring search across name + | `verimem/mcp_server.py:13237` | `tests/test_mcp_facts_skills_search.py` | - | NON MISURATO | - |
| 19 | `verimem/skill.py:411` `SkillLibrary._load_all_skills` | funzione: Load every skill JSON file once. The sleep cycle calls all() | `verimem/skill.py:359`; `verimem/skill.py:377` | `tests/test_le_skill_hanno_due_verita.py` | - | NON MISURATO | - |
| 20 | `verimem/skill.py:425` `SkillLibrary.invalidate_cache` | funzione: Drop the in-memory skill cache. Call after external changes | nessuno trovato | `tests/test_corruption_guards.py` | - | NON MISURATO | - |
| 21 | `verimem/skill.py:432` `SkillLibrary.retrieve` | funzione: Top-k skills by trigger-embedding similarity. | `verimem/active_probe.py:95`; `verimem/bench_harness.py:185`; `verimem/bench_harness.py:351` (+47) | `tests/perf/baseline.json`; `tests/perf/bench.py`; `tests/perf/post_final.json` (+33) | - | NON MISURATO | - |
| 22 | `verimem/skill.py:478` `SkillLibrary.find_duplicates` | funzione: Pairs of skills with cosine similarity ≥ threshold (de-dup candidates). | `verimem/curate_pipeline.py:20`; `verimem/mcp_server.py:6896`; `verimem/mcp_server.py:10215` (+6) | `tests/perf/baseline.json`; `tests/perf/bench.py`; `tests/perf/post_final.json` (+10) | - | NON MISURATO | - |
| 23 | `verimem/skill.py:532` `SkillLibrary.find_duplicates._norm` | funzione: (nessun docstring) | `verimem/derivation_detect.py:62`; `verimem/derivation_detect.py:73`; `verimem/entity_kg.py:307` (+14) | `tests/test_entity_kg.py`; `tests/test_external_f1_msc.py`; `tests/test_openie.py` | - | NON MISURATO | - |
| 24 | `verimem/skill.py:546` `SkillLibrary.update_fitness` | funzione: (nessun docstring) | `verimem/dashboard_routes/chat.py:143`; `verimem/dashboard_routes/chat.py:147`; `verimem/mcp_server.py:9339` (+8) | `tests/test_dashboard_api.py`; `tests/test_flow_episodi_skill.py`; `tests/test_hebbian.py` (+8) | - | NON MISURATO | - |
| 25 | `verimem/skill.py:593` `SkillLibrary._hebbian_update` | funzione: Lerp skill.trigger embedding toward task embedding, then re-normalise. | `verimem/skill.py:565` | nessuno | - | NON MISURATO | - |
| 26 | `verimem/skill.py:616` `SkillLibrary._lateral_inhibition` | funzione: Push the embeddings of rival skills AWAY from the task vector. | `verimem/skill.py:576` | nessuno | - | NON MISURATO | - |
| 27 | `verimem/skill.py:711` `SkillLibrary.decay_idle_embeddings` | funzione: Pull stale skill embeddings back toward their canonical anchor. | `verimem/cli.py:2916`; `verimem/embedding.py:472`; `verimem/sleep.py:1007` (+2) | `tests/test_il_sonno_moriva_su_un_modello_che_non_ce_piu.py`; `tests/test_rnd_active_memory.py` | - | NON MISURATO | - |
| 28 | `verimem/skill.py:775` `SkillLibrary.promote_or_retire` | funzione: (nessun docstring) | `verimem/mcp_server.py:940`; `verimem/mcp_server.py:5705`; `verimem/skill.py:246` (+6) | `tests/test_skill.py`; `tests/test_skill_dormant_retire.py`; `tests/test_skill_promote_from_emerging.py` (+1) | - | NON MISURATO | - |
| 29 | `verimem/skill.py:801` `SkillLibrary.retire_dormant_candidates` | funzione: Ritira le candidate-ZOMBIE: sotto ``min_trials`` (quindi invisibili | `verimem/sleep.py:1135` | `tests/test_skill_dormant_retire.py` | - | NON MISURATO | - |
| 30 | `verimem/skill.py:848` `SkillLibrary.add_lineage_edge` | funzione: Record an arbitrary lineage edge (e.g. 'specialises' for schemas). | `verimem/sleep.py:859` | `tests/test_corpus_health_lineage.py`; `tests/test_rnd_active_memory.py` | - | NON MISURATO | - |
| 31 | `verimem/skill.py:863` `SkillLibrary.cluster_by_embedding` | funzione: Cluster skills by trigger-embedding similarity (connected components). | `verimem/sleep.py:827` | `tests/perf/baseline.json`; `tests/perf/bench.py`; `tests/perf/post_final.json` (+5) | - | NON MISURATO | - |
| 32 | `verimem/skill.py:925` `SkillLibrary.lineage_graph` | funzione: (nessun docstring) | `verimem/dashboard_routes/active_memory.py:109`; `verimem/dashboard_routes/lineage.py:47`; `verimem/lineage_trace.py:7` (+2) | `tests/test_dashboard_api.py`; `tests/test_mcp_lineage_trace.py`; `tests/test_schema.py` (+1) | - | NON MISURATO | - |
| 33 | `verimem/skill.py:935` `SkillLibrary.count` | funzione: (nessun docstring) | `verimem/_compat.py:67`; `verimem/active_probe.py:11`; `verimem/adjudication_log.py:300` (+402) | `tests/perf/bench_briefing_proactive.py`; `tests/perf/bench_briefing_proactive_v2.py`; `tests/perf/bench_self_model_ab.py` (+201) | `README.md:379`; `README.md:380` | NON MISURATO | - |
| 34 | `verimem/skill.py:938` `SkillLibrary.clear` | funzione: (nessun docstring) | `verimem/_compat.py:37`; `verimem/_hang_watchdog.py:98`; `verimem/_hang_watchdog.py:127` (+85) | `tests/conftest.py`; `tests/security/test_pentest_validation.py`; `tests/test_ann_recall_equivalence.py` (+42) | `README.md:754` | NON MISURATO | - |

⚠️ **I verdetti di questa tabella NON sono ancora dati**: la catena
sopra dice che il modulo è raggiungibile e presidiato, **non** che
ogni sua funzione faccia ciò che promette. Per quello serve il banco
nel merito, che per questa famiglia **non ho ancora scritto** — e lo
dichiaro invece di lasciar credere che «catena completa» significhi
«funziona come promesso».
