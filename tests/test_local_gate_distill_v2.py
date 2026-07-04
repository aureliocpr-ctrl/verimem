"""Unit tests for benchmark/local_gate_distill_v2.py — corpus sampling + label-file
plumbing only (claude labeling and training run live, not in unit tests)."""
from __future__ import annotations

import json
import sqlite3

from benchmark.local_gate_distill_v2 import (
    load_labeled_jsonl,
    make_swap_negatives,
    sample_corpus_facts,
)


def _mini_dbs(tmp_path):
    sem = tmp_path / "semantic.db"
    epi = tmp_path / "episodes.db"
    c = sqlite3.connect(sem)
    c.execute("CREATE TABLE facts (id TEXT, proposition TEXT, source_episodes TEXT,"
              " topic TEXT, superseded_by TEXT, created_at REAL)")
    for i in range(12):
        c.execute("INSERT INTO facts VALUES (?,?,?,?,NULL,?)",
                  (f"f{i:02d}", f"Proposizione tecnica numero {i} con dettagli vari "
                                f"su modulo M{i} e parametro P{i}.",
                   f"ep{i:02d}", f"topic/{i % 3}", float(i)))
    c.execute("INSERT INTO facts VALUES ('fsup','superseded fact xxxxxxxxxxxxxxxxxxxxxxx',"
              "'ep00','topic/0','other',99.0)")
    c.commit(); c.close()
    e = sqlite3.connect(epi)
    e.execute("CREATE TABLE episodes (id TEXT, task_text TEXT, final_answer TEXT)")
    for i in range(12):
        e.execute("INSERT INTO episodes VALUES (?,?,?)",
                  (f"ep{i:02d}", f"Task {i}: lavorare sul modulo M{i}",
                   f"Esito {i}: il parametro P{i} del modulo M{i} configurato. " * 8))
    e.commit(); e.close()
    return sem, epi


def test_sample_excludes_ids_and_superseded(tmp_path):
    sem, epi = _mini_dbs(tmp_path)
    items = sample_corpus_facts(sem, epi, seed=7, n=20,
                                exclude_ids={"f00", "f01"}, budget=400)
    ids = {x["fact_id"] for x in items}
    assert "f00" not in ids and "f01" not in ids, "test-v1 ids must stay held out"
    assert "fsup" not in ids, "superseded facts excluded"
    assert 0 < len(items) <= 10
    for x in items:
        assert x["span"] and x["fact"]
        assert len(x["span"]) <= 400


def test_sample_deterministic(tmp_path):
    sem, epi = _mini_dbs(tmp_path)
    a = sample_corpus_facts(sem, epi, seed=7, n=5, exclude_ids=set(), budget=400)
    b = sample_corpus_facts(sem, epi, seed=7, n=5, exclude_ids=set(), budget=400)
    assert a == b


def test_swap_negatives_cross_topic(tmp_path):
    sem, epi = _mini_dbs(tmp_path)
    items = sample_corpus_facts(sem, epi, seed=7, n=10, exclude_ids=set(), budget=400)
    negs = make_swap_negatives(items, seed=7, n=4)
    assert 0 < len(negs) <= 4
    by_id = {x["fact_id"]: x for x in items}
    for ng in negs:
        host_id, donor_id = ng["fact_id"].split("<-")
        assert by_id[host_id.replace("swap:", "")]["topic"] != by_id[donor_id]["topic"]
        assert ng["fact"] == by_id[donor_id]["fact"], "donor proposition on host span"
        assert ng["span"] == by_id[host_id.replace("swap:", "")]["span"]


def test_load_labeled_jsonl_resume_and_soft_labels(tmp_path):
    p = tmp_path / "labels.jsonl"
    rows = [
        {"fact_id": "a", "fact": "fa", "span": "sa", "claude_score": 96.0},
        {"fact_id": "b", "fact": "fb", "span": "sb", "claude_score": 12.0},
        {"fact_id": "a", "fact": "fa", "span": "sa", "claude_score": 96.0},  # dup
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    done_ids, train_items = load_labeled_jsonl(p)
    assert done_ids == {"a", "b"}
    assert len(train_items) == 2, "duplicates collapsed"
    by = {x["fact_id"]: x for x in train_items}
    assert by["a"]["label"] == 0.96 and by["b"]["label"] == 0.12, "soft labels = score/100"
    assert by["a"]["kind"] == "corpus_claude"
    # binarized mode distills the claude admit DECISION at the given cut
    _, hard = load_labeled_jsonl(p, binarize_at=40.0)
    byh = {x["fact_id"]: x for x in hard}
    assert byh["a"]["label"] == 1.0 and byh["b"]["label"] == 0.0
