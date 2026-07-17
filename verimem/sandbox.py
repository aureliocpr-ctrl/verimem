"""Cycle 2026-05-27 round 13 P1 — sandbox Bash deny-by-default.

Aurelio audit gap C3: "no sandbox Bash isolato (Claude esegue qualsiasi
shell command, zero isolation per task rischiosi)".

Triangulation Gemini+GPT consensus: sandbox Bash P1 (immediately after P0
backup+rollback foundation). GPT verbatim: "appena l'agente puo agire
davvero sul sistema, il rischio passa da risposta sbagliata a danno
operativo. Serve allowlist, dry-run, cwd jail, timeout, env scrub, no
network opzionale."

Architecture:
    SandboxPolicy
        - allowlist: list[re.Pattern]   — commands matching pass
        - denylist:  list[re.Pattern]   — commands matching always reject
        - allowed_cwds: list[Path]      — execution restricted to these
        - timeout_s: int                — kill after N seconds
        - env_scrub_prefixes: list[str] — env vars with these prefixes hidden
        - allow_network: bool           — if False, blocks known net commands

    SandboxedShell(policy)
        .validate(cmd, cwd) -> ValidationResult
        .execute(cmd, cwd, *, dry_run=False) -> ExecResult
        .audit_log_path -> Path

Deny-by-default: a command that matches NO allowlist regex AND NO denylist
regex is REJECTED. Allowlist must explicitly authorize.

Audit: every validate + execute call writes JSONL line to
~/.engram/audit/sandbox-YYYYMMDD.jsonl.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import signal as _signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

DEFAULT_AUDIT_ROOT = Path.home() / ".engram" / "audit"


# Cycle 2026-05-27 round 14 FIX 2 (agy audit Critical sandbox.py:74-98).
#
# Empirical denylist: commands that MUST NEVER run via sandbox. Two layers:
# (a) hard binary patterns (rm -rf /, format, dd, sudo, etc) and
# (b) shell METACHARACTERS — pre-round 13 the allowlist regex were NOT
# end-anchored so attacks like `echo "ok" && rm -rf /tmp/X` matched the
# allowlist prefix and the shell happily executed both statements. The
# meta-character denylist short-circuits these compound attacks BEFORE
# the allowlist check.
#
# Caveat: this is partial mitigation. The full fix is shell=False +
# shlex.split (FIX 3, separate task). The metachar denylist is the
# minimum bar for "deny-by-default actually denies compound commands".
DEFAULT_DENYLIST_PATTERNS: tuple[str, ...] = (
    # (a) Destructive binaries / commands.
    # Cycle 14 FIX 2b (critic-orchestrator job 452e0d0174e8ada1
    # counterexample 0.88 conf): pre-fix `rm -rf ~/foo` slipped because
    # the path anchor required `/`. Post-fix: rm -rf is denied regardless
    # of target. Same for the Windows `del /q /s`, `rd /s`, `erase` family
    # which were not previously listed at all.
    r"\brm\s+-[rRfF][rRfF]?\b",     # rm -rf, rm -fr (any target)
    r"\brmdir\s+/[sSqQ]",            # rmdir /s, rmdir /q (Win recursive)
    r"\b(?:del|erase)\s+(?:/[sSqQfF]\s+){0,3}[^\r\n]",  # del /q /s ...
    r"\brd\s+/[sSqQ]",               # rd /s /q (Win)
    r"\bformat\b",                   # format C:
    r"\bmkfs(\.[a-z0-9]+)?\b",      # mkfs.ext4
    r"\bdd\s+if=.*of=/dev/",        # dd if=... of=/dev/sda
    r"\bshred\b",
    r"\bsudo\b",
    r"\bsu\s+-",
    r"\bsetx\s+/M\s+",              # global env mutation
    r"\bcacls\b|\bicacls\b",        # ACL changes
    r"\bnet\s+user\s+\w+\s+/add",   # add Windows user
    r"\bschtasks\s+/create",        # arbitrary scheduled task
    r"\bcurl\s+.*\|\s*(bash|sh|pwsh|powershell)",  # curl pipe shell
    r"\biwr\s+.*\|\s*iex\b",                       # PS download+exec
    r"\bInvoke-WebRequest\s+.*\|\s*Invoke-Expression",
    r":\(\)\s*\{",                   # fork bomb opener
    r"\b(reg\s+)?delete\s+(HKLM|HKCR|HKU)\b",  # HKLM delete (HKCU is fine)
    r"\bbcdedit\b",                  # boot config
    r"\bdiskpart\b",
    # (b) Shell metacharacters paired with destructive / non-allowlist
    # follow-up tokens. Pre-fix the allowlist anchors were broken so
    # `echo ok && rm -rf /` slipped through; this layer catches the
    # compound-attack class without false-positiving legitimate uses
    # of `;` inside quoted strings (e.g. `python -c "import x; y"`).
    #
    # Heuristic: a metachar followed by another COMMAND token is the
    # red flag. We list a conservative set of binaries that should
    # NEVER appear post-metachar in this sandbox.
    #
    # Cycle 14 FIX 2b (critic counterexample): added `&` SINGLE (Windows
    # cmd.exe sequential separator — pre-fix only `&&` was caught) and
    # extended the post-metachar dangerous-binary list with `del`, `rd`,
    # `erase` (Win destructive) which were absent.
    r"&&\s*\S",                              # any && chain
    r"\|\|\s*\S",                            # any || chain
    r"`[^`]*`",                              # `backtick subshell`
    r"\$\(",                                 # $(subshell)
    r">>?\s*[A-Za-z0-9/_.~$-]",              # file redirect (write/append)
    r"<\s*[A-Za-z0-9/_.~$-]",                # file redirect (read)
    r"[\r\n]",                               # literal CR/LF inside cmd
    # Windows-specific: `&` is a sequential separator on cmd.exe
    # (different semantics from POSIX which uses `&` for background).
    # We deny `&` followed by a non-`&` character — that excludes the
    # already-caught `&&` chain pattern and disallows lone `&`.
    r"&(?!&)\s*\S",
    # Semicolon / pipe / single-ampersand followed by ANY known-
    # dangerous binary. Includes Windows del/rd/erase (round 14 FIX 2b).
    r"[;|&]\s*(rm|del|rd|erase|sudo|chmod|chown|kill|killall|"
    r"format|mkfs|dd|shred|"
    r"curl|wget|nc|netcat|ncat|ssh|scp|"
    r"bash|sh|pwsh|powershell|cmd|"
    # Round 2026-06-04 (hunt [00]/[04]): a pipe/semicolon/amp must not be
    # able to smuggle a NON-allowlisted interpreter or fan-out util. The
    # legacy list above blocked shells but omitted these — close the hole.
    r"python|python3|py|node|nodejs|deno|bun|perl|ruby|php|"
    r"tee|xargs|env|eval|exec|source|awk|gawk|"
    r"Invoke-WebRequest|Invoke-Expression|iex)\b",
    # Newline-followed compound (multi-line injection). The \n must
    # appear LITERALLY (not as ^ start-of-string) so legit single-cmd
    # `curl http://x` is caught by the network gate, not by this.
    r"\n\s*(rm\s+-r|del|rd\s+/|erase|sudo|curl|wget)\b",
)

# Cycle 2026-05-27 round 14 FIX 2 (agy audit Critical): end-anchor regex.
#
# Empirical allowlist: low-risk read-only / dev-loop commands.
# All patterns now end with $ (or .*$ for variable trailing args) so the
# allowlist matches the WHOLE command, not just a prefix. Pre-fix
# `echo "ok"; rm -rf /tmp/X` matched `^\s*echo\s+` and slipped through;
# post-fix the trailing `; rm ...` is outside the anchored region.
#
# Defense in depth: the metachar denylist in DEFAULT_DENYLIST_PATTERNS
# fires BEFORE the allowlist, so even an allowlist regex that misses the
# anchor would be caught by the metachar layer.
#
# NOTE: this layered defense is still NOT a substitute for shell=False
# (FIX 3). It blocks the obvious compound-statement attacks; exotic shell
# tricks (process substitution, brace expansion, env-var-expanded paths)
# can still slip through. FIX 3 will move to subprocess.run(list, shell=False).
DEFAULT_ALLOWLIST_PATTERNS: tuple[str, ...] = (
    # Read-only file operations.
    r"^\s*(cat|head|tail|less|more|file|wc|stat)\s+\S[^\r\n]*$",
    r"^\s*(ls|dir|tree)(\s+[-/\w.]+)*\s*$",
    r"^\s*(find|where|which|type)\s+\S[^\r\n]*$",
    r"^\s*(grep|rg|ripgrep|ack|ag|select-string)\s+\S[^\r\n]*$",
    # Git read-only.
    r"^\s*git\s+(status|diff|log|show|blame|branch|tag|remote|"
    r"config\s+(?!--global)|"
    r"rev-parse|describe|reflog|stash\s+list)([^\r\n]*)$",
    # Pytest + python.
    r"^\s*python\s+-m\s+pytest([^\r\n]*)$",
    r"^\s*pytest([^\r\n]*)$",
    r"^\s*python\s+-c\s+[^\r\n]*$",
    r"^\s*python\s+\S+\.py([^\r\n]*)$",
    # echo / printf (only literal strings — denylist still blocks metachar).
    r"^\s*echo\s+[^\r\n]*$",
    r"^\s*printf\s+[^\r\n]*$",
    # date / time / pwd / id-style read-only.
    r"^\s*(date|time|pwd|whoami|hostname|uname|whence)(\s+[^\r\n]*)?$",
    # CLI tool: clp (read-only subcommands only).
    r"^\s*clp\s+(help|--help|version|--version|tip|chain\s+show|"
    r"chain\s+latest|recent|search|stats|dashboard|digest|arsenal)"
    r"([^\r\n]*)$",
    # Conda / pip read-only.
    r"^\s*(conda|pip)\s+(list|show|info|search|freeze)([^\r\n]*)$",
)

# Net-blocking patterns (when allow_network=False).
NETWORK_PATTERNS: tuple[str, ...] = (
    r"^\s*(curl|wget|http|nc|netcat|ncat)\s+",
    r"^\s*(ssh|scp|sftp|rsync)\s+",
    r"^\s*ping\s+",
    r"^\s*Invoke-WebRequest\b",
    r"^\s*Invoke-RestMethod\b",
)


# Cycle 2026-05-27 round 16 FIX 3 — shell=False refactor.
#
# Aurelio audit gap (Gemini+agy verdict Critical sandbox.py:74-98+306):
# subprocess shell=True + regex allowlist is bypassable via shell
# metacharacters. The fundamental fix is shell=False + argv list parsing
# via shlex. This module-level config supports the new mode WITHOUT
# breaking dev productivity (FIX 6 pattern: env var toggle).
#
# Binary allowlist: argv[0] -> ('*' for any args | set of allowed first-args).
# When in strict mode, the first token MUST be in this dict, otherwise
# denied. Subsequent args are NOT regex-validated (subprocess shell=False
# already prevents the metachar injection class).
DEFAULT_BINARY_ALLOWLIST: dict[str, str | frozenset[str]] = {
    # Read-only inspection
    "echo": "*",
    "printf": "*",
    "cat": "*",
    "head": "*",
    "tail": "*",
    "less": "*",
    "more": "*",
    "file": "*",
    "wc": "*",
    "stat": "*",
    "ls": "*",
    "dir": "*",
    "tree": "*",
    "find": "*",
    "where": "*",
    "which": "*",
    "type": "*",
    "grep": "*",
    "rg": "*",
    "ripgrep": "*",
    "ack": "*",
    "ag": "*",
    "select-string": "*",
    "date": "*",
    "time": "*",
    "pwd": "*",
    "whoami": "*",
    "hostname": "*",
    "uname": "*",
    # Git — only read-only subcommands.
    "git": frozenset({
        "status", "diff", "log", "show", "blame", "branch", "tag",
        "remote", "config", "rev-parse", "describe", "reflog",
    }),
    # Python / pytest.
    "python": "*",
    "python3": "*",
    "pytest": "*",
    "py": "*",
    # CLI tools (read-only subcommands only).
    "clp": frozenset({
        "help", "--help", "version", "--version", "tip", "chain",
        "recent", "search", "stats", "dashboard", "digest", "arsenal",
    }),
    "verimem": frozenset({"--help", "facts", "status"}),
    "engram": frozenset({"--help", "facts", "status"}),
    "hippo": frozenset({"--help", "status"}),
    # Conda / pip — read-only subcommands only.
    "conda": frozenset({"list", "show", "info", "search"}),
    "pip": frozenset({"list", "show", "info", "search", "freeze"}),
}


def _resolve_sandbox_mode() -> str:
    """Cycle 16 FIX 3 — sandbox shell mode toggle.

    Returns ``"strict"`` (shell=False + binary allowlist enforced) when
    ENGRAM_SANDBOX_MODE in {strict, shell-false, 1, on, enforce}.
    Otherwise ``"legacy"`` (shell=True + regex allowlist, the original
    cycle-13 behavior — keeps dev productivity, no breaking change).

    Default legacy preserves backward compatibility for the existing
    test suite + Aurelio's autonomous workflows. Flip to strict in
    production where command-injection-via-metachar must be impossible.
    """
    val = (os.environ.get("ENGRAM_SANDBOX_MODE") or "").strip().lower()
    if val in ("strict", "shell-false", "1", "on", "enforce"):
        return "strict"
    return "legacy"


def _parse_argv(cmd: str) -> list[str] | None:
    """Tokenize cmd into argv via shlex. Returns None on parse error.

    posix=False on Windows keeps the rules closer to cmd.exe quoting
    semantics (no backslash escaping in non-quoted parts).
    """
    try:
        return shlex.split(cmd, posix=(sys.platform != "win32"))
    except ValueError:
        return None


def _validate_argv(argv: list[str]) -> tuple[bool, str]:
    """In strict mode: check argv[0] is in DEFAULT_BINARY_ALLOWLIST + the
    first argument (if present) is in the per-binary allow set.

    Returns (allowed: bool, matched_rule: str).
    """
    if not argv:
        return False, "empty argv"
    # Normalize binary basename: 'git.exe' -> 'git', 'C:/Python/python.exe' -> 'python'
    binary_raw = argv[0]
    binary = binary_raw.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    if binary.endswith(".exe"):
        binary = binary[:-4]
    if binary not in DEFAULT_BINARY_ALLOWLIST:
        return False, f"binary '{binary}' not in allowlist"
    # SECURITY (rescan2 2026-06-02): in STRICT mode a bare "*" allowlist for
    # python/find would wave through arbitrary code execution. Restrict those
    # dangerous binaries BEFORE the generic "*" allow. (Legacy mode keeps
    # python -c for dev-productivity — that policy change is left to Aurelio.)
    if binary in ("python", "python3", "py"):
        # Only `python -m pytest ...` is allowed; `-c` and direct-script
        # execution (`python foo.py`) are arbitrary code execution.
        if len(argv) >= 3 and argv[1] == "-m" and argv[2].lower() == "pytest":
            # H3 (2026-07-04 security sweep): `python -m pytest` alone isn't
            # safe — pytest args can load arbitrary code: `-p mod`/`--pyargs`
            # import a module, `--import-mode importlib` + a planted conftest,
            # `-c cfg`/`-o addopts=...` point at an attacker config that runs
            # code at collection. Block those flags in strict mode.
            _pytest_danger = {
                "-p", "--pyargs", "-c", "--import-mode", "--rootdir",
                "--confcutdir", "-o", "--override-ini",
            }
            for tok in argv[3:]:
                base = tok.lower().split("=", 1)[0]
                if base in _pytest_danger:
                    return False, (
                        f"pytest flag '{tok}' blocked in strict mode "
                        f"(plugin/config load = arbitrary-exec vector)"
                    )
            return True, f"strict_allow:{binary}:-m pytest"
        return False, (
            f"binary '{binary}' arbitrary-exec blocked in strict mode "
            f"(only `-m pytest` allowed; got {argv[1:3]})"
        )
    if binary == "find":
        _find_danger = {
            "-exec", "-execdir", "-delete", "-ok", "-okdir",
            "-fprintf", "-fprint", "-fprint0", "-fls",
        }
        hit = next((t for t in argv[1:] if t.lower() in _find_danger), None)
        if hit is not None:
            return False, f"find action '{hit}' blocked (arbitrary exec)"
    if binary == "git":
        # SECURITY (loop 2026-06-05): `git config` is in the git allow-set, so a
        # WRITE like `git config core.pager "sh -c evil"` is accepted — then an
        # already-allowed `git log`/`git diff` runs evil through the pager. Same
        # persistence-exec vector via core.editor / core.hooksPath / core.fsmonitor
        # / alias.* / *.sshCommand. The entire chain lives INSIDE the strict
        # allowlist, breaking strict mode's "injection impossible" contract. Only
        # READ forms of config are safe; other git subcommands fall through to the
        # normal allow-set check below. (Legacy mode = Aurelio's dev policy, as
        # with python -c / find -exec — intentionally not changed here.)
        if len(argv) >= 2 and argv[1].lower() == "config":
            _config_read_flags = {
                "--get", "--get-all", "--get-regexp", "--get-urlmatch",
                "--get-color", "--get-colorbool", "-l", "--list",
            }
            if not any(a.lower() in _config_read_flags for a in argv[2:]):
                return False, (
                    "git config write blocked in strict mode "
                    "(core.editor/pager/hooksPath/alias = arbitrary-exec "
                    "vector); only --get/--list reads allowed"
                )
    allowed_args = DEFAULT_BINARY_ALLOWLIST[binary]
    if allowed_args == "*":
        return True, f"strict_allow:{binary}:*"
    # Per-binary subcommand check (argv[1] must be in the set).
    if len(argv) < 2:
        # Bare binary call (e.g. `git`) — allowed (will show help/usage).
        return True, f"strict_allow:{binary}:bare"
    first_arg = argv[1].lower()
    if first_arg in allowed_args:
        return True, f"strict_allow:{binary}:{first_arg}"
    return False, (
        f"binary '{binary}' first-arg '{first_arg}' not in "
        f"allowed set: {sorted(allowed_args)}"
    )


Action = Literal["allow", "deny", "dry_run", "timeout", "error"]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of policy check."""
    allowed: bool
    matched_rule: str
    reason: str


