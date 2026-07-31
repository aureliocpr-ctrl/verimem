"""Profilo di esposizione dei tool MCP — la lista, mai il dispatch.

Misurato il 2026-07-31 su ``mcp_audit.log`` (14.298 chiamate in 78 giorni):
la tools/list pesa 168.169 char (~42k token) che ogni client paga a ogni
sessione, e 126 tool su 244 non sono mai stati chiamati — 80.687 char
(~20k token), il 48% del prompt. Tre famiglie intere senza una chiamata
(trajectory, outcome, emerging).

``VERIMEM_TOOL_PROFILE=core`` (default) toglie dalla LISTA i tool sotto:
il dispatch resta completo, quindi un client che chiama per nome un tool
non esposto viene comunque servito — nessun flusso esistente puo'
rompersi, per costruzione. ``full`` espone tutto. La lista e' dei
NASCOSTI (non dei core) di proposito: un tool nuovo nasce visibile.
"""
from __future__ import annotations

import os

# generato 2026-07-31 da mcp_audit.log (14298 chiamate, 78 giorni): 126 tool mai chiamati
HIDDEN_IN_CORE_PROFILE: frozenset[str] = frozenset((
    "hippo_agent_specialization",
    "hippo_agent_workload",
    "hippo_anchor_set",
    "hippo_anti_confab_apply",
    "hippo_apply_recommendations",
    "hippo_assess_fact_freshness",
    "hippo_causal_extract",
    "hippo_causal_skill_mine",
    "hippo_chain_complexity",
    "hippo_chain_render",
    "hippo_compose_macro",
    "hippo_compose_plan",
    "hippo_contradictions_resolve",
    "hippo_corpus_diff",
    "hippo_count_by_agent",
    "hippo_cross_agent_consensus",
    "hippo_curate_pipeline",
    "hippo_dashboard_overview",
    "hippo_decay_run",
    "hippo_detect_anomalies",
    "hippo_detect_skill_drift",
    "hippo_diagnose_failure",
    "hippo_document_get",
    "hippo_document_index_file",
    "hippo_document_promote_chunk",
    "hippo_document_search",
    "hippo_document_semantic_search",
    "hippo_dream_create_shadow",
    "hippo_dream_list_pending",
    "hippo_dream_status",
    "hippo_emergence_pipeline_status",
    "hippo_emerging_patterns",
    "hippo_emerging_skill_promote",
    "hippo_emerging_skills_draft",
    "hippo_emerging_skills_register",
    "hippo_entity_link",
    "hippo_entity_neighbors",
    "hippo_episode_batch_get",
    "hippo_episodes_with_skill",
    "hippo_epistemic_health",
    "hippo_export_dot",
    "hippo_extract_entities",
    "hippo_fact_label",
    "hippo_fact_priority",
    "hippo_facts_by_agent",
    "hippo_facts_cluster_by_topic",
    "hippo_facts_export_all",
    "hippo_facts_freshness_check",
    "hippo_facts_merge",
    "hippo_facts_topic_merge",
    "hippo_failure_clusters",
    "hippo_forward_chain",
    "hippo_heal_contradictions",
    "hippo_ignorance_map",
    "hippo_import_conversations",
    "hippo_ingest_conversation",
    "hippo_introspect_state",
    "hippo_legacy_audit",
    "hippo_metrics_export",
    "hippo_mine_skill_combos",
    "hippo_outcome_patterns",
    "hippo_outcome_predict",
    "hippo_outcome_timeseries",
    "hippo_outcomes_by_skill",
    "hippo_ppr_retrieve",
    "hippo_predicate_graph_check",
    "hippo_predict_warmup_skills",
    "hippo_promote_chain",
    "hippo_prompt_skeleton",
    "hippo_quarantine_log",
    "hippo_quarantine_restore",
    "hippo_query_skills",
    "hippo_rank_facts_trust",
    "hippo_rank_skills_roi",
    "hippo_recall_as_of",
    "hippo_recall_chain",
    "hippo_recall_history",
    "hippo_recommend_alternatives",
    "hippo_render_chain",
    "hippo_review_promotions",
    "hippo_rollout_actions",
    "hippo_rollup_old_episodes",
    "hippo_screen_content",
    "hippo_self_model_refresh",
    "hippo_session_recap",
    "hippo_skill_archive",
    "hippo_skill_bottlenecks",
    "hippo_skill_clone",
    "hippo_skill_compile_macro",
    "hippo_skill_cooccurrence_graph",
    "hippo_skill_diff_render",
    "hippo_skill_drafts_list",
    "hippo_skill_exposure_audit",
    "hippo_skill_failure_audit",
    "hippo_skill_health",
    "hippo_skill_inspect",
    "hippo_skill_lineage_full",
    "hippo_skill_lineage_metrics",
    "hippo_skill_merge_pair",
    "hippo_skill_path",
    "hippo_skill_promote_by_threshold",
    "hippo_skill_provenance",
    "hippo_skill_recover",
    "hippo_skill_retire_invisible",
    "hippo_skill_usage_decay",
    "hippo_skills_co_occurrence",
    "hippo_skills_derive_predicates_batch",
    "hippo_skills_export_all",
    "hippo_skills_recent",
    "hippo_skills_recommend_actions",
    "hippo_skills_search_by_predicate",
    "hippo_skills_top_failing",
    "hippo_skills_top_used",
    "hippo_skills_topology",
    "hippo_skills_untested",
    "hippo_smart_prune",
    "hippo_success_factors",
    "hippo_trajectory_diff",
    "hippo_trajectory_fork",
    "hippo_trajectory_render",
    "hippo_trajectory_summary",
    "hippo_transcript_promote",
    "hippo_transcript_recall",
    "hippo_undo_list",
    "hippo_validate_claim",
    "hippo_world_simulate",
))


def profile() -> str:
    """``core`` (default) o ``full`` — letto per-chiamata, mai congelato."""
    p = os.environ.get("VERIMEM_TOOL_PROFILE", "core").strip().lower()
    return p if p in ("core", "full") else "core"


def exposed(name: str) -> bool:
    return profile() == "full" or name not in HIDDEN_IN_CORE_PROFILE
