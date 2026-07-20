"""Task #48 — MCP wrapper exposing verimem.sandbox.SandboxedShell.

The sandbox CORE (engram/sandbox.py, cycle 13, 44 tests) already enforces
deny-by-default + allowlist + cwd jail + timeout + audit. This module
verifies the MISSING piece: a `sandbox_exec` MCP tool that lets an MCP
client (Claude Code, etc.) run a command THROUGH the sandbox instead of
the unsandboxed shell.

Contract:
  - tool is registered in the capability matrix as EXECUTE (not the
    fail-CLOSED unknown default), executes_command=True, requires_sandbox
    is irrelevant (it IS the sandbox), requires_confirm=False (security is
    in the deny-by-default allowlist, mirrors hippo_run_task).
  - tool appears in list_tools() with a cmd/cwd/dry_run schema.
  - allowlisted read-only command (echo) → action=allow, runs, rc=0.
  - denylisted destructive command (rm -rf) → action=deny, NOT executed.
  - dry_run=True → action=dry_run, returncode=None (no subprocess).
  - command outside allowlist → action=deny, matched_rule=default_deny.
  - in enforce gate mode the tool passes WITHOUT _user_confirmed (it is
    not requires_confirm) but is NOT in the read-only bypass list.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server


@pytest.fixture(autouse=True)
def _enable_shell_perm(monkeypatch: pytest.MonkeyPatch):
    """sandbox_exec is behind HIPPO_ENABLE_SHELL since the 2026-07-04 H2 fix;
    these tests exercise the dispatch/behavior *given the permission is on*
    (the off-by-default refusal is covered in
    tests/test_sandbox_exec_shell_gate_h2.py)."""
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    """Drive the REAL @server.call_tool() dispatcher (same harness as
    test_mcp_capability_gate)."""
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


class TestCapabilityClassification:
    def test_sandbox_exec_registered_not_unknown(self):
        from verimem.tool_registry import REGISTRY
        assert "sandbox_exec" in REGISTRY._caps, (
            "sandbox_exec must be explicitly registered (else fail-CLOSED "
            "as DESTRUCTIVE/critical unknown)"
        )

    def test_sandbox_exec_is_execute_capability(self):
        from verimem.tool_registry import REGISTRY
        cap = REGISTRY.get("sandbox_exec")
        assert cap.capability == "EXECUTE"
        assert cap.executes_command is True
        # Mirrors hippo_run_task: sandbox itself is the gate, no per-call
        # confirm prompt (deny-by-default allowlist does the gating).
        assert cap.requires_confirm is False


class TestListToolsRegistration:
    @pytest.mark.asyncio
    async def test_sandbox_exec_listed(self):
        from mcp.types import ListToolsRequest
        handler = mcp_server.server.request_handlers[ListToolsRequest]
        req = ListToolsRequest(method="tools/list")
        result = await handler(req)
        payload = result.root if hasattr(result, "root") else result
        names = {tool.name for tool in payload.tools}
        assert "sandbox_exec" in names, (
            "sandbox_exec must be advertised by list_tools()"
        )


class TestSandboxExecDispatch:
    @pytest.mark.asyncio
    async def test_allow_echo_runs(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)  # dev OFF
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)     # legacy
        out = await _invoke("sandbox_exec", {"cmd": "echo sandbox_proof_42"})
        assert out.get("ok") is True, out
        assert out["action"] == "allow", out
        assert out["returncode"] == 0, out
        assert "sandbox_proof_42" in out["stdout"], out

    @pytest.mark.asyncio
    async def test_deny_rm_rf_not_executed(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        out = await _invoke("sandbox_exec", {"cmd": "rm -rf /tmp/should_not_run"})
        assert out["action"] == "deny", out
        assert out["matched_rule"].startswith("deny:"), out
        assert out["returncode"] is None, out

    @pytest.mark.asyncio
    async def test_dry_run_skips_subprocess(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        out = await _invoke(
            "sandbox_exec", {"cmd": "echo hi", "dry_run": True},
        )
        assert out["action"] == "dry_run", out
        assert out["returncode"] is None, out

    @pytest.mark.asyncio
    async def test_default_deny_for_unknown_command(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        out = await _invoke(
            "sandbox_exec", {"cmd": "totallyunknownbinary --foo"},
        )
        assert out["action"] == "deny", out
        assert out["matched_rule"] == "default_deny", out


class TestEnforceGateInteraction:
    def test_passes_gate_without_user_confirmed(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """In enforce mode sandbox_exec must pass the capability gate
        WITHOUT _user_confirmed — proves it is registered AND not
        requires_confirm. If misclassified, this test fails."""
        monkeypatch.setenv("ENGRAM_CAPABILITY_GATE", "enforce")
        from verimem.mcp_server import _capability_gate
        ok, msg = _capability_gate("sandbox_exec", {})
        assert ok is True, f"sandbox_exec must pass enforce gate; msg={msg}"


class TestOutputTruncation:
    """Spec (twin MEMORY CONSULTANT): output must be truncated so a huge
    stdout never floods the MCP context window."""

    @pytest.mark.asyncio
    async def test_stdout_truncated_to_max_output(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        out = await _invoke("sandbox_exec", {
            "cmd": "python -c \"print('A'*20000)\"",
            "max_output": 5000,
        })
        assert out["action"] == "allow", out
        assert len(out["stdout"]) <= 5200, (  # 5000 + truncation marker slack
            f"stdout must be truncated to ~5000; got {len(out['stdout'])}"
        )
        assert out["stdout_truncated"] is True, out
        assert out["stdout_full_len"] >= 20000, out

    @pytest.mark.asyncio
    async def test_short_output_not_truncated(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        out = await _invoke("sandbox_exec", {"cmd": "echo short_out"})
        assert out["action"] == "allow", out
        assert out["stdout_truncated"] is False, out
        assert "short_out" in out["stdout"], out

    @pytest.mark.asyncio
    async def test_default_max_output_applied(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        """No max_output passed → a sane default cap (<=10000) still applies."""
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        out = await _invoke("sandbox_exec", {
            "cmd": "python -c \"print('B'*50000)\"",
        })
        assert out["action"] == "allow", out
        assert out["stdout_truncated"] is True, out
        assert len(out["stdout"]) <= 10200, (
            f"default cap must bound stdout; got {len(out['stdout'])}"
        )


class TestCwdEnvVar:
    """Spec OPZIONE C (twin direttiva 00:49): cwd configurable via env var
    ENGRAM_SANDBOX_CWD. Default = process cwd. Override = absolute path.
    fail-CLOSED if the configured path does not exist / is not a dir.
    Mirrors the ENGRAM_CAPABILITY_GATE / ENGRAM_SANDBOX_MODE env toggles."""

    @pytest.mark.asyncio
    async def test_cwd_from_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        monkeypatch.setenv("ENGRAM_SANDBOX_CWD", str(tmp_path))
        out = await _invoke("sandbox_exec", {
            "cmd": "python -c \"import os;print(os.getcwd())\"",
        })
        assert out["action"] == "allow", out
        printed = Path(out["stdout"].strip()).resolve()
        assert printed == tmp_path.resolve(), (
            f"cwd should come from ENGRAM_SANDBOX_CWD; got {printed}"
        )

    @pytest.mark.asyncio
    async def test_invalid_env_cwd_fail_closed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        bad = tmp_path / "does_not_exist_xyz"
        monkeypatch.setenv("ENGRAM_SANDBOX_CWD", str(bad))
        out = await _invoke("sandbox_exec", {"cmd": "echo hi"})
        assert out["action"] in ("deny", "error"), out
        blob = (out.get("reason", "") or "") + (out.get("matched_rule", "") or "")
        assert "ENGRAM_SANDBOX_CWD" in blob, (
            f"fail-closed reason must name the env var; got {out}"
        )

    @pytest.mark.asyncio
    async def test_explicit_cwd_arg_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        env_dir = tmp_path / "env_dir"
        arg_dir = tmp_path / "arg_dir"
        env_dir.mkdir()
        arg_dir.mkdir()
        monkeypatch.setenv("ENGRAM_SANDBOX_CWD", str(env_dir))
        # The PRECEDENCE contract (explicit arg > env > process cwd) is
        # unchanged. What changed (red-team audit C2) is that the chosen cwd
        # must also be inside the jail: this test used to assert precedence AND
        # reachability-anywhere in one breath, and reachability-anywhere is the
        # precondition of the pytest/conftest.py RCE. Both dirs are allowed
        # here, so precedence is still what is under test.
        import os as _os
        monkeypatch.setenv("ENGRAM_SANDBOX_ALLOWED_CWDS",
                           str(env_dir) + _os.pathsep + str(arg_dir))
        out = await _invoke("sandbox_exec", {
            "cmd": "python -c \"import os;print(os.getcwd())\"",
            "cwd": str(arg_dir),
        })
        assert out["action"] == "allow", out
        printed = Path(out["stdout"].strip()).resolve()
        assert printed == arg_dir.resolve(), (
            f"explicit cwd arg must override env var; got {printed}"
        )

    async def test_explicit_cwd_arg_outside_the_jail_is_denied(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        """The security half, now stated on its own: an explicit cwd wins the
        PRECEDENCE contest but still cannot leave the jail. Without this, a
        caller picks the directory and `python -m pytest` (allowlisted in
        strict) executes that directory's conftest.py."""
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        jail = tmp_path / "jail"
        outside = tmp_path / "outside"
        jail.mkdir()
        outside.mkdir()
        monkeypatch.setenv("ENGRAM_SANDBOX_ALLOWED_CWDS", str(jail))
        out = await _invoke("sandbox_exec", {
            "cmd": "python -c \"import os;print(os.getcwd())\"",
            "cwd": str(outside),
        })
        assert out["action"] == "deny", f"cwd escaped the jail: {out}"