@dataclass(frozen=True)
class ExecResult:
    """Outcome of execute()."""
    action: Action
    returncode: int | None
    stdout: str
    stderr: str
    elapsed_s: float
    cmd: str
    cwd: str
    matched_rule: str
    reason: str


@dataclass
class SandboxPolicy:
    """Configurable policy. Defaults are conservative (read-only-ish)."""
    allowlist: list[re.Pattern] = field(
        default_factory=lambda: [
            re.compile(p, re.IGNORECASE) for p in DEFAULT_ALLOWLIST_PATTERNS
        ]
    )
    denylist: list[re.Pattern] = field(
        default_factory=lambda: [
            re.compile(p, re.IGNORECASE) for p in DEFAULT_DENYLIST_PATTERNS
        ]
    )
    allowed_cwds: list[Path] = field(default_factory=list)
    timeout_s: int = 60
    env_scrub_prefixes: tuple[str, ...] = (
        "AWS_", "AZURE_", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
        "GOOGLE_API_KEY", "HF_TOKEN", "GITHUB_TOKEN", "GH_TOKEN",
        "SLACK_TOKEN", "NPM_TOKEN", "STRIPE_", "TWILIO_",
    )
    allow_network: bool = False

    def add_allow_pattern(self, pattern: str) -> None:
        self.allowlist.append(re.compile(pattern, re.IGNORECASE))

    def add_deny_pattern(self, pattern: str) -> None:
        self.denylist.append(re.compile(pattern, re.IGNORECASE))

    def add_allowed_cwd(self, cwd: Path | str) -> None:
        self.allowed_cwds.append(Path(cwd).resolve())


