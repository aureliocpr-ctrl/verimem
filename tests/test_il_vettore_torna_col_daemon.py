"""Il vettore di una scrittura rinviata torna quando torna il daemon.

MISURATO il 2026-09-25 sullo store vero, in sola lettura: otto fatti scritti il
24/09 fra le 22:56 e le 22:59, col daemon assente, erano entrati SENZA vettore
e l'hanno avuto solo dopo il riavvio della macchina del giorno dopo. L'unica
guarigione automatica era `self_heal`, all'avvio di un server MCP: in un
processo CLI o SDK non arrivava mai, e per gli episodi da nessuna parte. E
nessuna delle otto scritture aveva chiesto il daemon: dei quattro punti che
degradano per `EncodeDelegateUnavailable`, uno solo lo svegliava.

La promessa (I7): una degradazione non resta silenziosa, e un fatto scritto si
ritrova per significato appena il daemon c'e'.

NESSUN MODELLO: il conftest sostituisce il modello con uno stub deterministico;
il daemon si simula con `encode_service.daemon_usable` (c'e' o no) ed
`encode_service.ensure_running` (la spia della sveglia).
"""
from __future__ import annotations

import pytest

from verimem import embedding, encode_service, memory
from verimem.episode import Episode
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sveglie(monkeypatch):
    """Registra ogni richiesta di un daemon, senza avviarne nessuno."""
    chiamate: list[int] = []
    monkeypatch.setattr(encode_service, "ensure_running",
                        lambda *a, **k: chiamate.append(1))
    return chiamate


@pytest.fixture(autouse=True)
def _nessun_limite_ereditato(monkeypatch):
    # Il limite di frequenza della guarigione e' per processo: una cella non
    # deve trovare quello lasciato dalla precedente.
    if hasattr(embedding, "_prossima_guarigione"):
        monkeypatch.setattr(embedding, "_prossima_guarigione", {})


def _il_daemon(monkeypatch, c_e: bool) -> None:
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: c_e)


def _delegato_assente(*a, **k):
    raise embedding.EncodeDelegateUnavailable(
        "encode daemon unavailable and in-process cold-load is disabled "
        "(HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade")


def _byte_del_vettore(sm: SemanticMemory, fid: str) -> int:
    with sm._connect() as conn:
        return conn.execute("SELECT length(embedding) FROM facts WHERE id = ?",
                            (fid,)).fetchone()[0]


def _byte_del_vettore_episodio(mem: EpisodicMemory, eid: str) -> int:
    with mem._connect() as conn:
        return conn.execute(
            "SELECT length(summary_embedding) FROM episodes WHERE id = ?",
            (eid,)).fetchone()[0]


def test_la_recall_rida_il_vettore_ai_fatti_rinviati_quando_il_daemon_c_e(
        tmp_path, monkeypatch):
    """LA CURA. RED sul tronco: il vettore tornava solo all'avvio di un server."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Il magazzino di Padova apre alle otto.", topic="negozio")
    sm.store(f, embed="defer")
    assert _byte_del_vettore(sm, f.id) == 0, (
        "il rinvio non ha lasciato la riga senza vettore: la cella non misura")
    _il_daemon(monkeypatch, True)

    sm.recall("magazzino di Padova", k=3)

    assert _byte_del_vettore(sm, f.id) == embedding.expected_embedding_bytes(), (
        "il daemon c'era e la recall non ha rifatto il vettore: il fatto resta "
        "invisibile alla ricerca per significato fino al prossimo server")


def test_senza_daemon_la_recall_non_prova_a_rifare_i_vettori(tmp_path, monkeypatch):
    """Il daemon non c'e': niente guarigione, e soprattutto niente modello
    caricato in questo processo per farla."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="Il magazzino di Treviso chiude alle sette.", topic="negozio")
    sm.store(f, embed="defer")
    _il_daemon(monkeypatch, False)
    tentativi: list[int] = []
    monkeypatch.setattr(sm, "backfill_pending_embeddings",
                        lambda **k: tentativi.append(1) or 0)

    sm.recall("magazzino di Treviso", k=3)

    assert tentativi == [], "senza daemon non si ricodifica niente"
    assert _byte_del_vettore(sm, f.id) == 0


def test_una_scrittura_sincrona_senza_delegato_chiede_il_daemon(
        tmp_path, monkeypatch, sveglie):
    """Il ramo di `verimem save` e di `Memory.add`: degradava e basta. RED sul
    tronco."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    monkeypatch.setattr(embedding, "encode", _delegato_assente)
    f = Fact(proposition="Il furgone parte alle sei.", topic="negozio")

    sm.store(f)

    assert _byte_del_vettore(sm, f.id) == 0, "la scrittura doveva degradare"
    assert sveglie, (
        "la scrittura e' entrata senza vettore e nessuno ha chiesto il daemon: "
        "la prossima fallira' identica")


def test_un_episodio_sincrono_senza_delegato_chiede_il_daemon(
        tmp_path, monkeypatch, sveglie):
    """Il gemello negli episodi. RED sul tronco."""
    mem = EpisodicMemory(db_path=tmp_path / "e.db")
    monkeypatch.setattr(embedding, "encode", _delegato_assente)

    mem.store(Episode(id="ep-sincrono", task_text="riordinare il magazzino",
                      final_answer="fatto"))

    assert _byte_del_vettore_episodio(mem, "ep-sincrono") == 0
    assert sveglie, "l'episodio e' entrato senza vettore e nessuno ha chiesto il daemon"


def test_un_episodio_nel_budget_senza_delegato_chiede_il_daemon(monkeypatch, sveglie):
    """Il ramo dell'episodio che scrive nel budget. RED sul tronco: il suo ramo
    LENTO chiedeva il daemon, quello ASSENTE no."""
    monkeypatch.setattr(embedding, "encode", _delegato_assente)

    esito = memory._encode_episode_within_budget("un episodio qualsiasi", 5.0)

    assert esito is None, "il ramo doveva degradare"
    assert sveglie, "nessuno ha chiesto il daemon"


def test_la_recall_degli_episodi_rida_il_vettore_quando_il_daemon_c_e(
        tmp_path, monkeypatch):
    """Gli episodi non li guariva nemmeno l'avvio del server. RED sul tronco."""
    mem = EpisodicMemory(db_path=tmp_path / "e.db")
    mem.store(Episode(id="ep-rinviato", task_text="contare le scatole in magazzino",
                      final_answer="dodici"), embed="defer")
    assert _byte_del_vettore_episodio(mem, "ep-rinviato") == 0
    _il_daemon(monkeypatch, True)

    mem.recall("scatole in magazzino", k=3)

    assert _byte_del_vettore_episodio(mem, "ep-rinviato") > 0, (
        "il daemon c'era e la recall non ha rifatto il vettore dell'episodio")
