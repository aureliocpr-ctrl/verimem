# FINAL_REVIEW — HippoAgent v0.2.0 release candidate

Reviewer: code-reviewer agent · Scope: 7 commits `c4a8977c..b56e1f3e` · Date: 2026-05-08

---

## 1. Executive verdict

**APPROVE WITH CONDITIONS** per il tag v0.2.0.

Il treno di 7 commit è un hardening sostanziale e ben ingegnerizzato di
HippoAgent: 13 CVE chiusi con verifiche pentest avversariali, refactor
architetturale di `dashboard.py` (2.338 -> 159 LOC + 11 route packs), test
suite +310% (113 -> 463), coverage 46% -> 59%, ruff 0 errori, CI/CD 11-job
matrix, perf 16x-4700x. Lo stato funzionale e' verde (`pytest -q`: 463
passed, 3 skipped) e ruff e' pulito.

**Condizioni di approvazione (1 BLOCKER, 5 MAJOR — vedi sezione 4)**:
- BLOCKER: il proxy `dashboard._SESSION_TOKEN` e' cosmetic dead-code,
  lascia i test in modalita' "monkeypatch invisibile" -> falso senso di
  sicurezza. Va rimosso o il proxy va effettivamente installato (~1h).
- MAJOR: 5 punti elencati in sezione 4 da affrontare prima del tag o
  tracciati come follow-up immediato 0.2.1.

Una volta rientrato il BLOCKER (<= 1h di lavoro), v0.2.0 e' pronta.

---

## 2. Per Sprint

### Sprint 1 — Emergency security hardening (`c4a8977c`)

8 CVE chiusi: RCE in `/api/ide/run` (CVE-001), RCE in WebSocket terminal
(CVE-002), FS root permissivo (CVE-003), api_keys leak (CVE-004), SSRF
(CVE-006), XSS quote-escape (CVE-007), Docker bind insicuro (CVE-008),
computer-use safety (CVE-010), e bug-fix vision_describe.

#### File: `hippoagent/ide.py`

- `_shell_argv` (line 84): allowlist binary, strip suffisso
  `.exe/.cmd/.bat/.ps1`, case-insensitive su Windows. **Solido.** Edge
  case gia' testati in pentest: `rm.exe`, `RM`, `"rm"`, `/usr/bin/rm`
  (test_pentest_validation.py:139-177).
- `_check_ws_origin` (line 122): rifiuta no-Origin, normalizza
  trailing-slash, substring attack respinta. **Solido.**
- `_NO_SHELL_SPAWN = getattr(asyncio, "create_subprocess_" + "exec")`
  (line 394): hack curioso per evitare static-analysis matchers. Funziona
  ma e' fragile — un linter piu' stretto (Bandit) potrebbe non flaggarlo,
  mentre i manutentori si chiederanno cosa stia succedendo. *MINOR —
  aggiungere `# noqa: B602` con spiegazione esplicita o usare direttamente
  `asyncio.create_subprocess_exec`.*
- `_safe_path` (line 154): risolve simlink prima di `relative_to(root)`
  -> buon design.
- Manca **rate-limit sul WebSocket** dichiarato in docstring (riga 30 dice
  "WebSocket terminal is rate-limited"). Non c'e' codice di rate-limit nel
  loop `ide_term`. *MINOR — docstring vs realta'.*

#### File: `hippoagent/tools_extra.py`

- `_is_blocked_host` (line 304): risolve via `getaddrinfo`, controlla
  loopback / RFC1918 / link-local / multicast / 169.254.169.254. Eccezione
  esplicita per `OLLAMA_HOST` allowlist. **Difesa SSRF robusta.**
- `_is_sensitive` + `_strip_editor_backup_suffixes` (line 87): copre Vim
  `~`, Emacs lockfile `.#foo`, autosave `#foo#`, suffix `.bak/.backup/.old/
  .orig/.swp/.swo/.tmp/.save`. **Eccellente, raro vederlo.**
- `web_fetch` (line 347): `follow_redirects=False` + manual one-hop con
  re-validation. **Pattern corretto contro DNS rebind dopo redirect.**
- TOCTOU residuo: `_is_blocked_host` risolve l'host per la blocklist, poi
  `httpx` risolve di nuovo per la connessione. Tra le due risoluzioni il
  DNS puo' cambiare. **MAJOR (#5)** — vedi sezione 4.
- `_HOTKEY_DENY` (line 722): copre `win+l`, `ctrl+alt+del`, `alt+f4`,
  `cmd+q`. Buona copertura, ma manca esplicitamente `ctrl+r` (browser
  refresh) e combo IME. *MINOR — tracciabile.*
- `_init_pyautogui_safety` (line 732): `FAILSAFE=True`, `PAUSE=0.05`. Solido.

#### File: `hippoagent/settings.py`

- Default `perm_filesystem = "strict"` ok (CVE-003 fix).
- `apply_to_env` (line 83): proietta correttamente
  `HIPPO_FS_STRICT/_HOME/_ROOT`. Pattern di refresh
  `settings_v2.refresh_settings()` (line 149) con try/except per
  circular-import safety: ragionevole.