class TestReplayableAudit:
    """Spec (twin direttiva 01:18, insight Codex tribunal): every tool call
    appends a replayable JSONL record to ~/.engram/sandbox-audit/<date>.jsonl
    with ts, cmd, cmd_normalized, cwd, action, matched_rule (allow-rule),
    returncode (exit), elapsed_s (durata), and output HASHES (replayability).
    Override dir via ENGRAM_SANDBOX_AUDIT_DIR (mirrors the env-var pattern)."""

    REQUIRED_FIELDS = (
        "ts", "tool", "cmd", "cmd_normalized", "cwd", "action",
        "matched_rule", "returncode", "elapsed_s",
        "stdout_sha256", "stderr_sha256", "stdout_full_len",
    )

    @pytest.mark.asyncio
    async def test_audit_record_written_with_all_fields(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        audit_dir = tmp_path / "sandbox-audit"
        monkeypatch.setenv("ENGRAM_SANDBOX_AUDIT_DIR", str(audit_dir))
        out = await _invoke("sandbox_exec", {"cmd": "echo replay_marker"})
        assert out["action"] == "allow", out
        files = list(audit_dir.glob("*.jsonl"))
        assert len(files) == 1, f"one daily audit file expected; got {files}"
        rec = json.loads(
            files[0].read_text(encoding="utf-8").strip().splitlines()[-1]
        )
        for key in self.REQUIRED_FIELDS:
            assert key in rec, f"audit record missing {key!r}: {rec}"
        assert rec["action"] == "allow"
        assert rec["returncode"] == 0
        assert rec["tool"] == "sandbox_exec"
        assert len(rec["stdout_sha256"]) == 64  # sha256 hex digest

    @pytest.mark.asyncio
    async def test_same_command_same_output_hash_replayable(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
        audit_dir = tmp_path / "sandbox-audit"
        monkeypatch.setenv("ENGRAM_SANDBOX_AUDIT_DIR", str(audit_dir))
        await _invoke("sandbox_exec", {"cmd": "echo deterministic_payload"})
        await _invoke("sandbox_exec", {"cmd": "echo deterministic_payload"})
        recs = [
            json.loads(line)
            for f in audit_dir.glob("*.jsonl")
            for line in f.read_text(encoding="utf-8").strip().splitlines()
        ]
        assert len(recs) >= 2
        assert recs[-1]["stdout_sha256"] == recs[-2]["stdout_sha256"], (
            "identical cmd must produce identical output hash (replayable)"
        )

    @pytest.mark.asyncio
    async def test_denied_command_also_audited(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        audit_dir = tmp_path / "sandbox-audit"
        monkeypatch.setenv("ENGRAM_SANDBOX_AUDIT_DIR", str(audit_dir))
        out = await _invoke("sandbox_exec", {"cmd": "rm -rf /tmp/x"})
        assert out["action"] == "deny", out
        recs = [
            json.loads(line)
            for f in audit_dir.glob("*.jsonl")
            for line in f.read_text(encoding="utf-8").strip().splitlines()
        ]
        assert any(r["action"] == "deny" for r in recs), (
            "denied commands must also be audited (accountability)"
        )

    @pytest.mark.asyncio
    async def test_cwd_fail_closed_is_audited(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ):
        """Critic O3 #3 counterexample (conf 0.8): the cwd fail-CLOSED deny
        early-returns before the audit block, so it was NOT audited despite
        action=deny. This pins the regression: that deny MUST be audited."""
        monkeypatch.delenv("ENGRAM_CAPABILITY_GATE", raising=False)
        audit_dir = tmp_path / "sandbox-audit"
        bad_cwd = tmp_path / "nonexistent_dir_xyz"
        monkeypatch.setenv("ENGRAM_SANDBOX_AUDIT_DIR", str(audit_dir))
        monkeypatch.setenv("ENGRAM_SANDBOX_CWD", str(bad_cwd))
        out = await _invoke("sandbox_exec", {"cmd": "echo hi"})
        assert out["action"] == "deny", out
        assert out["matched_rule"] == "cwd_env_fail_closed", out
        recs = [
            json.loads(line)
            for f in audit_dir.glob("*.jsonl")
            for line in f.read_text(encoding="utf-8").strip().splitlines()
        ]
        assert any(
            r.get("matched_rule") == "cwd_env_fail_closed" for r in recs
        ), "cwd fail-closed deny MUST also be audited (critic counterexample)"
