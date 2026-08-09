"""Due punti leggevano vettori persistiti senza chiedersi di quale modello fossero.

LO SWEEP CHE AVEVO LASCIATO A METÀ. Curando il crash del ciclo di sonno
(`f8024a7a`) ho chiuso sei consumatori dentro ``skill.py`` ed **estratto la
funzione** ``embedding.vettore_compatibile`` proprio per non scrivere la settima
copia del criterio. Poi non ho chiesto la domanda che chiude la classe: **chi
ALTRO legge vettori persistiti?**

ws1 l'ha chiesta, e ce n'erano due fuori::

    cli.py:2066  (comando `introspect`)   -> CRASHA: cosine(768,) vs (384,)
    document_index.py:423                 -> TACE: zero risultati, in silenzio

⚠️ E I DUE MODI DI ROMPERSI NON SI EQUIVALGONO. Il crash è rumoroso: chi lo
vede sa che qualcosa non va. Il silenzio no — ed è il caso che ws5 ha trovato
da un'altra strada: *«un backup del corpus non è più interrogabile dopo un
cambio di modello: gli snapshot di maggio hanno vettori a 384, il motore di
oggi ne vuole 768 → ZERO risultati, in silenzio»*. Un archivio che risponde
«non ho trovato niente» quando in realtà non può leggere è indistinguibile da
un archivio vuoto.

🔑 STESSA CLASSE, STESSA FUNZIONE: qui non nasce un criterio nuovo. Si chiama
``vettore_compatibile``, che risolve ``expected_embedding_bytes()`` LIVE — così
un cambio di modello a runtime muove tutti e otto i controlli insieme invece di
lasciarne sette congelati.

📌 SUL DOCUMENT INDEX SI DICHIARA, NON SI TACE: i chunk illeggibili si saltano
(altrimenti l'errore resta) **e il loro numero esce nel risultato**, con la
stessa forma di ``nascosti`` — «non ho trovato niente» e «non riesco a leggere
quello che ho» sono due risposte diverse, e finora erano la stessa.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from verimem import embedding
from verimem.document_index import DocumentIndex

TESTO = ("Relazione: il magazzino di Verona contiene 480 unita. Il referente "
         "commerciale e' la dott.ssa Bianchi. Il pagamento avviene a 60 giorni.")


#: ⚠️ NON 384, e il motivo è una trappola di questa casa: sotto pytest
#: l'embedder è uno STUB, e se la sua dimensione coincidesse con quella
#: «guasta» il banco misurerebbe due vettori COMPATIBILI credendo di misurarne
#: due incompatibili. La prima stesura usava 384 e passava per finta. Si sceglie
#: una dimensione che nessun modello reale produce, così l'incompatibilità è
#: garantita qualunque embedder giri.
_DIM_DI_UN_ALTRO_MODELLO = 999


def _guasta_i_vettori(db_path, dim_sbagliata: int = _DIM_DI_UN_ALTRO_MODELLO) -> int:
    """Riscrive i vettori dei chunk con la dimensione di un altro modello.

    È lo stato reale di un backup di maggio riaperto col motore di oggi, e di
    qualunque store sopravvissuto a un cambio di modello.
    """
    finto = np.zeros(dim_sbagliata, dtype=np.float32).tobytes()
    c = sqlite3.connect(str(db_path))
    try:
        n = c.execute("UPDATE chunks SET vec=?", (finto,)).rowcount
        c.commit()
        return n
    finally:
        c.close()


@pytest.fixture()
def indice_guasto(tmp_path):
    idx = DocumentIndex(str(tmp_path / "doc.db"))
    idx.index_document(source_id="relazione", content=TESTO)
    assert _guasta_i_vettori(tmp_path / "doc.db") > 0, "nessun chunk da guastare"
    return DocumentIndex(str(tmp_path / "doc.db"))


def test_un_archivio_di_un_ALTRO_MODELLO_non_esplode(indice_guasto):
    """IL CUORE, primo lato: leggere un backup vecchio non deve alzare. Oggi il
    `np.dot` fra un vettore a 384 e una query a 768 non è nemmeno definito."""
    esito = indice_guasto.search("chi e' il referente", k=3)
    assert isinstance(esito, list)


def test_e_DICHIARA_che_non_riesce_a_leggerli(indice_guasto):
    """IL CUORE, secondo lato — ed è quello che conta di più: senza, la ricerca
    risponde «niente» e chi legge conclude che l'archivio è vuoto. Sono due
    fatti diversi e devono avere due risposte diverse."""
    esito = indice_guasto.search("chi e' il referente", k=3)
    assert getattr(esito, "illeggibili", 0) > 0, (
        "l'archivio è muto: «non ho trovato niente» e «non riesco a leggere "
        "quello che ho» restano indistinguibili")


def test_CONTROLLO_POSITIVO_un_archivio_SANO_non_dichiara_niente(tmp_path):
    """⚠️ Il presidio che tiene onesto il segnale: se `illeggibili` fosse
    valorizzato sempre non direbbe niente, e chi legge imparerebbe a
    ignorarlo."""
    idx = DocumentIndex(str(tmp_path / "sano.db"))
    idx.index_document(source_id="relazione", content=TESTO)
    esito = idx.search("chi e' il referente", k=3)
    assert esito, "l'archivio sano non risponde: banco rotto"
    assert getattr(esito, "illeggibili", 0) == 0


def test_i_chunk_LEGGIBILI_continuano_a_rispondere(tmp_path):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA: un archivio MISTO — qualche
    chunk del modello vecchio e qualcuno del nuovo — deve servire quelli che
    può leggere, non spegnersi tutto. Saltare è una degradazione; rifiutare
    sarebbe una seconda perdita sopra la prima."""
    idx = DocumentIndex(str(tmp_path / "misto.db"))
    idx.index_document(source_id="buono", content=TESTO)
    idx.index_document(source_id="vecchio", content="Testo di un altro periodo.")
    c = sqlite3.connect(str(tmp_path / "misto.db"))
    finto = np.zeros(_DIM_DI_UN_ALTRO_MODELLO, dtype=np.float32).tobytes()
    c.execute("UPDATE chunks SET vec=? WHERE source_id='vecchio'", (finto,))
    c.commit()
    c.close()
    esito = DocumentIndex(str(tmp_path / "misto.db")).search(
        "chi e' il referente", k=3)
    assert esito, "i chunk leggibili non rispondono più"
    assert all(h["source_id"] == "buono" for h in esito)
    assert getattr(esito, "illeggibili", 0) > 0


def test_la_funzione_e_LA_STESSA_dello_sweep_precedente():
    """Non nasce l'ottava copia del criterio: è la funzione estratta curando il
    ciclo di sonno, e risolve la dimensione attesa LIVE."""
    attesi = embedding.expected_embedding_bytes() // 4
    assert embedding.vettore_compatibile([0.0] * attesi) is True
    assert embedding.vettore_compatibile([0.0] * (attesi // 2)) is False
