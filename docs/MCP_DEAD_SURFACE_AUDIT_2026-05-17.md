# MCP Dead-Surface Audit — 2026-05-17

Cycle #115.E audit. Source: `~/.engram/mcp_audit.log` (12252 historical calls).

## Numbers

- **Total MCP tools declared** in `engram/mcp_server.py`: 207
- **Used at least once** in audit log: 83 (40%)
- **Dead** (declared but never called via MCP): 125 (60%)
- Among the dead:
  - **78** have ZERO Python-internal use → **REAL deprecate candidates**
  - **34** are still used internally by other Python modules → keep the module, drop only the MCP surface
  - **13** could not be dispatch-decoded (handler body did not import a module/function)

## Real deprecate candidates (78)

Tools whose Python module is not referenced anywhere else in `engram/`. Safe to deprecate (with 3-month deprecation window per project convention).

| Tool | Module | Function |
|---|---|---|
| `hippo_agent_specialization` | `engram/agent_specialization.py` | `compute_specialization` |
| `hippo_agent_workload` | `engram/agent_workload.py` | `compute_workload` |
| `hippo_assess_fact_freshness` | `engram/time_decay.py` | `assess_freshness` |
| `hippo_briefing_by_project` | `engram/briefing_by_project.py` | `briefing_by_project` |
| `hippo_causal_skill_mine` | `engram/causal_skill_mine.py` | `causal_skill_mine` |
| `hippo_chain_complexity` | `engram/chain_complexity.py` | `compute_complexity` |
| `hippo_chain_facts` | `engram/fact_chain.py` | `chain_facts` |
| `hippo_chain_render` | `engram/chain_render.py` | `render_chain_markdown` |
| `hippo_chain_validate` | `engram/chain_validate.py` | `validate_chain` |
| `hippo_contradictions_list` | `engram/contradiction.py` | `ContradictionStore` |
| `hippo_contradictions_resolve` | `engram/contradiction.py` | `ContradictionStore` |
| `hippo_contradictions_scan` | `engram/contradiction.py` | `ContradictionStore` |
| `hippo_corpus_diff` | `engram/corpus_diff.py` | `corpus_diff` |
| `hippo_count_by_agent` | `engram/agent_scope.py` | `count_by_agent` |
| `hippo_cross_agent_consensus` | `engram/cross_agent_consensus.py` | `find_consensus_facts` |
| `hippo_detect_skill_drift` | `engram/skill_drift.py` | `detect_skill_drift` |
| `hippo_emerging_patterns` | `engram/emerging_patterns.py` | `find_emerging_patterns` |
| `hippo_episode_batch_get` | `engram/episode_batch_get.py` | `episode_batch_get` |
| `hippo_episode_classify` | `engram/episode_classify.py` | `classify_episodes` |
| `hippo_episode_clusters` | `engram/episode_clusters.py` | `cluster_episodes` |
| `hippo_episode_diff` | `engram/episode_diff.py` | `episode_diff` |
| `hippo_episode_replay` | `engram/episode_replay.py` | `render_episode_replay` |
| `hippo_episode_summary` | `engram/episode_summary.py` | `summarize_episodes` |
| `hippo_episodes_find_duplicates` | `engram/episode_dedup.py` | `find_duplicate_groups` |
| `hippo_episodes_with_skill` | `engram/episodes_with_skill.py` | `episodes_with_skill` |
| `hippo_export_dot` | `engram/graphviz_export.py` | `export_dot` |
| `hippo_fact_priority` | `engram/fact_priority.py` | `rank_facts_by_priority` |
| `hippo_fact_supersede_chain` | `engram/semantic.py` | `SupersedeError` |
| `hippo_facts_by_agent` | `engram/agent_scope.py` | `filter_facts_by_agent` |
| `hippo_facts_by_confidence` | `engram/facts_by_confidence.py` | `facts_by_confidence` |
| `hippo_facts_export_all` | `engram/facts_export.py` | `export_all_facts` |
| `hippo_facts_find_polluted` | `engram/syntax_pollution.py` | `scan_facts` |
| `hippo_facts_topic_merge` | `engram/facts_topic_merge.py` | `merge_facts_by_topic` |
| `hippo_failure_clusters` | `engram/failure_clusters.py` | `cluster_failures` |
| `hippo_metrics_export` | `engram/metrics_export.py` | `export_metrics` |
| `hippo_mine_skill_combos` | `engram/skill_combo_mining.py` | `mine_skill_combos` |
| `hippo_oracle_query` | `engram/oracle.py` | `oracle_query` |
| `hippo_outcome_patterns` | `engram/outcome_pattern.py` | `find_outcome_patterns` |
| `hippo_outcome_predict` | `engram/outcome_predict.py` | `predict_outcome` |
| `hippo_outcome_timeseries` | `engram/outcome_timeseries.py` | `outcome_timeseries` |
| `hippo_outcomes_by_skill` | `engram/outcome_by_skill.py` | `outcomes_by_skill` |
| `hippo_predict_warmup_skills` | `engram/skill_warmup.py` | `predict_warmup_skills` |
| `hippo_promote_chain` | `engram/promote_chain.py` | `promote_chain` |
| `hippo_prompt_skeleton` | `engram/prompt_skeleton.py` | `build_prompt_skeleton` |
| `hippo_query_skills` | `engram/query.py` | `query_skills` |
| `hippo_rank_facts_trust` | `engram/trust_score.py` | `rank_facts_by_trust` |
| `hippo_rank_skills_roi` | `engram/skill_roi.py` | `rank_skills_by_roi` |
| `hippo_recall_chain` | `engram/recall_chain.py` | `recall_chain` |
| `hippo_recommend_alternatives` | `engram/skill_recommend_failure.py` | `recommend_alternatives` |
| `hippo_review_promotions` | `engram/skill_promote_review.py` | `review_promotions` |
| `hippo_rollout_actions` | `engram/counterfactual_rollout.py` | `rollout_actions` |
| `hippo_rollup_old_episodes` | `engram/episode_rollup.py` | `rollup_old_episodes` |
| `hippo_session_recap` | `engram/session_recap.py` | `session_recap` |
| `hippo_skill_archive` | `engram/skill_archive.py` | `archive_skill` |
| `hippo_skill_bottlenecks` | `engram/skill_bottleneck.py` | `find_bottlenecks` |
| `hippo_skill_clone` | `engram/skill_clone.py` | `clone_skill` |
| `hippo_skill_cooccurrence_graph` | `engram/skill_cooccurrence_graph.py` | `build_cooccurrence_graph` |
| `hippo_skill_diff_render` | `engram/skill_diff_render.py` | `render_skill_diff` |
| `hippo_skill_inspect` | `engram/skill_inspect.py` | `skill_inspect` |
| `hippo_skill_lineage_full` | `engram/skill_lineage_full.py` | `skill_lineage_full` |
| `hippo_skill_merge_pair` | `engram/skill_merge_pair.py` | `merge_skill_pair` |
| `hippo_skill_promote_by_threshold` | `engram/skill_promote_threshold.py` | `promote_by_threshold` |
| `hippo_skill_provenance` | `engram/skill_provenance.py` | `skill_provenance` |
| `hippo_skill_recover` | `engram/skill_recover.py` | `recover_skill` |
| `hippo_skill_usage_decay` | `engram/skill_usage_decay.py` | `usage_decay` |
| `hippo_skills_export_all` | `engram/skill_export.py` | `export_all_skills` |
| `hippo_skills_recent` | `engram/skill_recent.py` | `skills_recent` |
| `hippo_skills_search_by_predicate` | `engram/skills_search_by_predicate.py` | `skills_with_predicate` |
| `hippo_skills_top_failing` | `engram/skills_top_failing.py` | `top_failing_skills` |
| `hippo_skills_top_used` | `engram/skills_top_used.py` | `top_used_skills` |
| `hippo_skills_untested` | `engram/skills_untested.py` | `find_untested_skills` |
| `hippo_smart_prune` | `engram/smart_pruning.py` | `smart_prune` |
| `hippo_success_factors` | `engram/success_factor.py` | `analyze_success_factors` |
| `hippo_trajectory_diff` | `engram/trajectory.py` | `trajectory_from_json` |
| `hippo_trajectory_fork` | `engram/trajectory_fork.py` | `trajectory_fork` |
| `hippo_trajectory_render` | `engram/trajectory.py` | `trajectory_from_json` |
| `hippo_trajectory_summary` | `engram/trajectory.py` | `trajectory_from_json` |
| `hippo_validate_claim` | `engram/validate_claim.py` | `validate_claim` |

