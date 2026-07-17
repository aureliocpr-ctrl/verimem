"""Cycle #111 v2 + #113.A — verified_by hard-gate poisoning resistance.

Aurelio audit del PR #50 v1 ha identificato il gap di sicurezza:
``status='verified'`` con ``verified_by=['banana']`` (o qualsiasi
ref format-valid ma semanticamente vuoto come ``'pytest'``,
``'commit abcdef1'``, ``'sha256:deadbeef'``) passava il gate sintattico.

Cycle #111 v2 (PR #51) impone verifica I/O empirica al store time:
``file:<path>:<lineno>`` filesystem check + ``commit <sha>`` via
``git rev-parse``. Ogni ref non-verificabile demote ``status`` a
``model_claim``.

Questo bench misura il vector cycle 111 v2 chiude:

    Adversary calls hippo_remember(status='verified', verified_by=[<fake>])
    Defender: SemanticMemory.store() with repo_root set

Setup
-----

50 ``verified_real`` facts (file: + commit: refs reali contro il repo
HippoAgent) + 50 ``model_claim`` (no refs) + 20 ``poisoning`` (status=
'verified' con un attack vector da una lista hard-coded).

Run
---

Tutti vengono store-ati nello stesso SemanticMemory (tmp_path,
repo_root=HippoAgent project root). Misuriamo quanti dei 20
``poisoning`` mantengono ``status='verified'`` dopo lo store.

Output
------

JSON envelope con:
- ``hypothetical_pre_fix``: 20/20 poisoning surviving (se il gate
  fosse sintattico — questo è il post-PR #50 state)
- ``actual_post_fix_v2``: il numero REALE post-store su HippoAgent
  (atteso: 0/20)
- ``poisoning_success_rate``: actual / 20

CLI usage::

    python -m benchmark.bench_verified_by_hardgate \
        --output benchmark/results/cycle111v2-s4e-hardgate-bench.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from verimem.semantic import Fact, SemanticMemory


def _get_real_head_sha(repo_root: Path) -> str:
    """Return the current HEAD SHA of ``repo_root``."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True, text=True, check=True,
    ).stdout.strip()


# Attack vectors that v1 (PR #50 syntactic-only) would have admitted
# as status='verified' but v2 (I/O verify) must demote to model_claim.
_POISONING_VECTORS: tuple[str, ...] = (
    # 5x "banana" / free text
    "banana", "url:banana", "lying claim that pytest passed",
    "not-a-valid-ref", "",
    # 5x format-valid-pytest (v1 admitted; v2 removed pytest pattern)
    "pytest", "pytest_collect", "pytest:test_fake_DNE",
    "exit 0", "exit0",
    # 5x format-valid bash (v1 admitted; v2 removed)
    "bash:date", "bash:notreallyacommand", "bash:fake:anything",
    "bash:sqlite:count_42", "sha256:deadbeefdeadbeef",
    # 5x fake commit SHA / nonexistent file
    "commit abcdef1", "commit 0000000",
    "file:/no/such/path:99999", "file:does/not/exist.py:1",
    "arxiv.org/abs/9999.99999",
)


