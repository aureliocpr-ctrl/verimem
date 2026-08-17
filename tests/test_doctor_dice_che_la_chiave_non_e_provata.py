"""Il referto dichiarava un provider llm senza dire che non l'aveva contattato.

`_autodetect_provider()` guarda i NOMI delle variabili d'ambiente: trova una
chiave **impostata**, non una chiave **valida**. Il referto però si limitava a::

    ✓ llm  provider auto-detected: openai

⇒ Una chiave scaduta, revocata o copiata male esce con la riga verde di una
funzionante, e chi legge `doctor` — il comando che il README prescrive per
verificare l'installazione — conclude che l'llm è a posto.

⚠️ **Qui la cura NON è accertare**, ed è la differenza rispetto agli altri due
casi curati lo stesso giorno (`moat-judge` guardava una cartella e poteva
guardarci meglio; `gateway` guardava un nome di file e poteva aprirlo). Provare
una chiave vuole una chiamata al provider: sta fuori dal budget di ~2 s che
`doctor` dichiara, fallirebbe da sola su una macchina air-gapped, e spenderebbe
soldi dell'operatore per una diagnosi. L'indizio è tutto ciò che si può avere a
costo zero ⇒ **la cura è non lasciar credere di aver fatto di più.**

📌 Il verdetto resta OK in entrambi i rami, e deve restarci: il README promette
due volte che l'llm non serve, e un avviso su una configurazione normale
trascinerebbe l'intero `doctor` a EXIT=1 su una macchina perfetta. Cambia
l'informazione, non lo stato.
"""
from __future__ import annotations

import pytest

from verimem.doctor import OK, run_doctor


def _llm(checks):
    return next(c for c in checks if c["name"] == "llm")


@pytest.fixture
def store(tmp_path, monkeypatch):
    d = tmp_path / "store"
    d.mkdir()
    for _env in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_env, str(d))
    return d


def test_un_provider_rilevato_dichiara_di_non_essere_stato_contattato(
        store, monkeypatch):
    """Il caso: la variabile c'è, e questo è tutto ciò che si sa."""
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: "openai")
    c = _llm(run_doctor())
    assert c["status"] == OK, (
        f"un provider rilevato non è un problema e non deve diventarlo: {c}")
    assert "openai" in c["detail"], c["detail"]
    assert "NOT contacted" in c["detail"], (
        f"il referto dichiara il provider senza dire che la chiave non è "
        f"stata provata: {c['detail']}. Una chiave revocata esce identica a "
        f"una funzionante")


def test_senza_provider_il_referto_non_promette_nulla_da_verificare(
        store, monkeypatch):
    """⚠️ POPOLAZIONE OPPOSTA. Senza di essa, «dillo» si soddisfa anche
    appiccicando la stessa frase ovunque: dove non c'è nessuna chiave, non c'è
    nessuna chiave non provata di cui avvisare."""
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: "mock")
    c = _llm(run_doctor())
    assert c["status"] == OK, c
    assert "no llm provider" in c["detail"], c["detail"]
    assert "NOT contacted" not in c["detail"], (
        f"avviso su una chiave che non esiste: {c['detail']}")
