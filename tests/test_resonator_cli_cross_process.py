"""Cycle 401 — ResonatorMemory CLI cross-process N=10 live integration test.

Test scenario REALE production: N writes via separate subprocesses,
single recall in nuovo subprocess. Simula uso real CLI da shell.

Falsifiable contract: ≥7/10 recovery (cycle 393 bench mean 88% at N=10).
"""
from __future__ import annotations

import subprocess
import sys


def test_cli_cross_process_n10_recall_above_70pct(tmp_path) -> None:
    """A1 honest empirical: N=10 cross-process recall ≥7/10.

    Each remember + recall is a separate Python subprocess (like real
    shell usage). Tests save/load round-trip + matching pursuit at N=10.
    """
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"

    facts = [
        "aurelio is the ceo",
        "claude is the cto",
        "hippoagent is memory",
        "python is a language",
        "rome is in italy",
        "milan is north italy",
        "naples is south italy",
        "code is testable",
        "tests are necessary",
        "ship daily not weekly",
    ]
    for txt in facts:
        r = subprocess.run(
            [
                sys.executable, "-m", "engram.resonator_cli",
                "--state-path", str(state),
                "--index-path", str(index),
                "remember", txt,
            ],
            capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, (
            f"remember failed: stderr={r.stderr}"
        )

    r = subprocess.run(
        [
            sys.executable, "-m", "engram.resonator_cli",
            "--state-path", str(state),
            "--index-path", str(index),
            "recall",
        ],
        capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == 0

    import json
    out = json.loads(r.stdout)
    recovered_texts = [x["text"] for x in out["recovered"]]
    correct = sum(1 for t in recovered_texts if t in facts)
    print(f"\ncycle 401 cross-process N=10: recovered {correct}/10 "
          f"unknown={out['n_unknown']}")
    assert correct >= 7, (
        f"cross-process N=10 recovery {correct}/10 < 70%. "
        f"FALSIFIED honest baseline."
    )
