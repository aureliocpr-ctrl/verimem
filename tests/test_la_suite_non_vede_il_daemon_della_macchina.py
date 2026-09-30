"""La suite non vede il daemon della macchina: un daemon avviato da un test si
pubblica nella cartella dati del test.

I percorsi del daemon di un modello (scoperta, lock del daemon, lock dello spawn)
si calcolano all'import di `encode_service`, nella home di chi lancia la suite e
sotto la chiave del modello dei test. Un daemon avviato da un test vi si
pubblicava: nessuna collisione con il daemon di produzione, che ha un altro
modello e quindi un'altra chiave, ma le sessioni di test di due copie di lavoro
sulla stessa macchina si vedevano a vicenda, e sul runner due job.

NESSUN MODELLO: un server con encoder finto su una porta locale.
"""
from __future__ import annotations

import os
from pathlib import Path

from verimem import encode_service as es
from verimem.config import CONFIG


def _nella_cartella_del_test(percorso) -> bool:
    return Path(percorso).resolve().is_relative_to(Path(CONFIG.data_dir).resolve())


def test_i_tre_percorsi_stanno_nella_cartella_dati_del_test():
    """RED senza la cura: sono quelli calcolati alla raccolta."""
    fuori = [str(p) for p in (es.DISCOVERY_PATH, es.DAEMON_LOCK_PATH, es._SPAWN_LOCK_PATH)
             if not _nella_cartella_del_test(p)]

    assert not fuori, f"fuori dalla cartella dati del test ({CONFIG.data_dir}): {fuori}"


def test_un_daemon_avviato_da_un_test_si_pubblica_nella_sabbia():
    server = es.EncodeServer(encode_fn=lambda testo: [0.0, 0.0],
                             model_name="modello/a", model_dim=2)
    try:
        server.start()
        annunciato = es.read_discovery() or {}
        assert annunciato.get("pid") == os.getpid(), annunciato
        assert _nella_cartella_del_test(server._discovery_path), server._discovery_path
    finally:
        server.stop()
