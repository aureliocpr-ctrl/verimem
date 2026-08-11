"""Il log eventi vive nella data dir che l'utente ha scelto.

Misurato (ws6) e diagnosticato (ws5) il 2026-08-05: lanciando un banco con
``HIPPO_DATA_DIR`` su una cartella temporanea, il prodotto AVVISA che le
tre variabili non concordano e dichiara «HIPPO_DATA_DIR wins» — insegnando
che quella è LA leva per isolare. Poi il log eventi scriveva comunque in
``~/.engram/events.jsonl``: 39 righe di banchi isolati finite nel corpus di
casa.

La causa non era un resolver divergente: era ``Path.home()`` scritto a mano
nel default (riga 34), con un override su una QUARTA variabile
(``ENGRAM_EVENT_LOG``) che l'avviso non nomina. Il log non aveva mai
guardato la data dir, per disegno.

La cura scelta (proposta (a) di ws5): il default DERIVA dalla data dir
risolta; ``ENGRAM_EVENT_LOG`` resta l'override esplicito per chi vuole il
log altrove. Non si unifica osservabilità e store in un resolver solo —
sono due cose diverse e accoppiarle andrebbe sciolto dopo.
"""
from __future__ import annotations

import subprocess
import sys

CODE = (
    "from verimem import event_jsonl_log as e; print(str(e.EVENT_LOG_PATH))"
)


def _path_in_subprocess(env_extra: dict[str, str]) -> str:
    """Il path va letto in un processo NUOVO: EVENT_LOG_PATH è calcolato a
    livello di modulo, quindi settare l'env dopo l'import non ha effetto —
    limite reale del modulo, che il banco rispetta invece di aggirarlo."""
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR",
                        "VERIMEM_DATA_DIR", "ENGRAM_EVENT_LOG")}
    env.update(env_extra)
    out = subprocess.run([sys.executable, "-c", CODE], env=env,
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[-400:]
    return out.stdout.strip().splitlines()[-1]


def test_il_log_segue_hippo_data_dir(tmp_path):
    p = _path_in_subprocess({"HIPPO_DATA_DIR": str(tmp_path)})
    assert str(tmp_path) in p, (
        f"chi isola lo store deve isolare anche la telemetria: {p}")
    assert p.endswith("events.jsonl")


def test_l_override_esplicito_vince_sempre(tmp_path):
    altrove = tmp_path / "altrove" / "eventi.jsonl"
    p = _path_in_subprocess({"HIPPO_DATA_DIR": str(tmp_path),
                             "ENGRAM_EVENT_LOG": str(altrove)})
    assert p == str(altrove), (
        "ENGRAM_EVENT_LOG resta l'override esplicito e batte la data dir")


#: Le due cartelle dati del prodotto. ⚠️ NON sono un'alternativa storica da
#: ripulire: convivono per contratto, e il README lo dichiara — «Existing
#: ``~/.engram`` data stores keep working untouched; new installs default to
#: ``~/.verimem``» (``_compat.py:51`` definisce il nome nuovo).
_CASA = (".engram", ".verimem")


def test_senza_env_resta_il_percorso_di_casa(tmp_path):
    """Nessuna env: il log resta nella cartella dati del prodotto — la cura
    sposta il log SOLO per chi ha chiesto l'isolamento.

    ⚠️ QUESTO ASSERT ESIGEVA ``.engram`` E BASTA, e non poteva passare su
    NESSUNA installazione nuova: una macchina che installa oggi ha
    ``~/.verimem``, e ogni runner di CI e' una macchina che installa oggi. In
    locale passava — su una macchina con lo store storico — e falliva sui tre
    sistemi della CI con tre percorsi diversi (``/home/runner/.verimem``,
    ``/Users/runner/.verimem``, ``C:\\Users\\runneradmin\\.verimem``).

    🔑 IL COSTO NON ERA IL ROSSO: e' che il default NUOVO — quello che riceve
    ogni utente nuovo — non era verificato da nessuno. Il test guardava solo la
    generazione di chi l'aveva scritto.
    """
    p = _path_in_subprocess({})
    assert p.endswith("events.jsonl")
    assert any(c in p for c in _CASA), (
        f"il giornale non e' in una cartella dati del prodotto {_CASA}: {p}")