def _cwd_within(allowed: list[Path], cwd: Path) -> bool:
    """Return True if cwd is inside one of the allowed roots."""
    cwd_r = cwd.resolve()
    for root in allowed:
        try:
            cwd_r.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _scrub_env(env: dict[str, str], prefixes: tuple[str, ...]) -> dict[str, str]:
    """Return env copy with any var whose name STARTS WITH a prefix removed."""
    if not prefixes:
        return dict(env)
    out = {}
    for k, v in env.items():
        if any(k.upper().startswith(p.upper()) for p in prefixes):
            continue
        out[k] = v
    return out


class SandboxedShell:
    """Execute shell commands behind a deny-by-default policy."""

    def __init__(
        self,
        policy: SandboxPolicy | None = None,
        *,
        audit_root: Path | str = DEFAULT_AUDIT_ROOT,
    ) -> None:
        self.policy = policy or SandboxPolicy()
        self.audit_root = Path(audit_root)
        self.audit_root.mkdir(parents=True, exist_ok=True)

    @property
    def audit_log_path(self) -> Path:
        """Today's audit log file. Lazily created on first write."""
        return self.audit_root / f"sandbox-{datetime.now():%Y%m%d}.jsonl"

    def _audit(self, event: dict) -> None:
        """Append one JSONL event to today's audit log."""
        event = {"ts": time.time(), **event}
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _validate_security_layers(
        self, cmd: str, cwd: Path | str,
    ) -> ValidationResult:
        """FIX 8 (critic ROUND 2 counterexample 0.80): expose ONLY the
        security layers (denylist + cwd_jail + network) without the
        regex-allowlist + default_deny that follow.

        The strict shell=False branch in execute() uses its own
        DEFAULT_BINARY_ALLOWLIST (basename-based) and must NOT be
        rejected by the legacy regex allowlist that was tuned for
        shell-string matching. This helper returns:
          - ValidationResult(False, ...) when a security layer blocks.
          - ValidationResult(True, "security_ok", ...) when ALL three
            security layers pass. The caller decides what to do next.
        """
        cmd_str = (cmd or "").strip()
        if not cmd_str:
            return ValidationResult(False, "empty", "empty command")
        # 1. Denylist.
        for pat in self.policy.denylist:
            if pat.search(cmd_str):
                return ValidationResult(
                    False, f"deny:{pat.pattern}",
                    "command matches denylist pattern",
                )
        # 2. Cwd jail.
        if self.policy.allowed_cwds:
            cwd_p = Path(cwd) if cwd else Path.cwd()
            if not _cwd_within(self.policy.allowed_cwds, cwd_p):
                return ValidationResult(
                    False, "cwd_jail",
                    f"cwd {cwd_p} not within allowed roots",
                )
        # 3. Network.
        if not self.policy.allow_network:
            for pat in (re.compile(p, re.IGNORECASE) for p in NETWORK_PATTERNS):
                if pat.search(cmd_str):
                    return ValidationResult(
                        False, "network_blocked",
                        "command performs network I/O; "
                        "allow_network=False",
                    )
        return ValidationResult(
            True, "security_ok",
            "all 3 security layers passed (denylist/cwd_jail/network)",
        )

    def validate(self, cmd: str, cwd: Path | str) -> ValidationResult:
        """Pure check: would this command + cwd be allowed?

        Order:
          1. Denylist match → deny (highest priority).
          2. Cwd jail check (if allowed_cwds set) → deny on miss.
          3. Network check (if allow_network=False) → deny on net match.
          4. Allowlist match → allow.
          5. Default → deny (deny-by-default).

        Layers 1-3 delegated to _validate_security_layers (FIX 8).
        """
        sec = self._validate_security_layers(cmd, cwd)
        if not sec.allowed:
            return sec
        cmd_str = (cmd or "").strip()
        # 4. Allowlist.
        for pat in self.policy.allowlist:
            if pat.search(cmd_str):
                return ValidationResult(
                    True, f"allow:{pat.pattern}",
                    "command matches allowlist",
                )
        # 5. Default deny.
        return ValidationResult(
            False, "default_deny",
            "command not in allowlist (deny-by-default)",
        )

    def execute(
        self,
        cmd: str,
        cwd: Path | str | None = None,
        *,
        dry_run: bool = False,
    ) -> ExecResult:
        """Validate + execute. Returns ExecResult; never raises on shell error.

        On dry_run=True: validate only, never invokes subprocess; returns
        action="dry_run" with returncode=None.

        Cycle 16 FIX 3 (Gemini+agy audit Critical): when
        ENGRAM_SANDBOX_MODE=strict, execution uses subprocess.Popen with
        shell=False + argv list parsed via shlex. This eliminates the
        metachar injection class entirely (no shell interprets the
        argument list, so `&`, `&&`, `;`, `|`, `$()`, backticks become
        literal characters passed to the binary). Validation runs against
        DEFAULT_BINARY_ALLOWLIST instead of the regex allowlist.

        Legacy mode (default, no env var) keeps shell=True + regex
        allowlist + metachar denylist (cycle 13/14). Backward compatible.
        """
        cwd_resolved = Path(cwd).resolve() if cwd else Path.cwd().resolve()
        mode = _resolve_sandbox_mode()
        if mode == "strict":
            # FIX 3 strict path: argv-based validation + shell=False exec.
            argv = _parse_argv(cmd)
            if argv is None:
                self._audit({
                    "event": "deny", "cmd": cmd, "cwd": str(cwd_resolved),
                    "matched_rule": "shlex_parse_error",
                    "reason": "cmd has unbalanced quotes / parse failed",
                })
                return ExecResult(
                    action="deny", returncode=None, stdout="", stderr="",
                    elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule="shlex_parse_error",
                    reason="cmd has unbalanced quotes / parse failed",
                )
            ok_argv, matched = _validate_argv(argv)
            if not ok_argv:
                self._audit({
                    "event": "deny", "cmd": cmd, "cwd": str(cwd_resolved),
                    "matched_rule": "strict_binary_deny",
                    "reason": matched,
                })
                return ExecResult(
                    action="deny", returncode=None, stdout="", stderr="",
                    elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule="strict_binary_deny", reason=matched,
                )
            # FIX 7 (critic counterexample 0.82): strict branch MUST also
            # apply denylist + cwd_jail + network_gate from self.validate().
            # Allowlist alone is insufficient: e.g. `find . -exec rm -rf {} \;`
            # has find='*' in allowlist but the denylist `\brm\s+-[rRfF]`
            # in validate() catches the destructive substring. Without this
            # call strict mode would be LESS safe than legacy.
            #
            # FIX 8 (critic ROUND 2 counterexample 0.80): use
            # _validate_security_layers() instead of full validate() so
            # the regex-allowlist (which lacks engram/hippo/python3/py)
            # does NOT force default_deny on legitimate binaries that the
            # basename allowlist (_validate_argv) already approved.
            v_strict = self._validate_security_layers(cmd, cwd_resolved)
            if not v_strict.allowed:
                self._audit({
                    "event": "deny", "cmd": cmd, "cwd": str(cwd_resolved),
                    "matched_rule": v_strict.matched_rule or "validate_deny",
                    "reason": v_strict.reason or "validate denied",
                    "phase": "strict_post_allowlist",
                })
                return ExecResult(
                    action="deny", returncode=None, stdout="", stderr="",
                    elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=v_strict.matched_rule or "validate_deny",
                    reason=v_strict.reason or "validate denied",
                )
            if dry_run:
                self._audit({
                    "event": "dry_run", "cmd": cmd, "cwd": str(cwd_resolved),
                    "matched_rule": matched, "argv": argv,
                })
                return ExecResult(
                    action="dry_run", returncode=None, stdout="", stderr="",
                    elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=matched, reason="dry_run strict",
                )
            scrubbed_env = _scrub_env(
                dict(os.environ), self.policy.env_scrub_prefixes,
            )
            popen_kw_strict: dict = {
                "shell": False, "cwd": str(cwd_resolved),
                "env": scrubbed_env, "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE, "text": True,
            }
            if sys.platform == "win32":
                popen_kw_strict["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            else:
                popen_kw_strict["start_new_session"] = True
            t0_strict = time.perf_counter()
            try:
                proc_strict = subprocess.Popen(argv, **popen_kw_strict)
            except FileNotFoundError as exc:
                self._audit({
                    "event": "error", "cmd": cmd, "cwd": str(cwd_resolved),
                    "error": f"binary not found: {argv[0]}",
                })
                return ExecResult(
                    action="error", returncode=None, stdout="",
                    stderr=f"binary not found: {argv[0]}",
                    elapsed_s=time.perf_counter() - t0_strict,
                    cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=matched, reason=str(exc),
                )
            except Exception as exc:  # noqa: BLE001
                self._audit({
                    "event": "error", "cmd": cmd, "cwd": str(cwd_resolved),
                    "error": str(exc),
                })
                return ExecResult(
                    action="error", returncode=None, stdout="", stderr=str(exc),
                    elapsed_s=time.perf_counter() - t0_strict,
                    cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=matched, reason=str(exc),
                )
            try:
                stdout_s, stderr_s = proc_strict.communicate(
                    timeout=self.policy.timeout_s,
                )
                res_strict = ExecResult(
                    action="allow", returncode=proc_strict.returncode,
                    stdout=stdout_s or "", stderr=stderr_s or "",
                    elapsed_s=time.perf_counter() - t0_strict,
                    cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=matched, reason="strict shell=False",
                )
                self._audit({
                    "event": "allow_exec_strict", "cmd": cmd,
                    "cwd": str(cwd_resolved), "matched_rule": matched,
                    "returncode": proc_strict.returncode,
                    "elapsed_s": res_strict.elapsed_s, "argv": argv,
                })
                return res_strict
            except subprocess.TimeoutExpired:
                # Reuse the process-group kill cascade (FIX A pattern).
                try:
                    if sys.platform == "win32":
                        try:
                            proc_strict.send_signal(_signal.CTRL_BREAK_EVENT)
                            proc_strict.wait(timeout=2.0)
                        except Exception:
                            proc_strict.kill()
                    else:
                        try:
                            os.killpg(os.getpgid(proc_strict.pid),
                                      _signal.SIGTERM)
                            proc_strict.wait(timeout=2.0)
                        except Exception:
                            try:
                                os.killpg(os.getpgid(proc_strict.pid),
                                          _signal.SIGKILL)
                            except Exception:
                                proc_strict.kill()
                except Exception:
                    try:
                        proc_strict.kill()
                    except Exception:
                        pass
                try:
                    stdout_s, stderr_s = proc_strict.communicate(timeout=2.0)
                except Exception:
                    stdout_s, stderr_s = "", ""
                self._audit({
                    "event": "timeout_strict", "cmd": cmd,
                    "cwd": str(cwd_resolved),
                    "timeout_s": self.policy.timeout_s,
                })
                return ExecResult(
                    action="timeout", returncode=None,
                    stdout=stdout_s or "", stderr=stderr_s or "",
                    elapsed_s=time.perf_counter() - t0_strict,
                    cmd=cmd, cwd=str(cwd_resolved),
                    matched_rule=matched,
                    reason=f"timeout after {self.policy.timeout_s}s "
                           f"(strict, process-group killed)",
                )
        # === Legacy mode (shell=True + regex allowlist) — current code ===
        v = self.validate(cmd, cwd_resolved)
        if not v.allowed:
            res = ExecResult(
                action="deny", returncode=None, stdout="", stderr="",
                elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule, reason=v.reason,
            )
            self._audit({
                "event": "deny", "cmd": cmd, "cwd": str(cwd_resolved),
                "matched_rule": v.matched_rule, "reason": v.reason,
            })
            return res
        if dry_run:
            self._audit({
                "event": "dry_run", "cmd": cmd, "cwd": str(cwd_resolved),
                "matched_rule": v.matched_rule,
            })
            return ExecResult(
                action="dry_run", returncode=None, stdout="", stderr="",
                elapsed_s=0.0, cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule, reason=v.reason,
            )
        # Cycle 14 FIX A (agy audit High sandbox.py:306-310): timeout
        # via subprocess.Popen + process-group kill. Pre-fix used
        # subprocess.run(timeout=N) which only kills the SHELL parent;
        # background children spawned with `&` or detached PowerShell
        # jobs survive as zombies. Post-fix opens the child in its own
        # process group / new session and signals the whole group on
        # TimeoutExpired so no descendant escapes.
        scrubbed_env = _scrub_env(
            dict(os.environ), self.policy.env_scrub_prefixes,
        )
        t0 = time.perf_counter()
        # Platform-specific knobs for "create a new process group".
        popen_kw: dict = {
            "shell": True, "cwd": str(cwd_resolved),
            "env": scrubbed_env, "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE, "text": True,
        }
        if sys.platform == "win32":
            popen_kw["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
        else:
            popen_kw["start_new_session"] = True

        try:
            proc = subprocess.Popen(cmd, **popen_kw)
        except Exception as exc:  # noqa: BLE001
            self._audit({
                "event": "error", "cmd": cmd, "cwd": str(cwd_resolved),
                "error": str(exc),
            })
            return ExecResult(
                action="error", returncode=None, stdout="", stderr=str(exc),
                elapsed_s=time.perf_counter() - t0,
                cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule, reason=str(exc),
            )

        try:
            stdout, stderr = proc.communicate(
                timeout=self.policy.timeout_s,
            )
            res = ExecResult(
                action="allow", returncode=proc.returncode,
                stdout=stdout or "", stderr=stderr or "",
                elapsed_s=time.perf_counter() - t0,
                cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule, reason=v.reason,
            )
            self._audit({
                "event": "allow_exec", "cmd": cmd, "cwd": str(cwd_resolved),
                "matched_rule": v.matched_rule, "returncode": proc.returncode,
                "elapsed_s": res.elapsed_s,
            })
            return res
        except subprocess.TimeoutExpired:
            # Kill the whole process group / job tree, NOT just the shell.
            try:
                if sys.platform == "win32":
                    # CTRL_BREAK_EVENT is the only signal Windows accepts
                    # on a CREATE_NEW_PROCESS_GROUP child; fall back to
                    # terminate() / kill() if it fails.
                    try:
                        proc.send_signal(_signal.CTRL_BREAK_EVENT)
                        proc.wait(timeout=2.0)
                    except Exception:
                        proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), _signal.SIGTERM)
                        proc.wait(timeout=2.0)
                    except Exception:
                        try:
                            os.killpg(os.getpgid(proc.pid), _signal.SIGKILL)
                        except Exception:
                            proc.kill()
            except Exception:
                # Last resort: best-effort process kill (children may leak).
                try:
                    proc.kill()
                except Exception:
                    pass
            # Drain any pending I/O so the file descriptors close cleanly.
            try:
                stdout, stderr = proc.communicate(timeout=2.0)
            except Exception:
                stdout, stderr = "", ""
            self._audit({
                "event": "timeout", "cmd": cmd, "cwd": str(cwd_resolved),
                "timeout_s": self.policy.timeout_s,
                "killpg_attempted": True,
            })
            return ExecResult(
                action="timeout", returncode=None,
                stdout=stdout or "", stderr=stderr or "",
                elapsed_s=time.perf_counter() - t0,
                cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule,
                reason=f"timeout after {self.policy.timeout_s}s "
                       f"(process-group killed)",
            )
        except Exception as exc:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:
                pass
            self._audit({
                "event": "error", "cmd": cmd, "cwd": str(cwd_resolved),
                "error": str(exc),
            })
            return ExecResult(
                action="error", returncode=None, stdout="", stderr=str(exc),
                elapsed_s=time.perf_counter() - t0,
                cmd=cmd, cwd=str(cwd_resolved),
                matched_rule=v.matched_rule, reason=str(exc),
            )


__all__ = [
    "Action",
    "DEFAULT_ALLOWLIST_PATTERNS",
    "DEFAULT_AUDIT_ROOT",
    "DEFAULT_DENYLIST_PATTERNS",
    "ExecResult",
    "NETWORK_PATTERNS",
    "SandboxPolicy",
    "SandboxedShell",
    "ValidationResult",
]
