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
    che il canale MCP serve, l'SDK lo serve.

    QUI C'ERA UNO SKIP, E TACEVA PROPRIO SUL DIFETTO CHE DEVE CATTURARE::

        if campo not in mcp:
            pytest.skip(f"«{campo}» non esce nemmeno da MCP su questo fatto")

    L'assenza da MCP veniva letta come una condizione dell'ambiente — «su
    questo fatto il campo non c'è, pazienza» — quando è invece **il difetto
    peggiore dei due**: `SOLO_MCP` è per definizione l'elenco dei campi *che il
    canale MCP serve*, quindi un campo che non esce da MCP smentisce la
    premessa dell'intero caso. Il presidio non si limitava a mancarlo: si
    **spegneva**, e uno che si spegne è indistinguibile da uno che approva.

    Misurato prima di toccarlo (2026-08-15, `-rs`): **8 passed, 0 skipped** —
    tutti e quattro i campi escono da MCP. Lo skip non scattava mai. È ciò che
    rende la sostituzione sicura *e* necessaria insieme: un ramo che oggi non
    cambia alcun esito non sta facendo il lavoro che dichiara, sta solo
    aspettando il giorno in cui lo farebbe al contrario.

    ⚠️ PERIMETRO. L'assert vale per il fatto della fixture — con garanzia e con
    `source`, quindi giudicato. Su un fatto mai giudicato `confidence_tier`
    potrebbe legittimamente non esserci; se un domani questo caso dovesse
    coprire anche quello, la strada è **una seconda fixture con la sua attesa**,
    non un ramo che salta e riporta il presidio al silenzio di prima.

    📌 `tests/test_fact_ha_un_contratto_di_uscita.py` impedisce a monte che un
    campo di `SOLO_MCP` finisca in `NON_ESCONO`. I due casi non si sostituiscono:
    quello previene la contraddizione fra i due elenchi, questo verifica il
    prodotto. Se togli uno, l'altro non copre il suo verso.
    """
    m, fid = fatto_con_garanzia
    from verimem.fact_contract import fact_payload

    f = m.semantic.get(fid)
    mcp = fact_payload(f)
    sdk = Memory._fact_view(f)
    assert campo in mcp, (
        f"«{campo}» è in SOLO_MCP — l'elenco dei campi che il canale MCP serve "
        f"— e da MCP non esce. O il contratto di uscita ha smesso di servirlo, "
        f"e allora è una regressione del prodotto, o non appartiene più a "
        f"quell'elenco, e allora va tolto di lì: in nessuno dei due casi la "
        f"risposta è passare oltre in silenzio")
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
