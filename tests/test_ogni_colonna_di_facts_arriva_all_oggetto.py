"""Ogni colonna della tabella che è anche un campo di ``Fact`` viene ricostruita.

La ricostruzione di un ``Fact`` da una riga del database elenca i campi **a mano**.
Tre volte un campo nuovo è stato aggiunto allo schema e alla scrittura, e non a
quell'elenco: ``writer_role`` nel giugno, ``writer_principal`` il 30 luglio,
``grounding_span`` il 14 agosto. Ogni volta il dato era sul disco e nessuna
lettura lo restituiva, e ogni volta è stato trovato per caso — quando una
superficie ha iniziato a mostrarlo.

Questo collaudo non cerca il caso: confronta le **colonne della tabella** con gli
**argomenti passati al costruttore**, e fallisce da solo la prossima volta che i
due elenchi divergono.

Come è misurato, e perché così:

- l'elenco degli argomenti si estrae con ``ast``, non con una ricerca testuale.
  Due misure fatte con ``grep`` hanno sbagliato durante la stesura: ``source_signature``
  arriva da una variabile locale e non da ``_opt(...)``, e una finestra di 4200
  caratteri tagliava metà del blocco. Un albero sintattico non ha questi difetti.
- lo schema si legge da uno store **temporaneo**, cioè da quello che il prodotto
  crea oggi, e non dal database di chi esegue i test.
- le colonne che non sono campi del dataclass sono fuori perimetro per
  costruzione: si confronta l'intersezione, non l'unione, così una colonna di
  servizio non produce un falso allarme.

Il secondo test è quello che tiene onesto il primo. Un criterio che riporta zero
può essere spento: qui gli si toglie un campo dal sorgente e si verifica che il
conteggio cambi. Misurato durante la stesura sui due stati reali — sul sorgente
curato riporta 0, sul sorgente precedente riporta ``['grounding_span']``.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest

from verimem import semantic as modulo_semantico
from verimem.semantic import Fact, SemanticMemory


def _argomenti_del_costruttore(sorgente: str) -> set[str]:
    """I nomi passati per chiave a ``Fact(...)`` dentro ``_row``."""
    for nodo in ast.walk(ast.parse(sorgente)):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "_row":
            for chiamata in ast.walk(nodo):
                if (isinstance(chiamata, ast.Call)
                        and getattr(chiamata.func, "id", "") == "Fact"):
                    return {k.arg for k in chiamata.keywords if k.arg}
    raise AssertionError(
        "la funzione `_row` o la sua chiamata a Fact(...) non esistono più: "
        "questo collaudo va riscritto, non cancellato")


def _colonne_della_tabella(percorso: Path) -> set[str]:
    store = SemanticMemory(db_path=percorso)
    with store._connect() as conn:  # noqa: SLF001 — lettura di collaudo
        return {r[1] for r in conn.execute("PRAGMA table_info(facts)")}


@pytest.fixture(scope="module")
def sorgente() -> str:
    return Path(inspect.getfile(modulo_semantico)).read_text(encoding="utf-8")


def test_nessuna_colonna_resta_indietro(tmp_path: Path, sorgente: str):
    """Il collaudo che chiude la classe: schema e costruttore non divergono."""
    nomi_del_dataclass = {f.name for f in dataclasses.fields(Fact)}
    attesi = _colonne_della_tabella(tmp_path / "semantic.db") & nomi_del_dataclass
    assert attesi, "il banco è rotto: nessuna colonna coincide con un campo"

    mancanti = attesi - _argomenti_del_costruttore(sorgente)
    assert not mancanti, (
        f"queste colonne esistono, sono campi di Fact, e la ricostruzione non le "
        f"legge: {sorted(mancanti)}. Il dato è sul disco e nessuna lettura lo "
        f"restituisce — è la quarta volta. Aggiungerle a `Fact(...)` in `_row`.")


def test_il_criterio_si_accorge_di_un_campo_tolto(tmp_path: Path, sorgente: str):
    """Il controllo positivo del controllo: spento, il primo test non direbbe nulla."""
    vittima = "grounding_span"
    assert vittima in _argomenti_del_costruttore(sorgente)

    mutilato = sorgente.replace(f'            {vittima}=_opt("{vittima}"),\n', "", 1)
    assert mutilato != sorgente, "la riga da togliere non è stata trovata"

    assert vittima not in _argomenti_del_costruttore(mutilato), (
        "il criterio non distingue un sorgente a cui manca un campo da uno "
        "completo: riporterebbe zero comunque, ed è un sensore scollegato")
