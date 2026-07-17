"""Cycle 138 — REAL-WORLD replay (not synthetic).

Aurelio direttiva 2026-05-18: "non lab empirico, lab reali!".

This script replays the 1183 facts currently sitting in the live
~/.engram corpus through the cycle 138 gate (run_validation_gate).
For each historical fact we ask: "if this same proposition+verified_by
were submitted to hippo_remember today, would the cycle 138 gate
have downgraded / rejected it?".

Cross-check: cycle 137's scan_orphaned_facts already flagged 75 of the
1183 facts as L1-orphan (52 shipped + 22 diagnosis + 1 task_state).
The cycle 138 gate runs the SAME three detectors at write-time, so the
overlap must be ~100% (modulo any classifier-bug differences).

Output: per-layer breakdown of what the gate would do, plus the 75-row
cross-check against cycle 137. No mutation of the live corpus —
strictly read-only.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.anti_confab_gate import run_validation_gate
from verimem.anti_confabulation import scan_orphaned_facts
from verimem.semantic import SemanticMemory


class _AgentShim:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


def _temp_clone_corpus() -> tuple[Path, sqlite3.Connection]:
    src = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not src.exists():
        src = Path.home() / ".engram" / "semantic.db"
    tmp = Path.home() / ".engram_lab_real_replay.db"
    if tmp.exists():
        tmp.unlink()
    shutil.copyfile(src, tmp)
    return tmp, sqlite3.connect(str(tmp))


def main() -> int:
    tmp, conn = _temp_clone_corpus()
    try:
        rows = conn.execute(
            "SELECT id, proposition, topic, verified_by, status "
            "FROM facts "
            "WHERE superseded_by IS NULL "
            "AND status NOT IN ('orphaned', 'quarantined')"
        ).fetchall()
        total = len(rows)
        print(f"Loaded {total} live facts from {tmp}")
        print()
        # Re-instantiate SemanticMemory pointed at the same temp file so
        # validate_claim can search inside.
        sm = SemanticMemory(db_path=tmp)
        agent = _AgentShim(sm)

        actions = Counter()
        layer_hits = Counter()
        downgraded_ids: list[str] = []
        l1_only_ids: list[str] = []

        t_start = time.perf_counter()
        for r in rows:
            fid, prop, topic, vb_raw, status = r
            # verified_by is stored as JSON list — be defensive.
            verified_by: list[str] = []
            if vb_raw:
                import json as _json
                try:
                    parsed = _json.loads(vb_raw)
                    if isinstance(parsed, list):
                        verified_by = [str(x) for x in parsed]
                except Exception:
                    pass

            # Default config: validate="fast", gate_mode="downgrade".
            g = run_validation_gate(
                proposition=prop or "",
                verified_by=verified_by,
                topic=topic,
                agent=agent,
                validate="fast",  # production default
                gate_mode="downgrade",
            )
            actions[g.action] += 1
            layers_fired = {w["layer"] for w in g.warnings}
            for ll in layers_fired:
                layer_hits[ll] += 1
            if g.action == "downgrade":
                downgraded_ids.append(fid)
                if "L1" in layers_fired and "L1.5" not in layers_fired:
                    l1_only_ids.append(fid)

        t_fast = time.perf_counter() - t_start

        # Cross-check against cycle 137 scan_orphaned_facts.
        # Bypass recall (limited query path) and iterate the legacy db
        # directly — we need every row for the L1 detector parity check.
        with sm._connect() as c2:  # noqa: SLF001
            corpus_rows = c2.execute("SELECT * FROM facts").fetchall()
        corpus_facts = [sm._row(rr) for rr in corpus_rows]  # noqa: SLF001
        l2_report = scan_orphaned_facts(corpus_facts)
        l2_shipped = {fid for fid, _ in l2_report["shipped"]}
        l2_diagnosis = {fid for fid, _ in l2_report["diagnosis"]}
        l2_task_state = {fid for fid, _ in l2_report["task_state"]}
        l2_union = l2_shipped | l2_diagnosis | l2_task_state

        gate_downgraded_set = set(downgraded_ids)

        # Now a full-mode pass on a 200-sample subset to measure
        # L3 contradictions (full pass on 1183 would still run but
        # could be slower; 200 random is enough signal).
        import random
        sample = random.Random(42).sample(rows, min(200, total))
        t_full_start = time.perf_counter()
        full_actions = Counter()
        full_layer = Counter()
        for r in sample:
            fid, prop, topic, vb_raw, _ = r
            verified_by = []
            if vb_raw:
                import json as _json
                try:
                    parsed = _json.loads(vb_raw)
                    if isinstance(parsed, list):
                        verified_by = [str(x) for x in parsed]
                except Exception:
                    pass
            g = run_validation_gate(
                proposition=prop or "",
                verified_by=verified_by,
                topic=topic,
                agent=agent,
                validate="full",
                gate_mode="reject",
            )
            full_actions[g.action] += 1
            for w in g.warnings:
                full_layer[w["layer"]] += 1
        t_full = time.perf_counter() - t_full_start

        # --- Reports ---
        print("=" * 70)
        print("FAST PASS — full corpus, validate='fast' gate_mode='downgrade'")
        print("=" * 70)
        print(f"N={total}, wall={t_fast:.2f}s ({(t_fast/total)*1000:.3f}ms/fact)")
        print(f"actions:        {dict(actions)}")
        print(f"layer hits:     {dict(layer_hits)}")
        print(f"downgraded:     {len(downgraded_ids)}")
        print()

        print("=" * 70)
        print("L1 CROSS-CHECK vs cycle 137 scan_orphaned_facts")
        print("=" * 70)
        print(f"cycle 137 scan: shipped={len(l2_shipped)} diagnosis="
              f"{len(l2_diagnosis)} task_state={len(l2_task_state)} "
              f"union={len(l2_union)}")
        print(f"cycle 138 gate downgraded: {len(gate_downgraded_set)}")
        print(f"intersection:   {len(gate_downgraded_set & l2_union)}")
        print(f"only in cycle 137 (gate missed): "
              f"{len(l2_union - gate_downgraded_set)}")
        print(f"only in cycle 138 (gate extra):  "
              f"{len(gate_downgraded_set - l2_union)}")
        if gate_downgraded_set - l2_union:
            extras = sorted(gate_downgraded_set - l2_union)[:5]
            print(f"  sample extras: {extras}")
        if l2_union - gate_downgraded_set:
            misses = sorted(l2_union - gate_downgraded_set)[:5]
            print(f"  sample misses: {misses}")
        print()

        print("=" * 70)
        print("FULL PASS — N=200 random sample, validate='full' "
              "gate_mode='reject'")
        print("=" * 70)
        print(f"wall={t_full:.2f}s ({(t_full/len(sample))*1000:.1f}ms/fact)")
        print(f"actions:        {dict(full_actions)}")
        print(f"layer hits:     {dict(full_layer)}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            tmp.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
