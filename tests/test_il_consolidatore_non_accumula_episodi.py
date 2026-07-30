"""ws4/episodi — il consolidatore non deve accumulare episodi.

Misurato sul corpus vivo il 2026-07-30 (backup
``episodes.pre-dogfood-cleanup-20260730-133453.db``): 1729 episodi
``Auto-consolidation pass`` su 2167 totali (79,8%), distribuzione
bimodale — 92 prefix con mediana 1 pass, ma i top-5 sono tutti
``metric/*`` con 185-198 pass ciascuno. Due cause, due invarianti:

1. il master Episode nasce NUOVO a ogni re-pass dello stesso prefix,
   mentre il master Fact e' unique per topic
   (``idx_facts_auto_master_unique``) — l'asimmetria accumula ancore;
2. i prefix di telemetria (``metric/``) vengono consolidati come
   qualunque altro topic, e il loro flusso continuo di supersessioni
   ri-innesca il pass ~190 volte.

Effetto utente documentato nel dogfooding: ``hippo_recall('lavoro
fatto sul progetto civsim')`` tornava la telemetria del consolidatore
come top-1 (0.839) sopra il lavoro reale.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from verimem.consolidation import auto_consolidate
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


def _seed_facts(sm: SemanticMemory, topic: str, n: int, *, tag: str) -> None:
    for i in range(n):
        sm.store(Fact(
            proposition=f"Atom {tag} #{i} in {topic} — content {i}",
            topic=topic,
            confidence=0.7,
            source_episodes=[f"ep_seed_{tag}_{i}"],
            verified_by=[f"test:seed:{tag}:{i}"],
            status="model_claim",
        ))


def _count_episodes(db: Path, task_id_like: str) -> int:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT count(*) FROM episodes WHERE task_id LIKE ?",
            (task_id_like,),
        ).fetchone()[0]
    finally:
        con.close()


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def test_un_re_pass_sullo_stesso_prefix_non_accumula_episodi(
    sm: SemanticMemory, mem: EpisodicMemory, tmp_path: Path,
) -> None:
    """Il re-pass legittimo (master superseded + cluster cresciuto)
    deve RIUSARE l'episodio-ancora del prefix, non coniarne un altro.

    Sul corpus vivo questa asimmetria valeva fino a 198 ancore per un
    solo prefix."""
    _seed_facts(sm, "project/acme/sub", 6, tag="a")
    auto_consolidate(sm, mem, min_size=5, prefix_depth=2)
    ep_db = tmp_path / "ep.db"
    first = _count_episodes(ep_db, "project/acme%")
    assert first == 1, f"primo pass: atteso 1 episodio-ancora, trovati {first}"

    # Re-pass legittimo: il master fact viene superseded (come accade
    # sul corpus vivo quando il cluster evolve) e arrivano nuovi atomi.
    with sm._connect() as conn:  # noqa: SLF001 — pattern dei test consolidation
        conn.execute(
            "UPDATE facts SET superseded_by = 'test-re-pass' "
            "WHERE topic LIKE '%auto-MASTER'",
        )
    _seed_facts(sm, "project/acme/sub", 2, tag="b")
    auto_consolidate(sm, mem, min_size=5, prefix_depth=2)

    after = _count_episodes(ep_db, "project/acme%")
    assert after == 1, (
        f"re-pass sullo stesso prefix: l'episodio-ancora deve essere "
        f"riusato, non accumulato — trovati {after} episodi (era il "
        f"meccanismo dei 198 'cycle 144' per prefix sul corpus vivo)"
    )


# NOTA (post-critic 0e65a25d04b48653): qui viveva un secondo test,
# "un prefix di telemetria non produce episodi", scritto per la lama
# 'skip metric/' poi RITIRATA dopo misura (0 fatti metric/ nel corpus:
# il gate di ingest li instrada in telemetry dal 2026-07-20, il filtro
# sarebbe stato codice morto). Il test era rimasto nel file ed era
# AMBIENTE-DIPENDENTE: verde dove il telemetry-routing e' attivo (il
# seed veniva instradato via gate), rosso nell'ambiente pulito della
# suite (il seed scriveva nello store e l'episodio veniva coniato).
# Un test la cui verita' dipende dall'env non misura il prodotto:
# rimosso insieme alla lama che doveva presidiare.
