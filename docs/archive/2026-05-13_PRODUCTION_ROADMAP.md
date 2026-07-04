# HippoAgent / EngramCode — Production Roadmap

**CTO**: team-lead
**Date**: 2026-05-07
**Inputs**: ARCHITECTURE_AUDIT.md, CODE_QUALITY_AUDIT.md, QA_AUDIT.md, SECURITY_AUDIT.md
**Goal**: take the project from R&D prototype to **vendible, production-grade, no-bug** state.

---

## Executive verdict

The cognitive core (memory consolidation, 6 active-memory mechanisms, sleep/wake loop, skill library) is scientifically rigorous and **A-tier coverage** (>87%). The **perimeter is the problem**: CLI/IDE/MCP/dashboard/tools_extra carry 3 CRITICAL RCEs, 6 HIGH issues, and ~1k LOC at 0% coverage. Six focused sprints close the gap.

**Convergent CRITICAL findings (4/4 audits agree)**:
1. **RCE in `/api/ide/run`** (`ide.py:241-279`) — `subprocess.run(body.cmd, shell=True)`, no auth, no gate.
2. **RCE in `/api/ide/term` WebSocket** (`ide.py:285-355`) — `asyncio.create_subprocess_shell(cmd)`, no Origin check.
3. **Sandbox is theatre** — `subprocess -I` isolates Python imports only, not FS/net/processes.
4. **API keys plaintext** in `data/user_settings.json`, leakable via the agent's own `fs_read_file` (because `data_dir` is an allowed FS root by default).
5. **FS root defaults to `$HOME`** (`tools_extra.py:48-65`) — LLM can write to `~/.ssh/authorized_keys`, IDE configs, etc.
6. **`dashboard.py` is 2,338 LOC monolith** — un-reviewable, untestable.

---

## Sprint 1 — Emergency Security Stop (TARGET: this session)

Goal: close every same-day P0 vulnerability so the dashboard is safe to run beyond a trusted single-user box.

