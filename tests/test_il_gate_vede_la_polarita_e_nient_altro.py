"""Il gate L1 vede UNA dimensione del significato: la polarita'.

Misurato il 2026-08-26 alle 20:11, `48e130f0`, fuori da pytest, store
temporaneo, regime SENZA source (`moat: not_run:no_source`, quindi L1 e'
l'unica difesa — con una source interviene anche il moat).

Su 12 rilevatori, tre frasi ciascuno:

    ① canoniche trattenute ................................ 9/12
    ② controlli (senso diverso) giustamente passati ....... 7/12
    ③ ELUSIONE: canonica TRATT ma riformulata passa ....... 9/9
    resistono (entrambe trattenute) ....................... NESSUNO

Ogni rilevatore che funziona viene eluso da una riformulazione equivalente,
e le riformulazioni non sono piu' deboli — sono uguali o piu' forti:

    «Il modulo e' stato testato»  TRATT L1.15  ·  «ha superato i test»  passa
    «Il sistema e' sicuro»        TRATT L1.12  ·  «non ci sono vulnerabilita'»  passa

Sull'altra popolazione l'errore e' opposto — 5 falsi positivi su 12, tutti su
frasi che vanto non sono: «sto provando se funziona» (intenzione), «valutiamo
se e' pronto» (valutazione), «andrebbe documentato/automatizzato/monitorato»
(TODO). Il gate premia chi si vanta con parole diverse e punisce chi ammette
un debito.

⚠️ Ma NON e' un dizionario cieco, e la prima stesura di questo banco lo dava
per tale a torto. La guardia sulla polarita' c'e' e funziona:

    «Il modulo NON e' documentato» · «NON e' stato testato» · «NON funziona»
    · «Il sistema NON e' sicuro»  ->  negazioni trattenute per errore: 0/5

Cio' che manca non e' la semantica: e' ogni dimensione semantica DIVERSA dalla
polarita' — sinonimia, diatesi, modalita'. La tesi si falsifica con una cella
sola: un sinonimo intercettato, o un condizionale non trattenuto.

Vicino di casa: `test_il_rilevatore_prestazioni_e_scritto_attivo.py` misura la
diatesi (attiva 4/4, passiva 1/4) sullo stesso gate.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory


@pytest.fixture()
def mem() -> Memory:
    return Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "pol.db"))


def _trattenuta(mem: Memory, frase: str) -> bool:
    return mem.add(frase, topic="polarita/prova").get("status") == "quarantined"


# ── ① IL RIGHELLO: senza questo, gli xfail sotto misurano me e non il prodotto
@pytest.mark.parametrize(
    "canonica",
    [
        "Il modulo e stato testato.",
        "Il servizio funziona correttamente.",
        "Il sistema e sicuro.",
        "Il modulo e documentato.",
    ],
)
def test_IL_RIGHELLO_la_forma_canonica_e_trattenuta(mem, canonica):
    assert _trattenuta(mem, canonica), (
        f"il controllo positivo e' caduto su {canonica!r}: il gate non intercetta "
        "nemmeno la forma canonica, quindi questo banco non misura il prodotto"
    )


# ── ② LA GUARDIA CHE C'E' E FUNZIONA: la polarita'. Non e' un dizionario cieco.
@pytest.mark.parametrize(
    "negata",
    [
        "Il modulo NON e stato testato.",
        "Il servizio NON funziona.",
        "Il sistema NON e sicuro.",
        "Il modulo NON e documentato.",
    ],
)
def test_LA_POLARITA_e_l_unica_dimensione_che_il_gate_rispetta(mem, negata):
    assert not _trattenuta(mem, negata), (
        f"{negata!r} e' una negazione, non un vanto: se viene trattenuta la "
        "guardia sulla polarita' si e' rotta e la tesi di questo banco cade"
    )


# ── ③ IL DIFETTO PER DIFETTO: sinonimia. Stesso significato, o piu' forte.
@pytest.mark.xfail(
    strict=True,
    reason="sinonimia invisibile al gate: elusione 9/9 sui rilevatori che "
    "funzionano, misurato 2026-08-26",
)
@pytest.mark.parametrize(
    "riformulata",
    [
        "Il modulo ha superato i test.",
        "Il servizio non da piu errori.",
        "Nel sistema non ci sono vulnerabilita.",
        "Per il modulo c e la documentazione.",
    ],
)
def test_LA_SINONIMIA_dovrebbe_essere_trattenuta_come_la_canonica(mem, riformulata):
    assert _trattenuta(mem, riformulata)


# ── ④ IL DIFETTO PER ECCESSO: modalita'. Una TODO non e' un vanto.
@pytest.mark.xfail(
    strict=True,
    reason="modalita' invisibile al gate: il condizionale «andrebbe» contiene "
    "la parola chiave e viene trattenuto come un vanto (5 falsi positivi su 12)",
)
@pytest.mark.parametrize(
    "todo",
    [
        "Il modulo andrebbe documentato.",
        "Il processo andrebbe automatizzato.",
        "Il servizio andrebbe monitorato.",
    ],
)
def test_LA_MODALITA_una_TODO_non_dovrebbe_essere_trattenuta(mem, todo):
    assert not _trattenuta(mem, todo)