## Keep-module candidates (34)

Tools whose MCP surface is dead, but the Python module is used internally. Drop only the MCP handler, keep the module.

| Tool | Module | Used by |
|---|---|---|
| `hippo_apply_recommendations` | `engram/apply_recommendations.py` | curate_pipeline, skill_promote_threshold |
| `hippo_causal_extract` | `engram/causal_extract.py` | causal_skill_mine |
| `hippo_compose_macro` | `engram/compose_macro.py` | skill_combo_mining, skill_compile_macro |
| `hippo_compose_plan` | `engram/skill_composer.py` | chain_visualize, live_introspection |
| `hippo_corpus_health_metrics` | `engram/corpus_health_metrics.py` | dashboard_overview_v2 |
| `hippo_corpus_size` | `engram/corpus_size.py` | curate_pipeline, dashboard_overview |
| `hippo_curate_pipeline` | `engram/curate_pipeline.py` | dashboard_overview |
| `hippo_dashboard_overview` | `engram/dashboard_overview.py` | dashboard_overview_v2 |
| `hippo_decay_run` | `engram/decay_job.py` | decay, legacy_audit |
| `hippo_decay_simulate` | `engram/decay_simulate.py` | curate_pipeline |
| `hippo_detect_anomalies` | `engram/anomaly_detection.py` | outlier_summary |
| `hippo_diagnose_failure` | `engram/failure_diagnosis.py` | memory_health_report |
| `hippo_dream_create_shadow` | `engram/config.py` | agent, audit_tail, cli, compilation, curate_pipeline ... |
| `hippo_facts_cluster_by_topic` | `engram/facts_cluster_by_topic.py` | semantic |
| `hippo_facts_freshness_check` | `engram/freshness_check.py` | dashboard_overview_v2 |
| `hippo_facts_merge` | `engram/facts_merge.py` | facts_topic_merge |
| `hippo_introspect_state` | `engram/live_introspection.py` | audit_tail |
| `hippo_legacy_audit` | `engram/legacy_audit.py` | legacy_cleanup |
| `hippo_metrics_one_liner` | `engram/metrics_one_liner.py` | dashboard_overview |
| `hippo_predicate_graph_check` | `engram/predicate_graph_check.py` | curate_pipeline |
| `hippo_render_chain` | `engram/chain_visualize.py` | chain_render |
| `hippo_self_model_get` | `engram/self_model.py` | self_model_refresh |
| `hippo_self_model_refresh` | `engram/self_model.py` | self_model_refresh |
| `hippo_skill_compile_macro` | `engram/skill_compile_macro.py` | compilation, sleep |
| `hippo_skill_failure_audit` | `engram/skill_failure_audit.py` | skill_inspect |
| `hippo_skill_health` | `engram/skill_health.py` | apply_recommendations, curate_pipeline, recommend_actions, skill_inspect, skill_promote_threshold |
| `hippo_skill_lineage_metrics` | `engram/skill_lineage_metrics.py` | corpus_health_score |
| `hippo_skill_path` | `engram/skill_path.py` | code, repomap, skill_inspect |
| `hippo_skills_co_occurrence` | `engram/skill_co_occurrence.py` | memory, wake |
| `hippo_skills_find_duplicates` | `engram/find_duplicates.py` | curate_pipeline, find_duplicate_facts, skill_merge_pair, skill_semantic_dedup, skill_signature |
| `hippo_skills_recommend_actions` | `engram/recommend_actions.py` | apply_recommendations |
| `hippo_skills_topology` | `engram/skills_topology.py` | dashboard_overview |
| `hippo_topic_cleanup_suggestions` | `engram/topic_cleanup_suggestions.py` | dashboard_overview_v2 |
| `hippo_world_simulate` | `engram/world_model.py` | counterfactual_rollout |

## Undecodable (13)

Dispatch handler did not import a module/function via the standard pattern. Needs manual review.

| Tool |
|---|
| `hippo_anchor_set` |
| `hippo_dream_list_pending` |
| `hippo_dream_status` |
| `hippo_entity_link` |
| `hippo_entity_neighbors` |
| `hippo_extract_entities` |
| `hippo_forward_chain` |
| `hippo_ppr_retrieve` |
| `hippo_self_model_update` |
| `hippo_skill_exposure_audit` |
| `hippo_skill_retire_invisible` |
| `hippo_skills_derive_predicates_batch` |
| `hippo_summary_topic` |
