"""Riga 3 del tabellone: la ricevuta dice QUALE giudice ha deciso, con la sua versione.

La promessa (README, quickstart: «the local CE is the judge»; invarianti I1 e I5): chi
legge una scrittura ammessa deve poter sapere quale artefatto l'ha giudicata. Fino a
questa cura `adjudication.judge.version` era scritto `None` a mano in
`_judge_of_record_dict`, e il suo docstring rimandava l'impronta «a un seguito»; il
tabellone dal wheel (`accettazione/test_riga_3_...`) lo legge e restava rosso.

La versione e' un'impronta del CONTENUTO che il giudice carica (i pesi, poi
gate_config.json con la soglia), non il nome della cartella: due giudici con lo stesso
nome e pesi o soglia diversi devono dare due versioni diverse.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from verimem import client, local_grounding

CONFIG = b'{"threshold": 0.5}'


def _attesa(pesi: bytes, config: bytes) -> str:
    h = hashlib.sha256()
    h.update(pesi)
    h.update(config)
    return "sha256:" + h.hexdigest()[:16]


@pytest.fixture
def giudice(monkeypatch, tmp_path):
    """Mette al posto del giudice locale una cartella con i pesi e la config dati."""
    def usa(pesi: bytes, config: bytes = CONFIG) -> Path:
        d = tmp_path / "local_gate_ce_prova"
        d.mkdir(exist_ok=True)
        (d / "model.safetensors").write_bytes(pesi)
        (d / "gate_config.json").write_bytes(config)
        monkeypatch.setattr(local_grounding, "get_local_judge",
                            lambda: SimpleNamespace(model_dir=d))
        return d
    return usa


def test_la_ricevuta_del_giudice_locale_porta_la_versione(giudice):
    giudice(b"pesi A")
    j = client._judge_of_record_dict("local")
    assert j["model"] == "local_gate_ce_prova", j
    assert j["version"] == _attesa(b"pesi A", CONFIG), (
        f"la ricevuta non dice quale giudice ha deciso: {j}")


def test_la_versione_segue_il_contenuto_non_il_nome(giudice):
    giudice(b"pesi A")
    prima = client._judge_of_record_dict("local")["version"]
    giudice(b"pesi B, un altro giudice")
    dopo = client._judge_of_record_dict("local")["version"]
    assert prima != dopo, "stesso nome di cartella, pesi diversi: la versione deve cambiare"
    giudice(b"pesi B, un altro giudice", b'{"threshold": 0.9}')
    con_altra_soglia = client._judge_of_record_dict("local")["version"]
    assert con_altra_soglia != dopo, (
        "la soglia fa parte del giudice: cambiarla deve cambiare la versione")


def test_un_giudice_che_non_e_il_ce_locale_non_si_inventa_una_versione():
    assert client._judge_of_record_dict("llm")["version"] is None
    assert client._judge_of_record_dict(None) is None


def test_senza_pesi_la_versione_resta_dichiarata_assente(monkeypatch, tmp_path):
    vuota = tmp_path / "senza_pesi"
    vuota.mkdir()
    monkeypatch.setattr(local_grounding, "get_local_judge",
                        lambda: SimpleNamespace(model_dir=vuota))
    assert client._judge_of_record_dict("local")["version"] is None
