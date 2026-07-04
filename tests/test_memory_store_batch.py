"""CYCLE #18 — test store_batch.

Verifica:
  1. Equivalenza semantica con loop di store()
  2. Speedup misurabile (no assertion strict, solo verify che funziona)
  3. Edge case: empty list, mismatched context_embs

Stress test live: N=200 store_batch = ~0.24s vs N=200 store sequential = ~6.7s
→ speedup 28x (embedding model overhead amortizzato + single transaction).
"""
from __future__ import annotations

import time

import pytest

from engram.memory import Episode, EpisodicMemory


@pytest.fixture
def memory(tmp_path):
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _make_eps(n: int) -> list[Episode]:
    return [
        Episode(
            id=f"e{i:03d}", task_id=f"t-{i}",
            task_text=f"task {i} unique text here",
            outcome="success" if i % 2 else "failure",
            final_answer=f"ans-{i}", tokens_used=100,
            skills_used=[], traces=[], created_at=1000.0 + i,
        )
        for i in range(n)
    ]


def test_store_batch_empty_noop(memory):
    """List vuota → no-op (no crash)."""
    memory.store_batch([])
    assert memory.count() == 0


def test_store_batch_persists_all(memory):
    """N=10 episodi → tutti presenti dopo store_batch."""
    eps = _make_eps(10)
    memory.store_batch(eps)
    assert memory.count() == 10
    for ep in eps:
        got = memory.get(ep.id)
        assert got is not None
        assert got.task_text == ep.task_text
        assert got.outcome == ep.outcome


def test_store_batch_equivalent_to_loop_store(tmp_path):
    """store_batch deve produrre stesso DB state di loop store()."""
    eps1 = _make_eps(5)
    eps2 = [Episode(**{**e.__dict__}) for e in eps1]  # deep copy

    mem_seq = EpisodicMemory(db_path=tmp_path / "seq.db")
    for ep in eps1:
        mem_seq.store(ep)

    mem_batch = EpisodicMemory(db_path=tmp_path / "batch.db")
    mem_batch.store_batch(eps2)

    assert mem_seq.count() == mem_batch.count() == 5
    # Stesso content (id, task_text, outcome)
    for eid in [e.id for e in eps1]:
        a, b = mem_seq.get(eid), mem_batch.get(eid)
        assert a.task_text == b.task_text
        assert a.outcome == b.outcome
        assert a.skills_used == b.skills_used


@pytest.mark.perf
def test_store_batch_speedup_real(memory):
    """Stress check: N=50 batch deve essere SIGNIFICATIVAMENTE più veloce
    di N=50 sequential. Soglia conservativa: 1.5x speedup minimo.

    Marked ``perf`` (2026-06-08): this is a wall-clock RATIO assertion, which
    is inherently noisy on shared CI runners (observed 1.27x on a loaded
    macos runner → false failure). The deterministic merge gate now excludes
    ``perf`` (ci.yml: ``-m "not slow and not e2e and not perf"``), matching the
    marker's documented intent ("run with --benchmark-only"). Run it on demand
    with ``pytest -m perf`` where the environment is controlled."""
    eps_seq = _make_eps(50)
    eps_batch = [Episode(**{**e.__dict__, "id": f"b{i:03d}"})
                  for i, e in enumerate(eps_seq)]

    # Warmup embedding model
    from engram import embedding
    embedding.encode("warmup")

    t0 = time.perf_counter()
    for ep in eps_seq:
        memory.store(ep)
    seq_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    memory.store_batch(eps_batch)
    batch_time = time.perf_counter() - t0

    speedup = seq_time / batch_time if batch_time > 0 else 0
    # Print per visibility
    print(f"\nseq={seq_time*1000:.0f}ms batch={batch_time*1000:.0f}ms speedup={speedup:.1f}x")
    # Conservative threshold: batch deve essere almeno 2x. Live mostra 15-28x.
    # NOTA: con stub embedding del conftest che è O(1), lo speedup vine dal
    # solo single-transaction (modello reale dà 10-30x).
    assert speedup >= 1.5, f"Batch non più veloce: {speedup}x"


def test_store_batch_context_embs_length_mismatch(memory):
    """context_embs len != episodes len → ValueError."""
    eps = _make_eps(3)
    import numpy as np
    bad_ctx = [np.zeros(384, dtype=np.float32) for _ in range(2)]  # solo 2
    with pytest.raises(ValueError, match="context_embs"):
        memory.store_batch(eps, context_embs=bad_ctx)


