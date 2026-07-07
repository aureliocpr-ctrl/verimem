"""Dedup skill same-name (qualità skill #5, 2026-07-08).

Gap misurato sul corpus vivo (324 skill): 6 paia residue con NOME IDENTICO e
jaccard token 0.81-0.99 sopravvivono al curator perché ``find_duplicates`` è
solo cosine-su-trigger ≥ CONFIG.fitness_merge_similarity (~0.95) — trigger
riscritti in run diversi non superano la soglia pur essendo la stessa skill.
Un nome normalizzato identico è un segnale ESATTO di duplicazione funzionale:
va riportato come paio a similarity 1.0, in testa alla lista merge, senza LLM.
"""
from __future__ import annotations

from engram.skill import Skill, SkillLibrary


def _mk(name: str, trigger: str) -> Skill:
    return Skill(name=name, trigger=trigger,
                 body="do the thing", rationale="r", stage="rem")


def test_same_name_pair_is_duplicate_even_with_far_triggers(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    a = _mk("Use ReAct format for trivial repeat tasks",
            "when the task repeats a known trivial pattern")
    b = _mk("Use ReAct format for trivial repeat tasks",
            "formatting guidance about stepwise tool responses in loops")
    lib.store(a)
    lib.store(b)
    pairs = lib.find_duplicates(threshold=0.99)  # soglia altissima: embedding non basta
    got = {frozenset((x.id, y.id)) for x, y, _ in pairs}
    assert frozenset((a.id, b.id)) in got, (
        "nome normalizzato identico = duplicato, a prescindere dalla cosine"
    )
    sim = next(s for x, y, s in pairs if {x.id, y.id} == {a.id, b.id})
    assert sim >= 0.999, "il paio same-name va in testa alla lista merge"


def test_same_name_normalisation_is_case_and_space_insensitive(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    a = _mk("Enforce Strict ReAct Format", "alpha trigger")
    b = _mk("  enforce strict react  format ", "completely different beta")
    lib.store(a)
    lib.store(b)
    got = {frozenset((x.id, y.id)) for x, y, _ in lib.find_duplicates(threshold=0.99)}
    assert frozenset((a.id, b.id)) in got


def test_retired_and_distinct_names_not_paired(tmp_path):
    lib = SkillLibrary(db_path=tmp_path / "skills.db")
    a = _mk("Skill Alpha", "t1")
    b = _mk("Skill Alpha", "t2")
    b.status = "retired"
    c = _mk("Skill Beta", "t3")
    for s in (a, b, c):
        lib.store(s)
    got = {frozenset((x.id, y.id)) for x, y, _ in lib.find_duplicates(threshold=0.99)}
    assert frozenset((a.id, b.id)) not in got, "le retired restano fuori dal dedup"
    assert frozenset((a.id, c.id)) not in got, "nomi diversi non si accoppiano"
