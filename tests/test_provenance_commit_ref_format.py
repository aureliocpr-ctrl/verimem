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
    # ⚠️ Questo banco NON guarda il `returncode`, ed è corretto così: guarda
    # l'ESITO PER COMPORTAMENTO — se `git` fallisce, `stdout` è vuoto e
    # l'`assert sha` del chiamante scatta. È la stessa forma di
    # `test_crash_injection_g3`, e vale più del codice d'uscita perché prova
    # che lo SHA *serve*, non solo che il comando è finito bene.
    # 📌 L'unica cosa che mancava era il PERCHÉ: senza `stderr` nel messaggio,
    # un `git` che fallisce per una ragione strana (repo non inizializzato,
    # `safe.directory`) si legge come «no HEAD sha» e basta. Una riga, e la
    # diagnosi c'è.
    # ⚠️ SOLLEVA, non rende una stringa di diagnosi: la prima versione di questa
    # riga rendeva `f"__git_muto__ rc=…"`, che è TRUTHY — e avrebbe spento
    # l'`assert sha` del chiamante, cioè avrebbe rotto il presidio che stavo
    # arricchendo. Un valore di ripiego dentro una funzione il cui risultato
    # viene testato per verità è un modo silenzioso di disattivare un controllo.
    if not out.stdout.strip():
        raise AssertionError(
            f"`git rev-parse --short HEAD` non ha reso uno SHA: "
            f"returncode={out.returncode} stderr={out.stderr.strip()[:200]!r}")
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
