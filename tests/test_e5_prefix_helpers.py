"""``embedding.as_query`` / ``as_passage``: prefissi e5 model-gated.

I modelli e5 (intfloat/*e5*) sono addestrati con i prefissi ``query: ``/``passage: ``
sui due lati (ricerca vs documento) — senza, il recall degrada. Gli altri modelli
(MiniLM, paraphrase-multilingual) NON usano prefissi. Gli helper sono il gate: e5 ->
prefisso, altri -> passthrough (backward-compat zero-impatto sul flip L12 attuale).

Subprocess perche' ``CONFIG`` e' ``frozen`` (il modello si fissa a costruzione, da
``HIPPO_EMBEDDING_MODEL``). Ermetico, nessun load modello.
"""
from __future__ import annotations

import subprocess
import sys


def _run(model: str, expr: str) -> str:
    code = (
        f"import os; os.environ['HIPPO_EMBEDDING_MODEL']={model!r}; "
        f"from engram import embedding; print(repr({expr}))"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"stderr={r.stderr[-600:]!r}"
    return r.stdout.strip()


def test_e5_model_adds_query_and_passage_prefixes():
    m = "intfloat/multilingual-e5-base"
    assert _run(m, "embedding.as_query('gatto')") == "'query: gatto'"
    assert _run(m, "embedding.as_passage('gatto')") == "'passage: gatto'"


def test_non_e5_model_is_passthrough():
    m = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert _run(m, "embedding.as_query('gatto')") == "'gatto'"
    assert _run(m, "embedding.as_passage('gatto')") == "'gatto'"
