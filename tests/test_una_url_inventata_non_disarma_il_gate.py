"""Un vanto entrava servibile dichiarando una URL qualsiasi in `verified_by`.

IL BUCO, ricostruito riga per riga da ws4 e verificato end-to-end qui. È un
buco **che ho introdotto io** con `3c54f580`, la cura che ha portato il router
di provenienza ai quattordici layer L1.x::

    verified_by = None                 quarantined  L1=['L1.10','L1.15']  ok
    verified_by = ['commit:abc123']    quarantined  L1=['L1.10','L1.15']  ok
    verified_by = ['url:https://…']    **model_claim  L1=NESSUNO**       🔴
    verified_by = ['https://…']        **model_claim  L1=NESSUNO**       🔴
    verified_by = ['doc:inventato']    **model_claim  L1=NESSUNO**       🔴

La catena: ``classify_provenance`` deduce ``external_content`` da un prefisso di
``verified_by`` (``url:``, ``doc:``, ``http://``…); ``l1x_applies`` diventa
``False``; L1 perde giurisdizione. E `Memory.add` passa `provenance_trusted=True`
perché è una superficie in-process — ma **il gateway HTTP passa da lì**, e lì
`verified_by` arriva dal *body della richiesta*.

🔑 QUARTA ISTANZA DELLA STESSA CLASSE, e le prime tre sono in casa:
``narrative_l1_skip`` (27/05), ``trusted_writer.py`` sul campo ``writer_role``
(02/06), e la **prima stesura di questa stessa cura** ieri, presa dal presidio
``test_attacker_with_user_role_cannot_bypass``. Allora avevo scritto che il
privilegio non deve pendere da ``writer_role``, che arriva dalla rete, ma da
``provenance_trusted``, che solo SDK/CLI passano.

⚠️ **E non ho applicato lo stesso ragionamento a `verified_by`.** Il mio presidio
di ieri copriva un solo campo — quello che avevo in mente — mentre la funzione ne
legge due. È la classe ② («la cura c'era e mancava lo sweep») dentro la cura
contro la classe ②.

LA REGOLA CHE NE SEGUE, e vale oltre questo caso: **`writer_role` è una
DICHIARAZIONE di chi chiama, `verified_by` è un DATO.** Un dato non decide i
privilegi di chi lo porta — è lo stesso principio per cui il contenuto di un
documento non è un'istruzione. Chi ingerisce davvero un documento ha la strada
esplicita: ``writer_role='external_content'``, che è precisamente ciò che la cura
di ieri ha cablato e reso raggiungibile.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.gate_router import classify_provenance

VANTO = "Ho verificato che la funzione ora funziona correttamente."


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.mark.parametrize("verified_by", [
    ["url:https://evil.example/prova"],
    ["https://evil.example/prova"],
    ["http://evil.example/prova"],
    ["doc:inventato"],
    ["document:qualsiasi"],
    ["source-doc:mai-esistito"],
])
def test_un_riferimento_ESTERNO_nei_dati_non_disarma_L1(mem, verified_by):
    """IL CUORE: chiunque può scrivere `url:` in un campo. Se questo bastasse a
    togliere la giurisdizione a L1, il gate avrebbe una porta di servizio che si
    apre con una stringa."""
    r = mem.add(VANTO, topic="az/u", verified_by=verified_by)
    layer_l1 = [w.get("layer") for w in (r.get("warnings") or [])
                if str(w.get("layer", "")).startswith("L1")]
    assert layer_l1, (
        f"L1 disarmato da verified_by={verified_by}: un'auto-attestazione "
        f"entra come {r.get('status')}")


@pytest.mark.parametrize("verified_by", [
    None,
    ["commit:abc123"],
    ["ticket:PROJ-42"],
])
def test_CONTROLLO_POSITIVO_i_riferimenti_ORDINARI_non_cambiano(mem, verified_by):
    """La popolazione che già funzionava: un ref che àncora un claim
    dell'agente lo lascia agent_claim, e L1 continua a fare il suo mestiere.

    ⚠️ `pytest:<test>_PASS` NON sta in questa lista, e il motivo è istruttivo:
    la prima stesura ce l'aveva e il test cadeva — giustamente. Quel ref è
    **evidenza vera** per L1.15 (tested), quindi L1 tace *per il motivo giusto*.
    Metterlo qui avrebbe preteso che il gate ignorasse una prova valida: il caso
    di test era sbagliato, non il codice.
    """
    r = mem.add(VANTO, topic="az/o", verified_by=verified_by)
    layer_l1 = [w.get("layer") for w in (r.get("warnings") or [])
                if str(w.get("layer", "")).startswith("L1")]
    assert layer_l1, f"regressione su verified_by={verified_by}"


def test_chi_DICHIARA_la_provenienza_continua_a_essere_creduto(mem):
    """⚠️ IL PRESIDIO CHE PROTEGGE LA CURA DI IERI: la strada esplicita deve
    restare aperta. Chi ingerisce davvero un documento passa
    `writer_role='external_content'` — una DICHIARAZIONE di chi chiama, non un
    dato che viaggia nel payload — e per lui L1 non ha giurisdizione."""
    verbale = ("Verbale dell'assemblea: hanno firmato il registro Neri e "
               "Gialli.")
    r = mem.add("Hanno firmato il registro Neri e Gialli.", topic="az/d",
                source=verbale, writer_role="external_content")
    assert r.get("status") != "quarantined", r.get("warnings")


def test_la_REGOLA_e_nel_router_non_solo_nel_chiamante():
    """🔑 Il presidio che impedisce alla cura di essere aggirata da un'altra
    porta: la si mette dove la decisione si PRENDE. `classify_provenance` non
    deve dedurre una provenienza esterna da un dato, chiunque sia il chiamante
    — e questo test lo verifica sulla funzione, non sul percorso."""
    assert classify_provenance(None, ["url:https://x"]) == "agent_claim"
    assert classify_provenance(None, ["doc:x"]) == "agent_claim"
    # la DICHIARAZIONE esplicita continua a valere
    assert classify_provenance("external_content", None) == "external_content"
    assert classify_provenance("user", None) == "user_input"
