"""`decomponi()` does not change how a word is written: the receipt quotes the claim as the user wrote it.

The write gate judges a memory claim by claim, and the `L4-claim` warning names the claim that fell. Two
places in the splitter changed the case of a word. The subject inheritance lowercased the first letter of
the piece, which is right for «Visited» after «Mara» and wrong for a word in capitals: «The build FAILED
and STOPPED the deploy» gave «The build sTOPPED the deploy». And the closing capital turned an identifier
at the start of a claim into another one: «test_alpha PASSED» gave «Test_alpha PASSED».

Logs write status words in capitals (PASSED, FAILED, STOPPED), and agents write memories from logs: a
receipt that quotes «sTOPPED» or «Test_alpha» quotes words the source and the user never wrote.

Declared, not cured here: in «Il test_alpha e PASSED e il test_beta e PASSED.» the letter «e» stands for
the verb, and the splitter cuts on it. Reading «e» as a copula is a road already falsified; this file only
guarantees that no word comes out written differently.

No model: the cell at the write port injects the judge's score. Run from the root of the checkout:

    python -m pytest tests/test_decomponi_non_cambia_le_maiuscole.py -q -p no:randomly
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate as g
from verimem import grounding_gate as gg
from verimem.atomic_claims import decomponi


@pytest.mark.parametrize("testo, atteso", [
    ("The build FAILED and STOPPED the deploy.", ["The build FAILED.", "The build STOPPED the deploy."]),
    ("test_alpha PASSED and test_beta PASSED.", ["test_alpha PASSED.", "test_beta PASSED."]),
])
def test_le_parole_in_maiuscolo_e_gli_identificatori_restano_come_sono(testo: str, atteso: list[str]) -> None:
    assert decomponi(testo) == atteso


def test_nessuna_parola_esce_scritta_diversamente_anche_quando_la_spezzatura_sbaglia() -> None:
    unita = decomponi("Il test_alpha e PASSED e il test_beta e PASSED.")
    scritte = {w.strip(".,;:") for u in unita for w in u.split()}
    assert "pASSED" not in scritte and scritte <= {"Il", "il", "test_alpha", "test_beta", "e", "PASSED"}, unita


@pytest.mark.parametrize("testo, atteso", [
    # the two changes that stay: a Title-case verb after an inherited subject, a plain word at the start
    ("Mara went home and Visited her aunt.", ["Mara went home.", "Mara visited her aunt."]),
    ("mara went home and visited her aunt.", ["Mara went home.", "Mara visited her aunt."]),
])
def test_le_due_correzioni_giuste_restano(testo: str, atteso: list[str]) -> None:
    assert decomponi(testo) == atteso


def test_alla_porta_il_giudice_e_la_ricevuta_vedono_il_claim_come_scritto(monkeypatch) -> None:
    debole = "The build STOPPED the deploy."
    visti: list[str] = []

    def giudice(_llm, _fonte, testo, **_k):
        visti.append(testo)
        return (12.0 if testo == debole else 96.0), "local"

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", giudice)
    gate = g.run_validation_gate(proposition="The build FAILED and STOPPED the deploy.",
                                 verified_by=["source-doc:x:1"], topic="t", agent=None, validate="fast",
                                 source="ci log: build FAILED at step 3")
    assert debole in visti, visti
    assert gate.action != "persist", (gate.action, visti)
    claim = [w for w in gate.warnings if w.get("layer") == "L4-claim"]
    assert claim and debole in claim[0]["reason"], (visti, [w.get("layer") for w in gate.warnings])
