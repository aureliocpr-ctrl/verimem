"""`L1.13` non deve fermare un claim che RICALCA la fonte — EN e IT.

Reperto di ws7 (2026-08-28): su un verbale d'ufficio italiano il gate fermava
fatti VERI con la fonte al 99,9 perche' contenevano «fatta», «chiusa»,
«concluso». La causa non era la lista di parole: era che
`detect_unsupported_completion_claim` riceveva solo `proposition` e
`verified_by` e **non poteva sapere che il participio era nella fonte**.

I due criteri, e stanno insieme perche' da soli non dicono niente:
  - un claim il cui participio compare NELLA FONTE non e' una self-claim;
  - una self-claim SENZA fonte, o con una fonte che non la sostiene, resta
    fermata. Spegnere il layer non e' una cura.

Misurato prima della cura: 6 dei 7 casi di ws7 fermati, 6 self-claim su 6
fermati. Dopo: 0 su 7 e 6 su 6.
"""

from __future__ import annotations

import pytest

from verimem.l1_completion_detector import detect_unsupported_completion_claim

# ── il verbale italiano di ws7, e le sue frasi ───────────────────────────────
FONTE_IT = (
    "Verbale del cantiere. La consegna e' stata fatta il 28 marzo presso il "
    "magazzino centrale. La pratica e' stata chiusa il 28 marzo dall'ufficio "
    "protocollo. Il collaudo si e' concluso il 28 marzo alla presenza del "
    "direttore dei lavori. Il collaudo e' stato completato il 28 marzo."
)
RICALCHI_IT = [
    "La consegna e' stata fatta il 28 marzo.",
    "La pratica e' stata chiusa il 28 marzo.",
    "Il collaudo si e' concluso il 28 marzo.",
    "Il collaudo e' stato completato il 28 marzo.",
]

FONTE_EN = (
    "Site log. The delivery was completed on 28 March at the central "
    "warehouse. The case was closed on 28 March by the records office. "
    "Acceptance testing is done and the work is finished."
)
RICALCHI_EN = [
    "The delivery was completed on 28 March.",
    "The case was closed on 28 March.",
    "Acceptance testing is done.",
    "The work is finished.",
]

# ── le self-claim: devono restare fermate ────────────────────────────────────
SELFCLAIM_SENZA_FONTE = [
    "La migrazione e' completata e tutti i test passano.",
    "The migration is complete and all tests pass.",
    "Il lavoro e' stato completato.",
    "The task is done.",
]
FONTE_CHE_NON_SOSTIENE_IT = "Il cantiere ha ricevuto la visita dell'ispettore il 12 aprile."
FONTE_CHE_NON_SOSTIENE_EN = "The site received an inspection visit on 12 April."


@pytest.mark.parametrize("claim", RICALCHI_IT)
def test_it_il_ricalco_della_fonte_non_e_una_self_claim(claim):
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=FONTE_IT) is None


@pytest.mark.parametrize("claim", RICALCHI_EN)
def test_en_il_ricalco_della_fonte_non_e_una_self_claim(claim):
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=FONTE_EN) is None


@pytest.mark.parametrize("claim", SELFCLAIM_SENZA_FONTE)
def test_una_self_claim_senza_fonte_resta_fermata(claim):
    """Il criterio che rende la cura una cura e non uno spegnimento."""
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=None) is not None


@pytest.mark.parametrize("claim,fonte", [
    ("Il collaudo e' stato completato.", FONTE_CHE_NON_SOSTIENE_IT),
    ("The delivery is complete.", FONTE_CHE_NON_SOSTIENE_EN),
])
def test_una_fonte_che_non_porta_il_participio_non_perdona(claim, fonte):
    """La fonte c'e' ma non contiene la parola: nessun perdono."""
    assert detect_unsupported_completion_claim(
        proposition=claim, verified_by=[], source=fonte) is not None


def test_senza_source_il_comportamento_e_quello_di_prima():
    """Il default `source=None` non cambia nessun chiamante esistente."""
    assert detect_unsupported_completion_claim(
        proposition="La consegna e' stata fatta il 28 marzo.",
        verified_by=[]) is not None


def test_il_confronto_ignora_le_maiuscole():
    """Una fonte che apre la frase con la maiuscola perdona lo stesso."""
    assert detect_unsupported_completion_claim(
        proposition="il lavoro e' stato completato",
        verified_by=[],
        source="Completato il 28 marzo, come da verbale.") is None
