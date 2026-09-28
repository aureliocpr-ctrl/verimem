"""`verimem doctor` stampa quanto costa verimem alla macchina: la riga 7.

La promessa (T217, riga 7 del tabellone): verimem costa al massimo X MB fissi
sulla macchina e Y MB per sessione, e il doctor stampa i due numeri misurati.
MISURATO il 2026-09-28 con i processi vivi e con un banco a passi: il daemon con
i quattro modelli impegna 7470 MB sulla scheda e 5868 su CPU (quello vero, con
tre modelli, 6298); un server MCP fra 348 e 528. Fino a oggi nessuna superficie
del prodotto lo diceva: la RAM satura si leggeva a mano nel Task Manager.

⚠️ LA GRANDEZZA E' LA MEMORIA IMPEGNATA, non la unica (USS). La prima stesura
misurava la USS, e sulla macchina vera ha stampato «fixed 334 MB» per un daemon
che alle 19:26 ne teneva 1689 in RAM: sotto pressione Windows toglie pagine ai
processi fermi, la USS scende e l'impegnata no. Un tetto massimo misurato con la
USS passa proprio quando la macchina e' piena.

NESSUN PROCESSO VERO: uno psutil finto con un daemon, due server MCP, il loro
lanciatore e un processo estraneo.
"""
from __future__ import annotations

import types

from verimem import doctor

MB = 2 ** 20


class _Processo:
    def __init__(self, pid, cmdline, privata_mb, unica_mb, *, windows=True, swap_mb=0):
        self.pid = pid
        self.info = {"pid": pid, "cmdline": cmdline}
        self._privata, self._unica = privata_mb, unica_mb
        self._windows, self._swap = windows, swap_mb

    def memory_info(self):
        if self._windows:
            return types.SimpleNamespace(rss=self._unica * MB, private=self._privata * MB)
        return types.SimpleNamespace(rss=self._unica * MB)

    def memory_full_info(self):
        return types.SimpleNamespace(uss=self._unica * MB, swap=self._swap * MB)


def _psutil_finto(processi):
    per_pid = {p.pid: p for p in processi}
    return types.SimpleNamespace(
        Process=lambda pid: per_pid[pid],
        process_iter=lambda attrs=None: iter(processi))


# Il daemon e' stato compresso da Windows: 334 MB in RAM, 6298 impegnati.
_MACCHINA = [
    _Processo(10, ["pythonw.exe", "-m", "verimem.encode_service"], 6298, 334),
    _Processo(20, ["engram.exe", "mcp"], 1, 0),
    _Processo(21, ["python.exe", "-m", "verimem.mcp_server"], 357, 19),
    _Processo(30, ["verimem.exe", "mcp"], 528, 150),
    _Processo(40, ["notepad.exe"], 90, 90),
]


def test_i_due_numeri_sono_misurati_sui_processi_vivi():
    """RED sul tronco: la funzione non c'e'."""
    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(_MACCHINA))

    assert misura["per_sessione_mb"] == 528, misura     # il server piu' grande
    assert misura["per_sessione_unica_mb"] == 150, misura
    assert misura["processi_mcp"] == 3, misura          # lanciatore compreso, notepad no


def test_un_daemon_compresso_conta_per_quello_che_impegna():
    """IL RIGHELLO CHE SBAGLIAVA A FAVORE: la unica dice 334, l'impegnata 6298.
    La promessa si misura sulla seconda."""
    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(_MACCHINA))

    assert misura["fissa_mb"] == 6298, misura
    assert misura["fissa_unica_mb"] == 334, misura


def test_fuori_da_windows_l_impegnata_e_la_unica_piu_lo_swap():
    macchina = [_Processo(10, ["python3", "-m", "verimem.encode_service"], 0, 1500,
                          windows=False, swap_mb=700)]

    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(macchina))

    assert misura["fissa_mb"] == 2200, misura


def test_la_riga_del_doctor_dice_i_due_numeri_e_il_tetto(monkeypatch):
    """RED sul tronco: il doctor non ha la riga `memory`."""
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": True, "fissa_mb": 6298, "fissa_unica_mb": 334,
        "per_sessione_mb": 528, "per_sessione_unica_mb": 150, "processi_mcp": 3})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"]

    assert len(riga) == 1, "il doctor non dice quanto costa verimem"
    assert riga[0]["status"] == doctor.OK, riga
    assert "fixed 6298 MB" in riga[0]["detail"], riga
    assert "per session 528 MB" in riga[0]["detail"], riga
    assert "committed memory" in riga[0]["detail"], riga
    assert riga[0]["fixed_mb"] == 6298 and riga[0]["per_session_mb"] == 528, riga


def test_sopra_il_tetto_il_doctor_avvisa(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": True, "fissa_mb": doctor.MEMORIA_FISSA_MAX_MB + 1,
        "fissa_unica_mb": 100, "per_sessione_mb": 100, "per_sessione_unica_mb": 50,
        "processi_mcp": 1})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga


def test_senza_psutil_lo_dice_invece_di_inventare(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": False, "perche": "psutil is not installed"})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga
    assert "not measured" in riga["detail"], riga
