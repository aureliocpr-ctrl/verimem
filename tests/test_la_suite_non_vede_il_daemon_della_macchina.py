"""La suite non vede il daemon della macchina: un daemon avviato da un test si
pubblica nella cartella dati del test.

I percorsi della configurazione (scoperta, lock del daemon, lock dello spawn) si
calcolano all'import di `encode_service`, e sotto pytest l'import avviene alla
raccolta, quando la cartella dati e' ancora quella della shell. In una shell che
esporta lo store vero (quella della macchina di sviluppo lo fa) i tre percorsi
puntavano in `<store vero>/daemon/`, sotto la chiave dei test: nessuna collisione
con il daemon di produzione, che ha un'altra chiave, ma le sessioni di test di due
copie di lavoro si sarebbero viste a vicenda. Sul runner puntavano nella home del
runner: stessa cosa fra due job sulla stessa macchina.

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
