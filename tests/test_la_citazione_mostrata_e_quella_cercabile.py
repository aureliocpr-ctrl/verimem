"""La citazione che l'utente VEDE non era quella che il corpus PORTA.

`chunk_citation()` (document_promote.py:27) produce la citazione canonica —
``file:<source_id>:<start>-<end>`` — ed e' quella che la promozione mette in
`verified_by` e in `source_episodes`. `verimem search-docs` la ricostruiva a
mano in un formato diverso:

    cli.py:515   cite = f"{h['source_id']} v{h['version']} [{h['start']}:{h['end']}]"

cioe' `listino.md v1 [0:80]` sullo schermo e `file:listino.md:0-80` nel
corpus. `chunk_citation` non compariva in `cli.py` (0 occorrenze).

Chi legge un risultato e vuole sapere se quel chunk e' gia' stato promosso —
o vuole ritrovare il fatto che lo cita — cerca la stringa che ha davanti e non
trova niente. La citazione esatta e' il punto dell'intero tier documenti
(«memoria documentale che non allucina e cita sempre»): due formati per la
stessa citazione la rendono inutilizzabile proprio nel gesto per cui esiste.

E' la stessa classe di `_fact_view` ricopiata da `search` e di
`n_quarantined` divergente da sei superfici: una copia invece della superficie
unica. Terza occorrenza in due giorni.

La versione NON si perde: resta stampata accanto, perche' il tier versiona i
documenti e la citazione canonica non porta quel numero.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from verimem import cli as cli_mod
from verimem.document_promote import chunk_citation


@pytest.fixture()
def indice_con_un_documento(tmp_path, monkeypatch):
    from verimem.document_index import DocumentIndex

    idx = DocumentIndex(tmp_path / "docs.db")
    idx.index_document(
        "listino.md",
        "Il piano annuale del prodotto costa 100 euro e include il supporto "
        "via email. Il piano mensile costa dodici euro.")
    import verimem.document_index as mod
    reale = mod.DocumentIndex
    monkeypatch.setattr(
        mod, "DocumentIndex",
        lambda *a, **k: reale(tmp_path / "docs.db") if not a and not k
        else reale(*a, **k))
    return idx


def _cerca(query: str = "quanto costa il piano annuale") -> str:
    return CliRunner().invoke(cli_mod.app, ["search-docs", query]).output


def test_la_citazione_stampata_e_quella_canonica(indice_con_un_documento):
    """Il criterio: cio' che l'utente vede dev'essere cio' che puo' cercare."""
    out = _cerca()
    assert "file:listino.md:" in out, (
        f"la citazione stampata non e' quella che il corpus porta:\n{out}")


def test_e_la_stessa_stringa_che_la_promozione_mette_in_verified_by(
        indice_con_un_documento):
    """Non «un formato simile»: la stessa funzione, quindi la stessa stringa.
    Se un giorno `chunk_citation` cambia, questo test lo segue da solo."""
    out = _cerca()
    attesa = chunk_citation({"source_id": "listino.md", "start": 0, "end": 0})
    prefisso = attesa.rsplit(":", 1)[0]        # file:listino.md
    assert prefisso in out, f"atteso il prefisso {prefisso!r}:\n{out}"


def test_la_versione_non_si_perde(indice_con_un_documento):
    """La citazione canonica non porta il numero di versione, e il tier
    versiona i documenti apposta: resta stampato accanto."""
    out = _cerca()
    assert "v1" in out, f"la versione e' sparita dalla riga:\n{out}"


def test_anche_una_query_fuori_tema_cita_in_modo_canonico(
        indice_con_un_documento):
    """Scritto prima come «una query fuori tema non stampa citazioni», ed era
    il TEST a sbagliare: `search-docs` e' una ricerca semantica top-k e non si
    astiene mai — su un indice con un documento solo, qualunque domanda
    riporta quel documento. Il test ora dice cio' che il prodotto fa, e il
    contratto che verifica resta lo stesso: qualunque riga stampi, la
    citazione e' quella canonica.

    (Che la ricerca sui documenti non abbia una soglia di rilevanza e' un
    fatto osservato qui e non misurato: non lo trasformo in un requisito di
    nascosto.)
    """
    out = _cerca("un argomento che nel documento non c'e' affatto xyzzy")
    if "no results" in out.lower():
        return
    assert "file:listino.md:" in out, out