| # | Item | Source | Files | Status |
|---|------|--------|-------|--------|
| 1.1 | Gate `/api/ide/run` + `/api/ide/term` behind `HIPPO_ENABLE_SHELL` + bearer token + Origin check | SEC V1, V2 | `ide.py`, `dashboard.py` | TODO |
| 1.2 | Default `perm_filesystem = "strict"`; deny-list `~/.ssh`, `~/.aws`, `~/.gnupg`, `**/credentials*`, `**/*.pem` | SEC V4, ARCH #2 | `settings.py`, `tools_extra.py` | TODO |
| 1.3 | Strip `api_keys` from every HTTP response | SEC V15 | `dashboard.py` | TODO |
| 1.4 | Refuse `--host 0.0.0.0` unless `HIPPO_TRUSTED_NETWORK=1`; loud warning in README/Dockerfile | SEC V8 | `cli.py`, `Dockerfile`, `README.md` | TODO |
| 1.5 | Drop `shell=True` in `ide.py`; use `shlex.split` + binary allowlist | SEC V1 | `ide.py` | TODO |
| 1.6 | Origin/Host validation on WebSocket `accept()` | SEC V2 | `ide.py` | TODO |
| 1.7 | Add SSRF blocklist in `web_fetch` (RFC1918, link-local, metadata, loopback) | SEC V10 | `tools_extra.py` | TODO |
| 1.8 | Replace `_html_escape` with `html.escape(quote=True)`; remove inline `onclick=` | SEC V7 | `dashboard.py` | TODO |
| 1.9 | Add `.gitignore` entry for `*.egg-info/`; `git rm -rf --cached hippoagent.egg-info/` | ARCH #10 H | repo root | TODO |
| 1.10 | Quick correctness fixes: vision_describe kwargs (#4), list_models guards (#5), OpenAI tool parse (#12), pyautogui FAILSAFE (V11) | CQ #4,5,12; SEC V11 | `code.py`, `llm.py`, `tools_extra.py` | TODO |

**Exit criterion**: pytest green, ruff clean on touched files, no new CRITICAL/HIGH at security re-audit.

---

## Sprint 2 — Advanced Security (DONE 2026-05-08)

Status: 5/5 CVE chiusi. Tests: 366 passed (baseline 299 + 67 nuovi).
Lines changed: ~750 add, ~50 mod across 5 modules + 4 nuovi test files.

| # | CVE | Status | Files | Tests added |
|---|-----|--------|-------|-------------|
| 2.1 | CVE-005 sandbox containerizzato | DONE | `tools.py` (DockerPythonExecutor + factory) | `tests/security/test_python_executor_isolation.py` (8 test) |
| 2.2 | CVE-007 MCP schema/audit/rate-limit/perm gate | DONE | `mcp_server.py` (validation, JSONL audit, token-bucket, shell-perm gate) | `tests/test_mcp_server_security.py` (15 test) |
| 2.3 | CVE-008 prompt-injection defense | DONE | `wake.py` + `prompts.py` (`<untrusted_content>` wrapper, dangerous-after-external review hook) | `tests/security/test_prompt_injection_defense.py` (15 test) |
| 2.4 | CVE-009 dashboard CORS + session token | DONE | `dashboard.py`, `dashboard_routes/auth.py` (locked CORS allowlist, `verify_session_token` dep, constant-time compare) | `tests/test_dashboard_api.py` (5 nuovi test auth) |
| 2.5 | CVE-011 editfmt deny-list | DONE | `editfmt.py` (block `.git/`, `.vscode/`, `*.sh`, `pyproject.toml`, etc.) | `tests/security/test_editfmt_sensitive.py` (24 test) |

### Implementation notes
- **Backwards compatibility**: Dashboard auth defaults DISABLED via `HIPPO_DASHBOARD_AUTH_DISABLED=1`. Operators harden by setting `=0` for non-loopback / multi-user contexts. The 299 baseline tests run unchanged.
- **Docker fallback**: `make_python_executor()` reads `HIPPO_PYTHON_EXEC_BACKEND`. If `=docker` and Docker SDK/daemon missing, transparently falls back to subprocess + emits warning event.
- **Audit log**: `data/mcp_audit.log` JSONL, append-only, args hashed (SHA-256 prefix 16 chars) — never logs raw payloads. Override path via `HIPPO_MCP_AUDIT_LOG`.
- **Rate limit**: token-bucket in-memory, 1/min default for `hippo_run_task` and `hippo_consolidate`. Override via `HIPPO_MCP_RATELIMIT_<TOOL>_{CAP,RPM}` env. Disable in tests via `HIPPO_MCP_DISABLE_RATELIMIT=1`.
- **Prompt-injection review**: `_DANGEROUS_TOOLS_AFTER_EXTERNAL` blocked when last 3 traces include `web_fetch`/`vision_describe`/`web_search`. Override: `HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL=1`.

---

## Sprint 3 — Correctness & Resilience (1 week)

| # | Item | Source | Files |
|---|------|--------|-------|
| 3.1 | Define exception taxonomy: `LLMError`, `ProviderError`, `RateLimitError`, `MemoryError`, `ToolError` | ARCH HIGH #5 | new `errors.py` |
| 3.2 | Replace 44 `except Exception` BLE001 with specific catches at boundaries; convert `log.error("...", error=str(exc))` to `log.exception()` | CQ #20, SEC V13 | all modules |
| 3.3 | SQLite `PRAGMA journal_mode=WAL; busy_timeout=10000` in every `_connect()` | CQ #11 | `skill.py`, `memory.py`, `semantic.py` |
| 3.4 | FallbackLLM: per-provider failure rate tracking, demote within sliding window | CQ #6 | `llm.py` |
| 3.5 | Replace 9 `except: pass` with `log.exception` + re-raise | SEC V13 | `settings.py`, `wake.py`, `code.py` |
| 3.6 | Auto-fix ruff: remove 19 unused imports (F401/F811/F541) | CQ ruff | hippoagent/* |
| 3.7 | LRU cache on `embedding.encode` (1024 entries) | ARCH J | `embedding.py` |
| 3.8 | Fix vision_describe Anthropic content union typing (#16) + cache token accounting | CQ #16 | `tools_extra.py` |
| 3.9 | Fix REM recombination lineage cycle check (#13) | CQ #13 | `sleep.py` |
| 3.10 | Refactor: extract `_with_retries(call_fn, label)` helper; replace 4× duplicated retry loops in llm.py | CQ #15 | `llm.py` |

---

## Sprint 3 — Test Foundation + Test-Driven Hardening (1 week)

Goal: P0 test files from QA plan + security regression suite.

| # | Item | Source | Target |
|---|------|--------|--------|
| 3.1 | `tests/conftest.py` stub `embedding._model` with deterministic hash (rimuove HF dep, CI -25s) | QA I-1 | conftest |
| 3.2 | `tests/security/test_path_traversal.py` — `editfmt.apply_block` deny-list, FS strict, symlink escape | SEC V4, V11 | new |
| 3.3 | `tests/security/test_csrf.py` — assert state-changing routes require token | SEC V6 | new |
| 3.4 | `tests/security/test_secrets_redaction.py` — observability + dashboard responses | SEC V5, V15 | new |
| 3.5 | `tests/security/test_ssrf.py` — `web_fetch` blocklist | SEC V10 | new |
| 3.6 | `tests/security/test_prompt_injection.py` — untrusted content wrapper | SEC V3 | new |
| 3.7 | `tests/test_settings.py` — perm_* gates effectively disable capabilities | QA P0 I-7 | new |
| 3.8 | `tests/test_tools_extra_fs.py` + `_shell.py` + `_web.py` + `_capabilities.py` — sandbox boundaries | QA P0 | new × 4 |
| 3.9 | `tests/test_cli.py` — typer CliRunner per subcommand | QA P0 | new |
| 3.10 | `tests/test_dashboard_api.py` — TestClient on 38 routes | QA P0 | new |
| 3.11 | `tests/test_mcp_server.py` — stdio JSON-RPC contract | QA P0 | new |
| 3.12 | `tests/test_llm_providers.py` — respx mock matrix per provider | QA P0 | new |

**Exit criterion**: coverage ≥ 70% (from 46%), all security tests green.

---

## Sprint 4 — Architecture & Storage (1.5 weeks)

Big refactors enabled by safety net from Sprint 3.

| # | Item | Source | Files |
|---|------|--------|-------|
| 4.1 | Split `dashboard.py` (2338 LOC) → `dashboard/__init__.py` + `routes/*.py` + `templates/*.html` + `static/*.js` | ARCH C #1 | dashboard/ |
| 4.2 | Migrate config to `pydantic-settings`; remove 65 scattered `os.environ.get` | ARCH HIGH #6 | `settings/` |
| 4.3 | Move LLM provider registry to YAML + Pydantic spec; add `hippo provider check <name>` round-trip diagnostic CLI | ARCH C #3 | `llm/`, `providers.yaml` |
| 4.4 | Skill storage atomicity: pick SQLite-only OR transactional JSON+SQLite; add `rebuild_index_from_files()` recovery | ARCH C #4 | `skill.py` |
| 4.5 | Add Alembic migrations for the 3 SQLite DBs | ARCH HIGH #8 | `migrations/` |
| 4.6 | Pydantic models for every FastAPI request body and MCP tool inputSchema | ARCH HIGH #7 | `dashboard/`, `mcp_server.py` |

---

## Sprint 5 — Sandbox Hardening (1 week)

| # | Item |
|---|------|
| 5.1 | `containerised_executor.py` (Docker SDK; `--network=none`, `--cap-drop=ALL`, ephemeral volume) |
| 5.2 | Linux fallback: `firejail`/`bubblewrap` |
| 5.3 | Macros: `compilation.execute_macro` reviewed for the same prompt-injection rules |
| 5.4 | OS keychain via `keyring` for API keys |
| 5.5 | Untrusted-content `<untrusted source="...">` wrapper around web/vision/file-read tool results in agent prompt |
| 5.6 | Audit log (HMAC-chained) of every tool execution |

---

## Sprint 6 — DevOps + Distribution (1 week)

| # | Item |
|---|------|
| 6.1 | CI matrix 3 OS × Py 3.10/3.11/3.12/3.13 with coverage gate `--cov-fail-under=85` |
| 6.2 | Smoke install: `pip install .` + `engram --help` on a clean venv |
| 6.3 | `pip-audit` and `safety` job in CI |
| 6.4 | Multi-stage Dockerfile → ≤ 500 MB |
| 6.5 | Pip extras: `[headless]`, `[mcp-only]`, `[full]` (default = headless) |
| 6.6 | PyInstaller standalone Windows binary |
| 6.7 | PyPI publish workflow (`0.2.0` RC) |

---

## Sprint 7-8 — Documentation + v1.0 (2 weeks)

| # | Item |
|---|------|
| 7.1 | ADRs for the 6 active-memory mechanisms |
| 7.2 | Sphinx API reference; tutorial "Build a sleep-consolidating agent in 30 minutes" |
| 7.3 | `docs/SECURITY.md`, `docs/SUPPORTED_DEPLOYMENT.md`, `docs/THREAT_MODEL.md` |
| 7.4 | `CHANGELOG.md` from 0.1.0 to 1.0.0 |
| 7.5 | Migration guide 0.1.x → 1.0 |
| 7.6 | Final security re-audit + pentester pass |
| 7.7 | Tag `v1.0.0`, publish wheels to PyPI |

---

## Aggregate metrics

| Metric | Today | Sprint 1 exit | Sprint 3 exit | v1.0 |
|---|---|---|---|---|
| CRITICAL vulns | 3 | **0** | 0 | 0 |
| HIGH vulns | 6 | 2 | 0 | 0 |
| Coverage | 46% | 50% | 70% | 90% |
| Test cases | 110 | 130 | 250 | 400+ |
| Ruff errors | 33 | <5 | 0 | 0 |
| LOC dashboard.py | 2338 | 2338 | 2338 | <300/route file |
| `except: pass` | 9 | 0 | 0 | 0 |
| BLE001 | 44 | 30 | 5 | 0 |
| 0%-cov modules | 4 | 4 | 0 | 0 |

---

---

## Sprint 7 — Hippo Dreams subscription-first (2026-05-13 → in progress)

**Direttiva fondamentale Aurelio** (fact `d4dd857b1eea`, `preferences/aurelio`):
HippoAgent deve usare la subscription Claude Code come base sempre e comunque.
La modalità `ANTHROPIC_API_KEY` separata diventa opt-in per utenti pubblici.

**Background**: `hippo_consolidate` è BLOCCATO in hosted mode (`mcp_server.py:3991-4004`) perché `engine.cycle()` fa LLM call internamente via env API key — costo separato dalla subscription. Conseguenza misurata: solo 5 promoted su 318 skill (1.5%), sleep cycle non gira da 5+ giorni, vera evoluzione genealogica ferma (4% derived_from edges).

**Architettura nuova** (ispirata a Anthropic Dreams + Google ReasoningBank + MemSkill — vedi `STATE_OF_HIPPOAGENT_2026-05-13.md` §10):

| Cycle | Tool MCP | Funzione | Status |
|---|---|---|---|
| #34 ✅ | `hippo_dream_create_shadow` | Snapshot immutabile dei live DB | MERGIATO PR #25 |
| #35 | `hippo_dream_propose` | Prepara cluster + prompt template, **zero LLM internal** | TODO |
| #36 | `hippo_dream_submit_result` | Claude (host) passa skill JSON post-LLM-call, persiste su shadow | TODO |
| #37 | `hippo_dream_status` / `list_pending` / `diff` | Review proposed vs live | TODO |
| #38 | `hippo_dream_adopt` | Apply atomico con backup + rollback | TODO |
| #39 | (test) | E2E integration test + benchmark evoluzione reale | TODO |
| #40+ | (refactor) | Rimozione blocco hosted, inversione default, `HIPPO_USE_OWN_API_KEY` opt-in, doc pass | TODO |

**Exit criterion Sprint 7**: `corpus_health_score` ≥ 70 (oggi 56.38), `promoted_frac` ≥ 10% (oggi 2.94%), `derivedness` ≥ 0.5 (oggi 0.26), zero `ANTHROPIC_API_KEY` requirement in default flow.

**Regole non negoziabili** (fact `cd1af54f127e`):
1. READ-first via `hippo_recall` + audit codice prima di scrivere
2. Ricerca paper/blog/GitHub prima di decisioni architetturali grandi
3. TDD red→green ogni cycle
4. Critic-orchestrator 3-worker post-implementation (pattern documentato in fact `7377054b0971`)
5. Live test su corpus reale + live test malevolo
6. Commit+push+PR+merge main per ogni cycle chiuso
7. `hippo_record_episode` al termine
8. Sincerità assoluta: se critic boccia, dico subito + fix

---

## Decisione: cosa parto a fare adesso

**Sprint 1 immediato**, in autonomia totale:
1. Fix V1/V2 RCE (gate IDE shell + token + Origin)
2. Fix V4 FS strict default
3. Fix V15 api_keys leak
4. Fix V8 Docker/README 0.0.0.0
5. Drop shell=True in ide.py
6. SSRF blocklist
7. Correctness: vision_describe kwargs, list_models guards, pyautogui FAILSAFE
8. .gitignore *.egg-info/
9. Run pytest + ruff check, verify nothing breaks

Poi spawnerò code-reviewer per sign-off, e devops-engineer per CI matrix.
