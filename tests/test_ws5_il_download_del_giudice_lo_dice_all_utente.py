"""Scaricare 746 MB senza dirlo e' una sorpresa, non una cura.

Il piano delle versioni (02/09, 0.7.2 atomica) chiede: «*Il giudice si scarica da solo al
primo write con fonte (o all'avvio del server MCP), **con un messaggio all'utente (peso,
tempo)**, e il pacchetto lo dichiara*».

Oggi il download parte **muto**: l'utente vede il comando fermo per una quindicina di
secondi e non sa perche'. La stessa cosa che rende utile la cura — procurarsi il giudice
senza che nessuno lo chieda — la rende opaca se non la si annuncia.

DOVE va il messaggio, e perche' li'::

    stderr, non stdout   stdout porta l'output strutturato dei comandi: sporcarlo
                         romperebbe chi ne fa il parsing
    una riga sola        e' un evento raro (una volta per macchina), non un log
    peso E tempo         «746 MB» dice quanto costa in rete, «una volta sola» dice
                         che non si ripete: senza il secondo, il primo spaventa

⚠️ E deve comparire **solo quando il download parte davvero**: se il modello c'e' gia',
o se l'operatore ha spento la rete (`VERIMEM_OFFLINE`), un messaggio sarebbe rumore.
"""
from __future__ import annotations

import verimem.local_grounding as lg


