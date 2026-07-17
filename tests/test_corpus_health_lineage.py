"""CYCLE #29 — corpus_health_score connect_frac via skill_lineage.

Bug ricorrente non mergiato dal cycle #2: connect_frac contava
`s.preconditions or s.postconditions` che non sono mai popolati →
score sempre 0 per Component 4 (10 punti sottostimati).

Fix: SQL COUNT(DISTINCT id) su skill_lineage table.
"""
from __future__ import annotations

import pytest

from verimem.corpus_health_score import _count_lineage_connected, compute_health_score
from verimem.skill import Skill, SkillLibrary


class _FakeAgent:
    def __init__(self, skills_store, memory=None):
        self.skills = skills_store
        self.memory = memory


class _FakeMemory:
    def __init__(self):
        self._eps = []

    def all(self, **kwargs):
        return self._eps


@pytest.fixture
def library(tmp_path):
    return SkillLibrary(dir_path=tmp_path / "sk", db_path=tmp_path / "sk.db")


def test_count_lineage_connected_empty(library):
    """No edges → 0 connected."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B"))
    assert _count_lineage_connected(library, {"a", "b"}) == 0


def test_count_lineage_connected_with_edges(library):
    """3 skill, 1 parent edge a→b → 2 connected (a + b)."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))
    library.store(Skill(id="c", name="C"))
    assert _count_lineage_connected(library, {"a", "b", "c"}) == 2


def test_count_lineage_connected_filters_by_ids(library):
    """Conta solo skill nei id_set passato."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))
    # Restrict a solo "a"
    assert _count_lineage_connected(library, {"a"}) == 1


def test_health_score_connect_frac_nonzero_with_lineage(library):
    """Component 4 deve essere > 0 con lineage edges, non più sempre 0."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))
    library.store(Skill(id="c", name="C"))
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    # CYCLE #32: composta mean(derivedness, fecundity).
    # a→b, c isolated → derived=1/3 (b), fecund=1/3 (a) → mean=1/3
    # Importante: > 0 (non più sempre 0 come pre-#29), ma non satura.
    assert result["components"]["connect_frac"] > 0.0
    assert result["components"]["connect_frac"] == pytest.approx(1 / 3, abs=0.01)


def test_health_score_no_skills_returns_neutral(library):
    """Edge case: 0 skill → connect_frac = 0.5 (neutral, no division by zero)."""
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    assert "connect_frac" in result["components"]
    # Codice usa 0.5 come neutral default quando skills vuoto.
    assert result["components"]["connect_frac"] == 0.5


# CYCLE #31 — retired skill NON devono distorcere health metrics.
# Bug live scoperto: 318 skill (.all()), di cui 148 retired (47%). promoted_frac
# = 5/318 = 1.5% (matematica corretta ma fuorviante: 5/170 vivi = 2.94%).
# connect_frac saturato a 1.0 perché 318/318 sono in lineage, anche le morte.
# Le retired sono "morte" — non contano per la salute del corpus attivo.

def test_health_score_excludes_retired_from_promoted_frac_denominator(library):
    """promoted_frac deve ignorare retired nel denominatore."""
    library.store(Skill(id="p1", name="P1", status="promoted"))
    library.store(Skill(id="c1", name="C1", status="candidate"))
    library.store(Skill(id="r1", name="R1", status="retired"))
    library.store(Skill(id="r2", name="R2", status="retired"))
    library.store(Skill(id="r3", name="R3", status="retired"))
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    # Pre-fix bug: 1 promoted / 5 totali = 0.20
    # Post-fix: 1 promoted / 2 attivi (p1+c1) = 0.50
    assert result["components"]["promoted_frac"] == pytest.approx(0.5, abs=0.01), (
        f"retired inflano denom: got {result['components']['promoted_frac']}"
    )


def test_health_score_excludes_retired_from_connect_frac(library):
    """connect_frac non deve contare retired anche se sono in lineage."""
    # 1 alive senza lineage, 1 retired CON lineage → connect_frac = 0/1 = 0.0
    library.store(Skill(id="alive", name="Alive", status="candidate"))
    library.store(Skill(id="dead_parent", name="DeadParent", status="retired"))
    library.store(Skill(
        id="dead_child", name="DeadChild", status="retired",
        parent_skills=["dead_parent"],
    ))
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    # alive non ha edges → 0/1 attive connected → 0.0
    assert result["components"]["connect_frac"] == pytest.approx(0.0, abs=0.01), (
        f"retired contano come connected: got {result['components']['connect_frac']}"
    )


def test_health_score_all_retired_returns_neutral(library):
    """Edge case: tutte retired → corpus vuoto attivo → neutral defaults."""
    library.store(Skill(id="r1", name="R1", status="retired"))
    library.store(Skill(id="r2", name="R2", status="retired"))
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    # Nessuna alive → tratta come corpus vuoto: connect_frac = 0.5 neutral
    assert result["components"]["promoted_frac"] == 0.0
    assert result["components"]["connect_frac"] == 0.5


def test_health_score_alive_only_no_retired_unchanged(library):
    """Backward compat: senza retired, scores identici al pre-fix."""
    library.store(Skill(id="a", name="A", status="candidate"))
    library.store(Skill(id="b", name="B", status="candidate", parent_skills=["a"]))
    library.store(Skill(id="c", name="C", status="promoted"))
    agent = _FakeAgent(library, memory=_FakeMemory())
    result = compute_health_score(agent=agent)
    assert result["components"]["promoted_frac"] == pytest.approx(1 / 3, abs=0.01)
    # CYCLE #32: connect_frac ora = mean(frac_with_parent, frac_with_child)
    # a: no parent + 1 child (b) → solo fecund
    # b: 1 parent (a), no child → solo derived
    # c: no parent, no child → isolated
    # frac_with_parent = 1/3 (solo b), frac_with_child = 1/3 (solo a)
    # mean = 1/3
    assert result["components"]["connect_frac"] == pytest.approx(1 / 3, abs=0.01)


