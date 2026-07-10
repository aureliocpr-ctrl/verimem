"""Pure-function tests for the QuALITY F1 harness (task #22, corpus #3).

Model-free logic: article dedup, question->article mapping, stable ids, and
the whole-vs-chunked piece-count difference that S2 rests on. The end-to-end
retrieval is verified by the run itself (needs the embedder).
"""
from __future__ import annotations

import pandas as pd

from engram.chunking import chunk_text
from benchmark.external_f1_quality import load_quality


def _parquet(tmp_path):
    long_art = "Para one. " + ("filler sentence. " * 400)  # >> 1000 chars
    df = pd.DataFrame([
        {"article": long_art, "question": "q1?", "options": ["a"], "answer": 0},
        {"article": long_art, "question": "q2?", "options": ["a"], "answer": 0},
        {"article": "Short article.", "question": "q3?", "options": ["a"], "answer": 0},
    ])
    p = tmp_path / "q.parquet"
    df.to_parquet(p)
    return p, long_art


def test_load_dedups_articles_keeps_all_questions(tmp_path):
    p, _ = _parquet(tmp_path)
    articles, questions = load_quality(p)
    assert len(articles) == 2, "same article text across questions = one entry"
    assert len(questions) == 3, "every question row is kept"


def test_questions_point_at_their_article(tmp_path):
    p, _ = _parquet(tmp_path)
    articles, questions = load_quality(p)
    assert questions[0]["article_id"] == questions[1]["article_id"]
    assert questions[2]["article_id"] != questions[0]["article_id"]
    assert all(q["article_id"] in articles for q in questions)


def test_chunked_yields_more_pieces_than_whole(tmp_path):
    _, long_art = _parquet(tmp_path)
    pieces = chunk_text(long_art, chunk_size=1000, overlap=150)
    assert len(pieces) > 1, (
        "a >1000-char article must chunk into multiple retrievable pieces "
        "(whole mode would embed only the truncated head — S2)")
