"""Fail-closed: sotto test, uno store fuori dalla cartella temporanea e' un
errore, non un avviso.

═══ PERCHE' SUL RISULTATO E NON SUI NOMI ═══
Il `conftest` pinna quattro variabili d'ambiente — `HIPPO_DATA_DIR`,
`ENGRAM_DATA_DIR`, `ENGRAM_DIR`, `VERIMEM_DATA_DIR` — e ognuna e' stata
aggiunta DOPO che un risolutore aveva guardato il nome non ancora pinnato e i
test avevano scritto nello store reale. Il commento del conftest conta le
occorrenze da se': «*Questa e' la quarta: si pinnano TUTTI*».

Pinnare i nomi e' enumerare le porte. La quinta porta e' il prossimo alias che
qualcuno introdurra', e la si scoprira' come le altre quattro: da un danno.
Questa funzione non chiede quali nomi siano stati pinnati — chiede **dove
finisce il file**. E' la stessa domanda per ogni alias, compreso quello che
ancora non esiste.

═══ COSA NON FA ═══
Non apre niente e non legge niente: riceve un percorso e lo confronta. Non
sostituisce il pinning delle variabili, che serve a far funzionare i test; e'
la rete sotto — quando il pinning fallisce, qui si ferma invece di scrivere.
"""
from __future__ import annotations

import os
import pathlib

__all__ = ["assert_store_isolato", "sotto_test"]


def sotto_test() -> bool:
    """Vero quando il processo gira dentro pytest.

    `PYTEST_CURRENT_TEST` la mette pytest stesso a ogni test, ed e' l'indizio
    che sopravvive anche ai subprocess che ereditano l'ambiente — che sono
    esattamente i casi in cui l'isolamento si e' rotto in passato.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def assert_store_isolato(
    percorso: str | os.PathLike[str],
    *,
    tmp_root: str | os.PathLike[str],
) -> None:
    """Solleva se ``percorso`` non sta dentro ``tmp_root``.

    Args:
        percorso: il file di store che si sta per aprire.
        tmp_root: la cartella temporanea di QUESTO test.

    Raises:
        RuntimeError: se il percorso cade fuori — con dentro il percorso vero,
            perche' un messaggio che non dice DOVE lascia chi legge senza
            niente da correggere.
    """
    p = pathlib.Path(percorso).expanduser()
    root = pathlib.Path(tmp_root).expanduser()
    # `resolve()` su entrambi: su Windows la tmp di pytest arriva spesso come
    # nome corto 8.3 (`RUNNER~1`) mentre il percorso dello store e' esteso, e
    # un confronto testuale fra le due forme dice «fuori» su due percorsi che
    # sono lo stesso posto.
    try:
        p_r, root_r = p.resolve(), root.resolve()
    except OSError:  # percorso non risolvibile: non inventare, confronta grezzo
        p_r, root_r = p, root
    if root_r == p_r or root_r in p_r.parents:
        return
    raise RuntimeError(
        f"store FUORI dall'isolamento del test: {p_r}\n"
        f"  atteso dentro: {root_r}\n"
        "  ⇒ una variabile DATA_DIR non e' pinnata su questo percorso, oppure "
        "il modulo era gia' importato quando il conftest l'ha pinnata "
        "(`CONFIG.semantic_db` si fissa all'import). Non e' un avviso: se "
        "questo test proseguisse, scriverebbe nel corpus servito."
    )