def _fai_partire_il_download(monkeypatch, tmp_path, capsys, *, offline=False):
    """Mette il giudice in condizione di doversi procurare il modello."""
    mancante = tmp_path / "assente"
    chiamate = {"fetch": 0}

    def finto_fetch(model_dir=None, **kw):
        chiamate["fetch"] += 1
        from pathlib import Path
        d = Path(model_dir) if model_dir else mancante
        d.mkdir(parents=True, exist_ok=True)
        (d / "config.json").write_text("{}")
        (d / "model.safetensors").write_bytes(b"\x00")
        return True, "installed"

    def finto_load(model_dir, **kw):
        from pathlib import Path
        if not (Path(model_dir) / "config.json").exists():
            raise FileNotFoundError(str(model_dir))
        return lambda coppie: [0.5 for _ in coppie]

    monkeypatch.setattr(lg, "ensure_gate_model", finto_fetch)
    monkeypatch.setattr(lg, "make_finetuned_scorer", finto_load)
    for f in ("VERIMEM_OFFLINE", "HIPPO_OFFLINE", "ENGRAM_OFFLINE",
              "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(f, raising=False)
    if offline:
        monkeypatch.setenv("VERIMEM_OFFLINE", "1")
    return lg.LocalGroundingJudge(mancante), chiamate


def test_il_download_annuncia_peso_e_durata(tmp_path, monkeypatch, capsys):
    """RED prima della cura: il download parte e non stampa niente."""
    j, chiamate = _fai_partire_il_download(monkeypatch, tmp_path, capsys)
    j._ensure_scorer()
    assert chiamate["fetch"] == 1, "il modello doveva essere procurato"

    err = capsys.readouterr().err
    assert err.strip(), "un download di tre quarti di giga non deve partire in silenzio"
    # il PESO, e dev'essere IL NUMERO VERO, non un numero qualsiasi seguito da «MB».
    # ⚠️ Questo assert prima diceva `"711" in err or "MB" in err`: con quell'`or` bastava
    # la parola «MB» per passare, e infatti non si e' accorto che il numero annunciato
    # era in MiB con l'etichetta MB (711 invece di 746). Un `or` in un assert e' una
    # porta di servizio: qui il numero si confronta con la costante, e basta.
    assert str(lg._PESO_DEL_GIUDICE_MB) in err, \
        f"il messaggio non dice il peso vero ({lg._PESO_DEL_GIUDICE_MB} MB): {err!r}"
    assert "MB" in err, f"il peso senza unita' non si legge: {err!r}"
    # e che NON si ripetera': senza, il peso sembra un costo a ogni scrittura
    assert "una volta" in err.lower() or "once" in err.lower(), \
        f"manca «una volta sola» nel messaggio: {err!r}"


def test_il_peso_annunciato_e_quello_che_si_scarica_davvero():
    """Il numero pubblico contro il disco: e' MB decimali, non MiB.

    Il difetto che questo presidio impedisce di ripetere e' gia' successo (02/09): la
    costante valeva 711, che e' il peso in **MiB**, mentre il messaggio scriveva «MB».
    Chi installava vedeva il contatore di rete del sistema — che conta in MB decimali,
    come i piani dati — arrivare a 746 dopo aver letto 711.

    Gira solo dove il modello c'e' (la mia macchina, e la CI dopo un download). Dove
    manca si SALTA DICENDOLO: un presidio che tace quando non puo' misurare e' onesto,
    uno che passa in silenzio e' un sensore scollegato.
    """
    import pytest

    for d in (lg.DEFAULT_MODEL_DIR, lg._LEGACY_MODEL_DIR):
        if d.exists() and any(d.glob("*.safetensors")):
            byte = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
            mb_decimali = byte / 1e6
            scarto = abs(mb_decimali - lg._PESO_DEL_GIUDICE_MB) / mb_decimali
            assert scarto < 0.02, (
                f"il peso annunciato ({lg._PESO_DEL_GIUDICE_MB} MB) non e' quello sul "
                f"disco ({mb_decimali:.1f} MB decimali = {byte/2**20:.1f} MiB) in {d}. "
                f"Scarto {scarto:.1%}: se e' vicino al 4,9% e' la confusione MB/MiB."
            )
            return
    pytest.skip(
        "il modello del giudice non e' su questa macchina: il peso annunciato non e' "
        "verificabile qui. NON e' un pass — e' una misura che non si e' potuta fare."
    )


def test_niente_messaggio_se_il_modello_c_e_gia(tmp_path, monkeypatch, capsys):
    """Il controllo negativo: nessun rumore quando non si scarica nulla."""
    presente = tmp_path / "presente"
    presente.mkdir()
    (presente / "config.json").write_text("{}")
    (presente / "model.safetensors").write_bytes(b"\x00")
    monkeypatch.setattr(lg, "make_finetuned_scorer",
                        lambda model_dir, **kw: (lambda c: [0.5 for _ in c]))
    lg.LocalGroundingJudge(presente)._ensure_scorer()
    assert not capsys.readouterr().err.strip(), \
        "senza download non deve esserci nessun messaggio"


def test_niente_messaggio_se_il_download_e_disattivato(tmp_path, monkeypatch, capsys):
    """L'altro controllo negativo: `VERIMEM_OFFLINE` non deve nemmeno annunciare."""
    j, chiamate = _fai_partire_il_download(monkeypatch, tmp_path, capsys, offline=True)
    try:
        j._ensure_scorer()
    except Exception:
        pass
    assert chiamate["fetch"] == 0, "offline: nessun download"
    assert not capsys.readouterr().err.strip(), \
        "offline: nessun download, quindi nessun annuncio"


# ---------------------------------------------------------------------------
# L'annuncio non deve poter impedire cio' che annuncia.
#
# Nato da un incidente REALE in CI (02/09, job 100383919068):
# un `Popen(text=True)` senza `encoding=` leggeva cp1252 su Windows e moriva sul
# byte 0x8f di una emoji. Il difetto non era la emoji: era che un CANALE DI TESTO
# su Windows puo' rompersi dove su Linux non si rompe mai.
#
# Qui la posta e' piu' alta che in un test: `annuncia_download_del_giudice()` e'
# chiamata DENTRO il blocco `except` di `_ensure_scorer`, **una riga prima** del
# download. Se l'annuncio solleva, l'eccezione sostituisce quella originale, il
# download non parte, e la cura «il giudice si procura da solo» si spegne — per
# colpa del messaggio che doveva solo raccontarla.
#
# `sys.stderr is None` non e' ipotetico: e' lo stato normale di un processo
# avviato con `pythonw.exe`, cioe' di un server MCP lanciato da un client GUI —
# esattamente il caso in cui il giudice si deve procurare da solo.
# ---------------------------------------------------------------------------

def test_senza_stderr_il_messaggio_non_finisce_su_stdout(tmp_path, monkeypatch, capsys):
    """`pythonw`: `sys.stderr is None`. E li' `print` ha una trappola.

    `print(x, file=None)` NON e' un no-op: Python tratta `None` come «il default»,
    cioe' **stdout**. Un annuncio che ripiega su stdout dentro il server MCP
    inquina il canale JSON-RPC — che e' letteralmente l'incidente che era stato
    appena diagnosticato in CI, causato stavolta da noi.
    """
    j, chiamate = _fai_partire_il_download(monkeypatch, tmp_path, None)
    monkeypatch.setattr("sys.stderr", None)
    j._ensure_scorer()
    assert chiamate["fetch"] == 1, \
        "senza stderr l'annuncio non puo' partire, ma il DOWNLOAD si'"
    assert not capsys.readouterr().out.strip(), \
        "senza stderr il messaggio deve TACERE, non ripiegare su stdout"


def test_il_download_parte_anche_se_stderr_solleva(tmp_path, monkeypatch):
    """Lo stream c'e' ma e' rotto (chiuso, detached, codifica che non mappa)."""
    class StderrRotto:
        def write(self, *a, **kw):
            raise UnicodeEncodeError("charmap", "x", 0, 1, "rotto come in CI")

        def flush(self, *a, **kw):
            raise ValueError("I/O operation on closed file")

    j, chiamate = _fai_partire_il_download(monkeypatch, tmp_path, None)
    monkeypatch.setattr("sys.stderr", StderrRotto())
    j._ensure_scorer()
    assert chiamate["fetch"] == 1, \
        "uno stderr rotto non deve impedire al giudice di procurarsi il modello"