# CYCLE #32 — connect_frac discriminativo (no saturation).
# Pre-fix #32: connect_frac = frac alive che ha ALMENO un edge (parent OR child).
# Su corpus reale satura a 1.0 (170/170 alive in lineage) → metrica morta.
# Fix #32: connect_frac = mean(frac_with_parent, frac_with_child).
#   - frac_with_parent = "derivedness" (skill è figlia di apprendimento)
#   - frac_with_child = "fecundity" (skill genera derivazioni)
# Satura a 1.0 SOLO se ogni alive è nodo interno (parent AND child) → mai in pratica.

def test_connect_frac_discriminative_isolated_singleton(library):
    """1 skill isolata → connect_frac = 0.0 (no parent, no child)."""
    library.store(Skill(id="solo", name="Solo", status="candidate"))
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    assert r["components"]["connect_frac"] == pytest.approx(0.0, abs=0.01)


def test_connect_frac_discriminative_chain(library):
    """3 skill in chain a→b→c → mean(2/3 with_parent, 2/3 with_child) = 2/3."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))
    library.store(Skill(id="c", name="C", parent_skills=["b"]))
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    # frac_with_parent = 2/3 (b, c), frac_with_child = 2/3 (a, b)
    assert r["components"]["connect_frac"] == pytest.approx(2 / 3, abs=0.01)


def test_connect_frac_does_not_saturate_on_star(library):
    """Star: 1 root, N foglie. Pre-fix saturava a 1.0. Post-fix < 1.0."""
    library.store(Skill(id="root", name="Root"))
    for i in range(5):
        library.store(Skill(id=f"leaf{i}", name=f"L{i}", parent_skills=["root"]))
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    # 6 skill: 5 hanno parent (leaves) → frac_with_parent = 5/6
    # 1 ha child (root) → frac_with_child = 1/6
    # mean = 6/12 = 0.5
    assert r["components"]["connect_frac"] == pytest.approx(0.5, abs=0.01)
    # Crucial: NOT saturated despite all 6 nodes touching lineage
    assert r["components"]["connect_frac"] < 0.99


def test_connect_frac_excludes_specialises_schema_edges(library):
    """CYCLE #33: schema 'specialises' edges (clustering) NON sono vera derivazione.
    Pre-fix: gonfiate fecundity di skill-schemi che ASTRAGGONO N skill esistenti.
    Post-fix: connect_frac conta solo 'derived_from' (vera genealogia)."""
    library.store(Skill(id="s_root", name="Schema Root", status="candidate"))
    library.store(Skill(id="m1", name="Member 1", status="candidate"))
    library.store(Skill(id="m2", name="Member 2", status="candidate"))
    library.store(Skill(id="m3", name="Member 3", status="candidate"))
    # Schema-style edges (clustering aggregation) — NOT genealogy
    library.add_lineage_edge("s_root", "m1", "specialises")
    library.add_lineage_edge("s_root", "m2", "specialises")
    library.add_lineage_edge("s_root", "m3", "specialises")
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    # 4 skill, ZERO derived_from edges → derivedness=0, fecundity=0, connect=0
    assert r["components"]["derivedness"] == pytest.approx(0.0, abs=0.01), (
        f"specialises edges contano come derivazione: {r['components']}"
    )
    assert r["components"]["fecundity"] == pytest.approx(0.0, abs=0.01)
    assert r["components"]["connect_frac"] == pytest.approx(0.0, abs=0.01)


def test_connect_frac_mixes_derived_from_only(library):
    """Mix: 1 chain a→b derived_from + 1 specialises x→y → connect_frac da solo a→b."""
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))  # derived_from
    library.store(Skill(id="x", name="X (schema)"))
    library.store(Skill(id="y", name="Y (cluster member)"))
    library.add_lineage_edge("x", "y", "specialises")
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    # 4 alive. derived_from: b has parent (1/4), a has child (1/4)
    # specialises ignored.
    assert r["components"]["derivedness"] == pytest.approx(1 / 4, abs=0.01)
    assert r["components"]["fecundity"] == pytest.approx(1 / 4, abs=0.01)
    assert r["components"]["connect_frac"] == pytest.approx(1 / 4, abs=0.01)


def test_connect_frac_full_internal_saturates(library):
    """Solo DAG completamente "internal" (ogni nodo è sia parent che child) → 1.0.
    Praticamente impossibile, ma copre l'edge case matematico."""
    # a→b, b→c, c→a impossibile (DAG aciclico). Quindi facciamo:
    # a→b, a→c, b→c (a parent di b,c; b parent di c)
    # frac_with_parent: b,c = 2/3 (a no)
    # frac_with_child: a,b = 2/3 (c no)
    # mean = 2/3
    library.store(Skill(id="a", name="A"))
    library.store(Skill(id="b", name="B", parent_skills=["a"]))
    library.store(Skill(id="c", name="C", parent_skills=["a", "b"]))
    agent = _FakeAgent(library, memory=_FakeMemory())
    r = compute_health_score(agent=agent)
    assert r["components"]["connect_frac"] == pytest.approx(2 / 3, abs=0.01)
