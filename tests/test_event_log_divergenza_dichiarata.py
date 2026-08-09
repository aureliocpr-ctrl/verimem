"""Se il log finisce lontano dallo store, il prodotto lo DICE.

`EVENT_LOG_PATH` è calcolato all'import: chi setta `HIPPO_DATA_DIR` DOPO
aver importato ottiene fatti nella cartella isolata ed eventi nel corpus di
casa. Misurato il 2026-08-05:

    data_dir()      -> C:/…/Temp/tmpXXXX      (segue l'env: ricalcolata)
    EVENT_LOG_PATH  -> C:/Users/…/.engram     (congelata all'import)

È la stessa causa che ha fatto finire 210 fatti di laboratorio nel corpus
di produzione (ws5): l'ORDINE fra import ed env decide, e nessuno lo
dichiara. Documentarlo non basta — chi sbaglia l'ordine non sta leggendo la
docstring proprio in quel momento.

Contratto pinnato qui: al primo evento scritto in una posizione che NON
corrisponde alla data dir corrente, il modulo avvisa una volta sola. Non
sposta il file (spostarlo a metà corsa spezzerebbe i lettori già attaccati)
e non avvisa quando la divergenza è una scelta esplicita
(`ENGRAM_EVENT_LOG`) o quando non c'è.
"""
from __future__ import annotations

import warnings

import pytest

from verimem import event_jsonl_log as ejl


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(ejl, "_DIVERGENZA_AVVISATA", False, raising=False)


def test_avvisa_quando_il_log_e_lontano_dalla_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ejl, "EVENT_LOG_PATH", tmp_path / "altrove" / "events.jsonl")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("ENGRAM_EVENT_LOG", raising=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ejl.append_event("flow.test", {"x": 1})
    msgs = [str(x.message) for x in w]
    assert any("events.jsonl" in m and "data dir" in m.lower() for m in msgs), msgs


def test_avvisa_UNA_SOLA_VOLTA(tmp_path, monkeypatch):
    """Un avviso per evento sarebbe rumore su un log che scrive 330 righe
    l'ora: chi non l'ha letto la prima volta non lo legge alla millesima."""
    monkeypatch.setattr(ejl, "EVENT_LOG_PATH", tmp_path / "altrove" / "events.jsonl")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("ENGRAM_EVENT_LOG", raising=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        for _ in range(5):
            ejl.append_event("flow.test", {"x": 1})
    # solo i MIEI: `data_dir()` emette il proprio avviso quando gli alias
    # dell'env non concordano, ed è legittimo — contarlo qui misurerebbe
    # un'altra funzione (sbagliato nel primo giro del banco)
    miei = [x for x in w if "log eventi" in str(x.message)]
    assert len(miei) == 1, [str(x.message) for x in w]


def test_niente_avviso_se_coincidono(tmp_path, monkeypatch):
    monkeypatch.setattr(ejl, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ENGRAM_EVENT_LOG", raising=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ejl.append_event("flow.test", {"x": 1})
    miei = [x for x in w if "log eventi" in str(x.message)]
    assert not miei, [str(x.message) for x in w]


def test_niente_avviso_se_la_divergenza_e_una_scelta(tmp_path, monkeypatch):
    """`ENGRAM_EVENT_LOG` è un override esplicito: avvisare chi ha scelto
    sarebbe l'errore opposto — il rumore che fa ignorare gli avvisi veri."""
    monkeypatch.setattr(ejl, "EVENT_LOG_PATH", tmp_path / "altrove" / "events.jsonl")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(tmp_path / "altrove" / "events.jsonl"))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ejl.append_event("flow.test", {"x": 1})
    miei = [x for x in w if "log eventi" in str(x.message)]
    assert not miei, [str(x.message) for x in w]


def test_l_evento_viene_scritto_comunque(tmp_path, monkeypatch):
    """L'avviso non è un blocco: l'osservabilità non rompe mai il path."""
    log = tmp_path / "altrove" / "events.jsonl"
    monkeypatch.setattr(ejl, "EVENT_LOG_PATH", log)
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("ENGRAM_EVENT_LOG", raising=False)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        ejl.append_event("flow.test", {"x": 1})
    assert log.exists() and "flow.test" in log.read_text(encoding="utf-8")
