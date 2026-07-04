"""Tests for schema formation (skill cluster → meta-skill).

Cluster of semantically-close skills get an abstract SCHEMA parent connected
by `specialises` lineage edges. This builds a 2-level hierarchy:
schema → specific skills, navigable through the lineage graph and dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass

from engram.config import CONFIG
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.sleep import SleepEngine, SleepReport


@dataclass
class _LLMResp:
    text: str
    input_tokens: int = 1
    output_tokens: int = 1
    model: str = "mock"
    latency_s: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class _ScriptedLLM:
    def __init__(self, scripts: list[str]) -> None:
        self.scripts = scripts
        self.calls = 0

    def complete(self, system, messages, **kwargs) -> _LLMResp:
        idx = min(self.calls, len(self.scripts) - 1)
        self.calls += 1
        return _LLMResp(text=self.scripts[idx])


def _engine(tmp_data_dir, llm) -> tuple[SleepEngine, SkillLibrary]:
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    mem = EpisodicMemory(tmp_data_dir / "ep.db")
    sem = SemanticMemory(tmp_data_dir / "sem.db")
    return SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm), lib


def test_cluster_by_embedding_groups_similar_skills(tmp_data_dir):
    """Filesystem-themed skills cluster together; an unrelated skill stays out.

    The greedy clustering is sensitive to seed order, and embedding cosine
    between e.g. 'read file from disk' and 'list directory' can be modest.
    We use closely-worded triggers so the cluster is robust on a generic
    sentence-transformer (all-MiniLM-L6-v2) without HF_TOKEN.
    """
    lib = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    fs1 = Skill(name="read file",
                 trigger="read a file from disk to retrieve its contents", body="x")
    fs2 = Skill(name="write file",
                 trigger="write a file to disk to persist its contents", body="x")
    fs3 = Skill(name="open file",
                 trigger="open a file from disk to inspect its contents", body="x")
    other = Skill(name="solve quadratic",
                  trigger="solve a quadratic algebra equation using the formula",
                  body="x")
    for s in (fs1, fs2, fs3, other):
        lib.store(s)

    clusters = lib.cluster_by_embedding(threshold=0.40, min_size=2)
    fs_ids = {fs1.id, fs2.id, fs3.id}
    matched = [c for c in clusters if fs_ids.issubset({s.id for s in c})]
    assert matched, (
        f"fs skills did not cluster together: "
        f"{[[s.name for s in c] for c in clusters]}"
    )
    # The unrelated skill must NOT be in any fs cluster
    for c in matched:
        assert other.id not in {s.id for s in c}


def test_schema_synthesis_creates_meta_skill(tmp_data_dir):
    """A successful schema synthesis stores a 'schema'-stage skill plus
    `specialises` lineage edges to each cluster member."""
    schema_json = """{
  "name": "Filesystem operations",
  "trigger": "any task that reads, writes, or lists files on disk",
  "body": "use read file for fetches; write file for persistence; list dir for inventory",
  "rationale": "all three skills share the disk-IO domain"
}"""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM([schema_json]))
    fs1 = Skill(name="read file",
                 trigger="read a file from disk to retrieve its contents", body="x")
    fs2 = Skill(name="write file",
                 trigger="write a file to disk to persist its contents", body="x")
    fs3 = Skill(name="open file",
                 trigger="open a file from disk to inspect its contents", body="x")
    for s in (fs1, fs2, fs3):
        lib.store(s)
    # Lower the schema cluster threshold for this test to make clustering robust
    # to embedding variability under the default sentence-transformer.
    original_threshold = CONFIG.schema_cluster_threshold
    object.__setattr__(CONFIG, "schema_cluster_threshold", 0.40)

    report = SleepReport()
    try:
        engine._stage_schema(report)
    finally:
        object.__setattr__(CONFIG, "schema_cluster_threshold", original_threshold)
    assert report.n_schemas == 1
    schemas = [s for s in lib.all() if s.stage == "schema"]
    assert len(schemas) == 1
    schema = schemas[0]
    assert "Filesystem" in schema.name

    # Lineage: schema should have `specialises` edges to all three children
    g = lib.lineage_graph()
    edges = [(u, v, g.edges[u, v].get("relation"))
             for u, v in g.edges() if u == schema.id]
    assert len(edges) == 3
    assert all(rel == "specialises" for _, _, rel in edges)
    children = {v for _, v, _ in edges}
    assert children == {fs1.id, fs2.id, fs3.id}


def test_schema_rejects_incoherent_cluster(tmp_data_dir):
    """If the LLM emits 'REJECT', no schema is created."""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["REJECT — no shared theme"]))
    a = Skill(name="x", trigger="x x x x", body="x")
    b = Skill(name="y", trigger="x x x x", body="y")  # near-duplicate trigger to force cluster
    c = Skill(name="z", trigger="x x x x", body="z")
    for s in (a, b, c):
        lib.store(s)

    report = SleepReport()
    engine._stage_schema(report)
    assert report.n_schemas == 0
    assert not [s for s in lib.all() if s.stage == "schema"]


def test_schema_skips_when_no_cluster_meets_min_size(tmp_data_dir):
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["should-not-be-called"]))
    # Only 2 fs skills — below schema_min_cluster_size = 3 (default)
    a = Skill(name="read", trigger="when reading a file from disk", body="x")
    b = Skill(name="write", trigger="when writing a file to disk", body="x")
    for s in (a, b):
        lib.store(s)

    report = SleepReport()
    engine._stage_schema(report)
    assert report.n_schemas == 0
    # Counterintuitive but important: LLM must not have been called
    # (the engine.llm is _ScriptedLLM, count its calls)
    assert engine.llm.calls == 0


def test_schema_does_not_recluster_existing_schemas(tmp_data_dir):
    """Existing schema-stage skills should be excluded from clustering."""
    engine, lib = _engine(tmp_data_dir, _ScriptedLLM(["should-not-be-called"]))
    pre_existing = Skill(name="prev schema", trigger="x", body="x", stage="schema")
    a = Skill(name="other", trigger="x", body="x")
    b = Skill(name="another", trigger="x", body="x")
    for s in (pre_existing, a, b):
        lib.store(s)
    report = SleepReport()
    engine._stage_schema(report)
    # Only 2 non-schema skills → below min_size → no new schema
    assert report.n_schemas == 0
