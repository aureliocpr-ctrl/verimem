#!/usr/bin/env python
"""DEPRECATED + DEFUSED (2026-06-07). DO NOT USE.

This script hardcoded the embedding target to
``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`` (384-dim) and
force-set ``HIPPO_EMBEDDING_MODEL`` to it before importing config. Running it
against a corpus whose ACTIVE model is ``intfloat/multilingual-e5-base`` (768-dim)
would DOWNGRADE every re-embedded row to a wrong-dim vector that the per-row
isolation filter then silently excludes from recall — i.e. it corrupts reach.

Use the model-agnostic replacement instead, which reads the ACTIVE model from
``embedding.model_signature()`` (never hardcoded), probes the dim before writing,
backs up, commits in chunks, and verifies:

    python scripts/reembed_to_active_model.py            # dry-run
    python scripts/reembed_to_active_model.py --live     # write

This stub refuses to run so the landmine cannot fire by accident.
"""
from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "flip_embedding.py is DEPRECATED and DISABLED — it hardcoded a 384-dim "
        "model and would corrupt an e5-768 corpus.\n"
        "Use: python scripts/reembed_to_active_model.py [--live]\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
