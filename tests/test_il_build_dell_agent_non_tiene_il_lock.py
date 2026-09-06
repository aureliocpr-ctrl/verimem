"""Il build dell'Agent non deve tenere `_agent_lock`, e chi aspetta non resta muto.

MISURATO il 06/09 sul server MCP, con la sonda degli stack, nel giro fallito del
banco end-to-end (`1 giro su 3`, criterio `3 su 3`):

    LA RICHIESTA          mcp_server.py:7731  call_tool
                          mcp_server.py:7878  _call_tool_impl -> a = _ag()
                          mcp_server.py:93    _ag  ->  with _agent_lock:   FERMA

    CHI TIENE IL LOCK     self_heal.py:114 _run -> _run_self_heal:65
                          mcp_server.py:95 _ag -> agent.py:82 build
                          -> wake.py:301 __init__ -> import numpy.random

`_ag` teneva `_agent_lock` per TUTTA la durata di `VerimemAgent.build()`, che
carica numpy, scipy e transformers. `self_heal` lo chiama all'avvio su un thread
di sfondo: ogni richiesta che arriva DURANTE il build si accodava a riga 93.

⇒ L'intermittenza non era un mistero: e' una CORSA fra l'avvio e la prima
chiamata. Se il build finisce prima, il giro passa; altrimenti la chiamata
aspetta tutto il build. Esattamente 1 su 3.

COSA PRESIDIA QUESTO FILE (le tre celle chieste dal lead il 06/09 09:55):
  (b) il lock NON e' tenuto durante il build — un altro thread lo prende in meno
      di 100 ms mentre il build e' in corso;
  (c) l'agent e' costruito UNA volta sola, anche con piu' chiamate insieme (era
      la ragione per cui il lock esisteva: non si perde curando);
  (a) una richiesta che arriva DURANTE il build non resta muta: o torna entro il
      budget, o solleva un errore LEGGIBILE. Mai pendere.

⚠️ NESSUN MODELLO QUI: `VerimemAgent.build` e' sostituito da uno finto che dorme.
Il banco costa quanto un `sleep`.
"""
import threading
import time

import pytest

from verimem import mcp_server as m

DORMITA = 5.0


@pytest.fixture()
def build_lento(monkeypatch):
    """Sostituisce il build con uno lento, e conta quante volte parte.

    ⚠️ CONTROLLO POSITIVO in coda al test: il finto DEVE essere stato chiamato.
    Se `_agent` fosse gia' costruito da un altro test, nessuna cella qui
    misurerebbe niente e passerebbero tutte — un verde che non vale.
    """
    partenze: list[float] = []

    def _finto():
        partenze.append(time.time())
        time.sleep(DORMITA)
        return object()          # un agent finto: qui non si usa

    monkeypatch.setattr(m, "_agent", None, raising=False)
    monkeypatch.setattr(m.VerimemAgent, "build", staticmethod(_finto))
    return partenze


def test_il_lock_non_e_tenuto_durante_il_build(build_lento):
    """(b) Mentre il build dorme, un altro thread deve poter prendere il lock."""
    costruttore = threading.Thread(target=m._ag, daemon=True)
    costruttore.start()

    # si aspetta che il build sia PARTITO, non un tempo a caso
    inizio = time.time()
    while not build_lento and time.time() - inizio < 5.0:
        time.sleep(0.01)
    assert build_lento, "il build finto non e' mai partito: il banco non misura"

    time.sleep(0.2)              # siamo dentro il build (dorme 5 s)
    t0 = time.time()
    preso = m._agent_lock.acquire(timeout=0.1)
    attesa = time.time() - t0
    if preso:
        m._agent_lock.release()

    costruttore.join(timeout=DORMITA + 5)

    assert preso, (
        f"il lock e' TENUTO durante il build (atteso {attesa:.3f}s e non preso). "
        "Ogni richiesta che chiama _ag() mentre l'agent si costruisce si accoda "
        "qui: misurato il 06/09, la richiesta ferma in mcp_server.py:93 mentre "
        "self_heal era dentro agent.build() a caricare numpy. E' la corsa che "
        "produce il «1 giro su 3»."
    )


