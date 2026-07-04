"""Cycle 277 (2026-05-23) — Session lineage chain visualizer.

Pioneering singolarità #28: walk the lineage_to chain backward from
a tip fact, emit DOT graph + JSON metadata. Foundation for
cross-session retrospective analysis.

Background: cycles 253-276 produced a 15+ hop fact chain via clp
save --lineage-to auto. Each fact references parent via lineage_to.
This script materialises the chain as a graph artifact.

Usage:
    python -m scripts.visualize_session_lineage \\
        --tip d315f906ae15 \\
        --max-hops 30 \\
        --output session_lineage.dot
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def walk_chain_backward(
    db: Path, tip_id: str, max_hops: int,
) -> list[dict]:
    """Follow lineage_to backward. Returns list of facts from tip to root."""
    conn = sqlite3.connect(str(db))
    try:
        chain: list[dict] = []
        current = tip_id
        visited: set[str] = set()
        for _ in range(max_hops):
            if not current or current in visited:
                break
            visited.add(current)
            row = conn.execute(
                "SELECT id, topic, proposition, lineage_to, created_at "
                "FROM facts WHERE id = ? OR id LIKE ?",
                (current, f"{current}%"),
            ).fetchone()
            if not row:
                break
            fid, topic, prop, parent, ts = row
            chain.append({
                "id": fid,
                "id_short": fid[:10],
                "topic": topic,
                "proposition_excerpt": (prop or "")[:120],
                "lineage_to": parent,
                "lineage_to_short": (parent or "")[:10],
                "created_at": ts,
                "created_at_iso": datetime.fromtimestamp(ts).isoformat()
                if ts else None,
            })
            current = parent
    finally:
        conn.close()
    return chain


def emit_dot(chain: list[dict]) -> str:
    """Emit graphviz DOT representation of the chain."""
    lines = [
        "digraph SessionLineage {",
        "  rankdir=BT;",
        "  node [shape=box, fontname=\"Helvetica\", fontsize=10];",
        "  edge [arrowhead=open];",
    ]
    for f in chain:
        # Sanitise topic for label
        label = (
            f"{f['id_short']}\\n"
            f"{f['topic'][:60]}\\n"
            f"{f['created_at_iso'] or '?'}"
        )
        # Cluster by topic prefix
        topic = f["topic"] or ""
        if topic.startswith("project/hippoagent/"):
            color = "lightblue"
        elif topic.startswith("rules/"):
            color = "lightyellow"
        elif topic.startswith("lessons/"):
            color = "lightgreen"
        elif topic.startswith("critic/"):
            color = "lightcoral"
        else:
            color = "white"
        lines.append(
            f"  \"{f['id_short']}\" "
            f"[label=\"{label}\", fillcolor={color}, style=filled];"
        )
    for f in chain:
        if f["lineage_to_short"]:
            lines.append(
                f"  \"{f['id_short']}\" -> "
                f"\"{f['lineage_to_short']}\";"
            )
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument(
        "--tip", required=True, type=str,
        help="Tip fact id (full or short).",
    )
    parser.add_argument("--max-hops", type=int, default=30)
    parser.add_argument(
        "--output-dot", type=Path, default=None,
    )
    parser.add_argument(
        "--output-json", type=Path, default=None,
    )
    args = parser.parse_args()

    chain = walk_chain_backward(args.db, args.tip, args.max_hops)
    if not chain:
        print(f"[error] chain empty for tip {args.tip}", file=sys.stderr)
        return 1

    print(f"[ok] chain {len(chain)} hops", file=sys.stderr)
    dot = emit_dot(chain)
    if args.output_dot:
        args.output_dot.write_text(dot, encoding="utf-8")
        print(f"Wrote {args.output_dot}", file=sys.stderr)
    if args.output_json:
        args.output_json.write_text(
            json.dumps(chain, indent=2), encoding="utf-8",
        )
        print(f"Wrote {args.output_json}", file=sys.stderr)

    # Print summary
    by_namespace: dict[str, int] = {}
    for f in chain:
        ns = (f["topic"] or "").split("/")[0] or "root"
        by_namespace[ns] = by_namespace.get(ns, 0) + 1
    print(json.dumps({
        "n_hops": len(chain),
        "tip_id": chain[0]["id_short"],
        "root_id": chain[-1]["id_short"],
        "by_namespace": by_namespace,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
