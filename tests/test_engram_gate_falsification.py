"""FASE 3 — FALSIFICAZIONE del gate anti-confab (Popper). Scoperte empiriche
2026-06-02 driving run_validation_gate su scenari reali.

Doppio scopo:
- i test che PASSANO documentano comportamenti CORRETTI da preservare (regression-guard);
- i test xfail documentano failure-mode REALI da chiudere in FASE 4 (con prova riproducibile).

Hermetic: gate puro, niente DB, niente rete.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from engram.anti_confab_gate import run_validation_gate

CONFAB = "SHIPPED la feature X, tutti i test passano, completato e verificato"


def _gate(**kw):
    base = dict(verified_by=None, topic="project/x", agent=None, validate="fast",
                writer_role="agent_inference")
    base.update(kw)
    return run_validation_gate(**base)


# ---- comportamenti CORRETTI (devono restare verdi) ----

def test_confab_without_proof_is_downgraded():
    assert _gate(proposition=CONFAB).action == "downgrade"


def test_gate_honors_well_formed_evidence():
    assert _gate(proposition="SHIPPED il fix",
                 verified_by=["commit:abc1234", "pytest:test_x_PASS"]).action == "persist"


def test_gate_honors_git_sha_evidence():
    # Falsifica l'assunzione del piano ("il gate non accetta git:SHA"): LO ACCETTA.
    assert _gate(proposition="FIXED il bug",
                 verified_by=["git:abc1234"]).action == "persist"


def test_neutral_fact_persists():
    assert _gate(proposition="Il branch si chiama loop253").action == "persist"


# ---- failure-mode da CHIUDERE in FASE 4 (xfail = problema noto + prova) ----

def test_spoofed_trusted_hook_must_not_bypass():
    # FIX 2026-06-02 (sorelle loop): chiuso. Il bypass e' ora token-gated
    # (verify_trusted_writer). Il client MCP non passa hook_token → il _gate
    # helper non lo passa → fail-closed → lo spoof NON bypassa piu i detector.
    spoof = _gate(proposition=CONFAB, writer_role="trusted_hook", meta_narrative=True)
    assert spoof.action != "persist", "lo spoof dal client non deve bypassare i detector"


def test_evidence_must_cover_all_claims():
    # comportamento CORRETTO da preservare: CONFAB ha piu claim ("SHIPPED" + "tutti i
    # test passano"); una sola commit: ref non li copre -> downgrade.
    assert _gate(proposition=CONFAB, verified_by=["commit:0000000"]).action == "downgrade"


def _repo_root():
    # tests/ vive sotto la repo root.
    return Path(__file__).resolve().parents[1]


def test_wellformed_but_fabricated_evidence_must_not_pass():
    # FIX 2026-06-02 (buco #2): chiuso. Con repo_root fornito, il gate verifica
    # l'ESISTENZA dei ref (non solo il formato). Un commit:deadbeef ben formato
    # ma INVENTATO non esiste -> non sopprime piu il detector SHIPPED -> downgrade.
    r = _gate(proposition="SHIPPED il modulo di auth",
              verified_by=["commit:deadbeef", "pytest:test_auth_PASS"],
              repo_root=_repo_root())
    assert r.action != "persist", (
        "evidenza ben formata ma inventata non deve bastare: il gate ne verifica l'esistenza")


def test_real_commit_evidence_still_persists():
    # Controllo positivo: la verifica e' di ESISTENZA, non un "rifiuta tutto se
    # repo_root settato". Un commit REALE (HEAD) sopprime correttamente il detector.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(_repo_root()),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    r = _gate(proposition="SHIPPED il modulo di auth",
              verified_by=[f"commit:{head}"],
              repo_root=_repo_root())
    assert r.action == "persist", (
        f"un commit reale ({head[:12]}) deve restare evidenza valida -> persist")


def test_fabricated_evidence_persists_without_repo_root():
    # Default invariato (hermetic): senza repo_root il gate resta format-only.
    # Documenta che l'enforcement esistenza e' opt-in (i test honoring-evidence
    # sopra non passano repo_root e restano verdi).
    r = _gate(proposition="SHIPPED il modulo di auth",
              verified_by=["commit:deadbeef", "pytest:test_auth_PASS"])
    assert r.action == "persist"
