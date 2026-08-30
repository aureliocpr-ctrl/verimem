"""La descrizione parlava di percorsi e taceva l'unico vincolo che li rifiuta.

MISURATO ALLA PORTA il 2026-08-31 alle 01:44. La descrizione di
`hippo_document_index_file` dedica una frase intera ai percorsi — *«The path is
stored AS GIVEN and never resolved, so pass an absolute one if you want the
citation to keep re-opening the source»* — e non dice che un percorso assoluto
puo' essere RIFIUTATO. Passandone uno legittimo fuori dal repo::

    error: "path is outside the allowed document roots (…HippoAgent);
            set ENGRAM_DOC_ROOTS to widen it deliberately"

⇒ La guardia e' GIUSTA ed e' presidiata
(`tests/security/test_document_index_path_guard.py`); il messaggio d'errore e'
ottimo: nomina la variabile e dice «deliberately». **Il difetto e' che la
descrizione non prepara** — e proprio nella frase che parla di percorsi. Un
chiamante che la legge conclude che l'unica scelta sia relativo vs assoluto.

🪞 IL BANCO L'HA SCOPERTO LEGGENDO UN RIFIUTO, non la documentazione: il
controllo «il documento e' davvero indicizzato» e' caduto, e la ragione della
caduta era il reperto.

✅ E NELLA STESSA ESECUZIONE, l'altra affermazione REGGE: *«Isolated store —
NOT the accepted recall corpus»*. Indicizzato un file il cui unico termine
distintivo era «Portogruaro», la ricerca sui documenti restituisce il chunk e
le porte dei fatti lo restituiscono ZERO volte.

⚠️ E QUEL VERDETTO E' STATO SBAGLIATO PRIMA DI ESSERE GIUSTO. La prima stesura
concludeva «il confine perde» perche' contava QUANTE righe tornassero dalla
porta dei fatti: ne tornava una, ed era il fatto di CONTROLLO — restituito
perche' quella porta **non si astiene mai** (misurato alle 23:51 e scritto
nella guida: e' il vicino piu' prossimo, non una risposta). 🔑 Contare le righe
non misura la contaminazione: la misura e' se il TESTO del documento compaia
fra i fatti. A salvarmi e' stato **stampare i testi**, non un controllo
automatico — e la conclusione sbagliata avrebbe accusato il prodotto di servire
come fatto un testo che nessun moat ha giudicato.

Banco: ``docs/stato-reale/banchi/ws3-lo-store-dei-documenti-e-davvero-isolato.py``
"""

from __future__ import annotations

import asyncio

import pytest

from verimem import mcp_server


@pytest.fixture(scope="module")
def descrizione() -> str:
    for t in asyncio.run(mcp_server.list_tools()):
        if t.name == "hippo_document_index_file":
            return str(t.description or "")
    pytest.fail("hippo_document_index_file non e' fra gli strumenti listati")


def test_la_descrizione_dice_che_un_percorso_puo_essere_rifiutato(descrizione):
    """IL CUORE: la frase sui percorsi non nominava il vincolo."""
    assert "ENGRAM_DOC_ROOTS" in descrizione, descrizione[-400:]


def test_dice_anche_che_il_rifiuto_e_esplicito(descrizione):
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: sapere che un percorso puo' essere
    rifiutato, senza sapere che il rifiuto si VEDE, fa temere lo scenario
    peggiore — un file saltato in silenzio dentro un indice che sembra
    completo. Il prodotto non lo fa, e la descrizione deve dirlo."""
    assert "never a silent skip" in descrizione, descrizione[-400:]


def test_l_isolamento_resta_dichiarato_col_suo_numero(descrizione):
    """⚠️ LA POPOLAZIONE OPPOSTA della cura: aggiungere il vincolo non doveva
    indebolire l'affermazione che REGGE. L'isolamento e' misurato, e la misura
    sta nella stessa frase."""
    assert "NOT the accepted recall corpus" in descrizione, descrizione[-400:]
    assert "ZERO times" in descrizione, descrizione[-400:]