def test_l_agent_e_costruito_una_volta_sola(build_lento):
    """(c) Curare il lock non deve far tornare i build doppi che il lock evitava."""
    fili = [threading.Thread(target=m._ag, daemon=True) for _ in range(4)]
    for f in fili:
        f.start()
    for f in fili:
        f.join(timeout=DORMITA + 10)

    assert len(build_lento) == 1, (
        f"il build e' partito {len(build_lento)} volte invece di una. Il lock "
        "esisteva per questo (build concorrenti sugli stessi file SQLite): "
        "togliendolo dal percorso lento non si deve perdere la garanzia."
    )


def test_chi_arriva_durante_il_build_non_resta_muto(build_lento):
    """(a) O torna entro il budget, o dice perche'. Mai pendere in silenzio."""
    costruttore = threading.Thread(target=m._ag, daemon=True)
    costruttore.start()
    inizio = time.time()
    while not build_lento and time.time() - inizio < 5.0:
        time.sleep(0.01)
    assert build_lento, "il build finto non e' mai partito: il banco non misura"

    esito: list = []

    def _chiamata():
        try:
            esito.append(("ok", m._ag()))
        except Exception as exc:  # noqa: BLE001 — un errore leggibile e' un esito valido
            esito.append(("errore", str(exc)))

    richiesta = threading.Thread(target=_chiamata, daemon=True)
    t0 = time.time()
    richiesta.start()
    richiesta.join(timeout=DORMITA + 10)
    durata = time.time() - t0

    costruttore.join(timeout=DORMITA + 10)

    assert esito, (
        f"la richiesta non e' tornata in {durata:.1f}s: e' rimasta MUTA, che e' "
        "il caso misurato il 06/09 (75 s senza risposta sullo stdout, mentre "
        "initialize rispondeva a 2,4 s)."
    )
    tipo, valore = esito[0]
    if tipo == "errore":
        assert "agent" in str(valore).lower() or "retry" in str(valore).lower(), (
            f"l'errore non dice cosa sta succedendo: {valore!r}. Il budget puo' "
            "scadere, ma il messaggio deve nominare il build in corso."
        )


def test_se_il_budget_scade_l_errore_e_leggibile(build_lento, monkeypatch):
    """(a-bis) Il RAMO DELL'ERRORE deve essere ESEGUITO almeno una volta.

    La cella (a) accetta due esiti — torna entro il budget, oppure errore
    leggibile — e con un build finto da 5 s prende sempre il primo. Cosi' il
    messaggio del budget non lo costruisce nessun test: un refuso nell'f-string
    salterebbe fuori come eccezione oscura proprio quando il server e' gia' in
    difficolta', che e' il caso peggiore in cui scoprirlo.

    Qui il budget e' 0,2 s contro un build da 5 s: il ramo dell'errore e'
    obbligato.
    """
    monkeypatch.setattr(m, "_AGENT_BUILD_BUDGET_S", 0.2)

    costruttore = threading.Thread(target=m._ag, daemon=True)
    costruttore.start()
    inizio = time.time()
    while not build_lento and time.time() - inizio < 5.0:
        time.sleep(0.01)
    assert build_lento, "il build finto non e' mai partito: il banco non misura"

    t0 = time.time()
    with pytest.raises(RuntimeError) as caduta:
        m._ag()
    attesa = time.time() - t0

    costruttore.join(timeout=DORMITA + 10)      # chi lancia chiude

    messaggio = str(caduta.value)
    assert "still building" in messaggio and "retry" in messaggio, (
        f"l'errore non dice cosa fare: {messaggio!r}"
    )
    assert attesa < DORMITA, (
        f"ha aspettato {attesa:.1f}s con un budget di 0,2s: il budget non morde "
        "e la richiesta resta appesa al build."
    )
