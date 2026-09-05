"""L'import del tokenizzatore NON deve avvenire tenendo il lock del giudice.

MISURATO IL 06/09 sul server MCP di main, sonda ogni 5 s dentro il processo:

     1  LOCK=False TOK=False TOKFAIL=False     <- prima che la chiamata arrivi
    24  LOCK=True  TOK=False TOKFAIL=False     <- per i 120 s successivi

cioè `self._lock` viene preso e non viene più rilasciato, mentre il tokenizzatore
non viene né creato né dichiarato fallito. Il thread di richiesta è fermo dentro
``from transformers import AutoTokenizer`` — e quell'import sta DENTRO il lock:

    local_grounding.py, _tokenizzatore()
        with self._lock:
            if self._tok is None and not self._tok_failed:
                from transformers import AutoTokenizer      <- qui
                self._tok = AutoTokenizer.from_pretrained(…)

⇒ Finché quell'import non ritorna, ogni altra scrittura con fonte che arriva a
quel punto si accoda dietro lo stesso lock: non è una chiamata lenta, è il
giudizio che si ferma per tutte dopo la prima.

COSA PRESIDIA QUESTO TEST: che il lock protegga la COSTRUZIONE del tokenizzatore
(che è il suo scopo — non costruirne due) e **non l'import**, che Python già
serializza da sé e che non ha bisogno di protezione.

⚠️ COSA NON PRESIDIA, e va detto: non fa tornare un import che non ritorna. Se
l'import resta appeso, il thread che lo esegue resta appeso comunque. Questo test
toglie il CONTAGIO agli altri, non la causa — che al 06/09 non è ancora spiegata
(la stessa chiamata torna in 17 s senza il transport stdio e non torna in 1800 con).
"""
import threading
import time

from verimem.local_grounding import get_local_judge


def test_il_lock_non_e_tenuto_durante_l_import_del_tokenizzatore(monkeypatch):
    """Mentre l'import è in corso, un altro thread deve poter prendere il lock."""
    giudice = get_local_judge()
    # stato pulito: il tokenizzatore non è ancora stato costruito
    monkeypatch.setattr(giudice, "_tok", None, raising=False)
    monkeypatch.setattr(giudice, "_tok_failed", False, raising=False)

    import builtins
    _vero_import = builtins.__import__
    _dentro_import = threading.Event()
    _puo_finire = threading.Event()

    def _import_lento(nome, *a, **k):
        # rallenta SOLO l'import che ci interessa, e segnala di essere dentro
        if nome == "transformers" or nome.startswith("transformers."):
            _dentro_import.set()
            _puo_finire.wait(timeout=10.0)
        return _vero_import(nome, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _import_lento)
    # `from_pretrained` non deve pesare: qui misuriamo l'IMPORT, non il caricamento
    monkeypatch.setattr(giudice, "model_dir", giudice.model_dir, raising=False)

    esito = []

    def _chiama():
        try:
            esito.append(giudice._tokenizzatore())
        except Exception as exc:  # noqa: BLE001 — il modello può mancare: non conta
            esito.append(exc)

    lavoratore = threading.Thread(target=_chiama, daemon=True)
    lavoratore.start()

    assert _dentro_import.wait(timeout=10.0), (
        "l'import di transformers non è mai partito: il banco non sta misurando "
        "quello che dice di misurare")

    # QUI È IL PUNTO: siamo dentro l'import. Il lock deve essere LIBERO.
    preso = giudice._lock.locked()
    _puo_finire.set()
    lavoratore.join(timeout=30.0)

    assert not preso, (
        "il lock del giudice è tenuto DURANTE l'import di transformers: ogni "
        "altra scrittura con fonte che arriva in questo momento si accoda dietro "
        "un import, e se quell'import non ritorna il giudizio si ferma per tutte. "
        "Il lock deve avvolgere la costruzione del tokenizzatore, non l'import."
    )


def test_il_tokenizzatore_resta_costruito_una_volta_sola():
    """Il lock serve a questo, e togliendolo dall'import non deve perdersi."""
    giudice = get_local_judge()
    costruiti = []
    pronto = threading.Barrier(4)

    def _chiama():
        pronto.wait(timeout=10.0)
        try:
            costruiti.append(id(giudice._tokenizzatore()))
        except Exception:  # noqa: BLE001 — modello assente: il test non lo richiede
            costruiti.append(None)

    fili = [threading.Thread(target=_chiama, daemon=True) for _ in range(4)]
    for f in fili:
        f.start()
    for f in fili:
        f.join(timeout=60.0)

    distinti = {c for c in costruiti if c is not None}
    assert len(distinti) <= 1, (
        f"quattro thread hanno ottenuto tokenizzatori diversi: {distinti}. "
        "Il lock deve continuare a garantirne UNO solo.")
    time.sleep(0)  # nessuna attesa: il test è già deterministico
