"""`hang_trace` non deve avviare un thread NEL PERCORSO DELLA RICHIESTA.

MISURATO il 06/09 sul server MCP, con la sonda degli stack (12 dump su 12, nove
minuti, frame identici): il thread che serve una chiamata era fermo QUI —

    mcp_server.py:7730    call_tool
        with hang_trace(name, _HANG_TRACE_BUDGET_S):
    _hang_watchdog.py:123   hang_trace
        daemon=True).start()
    threading.py:982      Thread.start
        self._started.wait()
    threading.py:359      wait
        waiter.acquire()

**Non era fermo su un import: era fermo ad AVVIARE UN THREAD.** Nello stesso
istante un thread di preload era dentro ``from scipy.linalg import _fblas``
(transformers -> scipy.special -> _fblas), cioe' dentro il caricamento di una
DLL. Su Windows un thread nuovo non parte mentre un altro carica una DLL, e
``hang_trace`` ne avvia uno A OGNI CHIAMATA: percio' ogni richiesta si bloccava,
e restava bloccata.

⚠️ E IL PUNTO CHE RENDE IL DIFETTO SUBDOLO: quel codice sta dentro un
``try/except Exception`` che porta scritto «*tracing is best-effort, never break
the call*». La promessa non e' mantenuta, e non per un errore di scrittura:
``Thread.start()`` non FALLISCE, si BLOCCA — e un blocco non e' un'eccezione,
quindi la protezione non puo' vederlo. **La rete di sicurezza e' cieca proprio
al modo in cui questa riga rompe la chiamata.**

CHE SIA il loader lock di Windows resta l'ipotesi dichiarata (T1b, non
osservabile da Python). Questo presidio NON dipende da quell'ipotesi: pretende
soltanto che il percorso della richiesta non avvii thread, che e' vero comunque
— un thread avviato per ogni chiamata e' un costo e un rischio anche quando non
si blocca.

A COSA SERVE IL THREAD, per chi scrive la cura: sorveglia la DIMENSIONE del file
di dump e disarma ``faulthandler`` quando sfonda ``_MAX_FILE_BYTES``, perche' il
dump lo scrive faulthandler in C e non si puo' fermare da dentro. La cura non e'
togliere la sorveglianza: e' avviarla FUORI dal percorso della richiesta (una
volta per processo, all'avvio) o farne a meno controllando il tetto alla
chiusura del contesto.
"""
import threading

import pytest

from verimem import _hang_watchdog


@pytest.fixture()
def conta_thread(monkeypatch):
    """Conta gli start() di thread, senza farli partire davvero.

    ⚠️ I thread NON partono: il finto non fa nulla. Cosi' il banco non dipende
    dallo scheduler e non costa niente — e non puo' bloccarsi per la stessa
    ragione che sta misurando.
    """
    avviati: list[str] = []

    class _ThreadFinto:
        def __init__(self, *a, **kw):
            self._nome = kw.get("name", "?")

        def start(self):
            avviati.append(self._nome)

        def join(self, *a, **kw):
            return None

    monkeypatch.setattr(_hang_watchdog.threading, "Thread", _ThreadFinto)
    return avviati


def test_hang_trace_non_avvia_thread(conta_thread, tmp_path, monkeypatch):
    """Il percorso della richiesta non deve far partire nessun thread."""
    monkeypatch.setattr(_hang_watchdog, "_TRACE_DIR", tmp_path)

    with _hang_watchdog.hang_trace("banco", 30.0):
        pass

    assert not conta_thread, (
        "hang_trace ha avviato thread nel percorso della richiesta. "
        "Su Windows Thread.start() non ritorna mentre un altro thread carica "
        "una DLL — misurato il 06/09: call_tool fermo in self._started.wait() "
        "per nove minuti mentre un preload era dentro scipy _fblas. E il "
        "try/except intorno promette «never break the call» ma non puo' "
        f"vederlo, perche' un blocco non e' un'eccezione. "
        f"Visti: {len(conta_thread)} -> {conta_thread}")


def test_hang_trace_resta_una_sola_volta_anche_su_molte_chiamate(
        conta_thread, tmp_path, monkeypatch):
    """Anche cento chiamate non devono moltiplicare i thread.

    Se la cura scelta fosse «un sorvegliante solo per processo» invece di
    «nessuno», questo secondo presidio resta vero e il primo va aggiornato di
    conseguenza — non cancellato.
    """
    monkeypatch.setattr(_hang_watchdog, "_TRACE_DIR", tmp_path)

    for _ in range(100):
        with _hang_watchdog.hang_trace("banco", 30.0):
            pass

    assert len(conta_thread) <= 1, (
        "cento chiamate hanno avviato troppi thread: il costo e il rischio "
        f"crescono con il traffico, non sono una tantum. "
        f"Visti: {len(conta_thread)} -> {conta_thread[:5]}")


def test_il_banco_vede_davvero_gli_start(conta_thread):
    """CONTROLLO POSITIVO sullo strumento, non sul soggetto.

    Se il monkeypatch non mordesse, i due test sopra passerebbero **sempre** —
    un banco cieco che certifica una cura inesistente. Qui si avvia un thread
    di proposito: il contatore DEVE vederlo.
    """
    _hang_watchdog.threading.Thread(
        target=lambda: None, name="prova-del-banco", daemon=True).start()
    assert conta_thread == ["prova-del-banco"], (
        "il contatore non vede gli start: il monkeypatch non morde e i due "
        f"presidi di questo file non misurano niente. Visti: {conta_thread}")
