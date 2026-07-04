"""Diagnostic: isolate the recall rerank cost (cold-load vs steady predict).

Hard external timeout wraps the run (caller uses `timeout`). Prints
per-phase wall time so we can size the circuit-breaker budget.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEM = Path.home() / ".engram" / "semantic" / "semantic.db"
QUERY = sys.argv[1] if len(sys.argv) > 1 else "il save di engram si bloccava come risolto"

from engram import embedding  # noqa: E402
from engram.semantic import SemanticMemory  # noqa: E402

print(f"[diag] db={SEM} exists={SEM.exists()}", flush=True)
mem = SemanticMemory(db_path=SEM)
embedding.encode(embedding.as_query("warmup"))  # warm encoder only

# NO pre-load of the CE: recall #1 hits the COLD cross-encoder. WITH the
# circuit-breaker it must cap at ~budget (3s) instead of ~33s; the model
# keeps warming in the background, so a LATER recall reranks.
for i in range(3):
    t0 = time.perf_counter()
    hits = mem.recall(QUERY, k=5)
    print(f"[diag] recall ON #{i+1} (cold CE on #1): "
          f"{(time.perf_counter()-t0)*1000:.0f}ms hits={len(hits)}", flush=True)
    time.sleep(0.2)
print("[diag] DONE", flush=True)
