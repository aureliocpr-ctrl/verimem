"""In lettura chi decide se un token e' un'entita' e' lo STORE, non una regex.

Perche' questo file esiste (misurato sul corpus reale il 25/07). Il grafo di
entita' e' ricco — 8005 entita, 24953 legami fatto-entita, 81477 archi — e
``ppr_seeded_fact_ids`` restituiva 0 id in 0.0 ms su OGNI query reale: il
segnale-grafo, quello che i doc chiamano il moat del retrieval, era spento in
produzione. Non perche' il PPR non scali (a caldo costa 103 ms), ma perche' non
partiva: nessun seed.

La causa e' un'asimmetria che nessuno aveva visto. ``extract_entities_lite`` e'
tarato per l'INGEST, dove un falso positivo sporca il grafo per sempre, quindi
e' deliberatamente conservativo e non ha alcun pattern per una parola minuscola
singola. Misurato: 'verimem' -> [], 'Verimem' -> [] (guardia sull'iniziale di
frase), 'Cortex e Verimem' -> ['Verimem'] solo perche' non e' la prima parola.
Ma i nomi propri di questo corpus SONO minuscoli: verimem, cortex, engram.

In LETTURA l'economia e' rovesciata. Un falso positivo costa zero, perche' lo
store lo scarta: ``get_by_name('perde')`` -> None. Un falso negativo costa
tutto: nessun seed, nessun PPR. E lo store e' un arbitro migliore di qualunque
regex — ``get_by_name`` risolve verimem/Verimem/VERIMEM allo stesso id e
restituisce None per 'cortex', che nel grafo non c'e'. Evidence decides.
"""
from __future__ import annotations

import pytest

from verimem.entity_kg import Entity, EntityStore
from verimem.ppr_seed import ppr_seeded_fact_ids


def _store(tmp_path):
    return EntityStore(db_path=tmp_path / "ekg.db")


def _entita(es, nome: str, *, fatti: list[str], tipo: str = "proper") -> str:
    eid = es.store(Entity(canonical_name=nome, type=tipo))
    for f in fatti:
        es.link_fact(f, eid)
    es.add_edge(eid, eid, "self", weight=1.0)     # un nodo serve al PPR
    return eid


def test_a_lowercase_one_word_name_seeds_the_graph(tmp_path):
    """Il caso di produzione, ed e' il caso normale: un prodotto che si chiama
    'verimem'. Prima di questo fix la query non produceva nessun seed e il fatto
    collegato non veniva mai ripescato dal grafo."""
    es = _store(tmp_path)
    _entita(es, "verimem", fatti=["f_verimem"])
    ids = ppr_seeded_fact_ids("verimem perde fatti veri nel parser", es)
    assert "f_verimem" in ids, (
        "un nome proprio minuscolo non semina il grafo: il segnale-grafo resta "
        "spento su qualunque corpus i cui nomi propri siano minuscoli")


def test_the_name_seeds_it_even_as_the_first_word(tmp_path):
    """La guardia sull'iniziale di frase e' giusta per l'ingest (in inglese la
    prima parola e' maiuscola per grammatica) e sbagliata per una query, dove il
    soggetto sta quasi sempre all'inizio."""
    es = _store(tmp_path)
    _entita(es, "Verimem", fatti=["f_maiuscolo"])
    ids = ppr_seeded_fact_ids("Verimem ha perso dei fatti", es)
    assert "f_maiuscolo" in ids


def test_a_word_the_store_does_not_know_never_becomes_a_seed(tmp_path):
    """Il contrappeso: risolvere non vuol dire inondare. Un token che nello
    store non esiste non produce nessun seed, quindi il costo di provarci e'
    zero e il rumore non entra."""
    es = _store(tmp_path)
    _entita(es, "verimem", fatti=["f_verimem"])
    assert ppr_seeded_fact_ids("quante righe ha scritto ieri sera", es) == []


