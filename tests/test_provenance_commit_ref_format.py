"""RED->GREEN: il provenance validator deve accettare il formato commit:<sha>
(colon), non solo commit <sha> (spazio).

DOUBLE-BIND scoperto dal benchmark anti-confab (scripts/bench_anticonfab_effectiveness.py):
- i detector L1 (l1_orphan/l1_extended) creditano come prova SOLO il formato
  ``commit:<sha>`` (colon) — e' il formato che il warning raccomanda;
- il provenance validator (_COMMIT_PATTERN) accettava SOLO ``commit <sha>`` (spazio).
Risultato: un claim con ``commit:<sha>`` passa L1 ma viene declassato dallo store
(provenance non lo riconosce) -> falso positivo sui claim legittimi.

Fix: _COMMIT_PATTERN accetta colon O spazio. L'esistenza del commit resta
verificata via git rev-parse (nessun indebolimento di sicurezza).

Hermetic: usa il repo HippoAgent reale come repo_root (commit reali esistono).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from verimem.provenance_validator import is_valid_provenance_ref, validate_verified_refs

REPO = Path(__file__).resolve().parents[1]


def _a_real_sha() -> str:
    """Uno SHA reale di questo repo (HEAD), short form."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    return out.stdout.strip()


def test_colon_format_commit_ref_is_accepted_when_commit_exists():
    sha = _a_real_sha()
    assert sha, "no HEAD sha"
    # formato COLON (quello raccomandato dai detector L1) deve essere riconosciuto
    assert is_valid_provenance_ref(f"commit:{sha}", repo_root=REPO) is True, (
        "double-bind: il provenance deve accettare commit:<sha> (colon), "
        "non solo commit <sha> (spazio)"
    )


def test_space_format_still_accepted():
    sha = _a_real_sha()
    assert is_valid_provenance_ref(f"commit {sha}", repo_root=REPO) is True, (
        "il formato spazio storico deve restare valido (backward-compatible)"
    )


def test_colon_format_fake_sha_still_rejected():
    # sicurezza: il colon non deve far passare uno SHA inventato
    assert is_valid_provenance_ref("commit:deadbeefcafe", repo_root=REPO) is False, (
        "uno SHA inventato deve essere rifiutato anche in formato colon"
    )
    assert validate_verified_refs(["commit:deadbeefcafe"], repo_root=REPO) is False
