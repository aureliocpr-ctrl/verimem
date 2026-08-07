"""La storia di un fatto arrivava senza fonte, senza verdetto, senza data, senza autore.

IL CANDIDATO B1 DI ws2, censito contro la classe «una capacità dichiarata e
spenta»: non è un campo dimenticato, è **una proiezione scritta a mano che non è
mai stata allineata al resto del read-path**::

    get / get_all / search ->  14 chiavi   [asserted_at, confidence,
        confidence_tier, created_at, epistemic, grounding_score, id, source,
        status, superseded_by, text, topic, verified_by, writer_principal]
    history()              ->   4 chiavi   [id, status, superseded_by, text]

Su `get`/`search` la promessa «provenance on every read» **regge**. Su `history`
cadono tutte insieme: provenienza, verdetto, tempo, autore.

⚠️ E COLPISCE ESATTAMENTE CIÒ CHE HO APPENA ACCESO. Un'ora fa ho messo il
routing temporale su `"auto"` (`2aa8a4b1`) perché alle domande sul passato il
recall rispondeva col presente. Ora la storia arriva — ma **serve versioni senza
fonte, senza verdetto, senza data e senza autore**. Chi deve *scegliere fra
versioni* — l'unico motivo per cui si chiama `history` — non ha in mano niente
per farlo: due testi diversi e nessun criterio.

🔑 È LA TERZA COPIA DELLA STESSA VISTA, e la seconda era già stata trovata. Il
docstring di ``_fact_view`` promette *«the SAME provenance surface everywhere»*,
e accanto al suo uso in `search` c'è scritto cosa costò la copia precedente::

    «It used to be a hand-written copy of eight of its nine keys, and the ninth
     is how the copy was found: `superseded_by` was added to the shared view and
     `search` — the surface everyone actually calls — went on without it […]
     Two copies drift, and this one already had.»

Stessa forma, un piano più in basso: `history` è la copia che quella cura non ha
raggiunto. Per questo la cura è **una** (la proiezione), non quattro campi
aggiunti a mano — che sarebbe la quarta copia.

📌 ADDITIVO, nessun taglio: i campi stanno già nelle righe `facts` che `history`
legge. Le quattro chiavi storiche restano al loro posto, e chi le usa non si
accorge di niente.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FONTE = ("Listino interno: il prodotto A costa 100 euro, poi aggiornato a 120 "
         "euro, poi a 150 euro.")

#: Le chiavi di provenienza che `get`/`search` garantiscono e che servono a
#: scegliere fra due versioni. Non tutte e 14: queste sono quelle SENZA cui la
#: domanda «quale di queste versioni mi fido?» non ha risposta.
CHIAVI_DI_CUSTODIA = ("grounding_score", "source", "verified_by",
                      "asserted_at", "writer_principal", "topic")


@pytest.fixture()
def mem(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    for p in ("Il prodotto A costa 100 euro.",
              "Il prodotto A costa 120 euro.",
              "Il prodotto A costa 150 euro."):
        m.add(p, topic="az/listino", source=FONTE)
    return m


def _catena(mem):
    hits = mem.search("quanto costa il prodotto A", k=3)
    assert hits, "il banco non risponde"
    return mem.history(hits[0]["id"])


def test_la_storia_porta_la_CUSTODIA_di_ogni_versione(mem):
    """IL CUORE: chi deve scegliere fra versioni ha bisogno di sapere, per
    ognuna, chi l'ha scritta, da quale fonte, con che verdetto e quando."""
    catena = _catena(mem)
    assert catena, "nessuna storia: il banco non ha prodotto una catena"
    mancanti = [k for k in CHIAVI_DI_CUSTODIA if k not in catena[0]]
    assert not mancanti, (
        f"la storia serve versioni senza {mancanti} — chi sceglie fra due "
        f"testi non ha nessun criterio. Chiavi presenti: {sorted(catena[0])}")


def test_e_le_QUATTRO_CHIAVI_STORICHE_restano(mem):
    """⚠️ PRESIDIO DI COMPATIBILITÀ: la cura è additiva. Chi legge
    `id`/`text`/`status`/`superseded_by` — la forma documentata nel docstring —
    non deve accorgersi di niente."""
    catena = _catena(mem)
    for voce in catena:
        for k in ("id", "text", "status", "superseded_by"):
            assert k in voce, f"chiave storica {k} sparita: {sorted(voce)}"


def test_la_storia_e_la_STESSA_VISTA_di_search(mem):
    """🔑 IL PRESIDIO CHE IMPEDISCE LA QUARTA COPIA: le chiavi di `history`
    devono essere un SOVRAINSIEME di quelle di `search`, non un elenco scelto a
    mano che domani divergerà di nuovo. Se qualcuno aggiunge un campo alla vista
    condivisa, questo test lo pretende anche qui."""
    hits = mem.search("quanto costa il prodotto A", k=3)
    catena = mem.history(hits[0]["id"])
    assert catena
    # `score` e `confidence_tier` sono di search, non della vista condivisa.
    attese = set(hits[0]) - {"score", "confidence_tier", "history",
                             "hidden_records", "ranking"}
    mancanti = attese - set(catena[0])
    assert not mancanti, (
        f"history non allineata alla vista condivisa, mancano {sorted(mancanti)}")


def test_la_catena_resta_ordinata_e_completa(mem):
    """L'altro presidio: la cura tocca COSA si serve, non QUANTO né in che
    ordine. Tre scritture, tre voci, dalla più vecchia alla più recente."""
    catena = _catena(mem)
    assert len(catena) == 3, [v.get("text") for v in catena]
    assert catena[0]["text"].endswith("100 euro.")
    assert catena[-1]["text"].endswith("150 euro.")
    assert catena[-1]["superseded_by"] is None
