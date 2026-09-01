"""`engram warmup` — pre-load (and download on first run) the embedding model
with clear feedback.

Mainstream first-run gap: the embedding model (~1.1 GB e5-base) downloads
SILENTLY on the first recall, so a new user thinks recall is broken while it is
actually fetching weights in the background. `engram warmup` makes that step
explicit + observable (and is the natural pre-bake step in CI / Docker build).
⚠️ ISOLAMENTO OBBLIGATORIO (aggiunto il 2026-09-02): `warmup` ora tocca anche il
PAVIMENTO DI RILEVANZA, quindi apre uno store e puo' scriverne il file
persistito. Senza `isolated_corpus` questi test scriverebbero sullo store REALE
di chi li esegue — e sotto pytest l'embedder e' uno stub SHA-256, quindi il
valore scritto sarebbe spazzatura piazzata sul corpus vero. La fixture NON e'
autouse: va chiesta.
"""
from __future__ import annotations

import numpy as np
from typer.testing import CliRunner

import verimem.cli as cli
import verimem.embedding as emb

runner = CliRunner()


def test_warmup_loads_model_and_reports_ready(monkeypatch, isolated_corpus):
    loaded = {"v": False}

    def fake_model():
        loaded["v"] = True
        return object()

    monkeypatch.setattr(emb, "_model", fake_model)
    monkeypatch.setattr(emb, "encode", lambda *_a, **_k: np.ones(8, dtype=np.float32))

    res = runner.invoke(cli.app, ["warmup", "--no-daemon"])

    assert res.exit_code == 0, res.output
    assert loaded["v"] is True, "warmup must trigger the in-process model load (the download)"
    assert "ready" in res.output.lower()


def test_warmup_reports_failure_clearly_and_exits_nonzero(monkeypatch, isolated_corpus):
    def boom():
        raise RuntimeError("model not cached and HF_HUB_OFFLINE=1")

    monkeypatch.setattr(emb, "_model", boom)

    res = runner.invoke(cli.app, ["warmup", "--no-daemon"])

    assert res.exit_code == 1
    out = res.output.lower()
    assert "fail" in out or "✗" in res.output
    # actionable hint for the most common cause (offline + not cached)
    assert "offline" in out


def test_il_warmup_TOCCA_il_pavimento_e_lo_DICE(monkeypatch, isolated_corpus):
    """Il pavimento di rilevanza e' l'ultimo costo capace di smentire la riga
    finale di questo comando («recall will be instant»), quindi `warmup` lo
    controlla e lo rinfresca se il corpus e' cresciuto.

    ⚠️ QUESTA CELLA ESISTE PERCHE' QUEL CODICE STA DENTRO UN `except` CHE
    INGOIA TUTTO. Un blocco che fallisce li' — un nome sbagliato, un import
    spostato — stampa una riga «skipped» e prosegue: sarebbe una capacita'
    accesa e mai eseguita, con l'aria di funzionare. Verificare che la riga
    compaia NON basta: si verifica anche che non sia la riga della resa.

    🔑 E dimostra, di rimbalzo, perche' `isolated_corpus` e' obbligatorio qui:
    se il comando arriva davvero al pavimento, allora APRE uno store e puo'
    scriverne il file — senza isolamento sarebbe quello vero di chi esegue.
    """
    monkeypatch.setattr(emb, "_model", lambda: object())
    monkeypatch.setattr(emb, "encode",
                        lambda *_a, **_k: np.ones(8, dtype=np.float32))

    res = runner.invoke(cli.app, ["warmup", "--no-daemon", "--no-gate"])

    assert res.exit_code == 0, res.output
    basso = res.output.lower()
    assert "relevance floor" in basso, (
        f"warmup non nomina il pavimento: il blocco non e' stato eseguito o "
        f"e' morto prima\n{res.output}")
    assert "relevance floor skipped" not in basso, (
        f"il blocco del pavimento e' fallito e l'except l'ha ingoiato — la "
        f"capacita' c'e' solo all'apparenza\n{res.output}")
