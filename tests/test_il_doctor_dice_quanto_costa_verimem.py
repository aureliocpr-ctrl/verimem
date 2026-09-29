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
    def __init__(self, pid, cmdline, privata_mb, unica_mb, *, windows=True, swap_mb=0,
                 ws_mb=None, picco_mb=None, picco_ws_mb=None):
        self.pid = pid
        self.info = {"pid": pid, "cmdline": cmdline}
        self._privata, self._unica = privata_mb, unica_mb
        self._windows, self._swap = windows, swap_mb
        self._ws = unica_mb if ws_mb is None else ws_mb
        self._picco, self._picco_ws = picco_mb, picco_ws_mb

    def memory_info(self):
        if self._windows:
            campi = {"rss": self._ws * MB, "private": self._privata * MB}
            if self._picco is not None:
                campi["peak_pagefile"] = self._picco * MB
            if self._picco_ws is not None:
                campi["peak_wset"] = self._picco_ws * MB
            return types.SimpleNamespace(**campi)
        return types.SimpleNamespace(rss=self._ws * MB)

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
    assert "shared encode daemon: committed 6298 MB" in riga[0]["detail"], riga
    assert "MCP processes: committed 528 MB" in riga[0]["detail"], riga
    assert "peak n/a on this system" in riga[0]["detail"], riga   # nessun picco inventato
    assert riga[0]["fixed_mb"] == 6298 and riga[0]["per_session_mb"] == 528, riga


def test_sopra_il_tetto_il_doctor_avvisa(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": True, "fissa_mb": doctor.MEMORIA_FISSA_MAX_MB + 1,
        "fissa_unica_mb": 100, "per_sessione_mb": 100, "per_sessione_unica_mb": 50,
        "processi_mcp": 1})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga


#: La macchina misurata il 2026-09-29 alle 20:2x: il daemon vero e i due server MCP
#: che danno i massimi (uno per l'impegnata, l'altro per la unica).
_MACCHINA_29_09 = [
    _Processo(10, ["pythonw.exe", "-m", "verimem.encode_service"], 5990, 343,
              ws_mb=688, picco_mb=6025, picco_ws_mb=2863),
    _Processo(21, ["python.exe", "-m", "verimem.mcp_server"], 357, 53,
              ws_mb=104, picco_mb=357, picco_ws_mb=203),
    _Processo(22, ["python.exe", "-m", "verimem.mcp_server"], 355, 155,
              ws_mb=202, picco_mb=356, picco_ws_mb=202),
]


def _misura_finta(**campi):
    """Una misura con tutti i numeri dentro i due tetti, salvo quelli passati."""
    base = {"misurato": True, "processi_mcp": 2,
            "fissa_mb": 5990, "fissa_picco_mb": 6025, "fissa_unica_mb": 343,
            "fissa_ws_mb": 688, "fissa_picco_ws_mb": 2863,
            "per_sessione_mb": 357, "per_sessione_picco_mb": 357,
            "per_sessione_unica_mb": 155, "per_sessione_ws_mb": 202,
            "per_sessione_picco_ws_mb": 203}
    base.update(campi)
    return lambda info, psutil=None: base


def _riga_memoria(monkeypatch, **campi):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", _misura_finta(**campi))
    return [c for c in doctor.run_doctor() if c["name"] == "memory"][0]


def test_ogni_numero_per_sessione_e_il_massimo_della_sua_grandezza():
    """RED sul tronco: la sessione era il processo con l'impegnata piu' grande, e
    la sua unica (53) nascondeva quella del server accanto (155)."""
    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(_MACCHINA_29_09))

    assert misura["per_sessione_mb"] == 357, misura
    assert misura["per_sessione_unica_mb"] == 155, misura
    assert misura["per_sessione_ws_mb"] == 202, misura
    assert misura["per_sessione_picco_mb"] == 357, misura


def test_working_set_e_picchi_dove_il_sistema_li_tiene():
    """RED sul tronco: il doctor misurava solo impegnata e unica."""
    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(_MACCHINA_29_09))

    assert (misura["fissa_ws_mb"], misura["fissa_picco_mb"], misura["fissa_picco_ws_mb"]) \
        == (688, 6025, 2863), misura


def test_fuori_da_windows_il_picco_non_si_inventa():
    macchina = [_Processo(10, ["python3", "-m", "verimem.encode_service"], 0, 1500,
                          windows=False, swap_mb=700, ws_mb=1600)]

    misura = doctor.quanto_costa_verimem({"pid": 10}, psutil=_psutil_finto(macchina))

    assert misura["fissa_ws_mb"] == 1600, misura
    assert misura["fissa_picco_mb"] is None and misura["fissa_picco_ws_mb"] is None, misura


def test_la_riga_stampa_le_tre_grandezze_e_i_due_tetti(monkeypatch):
    """RED sul tronco: la riga diceva solo l'impegnata e un tetto solo."""
    riga = _riga_memoria(monkeypatch)

    assert riga["status"] == doctor.OK, riga
    for pezzo in ("committed 5990 MB (peak 6025)", "unique 343 MB",
                  "working set 688 MB (peak 2863)", "committed 357 MB (peak 357)",
                  "unique 155 MB", "2500", "300"):
        assert pezzo in riga["detail"], (pezzo, riga["detail"])
    assert (riga["fixed_unique_mb"], riga["per_session_unique_mb"]) == (343, 155), riga
    assert (riga["fixed_unique_max_mb"], riga["per_session_unique_max_mb"]) == (2500, 300), riga


def test_la_unica_fissa_sopra_il_suo_tetto_avvisa(monkeypatch):
    """RED sul tronco: con l'impegnata dentro, la unica non era confrontata."""
    riga = _riga_memoria(monkeypatch, fissa_unica_mb=2501)

    assert riga["status"] == doctor.WARN, riga


def test_la_unica_di_una_sessione_sopra_il_suo_tetto_avvisa(monkeypatch):
    riga = _riga_memoria(monkeypatch,
                         per_sessione_unica_mb=301)

    assert riga["status"] == doctor.WARN, riga


def test_il_tetto_dell_impegnata_vale_sul_picco(monkeypatch):
    """Un tetto massimo si legge sul massimo: adesso 5990, ma al picco oltre il tetto."""
    riga = _riga_memoria(monkeypatch, fissa_picco_mb=8001)

    assert riga["status"] == doctor.WARN, riga


def test_senza_psutil_lo_dice_invece_di_inventare(monkeypatch):
    monkeypatch.setattr(doctor, "quanto_costa_verimem", lambda info, psutil=None: {
        "misurato": False, "perche": "psutil is not installed"})

    riga = [c for c in doctor.run_doctor() if c["name"] == "memory"][0]

    assert riga["status"] == doctor.WARN, riga
    assert "not measured" in riga["detail"], riga
