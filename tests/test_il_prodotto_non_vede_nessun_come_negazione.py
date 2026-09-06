"""Cella RED del muro delle negazioni: «Nessun X …» non e' una negazione per il gate.

Misurato il 06/09 alle 06:21 sui fatti VERI quarantinati stanotte (banco
docs/stato-reale/banchi/ws3-muro-negazioni-la-fonte-enuncia-l-assenza-e-il-giudice-non-la-legge.py):
`negation_scope.e_un_claim_negativo` risponde False a «Nessun chiamante passa
freshness_fn.», a «Nessun file di verimem fuori da epistemic_health.py nomina
freshness_fn.» (il quarantinato 436851d26dff, grounding 31,9) e a «Nel registro
mcp_audit.log nessun campo dice CHI.» — e True a «… non ha un campo che dice
CHI» (1f6aa2aad6b6). L'avviso L4-negazione, che esiste proprio per dire a chi
scrive «il giudice non sa verificare un'assenza», scatta quindi sulla forma con
«non» e tace sulla forma con «nessun»: stessa assenza, stesso verdetto del moat
(sotto soglia), avviso solo per una delle due.

Il test e' una cella RED dichiarata (`xfail strict`): non cura, misura. La cura
sta in `quantity_match._NEGATOR_RE`, che vive in un posto solo per undici
lingue, e si decide con chi la tiene. Accanto ci sono i controlli positivi che
DEVONO restare verdi: se la cura rompe «non», si vede qui.
"""
from __future__ import annotations

import pytest

from verimem.negation_scope import e_un_claim_negativo

RICONOSCIUTE_OGGI = [
    "Il registro mcp_audit.log non ha un campo che dice CHI.",
    "assess_fact_freshness non compare fra gli strumenti registrati.",
    "Il fornitore Verdi non era presente.",
    "No supplier named Verdi appears in the list.",
]

NESSUN_NON_VISTO = [
    "Nessun chiamante passa freshness_fn.",
    "Nessun file di verimem fuori da epistemic_health.py nomina freshness_fn.",
    "Nel registro mcp_audit.log nessun campo dice CHI.",
    "Nessuna riga del log nomina recall.",
]


@pytest.mark.parametrize("claim", RICONOSCIUTE_OGGI)
def test_controllo_positivo_il_non_e_riconosciuto(claim: str) -> None:
    assert e_un_claim_negativo(claim), claim


@pytest.mark.xfail(
    strict=True,
    reason="RED dichiarato 06/09: «nessun/nessuna» non e' in _NEGATOR_RE; "
           "436851d26dff e' caduto a 31,9 senza l'avviso L4-negazione",
)
@pytest.mark.parametrize("claim", NESSUN_NON_VISTO)
def test_nessun_e_una_negazione_come_non(claim: str) -> None:
    assert e_un_claim_negativo(claim), claim


def test_una_affermazione_non_e_una_negazione() -> None:
    """La cura, quando arrivera', non deve trasformare ogni frase in una smentita."""
    for claim in ("Il controllo positivo su grounder stampa 1.",
                  "I campi del registro sono args_hash, caller_pid, tool, ts."):
        assert not e_un_claim_negativo(claim), claim
