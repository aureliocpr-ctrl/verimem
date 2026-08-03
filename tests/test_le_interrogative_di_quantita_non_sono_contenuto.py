"""Tutte le interrogative italiane erano nella lista tranne quelle di QUANTITÀ.

`bm25_rank._QUERY_STOPWORDS` contiene `quale quali cosa chi quando dove perche
come` — e non `quanto quanta quanti quante`. Cioè proprio quelle che
introducono una domanda di CONTEGGIO, che è il caso d'uso di `Memory.count` e
del router di cardinalità.

Trovato misurando un asse mai toccato — la lunghezza della QUERY, non del
fatto — su uno store di quattro fatti di listino::

    count(query="quanto costa il piano annuale")  ->  0

mentre «Il piano annuale di VeriMem costa 100 euro.» è nello store. `count` fa
un AND sui token informativi, «quanto» resta fra questi, e nessun fatto lo
contiene.

E IL PRODOTTO LE CONOSCE GIÀ, altrove. `query_intent._STOP` — la lista del
router che riconosce le domande di cardinalità — ha `how many much number count
times quanti quante volte numero`. Due liste, due verità:

    parola     bm25   query_intent
    quanti      NO         SI
    quante      NO         SI
    quanto      NO         NO      <- manca in ENTRAMBE, ed è il singolare
    quanta      NO         NO
    many        NO         SI
    much        NO         SI

`query_intent` ha i PLURALI e non i singolari: una dimenticanza di genere, non
di criterio.

QUELLO CHE NON ENTRA, e perché — misurato sul corpus vero (5371 fatti vivi)::

    count    43 occorrenze     è il nome di un metodo di questo prodotto
    numero  139                «il numero di fatti è 205»
    volte    75                «quante volte ho parlato del moat»
    times     3 / number 10    stessa famiglia, sostantivi

Sono SOSTANTIVI, e in questo dominio sono contenuto: toglierli dalla ricerca
renderebbe non cercabili i fatti che parlano di `count`. Stessa decisione presa
ieri per `ai` (281 occorrenze come sigla contro 254 come preposizione).

Entrano solo le INTERROGATIVE PURE — `quanto quanta quanti quante many much` —
che non sono mai il soggetto di una frase (`many` 3 occorrenze, `much` 1).
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory
from verimem.bm25_rank import _QUERY_STOPWORDS, _tokens

#: Le interrogative di quantità. Nessuna è mai il soggetto di una frase.
INTERROGATIVE = ["quanto", "quanta", "quanti", "quante", "many", "much"]

#: I sostantivi omografi che NON entrano, con la loro frequenza nel corpus.
#: Un test presidia l'esclusione: sono contenuto, non grammatica.
SOSTANTIVI = ["count", "number", "numero", "volte", "times"]


@pytest.mark.parametrize("parola", INTERROGATIVE)
def test_una_interrogativa_di_quantita_non_e_contenuto(parola):
    assert parola in _QUERY_STOPWORDS, (
        f"«{parola}» introduce una domanda di conteggio e conta come termine "
        f"da cercare: `count` ne esce a zero")


@pytest.mark.parametrize("parola", SOSTANTIVI)
def test_i_sostantivi_omografi_restano_cercabili(parola):
    """Presidia l'esclusione: se qualcuno «completa» la lista senza leggere le
    frequenze, i fatti che parlano di `count` diventano introvabili."""
    assert parola not in _QUERY_STOPWORDS, (
        f"«{parola}» è entrata nella lista: in questo dominio è un sostantivo "
        f"(count 43 occorrenze — è un metodo del prodotto; numero 139; "
        f"volte 75) e toglierlo rende non cercabili i fatti che ne parlano")


def test_il_conteggio_risponde_a_una_domanda_di_conteggio():
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    for t in ["Il piano annuale di VeriMem costa 100 euro.",
              "La prova gratuita dura 14 giorni."]:
        m.add(t, topic="listino")
    assert m.count(query="quanto costa il piano annuale") == 1, (
        "una domanda di conteggio conta zero sul fatto che la risponde")


def test_l_interrogativa_non_cambia_il_conteggio():
    """L'interrogativa davanti non può cambiare quello che si conta.

    ⚠️ La prima stesura confrontava «quanto costa il piano» con «quanti piani
    costano» e falliva 1 contro 0 — ma per un'altra ragione: «piani costano»
    sono forme FLESSE che il LIKE non riconduce a «piano costa». Chiedeva al
    prodotto un matching morfologico che non promette. Qui variano solo le
    interrogative, che è ciò che questo file misura."""
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s2.db"))
    m.add("Il piano annuale costa 100 euro.", topic="listino")
    nudo = m.count(query="costa piano")
    assert nudo == 1, nudo
    for domanda in ("quanto costa il piano", "quanta costa il piano",
                    "quanti costa il piano", "quante costa il piano",
                    "how much costa il piano", "how many costa il piano"):
        assert m.count(query=domanda) == nudo, (
            f"«{domanda}» conta {m.count(query=domanda)} dove la stessa "
            f"domanda senza l'interrogativa conta {nudo}")


def test_il_contenuto_della_domanda_resta():
    got = _tokens("quante volte ho parlato del moat")
    assert "moat" in got and "volte" in got, got
    assert "quante" not in got, got
