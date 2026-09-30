"""The parity of the int8 embedder on the product's corpus (benchmark/judge_v3/parita_corpus_onnx.py): the
parts that run anywhere.

The run itself reads the real store and needs the exported models, so it is measured by the script and
written in its output. What is checked here decides what that run reads and how it counts:

1. it reads only the rows whose vector the active model wrote (the model's name and its size), and not
   the rows a later fact has replaced: a MiniLM vector of 384 numbers or a stale row is not a reference;
2. it opens the store read-only: a write through its connection fails;
3. recall@k over the corpus leaves the query's own fact out, or every query finds itself first.

No model and no real store: the store is a small SQLite file with the columns the script reads.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

CARTELLA = Path(__file__).resolve().parents[1] / "benchmark" / "judge_v3"
sys.path.insert(0, str(CARTELLA))

MODELLO = "intfloat/multilingual-e5-base"


def _store(percorso: Path) -> Path:
    conn = sqlite3.connect(percorso)
    conn.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT NOT NULL, embedding BLOB NOT NULL, "
        "embedding_model TEXT, superseded_by TEXT)"
    )
    righe = [
        ("buono-1", "primo fatto", np.full(768, 0.1, dtype=np.float32).tobytes(), MODELLO, None),
        ("buono-2", "secondo fatto", np.full(768, 0.2, dtype=np.float32).tobytes(), MODELLO, None),
        ("minilm", "vettore vecchio", np.full(384, 0.3, dtype=np.float32).tobytes(), None, None),
        ("altro-modello", "altro spazio", np.full(768, 0.4, dtype=np.float32).tobytes(), "altro/modello", None),
        ("sostituito", "fatto sostituito", np.full(768, 0.5, dtype=np.float32).tobytes(), MODELLO, "buono-1"),
        ("vuoto", "vettore vuoto", b"", MODELLO, None),
    ]
    conn.executemany("INSERT INTO facts VALUES (?, ?, ?, ?, ?)", righe)
    conn.commit()
    conn.close()
    return percorso


def test_it_reads_only_the_live_rows_the_active_model_wrote(tmp_path: Path) -> None:
    import parita_corpus_onnx

    ids, testi, vettori = parita_corpus_onnx.leggi_corpus(_store(tmp_path / "semantic.db"), MODELLO, 768)
    assert ids == ["buono-1", "buono-2"]
    assert testi == ["primo fatto", "secondo fatto"]
    assert vettori.shape == (2, 768) and vettori.dtype == np.float32
    assert np.allclose(vettori[1], 0.2)


def test_the_store_is_opened_read_only(tmp_path: Path) -> None:
    import parita_corpus_onnx

    percorso = _store(tmp_path / "semantic.db")
    conn = parita_corpus_onnx.apri_in_sola_lettura(percorso)
    try:
        # POSITIVE CONTROL: the connection reads
        assert conn.execute("SELECT count(*) FROM facts").fetchone()[0] == 6
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM facts")
    finally:
        conn.close()
    assert sqlite3.connect(percorso).execute("SELECT count(*) FROM facts").fetchone()[0] == 6


def _numeri(coseno_mediano=0.995, p01=0.985, r10=0.97, r1=0.93, spostamento=0.01, r10_ricodifica=0.97, controllo=1.0):
    return {
        "C_controllo_fp32_contro_memorizzati": {"minimo": controllo},
        "per_file": {"model_int8.onnx": {
            "1_coseno_onnx_contro_memorizzati": {"mediano": coseno_mediano, "p01": p01},
            "2_richiamo_senza_ricodifica": {"1": r1, "10": r10},
            "2_spostamento_del_punteggio_top1": {"p99": spostamento},
            "3_richiamo_con_ricodifica": {"10": r10_ricodifica},
        }},
    }


def test_the_verdict_applies_the_thresholds_fixed_before_the_run() -> None:
    import parita_corpus_onnx

    assert parita_corpus_onnx.verdetto(_numeri())["model_int8.onnx"] == "regge senza ricodifica"
    # the cosine or the recall under its threshold: the price is re-encoding, if the re-encoded recall holds
    assert parita_corpus_onnx.verdetto(_numeri(coseno_mediano=0.98))["model_int8.onnx"] == "regge con la ricodifica"
    assert parita_corpus_onnx.verdetto(_numeri(r1=0.85))["model_int8.onnx"] == "regge con la ricodifica"
    assert parita_corpus_onnx.verdetto(_numeri(spostamento=0.03))["model_int8.onnx"] == "regge con la ricodifica"
    assert parita_corpus_onnx.verdetto(_numeri(r10=0.9, r10_ricodifica=0.9))["model_int8.onnx"] == "non regge"
    # the control first: stored vectors that are not the product's encode make the rest unreadable
    assert parita_corpus_onnx.verdetto(_numeri(controllo=0.99)) == {"controllo": "non regge: ci si ferma"}


def test_recall_over_the_corpus_leaves_the_query_fact_out() -> None:
    import parita_corpus_onnx

    # each query is fact 0 and fact 1 of the corpus, which they match best: left in, they would come first
    rif = np.array([[1.0, 0.2, 0.9, 0.8], [0.3, 1.0, 0.1, 0.7]])
    alt = np.array([[1.0, 0.2, 0.8, 0.9], [0.3, 1.0, 0.1, 0.7]])
    # without themselves: query 0 has top-1 {2} against {3}, query 1 has {3} against {3}
    assert parita_corpus_onnx.richiamo_senza_se_stesso(rif, alt, [0, 1], k=1) == pytest.approx(0.5)
    assert parita_corpus_onnx.richiamo_senza_se_stesso(rif, alt, [0, 1], k=2) == pytest.approx(1.0)
    # the inputs are not modified: the caller's similarity rows stay as they were
    assert rif[0, 0] == 1.0 and alt[1, 1] == 1.0
