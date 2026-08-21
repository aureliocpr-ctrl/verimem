"""Il tier documenti aperto dall'SDK deve stare ACCANTO ai fatti di quella
``Memory``, non nell'indice di sistema.

⚠️ QUESTO È IL PRESIDIO DI UNA RIGA CHE HO SCRITTO IO (`7060f9b7`,
``client.py:1296``) e che senza di lui sarebbe un COMMENTO, non una garanzia::

    db_path=Path(self.semantic.db_path).parent / "document_index.db"

``DocumentIndex`` senza ``db_path`` sceglie da sé
``Path(DocumentStore().db_path).parent / "document_index.db"`` — cioè il percorso
di SISTEMA, che non ha niente a che vedere con la ``Memory`` che lo sta aprendo.
⇒ Togliendo quella riga, **una `Memory(tmp_path)` in un test scrive nell'indice
documenti VERO**: il test passerebbe lo stesso, e se ne accorgerebbe solo chi
trova documenti di prova nel corpus di produzione.

🔑 Il motivo per cui questo file esiste, e non un commento in più: stamattina ho
misurato che `anti_confab_gate.py:1944` avvisava «è il GEMELLO … curare uno solo
dei due lascia intatto il difetto», con tanto di caso misurato — e la cura è
entrata lo stesso curando un percorso solo, a 300 righe da quell'avviso. **Un
commento non fallisce, non si accende, e chi non apre il file non lo incontra.**
Se rimuovo la riga, questo test diventa rosso; il commento sarebbe rimasto lì a
guardare.
"""
from __future__ import annotations

from pathlib import Path

from verimem.client import Memory


def test_il_db_dei_documenti_sta_accanto_a_quello_dei_fatti(tmp_path):
    """L'invariante, detta come la verifica chi legge: stessa cartella."""
    m = Memory(str(tmp_path / "memoria" / "s.db"))

    db_doc = Path(m.documents.db_path).resolve()
    db_fatti = Path(m.semantic.db_path).resolve()

    assert db_doc.parent == db_fatti.parent, (
        f"il tier documenti non e' accanto ai fatti:\n"
        f"  documenti: {db_doc}\n"
        f"  fatti    : {db_fatti}\n"
        "senza questo, una Memory(tmp_path) scrive nell'indice documenti di SISTEMA")


def test_CONTROLLO_non_e_l_indice_di_SISTEMA(tmp_path):
    """Il controllo che rende il primo non-vuoto.

    Senza questo, il test qui sopra passerebbe anche se `DocumentStore()` di
    sistema stesse per caso nella stessa cartella dei fatti — e non misurerebbe
    più niente. Qui si chiede l'opposto: che il default di sistema sia DIVERSO
    da quello che l'SDK ha scelto, cioè che ci fosse davvero qualcosa da evitare.
    """
    from verimem.document_index import DocumentStore

    m = Memory(str(tmp_path / "memoria" / "s.db"))
    di_sistema = (Path(DocumentStore().db_path).parent / "document_index.db").resolve()
    dell_sdk = Path(m.documents.db_path).resolve()

    assert dell_sdk != di_sistema, (
        "il db dell'SDK coincide con quello di SISTEMA: o la riga di client.py e' "
        "saltata, o questo banco sta girando in un ambiente dove i due percorsi "
        "coincidono e allora NON sta misurando niente")
    assert tmp_path in dell_sdk.parents, (
        f"il db dei documenti e' fuori da tmp_path: {dell_sdk}")


def test_un_documento_indicizzato_dall_SDK_si_ritrova_dall_SDK(tmp_path):
    """E la promessa che i due metodi esistono per mantenere: scrivo e ritrovo.

    È lo stesso giro che `test_le_promesse_valgono_appena_installato` fa per
    conto dell'utente; qui serve a legare l'invariante del percorso al
    comportamento — un db nel posto giusto ma inservibile non varrebbe niente.
    """
    doc = tmp_path / "procedura.md"
    doc.write_text(
        "Il codice della procedura di reso e' RMA-4417 e vale trenta giorni.",
        encoding="utf-8")

    m = Memory(str(tmp_path / "memoria" / "s.db"))
    assert m.index_document(str(doc)) is not None

    hits = m.search_documents("codice della procedura di reso", k=3)
    assert hits, "nessun risultato su un documento appena indicizzato dall'SDK"
