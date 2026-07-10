# Verimem side of the competitor probe — identical data, same scenarios.
import json
import os
import sqlite3
import tempfile
from pathlib import Path

M = 12
HELIOS = [f"On day {i} the team reviewed Project Helios progress and planned "
          f"the next milestone." for i in range(M)]
NOISE = [f"Note {i}: lunch plans and the weather in Lisbon today." for i in range(8)]
PAIRS = [
    ("The Zorbex reactor operates at 300 degrees.", "The Zorbex reactor operates at 900 degrees."),
    ("Project Aurora launches in March 2025.", "Project Aurora launches in September 2025."),
    ("Helena Vostok is the CEO of Kappa Dynamics.", "Marcus Reyes is the CEO of Kappa Dynamics."),
    ("The capital of Ruritania is Zenda.", "The capital of Ruritania is Strelsau."),
    ("The Talos engine uses hydrogen fuel.", "The Talos engine uses methane fuel."),
]

# --- aggregation (default config) ---
from engram.client import Memory
mem = Memory(Path(tempfile.mkdtemp()) / "agg.db")
for t in HELIOS:
    mem.add(t, topic="work/helios")
for t in NOISE:
    mem.add(t, topic="misc")
naive_top5 = sum(1 for h in mem.search("how many times did we discuss Project Helios", k=5)
                 if h.get("topic") == "work/helios")
ask = mem.ask("how many times did we discuss Project Helios")["count"]

# --- contradictions (reconcile ON + sim-fallback, the trust config) ---
os.environ["ENGRAM_RECONCILE_ON_WRITE"] = "1"
os.environ["ENGRAM_RECONCILE_SIM_FALLBACK"] = "1"
from engram.semantic import Fact, SemanticMemory
sm = SemanticMemory(db_path=Path(tempfile.mkdtemp()) / "con.db")
for old, new in PAIRS:
    sm.store(Fact(proposition=old, topic="s4", source_episodes=[old[:12]]))
    sm.store(Fact(proposition=new, topic="s4", source_episodes=[new[:12]]))
with sqlite3.connect(sm.db_path) as c:
    detected = c.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]

res = {"tool": "verimem",
       "aggregation": {"count_via_top5_naive": naive_top5, "count_via_ask": ask,
                       "ground_truth": M, "has_count_api": True},
       "contradictions": {"pairs": len(PAIRS), "detected_contradictions": detected,
                          "has_contradiction_signal": True}}
print(json.dumps(res, indent=2))
with open("benchmark/results/competitor_verimem.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)