def test_store_batch_salience_equivalent_to_loop_store(tmp_path):
    """CYCLE #23 — critic counterexample regression: salience SCALAR
    deve essere uguale (entro epsilon) tra store sequential e store_batch.

    Pre-cycle-23 store_batch divergeva per:
      (a) self-corpus: upsert su id esistente ritornava salience=0
          invece di 0.5 (no self-filter)
      (b) no max(0, delta) clip → cos<0 produce salience > 1
      (c) min(1.0, ...) cap solo in failure branch
    """
    # Popola entrambe le memory con uno stesso corpus baseline
    baseline = _make_eps(10)
    mem_seq = EpisodicMemory(db_path=tmp_path / "seq.db")
    mem_batch = EpisodicMemory(db_path=tmp_path / "batch.db")
    for ep in baseline:
        mem_seq.store(Episode(**{**ep.__dict__}))
    mem_batch.store_batch([Episode(**{**ep.__dict__}) for ep in baseline])

    # Aggiungi nuovi ep — uno con outcome=failure per testare 1.5x boost
    new_eps_seq = [
        Episode(
            id="n1", task_id="t-n1", task_text="task novel",
            outcome="success", final_answer="x", tokens_used=0,
            skills_used=[], traces=[], created_at=2000.0,
        ),
        Episode(
            id="n2", task_id="t-n2", task_text="task failure case",
            outcome="failure", final_answer="x", tokens_used=0,
            skills_used=[], traces=[], created_at=2001.0,
        ),
    ]
    new_eps_batch = [Episode(**{**e.__dict__}) for e in new_eps_seq]

    for ep in new_eps_seq:
        mem_seq.store(ep)
    mem_batch.store_batch(new_eps_batch)

    # Salience equivalente entro tolleranza embedding (stub deterministico)
    for eid in ["n1", "n2"]:
        s1 = mem_seq.get(eid).salience_score
        s2 = mem_batch.get(eid).salience_score
        assert abs(s1 - s2) < 0.05, (
            f"Salience divergence for {eid}: seq={s1:.3f} batch={s2:.3f}"
        )


def test_store_batch_upsert_does_not_corrupt_salience(tmp_path):
    """CYCLE #23 — critic worker 3 (a): upsert su id esistente NON deve
    self-confondere salience. store_batch usa INSERT OR REPLACE → un id
    duplicato è path valido. Pre-fix: cos=1.0 con self → delta=0 →
    salience=0. Post-fix: filtra self da top-k → fallback comportamento
    originale.
    """
    mem = EpisodicMemory(db_path=tmp_path / "u.db")
    # Pre-popola con e1
    e1 = Episode(
        id="e1", task_id="t-1", task_text="hello world",
        outcome="success", final_answer="x", tokens_used=0,
        skills_used=[], traces=[], created_at=1000.0,
    )
    mem.store(e1)
    sal_before = mem.get("e1").salience_score
    # Upsert via store_batch con stesso id
    e1_dup = Episode(**{**e1.__dict__})
    mem.store_batch([e1_dup])
    sal_after = mem.get("e1").salience_score
    # Salience deve restare 0.5 (no other neighbors after self-filter).
    # Pre-fix: era 0.0 perché cos(e1, e1)=1 → delta=0.
    assert sal_after == 0.5, (
        f"Upsert salience corrupted: {sal_before} → {sal_after} "
        "(self-filter mancante)"
    )


def test_store_batch_salience_capped_at_one(tmp_path):
    """CYCLE #23 — critic worker 3 (c): outer-cap min(1.0, salience)
    deve essere SEMPRE applicato. failure_boost 1.5 può portare
    salience oltre 1.0 senza cap.
    """
    mem = EpisodicMemory(db_path=tmp_path / "c.db")
    # Pre-popola un corpus diversificato per garantire salience > 0
    for i in range(5):
        mem.store(Episode(
            id=f"b{i}", task_id=f"t-b{i}",
            task_text=f"baseline text variant {i}",
            outcome="success", final_answer=f"a{i}", tokens_used=0,
            skills_used=[], traces=[], created_at=1000.0 + i,
        ))
    # Nuovo ep failure con text molto diverso → surprise alta
    mem.store_batch([Episode(
        id="failure_ep", task_id="t-f",
        task_text="totally orthogonal unrelated topic",
        outcome="failure", final_answer="!", tokens_used=0,
        skills_used=[], traces=[], created_at=2000.0,
    )])
    sal = mem.get("failure_ep").salience_score
    assert 0.0 <= sal <= 1.0, f"Salience out of [0,1]: {sal}"


def test_store_batch_preserves_skills_used(memory):
    """skills_used JSON deve persistere correttamente."""
    eps = _make_eps(3)
    eps[0].skills_used = ["sk1", "sk2"]
    eps[1].skills_used = []
    eps[2].skills_used = ["sk1"]
    memory.store_batch(eps)
    assert memory.get("e000").skills_used == ["sk1", "sk2"]
    assert memory.get("e001").skills_used == []
    assert memory.get("e002").skills_used == ["sk1"]
