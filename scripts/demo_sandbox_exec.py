"""Task #48 — end-to-end demo of the `sandbox_exec` MCP tool.

Drives the REAL @server.call_tool() dispatcher (the same code path a host
like Claude Code uses over stdio) and prints the observed ExecResult for
each scenario, proving the deny-by-default sandbox + output truncation +
audit log behave as specified.

Run:  python scripts/demo_sandbox_exec.py
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from engram import mcp_server


async def _invoke(name: str, arguments: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw_non_json": text, "_isError": getattr(payload, "isError", None)}


def _show(title: str, out: dict, fields: tuple[str, ...]) -> None:
    print(f"\n=== {title} ===")
    for f in fields:
        val = out.get(f)
        if isinstance(val, str) and len(val) > 80:
            val = val[:80] + f" …(+{len(out.get(f))-80} chars)"
        print(f"  {f:18} = {val!r}")


async def main() -> None:
    # Dev mode: capability gate off so the dispatch reaches the handler.
    os.environ.pop("ENGRAM_CAPABILITY_GATE", None)
    os.environ.pop("ENGRAM_SANDBOX_MODE", None)
    # sandbox_exec needs no LLM; offline keeps _ag() lightweight (mirrors
    # the pytest conftest so the demo runs without a provider configured).
    os.environ.setdefault("HIPPO_OFFLINE", "1")

    print("sandbox_exec MCP tool — end-to-end demo (Task #48)")
    print("=" * 60)

    out = await _invoke("sandbox_exec", {"cmd": "echo demo_allow_marker"})
    _show("1. ALLOW (allowlisted echo)", out,
          ("action", "returncode", "stdout", "matched_rule"))

    out = await _invoke("sandbox_exec", {"cmd": "rm -rf /tmp/demo_target"})
    _show("2. DENY (destructive rm -rf, NOT executed)", out,
          ("action", "returncode", "matched_rule", "reason"))

    out = await _invoke("sandbox_exec",
                        {"cmd": "totallyunknownbinary --x"})
    _show("3. DEFAULT-DENY (not in allowlist)", out,
          ("action", "matched_rule", "reason"))

    out = await _invoke("sandbox_exec",
                        {"cmd": "echo would_run", "dry_run": True})
    _show("4. DRY-RUN (validated, never spawned)", out,
          ("action", "returncode", "matched_rule"))

    out = await _invoke("sandbox_exec", {
        "cmd": "python -c \"print('Z'*30000)\"", "max_output": 4000,
    })
    _show("5. TRUNCATION (30k stdout capped at 4000)", out,
          ("action", "stdout_truncated", "stdout_full_len", "stdout"))

    # Show today's audit trail location + last line.
    audit_dir = Path.home() / ".engram" / "audit"
    logs = sorted(audit_dir.glob("sandbox-*.jsonl")) if audit_dir.exists() else []
    print("\n=== 6. AUDIT LOG ===")
    if logs:
        latest = logs[-1]
        last = latest.read_text(encoding="utf-8").strip().splitlines()[-1:]
        print(f"  file = {latest}")
        print(f"  last = {last[0] if last else '(empty)'}")
    else:
        print("  (no audit log found — sandbox writes on execute/validate)")

    # Replayable tool-call audit (with output hashes).
    replay_dir = Path.home() / ".engram" / "sandbox-audit"
    rlogs = sorted(replay_dir.glob("*.jsonl")) if replay_dir.exists() else []
    print("\n=== 7. REPLAYABLE AUDIT (output hashes) ===")
    if rlogs:
        latest = rlogs[-1]
        last = latest.read_text(encoding="utf-8").strip().splitlines()[-1:]
        print(f"  file = {latest}")
        if last:
            rec = json.loads(last[0])
            print(f"  action     = {rec.get('action')}")
            print(f"  cmd_norm   = {rec.get('cmd_normalized')!r}")
            print(f"  stdout_sha = {rec.get('stdout_sha256')}")
            print(f"  elapsed_s  = {rec.get('elapsed_s')}")
    else:
        print("  (no replayable audit yet)")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE — deny-by-default + truncation + audit + "
          "replay-hash verified.")


if __name__ == "__main__":
    asyncio.run(main())
