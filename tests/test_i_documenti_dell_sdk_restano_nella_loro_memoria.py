"""Un documento indicizzato dall'SDK deve trovarsi dalla porta che usa il resto
del prodotto — e in un test non deve finire nel corpus di produzione.

⚠️ QUESTO FILE HA GIÀ PRESIDIATO LA COSA SBAGLIATA, ed è la ragione per cui
adesso è scritto così. La prima stesura (`2b30e78a`) difendeva la riga::

    db_path=Path(self.semantic.db_path).parent / "document_index.db"

chiedendo che il db dei documenti stesse **accanto ai fatti**. Era verde, era
motivata bene, e sorvegliava che un difetto restasse al suo posto: misurato il
2026-08-21 su una ``Memory()`` senza argomenti, cioè l'uso normale::

    SDK    : <data_dir>/semantic/document_index.db
    SISTEMA: <data_dir>/documents/document_index.db
    STESSO STORE? False

    indicizzato dall'SDK  -> trovato dall'SDK stesso : True
                          -> trovato dalla porta MCP : False

Un utente che faceva ``m.index_document(...)`` e poi cercava da Claude Code con
``hippo_document_search`` non trovava niente.

🔑 LA LEZIONE, che vale oltre questo file: avevo risolto un problema di
**isolamento** rompendo l'**interoperabilità**, e il presidio che ho scritto
guardava solo il primo dei due. Un test che verifica la metà del problema che
avevi in mente non è una garanzia: è una fotografia della tua attenzione.

L'invariante vera è quella che questo file chiede adesso — le due porte vedono
lo stesso documento — e l'isolamento lo dà ``HIPPO_DATA_DIR``, non il percorso
del db. Il secondo test qui sotto lo verifica ancora, perché quel pericolo era
reale: è la ragione giusta, applicata dove serve.
"""
from __future__ import annotations

from pathlib import Path

from verimem.client import Memory


def test_un_documento_indicizzato_dall_SDK_si_trova_DALLA_PORTA_DI_SISTEMA(tmp_path):
    """L'INVARIANTE: SDK e porta MCP/CLI guardano lo stesso tier.

    ``hippo_document_search`` (mcp_server.py:1741) apre un ``DocumentIndex()``
    senza argomenti. Se l'SDK ne apre un altro, chi indicizza da qui non trova
    niente da là — che è lo stato in cui il prodotto era.
    """
    from verimem.document_index import DocumentIndex

    doc = tmp_path / "procedura.md"
    doc.write_text(
        "Il codice della procedura di reso e' RMA-4417 e vale trenta giorni.",
        encoding="utf-8")

    m = Memory(str(tmp_path / "memoria" / "s.db"))
    assert m.index_document(str(doc)) is not None

    dalla_porta = DocumentIndex().search("codice della procedura di reso", k=3)
    assert dalla_porta, (
        "indicizzato dall'SDK e NON trovato da `DocumentIndex()`, che e' la porta "
        "che usano hippo_document_search e la CLI: i due store sono divergenti e "
        "l'utente perde i documenti che ha appena indicizzato")


def test_e_il_giro_completo_dell_SDK_continua_a_funzionare(tmp_path):
    """Il controllo che l'invariante sopra non sia stata ottenuta rompendo l'SDK.

    Senza di lui, un ``search_documents`` che restituisse sempre l'indice di
    sistema vuoto passerebbe il primo test per la ragione sbagliata.
    """
    doc = tmp_path / "listino.md"
    doc.write_text(
        "Il piano annuale costa 1200 euro e include due giorni di formazione.",
        encoding="utf-8")

    m = Memory(str(tmp_path / "memoria" / "s.db"))
    assert m.index_document(str(doc)) is not None
    assert m.search_documents("quanto costa il piano annuale", k=3), (
        "nessun risultato su un documento appena indicizzato dall'SDK")


def test_NON_scrive_nel_corpus_di_PRODUZIONE(tmp_path, monkeypatch):
    """Il pericolo che la prima stesura voleva evitare — ed era reale.

    Non è sparito con la cura: è solo tornato al presidio giusto. L'isolamento
    lo dà ``HIPPO_DATA_DIR`` (che il conftest punta a una tmp per ogni test), non
    il percorso del db. Qui si verifica che sia davvero così, perché è
    l'invariante da cui dipende che una suite non sporchi la memoria vera.

    ⚠️ Il controllo è su ``HOME``/data-dir, non su un percorso scritto a mano:
    un test che confronta con una stringa fissa smette di misurare il giorno in
    cui il default cambia, e non lo dice.
    """
    from verimem.config import CONFIG

    m = Memory(str(tmp_path / "memoria" / "s.db"))
    db_doc = Path(m.documents.db_path).resolve()
    data_dir = Path(CONFIG.data_dir).resolve()

    assert data_dir in db_doc.parents or db_doc.parent == data_dir, (
        f"il db dei documenti ({db_doc}) e' fuori dalla data dir corrente "
        f"({data_dir}): in un test questo significa scrivere nel corpus di "
        "PRODUZIONE")
    assert tmp_path in data_dir.parents or str(data_dir).startswith(
        str(Path(tmp_path).anchor)), (
        f"la data dir del test e' {data_dir}: se non e' una tmp, la fixture di "
        "isolamento del conftest non sta girando e questo file sta scrivendo "
        "nella memoria vera")
