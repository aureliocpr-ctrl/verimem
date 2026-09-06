"""Il preload sincrono deve caricare ANCHE ``numpy.random``, non solo scipy.

⚠️ PERCHE' QUESTO FILE ESISTE, ed e' la parte della storia che mancava.

La cura di T1b (``85178818``) sposta ``_scalda_le_librerie_del_giudice`` fuori dal
thread di sfondo. Il commento di quel commit dice «l'import si fa dove si puo'
fare, cioe' prima di servire» — vero, ma **incompleto**, e l'incompletezza e'
stata scoperta il 06/09 cercando di capire perche' il caso senza daemon fosse
verde contro la predizione depositata (3 su 3 contro un ≤2 su 3 previsto).

Misurato in processi separati, quel giorno:

    import scipy.linalg   ->  numpy.random in sys.modules: True
                          ->  _bounded_integers caricato : True

    import torch          ->  numpy: True   ma  numpy.random: False   (7,24 s)
    import verimem.embedding -> numpy.random: False · torch: False

⇒ ``scipy.linalg`` trascina ``numpy.random`` e ``_bounded_integers``, che sono
**esattamente i moduli dentro cui la richiesta si fermava** nel dump del giro
fallito:

    wake.py:301  np.random.default_rng()
    -> import numpy.random -> _bounded_integers
    -> <frozen importlib._bootstrap_external>:1317 create_module    FERMO

Quindi la cura non vince una corsa fra due import: **la elimina**. Quando la
richiesta arriva non ha piu' niente da importare.

🔴 LA FRAGILITA' CHE QUESTO FILE PRESIDIA: l'effetto dipende da un dettaglio
INTERNO di scipy. Se una versione futura smettesse di importare
``numpy.random``, la cura perderebbe il suo effetto principale e **nessuno degli
altri test se ne accorgerebbe**: presidiano «in quale thread si importa»
(``test_il_preload_non_importa_su_un_thread``), non «cosa risulta importato».

⚠️ Il RED qui NON si ottiene con ``git show`` di una nostra versione precedente:
la riga nostra e' identica prima e dopo la cura, cambia solo da dove viene
chiamata. Cio' che questo file sorveglia e' l'AMBIENTE. Per questo la prima
cella e' un controllo positivo che dimostra che il banco vede la differenza: in
un processo pulito, prima della chiamata, ``numpy.random`` NON c'e'.

⚠️ Ogni cella gira in un SUBPROCESS pulito: dentro pytest ``numpy.random`` e'
quasi certamente gia' importato da qualcun altro, e la misura direbbe sempre
True — un verde che non vale.
"""
import subprocess
import sys
import textwrap

#: Il modulo dentro cui si fermava la richiesta, non un modulo a caso.
_MODULO = "numpy.random"


def _in_un_processo_pulito(codice: str) -> str:
    """Esegue il codice in un interprete nuovo e torna l'output ripulito."""
    esito = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(codice)],
        capture_output=True, text=True, timeout=180,
    )
    assert esito.returncode == 0, (
        f"il sotto-processo e' uscito con {esito.returncode}:\n{esito.stderr}"
    )
    return esito.stdout.strip()


def test_il_banco_vede_davvero_la_differenza():
    """CONTROLLO POSITIVO sullo strumento: prima della chiamata NON c'e'.

    Se `numpy.random` risultasse gia' presente in un processo pulito, la cella
    sotto passerebbe SEMPRE — anche se il preload non caricasse nulla — e non
    misurerebbe niente. Questa deve restare verde perche' l'altra significhi
    qualcosa.
    """
    visto = _in_un_processo_pulito(f"""
        import sys
        print({_MODULO!r} in sys.modules)
    """)
    assert visto == "False", (
        f"in un processo pulito {_MODULO} risulta gia' importato ({visto!r}): "
        "lo strumento non distingue il prima dal dopo e la cella qui sotto non "
        "misura nulla."
    )


def test_il_preload_carica_anche_il_modulo_su_cui_la_richiesta_si_fermava():
    """Dopo il preload sincrono, `numpy.random` deve essere gia' in sys.modules.

    E' la proprieta' da cui dipende l'effetto della cura di T1b: la richiesta
    non deve trovare nulla da importare.
    """
    visto = _in_un_processo_pulito(f"""
        import sys
        from verimem.preload import _scalda_le_librerie_del_giudice
        _scalda_le_librerie_del_giudice()
        print({_MODULO!r} in sys.modules)
    """)
    assert visto == "True", (
        f"il preload NON carica piu' {_MODULO} ({visto!r}).\n"
        "L'effetto della cura di T1b dipende da questo: la richiesta esegue\n"
        "`wake.py:301 np.random.default_rng()` e, se il modulo non e' gia'\n"
        "caricato, fa un `create_module` mentre un altro thread ne fa un altro\n"
        "— che e' il difetto misurato il 06/09 (0 giri su 3).\n"
        "Causa probabile: una versione di scipy che non importa piu'\n"
        "numpy.random. La cura va estesa a importarlo esplicitamente."
    )
