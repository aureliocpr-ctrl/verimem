"""Due configurazioni sulla stessa home non si sfrattano il daemon a vicenda.

MISURATO il 2026-09-28 sulla macchina di sviluppo: alle 19:33:52 un processo con
la configurazione dei test (modello MiniLM a 384) ha avviato un daemon suo nella
home vera. Dopo la grazia di 600 s il daemon di produzione (e5 a 768) contava
per lui come «zombie», perche' `_owner_is_zombie` chiedeva `daemon_usable`, che
e' tarato sul modello di CHI CHIEDE. Il nuovo gli ha rubato lock e scoperta,
quello vero si e' fatto da parte, e per 41 minuti ogni sessione ha cercato per
parole chiave. Una scoperta e un lock soli per tutte le configurazioni fanno di
ogni configurazione diversa uno sfratto in attesa.

La cura decisa dal lead (28/09 20:2x): zombie vuol dire SOLO morto o muto, e la
scoperta e' per configurazione (cartella dati, modello, dimensione), cosi' un
client trova solo il daemon della sua configurazione.

NESSUN MODELLO: i due daemon sono processi veri con un encoder finto e senza
tokenizzatore; la grazia e il passo indietro sono accorciati nel figlio a 2 s.
Tutto in una home e in una cartella dati di sabbia.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]

DAEMON = r'''
from verimem import encode_service as es, embedding
embedding._encode_local = lambda testo: [0.0, 0.0]
es._prepara_la_finestra = lambda: None
es._ZOMBIE_GRACE_S = 2.0
es._SUPERFLUOUS_IDLE_S = 2.0
es.main()
'''

CLIENTE = r'''
import json
from verimem import encode_service as es
d = es.read_discovery() or {}
print("VEDO " + json.dumps({"pid": d.get("pid"), "model": d.get("model"),
                            "usabile": bool(es.daemon_usable(timeout=2.0))}))
'''


def _ambiente(sabbia: Path, modello: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    casa = sabbia / "home"
    dati = sabbia / "dati"
    env.update({
        "USERPROFILE": str(casa), "HOME": str(casa),
        "HIPPO_DATA_DIR": str(dati), "ENGRAM_DATA_DIR": str(dati), "VERIMEM_DATA_DIR": str(dati),
        "ENGRAM_EVENT_LOG": str(sabbia / "eventi.jsonl"),
        "HIPPO_EMBEDDING_MODEL": modello, "HIPPO_EMBEDDING_DIM": "2",
        "ENGRAM_ENCODE_SERVICE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "PYTHONPATH": str(RADICE), "PYTHONIOENCODING": "utf-8",
    })
    return env


def _cosa_vede(sabbia: Path, modello: str) -> dict:
    uscita = subprocess.run([sys.executable, "-c", CLIENTE], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(RADICE),
                            env=_ambiente(sabbia, modello), timeout=120)
    righe = [r for r in uscita.stdout.splitlines() if r.startswith("VEDO ")]
    assert righe, f"il cliente non ha risposto: {uscita.stderr[-1500:]}"
    return json.loads(righe[-1][len("VEDO "):])


def _aspetta(condizione, secondi: float) -> bool:
    fine = time.monotonic() + secondi
    while time.monotonic() < fine:
        if condizione():
            return True
        time.sleep(0.5)
    return False


def test_due_configurazioni_tengono_ciascuna_il_suo_daemon(tmp_path):
    """RED sul tronco: il secondo daemon ruba lock e scoperta al primo, e il
    cliente della prima configurazione non trova piu' il suo."""
    for cartella in ("home/.engram", "dati"):
        (tmp_path / cartella).mkdir(parents=True)
    avviati = []
    try:
        a = subprocess.Popen([sys.executable, "-c", DAEMON], cwd=str(RADICE),
                             env=_ambiente(tmp_path, "modello/a"),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        avviati.append(a)
        assert _aspetta(lambda: _cosa_vede(tmp_path, "modello/a")["pid"] == a.pid, 60), (
            "il daemon della configurazione A non si e' mai annunciato")
        time.sleep(3.0)   # oltre la grazia accorciata: A ora e' «vecchio»

        b = subprocess.Popen([sys.executable, "-c", DAEMON], cwd=str(RADICE),
                             env=_ambiente(tmp_path, "modello/b"),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        avviati.append(b)
        assert _aspetta(lambda: _cosa_vede(tmp_path, "modello/b")["usabile"], 60), (
            "il daemon della configurazione B non e' mai diventato usabile")
        time.sleep(3.0)   # il tempo di un passo indietro accorciato

        vede_a = _cosa_vede(tmp_path, "modello/a")
        vede_b = _cosa_vede(tmp_path, "modello/b")
    finally:
        for processo in avviati:
            processo.kill()
            processo.wait(timeout=30)

    assert vede_a == {"pid": a.pid, "model": "modello/a", "usabile": True}, (
        f"la configurazione A ha perso il suo daemon: vede {vede_a}; B vede {vede_b}")
    assert vede_b == {"pid": b.pid, "model": "modello/b", "usabile": True}, vede_b
