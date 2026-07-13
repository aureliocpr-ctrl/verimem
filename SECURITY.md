# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities **privately** via GitHub Security
Advisories — open one at
[Security ▸ Report a vulnerability](https://github.com/aureliocpr-ctrl/verimem/security/advisories/new).
Do **not** open a public issue for a security report.

We aim to acknowledge a report within 72 hours and to ship a fix or mitigation
for confirmed, in-scope issues as a priority.

## Supported versions

Engram is pre-1.0; security fixes land on `main` and the latest release
(currently `0.3.x`). Pin a released version for production and watch releases.

## Security posture (know before you run)

Engram is a **memory layer**; in the default MCP / hosted mode it performs
**no LLM calls and no code execution** — it is SQLite reads/writes plus local
embedding. The optional **standalone agent** (`hippo run`, `hippo chat`,
`hippo_run_task`) can execute tools, and there the trust model matters:

- **The Python sandbox is `subprocess -I`, not a hard isolation layer.** Agent-
  generated code can touch the filesystem and network. Run the standalone agent
  only against models and tasks you trust, or in Docker with no host mounts.
- **Dashboard** state-changing endpoints are gated by a per-session
  `X-Hippo-Token` header; the dashboard binds to `127.0.0.1` by default. Do not
  expose it on `0.0.0.0` without a reverse proxy + auth.
- **Secrets**: API keys entered via the dashboard are stored in
  `data/user_settings.json` (gitignored, plaintext). For production, supply keys
  via environment variables / a secrets manager instead.
- **Air-gap**: `engram airgap` self-checks that a config makes zero network
  egress (local LLM + `HF_HUB_OFFLINE=1` + hosted-mode off).

## Memory-poisoning & prompt-injection screening

A memory store is itself an injection surface: poisoned content saved as a
"fact" is later recalled *verbatim* into the agent's context. Engram screens for
this at the write boundary and exposes the screen to agents:

- **Write screen (always-on):** every fact entering the curated corpus
  (`hippo_remember`, transcript→fact promotion) is checked by
  `engram.prompt_injection`. A poisoned proposition — instruction-override,
  role-hijack, chat-template smuggling (`<|im_start|>`, `[INST]`), tool-call
  spoofing, exfiltration, or invisible unicode (zero-width/bidi/tag) — is set
  `status="quarantined"`: hidden from default recall, kept on disk for audit,
  **never deleted**. Disable with `ENGRAM_INJECTION_SCREEN=0`.
- **Agent-callable screen:** the `hippo_screen_content` MCP tool lets an agent
  screen UNTRUSTED content (web pages, tool output, documents) *before* trusting
  or storing it — the read-side of indirect prompt injection (OWASP LLM01).
  Returns `is_injection` + `signals` + a recommendation; the caller decides.
- **Heuristic — a first line, not a guarantee.** Anchored, length-bounded regex
  + unicode scan; pure-CPU, local, no LLM. Novel/obfuscated injections can evade
  it, so the intended posture is defense-in-depth: tag provenance, treat
  recalled/observed content as DATA not instructions, and keep a human in the
  loop for agent writes. False positives are kept near zero (a detector that
  hides real memories is worse than none — see `tests/test_prompt_injection.py`
  + the 1109-test write/recall regression that quarantined no legitimate fact).

## Automated checks

On every change CI runs, as **blocking gates**: **CodeQL** (security-extended +
security-and-quality, whole-tree static analysis) and **`pip-audit --strict`**
(HIGH/CRITICAL dependency vulnerabilities). **`bandit`, ruff security (`S`) rules,
and `safety` run report-only over the `engram` package** — their findings surface
in CI logs but do not yet fail the build (a backlog of pre-existing low/medium
findings is being triaged before they gate). Secret-redaction, path-traversal,
SSRF, and prompt-injection guards have dedicated test suites under
`tests/security/`.

**Dependency hygiene.** Direct dependency floors exclude known-vulnerable ranges
(so the manifest itself is downgrade-proof and clean under third-party SCA, not
just the resolved latest). For locked / enterprise / air-gapped installs that
must also force the *transitive* closure to patched versions, apply the pinned
minimums in [`constraints/security.txt`](constraints/security.txt):
`pip install verimem -c constraints/security.txt`. The list is refreshed from
`pip-audit` sweeps.

**HTTP response headers.** The gateway stamps defensive headers on every response
(`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a
`frame-ancestors 'none'` CSP, `Referrer-Policy`, `Cross-Origin-Opener-Policy`,
`Permissions-Policy`) — additive, so a route may set stricter values; HSTS is
left to the TLS-terminating reverse proxy.
