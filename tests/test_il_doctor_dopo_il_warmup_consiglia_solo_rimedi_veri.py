"""Subito dopo `verimem warmup`, il doctor consigliava `verimem warmup`.

LA SCENA, dal job di accettazione del 25/09 (ubuntu, job 108188886269): un
venv vergine, il wheel installato con pip, `verimem warmup` riuscito, e il
doctor lanciato subito dopo rispondeva::

    ! daemon  no shared encode daemon — first encode in each process
      cold-loads the model (~20s)
        fix: run `verimem warmup` once
    ! relevance-floor  floor 0.0000 computed on 0 facts, now 0 — a floor of
      0.0 disables the relevance abstention (...)
        fix: verimem warmup

Due rimedi falsi, e tutti e due rimandano al comando appena eseguito. Il daemon
c'era: il warmup lo aveva appena lanciato («shared encode daemon spawning in
the background») e stava caricando il modello, quindi non aveva ancora scritto
il file di scoperta. E lo zero del pavimento era il valore voluto: su uno store
troppo piccolo la stima non puo' costruire le sue sonde di rumore e risponde
0.0 per scelta («a floor guessed from nothing would be worse than none»,
`estimate_relevance_floor`); rifare il warmup ridarebbe 0.0.

La promessa e' quella del comando (cli.py, `doctor`): «Each check says
PASS/WARN/FAIL and HOW to fix». Un rimedio che rimanda al passo appena fatto
non dice come si ripara.

Le celle mettono in scena gli stati come li lascia il warmup, con i suoi stessi
percorsi (`ensure_running`, il lock del daemon, `_open_memory` e
`rinfresca_se_stantio`) su file temporanei. E tengono i CONTROLLI: dove il
rimedio e' davvero il warmup, il doctor deve continuare a darlo.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time

import pytest

from verimem import encode_service as svc
from verimem.doctor import OK, WARN, run_doctor

CONSIGLIO_DEL_WARMUP = "run `verimem warmup` once"


def _check(nome):
    return next((c for c in run_doctor() if c["name"] == nome), None)


# ═══════════════════════════════════════════════════════════════════════════
# Il daemon che il warmup ha appena lanciato
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def daemon_isolato(tmp_path, monkeypatch):
    """I tre file del daemon su una cartella temporanea, e il servizio ACCESO.

    Il conftest spegne il servizio per tutta la suite (ENGRAM_ENCODE_SERVICE=0:
    un test non deve lanciare daemon veri). Qui lo si riaccende, perche' la
    scena e' quella di un utente; il lancio vero lo sostituisce un finto che
    registra la chiamata e non parte."""
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    monkeypatch.setattr(svc, "DISCOVERY_PATH", tmp_path / "encode_service.json")
    monkeypatch.setattr(svc, "_SPAWN_LOCK_PATH",
                        tmp_path / "encode_service.spawn.lock")
    monkeypatch.setattr(svc, "DAEMON_LOCK_PATH",
                        tmp_path / "encode_service.daemon.lock")
    lanci: list[int] = []
    monkeypatch.setattr(svc, "_spawn_detached", lambda: lanci.append(1))
    return lanci


def test_CONTROLLO_senza_daemon_e_senza_avvio_il_rimedio_resta_il_warmup(
        daemon_isolato):
    """Nessun daemon, nessun avvio in corso, servizio acceso: qui il warmup e'
    davvero il rimedio (lo lancia `ensure_running`), e il doctor deve dirlo."""
    c = _check("daemon")
    assert c is not None, "il doctor non espone il check del daemon"
    assert c["status"] == WARN, c
    assert c.get("fix") == CONSIGLIO_DEL_WARMUP, c


def test_il_daemon_appena_lanciato_dal_warmup_non_si_sente_consigliare_il_warmup(
        daemon_isolato):
    """IL CUORE, primo segno: il warmup ha chiesto il daemon (`ensure_running`,
    la riga del comando) e il processo non ha ancora preso il suo lock."""
    assert svc.ensure_running() is False
    assert daemon_isolato == [1], "il banco non ha messo in scena il lancio"
    c = _check("daemon")
    assert c.get("fix") != CONSIGLIO_DEL_WARMUP, (
        f"subito dopo il lancio del warmup il doctor consiglia il warmup: {c}")
    assert c["status"] == OK and "starting" in c["detail"], c


def test_il_daemon_che_carica_il_modello_non_si_sente_consigliare_il_warmup(
        daemon_isolato):
    """Secondo segno: il processo del daemon ha preso il lock (lo prende PRIMA
    di caricare il modello) e non ha ancora scritto la scoperta. Il lock lo
    prende qui la funzione vera, per il pid di questo processo, che e' vivo."""
    assert svc.acquire_daemon_lock() is True
    try:
        assert svc.daemon_in_arrivo() is True, "il banco non ha un daemon in arrivo"
        c = _check("daemon")
        assert c.get("fix") != CONSIGLIO_DEL_WARMUP, (
            f"con il daemon che carica il modello il doctor consiglia il "
            f"warmup: {c}")
        assert c["status"] == OK and "starting" in c["detail"], c
    finally:
        svc.release_daemon_lock()


