"""`verimem warmup` davanti a un download incompleto: nomina il file, ritenta una volta.

MISURATO IL 29/09 nella CI (job ubuntu di #151, cache dei modelli vuota): il file
`1_Pooling/config.json` di intfloat/multilingual-e5-base non e' arrivato dall'Hub,
sentence-transformers 6.1.0 ha risposto «TypeError: Pooling.__init__() missing 1
required positional argument: 'embedding_dimension'», e il comando ha detto::

    Most common cause: running offline with the model not cached. Unset
    VERIMEM_OFFLINE / HIPPO_OFFLINE / HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE ...

su una macchina ONLINE, con nessuna di quelle variabili accese. La diagnosi mandava a
spegnere un interruttore spento. Lo stesso job, 55 minuti dopo sul main, ha scaricato
lo stesso modello senza errori: il file mancante era un colpo di rete, non la versione.

LA CURA: se un interruttore offline e' ACCESO lo si nomina (ed e' la causa); se no si
nominano i file dei moduli che la cache non ha, si ritenta UNA volta, e se cade ancora
si dice che l'installazione e' a posto e che l'Hub non ha servito quel file. La cosa
veloce sarebbe stata rilanciare il job: va bene per la CI, e lascia a chi installa una
diagnosi sbagliata.

IL BANCO: una cache dell'Hub finta, con un modello sentence-transformers che dichiara
tre moduli (Transformer alla radice, Pooling in 1_Pooling, Normalize in 2_Normalize) e
a cui manca solo `1_Pooling/config.json`. Normalize non ha file per costruzione, e non
deve essere nominato.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest
from typer.testing import CliRunner

import verimem.cli as cli
import verimem.embedding as emb

runner = CliRunner()
MODELLO = "acme/modello-finto"
REVISIONE = "0" * 40
ERRORE_DEL_29 = TypeError(
    "Pooling.__init__() missing 1 required positional argument: 'embedding_dimension'")


@pytest.fixture()
def cache_senza_pooling(tmp_path, monkeypatch):
    """La cache dell'Hub come la lascia un download a cui e' mancato un file."""
    radice = tmp_path / "hub" / ("models--" + MODELLO.replace("/", "--"))
    (radice / "refs").mkdir(parents=True)
    (radice / "refs" / "main").write_text(REVISIONE, encoding="utf-8")
    istantanea = radice / "snapshots" / REVISIONE
    istantanea.mkdir(parents=True)
    (istantanea / "modules.json").write_text(json.dumps([
        {"idx": 0, "name": "0", "path": "", "type": "sentence_transformers.models.Transformer"},
        {"idx": 1, "name": "1", "path": "1_Pooling", "type": "sentence_transformers.models.Pooling"},
        {"idx": 2, "name": "2", "path": "2_Normalize",
         "type": "sentence_transformers.models.Normalize"},
    ]), encoding="utf-8")
    (istantanea / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    from verimem.airgap import _OFFLINE_FLAGS
    for variabile in _OFFLINE_FLAGS:  # il conftest accende HIPPO_OFFLINE: qui si e' online
        monkeypatch.delenv(variabile, raising=False)
    from verimem.config import CONFIG
    prima = CONFIG.embedding_model
    object.__setattr__(CONFIG, "embedding_model", MODELLO)
    yield
    object.__setattr__(CONFIG, "embedding_model", prima)


def test_controllo_la_cache_finta_e_quella_di_un_download_a_meta(cache_senza_pooling):
    """Il banco regge da solo: l'Hub vede modules.json e non vede il file del pooling."""
    from huggingface_hub import try_to_load_from_cache
    cache = os.environ["HF_HUB_CACHE"]
    assert isinstance(try_to_load_from_cache(MODELLO, "modules.json", cache_dir=cache), str)
    assert not isinstance(
        try_to_load_from_cache(MODELLO, "1_Pooling/config.json", cache_dir=cache), str)


def test_il_warmup_nomina_il_file_mancante_e_non_dice_offline(
        cache_senza_pooling, monkeypatch, isolated_corpus):
    chiamate = []

    def carica():
        chiamate.append(1)
        raise ERRORE_DEL_29

    monkeypatch.setattr(emb, "_model", carica)
    res = runner.invoke(cli.app, ["warmup", "--no-daemon", "--no-gate"])
    assert res.exit_code == 1, res.output
    assert "1_Pooling/config.json" in res.output, (
        f"il comando non nomina il file che non e' arrivato:\n{res.output}")
    assert "2_Normalize" not in res.output, (
        f"Normalize non ha file per costruzione: nominarlo e' una diagnosi falsa\n{res.output}")
    assert "running offline" not in res.output.lower(), (
        f"su una macchina online il comando dice ancora «running offline»:\n{res.output}")
    assert len(chiamate) == 2, f"il caricamento va ritentato UNA volta: chiamate={len(chiamate)}"


def test_il_warmup_ritenta_una_volta_e_se_riesce_va_avanti(
        cache_senza_pooling, monkeypatch, isolated_corpus):
    chiamate = []

    def carica():
        chiamate.append(1)
        if len(chiamate) == 1:
            raise ERRORE_DEL_29
        return object()

    monkeypatch.setattr(emb, "_model", carica)
    monkeypatch.setattr(emb, "encode", lambda *_a, **_k: np.ones(8, dtype=np.float32))
    res = runner.invoke(cli.app, ["warmup", "--no-daemon", "--no-gate"])
    assert res.exit_code == 0, res.output
    assert "model ready" in res.output, res.output
    assert len(chiamate) == 2, f"chiamate={len(chiamate)}"


def test_con_un_interruttore_offline_acceso_la_causa_e_quello(
        cache_senza_pooling, monkeypatch, isolated_corpus):
    """Quando l'interruttore c'e', «offline» E' la diagnosi giusta, e non si ritenta."""
    chiamate = []

    def carica():
        chiamate.append(1)
        raise ERRORE_DEL_29

    monkeypatch.setattr(emb, "_model", carica)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    res = runner.invoke(cli.app, ["warmup", "--no-daemon", "--no-gate"])
    assert res.exit_code == 1, res.output
    assert "HF_HUB_OFFLINE" in res.output, res.output
    assert len(chiamate) == 1, f"con l'interruttore acceso ritentare e' inutile: {len(chiamate)}"
