"""La lista funzionale aveva 6 forme articolate su 32.

`_QUERY_STOPWORDS` copre «del della dei delle nel nella» e nient'altro: mancano
tutte le forme di *a*, *da*, *su*, *con*, più `dello degli nello nei negli
nelle`. 26 su 32, e non sono rare — misurato sul corpus vero, 5343 fatti vivi::

    al      751 fatti  (14.1%)      alla    266  (5.0%)
    sul     590 fatti  (11.0%)      ai      254  (4.8%)
    dal     522 fatti   (9.8%)      sui     213  (4.0%)
    col     298 fatti   (5.6%)      dalla   204  (3.8%)

Il commento della lista prevede esattamente questo caso: «il filtro df NON le
prende — in un corpus di proposizioni dichiarative "what", "did", "on" sono
RARE (df bassa) ma il loro match è rumore puro. Linguistica, non
corpus-dipendente». `al` sta al 14,1%, ben sotto il `DF_CEILING` del 25%:
nessun filtro statistico la toglie, solo la lista può.

Le forme sono GENERATE dalla regola (preposizione × articolo), non elencate a
occhio: è l'unico modo perché la prossima persona non ne dimentichi altre sei.

DUE ESCLUSIONI DELIBERATE, e il motivo è misurato.

`ai` e `al` NON entrano. `_tokens` abbassa a minuscolo prima di consultare la
lista, e nel corpus vero::

    «AI» maiuscolo, parola intera:  281 fatti
    «ai» minuscolo (preposizione):  254 fatti
    «AL» maiuscolo:                  32 fatti

Metterle dentro toglierebbe l'acronimo AI dal percorso lessicale, in un corpus
che parla di AI — più occorrenze di quante ne guadagni. Vale finché la stoplist
è consultata sul testo abbassato: distinguere per capitalizzazione è una cura
diversa, e va misurata sul ranking prima di scriverla.
"""
from __future__ import annotations

import pytest

from verimem.bm25_rank import _QUERY_STOPWORDS, _tokens

#: preposizione -> forme articolate. La regola, non l'elenco.
ARTICOLATE = {
    "di": ["del", "dello", "della", "dei", "degli", "delle"],
    "a": ["al", "allo", "alla", "ai", "agli", "alle"],
    "da": ["dal", "dallo", "dalla", "dai", "dagli", "dalle"],
    "in": ["nel", "nello", "nella", "nei", "negli", "nelle"],
    "su": ["sul", "sullo", "sulla", "sui", "sugli", "sulle"],
    "con": ["col", "coi"],
}

#: Le due che collidono con sigle di questo dominio (AI, AL). Escluse con la
#: misura in cima al file, non per prudenza generica.
AMBIGUE = {"ai", "al"}

TUTTE = [f for forme in ARTICOLATE.values() for f in forme]


@pytest.mark.parametrize("forma", sorted(set(TUTTE) - AMBIGUE))
def test_ogni_forma_articolata_e_funzionale(forma):
    assert forma in _QUERY_STOPWORDS, (
        f"«{forma}» è una preposizione articolata e conta come parola di "
        f"contenuto nel percorso lessicale")


@pytest.mark.parametrize("forma", sorted(AMBIGUE))
def test_le_ambigue_restano_fuori_DI_PROPOSITO(forma):
    """Presidia l'esclusione: se un domani qualcuno «completa» la lista senza
    leggere la misura, questo test glielo dice."""
    assert forma not in _QUERY_STOPWORDS, (
        f"«{forma}» è entrata nella lista: la stoplist è consultata sul testo "
        f"abbassato, quindi toglie anche la sigla omografa (AI: 281 fatti nel "
        f"corpus contro 254 della preposizione)")


def test_una_domanda_italiana_resta_fatta_di_contenuto():
    got = _tokens("come si accede alla dashboard dal terminale della sede")
    assert "alla" not in got and "dal" not in got and "della" not in got, got
    assert {"accede", "dashboard", "terminale", "sede"} <= set(got), got


def test_non_mangia_le_parole_piene():
    """Controprova: la cura tocca le funzionali, non il contenuto."""
    got = set(_tokens("il costo del contratto con la ditta della zona"))
    assert {"costo", "contratto", "ditta", "zona"} <= got, sorted(got)


def test_una_sigla_omografa_sopravvive():
    """Il caso che ha deciso le esclusioni: «ai» resta perché AI resta."""
    assert "ai" in _tokens("quali modelli ai usiamo in produzione")


def test_le_inglesi_non_si_muovono():
    got = _tokens("how do you configure the backup of the machine")
    assert {"configure", "backup", "machine"} <= set(got), got
    assert not ({"the", "of", "how", "do"} & set(got)), got
