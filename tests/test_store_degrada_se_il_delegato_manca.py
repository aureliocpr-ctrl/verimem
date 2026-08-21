"""GATE — punto 3 del mandato di Aurelio (2026-08-20 19:48): «leak DELEGATE_ONLY
(contratto store-degrada)».

Il difetto, misurato il 20/08 su `f26c7b26` eseguendo
``tests/test_consolidation_unique_index_cross_process.py``::

    consolidation.py:507  _persist_master
      -> semantic.py:3235   store            (ramo embed="sync")
        -> embedding.py:254 _encode_one
    verimem.embedding.EncodeDelegateUnavailable: encode daemon unavailable and
    in-process cold-load is disabled (HIPPO_ENCODE_DELEGATE_ONLY=1)
    — caller must degrade

**Il messaggio dell'eccezione dice «caller must degrade», e il chiamante non
degrada.** Nello stesso file, sullo stesso errore, il percorso del RECALL degrada
già (``semantic.py:168``: ``return None``, «recall falls back to keyword, save
defers»). Due percorsi, uno protetto e uno no: la giuntura, non il componente.

⚠️ Perché conta per chi installa e non solo per noi: ``HIPPO_ENCODE_DELEGATE_ONLY``
**esce dal server MCP e resta nell'ambiente** — ``tests/conftest.py:136`` lo
documenta dal 2026-06-06 («an in-process ``mcp_server.main()`` leaks permanently
via ``os.environ.setdefault``»), e il 20/08 era nella shell di ws8 senza che
l'avesse mai impostata. Chi eredita il flag e non ha il daemon **perde la
scrittura** invece di scriverla senza embedding.

PERIMETRO STRETTO, e i due controlli qui sotto lo tengono:
  • degrada SOLO su ``EncodeDelegateUnavailable`` — cioè «il delegato non c'è»,
    che non è un errore di encoding ma di disponibilità;
  • ogni altra eccezione continua a propagare: ingoiarle nasconderebbe difetti
    veri dietro una scrittura silenziosamente senza vettore.
"""
from __future__ import annotations

import pytest

from verimem import embedding
from verimem.semantic import Fact, SemanticMemory


def _delegato_assente(monkeypatch):
    """``embedding.encode`` alza EncodeDelegateUnavailable, come quando
    ``HIPPO_ENCODE_DELEGATE_ONLY=1`` e il daemon non risponde. Stesso pattern di
    ``tests/test_recall_cold_fallback_bm25.py``: si monkeypatcha la funzione
    pubblica, non l'interno, per non dipendere dall'ordine dei test."""
    def _raise(*a, **k):
        raise embedding.EncodeDelegateUnavailable("delegato assente (banco ws8)")

    monkeypatch.setattr(embedding, "encode", _raise)


def test_store_sync_degrada_quando_il_delegato_non_c_e(tmp_path, monkeypatch):
    """Il caso del mandato: la scrittura NON deve morire perché manca il delegato."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    _delegato_assente(monkeypatch)

    f = Fact(proposition="Il servizio di encoding non risponde a questa scrittura.",
             topic="gate/delegate-only")
    sm.store(f, embed="sync")          # <- prima di questa cura: alzava

    riletto = sm.get(f.id)
    assert riletto is not None, (
        "la scrittura e' andata persa: store ha degradato l'embedding ma non ha "
        "scritto il fatto")


def test_CONTROLLO_un_errore_DIVERSO_continua_a_propagare(tmp_path, monkeypatch):
    """Il perimetro: si degrada sull'ASSENZA del delegato, non su tutto.

    Senza questo controllo la cura potrebbe essere un ``except Exception`` che
    scrive fatti senza vettore ogni volta che l'encoder ha un problema vero, e
    nessuno se ne accorgerebbe."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    def _raise_altro(*a, **k):
        raise RuntimeError("guasto vero dell'encoder, non un delegato assente")

    monkeypatch.setattr(embedding, "encode", _raise_altro)

    f = Fact(proposition="Questo errore non e' un delegato assente.",
             topic="gate/delegate-only")
    with pytest.raises(RuntimeError):
        sm.store(f, embed="sync")


def test_ANCHE_l_episodio_degrada_quando_il_delegato_non_c_e(tmp_path, monkeypatch):
    """IL GEMELLO, e senza questo la cura era mezza.

    ``consolidation._persist_master`` chiama DUE store: ``sm.store(f)``
    (semantic.py:507) e ``mem.store(ep)`` (:508). Curando solo il primo, il
    cross-process passava da «Worker A failed» a «Worker B failed» — stesso
    ``embedding.py:254``, altro chiamante. Misurato il 2026-08-21 su ``aeee8305``.

    🔑 E' la classe «manca lo SWEEP: chi ALTRO fa la stessa cosa?»: il difetto non
    era in un componente ma in DUE chiamanti simmetrici, e uno solo era protetto.
    """
    from verimem.memory import Episode, EpisodicMemory

    mem = EpisodicMemory(db_path=tmp_path / "episodes.db")
    _delegato_assente(monkeypatch)

    ep = Episode(task_id="gate-delegate-only",
                 task_text="scrittura con il delegato assente")
    mem.store(ep, embed="sync")        # <- prima di questa cura: alzava

    assert mem.get(ep.id) is not None, (
        "l'episodio e' andato perso: store ha degradato l'embedding ma non ha "
        "scritto l'episodio")


def test_CONTROLLO_senza_il_guasto_la_scrittura_resta_normale(tmp_path):
    """La popolazione opposta: con l'encoder sano nulla cambia.

    Se questo cade, il rotto e' il banco o la cura ha allargato il perimetro
    fino a toccare il percorso sano."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    f = Fact(proposition="Una scrittura ordinaria con l'encoder disponibile.",
             topic="gate/delegate-only")
    sm.store(f, embed="sync")
    assert sm.get(f.id) is not None
