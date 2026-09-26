"""T68 — il dump ha un proprietario, e solo lui lo annulla.

IL FATTO: in integrazione su Windows con py3.12 il processo e' morto con
`Windows fatal exception: access violation`, e nel traceback c'erano DUE thread
dentro il watchdog nello stesso istante — il sorvegliante che annullava, e il
chiamante che dentro `hang_trace` aveva i dump armati sullo stesso file.

`dump_traceback_later(..., file=f)` fa scrivere i dump a un writer interno di
CPython. Annullare da un thread che quel dump non l'ha armato puo' liberare
sotto il writer cio' che sta usando: il processo non fallisce, MUORE.

⚠️ QUESTE CELLE NON RIPRODUCONO UNA CORSA, e non e' una rinuncia: una corsa
riprodotta con un'altra corsa non prova niente e passa anche senza la cura (gia'
misurato su un difetto gemello, sei giri verdi con e senza). Qui lo stato si
COSTRUISCE — si dichiara chi possiede il dump e si guarda chi riesce ad
annullarlo — quindi l'esito e' lo stesso su qualunque macchina.
"""
from __future__ import annotations

import ast
import threading
from pathlib import Path

from verimem import _hang_watchdog as w


def test_chi_non_possiede_il_dump_non_lo_annulla(monkeypatch) -> None:
    """Il cuore, deterministico: due thread, uno solo e' il proprietario.

    Nessuna attesa, nessuna finestra da centrare: il thread non proprietario
    parte, finisce, e si guarda se ha annullato.
    """
    annulli: list[str] = []
    monkeypatch.setattr(
        w.faulthandler, "cancel_dump_traceback_later",
        lambda: annulli.append("annullato"))
    monkeypatch.setattr(w, "_proprietario_del_dump", threading.get_ident())

    estraneo = threading.Thread(target=w._annulla_il_dump)
    estraneo.start()
    estraneo.join(timeout=5.0)
    assert annulli == [], (
        "un thread che NON ha armato il dump lo ha annullato: e' esattamente "
        "la sequenza che uccide il processo con una violazione di accesso")

    w._annulla_il_dump()
    assert annulli == ["annullato"], (
        "il proprietario non e' riuscito ad annullare il proprio dump: la cura "
        "avrebbe rotto la pulizia invece di proteggerla")


def test_nessuno_annulla_quando_non_c_e_un_proprietario(monkeypatch) -> None:
    """Fuori da `hang_trace` non c'e' un dump nostro: nessuno lo tocca."""
    annulli: list[str] = []
    monkeypatch.setattr(
        w.faulthandler, "cancel_dump_traceback_later",
        lambda: annulli.append("annullato"))
    monkeypatch.setattr(w, "_proprietario_del_dump", None)

    w._annulla_il_dump()
    assert annulli == []


def test_l_annullamento_passa_da_un_punto_solo() -> None:
    """IL PRESIDIO: `cancel_dump_traceback_later` si chiama SOLO dentro
    `_annulla_il_dump`.

    Senza questa cella la cura dura fino alla prossima riga che chiama
    faulthandler direttamente — e quella riga sarebbe di nuovo un thread
    qualsiasi che annulla un dump non suo.

    Cerca con `ast` e non con una sottostringa: il nome della funzione compare
    anche nei commenti e nei docstring di questo modulo, che il difetto lo
    RACCONTANO.
    """
    sorgente = (Path(w.__file__)).read_text(encoding="utf-8")
    albero = ast.parse(sorgente)

    def annulla(n: ast.AST) -> bool:
        """DUE FORME, e la seconda me l'ha trovata Marie in revisione.

        `faulthandler.cancel_dump_traceback_later()` e' un `ast.Attribute`,
        ma `from faulthandler import cancel_dump_traceback_later` seguito da
        una chiamata nuda e' un `ast.Name`, e passava questo presidio.

        La riga e' copiata da `tests/test_rerank_breaker.py`, dove la stessa
        forma era gia' stata trovata e curata due giorni fa: una cura scritta
        in un file NON protegge il file accanto, e un presidio nuovo va
        guardato con le lezioni dei presidi vecchi in mano.
        """
        if not isinstance(n, ast.Call):
            return False
        return ((isinstance(n.func, ast.Attribute)
                 and n.func.attr == "cancel_dump_traceback_later")
                or (isinstance(n.func, ast.Name)
                    and n.func.id == "cancel_dump_traceback_later"))

    dentro: list[int] = []
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "_annulla_il_dump":
            dentro = [n.lineno for n in ast.walk(nodo) if annulla(n)]

    tutte = [n.lineno for n in ast.walk(albero) if annulla(n)]

    assert dentro, "`_annulla_il_dump` non annulla piu' niente: presidio cieco"
    fuori = sorted(set(tutte) - set(dentro))
    assert not fuori, (
        f"cancel_dump_traceback_later e' chiamata anche alle righe {fuori}, "
        "fuori dall'unico punto che verifica la proprieta' del dump: da li' "
        "un thread qualsiasi puo' annullare il dump di un altro")
