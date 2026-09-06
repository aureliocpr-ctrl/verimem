"""Le librerie pesanti si importano nel thread CHIAMANTE, mai su uno di sfondo.

MISURATO il 06/09 con la sonda degli stack sul banco end-to-end, ultimo dump di
un giro fallito — DUE thread fermi dentro ``create_module``, cioe' dentro il
caricamento di un'estensione C:

    thread di preload   preload.py:165  import scipy.linalg -> _fblas
                        <frozen importlib._bootstrap_external>:1317
                        create_module                         FERMO

    thread che serve    mcp_server.py:7935 _call_tool_impl -> _ag -> build
                        wake.py:301  np.random.default_rng()
                        -> import numpy.random -> _bounded_integers
                        create_module                         FERMO

A/B a UNA variabile, tre giri per braccio, su origin/main d14f0ece PULITO:

    tutto acceso (come in produzione)      0 giri su 3
    HIPPO_PRELOAD_BACKGROUND=0 (sincrono)  3 giri su 3

e sul ramo con la cura minima (l'import sincrono, il warm ancora in sfondo):

    tutto acceso                           3 giri su 3   (10,5 · 11,0 · 11,2 s)

⚠️ Il PERCHE' due import di estensioni C in parallelo non finiscano resta
un'IPOTESI — il loader lock di Windows — e NON e' osservabile da Python. Questo
test non la presidia: presidia il FATTO misurato, cioe' che l'import avvenga
nel thread chiamante. Se un giorno qualcuno lo rimette su un thread di sfondo
«perche' l'avvio e' piu' rapido», questa cella cade e racconta perche'.

⚠️ NESSUN MODELLO E NESSUN IMPORT VERO QUI: la funzione pesante e' sostituita
da una che registra solo da quale thread e' stata chiamata.
"""
import threading

from verimem import preload as p


def test_le_librerie_pesanti_si_importano_nel_thread_chiamante(monkeypatch):
    """L'import di scipy deve avvenire PRIMA di servire, non in parallelo.

    L'asserzione e' sull'IDENTITA' del thread, non su «la lista non e' vuota»:
    cosi' il rosso e' deterministico. Col codice vecchio la lista o e' ancora
    vuota (il thread non e' partito) o contiene l'ident di un ALTRO thread —
    in entrambi i casi diversa da [mio], e in entrambi i casi il test cade.
    """
    visti: list[int] = []

    monkeypatch.setattr(
        p, "_scalda_le_librerie_del_giudice",
        lambda *, log=None: visti.append(threading.get_ident()))
    # tutto il resto del preload e' spento: qui si misura QUALE THREAD importa,
    # non cosa fa il warm.
    monkeypatch.setattr(p, "_dichiara_il_piano_del_giudice",
                        lambda *, log=None: None)
    monkeypatch.setattr(p, "_service_enabled", lambda: False)
    monkeypatch.setattr(p, "_deve_scaldare_il_giudice", lambda: False)
    monkeypatch.setattr(p, "_segnala_rerank_delegato", lambda *, log=None: None)
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.delenv("HIPPO_PRELOAD_BACKGROUND", raising=False)
    monkeypatch.delenv("HIPPO_RERANK_PRELOAD", raising=False)

    mio = threading.get_ident()
    thread = p.preload_embedding()
    if thread is not None:
        thread.join(timeout=10)

    assert visti == [mio], (
        f"l'import delle librerie del giudice non e' avvenuto nel thread "
        f"chiamante (atteso [{mio}], visto {visti}). Su un thread di sfondo "
        "si incastra con l'import di numpy che fa la richiesta: misurato il "
        "06/09, 0 giri su 3 contro 3 su 3 col warm sincrono."
    )


def test_il_banco_vede_davvero_da_quale_thread_si_importa():
    """CONTROLLO POSITIVO sullo strumento, non sul prodotto.

    Se `threading.get_ident()` dentro un thread tornasse lo stesso valore del
    chiamante, la cella qui sopra passerebbe SEMPRE — anche col difetto — e non
    misurerebbe niente. Questa deve restare verde in entrambi i versi: se un
    giorno cade anche lei, e' rotto il banco, non il prodotto.
    """
    visti: list[int] = []
    filo = threading.Thread(target=lambda: visti.append(threading.get_ident()))
    filo.start()
    filo.join(timeout=5)

    assert visti and visti[0] != threading.get_ident(), (
        "un thread di sfondo riporta lo stesso ident del chiamante: lo "
        "strumento non distingue i thread e la cella sopra non misura nulla."
    )