def test_CONTROLLO_un_lancio_vecchio_e_il_lock_di_un_morto_non_sono_un_avvio(
        daemon_isolato):
    """La popolazione opposta: «sta partendo» non deve coprire un daemon morto
    o un lancio di ore fa. Li' il daemon non arriva, e il rimedio resta il
    warmup."""
    morto = subprocess.Popen([sys.executable, "-c", "pass"])
    morto.wait()
    svc.DAEMON_LOCK_PATH.write_text(str(morto.pid), encoding="utf-8")
    svc._SPAWN_LOCK_PATH.write_text("0", encoding="utf-8")
    vecchio = time.time() - 2 * svc._SPAWN_COOLDOWN_S
    os.utime(svc._SPAWN_LOCK_PATH, (vecchio, vecchio))
    assert svc.daemon_in_arrivo() is False, "il banco ha un daemon vivo"
    c = _check("daemon")
    assert c["status"] == WARN and c.get("fix") == CONSIGLIO_DEL_WARMUP, c


def test_col_servizio_spento_il_rimedio_nomina_l_interruttore(
        daemon_isolato, monkeypatch):
    """Con ENGRAM_ENCODE_SERVICE=0 il warmup NON lancia il daemon
    (`ensure_running` esce subito): consigliarlo e' un rimedio che non puo'
    funzionare. Il controllo positivo lo dimostra prima di chiedere al doctor."""
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    assert svc.ensure_running() is False and daemon_isolato == [], (
        "il banco non dimostra che col servizio spento il warmup non lancia")
    c = _check("daemon")
    assert c.get("fix") != CONSIGLIO_DEL_WARMUP, c
    assert "ENGRAM_ENCODE_SERVICE" in (c.get("fix") or ""), c


# ═══════════════════════════════════════════════════════════════════════════
# Il pavimento di uno store appena nato
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def store_nuovo(monkeypatch):
    """La cartella dati che il conftest da' a ogni test, nuova e vuota.

    Il conftest ci punta INSIEME i tre alias e `CONFIG`, come nel prodotto,
    dove vengono tutti e due dall'ambiente all'avvio. La prima versione di
    questa fixture spostava i soli alias su un'altra cartella, e la cella e'
    caduta per quello: lo store che il warmup apre (`CONFIG`) non era piu'
    quello che il doctor legge (gli alias). Era il banco, non il prodotto; il
    controllo qui sotto lo tiene fermo."""
    from pathlib import Path

    from verimem._compat import data_dir
    from verimem.config import CONFIG
    d = Path(str(CONFIG.data_dir))
    assert data_dir().resolve() == d.resolve(), (
        f"gli alias portano a {data_dir()}, CONFIG a {d}: la scena non e' "
        "quella del prodotto")
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    monkeypatch.delenv("VERIMEM_SERVER_URL", raising=False)
    return d