def test_stopwords_are_never_looked_up(tmp_path):
    """Le parole grammaticali non vanno nemmeno interrogate: sono la maggior
    parte dei token di una query in italiano, e ogni lookup e' una query SQL."""
    es = _store(tmp_path)
    _entita(es, "verimem", fatti=["f1"])
    interrogati: list[str] = []
    vero = es.get_by_name

    def _spia(nome):
        interrogati.append((nome or "").lower())
        return vero(nome)

    es.get_by_name = _spia                        # type: ignore[method-assign]
    ppr_seeded_fact_ids("il recall di verimem e' lento con la cache", es)
    assert "verimem" in interrogati, "il nome non e' stato nemmeno cercato"
    for grammaticale in ("il", "di", "la", "con"):
        assert grammaticale not in interrogati, (
            f"interrogato lo store per la stopword {grammaticale!r}")


def test_the_hub_guard_still_applies_to_resolved_seeds(tmp_path):
    """La protezione esistente non deve essere scavalcata dalla via nuova: un
    seed che linka piu' del 20% dei fatti non discrimina niente e il suo PPR e'
    quasi uniforme (fact a2217252f9ad). Vale per i seed risolti dai token
    esattamente come per quelli estratti."""
    es = _store(tmp_path)
    # 'aurelio' linka TUTTI i fatti: e' l'entita'-utente, un hub puro.
    tutti = [f"f{i}" for i in range(60)]
    _entita(es, "aurelio", fatti=tutti)
    ids = ppr_seeded_fact_ids("cosa ha fatto aurelio", es)
    assert ids == [], f"un hub e' entrato come seed: {ids[:5]}"


def test_extractor_seeds_keep_priority(tmp_path):
    """Si ESTENDE, non si sostituisce: i seed dell'estrattore (multiparola,
    piu' specifici) restano davanti, cosi' il comportamento storico non cambia
    e la via nuova occupa solo i posti liberi.

    L'asserzione e' sui SEED, non sui fatti restituiti: su un grafo di due
    fatti il PPR li restituisce entrambi anche con score 0, quindi un assert
    sui fatti passa identico senza il fix — l'ho verificato prima di scriverlo
    cosi'."""
    es = _store(tmp_path)
    estratto = _entita(es, "alpha_service", fatti=["f_estratto"], tipo="code")
    risolto = _entita(es, "verimem", fatti=["f_risolto"])
    visti: list[list[str]] = []
    vero_ppr = es.ppr

    def _spia(seeds, *a, **kw):
        visti.append(list(seeds))
        return vero_ppr(seeds, *a, **kw)

    es.ppr = _spia                                # type: ignore[method-assign]
    ppr_seeded_fact_ids("alpha_service e verimem insieme", es)
    assert visti, "il PPR non e' stato nemmeno invocato"
    seeds = visti[0]
    assert estratto in seeds and risolto in seeds, (
        f"una delle due vie e' stata persa: {seeds}")
    assert seeds.index(estratto) < seeds.index(risolto), (
        f"la via nuova ha scavalcato l'estrattore: {seeds}")


@pytest.mark.parametrize("query", ["", None, "   "])
def test_fail_soft_is_unchanged(tmp_path, query):
    """Il contratto fail-soft del modulo non cambia."""
    assert ppr_seeded_fact_ids(query, _store(tmp_path)) == []
    assert ppr_seeded_fact_ids("verimem", None) == []


def test_max_seeds_is_respected_across_both_paths(tmp_path):
    """Il tetto sui seed vale sulla somma delle due vie, altrimenti una query
    lunga farebbe esplodere la personalizzazione del PPR."""
    es = _store(tmp_path)
    nomi = [f"nome{i}" for i in range(12)]
    for n in nomi:
        _entita(es, n, fatti=[f"f_{n}"])
    interrogati: list[str] = []
    vero = es.get_by_name

    def _spia(nome):
        r = vero(nome)
        if getattr(r, "id", None):
            interrogati.append(nome)
        return r

    es.get_by_name = _spia                        # type: ignore[method-assign]
    ppr_seeded_fact_ids(" ".join(nomi), es, max_seeds=3)
    assert len(interrogati) <= 3, (
        f"risolti {len(interrogati)} seed con max_seeds=3: {interrogati}")
