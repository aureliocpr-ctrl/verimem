"""«Quante volte ho parlato DEL moat» contava un terzo in meno di «del moat».

`count` è documentato come «Set-size, NOT top-k — the honest primitive for
aggregation queries» e promette di vedere «the WHOLE matching set». Usa
`search_facts(require_all_tokens=True)`, cioè un AND su TUTTI i token — e i
token includono gli articoli e le preposizioni.

Misurato sul corpus vero, 5333 fatti vivi::

    moat        207   ->  del moat       134    73 persi  (35%)
    commit     1324   ->  un commit     1126   198 persi  (15%)
    gate        942   ->  il gate        877    65 persi   (7%)
    recall      559   ->  la recall      512    47 persi   (8%)
    skill       359   ->  le skill       323    36 persi  (10%)

429 fatti persi su otto coppie, e nessuno di quei fatti parla di qualcosa di
diverso: parlano dello stesso argomento senza quell'articolo.

È lo SPECULARE della cura di stamattina (`2f2c667e`): nel ramo OR le parole
funzionali ALLARGANO a caso, qui nel ramo AND RESTRINGONO a caso. E correggo
un mio ragionamento di quel commit, dove avevo scritto che
`require_all_tokens` «è il percorso di precisione, dove una funzionale in più
STRINGE invece di allargare» e l'avevo classificato come non-problema. Per una
RICERCA è vero — chi cerca una frase esatta vuole che stringa. Per un
CONTEGGIO il cui contratto è «vedo tutto l'insieme», no.

Quindi la cura sta in `count` e non in `search_facts`: contare quante volte si
è parlato di X non dipende dall'articolo con cui si nomina X. La ricerca resta
identica.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

CORPUS = [
    "Il moat giudica la fonte contro il fatto.",
    "Senza source il moat non gira.",
    "Moat e gate sono due nomi della stessa cosa.",
    "La quarantena tiene fuori dal recall di default.",
]


@pytest.fixture()
def store():
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in CORPUS:
        m.add(t, topic="note")
    return m


def test_una_preposizione_non_cambia_il_conteggio(store):
    nudo = store.count(query="moat")
    con = store.count(query="del moat")
    assert con == nudo, (
        f"«del moat» conta {con} dove «moat» conta {nudo}: la preposizione "
        f"ha tolto fatti che parlano dello stesso argomento")


def test_ne_un_articolo(store):
    assert store.count(query="il moat") == store.count(query="moat")


def test_le_parole_di_CONTENUTO_contano_eccome(store):
    """La controprova che tiene in piedi il senso di `count`: due termini veri
    restringono, ed è giusto che lo facciano."""
    assert store.count(query="moat gate") < store.count(query="moat")


def test_una_query_di_soli_articoli_non_conta_tutto(store):
    """Senza token informativi non c'è insieme da contare: zero, non tutto."""
    assert store.count(query="il la del") == 0


def test_il_conteggio_senza_query_non_si_muove(store):
    """Il ramo che conta il corpus intero non passa dai token."""
    assert store.count() == len(CORPUS)


def test_la_ricerca_resta_com_era(store):
    """Il perimetro della cura: `search_facts` con require_all_tokens è il
    percorso di precisione e NON cambia. Chi cerca la frase la trova ancora,
    e chi cerca due parole di cui una funzionale continua a stringere."""
    sm = store.semantic
    con = sm.search_facts("il moat", limit=100, require_all_tokens=True)
    senza = sm.search_facts("moat", limit=100, require_all_tokens=True)
    assert len(con) < len(senza), (
        "la ricerca ha smesso di stringere: la cura ha invaso il percorso di "
        "precisione invece di restare in `count`")
