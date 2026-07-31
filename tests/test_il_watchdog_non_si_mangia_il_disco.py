"""Lo strumento che diagnostica gli stalli non deve diventare il prossimo guaio.

Trovato il 2026-07-31 aprendo per la prima volta `~/.engram/hang-traces/` —
la cartella esisteva da mesi e nessuno l'aveva mai guardata::

    300 file, 34 MB in totale
    hang-1785412814-29092-hippo_health.txt   24.211.732 byte

Ventiquattro megabyte per UN solo stallo. La causa è
``dump_traceback_later(budget_s, repeat=True)``: rida' l'intero dump di tutti i
thread ogni ``budget_s`` secondi finché la chiamata non finisce. Su una chiamata
appesa dieci minuti con budget 30s sono venti dump — e dal secondo in poi è lo
stesso stack, cioè zero informazione in più a costo pieno.

I trace SONO preziosi: è da lì che è uscita la causa vera degli stalli di oggi
(gli import dentro la richiesta, non i modelli). Proprio per questo lo strumento
deve poter restare acceso senza che nessuno debba ricordarsi di svuotare la
cartella.

Due tetti, e nessuno dei due tocca il primo dump — quello che contiene la
diagnosi:

* per-file: oltre il tetto si smette di ridumpare e si scrive PERCHE', così chi
  legge sa che il file è troncato di proposito e non corrotto;
* per-cartella: i trace più vecchi si potano, tenendo i più recenti.
"""
from __future__ import annotations

import time

from verimem import _hang_watchdog as w


def test_il_primo_dump_non_si_tocca_mai(tmp_path, monkeypatch):
    """Il tetto non deve costare la diagnosi: un file sotto la soglia resta
    intero, ed è quello che serve a capire dove si è bloccato."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    with w.hang_trace("prova_veloce", 30.0):
        pass
    assert list(tmp_path.glob("hang-*.txt")) == [], (
        "una chiamata VELOCE ha lasciato un file: il header-only va rimosso")


def test_un_file_che_cresce_troppo_smette_e_lo_dichiara(tmp_path, monkeypatch):
    """Il caso misurato, in piccolo: budget minuscolo perché il watchdog
    ridumpi più volte, e tetto minuscolo perché scatti."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILE_BYTES", 4096)
    with w.hang_trace("prova_lenta", 0.05):
        time.sleep(1.2)
    file = list(tmp_path.glob("hang-*.txt"))
    assert file, "nessun trace scritto per una chiamata oltre budget"
    testo = file[0].read_text(encoding="utf-8", errors="replace")
    assert file[0].stat().st_size < 200_000, (
        f"il tetto non ha fermato la crescita: {file[0].stat().st_size} byte")
    assert "tetto" in testo.lower() or "troncato" in testo.lower(), (
        "il file è stato troncato senza dire perché: chi legge non distingue "
        f"un tetto da un file corrotto\n{testo[-300:]}")


def test_i_trace_vecchi_si_potano(tmp_path, monkeypatch):
    """300 file accumulati in mesi: chi accende una diagnostica non deve
    ricordarsi di spegnerla."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILES", 5)
    for i in range(12):
        p = tmp_path / f"hang-{1000+i}-1-vecchio.txt"
        p.write_text("x" * 500, encoding="utf-8")
    w._pota_i_vecchi()
    rimasti = sorted(p.name for p in tmp_path.glob("hang-*.txt"))
    assert len(rimasti) == 5, rimasti
    assert rimasti[-1] == "hang-1011-1-vecchio.txt", (
        f"potati i più RECENTI invece dei più vecchi: {rimasti}")


def test_la_potatura_non_tocca_cio_che_non_e_un_trace(tmp_path, monkeypatch):
    """La cartella è dell'utente: si tocca solo ciò che questo modulo scrive."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path)
    monkeypatch.setattr(w, "_MAX_FILES", 1)
    (tmp_path / "note-di-aurelio.txt").write_text("mie", encoding="utf-8")
    (tmp_path / "hang-1-1-a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "hang-2-1-b.txt").write_text("x", encoding="utf-8")
    w._pota_i_vecchi()
    assert (tmp_path / "note-di-aurelio.txt").exists()


def test_potare_non_puo_far_fallire_una_chiamata(tmp_path, monkeypatch):
    """Il contratto del modulo è «observability ONLY, never raises»: una
    cartella non scrivibile deve costare il trace, mai la chiamata."""
    monkeypatch.setattr(w, "_TRACE_DIR", tmp_path / "che-non-esiste")
    monkeypatch.setattr(w, "_MAX_FILES", 1)
    w._pota_i_vecchi()          # non deve sollevare
    with w.hang_trace("prova", 30.0):
        pass
