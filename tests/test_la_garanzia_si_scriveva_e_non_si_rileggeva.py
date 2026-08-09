"""`label()` scriveva la garanzia e nessuna superficie SDK la rileggeva.

Trovato dogfoodando le garanzie epistemiche — il tier che dice CHE TIPO di
prova sostiene un fatto::

    m.label(fid, 'proven', proof='listino firmato 2026-01-15')  ->  True

e nel DB c'è davvero::

    epistemic = {"kind": "proven", "proof": "listino firmato 2026-01-15"}

ma poi::

    search(...)          -> nessun campo di garanzia
    get(fid).epistemic   -> None
    explain(...)         -> nessuna chiave di garanzia

Il dato è persistito e nessuno lo serve. È la forma già vista in questo repo —
«`skills_used` impara a vuoto», «il campo `moat` non usciva» — applicata al
tier che dovrebbe dire perché un fatto merita fiducia.

I DUE CONTRATTI DI USCITA DIVERGONO, in entrambe le direzioni. Sullo stesso
fatto::

    MCP  fact_payload -> confidence confidence_tier created_at EPISTEMIC
                         grounding_score id meta_narrative proposition status
                         topic verified_by writer_principal
    SDK  _fact_view   -> asserted_at created_at grounding_score id source
                         status superseded_by text topic verified_by

Solo MCP: `confidence`, `confidence_tier`, `epistemic`, `meta_narrative`,
`writer_principal`. Solo SDK: `asserted_at`, `source`, `superseded_by`.

E il docstring di `_fact_view` promette «the SAME provenance surface
everywhere» — la stessa frase che il 2026-08-02 aveva fatto trovare
`superseded_by` mancante. La promessa non era ancora vera: mancavano cinque
campi dall'altra parte.

LA CURA È ADDITIVA, di proposito. `_fact_view` non viene sostituito da
`fact_payload`: i due hanno chiavi con nomi diversi per la stessa cosa (`text`
contro `proposition`) e cambiarli romperebbe ogni chiamante dell'SDK. Si
aggiunge ciò che manca, senza togliere niente.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

#: I campi che MCP serve e l'SDK non serviva. `epistemic` è quello che ha
#: fatto trovare il difetto; gli altri sono emersi dal confronto.
SOLO_MCP = ["epistemic", "confidence", "confidence_tier", "writer_principal"]


@pytest.fixture()
def fatto_con_garanzia():
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    r = m.add("Il piano annuale costa 100 euro.", topic="listino",
              source="Listino 2026: il piano annuale costa 100 euro.")
    assert m.label(r["id"], "proven", proof="listino firmato 2026-01-15")
    return m, r["id"]


def test_la_garanzia_esce_dal_recall(fatto_con_garanzia):
    m, _fid = fatto_con_garanzia
    hits = m.search("quanto costa il piano annuale", k=1)
    assert hits, "il fatto non si rilegge nemmeno"
    epi = hits[0].get("epistemic")
    assert epi, (
        "la garanzia è scritta nel DB e il recall non la porta: chi legge non "
        "sa che tipo di prova sostiene il fatto")
    assert epi.get("kind") == "proven", epi


def test_e_anche_da_get(fatto_con_garanzia):
    m, fid = fatto_con_garanzia
    f = m.get(fid)
    epi = getattr(f, "epistemic", None) if not isinstance(f, dict) \
        else f.get("epistemic")
    assert epi, "`get` non espone la garanzia del fatto che restituisce"


@pytest.mark.parametrize("campo", SOLO_MCP)
def test_i_due_contratti_non_divergono(fatto_con_garanzia, campo):
    """`_fact_view` promette «the SAME provenance surface everywhere»: quello
    che il canale MCP serve, l'SDK lo serve."""
    m, fid = fatto_con_garanzia
    from verimem.fact_contract import fact_payload

    f = m.semantic.get(fid)
    mcp = fact_payload(f)
    sdk = Memory._fact_view(f)
    if campo not in mcp:
        pytest.skip(f"«{campo}» non esce nemmeno da MCP su questo fatto")
    assert campo in sdk, (
        f"«{campo}» esce dal canale MCP e non dall'SDK: due contratti di "
        f"uscita per lo stesso fatto sono due verità che divergono")


def test_quello_che_l_SDK_aveva_in_piu_resta(fatto_con_garanzia):
    """La cura è ADDITIVA: `asserted_at`, `source` e `superseded_by` non
    spariscono perché sono arrivati campi nuovi."""
    m, fid = fatto_con_garanzia
    sdk = Memory._fact_view(m.semantic.get(fid))
    for campo in ("asserted_at", "source", "superseded_by", "text"):
        assert campo in sdk, campo


def test_un_fatto_SENZA_garanzia_non_inventa_nulla(fatto_con_garanzia):
    """`None` quando non c'è: una chiave assente non distingue «nessuna
    garanzia» da «questa vista non lo dice»."""
    m, _ = fatto_con_garanzia
    r = m.add("La prova gratuita dura 14 giorni.", topic="listino")
    sdk = Memory._fact_view(m.semantic.get(r["id"]))
    assert "epistemic" in sdk and sdk["epistemic"] is None
