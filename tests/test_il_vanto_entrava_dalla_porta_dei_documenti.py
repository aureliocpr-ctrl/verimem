"""«Ho verificato che funziona» è cestinato da una porta e servito dall'altra.

IL DIFETTO, isolato da ws4 e riprodotto sul percorso reale::

                                                    add()        promote(claim=…)
    «Ho verificato che la funzione ora funziona»   quarantined   model_claim g=99.9572
    «Il modulo è stato testato ed è pronto…»       quarantined   model_claim g=99.9825
    «Il bug è stato risolto e il sistema è stabile» quarantined  model_claim g=99.9840

    quarantinati da add(): 3/3   ·   SERVIBILI via promozione: 3/3

E il punteggio non è un caso: è il più alto del corpus, **perché il moat ha
ragione**. La frase sta letteralmente dentro il documento, quindi la fonte la
implica davvero. 🔑 La distinzione che manca non è fra punteggi — è fra **«il
documento RIPORTA X»** e **«X è vero»**. Per un dato oggettivo («il magazzino
contiene 300 pallet») le due coincidono; per un'auto-attestazione no: il moat
conferma la citazione, non il fatto.

⚠️ COSA NON VA TOCCATO, ed è il motivo per cui la cura guarda il LAYER e non il
punteggio. `document_promote:86-97` documenta una scelta deliberata e misurata::

    «QUARANTINA QUANDO IL MOAT BOCCIA, non quando l'azione è `downgrade`. La
     prima versione guardava `action in ("reject","downgrade")` ed era
     SBAGLIATA: `downgrade` copre due situazioni diverse […] la differenza sta
     nel PUNTEGGIO, non nell'azione.»

Il caso che quella riga protegge è una frase **implicata dalla fonte** a cui
decade solo lo *status* (`downgrade` con `grounding 98.78`): quarantinarla
nasconderebbe un fatto buono per un difetto di provenienza. Giusto — e questa
cura non lo tocca, perché non guarda l'azione: guarda **da quale layer** viene
il downgrade.

    downgrade da L4 / provenienza  ->  il contenuto è implicato, decade lo status
    downgrade da L1.x              ->  è un'AUTO-ATTESTAZIONE senza prova, e il
                                       moat ne conferma solo la citazione

Sul percorso di promozione L1 **spara e viene ignorato**: `L1.10` (works),
`L1.11` (production-ready), `L1.15` (tested) sono nei warning del verdetto, e la
riga di decisione legge solo `grounding_score`.

📌 IL CASO TAUTOLOGICO ERA GIÀ CURATO (`:111-124`, senza `claim` il moat verifica
«X implica X» e il punteggio esce `None`). Questo è il caso **con `claim`
esplicito**, che quel commento sfiora — *«lo stesso testo che `facts add`
quarantina entrava da qui come model_claim con 99.97»* — senza chiuderlo.

⚠️ E IL PERCORSO È RAGGIUNGIBILE: ws4 ha verificato che `index_file` vuole un
path, quindi serve anche uno strumento di scrittura file — cioè un ambiente
agentico qualsiasi. Un agente che scrive «ho verificato che funziona» in un file,
lo indicizza e lo promuove, si auto-certifica aggirando il gate che esiste
apposta per fermarlo.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.document_promote import promote_chunk_to_fact

VANTI = [
    "Ho verificato che la funzione ora funziona correttamente.",
    "Il modulo e' stato testato ed e' pronto per la produzione.",
    "Il bug e' stato risolto e il sistema e' stabile.",
]
#: I DATI OGGETTIVI, la popolazione opposta: un documento che riporta un fatto
#: su cose del mondo deve continuare a promuoversi. Se cadessero, avrei chiuso
#: la RAG documentale invece del buco.
OGGETTIVI = [
    "Il magazzino di Prato contiene 300 pallet.",
    "La consegna e' stata effettuata il 12 marzo 2026.",
    "Il contratto con Ferrero vale 4500 euro.",
]
DOC = ("Relazione interna del team di sviluppo. " + " ".join(VANTI) + " " +
       " ".join(OGGETTIVI) + " Il rilascio e' previsto la settimana prossima.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.fixture()
def hit():
    return {"source_id": "relazione.md", "start": 0, "end": len(DOC),
            "text": DOC}


def _stato(mem, esito):
    fid = esito.get("fact_id")
    if not fid:
        return "NON STORED"
    f = mem.semantic.get(fid)
    return getattr(f, "status", None) if f is not None else "MANCANTE"


@pytest.mark.parametrize("vanto", VANTI)
def test_un_vanto_non_diventa_servibile_passando_da_un_documento(mem, hit, vanto):
    """IL CUORE: la stessa frase che `add()` cestina non può tornare dal recall
    solo perché è stata scritta in un file prima di essere promossa."""
    esito = promote_chunk_to_fact(mem.semantic, hit, claim=vanto, topic="az/v")
    assert _stato(mem, esito) != "model_claim", (
        f"vanto servibile via promozione: {vanto}")


@pytest.mark.parametrize("vanto", VANTI)
def test_e_le_DUE_PORTE_concordano(mem, hit, vanto):
    """La promessa del prodotto è che il gate sia lo stesso ovunque. Questo test
    non fissa uno stato: fissa che i due percorsi **non divergano**, che è la
    cosa che ws4 ha misurato e che vale più di quale etichetta scegliamo."""
    via_add = mem.add(vanto, topic="az/w", source=DOC).get("status")
    via_doc = _stato(mem, promote_chunk_to_fact(mem.semantic, hit, claim=vanto,
                                                topic="az/x"))
    servibile = {"model_claim", "verified"}
    assert (via_add in servibile) == (via_doc in servibile), (
        f"le due porte divergono su «{vanto}»: add={via_add} doc={via_doc}")


@pytest.mark.parametrize("fatto", OGGETTIVI)
def test_CONTROLLO_POSITIVO_un_dato_OGGETTIVO_si_promuove_ancora(mem, hit, fatto):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA. La RAG documentale esiste per
    portare nel corpus ciò che i documenti dicono del mondo. Se questo cade, ho
    spento la funzione invece di chiudere il buco — e il difetto che curo è
    proprio l'incapacità di distinguere queste due popolazioni."""
    esito = promote_chunk_to_fact(mem.semantic, hit, claim=fatto, topic="az/o")
    assert _stato(mem, esito) == "model_claim", (
        f"dato oggettivo non piu' promosso: {fatto} ({esito.get('error')})")


def test_CONTROLLO_POSITIVO_il_chunk_grezzo_continua_a_passare(mem, hit):
    """L'altro presidio: senza `claim` il moat verifica «X implica X» e il caso
    è già curato a monte (punteggio `None`, mai giudicato). La cura non deve
    cambiare quel percorso — è il modo normale di usare la promozione."""
    esito = promote_chunk_to_fact(mem.semantic, hit, topic="az/g")
    assert esito.get("stored") is True, esito.get("error")


def test_la_ricevuta_DICE_perche_e_stato_trattenuto(mem, hit):
    """Chi promuove deve sapere che è stato L1 e non il moat: il punteggio dirà
    99.9 e senza il layer la ricevuta sembrerebbe contraddirsi da sola."""
    esito = promote_chunk_to_fact(mem.semantic, hit, claim=VANTI[0],
                                  topic="az/r")
    testo = " ".join(str(v) for v in esito.values())
    assert "L1" in testo, esito
