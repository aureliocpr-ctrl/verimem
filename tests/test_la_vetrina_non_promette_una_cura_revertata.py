"""La vetrina non puo' promettere una capacita' che il codice non ha piu'.

NASCE DA UN CASO, IL 07/09
==========================
`CHANGELOG.md` e `README.md` annunciavano la **coesistenza fra fonti distinte**
(«Two facts from different sources coexist», ricevuta `L3-fonti-distinte`).
Quella cura e' stata **revertita** da `05c26887` il 06/09 alle 15:31, 46 minuti
dopo che il testo era stato scritto (`f552e6eb`, 14:45). Prova, oltre al grep:
il test che i suoi stessi autori avevano scritto
(`tests/test_due_fonti_dichiarate_non_si_ritirano.py`, tolto dal revert),
ripreso dal padre del revert ed eseguito sul tip, **non si importa nemmeno**:
`ImportError: cannot import name 'due_fonti_dichiarate_e_diverse'`.

L'08/09 il CHANGELOG era stato ripulito e **il README no**: la riga 339 era
ancora li'. E' la stessa forma del banner curato in cima e non nell'Install:
**si corregge il posto che si sta guardando, e la frase resta nell'altro.**

PERCHE' UN PRESIDIO E NON UNA RIGA DI ELENCO
--------------------------------------------
Vietare la frase per sempre sarebbe sbagliato: se la cura rientra nella 0.7.8,
la riga torna VERA e il presidio la bloccherebbe a torto. Quindi qui la promessa
e' **legata al codice**: la vetrina puo' dire «coesistono» **se e solo se** la
funzione che lo fa esiste. Il giorno che rientra, questo file diventa verde da
solo — senza che nessuno si ricordi di aggiornarlo.

⚠️ LIMITE DICHIARATO: guarda il SORGENTE (`ast`), non l'importabilita'. Prova che
il codice c'e', non che funzioni: e' il verso che serve qui, perche' se il codice
NON c'e' la promessa e' certamente falsa.
"""
from __future__ import annotations

import ast
import pathlib
import re

RADICE = pathlib.Path(__file__).resolve().parents[1]
README = RADICE / "README.md"
CHANGELOG = RADICE / "CHANGELOG.md"
POLICY = RADICE / "verimem" / "supersession_policy.py"

#: la promessa, come la legge un utente, e il nome che la implementa
_PROMESSA = re.compile(r"different sources coexist|L3-fonti-distinte", re.I)
_FUNZIONE = "due_fonti_dichiarate_e_diverse"


def _nomi_definiti(percorso: pathlib.Path) -> set[str]:
    albero = ast.parse(percorso.read_text(encoding="utf-8", errors="replace"))
    fuori = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            fuori.add(nodo.name)
        elif isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store):
            fuori.add(nodo.id)
    return fuori


def _righe_che_promettono(percorso: pathlib.Path) -> list[str]:
    if not percorso.exists():
        return []
    return [
        f"{percorso.name}:{n}: {r.strip()[:110]}"
        for n, r in enumerate(percorso.read_text(encoding="utf-8", errors="replace")
                              .splitlines(), 1)
        if _PROMESSA.search(r)
    ]


def test_CONTROLLO_il_presidio_sa_leggere_il_codice():
    """Se il file della policy non si legge, ogni verdetto sotto e' cieco."""
    assert POLICY.exists(), f"non trovo {POLICY}"
    nomi = _nomi_definiti(POLICY)
    assert len(nomi) > 5, (
        f"in {POLICY.name} vedo solo {len(nomi)} nomi definiti: il parser non "
        "sta leggendo il file davvero, quindi il test sotto non vale."
    )


def test_la_coesistenza_si_promette_solo_se_il_codice_la_fa():
    promesse = _righe_che_promettono(README) + _righe_che_promettono(CHANGELOG)
    esiste = _FUNZIONE in _nomi_definiti(POLICY)
    if esiste:
        return  # la cura c'e': la vetrina puo' dirlo, e questo file tace
    assert not promesse, (
        f"la vetrina promette la coesistenza fra fonti, ma `{_FUNZIONE}` non "
        f"esiste in {POLICY.name}: la cura e' stata revertita (05c26887, "
        "06/09) e il testo non l'ha seguita. Righe:\n  " + "\n  ".join(promesse)
    )
