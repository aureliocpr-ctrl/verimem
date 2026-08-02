"""Il README dichiarava un nome e ne insegnava un altro.

Riga 486: «every `VERIMEM_X` setting can also be written `ENGRAM_X`/`HIPPO_X`»
— cioè VERIMEM è il nome, gli altri sono alias di compatibilità. E poi tutti e
cinque gli esempi di configurazione usavano l'alias::

    ENGRAM_BAND_LLM=0        (riga 61)
    ENGRAM_SEMANTIC_CONFLICT=0   (92)
    ENGRAM_SUPERSEDE_SAME_SOURCE=0 (96)
    ENGRAM_MIN_RELEVANCE=auto    (139)
    ENGRAM_ANN_RECALL=0          (433)

Chi legge impara il nome deprecato, perché è l'unico che vede scritto. È la
forma già curata tre volte il 2026-08-02 — due righe dello stesso documento,
una nega quello che l'altra dichiara (`44b85a2f`, `842816a5`, `correct`).

Il bridge regge in tutte e cinque le direzioni, verificato dal vivo prima di
toccare il testo — `VERIMEM_X` arriva al lettore canonico, `ENGRAM_X` torna
indietro per l'introspezione, `HIPPO_*` regge ancora, e un valore esplicito su
un lato non viene sovrascritto dall'altro. Quindi cambiare gli ESEMPI non
rompe nessuna installazione: cambia solo quale nome impara chi legge oggi.

La sezione che SPIEGA la compatibilità deve continuare a nominare i vecchi
prefissi — è il suo lavoro. Il cricchetto distingue le due cose.
"""
from __future__ import annotations

import pathlib
import re

import pytest

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"

#: Un esempio è una riga che ASSEGNA un valore: `NOME=valore`. La prosa che
#: cita un prefisso senza assegnargli niente sta spiegando, non insegnando.
_ASSEGNA = re.compile(r"\b(ENGRAM|HIPPO)_[A-Z0-9_]+\s*=")

#: Le righe che spiegano la compatibilità DEVONO nominare i vecchi prefissi.
_SPIEGA_COMPAT = ("compatibility", "mirrored", "still work", "alias",
                  "back-compat", "backward")


def _righe_di_esempio() -> list[tuple[int, str]]:
    fuori = []
    for n, riga in enumerate(README.read_text(encoding="utf-8").splitlines(), 1):
        if not _ASSEGNA.search(riga):
            continue
        if any(k in riga.lower() for k in _SPIEGA_COMPAT):
            continue
        fuori.append((n, riga.strip()))
    return fuori


def test_gli_esempi_usano_il_nome_del_prodotto():
    fuori = _righe_di_esempio()
    assert not fuori, (
        "il README dichiara VERIMEM_* come nome e poi insegna il prefisso "
        "deprecato negli esempi:\n"
        + "\n".join(f"  riga {n}: {r[:90]}" for n, r in fuori))


def test_la_sezione_di_compatibilita_resta():
    """Controprova: la cura non deve cancellare la promessa di
    retrocompatibilità, che è ciò che tiene vive le installazioni esistenti."""
    testo = README.read_text(encoding="utf-8")
    assert "ENGRAM_" in testo, (
        "sparito ogni riferimento: chi ha ENGRAM_* nell'ambiente non trova "
        "più scritto da nessuna parte che continua a funzionare")
    assert re.search(r"VERIMEM_X.*ENGRAM_X|ENGRAM_X.*VERIMEM_X", testo), (
        "manca la riga che lega i due nomi")


def test_il_package_si_presenta_col_nome_giusto():
    """La prima riga del docstring di `verimem/__init__.py` è la prima cosa che
    legge chi apre il package o chiama `help(verimem)`."""
    import verimem
    prima = (verimem.__doc__ or "").strip().splitlines()[0]
    assert "verimem" in prima.lower(), (
        f"il package si presenta con un altro nome: {prima!r}")


@pytest.mark.parametrize("prefisso", ["VERIMEM_", "ENGRAM_", "HIPPO_"])
def test_il_bridge_regge_tutti_e_tre(prefisso, monkeypatch):
    """La cura sui testi vale solo se il nome insegnato funziona davvero, e se
    quelli vecchi non smettono."""
    from verimem import _compat
    for p in ("VERIMEM_", "ENGRAM_", "HIPPO_"):
        monkeypatch.delenv(p + "PROVA_PONTE", raising=False)
    monkeypatch.setenv(prefisso + "PROVA_PONTE", "42")
    _compat.init_env_aliases()
    import os
    assert os.environ.get("ENGRAM_PROVA_PONTE") == "42", (
        f"{prefisso}PROVA_PONTE non raggiunge il lettore canonico")
