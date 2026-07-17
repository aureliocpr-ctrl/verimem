"""Real benchmark of cycle #46b _content_hash_id behavior.

Spawns a fresh Python subprocess with the UPDATED code, runs a sequence
of hippo_remember-equivalent calls via the internal dispatcher, and
measures:
  - id determinism (same input -> same id, always)
  - row count after N calls (should be N_unique_contents, not N)
  - ok_replaced count (should be N - N_unique)
  - wall time + per-call latency

This validates the live behavior of #46b before merging.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# E402 exception: the env setup MUST happen before mcp_server / engram
# imports because those read CONFIG at module load. noqa marks below.
os.environ["HIPPO_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTHONUTF8"] = "1"

# Force fresh code load from disk (assumes script at <repo>/scripts/)
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Use isolated tmp data dir so we don't pollute prod
tmp = Path(tempfile.mkdtemp(prefix="cycle46b-live-"))
os.environ["HIPPO_DATA_DIR"] = str(tmp)
os.environ["ENGRAM_DATA_DIR"] = str(tmp)

from mcp.types import CallToolRequest, CallToolRequestParams  # noqa: E402

from verimem import mcp_server  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402


# Minimal stub agent
class _StubSemantic:
    def __init__(self, db_path: Path) -> None:
        self.store_impl = SemanticMemory(db_path=db_path)
        self.replace_count = 0
        self.new_count = 0

    def store(self, fact, *, return_replaced: bool = False):
        replaced = self.store_impl.store(fact, return_replaced=True)
        if replaced:
            self.replace_count += 1
        else:
            self.new_count += 1
        return replaced if return_replaced else None

    def count(self) -> int:
        return self.store_impl.count()


class _Agent:
    semantic = None
    skills = None
    memory = None


a = _Agent()
a.semantic = _StubSemantic(tmp / "semantic" / "semantic.db")
mcp_server._agent = a
mcp_server._ag = lambda: a


async def call_remember(prop, topic, conf=0.9):
    h = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
        params=CallToolRequestParams(name="hippo_remember",
            arguments={"proposition": prop, "topic": topic, "confidence": conf}))
    result = await h(req)
    payload = result.root if hasattr(result, "root") else result
    return json.loads(payload.content[0].text)


# Bench scenario:
# - 20 unique (proposition, topic) pairs
# - Each repeated 50 times = 1000 total calls
# - Expected: 20 rows in DB, 20 ok_new + 980 ok_replaced
N_UNIQUE = 20
REPEATS = 50
TOTAL = N_UNIQUE * REPEATS

async def main():
    print("=== Cycle #46b live benchmark ===")
    print(f"  data dir:    {tmp}")
    print(f"  unique:      {N_UNIQUE}")
    print(f"  repeats:     {REPEATS}")
    print(f"  total calls: {TOTAL}")
    print()

    contents = [(f"Fact number {i} is the truth", f"bench/cycle46b/i{i}")
                for i in range(N_UNIQUE)]

    # First pass: 1 unique call per content
    print("Pass 1: 20 unique inserts (expect 20× ok_new, replaced=False)")
    ids_first = []
    t0 = time.time()
    for prop, topic in contents:
        out = await call_remember(prop, topic)
        ids_first.append(out["id"])
        assert out.get("replaced") is False, f"first call should be fresh: {out}"
    t1 = time.time() - t0
    print(f"  wall: {t1:.3f}s ({N_UNIQUE/t1:.1f} call/s)")
    print(f"  DB count after pass 1: {a.semantic.count()}")

    # Second pass: repeats — every call should be replaced=True
    print(f"\nPass 2: {N_UNIQUE * (REPEATS-1)} repeats (expect all replaced=True)")
    t0 = time.time()
    n_replaced = 0
    n_new_in_pass2 = 0
    for r in range(REPEATS - 1):
        for i, (prop, topic) in enumerate(contents):
            out = await call_remember(prop, topic, conf=0.5 + 0.01 * r)
            if out.get("replaced"):
                n_replaced += 1
            else:
                n_new_in_pass2 += 1
            # Id must match first pass for this content
            assert out["id"] == ids_first[i], (
                f"id changed for content {i}: {out['id']} vs {ids_first[i]}"
            )
    t2 = time.time() - t0
    rest_calls = N_UNIQUE * (REPEATS - 1)
    print(f"  wall: {t2:.3f}s ({rest_calls/t2:.1f} call/s)")
    print(f"  replaced=True: {n_replaced} / {rest_calls}")
    print(f"  unexpected replaced=False in pass 2: {n_new_in_pass2}")

    print(f"\nDB count after total {TOTAL} calls: {a.semantic.count()}")
    print(f"Stub agent.new_count={a.semantic.new_count} replace_count={a.semantic.replace_count}")
    print("\nEXPECTED: 20 rows, 20 new + 980 replaced")
    print(f"ACTUAL:   {a.semantic.count()} rows, {a.semantic.new_count} new + {a.semantic.replace_count} replaced")
    print(f"\nVERDICT: {'CLEAN' if a.semantic.count() == N_UNIQUE and a.semantic.replace_count == N_UNIQUE*(REPEATS-1) else 'FAIL'}")

asyncio.run(main())
