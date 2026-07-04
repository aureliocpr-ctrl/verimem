"""Bench ablation: disable Sprint 6a knobs via dataclass replace, then run bench.

Runs with the same TASKS as bench_engram_code.py but mutates CONFIG to turn
OFF the 7 active-memory fixes one-by-one (or all together) — to compare against
the bench results when they are all ON. Useful to see if the fixes help, hurt,
or are noise on this specific model.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram import config as _cfg

# Disable Sprint 6a active-memory fixes by setting fields on the SAME singleton.
# Frozen dataclass → we have to bypass __setattr__.
fields_to_patch = {
    "compile_adaptive_enabled": False,         # fix 1
    "forward_replay_include_failures": False,  # fix 2
    "hebbian_decay_enabled": False,            # fix 3
    "counterfactual_dedup_threshold": 2.0,     # fix 4 effectively off
    "schema_skip_if_covered": False,           # fix 5
    "working_memory_pruning_enabled": False,   # fix 7 (most impactful)
}
for k, v in fields_to_patch.items():
    object.__setattr__(_cfg.CONFIG, k, v)
print(f"[ablation] working_memory_pruning_enabled={_cfg.CONFIG.working_memory_pruning_enabled}")
print(f"[ablation] forward_replay_include_failures={_cfg.CONFIG.forward_replay_include_failures}")
print(f"[ablation] compile_adaptive_enabled={_cfg.CONFIG.compile_adaptive_enabled}")
print(f"[ablation] schema_skip_if_covered={_cfg.CONFIG.schema_skip_if_covered}")

# Now invoke the bench main
from scripts.bench_engram_code import main  # noqa: E402

sys.exit(main())
