"""Lo store e' UNO: due risolutori con precedenza opposta sono due store.

TROVATO il 2026-07-30 dal dogfooding in parallelo, che lo aveva letto come
«doctor ignora HIPPO_DATA_DIR». E' piu' largo: due funzioni risolvono la data
dir con precedenze diverse, e su una macchina dove ``ENGRAM_DATA_DIR`` e'
esportata nell'ambiente (questa) puntano a store DIVERSI.

    HIPPO_DATA_DIR=C:/tmp/isolato_prova, ENGRAM_DATA_DIR=C:\\Users\\aurel\\.engram

    _compat.data_dir()  -> C:\\Users\\aurel\\.engram      (produzione)
    Config.data_dir     -> C:\\tmp\\isolato_prova         (isolato)
    agent.semantic      -> C:\\tmp\\isolato_prova\\...    (isolato)

Il prodotto legge e scrive nello store isolato; **quattordici punti** in cinque
file passano invece da ``_compat.data_dir()`` — fra cui ``backup.py``, dove uno
store sbagliato non e' un messaggio sbagliato.

La parte istruttiva: ENTRAMBE le precedenze sono deliberate e documentate.
``config._data_root`` mette ``HIPPO_DATA_DIR`` per primo perche' e' l'handle
storico dell'isolamento nei test, e il suo commento descrive esattamente questa
macchina — «a machine whose shell exports ENGRAM_DATA_DIR (the maintainer's)
must not override a test's explicit HIPPO_DATA_DIR». ``_compat.data_dir`` fa
vincere il primo fra VERIMEM/ENGRAM/HIPPO. Due scelte ragionate, prese in due
posti, incompatibili: nessuno ha mai confrontato i due elenchi.

CURA: un risolutore solo (``_compat._env_data_dir``), usato da entrambi. E
quando piu' alias puntano a posti DIVERSI il prodotto lo dice una volta per
processo, invece di scegliere in silenzio — la scelta silenziosa e' cio' che ha
prodotto la divergenza.
"""
from __future__ import annotations

import os

import pytest

ALIAS = ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR")


@pytest.fixture(autouse=True)
def _ambiente_pulito():
    """Parte da un ambiente senza alias e lo rimette com'era.

    Non usa ``monkeypatch`` perche' l'ordine dei teardown conta: il suo gira
    DOPO quello dei fixture che lo richiedono, e qui serve che l'env sia
    integro prima che finisca il file.
    """
    salvato = {k: os.environ.get(k) for k in ALIAS}
    for k in ALIAS:
        os.environ.pop(k, None)
    try:
        yield
    finally:
        for k, v in salvato.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _due_risolutori(tmp_path):
    """NIENTE ``importlib.reload``: ``_data_root()`` rilegge l'ambiente a ogni
    chiamata, quindi il reload non serviva — e ricostruiva ``CONFIG`` (che e'
    congelato alla costruzione) sull'ambiente del momento, lasciandolo puntato
    a una ``tmp_path`` PER TUTTA LA SUITE. Due test verdi da soli cadevano
    dentro la suite, e sembravano difetti del prodotto: erano il mio attrezzo
    di misura lasciato acceso."""
    from verimem import _compat, config
    return _compat.data_dir(), config._data_root()


def test_i_due_risolutori_concordano_sempre(monkeypatch, tmp_path):
    """Il caso vero: ENGRAM esportata nell'ambiente, l'utente isola con HIPPO."""
    isolato = tmp_path / "isolato"
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "produzione"))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(isolato))
    a, b = _due_risolutori(tmp_path)
    assert a == b, (
        f"due risolutori, due store: _compat -> {a}, Config -> {b}. "
        f"Le superfici diagnostiche guardano un posto e il prodotto un altro")
    assert a.resolve() == isolato.resolve(), (
        "l'isolamento esplicito deve vincere sull'ambiente della shell — e' la "
        "ragione documentata in config._data_root")


def test_ogni_alias_da_solo_funziona(monkeypatch, tmp_path):
    for nome in ALIAS:
        for k in ALIAS:
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv(nome, str(tmp_path / nome))
        a, b = _due_risolutori(tmp_path)
        assert a == b == (tmp_path / nome).resolve(), (
            f"{nome} da sola non e' onorata da entrambi: {a} vs {b}")


def test_il_mirror_non_scavalca_chi_imposta_ENGRAM(monkeypatch, tmp_path):
    """Il caso che mi e' sfuggito e che ha trovato la suite intera.

    ``init_env_aliases`` CREA ``VERIMEM_DATA_DIR`` all'import, copiandola dal
    valore ereditato dalla shell. Se quel mirror sta davanti a ENGRAM nella
    precedenza, chi imposta ``ENGRAM_DATA_DIR`` — il quickstart del README, che
    la mette in .mcp.json — si vede scavalcare da una copia del valore che
    voleva sostituire. I test mirati non lo vedevano: partono da un ambiente
    pulito, dove il mirror non c'e'.
    """
    from verimem import _compat
    monkeypatch.setattr(_compat, "_avvisato_alias_discordi", True, raising=False)
    monkeypatch.setenv("VERIMEM_DATA_DIR", str(tmp_path / "vecchio_mirror"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "voluto"))
    a, b = _due_risolutori(tmp_path)
    assert a == b == (tmp_path / "voluto").resolve(), (
        f"il mirror ha scavalcato la variabile impostata apposta: {a}")


def test_senza_env_il_comportamento_storico_resta(monkeypatch, tmp_path):
    """Nessun alias: decide il resolver storico (~/.verimem, ~/.engram, ...).
    La cura non deve cambiare dove atterra un'installazione esistente."""
    a, b = _due_risolutori(tmp_path)
    assert a == b
    assert a.name in {".verimem", ".engram", ".hippoagent"}, a


def test_alias_discordi_vengono_DICHIARATI(monkeypatch, tmp_path, recwarn):
    """Scegliere in silenzio fra due store e' cio' che ha prodotto il difetto:
    chi ha impostato due alias diversi deve sapere quale ha vinto."""
    from verimem import _compat
    monkeypatch.setattr(_compat, "_avvisato_alias_discordi", False,
                        raising=False)
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "uno"))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "due"))
    with pytest.warns(RuntimeWarning, match="DATA_DIR"):
        _compat.data_dir()


def test_alias_concordi_non_avvisano(monkeypatch, tmp_path):
    """Il mirror di compatibilita' popola tutti gli alias con lo STESSO valore:
    quello e' il caso normale e non deve produrre rumore."""
    from verimem import _compat
    monkeypatch.setattr(_compat, "_avvisato_alias_discordi", False,
                        raising=False)
    uguale = str(tmp_path / "stesso")
    monkeypatch.setenv("ENGRAM_DATA_DIR", uguale)
    monkeypatch.setenv("HIPPO_DATA_DIR", uguale)
    monkeypatch.setenv("VERIMEM_DATA_DIR", uguale)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _compat.data_dir().resolve() == (tmp_path / "stesso").resolve()
