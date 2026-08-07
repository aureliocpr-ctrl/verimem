"""Il gate trattiene un verbale e gli chiede una prova che i verbali non hanno.

IL DIFETTO, ed è il residuo della cura di stanotte (`3c54f580`) — l'ho lasciato
io, cablando metà del router::

    «Hanno firmato Neri e Gialli.»
        moat           = passed, g=99.93     la fonte lo dice alla lettera
        quarantined_by = L1  (layer L1.16)
        advice         = «Add at least one of: approval:<id>_signed,
                          review:<id>_approved, pr:<n>_approved, ticket:…»

Per un verbale d'assemblea quell'advice **non ha nessuna uscita**: non esiste
una pull request che approvi una firma su un registro. La strada giusta esiste
— dichiarare che il testo è contenuto ingerito e non un'asserzione dell'agente
— ed è ``gate_router.attribution_question`` a saperla dire::

    «attribution=agent_claim — reads as the agent's own assertion; if this text
     was ingested from a document or user, set writer_role='external_content'
     to route it to the document policy»

🔑 MA QUELLA FUNZIONE È CHIAMATA SOLO IN ``semantic.py`` (tre punti) E MAI NEL
GATE. Stanotte ho cablato ``l1x_applies`` — la parte che *decide* — e non
``attribution_question``, la parte che *lo spiega a chi scrive*. Il router
esporta tre funzioni e il gate ne usava una: è la classe ② un'altra volta, e
stavolta dentro la mia stessa cura, il che è il motivo per cui questo file
esiste invece di una nota.

⚠️ QUANDO DIRLO, E PERCHÉ NON SEMPRE. Attaccare il suggerimento a ogni warning
L1 sarebbe rumore: su «ho fixato il bug» la provenienza non c'entra, e un advice
che compare ovunque non si legge più. Il segnale che isola il caso vero è la
**contraddizione interna del gate**: L1 trattiene *mentre il moat ha approvato
la fonte*. Lì il gate sta dicendo due cose incompatibili — «la fonte sostiene
questo» e «tu non hai la prova formale» — e la seconda è quella sbagliata,
perché il testo non è dell'agente.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

VERBALE = ("Verbale dell'assemblea del 12 marzo. Erano presenti i fornitori "
           "Bianchi e Rossi. Hanno firmato il registro Neri e Gialli. La "
           "pratica e' stata approvata dal consiglio.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def test_quando_L1_trattiene_e_il_moat_APPROVA_il_gate_indica_la_strada(mem):
    """IL CUORE. Il gate conosce l'uscita da quando esiste il router (10/07) e
    non la diceva a chi ne aveva bisogno."""
    r = mem.add("Hanno firmato il registro Neri e Gialli.", topic="az/v",
                source=VERBALE)
    testo = " ".join(f"{w.get('reason','')} {w.get('advice','')}"
                     for w in (r.get("warnings") or []))
    assert "writer_role" in testo and "external_content" in testo, (
        f"il gate trattiene senza indicare la strada che conosce: "
        f"{r.get('warnings')}")


def test_e_lo_dice_a_chi_LEGGE_la_ricevuta_non_solo_nei_warning(mem):
    """L'advice di primo livello è quello che un chiamante stampa: se la strada
    resta sepolta in un warning fra gli altri, chi integra non la vede."""
    r = mem.add("Hanno firmato il registro Neri e Gialli.", topic="az/w",
                source=VERBALE)
    assert "external_content" in str(r.get("advice") or ""), r.get("advice")


def test_CONTROLLO_POSITIVO_un_claim_SENZA_fonte_non_riceve_il_suggerimento(mem):
    """⚠️ IL PRESIDIO CONTRO IL RUMORE. Senza source il moat non gira, non c'è
    nessuna contraddizione interna, e «dichiara la provenienza» sarebbe un
    consiglio attaccato a ogni claim di sviluppo del corpus."""
    r = mem.add("Ho fixato il bug del parser.", topic="az/x")
    testo = " ".join(f"{w.get('advice','')}" for w in (r.get("warnings") or []))
    assert "external_content" not in testo + str(r.get("advice") or ""), (
        r.get("warnings"))


def test_CONTROLLO_POSITIVO_se_il_moat_BOCCIA_non_si_suggerisce_niente(mem):
    """L'altro lato: se la fonte NON sostiene il claim, non c'è nessuna
    contraddizione da sciogliere — c'è un claim non sostenuto, e suggerire di
    dichiararlo «contenuto esterno» sarebbe indicare la porta di servizio."""
    r = mem.add("Hanno firmato il registro Verdi e Neri.", topic="az/y",
                source="Verbale: erano presenti Bianchi e Rossi.")
    testo = " ".join(f"{w.get('advice','')}" for w in (r.get("warnings") or []))
    assert "external_content" not in testo + str(r.get("advice") or ""), (
        r.get("warnings"))


def test_un_claim_gia_dichiarato_esterno_non_riceve_il_suggerimento(mem):
    """Chi ha già dichiarato la provenienza non deve sentirsi dire di farlo:
    lì L1 non scatta nemmeno più (cura `3c54f580`), e un residuo di advice
    sarebbe la prova che il suggerimento non guarda lo stato reale."""
    r = mem.add("Hanno firmato il registro Neri e Gialli.", topic="az/z",
                source=VERBALE, writer_role="external_content")
    testo = " ".join(f"{w.get('advice','')}" for w in (r.get("warnings") or []))
    assert "external_content" not in testo, r.get("warnings")
