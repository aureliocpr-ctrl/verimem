"""`verimem doctor` stampa quanto costa verimem alla macchina: la riga 7.

La promessa (T217, riga 7 del tabellone): verimem costa al massimo X MB fissi
sulla macchina e Y MB per sessione, e il doctor stampa i due numeri misurati.
MISURATO il 2026-09-28 con i processi vivi e con un banco a passi: il daemon con
i quattro modelli tiene 2750 MB unici sulla scheda e 1561 su CPU; un server MCP
fra 147 e 277; uno scrittore in delegate-only 49 dopo le cure dello stesso
giorno. Fino a oggi nessuna superficie del prodotto lo diceva: la RAM satura si
misurava a mano col Task Manager, e il numero che leggeva (6027 MB) era la
memoria impegnata, non quella fisica.

NESSUN PROCESSO VERO: uno psutil finto con un daemon, due server MCP, il loro
lanciatore e un processo estraneo.
"""
from __future__ import annotations

import types

from verimem import doctor

MB = 2 ** 20


class _Processo:
    def __init__(self, pid, cmdline, uss_mb):
        self.pid = pid
        self.info = {"pid": pid, "cmdline": cmdline}
        self._uss = uss_mb

    def memory_full_info(self):
        return types.SimpleNamespace(uss=self._uss * MB)


def _psutil_finto(processi):
    per_pid = {p.pid: p for p in processi}
    return types.SimpleNamespace(
        Process=lambda pid: per_pid[pid],
        process_iter=lambda attrs=None: iter(processi))


_MACCHINA = [
    _Processo(10, ["pythonw.exe", "-m", "verimem.encode_service"], 1800),
    _Processo(20, ["engram.exe", "mcp"], 2),
    _Processo(21, ["python.exe", "-m", "verimem.mcp_server"], 150),
    _Processo(30, ["verimem.exe", "mcp"], 280),
    _Processo(40, ["notepad.exe"], 90),
]


def test_i_due_numeri_sono_misurati_sui_processi_vivi():
    """RED sul tronco: la funzione non c'e'."""
    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(_MACCHINA))

    assert misura["fissa_mb"] == 1800, misura
    assert misura["per_sessione_mb"] == 280, misura     # il server piu' grande
    assert misura["processi_mcp"] == 3, misura          # lanciatore compreso, notepad no


def test_la_riga_del_doctor_dice_i_due_numeri_e_il_tetto(monkeypatch):
    """RED sul tronco: il doctor non ha la riga `memory`."""
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": True, "fissa_mb": 1800, "per_sessione_mb": 280, "processi_mcp": 3})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"]

    assert len(riga) == 1, "il doctor non dice quanto costa verimem"
    assert riga[0]["status"] == doctor.OK, riga
    assert "fixed 1800 MB" in riga[0]["detail"], riga
    assert "per session 280 MB" in riga[0]["detail"], riga
    assert riga[0]["fixed_mb"] == 1800 and riga[0]["per_session_mb"] == 280, riga


def test_sopra_il_tetto_il_doctor_avvisa(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": True, "fissa_mb": doctor.MEMORIA_FISSA_MAX_MB + 1,
        "per_sessione_mb": 100, "processi_mcp": 1})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga


def test_senza_psutil_lo_dice_invece_di_inventare(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": False, "perche": "psutil is not installed"})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga
    assert "not measured" in riga["detail"], riga
