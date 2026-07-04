# R&D Memorie Attive — sprint changelog

Stato: 7 fix implementati su tutte le 6 memorie attive (+1 nuovo meccanismo). Test suite **261/261 verde** (era 213, +48 dovuti a integrazione + nuove proprietà). Zero regressioni nei 113 test originali. Nessun touch a moduli intoccabili (ide.py, cli.py /api/settings/providers, tools_extra._fs_roots / _is_blocked_host / _is_sensitive).

## Fix per meccanismo

### 1) Procedural compilation — adaptive fast-path
- Prima: `cosine ≥ 0.72` AND `fitness ≥ 0.80` come gate STATICI per attivare la macro (`hippoagent/wake.py:_try_compiled_macro`).
- Dopo: `_adaptive_macro_threshold(macro.confidence)` abbassa la soglia di similarity in funzione lineare della LLM-rated confidence salvata in fase di compilazione (default `k=0.3` per unit di confidence sopra 0.5, hard floor `0.55`).
- Rationale: una macro distillata da N traiettorie quasi identiche ha alta confidence — generalizza meglio, può accettare task leggermente meno simili. Modelli piccoli (Qwen 7B) ne beneficiano perché i loro task tendono ad arrivare con wording più variabile.
- File: `hippoagent/config.py` (3 nuovi knob), `hippoagent/wake.py` (gate riscritto + helper).
- Test: `tests/test_rnd_active_memory.py::test_adaptive_macro_threshold_lowers_with_high_confidence`, `::test_adaptive_threshold_disabled_returns_base`.

### 2) Forward replay — edge-case (failure trace)
- Prima: predicted-path block usava SOLO traiettorie successo (`hippoagent/wake.py:_forward_replay_block`).
- Dopo: aggiunto AVOID-PATH block parallelo che surface l'inizio di una recente traccia FALLIMENTO sulla stessa skill, includendo il critique. Il loop `_retrieve_episodes` adesso pulla anche un budget di failure (k=1) ma solo per il replay — non vanno nel few-shot block (potrebbero confondere il modello come esempi positivi).
- Rationale: hippocampal replay studies (Buzsáki 2015) mostrano che il replay encoda preferenzialmente eventi salient/aversive. Il modello ora "ricorda i suoi errori" e diverge prima dal pattern fallito.
- File: `hippoagent/config.py` (`forward_replay_include_failures`, `forward_replay_max_failure_actions`), `hippoagent/wake.py` (`_avoid_path_block`, `_retrieve_episodes` + `_build_user_prompt` filtra success-only).
- Test: `tests/test_rnd_active_memory.py::test_forward_replay_includes_avoid_path_for_recent_failure`, `::test_forward_replay_no_avoid_path_when_no_failures`. Test esistenti di forward_replay tutti verdi.

### 3) Hebbian — temporal decay (synaptic homeostasis)
- Prima: `learned_embedding` solo pull-to-task on success, mai pull-back. Skill usata 2 volte 6 mesi fa restava incollata a quel topic.
- Dopo: nuovo metodo `SkillLibrary.decay_idle_embeddings()` lerp `learned_embedding` verso il canonical anchor (`encode(name+trigger)`) per skill con `last_used_at < now − 14 giorni`. Se la decayed cosine raggiunge >0.995 di canonical, l'embedding learned viene azzerato (back-to-default). Tracciato `last_used_at` su skill (default 0.0 = "mai usata da quando esiste il feature" → niente decay aggressivo all'avvio).
- Rationale: omeostasi sinaptica (Tononi & Cirelli 2014). Una skill che non spara più non deve restare lock-in su un task one-shot.
- File: `hippoagent/config.py` (4 knob), `hippoagent/skill.py` (campo `last_used_at`, metodo `decay_idle_embeddings`, `update_fitness` setta last_used_at), `hippoagent/sleep.py` (`_stage_pruning` invoca decay).
- Test: `tests/test_rnd_active_memory.py::test_decay_pulls_idle_skill_back_toward_canonical`, `::test_decay_skips_recently_used_skills`, `::test_decay_disabled_is_noop`. Tutti i test Hebbian esistenti (5) restano verdi.

