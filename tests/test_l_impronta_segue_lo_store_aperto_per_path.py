"""Chi apre lo store con un PATH esplicito deve avere la sua impronta.

Seconda forma del difetto del campo `store` (`W2-115`). La cura del
30/08 (`9ac64916`) ha risolto la prima — l'impronta congelata all'import
— ma l'impronta continua a derivare da ``data_dir()``, cioe' dalla
variabile d'ambiente: **chi apre con ``Memory(path)`` resta marcato
«casa»**. Misurato: ~90% dei chiamanti apre cosi', e un banco dell'esame lo
mostra dal vivo — store in ``Temp\tmp2j860m62`` ed eventi che dicono
l'impronta di casa.

⚠️ LA TRAPPOLA CHE QUESTO BANCO PRESIDIA: derivare l'impronta dal FILE
farebbe di ``<casa>/semantic/semantic.db`` una memoria DIVERSA da casa,
pur essendo la stessa — si curerebbe un difetto creandone un altro. La
derivazione deve stare sulla stessa base di `_store_fingerprint`: la
RADICE dei dati.
"""
from __future__ import annotations

import json
import os

import pytest

from verimem import flow_events


def _impronta_attesa_di(radice) -> str:
    from hashlib import sha256
    return sha256(str(radice).encode("utf-8")).hexdigest()[:12]


def test_lo_stesso_store_dato_come_PATH_ha_la_STESSA_impronta(tmp_path,
                                                              monkeypatch):
    """IL CONTROLLO: `<X>/semantic/semantic.db` E' la memoria `<X>`."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    flow_events.reset_store_fingerprint()
    per_env = flow_events._store_fingerprint()
    per_path = flow_events.impronta_di_percorso(
        tmp_path / "semantic" / "semantic.db")
    assert per_path == per_env, (per_path, per_env)


def test_due_store_diversi_dati_come_PATH_hanno_impronte_diverse(tmp_path):
    a = flow_events.impronta_di_percorso(tmp_path / "a" / "s.db")
    b = flow_events.impronta_di_percorso(tmp_path / "b" / "s.db")
    assert a != b, (a, b)


def test_un_evento_scritto_con_Memory_path_NON_dice_casa(tmp_path,
                                                         monkeypatch):
    """L'integrazione, che e' il caso reale: `HIPPO_DATA_DIR` punta a casa
    (o altrove) e lo store si apre con un path. L'evento deve dire il
    path, non l'ambiente."""
    from verimem import event_jsonl_log
    from verimem.client import Memory

    casa = tmp_path / "casa"
    altrove = tmp_path / "altrove"
    monkeypatch.setenv("HIPPO_DATA_DIR", str(casa))
    flow_events.reset_store_fingerprint()
    journal = tmp_path / "ev.jsonl"
    monkeypatch.setattr(event_jsonl_log, "EVENT_LOG_PATH", journal)

    Memory(altrove / "semantic" / "semantic.db").add(
        "il magazzino ha 4200 metri quadrati", topic="t",
        source="Planimetria: il magazzino ha 4200 metri quadrati.")

    righe = [json.loads(r)
             for r in journal.read_text(encoding="utf-8").splitlines()
             if r.strip().startswith("{")]
    assert righe, "nessun evento scritto"
    visti = {r["payload"].get("store") for r in righe}
    atteso = _impronta_attesa_di(os.path.realpath(altrove))
    assert atteso in visti, (atteso, visti,
                             _impronta_attesa_di(os.path.realpath(casa)))