def _pavimento_come_il_warmup():
    """Le due righe del warmup (cli.py): lo store che il comando apre e il
    rinfresco che ci fa sopra."""
    from verimem.cli import _open_memory
    from verimem.relevance_floor import rinfresca_se_stantio
    mem = _open_memory()
    rinfresca_se_stantio(mem)
    return mem


def _corpus(store, n_servibili):
    """Uno store minimo con la sola colonna che il check conta."""
    db = store / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, "
                "superseded_by TEXT, status TEXT)")
    con.executemany("INSERT INTO facts (superseded_by, status) VALUES (?, ?)",
                    [(None, None)] * n_servibili)
    con.commit()
    con.close()
    return db


def _scrivi_pavimento(db, **campi):
    db.with_suffix(db.suffix + ".floor.json").write_text(
        json.dumps(campi), encoding="utf-8")


def test_lo_store_appena_nato_dopo_il_warmup_non_si_sente_consigliare_il_warmup(
        store_nuovo):
    """IL CUORE, secondo rimedio: lo zero su 0 fatti e' quello che la stima da'
    per scelta, e il warmup lo ridarebbe identico."""
    mem = _pavimento_come_il_warmup()
    f = mem._floor_file()
    atteso = store_nuovo / "semantic" / "semantic.db.floor.json"
    assert f.resolve() == atteso.resolve() and f.exists(), (
        f"il warmup ha scritto il pavimento in {f}, il doctor lo legge in {atteso}")
    assert json.loads(f.read_text(encoding="utf-8"))["floor"] == 0.0
    c = _check("relevance-floor")
    assert c.get("fix") != "verimem warmup", (
        f"su uno store di 0 fatti il doctor consiglia il warmup, che ridarebbe "
        f"lo stesso zero: {c}")
    assert c["status"] == OK, c


def test_il_pavimento_salvato_dice_se_lo_store_si_poteva_misurare(store_nuovo):
    """Il doctor non ricalcola (nessun modello, pochi secondi): puo' distinguere
    lo zero voluto da quello misurato solo se la stima lo scrive accanto al
    valore. Due fatti bastano alle sonde; zero no."""
    mem = _pavimento_come_il_warmup()
    d = json.loads(mem._floor_file().read_text(encoding="utf-8"))
    assert d.get("misurabile") is False, d
    mem.add("Il magazzino di Prato contiene trecento pallet di legno chiaro.")
    mem.add("La consegna del cemento arriva il dodici marzo al cantiere.")
    from verimem.relevance_floor import rinfresca_se_stantio
    mem._floor_cache = None
    rifatto, _ = rinfresca_se_stantio(mem)
    assert rifatto is True, "da 0 a 2 fatti il pavimento andava ricalcolato"
    d = json.loads(mem._floor_file().read_text(encoding="utf-8"))
    assert d.get("misurabile") is True, d


def test_un_file_scritto_prima_con_zero_fatti_si_legge_come_troppo_piccolo(
        store_nuovo):
    """Gli store che hanno gia' il file, scritto senza il campo: sotto le due
    fonti che le sonde chiedono, lo zero non puo' essere altro che quello
    voluto."""
    db = _corpus(store_nuovo, 0)
    _scrivi_pavimento(db, floor=0.0, n_facts=0, n_metric="servibili")
    c = _check("relevance-floor")
    assert c["status"] == OK and c.get("fix") != "verimem warmup", c


def test_CONTROLLO_lo_zero_su_uno_store_misurabile_resta_un_avviso_col_warmup(
        store_nuovo):
    """La popolazione opposta, ed e' l'allarme che il pavimento deve tenere:
    uno zero su un corpus che le sonde le ha e' il caso del 30/08 (0.0 su 13795
    fatti per sei ore), e li' il warmup e' il rimedio vero."""
    db = _corpus(store_nuovo, 100)
    _scrivi_pavimento(db, floor=0.0, n_facts=100, n_metric="servibili",
                      misurabile=True)
    c = _check("relevance-floor")
    assert c["status"] == WARN and c.get("fix") == "verimem warmup", c
