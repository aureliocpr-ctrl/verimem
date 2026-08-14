"""La porzione di fonte citata sopravvive al giro disco → oggetto → vista.

``grounding_span`` è la parte di fonte che sostiene il fatto: è ciò che rende
una provenienza *verificabile* invece che solo dichiarata. Il write-path la
persiste dalla v17; la ricostruzione di ``Fact`` non la rileggeva, quindi ogni
lettura la perdeva e le viste potevano servire solo ``None``.

È la terza volta che un campo nuovo non arriva fino all'oggetto — ``writer_role``
e ``writer_principal`` prima di questo — e i commenti nel modulo lo raccontano
già due volte. Questo collaudo misura il **valore** lungo tutti e tre i livelli,
non la presenza della chiave: un controllo che guarda la struttura invece del
contenuto dà sempre il verdetto più ottimista.

Non passa dal giudice: caricare il modello costerebbe mezzo minuto e misurerebbe
il gate, non il roundtrip. E non scrive nel database a mano — il campo si valorizza
sull'oggetto, che è la via che il prodotto stesso usa.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory

SORGENTE = "La sigla di collaudo RTRP-1 vale per il giro di andata e ritorno."
FATTO = "La sigla di collaudo RTRP-1 vale per il giro."


@pytest.fixture()
def store(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "semantic.db")


#: ``SemanticMemory.store`` restituisce ``None``, non l'id: l'identificativo è
#: quello che si passa. Sceglierlo qui rende il collaudo indipendente da come il
#: prodotto lo genererebbe.
ID_CON = "rtrp0000con1"
ID_SENZA = "rtrp0000senz"


def _fatto_con_porzione() -> Fact:
    return Fact(id=ID_CON, proposition=FATTO, topic="collaudo", confidence=0.5,
                source_signature="sha256:deadbeef", grounding_span=SORGENTE)


def _fatto_senza_porzione() -> Fact:
    return Fact(id=ID_SENZA, proposition="Un fatto senza alcuna fonte da citare.",
                topic="collaudo", confidence=0.5)


def test_il_disco_la_conserva(store: SemanticMemory):
    """Controllo positivo: senza questo, un None a valle non significherebbe nulla."""
    store.store(_fatto_con_porzione())
    with store._connect() as conn:  # noqa: SLF001 — lettura di collaudo
        riga = conn.execute(
            "SELECT grounding_span FROM facts WHERE id = ?", (ID_CON,)).fetchone()
    assert riga[0] == SORGENTE, "il banco è rotto: il disco non ha la porzione"


def test_l_oggetto_la_riporta(store: SemanticMemory):
    """LA RIGA CHE CONTA: togli `grounding_span` dalla ricostruzione e questo cade."""
    store.store(_fatto_con_porzione())
    fatto = store.get(ID_CON)
    assert fatto is not None
    assert fatto.grounding_span == SORGENTE, (
        "la porzione citata si perde nel roundtrip: il disco la ha, l'oggetto no")


def test_un_fatto_senza_porzione_resta_senza(store: SemanticMemory):
    """L'altra popolazione: il campo non deve inventare un valore."""
    store.store(_fatto_senza_porzione())
    fatto = store.get(ID_SENZA)
    assert fatto is not None
    assert fatto.grounding_span is None


def test_la_porzione_e_leggibile_anche_dopo_una_riapertura(tmp_path: Path):
    """Il giro completo: chi riapre lo store domani deve trovarla."""
    percorso = tmp_path / "semantic.db"
    SemanticMemory(db_path=percorso).store(_fatto_con_porzione())
    fatto = SemanticMemory(db_path=percorso).get(ID_CON)
    assert fatto is not None and fatto.grounding_span == SORGENTE
