"""T60 — chi isola `ENGRAM_DATA_DIR` isola i DATI ma non il DAEMON.

⚠️ COSA E' COSTATO, misurato due volte in quindici ore sulla macchina di Aurelio.
Un banco che gira in una data dir temporanea — cioe' la cosa giusta, quella che
ci viene chiesta — legge la discovery GLOBALE, non riconosce il modello del
daemon di casa, ne spawna uno col PROPRIO e lo registra per tutti::

    09/09 23:02:29   daemon rimpiazzato   ENGRAM_DATA_DIR = ...\\Temp\\ws2-t49-6d7_r4ee
    10/09 13:14:23   daemon rimpiazzato   ENGRAM_DATA_DIR = ...\\Temp\\ws2-t49-sxqm2ehk

(le due righe sono lette dall'`environ()` dei processi colpevoli, non dedotte)

Conseguenza per chi non c'entra: con il daemon che serve 384 e lo store a 768 il
client rifiuta — correttamente — e in delegate-only la scrittura entra **senza
vettore**. **17 fatti** sono entrati cosi', in due finestre, e le loro ricevute
dicevano `stored: true`. Chi li ha scritti non lo sapeva.

🔑 E NON E' COLPA DI CHI LANCIA IL BANCO: non c'e' niente, nel comando che
scrive, che possa dirglielo. E' il prodotto che promette un isolamento e ne
mantiene meta'.

📌 LA STESSA CLASSE E' GIA' STATA PAGATA su un altro percorso, e il prodotto lo
racconta nel docstring di `cli._facts_data_dir`: *«con entrambe poste … la CLI
scriveva nel corpus VIVO mentre l'avviso annunciava di usare quello isolato.
Misurato: i fatti in produzione da 7178 a 7179 con HIPPO_DATA_DIR su una
directory temporanea»*. Li' la cura e' stata far passare la risoluzione da
`_compat._env_data_dir()`. **Qui si usa la stessa**, non una copia nuova (R3).

📏 LIVELLO: i tre path del daemon, letti dopo aver impostato l'ambiente e
ricaricato il modulo. Zero RAM, nessun daemon spawnato, gira in CI. Non prova
che due daemon non si incontrino — prova che **i marcatori che li fanno
incontrare seguono la data dir**, che e' la promessa violata.

🧪 CONTROLLO POSITIVO: senza override, i tre path devono restare **esattamente
dove sono oggi** (`~/.engram/...`). Se cambiassero, la cura romperebbe ogni
installazione esistente — e il verde del primo test non varrebbe niente.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

import pytest


def _ricarica_encode_service():
    """`DISCOVERY_PATH` e i due lock sono costanti di modulo: si rileggono solo
    ricaricando. E' anche il motivo per cui il difetto e' invisibile a chi
    guarda il codice di un banco: il path e' gia' fissato quando il banco parte."""
    for nome in [m for m in list(sys.modules) if m.startswith("verimem")]:
        del sys.modules[nome]
    return importlib.import_module("verimem.encode_service")


@pytest.fixture
def data_dir_isolata(tmp_path, monkeypatch):
    dati = tmp_path / "engram"
    dati.mkdir(parents=True, exist_ok=True)
    for chiave in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(chiave, str(dati))
    return dati


def test_i_tre_marcatori_del_daemon_seguono_la_data_dir(data_dir_isolata):
    """RED atteso. I tre path stanno in `Path.home()`, quindi un processo
    isolato parla comunque del daemon di casa: lo trova, non lo riconosce, e lo
    sostituisce."""
    es = _ricarica_encode_service()

    fuori = {
        nome: percorso
        for nome, percorso in (
            ("DISCOVERY_PATH", es.DISCOVERY_PATH),
            ("_SPAWN_LOCK_PATH", es._SPAWN_LOCK_PATH),
            ("DAEMON_LOCK_PATH", es.DAEMON_LOCK_PATH),
        )
        if data_dir_isolata not in pathlib.Path(percorso).parents
    }
    assert not fuori, (
        "I MARCATORI DEL DAEMON NON SEGUONO LA DATA DIR: un processo isolato "
        "legge e RISCRIVE quelli di casa.\n"
        + "\n".join(f"    {n} = {p}" for n, p in fuori.items())
        + f"\n  data dir isolata: {data_dir_isolata}"
    )


def test_controllo_positivo_senza_override_i_path_NON_cambiano(monkeypatch):
    """VERDE atteso, e senza di lui il primo test non significa niente: la cura
    non deve spostare i path di chi non isola, o rompe ogni installazione viva
    (il daemon di casa diventerebbe invisibile a tutti i client)."""
    for chiave in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(chiave, raising=False)
    es = _ricarica_encode_service()

    casa = pathlib.Path.home() / ".engram"
    assert es.DISCOVERY_PATH == casa / "encode_service.json"
    assert es._SPAWN_LOCK_PATH == casa / "encode_service.spawn.lock"
    assert es.DAEMON_LOCK_PATH == casa / "encode_service.daemon.lock"