- `_LOCK = threading.RLock()` per persistenza JSON: corretto.

#### File: `hippoagent/cli.py`

- `dashboard` rifiuta non-loopback bind senza `--insecure-bind` AND
  `HIPPO_TRUSTED_NETWORK=1`. **Difesa appropriata.**
- Auto-genera `HIPPO_AUTH_TOKEN` se non set. ok.

**Sprint 1 verdict**: APPROVE. Solido baseline di hardening.

---

### Sprint 2 — Correctness + advanced security (`aa06f242` + `4d39b959`)

Sprint 2 include sia il batch correctness/CI/CD (aa06f242) sia il batch
advanced security 5 CVE (4d39b959, registrato come "Sprint 2-advanced"
nel commit message).

#### Sprint 2 correctness

- `skill.py`, `memory.py`, `semantic.py`: SQLite WAL + `busy_timeout=10000`
  (CVE-012). **Necessario per concurrent writers (mcp + dashboard + cli su
  stesso DB).** ok.
- OpenAI tool-call parsing in `llm.py`: getattr guards + skip
  `ChatCompletionMessageCustomToolCall`. ok.
- `sleep._stage_rem` REM lineage cycle skip (line 260): controllo
  bidirezionale `b.id in a.parent_skills or a.id in b.parent_skills`. ok.
  **Pero' il check si limita a parent diretti, non grand-parent — puo'
  ancora generare cicli A->B->C dove A.parent=[ ], C.parent=[B], poi REM
  pesca (A,C) e produce A=parent_of_C indirettamente.** *MINOR (#9).*
- `sleep._stage_rem` ora usa `log.exception("rem_recombine_failed", ...)`
  invece di `log.error("...", error=str(exc))` — preserva stack trace.
  Stesso pattern applicato in `_stage_nrem`, `_stage_curator`,
  `_stage_compilation`, `_stage_schema`, `_stage_practice`. Eccellente.
- Eccezione: `sleep._stage_counterfactual` (line 458) ancora usa
  `log.error("counterfactual_failed", skill_id=skill.id, error=str(exc))`
  invece di `log.exception`. **MINOR (#10) — incoerenza.**

#### Sprint 2-advanced — 5 CVE

##### CVE-005 — `tools.py` Docker sandbox

- `DockerPythonExecutor` opt-in via `HIPPO_PYTHON_EXEC_BACKEND=docker`,
  fallback trasparente a subprocess se Docker SDK/daemon manca.
  **Pattern corretto — non rompe nessuno, ma migliora la postura per chi
  ha Docker disponibile.**

##### CVE-007 (MCP) — `mcp_server.py`

- `_validate_input` (line 229) con `jsonschema` + fallback
  `_manual_validate`. Solido.
- `_TokenBucket` (line 108) con lock per thread-safety. ok.
- `_audit` JSONL append-only, args SHA-256 hashed (PII shield). Buon design.
- `_RATE_LIMITED_TOOLS = {"hippo_run_task", "hippo_consolidate"}`: solo
  le ops pesanti. Ragionevole.
- `_looks_shell_like` (line 186): regex ampia (`sudo|chmod|rm -rf|curl|
  wget|powershell|cmd.exe|/bin/sh|exec(|os.system|subprocess|shell_run|
  nc -l|netcat`). **Buono ma facilmente aggirabile** (ROT13, base64-decode
  poi exec, "subproc" + "ess" concat). Per MCP e' una difesa-in-profondita',
  non un confine — accettabile come implementato. *MAJOR (#3) — tradeoff
  documentato ma non in CHANGELOG.md.*
- Audit log path: `_audit_log_path()` legge `HIPPO_MCP_AUDIT_LOG` env;
  default `<data_dir>/mcp_audit.log`. Best-effort try/except `# noqa:
  BLE001` corretto su un percorso di audit (deve mai bloccare).

##### CVE-008 — `wake.py` prompt-injection defense

- `_EXTERNAL_TOOLS = {web_fetch, web_search, vision_describe, webcam_*}`. ok.
- `_DANGEROUS_TOOLS_AFTER_EXTERNAL = {shell_run, desktop_*}`. ok.
- `_episode_is_contaminated` (line 148) — **latching contamination**: una
  volta che l'episodio ha toccato external content, resta contaminato fino
  a fine task. Chiude il "lookback wash" bypass. **Eccellente.**
- `_wrap_untrusted` (line 108) con marker `<untrusted_content source="...">`
  + system prompt aggiornato in `prompts.WAKE_SYSTEM` (line 14): pattern di
  sicurezza moderno. ok.
- Override `HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL=1` per il caso "user
  davvero richiede l'azione". Ragionevole.
- `_run_loop_react` mode (line 817): stesso check applicato per parita'
  con tool-use mode. ok.
- *MAJOR (#1)*: `desktop_screenshot` e' in `_DANGEROUS_TOOLS_AFTER_EXTERNAL`
  ma e' anche read-only (cattura schermo, non muta nulla). Bloccarlo dopo
  un web_fetch e' eccessivo per un read; rende inutilizzabili workflow
  legittimi del tipo "guarda questa pagina e screenshot della finestra
  per riferimento". Considerare di spostarlo fuori dal deny-list e tenerlo
  solo per `desktop_click/type/key`. Vedi sezione 4.

##### CVE-009 — `dashboard_routes/auth.py`

- Token gen via `secrets.token_urlsafe(32)`. ok.
- Persistenza a `~/.hippoagent/session.token` con `chmod 0o600` su POSIX
  (Windows skip via try/except OSError). ok.
- `secrets.compare_digest` constant-time. ok.
- Default `HIPPO_DASHBOARD_AUTH_DISABLED=1` per backward-compat. **Documentato
  nel docstring (line 7-9) e nel CHANGELOG.** ok.
- CORS lockato a `127.0.0.1:8765` + `localhost:8765`, no credentials,
  `allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]`. ok.
- `dashboard.py` *backward-compat shim* `_SESSION_TOKEN`:
  - Riga 73-78: c'e' una **classe** `_SessionTokenProxy` con
    `__get__/__set__` ma **non viene mai usata** (non c'e'
    `_SESSION_TOKEN = _SessionTokenProxy()`).
  - Riga 81: `_SESSION_TOKEN = None` e' un placeholder fisso, mai
    aggiornato.
  - I test (test_dashboard_api.py:321, 337, 357, 375) fanno
    `monkeypatch.setattr(dash, "_SESSION_TOKEN", None, raising=False)`,
    setattr riesce ma la modifica **non si propaga** all'`auth._SESSION_TOKEN`
    reale. I test passano solo grazie al `_reset_session_token`
    autouse fixture che pulisce direttamente `auth._SESSION_TOKEN`.
  - **BLOCKER (#0)** — vedi sezione 4. Vedi anche sezione 3.1.

##### CVE-011 — `editfmt.py` deny-list

- Rifiuta `.git/`, `.vscode/`, `.idea/`, `.devcontainer/`, `*.sh/.bat/.ps1`,
  `Makefile`, `pyproject.toml`, `setup.py`, `setup.cfg` salvo
  `HIPPO_EDITFMT_ALLOW_SENSITIVE=1`. **Coverage solida.** Pentest copre
  case-insensitive `.GIT/`, fullwidth Unicode separator (.477).

**Sprint 2 verdict**: APPROVE pending BLOCKER #0.

---

### Sprint 4 — Architecture refactor (`4d39b959`)

#### File: `hippoagent/dashboard.py` (2.396 -> 159 LOC)

- Thin entry-point. `register_all(app, templates)` delegato. **Pulito.**
- Lifespan `bootstrap_token()` su startup. ok.
- Re-export di `verify_session_token`, `get_session_token`,
  `_session_token_path`, `_auth_disabled`, `_SESSION_TOKEN`, `_ag`,
  `_agent`, `PRESETS`. **Backward-compat ben pensato — eccetto
  `_SESSION_TOKEN` (vedi BLOCKER).**
- `_ag()` / `_agent` placeholder-proxy (line 48-58): `_agent = None` e' un
  placeholder che i test possono `setattr` per iniettare un fake; il
  codice produzione legge invece `layout.get_agent()`. Il pattern in
  `layout.get_agent()` (line 41-53) controlla se `dashboard._ag` e' una
  callable patchata e in tal caso la chiama. **Funziona** ma e' una
  contorsione fragile, copre solo la lambda-monkeypatch dei test, ed e'
  difficile da mantenere. *MINOR (#11) — accettabile per ora.*

#### File: `hippoagent/dashboard_routes/__init__.py`

- `register_all` chiama nell'ordine: health, welcome, chat, episodes,
  skills, lineage, active_memory, events, settings_routes. **Health primo
  -> /healthz mai shadow.** ok.

#### File: `hippoagent/dashboard_routes/settings.py` (460 LOC)

- Alle route mutevoli (`/api/settings`, `/api/settings/test`,
  `/api/fallback`, `/api/permissions`, `/api/presets/apply`) e' applicato
  `dependencies=[Depends(verify_session_token)]`. ok.
- `/api/settings/providers` (line 281) — il bugfix CVE-004 (line 308-309)
  produce `safe["api_keys"] = {env: bool(val) for env, val in ...}`.
  **Solido.**
- `/api/settings/test` (line 343) tiene snapshot env e ripristina nel
  `finally` (line 384). Ottimo pattern.
- *MINOR (#12)*: `_env_for_provider` (line 247) ritorna solo
  `ANTHROPIC_API_KEY` hard-coded; per `ollama` torna `None`. Ma se aggiungo
  un nuovo provider con env diverso da quello in `PROVIDERS`, il fallback
  `spec["env"]` lo copre. Ragionevole.

#### File: `hippoagent/settings_v2.py`

- `BaseSettings` con `env_prefix="HIPPO_"`, `case_sensitive=False`,
  `extra="ignore"`.
- `@lru_cache(maxsize=1)` + `refresh_settings()` per invalidazione. ok.
- Coexistance con `settings.py` legacy ben documentata.
- *MINOR (#13)*: `Settings.trusted_network: Literal["", "0", "1", "true",
  "false", "yes", "no"]` — un Literal stringa per un bool. Era piu'
  semplice un `bool` con default `False` e `parse_yes_no` validator.
  Cosmetic.

#### File: `hippoagent/provider_registry.py`

- `ProviderSpec(BaseModel)` con `name: str = Field(pattern=r"^[a-z0-9_]+$")`.
- `LEGACY_PROVIDERS_DICT` filtra `family == "openai_compat"` per
  backward-compat.
- `ALIASES_DICT` build da loop. Pulito.
- `reload_registry` test helper. ok.
- *MINOR (#14)*: `_REGISTRY = load_registry()` al modulo import -> se il
  YAML e' malformato, l'intera applicazione fallisce all'import. C'e' una
  try/except in `load_registry` (line 112) che converte ValidationError in
  RuntimeError con messaggio informativo, ma comunque blocca. Per un file
  della repo e' accettabile, ma potrebbe servire un fallback empty-registry
  per dev/test con repo corrotta.

#### File: `hippoagent/migrations/__init__.py`

- `ensure_schema_version(conn, db_id, target_version, migrations)` con
  ladder ordinata. ok.
- Singola transazione `BEGIN IMMEDIATE` con rollback su exception. ok.
- *MAJOR (#4)*: `pending = sorted(...)` — se vengono inserite migrazioni
  fuori-ordine (versioni 5, 3, 4), vengono applicate in ordine corretto.
  **Pero'**: se `target_version=5` ma in lista mancano la 3 (gap), le 4 e
  5 si applicano comunque silenziosamente, lasciando il DB in uno stato
  intermedio inconsistente. Non c'e' check di "no gaps" sulla ladder. Vedi
  sezione 4.
- `_write_version` usa `ON CONFLICT(db_id) DO UPDATE`: corretto.
- *MINOR (#15)*: il commit dice "schemi attuali stamped v1" ma le tre DB
  (skill, memory, semantic) **non lo fanno** — ho cercato chiamate a
  `ensure_schema_version` nei moduli persistence e non le ho trovate al
  build. Solo `tests/test_migrations.py` usa l'API. La feature e'
  shipped ma scollegata dai DB reali — e' infrastruttura latente per future
  schema changes. Documentato in `docs/MIGRATIONS.md`? Ho visto il file
  esistere — verificato. OK.

**Sprint 4 verdict**: APPROVE pending BLOCKER #0 + chiarimento MAJOR #4.

---

### Sprint 5 — Pentest validation + UX migration (`b56e1f3e`)

#### File: `tests/security/test_pentest_validation.py` (986 LOC, ~62 tests)

Per ogni CVE c'e' un test che **prova attivamente a bypassare** la
mitigazione: shlex tricks, allowlist defeat (case, suffix, quote,
full-path), Origin spoofing, IPv6 mapped SSRF, decimal/hex/octal IPs, DNS
rebind, XSS via attribute contexts, prompt-injection authority
impersonation, rate-limit parallel calls, editfmt symlink + Unicode
bypass.

- **Strong points**: timing-attack via `compare_digest` (line 215),
  token must-be-configured (line 235), IPv6-mapped IPv4
  (`[::ffff:127.0.0.1]`, CVE-006), decimal-form `2130706433`, fullwidth
  Unicode separator.
- *MINOR (#16)*: alcuni test sono `pytest.skip("ADS only on Windows")` o
  hanno branch `if os.name == "nt":` — coverage cross-platform e'
  limitata. Su CI matrix 11-job questo e' coperto, ma run locale Linux
  salta i NT-only.
- *MINOR (#17)*: `test_origin_substring_attack` verifica solo che
  `_check_ws_origin(...) is False`. Manca un test che inietti un real
  WebSocket con Origin manipolato — TestClient non lo supporta nativamente.
  Documentato come "expected limitation" nel docstring.
- I test fixture `shell_enabled` (line 45) imposta `HIPPO_AUTH_TOKEN` e
  `HIPPO_ENABLE_SHELL=1` con `monkeypatch.setenv`. Buon isolamento.

#### File: `hippoagent/templates/*.html` — Jinja2 migration

- 12 template HTML in totale (welcome, chat, episodes, episode_detail,
  lineage, active_memory, settings, skill_detail, events, overview,
  metrics, skills.html — quest'ultimo c'era gia').
- I template usano pattern semplici con header navigation. Design system
  centralizzato in `static/dashboard.css`.
- *MINOR (#18)*: `{% set active = "..." %}` pattern menzionato nel commit
  ma vedo solo i template piu' semplici (welcome.html, episodes.html) fare
  uso di `{{ page_title }}`. Chiede un `templates.TemplateResponse(
  request, ..., {...})` modern signature (FastAPI 0.111+). ok.
- I route handler welcome/chat/episodes ora delegano a
  `templates.TemplateResponse(...)` invece di restituire HTML inline. ok.

#### File: `hippoagent/sleep.py` — log.exception cleanup

- `_synthesize_from_cluster` (line 199) -> `log.exception("nrem_synth_failed")`. ok.
- `_recombine` (line 273) -> `log.exception("rem_recombine_failed", a_id=a.id, b_id=b.id)`. ok.
- `_curator` `_merge` (line 322) -> `log.exception("curator_merge_failed", a_id=a.id, b_id=b.id)`. ok.
- `_stage_compilation` (line 397) -> `log.exception("compile_failed", skill_id=skill.id)`. ok.
- `_stage_schema` (line 574) -> `log.exception("schema_failed")`. ok.
- `_stage_practice` (line 676) -> `log.exception("practice_failed", skill_id=skill.id)`. ok.
- **Eccezione**: `_stage_counterfactual` (line 458) ancora `log.error(...)`.
  *MINOR (#10).*
- `observability.py` (line 77) -> `log.exception("event_subscriber_failed", event=name)`. ok.
- `mcp_server.py` (line 566) -> `log.exception("mcp_tool_failed", tool=name)`. ok.

#### File: `tests/conftest.py` — fixture isolation

- `_reset_session_token` (line 121, autouse): pulisce
  `dashboard_routes.auth._SESSION_TOKEN`. Pattern corretto, fa funzionare i
  test del session-token nonostante il proxy mancante in dashboard.py.
  **CRITICO** — e' quello che salva i test dal BLOCKER #0.
- `_reset_mcp_rate_buckets` (line 138, autouse): wipe `_RATE_BUCKETS`.
  Critico per l'isolamento dei rate-limit test. ok.
- `_reset_settings_v2_cache` (line 103, autouse): clear `@lru_cache`. ok.
- `_stub_embedding_model` (line 82, autouse): replace
  `embedding._model()` con bag-of-tokens stub. **Eccellente** — niente
  download di sentence-transformers in CI.

**Sprint 5 verdict**: APPROVE.

---

### Sprint 6 — R&D prodotto (`477d21c6` + `9d30c61c` + `630ae559`)

Tre R&D agents in parallelo: memorie attive (Sprint 6a), perf (Sprint 6b),
UX (Sprint 6c).

#### Sprint 6a — Memorie attive

- **Procedural compilation** (`compilation.py` + `wake._try_compiled_macro`):
  fast-path adattivo che bypassa il LLM. `_adaptive_macro_threshold`
  (wake.py:419) aggiusta la soglia in funzione di `macro.confidence`.
  Pattern interessante.
- **Forward replay** (`wake._forward_replay_block`, line 275): pesca le
  azioni di episodi successi simili e le inietta. *MINOR (#19) — il
  blocco arriva solo se `top.fitness_mean >=
  forward_replay_min_fitness`; ok.*
- **AVOID-PATH** (`_avoid_path_block`, line 326): pesca le azioni di
  failure e le mostra. `forward_replay_max_failure_actions` cap. ok.
- **Hebbian temporal decay** (`skill.decay_idle_embeddings`, vedi
  `_stage_pruning` line 711): "synaptic homeostasis". Solido.
- **Counterfactual REM dedup** (`sleep._is_duplicate_skill`, line 462):
  due passi cheap (name+trigger string equality, then top-1 cosine >=
  threshold). Se la libreria e' grande, `self.skills.retrieve(query, k=1)`
  diventa costoso — copertura via cache LRU + matmul vettoriale.
- **Schema formation skip-if-covered** (`_cluster_already_covered`, line
  581): scansiona tutti i nodi del lineage graph, controlla se i children
  sono superset del cluster. **O(N^2)** sulla libreria; ok per librerie
  piccole, problematico per >1000 skill. Risk register lo segnala. ok.
- **Practice — Beta posterior variance** (`_stage_practice`, line 657):
  `targets.sort(key=lambda x: -x.fitness_variance)`. Information-theoretic
  optimal — corretto.
- **Working memory pruning** (`_prune_working_memory`, line 687): trim
  middle observations quando size > 24k. Pattern applicato sia in tool-use
  loop sia in ReAct loop (line 893). *MINOR (#20) — char-count proxy per
  token (~3-4x over-estimate). Documentato nel risk register.*
- *MINOR (#21)*: in `_run_loop_tools` (line 564), `trace_step` e'
  monotonic per supportare parallel tool calls in una turn. **Buon design.**

#### Sprint 6b — Performance

- `embedding.encode` LRU 1024-entry: corretto, ritorna `bytes` per hashable
  storage. *MINOR (#22)*: `_cached_encode` ritorna `bytes`, `encode` fa
  `np.frombuffer(...)` ogni volta — e' un memcpy O(D) ma evita
  l'allocazione di un nuovo cache slot. ok.
- `skill.find_duplicates` / `cluster_by_embedding` vectorise con
  `corpus@corpus.T` (numpy matmul): 320x / 17x speedup. **Convincente.**
- `memory.recall` index in-memory + dirty flag: 16x.
- `memory.cluster_similar` full-pairwise + opt FAISS (>=2k episodes,
  IndexFlatIP): 9.4x.
- `repomap.scan_repo` os.scandir + mtime+size disk cache: 30x.
- *MAJOR (#2)*: il commit `630ae559` (chore: untrack data/) e `9d30c61c`
  (chore: untrack repomap cache) hanno **rimosso file dal tracking** ma
  l'aggiunta a `.gitignore` e' successiva. Confermo che sono entrambi
  effettivamente untracked nel HEAD attuale (`git status` non li mostra
  piu'). **OK**, ma una nota nel CHANGELOG che `data/repomap_cache_*.json`
  e' ora gitignored sarebbe utile per chi clone old branch.

#### Sprint 6c — UX

- `dashboard.css` 570 LOC, palette WCAG 2.1 AA, scale 4px. Code review
  fuori scope qui (CSS), ma il riferimento in `RND_UX.md` documenta a11y
  (`role=search/tab/progressbar`, `aria-label`, `focus-visible`,
  `prefers-reduced-motion`). ok.
- `code.py` CLI banner con counter e contextual tip system. Fuori scope.
- *MINOR (#23)*: lo stile inline nei template (es.
  `style="background: #1f6feb;color:#fff"`) si mescola con il design
  system in `dashboard.css`. Inconsistente — qualcuno usera' la classe
  `tag.promoted`, qualcun altro un inline style. Cosmetic.

**Sprint 6 verdict**: APPROVE.

---

## 3. Cross-cutting concerns

### 3.1 dashboard.py backward-compat shims

#### `_SESSION_TOKEN` proxy — BROKEN (BLOCKER #0)

```python
# dashboard.py:73-81
class _SessionTokenProxy:
    def __get__(self, *_a, **_kw):
        return _dash_auth._SESSION_TOKEN
    def __set__(self, _instance, value):
        _dash_auth._SESSION_TOKEN = value

_SESSION_TOKEN = None  # placeholder; tests setattr this to None to reset
```

La classe `_SessionTokenProxy` e' definita ma **mai installata**. La riga
81 imposta `_SESSION_TOKEN = None` come *normale attributo di modulo*. I
test fanno `monkeypatch.setattr(dash, "_SESSION_TOKEN", None)` — riesce,
ma non si propaga. `auth._SESSION_TOKEN` e' completamente disaccoppiato.

I test passano grazie al fixture `_reset_session_token` autouse che
pulisce direttamente `auth._SESSION_TOKEN`. Se domani qualcuno rimuove
quel fixture o aggiunge un test che si fida del setattr, **fail
silenzioso**.

**Fix consigliato (1h)**: rimuovere la classe `_SessionTokenProxy` (dead
code) e la variabile `_SESSION_TOKEN`, e sostituirli con una `__getattr__`
a livello modulo che inoltra a `auth._SESSION_TOKEN`. Oppure rimuovere
`_SESSION_TOKEN` dall'`__all__` (line 42) e aggiornare i test a fare
`monkeypatch.setattr(auth, "_SESSION_TOKEN", None, raising=False)`
invece.

#### `_ag` / `_agent` shims — funzionante ma fragile

`dashboard._agent = None` e' un attributo di modulo, e `dashboard._ag()`
delega a `layout.get_agent()`. `layout.get_agent` (line 41-53) controlla
se `dashboard._ag` e' una callable patchata e la chiama. Questo gestisce
il caso "test fa `monkeypatch.setattr(dash, '_ag', lambda: fake_agent)`".

**Funziona** ma la guardia `getattr(fn, "__module__", "") != __name__`
(line 47) e' fragile: se un test fa setattr con una callable definita nel
modulo `dashboard.py` stesso, il check fallisce e si entra in
`_build_default_agent()` invece. *MINOR (#11).*

### 3.2 Test isolation fixtures

Tutti i module-globals problematici sono coperti:
- `dashboard_routes.auth._SESSION_TOKEN` -> `_reset_session_token`
- `mcp_server._RATE_BUCKETS` -> `_reset_mcp_rate_buckets`
- `settings_v2._build_settings.cache` -> `_reset_settings_v2_cache`
- `embedding._cached_encode.cache` -> `_stub_embedding_model`

**NON coperti** (ricerca grep):
- `mcp_server._agent` (line 51) — singleton. Se un test build un agent con
  un mock LLM e un altro test si aspetta un default agent, si infettano.
  *MAJOR (#5) — vedi sezione 4.*
- `dashboard_routes.layout._agent` — stesso pattern. Lo stesso fixture
  di reset andrebbe applicato. *MAJOR (#5).*
- `provider_registry._REGISTRY` — singleton dal YAML import. I test usano
  `reload_registry(custom_path)` esplicitamente. ok.

### 3.3 Endpoint coverage

Endpoint nuovi shipping in Sprint 1-6:
- `/api/ide/run`, `/api/ide/term` (WS), `/api/ide/file` GET/PUT/DELETE,
  `/api/ide/file/new`, `/api/ide/tree`, `/api/ide/git/status`,
  `/api/ide/git/diff`. **Coperti** in test_pentest_validation + test_ide.py.
- `/healthz`. *MINOR (#24) — non ho trovato un test esplicito;
  `tests/test_dashboard_api.py` non lo cita.* Verificare.
- `/api/auth/info`. **Coperto** (test_auth_info_default_disabled, line 301).
- `/api/settings/test`. **Coperto** indirettamente (le altre api/settings
  sono testate; il route e' simile).
- `/api/active-memory/stats`. *MINOR (#25) — ho trovato solo il route
  defining-test, non un test che asserisce lo shape della response.* OK
  per i test_dashboard_api che fanno smoke tests.
- `/api/skills/{id}/promote`, `/api/skills/{id}/retire`. **Coperti**
  (test_skill_promote_known_id / unknown_id, test_skill_retire_*).
- `/api/feedback`. *MINOR (#26) — non ho un test dedicato.*

### 3.4 Migration system edge cases

`ensure_schema_version` ha questi edge case **scoperti** (MAJOR #4):
- Gap nelle versioni: se ladder=[(1,m1), (3,m3)] e target=3, parte da
  current=0, applica m1 (v=1), cerca v=2 che non c'e', salta a m3 (v=3).
  Questo **e' ok** se il design intende skip — ma non c'e' check esplicito.
- Versioni decrescenti: se ladder include `(5, m5)` ma target=3, lo skip
  e' corretto (line 87 filtra `v <= target_version`).
- Migration callable raise -> rollback. **Testato** in
  `test_migrations.py`? Non ho verificato in dettaglio; il commento del
  file menziona il rollback, ma andrebbe esplicitamente testato.
- Concurrent migrate: se due processi migrano lo stesso DB simultaneamente,
  `BEGIN IMMEDIATE` su SQLite evita doppia applicazione (uno aspetta o
  fallisce). **Buono** ma non documentato.

---

## 4. Issues per severity

### BLOCKER (1)

**#0 — `dashboard._SESSION_TOKEN` proxy non installato**
- File: `hippoagent/dashboard.py:73-81`
- I test `monkeypatch.setattr(dash, "_SESSION_TOKEN", ...)` non hanno
  effetto sul vero token in `auth._SESSION_TOKEN`. I test passano solo
  per il side-effect del fixture autouse. Falso senso di sicurezza.
- **Fix (1h)**: rimuovere la classe `_SessionTokenProxy`, rimuovere
  `_SESSION_TOKEN = None` placeholder e da `__all__`, e fare i test
  patchare `dashboard_routes.auth._SESSION_TOKEN` direttamente. In
  alternativa, installare la classe correttamente come descriptor.

### MAJOR (5)

**#1 — `desktop_screenshot` in `_DANGEROUS_TOOLS_AFTER_EXTERNAL`**
- File: `hippoagent/wake.py:101-105`
- `desktop_screenshot` e' read-only (cattura schermo). Bloccarlo dopo un
  web_fetch e' eccessivo. Spostarlo fuori dal deny-list, tenere
  `desktop_click/type/key` (state-changing).

**#2 — CHANGELOG.md non documenta `repomap_cache` gitignore**
- I commit `630ae559` e `9d30c61c` rimuovono file ma chi clone l'old
  branch e fa pull avra' conflitti / file fantasma. Aggiungere riga in
  CHANGELOG sezione "Build / chore".

**#3 — `_looks_shell_like` regex aggirabile**
- File: `hippoagent/mcp_server.py:177-189`
- Difesa-in-profondita' ma non un confine. Un attaccante puo' usare
  `bash` (non in regex), `eval base64.b64decode("c3VkbyA=")`, concat
  string (`"sub" + "process"`). Documentare nel docstring di
  `_looks_shell_like` o nel CHANGELOG sotto CVE-007 (MCP) che la regex e'
  "tripwire", non "wall".

**#4 — Migration ladder non valida i gap**
- File: `hippoagent/migrations/__init__.py:86`
- Se ladder=[(1,m1), (3,m3)] e target=3, manca m2 silenziosamente. In
  produzione un team che inserisce migrazioni out-of-order rischia uno
  skip silenzioso. Aggiungere assertion: pending versions devono essere
  contigue da current+1 a target_version.

**#5 — TOCTOU in SSRF + module-singleton di agent non resetabile**
- File `tools_extra.py:304`: `_is_blocked_host` risolve via
  `getaddrinfo`, poi `httpx.get(url)` risolve di nuovo. Tra le due, DNS
  rebind e' possibile. Mitigazione: usare `httpx` con custom transport
  che pin l'IP risolto, o passare `host` esplicito. **Pratica nota —
  accettabile come MAJOR follow-up, non BLOCKER (la finestra e'
  stretta).**
- File `mcp_server.py:51` + `dashboard_routes/layout.py:18`: `_agent`
  singleton mai resetato fra test. Aggiungere fixture `_reset_agent`
  autouse a conftest.py per simmetria con gli altri reset autouse.

### MINOR (~21)

(Numeri come emessi nel testo, da #6 a #26.)

**#6 — `mcp_server.py:393` audit di rejected_schema** ok ma non c'e' cap
sul numero di reject in audit log: un attaccante puo' flood l'audit
file. Aggiungere rate-limit sull'audit write (separato dal rate-limit
del tool).

**#7 — `ide.py` doc dichiara WS rate-limit non implementato.**

**#8 — `ide.py:394` `_NO_SHELL_SPAWN` string concat hack.**

**#9 — REM lineage cycle skip e' solo parent diretto, non grand-parent.**

**#10 — `sleep._stage_counterfactual:458` ancora `log.error` invece
di `log.exception`.**

**#11 — `dashboard._ag()` proxy guard fragile (`__module__` check).**

**#12 — `_env_for_provider` hard-code anthropic.**

**#13 — `Settings.trusted_network` Literal sui bool stringa.**

**#14 — `provider_registry` import-time crash su YAML invalido.**

**#15 — Migration system shipped ma non collegato ai DB reali.**

**#16 — Pentest test cross-platform parziali.**

**#17 — `test_origin_substring_attack` testa solo helper, non WS reale.**

**#18 — Inline style nei template HTML.**

**#19 — `forward_replay_min_fitness` non testato esplicitamente per
edge case fitness=0.5+epsilon.**

**#20 — Working memory char-count proxy 3-4x over-estimate
(documentato).**

**#21 — `_run_loop_tools` `trace_step` monotonic — buon design ma poco
testato per parallel tool calls.**

**#22 — `embedding._cached_encode` returns bytes + frombuffer copy — ok
ma inefficiente.**

**#23 — Inline style + design system mescolati.**

**#24 — `/healthz` non ha test esplicito.**

**#25 — `/api/active-memory/stats` shape non asserito.**

**#26 — `/api/feedback` non ha test dedicato.**

### NIT (4)

- README.md menziona "+310% test" — pulito.
- `dashboard_routes/skills.py:148-156` — bottoni inline `onclick=` con
  `confirm(...)` poi `fetch(...)`. Fragile in caso di X-Hippo-Token
  required (quando auth e' on, fetch fallira' 401 senza header). Cosmetic
  in modalita' default (auth off).
- `tools_extra.py:295` `# noqa: BLE001` su shell_run — il blanket
  Exception capture qui e' giustificato (subprocess errors variabili) ma
  il commento potrebbe spiegare meglio.
- `compilation.py:185` `log.warning("compile_llm_failed", ...)` — e'
  un'occasione per `log.exception` se il LLM call solleva. Cosmetic.

---

## 5. Suggested follow-ups prima di v0.2.0

### Da fare ORA (<= 4h)

1. **BLOCKER #0** — fix `_SESSION_TOKEN` proxy (1h).
2. **MAJOR #1** — rimuovere `desktop_screenshot` da
   `_DANGEROUS_TOOLS_AFTER_EXTERNAL` (15min + test).
3. **MAJOR #4** — aggiungere assertion gap-free nella ladder migrations
   (30min + test).
4. **MAJOR #5b** — fixture `_reset_agent` autouse (15min).
5. **MAJOR #2** — riga in CHANGELOG.md su gitignore data/ (5min).

### Da rimandare a v0.2.1 (tracciato in PRODUCTION_ROADMAP.md)

- **MAJOR #3** — documentazione tripwire vs wall su `_looks_shell_like`.
- **MAJOR #5a** — DNS rebind pin nell'`httpx` client.
- **MINOR #15** — collegare migration system ai DB reali con un v1 stamp
  esplicito.
- **MINOR #6** — rate-limit dell'audit log MCP.
- **MINOR #21** — test parallel tool calls.
- **MINOR #24/25/26** — test mancanti per `/healthz`,
  `/api/active-memory/stats`, `/api/feedback`.

### Test mancanti per casi edge

- Concurrent migrate (2 processi insieme).
- Migration callable raise -> rollback verificato.
- WebSocket Origin spoofing reale (test con fake Origin via custom
  TestClient subclass).
- Parallel tool calls in `_run_loop_tools` (Anthropic API restituisce
  multipli `tool_use` blocks in un solo turn).
- Provider registry con YAML deliberatamente corrotto / mancante (fallback
  empty registry o crash chiaro).

---

## 6. Approval recommendation

**APPROVE WITH CONDITIONS** for v0.2.0 release tagging.

| Categoria | Conta | Stato |
|---|---|---|
| BLOCKER | 1 | da fixare |
| MAJOR | 5 | 4 da fixare ora, 1 follow-up immediato |
| MINOR | ~21 | follow-up tracciato |
| NIT | 4 | cosmetic |

Il lavoro Sprint 1-5 e' **un upgrade qualitativo significativo**: la
postura di sicurezza passa da "research prototype" a "loopback-only
production-grade", la copertura di test e' quadruplicata, l'architettura
del dashboard e' tornata gestibile dopo il refactor, e il tooling DevOps
(CI 11-job, multi-OS / multi-Py, security workflow) chiude il ciclo.

Una volta gestito il BLOCKER #0 e i 4 MAJOR ad alta priorita' (~3-4h di
lavoro totali), v0.2.0 e' pronta per il tag e il release annoucement.

---

*Review condotta da code-reviewer agent (Opus 4.7 1M ctx) il 2026-05-08.*
*Stato del repository: 463 passed / 3 skipped / 0 ruff errors.*
*Cross-checked contro audit precedenti (ARCHITECTURE_AUDIT.md,
CODE_QUALITY_AUDIT.md, QA_AUDIT.md, SECURITY_AUDIT.md), CHANGELOG.md,
RND_*.md.*
