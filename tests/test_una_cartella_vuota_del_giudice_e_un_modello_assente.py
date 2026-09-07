"""Una cartella del giudice ESISTENTE MA VUOTA e' un modello ASSENTE, non rotto.

Misurato il 07/09 (banco T1 del lead, venv nuovo col tip 2b82497f, env pulito,
``ENGRAM_LOCAL_GATE_MODEL`` su una cartella creata e vuota):

    flow.warmup  phase=start
    flow.warmup  phase=failed  elapsed_ms=17322  error=ValueError
                 reason="Couldn't instantiate the backend tokenizer ..."
    flow.write   grounding_score=None  judged=False
    admitted ... L4-skipped — "the local model is on disk but could not be
                 loaded in this process (the failure is cached for its lifetime)"

Nessun download, e la ricevuta dice «on disk» di una cartella senza un file.
Con la STESSA cartella ma INESISTENTE il prodotto scarica 712 MB e giudica
(99,85 in 184 s). La differenza sta in una riga di :class:`LocalGroundingJudge`:
il modello si procura «solo se la cartella NON ESISTE». Ma una cartella vuota, o
con i soli metadati (l'estrazione interrotta del 17/08 raccontata in
``_esito_dell_installazione``), e' cio' che ``from_pretrained`` non puo'
caricare: e' ASSENTE. Il criterio giusto e' quello che ``ensure_gate_model``
usa gia' per decidere di NON riscaricare: config.json E i pesi. Due criteri per
«presente» in due punti (classe ①: una copia invece della superficie unica).

Il vincolo di progetto resta: un modello CORROTTO (file presenti, carico che
fallisce) non si riscarica, perche' ripagherebbe 746 MB a ogni scrittura.
La seconda cella lo presidia.

Le celle iniettano il download e lo scorer: nessuna rete, nessun modello.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem import local_grounding as lg


class _Scorer:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, coppie, **kw):  # noqa: ANN001
        # lo scorer vero riceve una LISTA di coppie e rende una lista
        self.calls += 1
        return [0.97 for _ in coppie]


def _scrivi_un_modello_finto(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text("{}", encoding="utf-8")
    (d / "model.safetensors").write_bytes(b"pesi-finti")


@pytest.fixture
def procura(monkeypatch):
    """Il download e' iniettato: scrive un modello finto e conta le chiamate.
    Lo scorer finto carica SOLO se i file ci sono, come ``from_pretrained``."""
    stato = {"download": 0}

    def _ensure(model_dir=None, **kw):  # noqa: ANN001
        stato["download"] += 1
        _scrivi_un_modello_finto(Path(model_dir))
        return True, "gate model installed (finto)"

    def _make(model_dir, **kw):  # noqa: ANN001
        d = Path(model_dir)
        if not (lg._holds_a_model(d) and lg.holds_the_weights(d)):
            raise ValueError("Couldn't instantiate the backend tokenizer (finto)")
        return _Scorer()

    monkeypatch.setattr(lg, "ensure_gate_model", _ensure)
    monkeypatch.setattr(lg, "make_finetuned_scorer", _make)
    monkeypatch.setattr(lg, "_download_disattivato", lambda: False)
    monkeypatch.setattr(lg, "annuncia_download_del_giudice", lambda *a, **k: None)
    return stato


def test_CONTROLLO_cartella_inesistente_si_procura_e_carica(tmp_path, procura):
    """Il caso che gia' funziona (giro 2 del banco): il controllo positivo."""
    d = tmp_path / "non_esiste"
    j = lg.LocalGroundingJudge(model_dir=d)
    assert j.score("la fonte", "il fatto") is not None
    assert procura["download"] == 1
    assert getattr(j, "_load_failed", False) is False


def test_IL_ROSSO_cartella_esistente_ma_vuota_e_un_modello_assente(tmp_path, procura):
    """Giro 1 del banco: oggi nessun download, fallimento in cache, scrittura
    non giudicata. Deve procurare come se la cartella non esistesse."""
    d = tmp_path / "vuota"
    d.mkdir()
    j = lg.LocalGroundingJudge(model_dir=d)
    esito = j.score("la fonte", "il fatto")
    assert procura["download"] == 1, (
        "una cartella vuota non e' un modello: va procurato, non caricato")
    assert esito is not None
    assert getattr(j, "_load_failed", False) is False


def test_cartella_con_i_soli_metadati_e_un_modello_assente(tmp_path, procura):
    """L'estrazione interrotta del 17/08: config.json c'e', i pesi no."""
    d = tmp_path / "meta"
    d.mkdir()
    (d / "config.json").write_text("{}", encoding="utf-8")
    j = lg.LocalGroundingJudge(model_dir=d)
    assert j.score("la fonte", "il fatto") is not None
    assert procura["download"] == 1


def test_un_modello_CORROTTO_non_si_riscarica(tmp_path, monkeypatch, procura):
    """Il vincolo di progetto: file presenti e carico che fallisce = rotto,
    e un modello rotto non ripaga 746 MB a ogni scrittura."""
    d = tmp_path / "corrotto"
    _scrivi_un_modello_finto(d)

    def _make_rotto(model_dir, **kw):  # noqa: ANN001
        raise RuntimeError("pesi corrotti (finto)")

    monkeypatch.setattr(lg, "make_finetuned_scorer", _make_rotto)
    j = lg.LocalGroundingJudge(model_dir=d)
    with pytest.raises(Exception):
        j.score("la fonte", "il fatto")
    assert procura["download"] == 0
    assert getattr(j, "_load_failed", False) is True