### 4) Counterfactual REM — pre-store dedup
- Prima: cycle ripetuti producevano N copie quasi identiche dello stesso "alternative skill".
- Dopo: `SleepEngine._is_duplicate_skill(candidate)` filtra i counterfactual con (a) name+trigger esatti già esistenti o (b) cosine ≥ 0.90 con la top-1 esistente (usa l'index, non full scan). Counterfactual scartati emit `counterfactual_skipped_duplicate`.
- Rationale: meno noise nel library, più segnale per skill genuinamente nuove. Le retrieve diventano più diversi.
- File: `hippoagent/config.py` (`counterfactual_dedup_threshold=0.90`), `hippoagent/sleep.py` (`_is_duplicate_skill`, gate in `_stage_counterfactual`).
- Test: `tests/test_rnd_active_memory.py::test_counterfactual_skipped_when_alt_duplicates_existing_skill`. Tutti i 4 test counterfactual esistenti restano verdi (uno aggiornato in `test_sleep_full_cycle.py` per riflettere il fix: il mock LLM ora restituisce uno skill effettivamente diverso).

### 5) Schema formation — skip-if-covered
- Prima: ogni sleep cycle re-chiamava l'LLM per sintetizzare schema sui cluster già coperti → spreco di token.
- Dopo: `_cluster_already_covered(cluster)` controlla se esiste già una `stage='schema'` skill con outgoing `specialises` edges → superset del cluster corrente. Se sì, skip (zero LLM calls). Cap `schema_max_per_cycle=2` resta invariato.
- Rationale: idempotenza. Il sleep cycle gira spesso (es. ogni N task) — non deve duplicare lavoro.
- File: `hippoagent/config.py` (`schema_skip_if_covered=True`), `hippoagent/sleep.py` (`_cluster_already_covered`).
- Test: `tests/test_rnd_active_memory.py::test_schema_skips_cluster_already_covered_by_existing_schema`. Tutti i 4 test schema esistenti restano verdi.

### 6) Self-suggested practice — Beta variance prioritisation
- Prima: ordinamento per `abs(0.5 − fitness_mean)` → equipara `2/4` e `10/20` (entrambi mean 0.5) anche se la prima skill è MOLTO più incerta.
- Dopo: ordinamento per `Beta posterior variance` desc. Prima skill prioritizzate sono quelle con varianza alta = sample piccolo + outcomes ambigui. Math: `var = (a*b) / ((a+b)² (a+b+1))` con `a=α+s, b=β+f`. Nuova property `Skill.fitness_variance` esposta pubblicamente.
- Rationale: information-theoretic optimal — practice riduce uncertainty laddove uncertainty è massima, non dove la mean è arbitrariamente vicina a 0.5.
- File: `hippoagent/skill.py` (property `fitness_variance`), `hippoagent/sleep.py` (sort key in `_stage_practice`).
- Test: `tests/test_rnd_active_memory.py::test_fitness_variance_higher_for_smaller_n`, `::test_practice_prioritises_high_variance_skill`. Tutti i 4 test practice esistenti restano verdi.

### 7) Working Memory Pruning (NUOVO meccanismo, 7°)
- Aggiunto: durante il loop wake (sia tools-native che ReAct text), se la stima char-count dei messaggi supera `working_memory_max_chars=24000`, le observation tool_result più vecchie (al di fuori dei `keep_tail=3` finali) vengono compresse a un placeholder. La user-task originale (idx 0) è sempre preservata.
- Rationale: PFC working memory ha capacity limitata; modelli con 32k context (Qwen 7B) hallucinano quando si saturano. Il pruning preserva struttura del message graph mantenendo i tool_use_id e sostituendo solo il `content` testuale → schema dei provider non si rompe. Cap conservativo per default di Qwen; configurable per provider con context più ampio.
- File: `hippoagent/config.py` (5 knob), `hippoagent/wake.py` (`_prune_working_memory` per native tools, `_prune_working_memory_react` per text mode, `_estimate_messages_size`).
- Test: `tests/test_rnd_active_memory.py::test_working_memory_pruning_compresses_old_observations`, `::test_working_memory_pruning_disabled_is_noop`.

## Risultati misurati

- Pytest: 213 → **261/261 verde** (+13 R&D + 35 nuovi test esistenti che ora coprono lineage più completa). Zero regressioni nei 113 test originali del README.
- I fix sono pull-request-ready: ogni meccanismo è gated da un knob CONFIG con valori conservativi, tutti i nuovi test sono property tests deterministici (no LLM, usano embedding stub).
- Bench LLM-driven NON eseguito in questa sessione per evitare spese non autorizzate (Anthropic / DeepSeek). Il prossimo step naturale è girare `python scripts/bench_engram_code.py --provider ollama --model qwen2.5:7b` per confermare che il working_memory_pruning + adaptive_macro_threshold portano qwen da 2/5 → 3/5 e DeepSeek da 3/5 → 4/5 come da target.

## Rischi residui

1. `_is_duplicate_skill` itera su tutte le skill (`self.skills.all()`) per il pass name+trigger — O(N) per cycle. Per library con migliaia di skill bisognerà aggiungere un index. Per ora N≪1000 → trascurabile.
2. `decay_idle_embeddings` viene chiamato ad ogni sleep cycle — se la library cresce molto serve un cap (`hebbian_decay_max_per_cycle=50` già implementato, ma da rivedere se library molto grande).
3. Working memory pruning usa char-count come proxy per token-count — accurato a ~3-4× (1 token ≈ 4 char EN). Per provider con tokenizer accurato (Anthropic) si potrebbe usare `count_tokens` API in futuro.
4. La compressione working memory potrebbe troncare informazione critica per task multi-step lunghi. Mitigation: `keep_tail=3` preserva il contesto recente, e un'observation pruned è chiaramente marcata col placeholder così il modello sa che c'era ma non c'è più.

## Files modificati
- `hippoagent/config.py` — 13 nuovi knob (gating-friendly, valori conservativi)
- `hippoagent/wake.py` — adaptive macro threshold, avoid-path block, working memory pruning, retrieve_episodes con failures
- `hippoagent/skill.py` — `last_used_at`, `fitness_variance`, `decay_idle_embeddings`
- `hippoagent/sleep.py` — counterfactual dedup, schema skip-if-covered, practice variance sort, decay invocation
- `tests/test_rnd_active_memory.py` — 13 property tests (NUOVO)
- `tests/test_sleep_full_cycle.py` — mock LLM aggiornato per riflettere counterfactual dedup
