"""Gli import pesanti passano tutti sotto UN lock, e il lock non tiene il lavoro.

⚠️ LE DUE FORME DELLO STESSO DIFETTO, misurate il 06/09:

  bloccante (T1b):     due `create_module` in parallelo, entrambi fermi
                       (`scipy.linalg._fblas` e `numpy.random._bounded_integers`).
                       Banco end-to-end su origin/main pulito: 0 giri su 3.

  fallimentare (P0):   `from transformers import AutoModelForSequenceClassification`
                       su un thread di sfondo -> «cannot import name ...»,
                       mentre lo stesso import da solo riesce.
                       @ws1 Marie, A/B a una variabile sul commit installato:
                       warm su thread judged=False · warm sincrono grounding 98.37.

⇒ La cura e' metterli in fila: `verimem/_import_lock.py`.

🔑 E LA REGOLA CHE QUESTO FILE PRESIDIA PIU' DI TUTTE: **il lock si tiene solo
attorno all'import, mai attorno al lavoro**. I pesi del giudice sono 746 MB e
19,1 s: se stessero dentro il lock, una richiesta che arriva nel frattempo
aspetterebbe 19 secondi — cioe' avrei rimesso al suo posto il difetto tolto
stamattina con `a562e232` (il build che teneva `_agent_lock`). La cella
`test_il_lock_non_resta_preso_dopo_l_import` e' quella che se ne accorgerebbe.

⚠️ Nessun modello e nessun import vero: si misura chi prende il lock e quando.
"""
import threading
import time

from verimem import _import_lock as il


def test_il_lock_e_UNO_solo():
    """Se ogni chiamata tornasse un lock nuovo, non proteggerebbe niente.

    E' il modo silenzioso in cui una cura del genere puo' essere inutile: due
    chiamanti si serializzano ognuno con se' stesso, il codice sembra giusto e
    i due import continuano a incrociarsi.
    """
    assert il.lock_import() is il.lock_import(), (
        "lock_import() torna oggetti diversi: ogni chiamante si serializzerebbe "
        "solo con se' stesso e gli import continuerebbero a incrociarsi."
    )


def test_chi_importa_mentre_un_altro_importa_ASPETTA():
    """Il contratto: due import non si sovrappongono."""
    dentro = threading.Event()
    rilascia = threading.Event()
    ordine: list[str] = []

    def _primo() -> None:
        with il.lock_import():
            ordine.append("primo-entra")
            dentro.set()
            rilascia.wait(timeout=5)
            ordine.append("primo-esce")

    def _secondo() -> None:
        dentro.wait(timeout=5)
        with il.lock_import():
            ordine.append("secondo-entra")

    a = threading.Thread(target=_primo, daemon=True)
    b = threading.Thread(target=_secondo, daemon=True)
    a.start()
    b.start()
    dentro.wait(timeout=5)
    time.sleep(0.2)          # il secondo e' fermo sul lock, non dentro
    rilascia.set()
    a.join(timeout=5)
    b.join(timeout=5)

    assert ordine == ["primo-entra", "primo-esce", "secondo-entra"], (
        f"i due import si sono sovrapposti: {ordine!r}. Il secondo deve entrare "
        "SOLO dopo che il primo e' uscito."
    )


def test_il_lock_e_RIENTRANTE():
    """Un import ne innesca altri: senza rientranza la cura sarebbe un deadlock.

    ⚠️ E' il modo peggiore di curare — introdurre un blocco nuovo mentre se ne
    toglie uno — quindi va presidiato, non solo scritto nel docstring.
    """
    with il.lock_import():
        with il.lock_import():
            preso_due_volte = True
    assert preso_due_volte


def test_il_lock_non_resta_preso_dopo_l_import():
    """Il lavoro NON deve stare sotto il lock: qui si misura che venga liberato.

    Se un giorno qualcuno allargasse il `with` per comprendere anche il
    caricamento dei pesi (19,1 s), questa cella non basterebbe a vederlo da
    sola — ma il lock lasciato preso a fine blocco, che e' l'errore piu' facile,
    lo vede subito.
    """
    with il.lock_import():
        pass
    fuori: list[bool] = []
    filo = threading.Thread(
        target=lambda: fuori.append(il.e_tenuto_da_un_altro_thread()))
    filo.start()
    filo.join(timeout=5)
    assert fuori == [False], (
        "il lock e' rimasto preso dopo il blocco: ogni import successivo, in "
        "qualunque thread, resterebbe in coda per sempre."
    )


def test_il_banco_vede_davvero_un_lock_tenuto():
    """CONTROLLO POSITIVO sullo strumento.

    Se `e_tenuto_da_un_altro_thread()` rispondesse sempre False, la cella qui
    sopra passerebbe anche con un lock mai rilasciato. Questa deve restare verde
    perche' quella significhi qualcosa.
    """
    dentro = threading.Event()
    rilascia = threading.Event()
    visto: list[bool] = []

    def _tiene() -> None:
        with il.lock_import():
            dentro.set()
            rilascia.wait(timeout=5)

    filo = threading.Thread(target=_tiene, daemon=True)
    filo.start()
    dentro.wait(timeout=5)
    visto.append(il.e_tenuto_da_un_altro_thread())
    rilascia.set()
    filo.join(timeout=5)

    assert visto == [True], (
        "con il lock tenuto da un altro thread lo strumento risponde False: "
        "non distingue preso da libero, e la cella del rilascio non misura nulla."
    )