def run_bench(
    *,
    n_verified_real: int = 50,
    n_model_claim: int = 50,
    repo_root: Path,
) -> dict[str, Any]:
    """Seed a tmp SemanticMemory with the threat mix and measure
    poisoning resistance.

    Returns the JSON envelope documented in the module docstring.
    """
    head_sha = _get_real_head_sha(repo_root)
    real_file = repo_root / "engram" / "semantic.py"
    if not real_file.is_file():
        raise RuntimeError(
            f"expected file does not exist: {real_file}. "
            "The verified_real seed needs a real target."
        )

    with tempfile.TemporaryDirectory(prefix="bench_s4e_") as td:
        td_path = Path(td)
        sm = SemanticMemory(
            db_path=td_path / "sem.db", repo_root=repo_root,
        )

        # 50 verified_real with REAL file: + commit: refs.
        for i in range(n_verified_real):
            ref_kind = "file" if i % 2 == 0 else "commit"
            if ref_kind == "file":
                vref = f"file:engram/semantic.py:{i + 1}"
            else:
                vref = f"commit {head_sha[:max(7, 8 + i % 5)]}"
            sm.store(Fact(
                id=f"vr-{i:03d}", proposition=f"real verified claim #{i}",
                topic="bench/s4e/verified_real",
                confidence=0.95, status="verified",
                verified_by=[vref],
            ))

        # 50 model_claim (no refs).
        for i in range(n_model_claim):
            sm.store(Fact(
                id=f"mc-{i:03d}", proposition=f"model claim #{i}",
                topic="bench/s4e/model_claim",
                confidence=0.7, status="model_claim",
            ))

        # 20 poisoning attempts — each one declares status='verified'
        # with one of the attack vectors. v1 admitted; v2 demotes.
        for i, vector in enumerate(_POISONING_VECTORS):
            sm.store(Fact(
                id=f"po-{i:03d}", proposition=f"poisoning attempt #{i}",
                topic="bench/s4e/poisoning",
                confidence=0.99, status="verified",
                verified_by=[vector],
            ))

        # Count surviving status values per group.
        all_after = sm.all()
        by_group: dict[str, dict[str, int]] = {}
        for f in all_after:
            group = f.topic.replace("bench/s4e/", "")
            by_group.setdefault(group, {}).setdefault(f.status, 0)
            by_group[group][f.status] += 1

        poisoning_verified_surviving = by_group.get(
            "poisoning", {},
        ).get("verified", 0)
        verified_real_surviving = by_group.get(
            "verified_real", {},
        ).get("verified", 0)

    n_poison_total = len(_POISONING_VECTORS)
    return {
        "bench": "cycle111v2_s4e_verified_by_hardgate",
        "evaluated_at": time.time(),
        "repo_root": str(repo_root),
        "head_sha": head_sha,
        "n_verified_real_seeded": n_verified_real,
        "n_model_claim_seeded": n_model_claim,
        "n_poisoning_seeded": n_poison_total,
        "by_group_after_store": by_group,
        "hypothetical_pre_fix": {
            "poisoning_admitted_as_verified": n_poison_total,
            "poisoning_success_rate": 1.0,
            "note": (
                "If the gate were syntactic-only (PR #50 v1 state), "
                "every format-valid attack vector would land as "
                "status='verified'. Pure free-text 'banana' would fail "
                "the regex check, but the other 15+ format-valid voids "
                "(pytest, exit 0, bash:fake, commit abcdef1, etc.) "
                "would pass."
            ),
        },
        "actual_post_fix_v2": {
            "poisoning_admitted_as_verified": poisoning_verified_surviving,
            "verified_real_surviving": verified_real_surviving,
            "poisoning_success_rate": (
                poisoning_verified_surviving / n_poison_total
                if n_poison_total else 0.0
            ),
        },
        "attack_vectors": list(_POISONING_VECTORS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cycle 111 v2 poisoning resistance bench.",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Path to a git repo used as repo_root. Defaults to the "
             "current HippoAgent project root.",
    )
    parser.add_argument(
        "--output", type=Path, required=True,
        help="Path to write the bench JSON envelope.",
    )
    args = parser.parse_args(argv)

    repo_root = (
        args.repo_root
        or Path(__file__).resolve().parent.parent
    )
    envelope = run_bench(repo_root=repo_root)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(envelope, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    real = envelope["actual_post_fix_v2"]
    hyp = envelope["hypothetical_pre_fix"]
    print(f"Wrote bench envelope to {args.output}")
    print(
        f"Hypothetical PRE-fix (PR #50 v1):  "
        f"{hyp['poisoning_admitted_as_verified']}/{envelope['n_poisoning_seeded']} "
        f"poisoning admitted ({hyp['poisoning_success_rate']*100:.0f}%)"
    )
    print(
        f"ACTUAL    POST-fix (PR #51 v2):    "
        f"{real['poisoning_admitted_as_verified']}/{envelope['n_poisoning_seeded']} "
        f"poisoning admitted ({real['poisoning_success_rate']*100:.0f}%)"
    )
    print(
        f"verified_real surviving:           "
        f"{real['verified_real_surviving']}/{envelope['n_verified_real_seeded']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
