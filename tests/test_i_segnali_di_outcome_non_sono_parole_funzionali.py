"""I segnali di `outcome_pattern` non sono parole funzionali italiane.

⚠️ **NASCE DA `W7-85`**, dove chiamando il tool MCP `hippo_outcome_patterns`
sul corpus vero uscivano fra i *«tokens correlated with success»*::

    per   41 occorrenze
    con   37
    non   25

La `_STOP` del modulo aveva **11 voci inglesi e zero italiane**, in un prodotto
i cui `task_text` sono scritti in italiano. E' la **classe ③ — liste
monolingue**, la stessa che avevo gia' curato in `verimem/vicinato_del_valore.py`
(`W7-84`).

MISURATO PRIMA DI CURARE (`W7-100`, A/B **nella stessa esecuzione**, 459
episodi, funzione pura)::

    segnali che CAMBIANO      3
    TOLTI                     per · con · non      <- le tre di `W7-85`
    NUOVI                     live · audit · pqc-audit-italia

⇒ 🔑 **La cura tocca esattamente cio' che doveva**: toglie tre parole
funzionali dalla cima della classifica e ne lascia entrare tre piene. **Non
rifa' la classifica: la ripulisce.** I primi nove segnali non si muovono.

⚖️ **COSA NON CAMBIA**: la funzione, le soglie, l'ordinamento. Cambia **quali
token sono considerati informativi**, ed e' esattamente cio' che la lista serve
a decidere.

🔴 **AMBIGUI TENUTI FUORI DI PROPOSITO**: «danno», «conta», «stato», «era»,
«parte», «caso», «modo», «punto», «campo», «resto», «fine», «torno» in italiano
sono **anche sostantivi**. Una parola che puo' nominare qualcosa non entra in
una lista di non-parole, per quanto frequente sia come funzione.

⚠️ **PERIMETRO DICHIARATO**: `failure_clusters.py` e `failure_diagnosis.py`
hanno la **stessa lista monolingue**, ma funzioni diverse e **non li ho
misurati**. Non li tocco: una cura si applica dove l'effetto e' stato visto.
"""

from __future__ import annotations

import pytest

from verimem.outcome_pattern import _STOP

#: le tre che uscivano come segnali in `W7-85`, piu' le altre funzioni
#: italiane trovate nel corpus. Nessuna di queste puo' essere un sostantivo.
FUNZIONALI = ["per", "con", "non", "che", "come", "nel", "nella", "sul",
              "sulla", "dei", "delle", "degli", "dal", "dalla", "alla",
              "una", "uno", "gli", "piu", "anche", "solo", "quando", "dove",
              "sono", "hanno"]

#: parole che in italiano sono ANCHE sostantivi: NON devono entrare.
AMBIGUE = ["danno", "conta", "stato", "era", "parte", "caso", "modo",
           "punto", "campo", "resto", "fine"]


@pytest.mark.parametrize("parola", FUNZIONALI)
def test_le_funzionali_italiane_sono_filtrate(parola: str) -> None:
    """Il cuore: `per`, `con` e `non` non devono uscire come «correlated
    with success»."""
    assert parola in _STOP, (
        f"«{parola}» non e' filtrata: puo' comparire fra i segnali")


@pytest.mark.parametrize("parola", AMBIGUE)
def test_le_ambigue_NON_sono_filtrate(parola: str) -> None:
    """In italiano sono anche sostantivi: filtrarle toglierebbe un segnale
    possibile. E' il presidio che impedisce alla lista di crescere a caso."""
    assert parola not in _STOP, (
        f"«{parola}» e' anche un sostantivo: filtrarla toglie un segnale")


def test_l_inglese_resta_coperto() -> None:
    """La cura AGGIUNGE, non sostituisce: le voci inglesi restano."""
    for parola in ("the", "and", "was", "with", "this"):
        assert parola in _STOP


def test_la_lista_non_e_esplosa() -> None:
    """Un presidio contro la crescita indiscriminata: se un giorno qualcuno
    ci versa dentro un dizionario, questo test lo dice."""
    assert len(_STOP) < 120, (
        f"`_STOP` ha {len(_STOP)} voci: e' diventata un dizionario, e una"
        " stop-list che cresce senza misura toglie segnali veri")
