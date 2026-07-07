"""`verimem index <file>` + `verimem search-docs <query>` — the document RAG
(roadmap #1) from the command line. Hermetic: fake embedder, tmp index DB."""
from __future__ import annotations

import math
import re

import pytest
from typer.testing import CliRunner

import engram.document_index as di
from engram.cli import app

runner = CliRunner()


class _FakeEmbedder:
    DIM = 32

    def encode(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


@pytest.fixture(autouse=True)
def _iso(monkeypatch, tmp_path):
    monkeypatch.setenv("HIPPO_DOCINDEX_DB", str(tmp_path / "docidx.db"))
    monkeypatch.setattr(di, "_DefaultEmbedder", _FakeEmbedder)


def test_index_then_search_with_citation(tmp_path):
    f = tmp_path / "manuale.txt"
    f.write_text("Ricette varie di cucina. " * 10 +
                 "Il condensatore zorbium richiede calibrazione trimestrale. " +
                 "Altre note sparse. " * 10, encoding="utf-8")

    r = runner.invoke(app, ["index", str(f)])
    assert r.exit_code == 0, r.output
    assert "1" in r.output  # chunks indexed / version

    r2 = runner.invoke(app, ["search-docs", "calibrazione zorbium", "-k", "3"])
    assert r2.exit_code == 0, r2.output
    assert "zorbium" in r2.output.lower()
    assert "manuale.txt" in r2.output  # citation: the source file is shown


def test_reindex_is_idempotent(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("Contenuto stabile che non cambia mai. " * 12, encoding="utf-8")
    assert runner.invoke(app, ["index", str(f)]).exit_code == 0
    r = runner.invoke(app, ["index", str(f)])
    assert r.exit_code == 0
    assert "unchanged" in r.output.lower() or "0" in r.output


def test_index_missing_file_exits_1(tmp_path):
    r = runner.invoke(app, ["index", str(tmp_path / "manca.pdf")])
    assert r.exit_code == 1
    assert "not found" in r.output.lower() or "non trovato" in r.output.lower()


def test_search_docs_empty_index_says_so():
    r = runner.invoke(app, ["search-docs", "qualsiasi cosa"])
    assert r.exit_code == 0
    assert "no" in r.output.lower() or "0" in r.output
