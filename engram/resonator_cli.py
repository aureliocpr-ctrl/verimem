"""Cycle 399 (2026-05-23) — ResonatorMemory CLI production wrapper.

Standalone CLI to remember/recall/save/load using ResonatorMemory.
NON modifica engram.semantic.py monolite (cycle 399 conservative scope).

Storage: ~/.engram/resonator/memory.npz (default).

Commands:
  remember <text>           — encode text → add to aggregate
  recall                    — matching_pursuit recall all + reverse map
  stats                     — show state (n_facts, storage, aggregate norm)
  save [path]               — persist (npz)
  load [path]               — restore (npz)
  reset                     — wipe memory

Falsifiable contracts (vedi tests/test_resonator_cli.py):
  (a) remember + recall roundtrip on 1 fact = SUCCESS
  (b) load(save(state)) preserves n_facts + aggregate
  (c) reset zeros aggregate + cleanup cleanup

Usage:
    python -m engram.resonator_cli remember "fact text"
    python -m engram.resonator_cli recall
    python -m engram.resonator_cli stats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_STATE_PATH = Path.home() / ".engram" / "resonator" / "memory.npz"
DEFAULT_INDEX_PATH = Path.home() / ".engram" / "resonator" / "index.jsonl"
DEFAULT_D = 4096
DEFAULT_M = 32
DEFAULT_K = 3


def _load_state(
    state_path: Path = DEFAULT_STATE_PATH,
) -> Any:
    """Load state if exists, else fresh."""
    from engram.resonator_memory import ResonatorMemory
    if state_path.exists():
        return ResonatorMemory.load(state_path)
    return ResonatorMemory(
        n_roles=DEFAULT_K, atoms_per_role=DEFAULT_M, d=DEFAULT_D,
    )


def _save_state(
    mem: Any, state_path: Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    return mem.save(state_path)


def _load_text_index(
    index_path: Path = DEFAULT_INDEX_PATH,
) -> dict[tuple[int, ...], str]:
    """Load text→indices reverse mapping (JSONL)."""
    if not index_path.exists():
        return {}
    mapping: dict[tuple[int, ...], str] = {}
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        mapping[tuple(entry["indices"])] = entry["text"]
    return mapping


def _append_text_index(
    indices: tuple[int, ...], text: str,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"indices": list(indices), "text": text}
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def cmd_remember(text: str, state_path: Path, index_path: Path) -> dict[str, Any]:
    from engram.resonator_text_bridge import text_to_atoms_via_hash
    mem = _load_state(state_path)
    indices = text_to_atoms_via_hash(text, DEFAULT_K, DEFAULT_M)
    r = mem.remember_tuple(indices)
    _append_text_index(indices, text, index_path)
    _save_state(mem, state_path)
    return {
        "ok": True,
        "text": text,
        "indices": list(indices),
        "n_facts": r["n_facts"],
        "aggregate_norm": r["aggregate_norm"],
    }


def cmd_recall(state_path: Path, index_path: Path,
               max_facts: int = 100) -> dict[str, Any]:
    mem = _load_state(state_path)
    res = mem.recall_all_via_matching_pursuit(
        max_facts=max_facts, n_restarts_per_pass=32,
    )
    index = _load_text_index(index_path)
    recovered: list[dict[str, Any]] = []
    unknown: list[list[int]] = []
    for idx in res["found_facts"]:
        if idx in index:
            recovered.append({"indices": list(idx), "text": index[idx]})
        else:
            unknown.append(list(idx))
    return {
        "ok": True,
        "n_passes": res["n_passes"],
        "n_recovered": len(recovered),
        "n_unknown": len(unknown),
        "recovered": recovered,
        "unknown_atoms": unknown,
    }


def cmd_stats(state_path: Path, index_path: Path) -> dict[str, Any]:
    mem = _load_state(state_path)
    index = _load_text_index(index_path)
    s = mem.stats()
    return {
        **s,
        "n_indexed_texts": len(index),
        "state_path": str(state_path),
        "index_path": str(index_path),
        "state_exists": state_path.exists(),
        "index_exists": index_path.exists(),
    }


def cmd_reset(state_path: Path, index_path: Path) -> dict[str, Any]:
    removed = []
    for p in (state_path, index_path):
        if p.exists():
            p.unlink()
            removed.append(str(p))
    return {"ok": True, "removed": removed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-path", type=Path, default=DEFAULT_STATE_PATH,
    )
    parser.add_argument(
        "--index-path", type=Path, default=DEFAULT_INDEX_PATH,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub_r = sub.add_parser("remember")
    sub_r.add_argument("text")
    sub.add_parser("recall")
    sub.add_parser("stats")
    sub.add_parser("reset")
    args = parser.parse_args()

    if args.cmd == "remember":
        out = cmd_remember(args.text, args.state_path, args.index_path)
    elif args.cmd == "recall":
        out = cmd_recall(args.state_path, args.index_path)
    elif args.cmd == "stats":
        out = cmd_stats(args.state_path, args.index_path)
    elif args.cmd == "reset":
        out = cmd_reset(args.state_path, args.index_path)
    else:
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
