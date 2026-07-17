"""Quality guards sulla fusione PPR+BM25 (blocco grafo 2026-07-07).

Diagnosi (fact a2217252f9ad, store e2e HaluMem u1): a k=12 la fusione RRF
DANNEGGIAVA il retrieval — all-cov evidence 16/61 dense-only vs 8/61 con
fusione — perché su un grafo hub-dominated il PPR seedato sull'hub utente è
quasi-random, e BM25 su query di soli token comuni è quasi-random: RRF cieco
dà 2/3 del top-k a rumore, sfrattando i dense hit già CE-verificati.

Tre guardie, tutte attive SOLO su corpus non-piccoli (>= floor 50, coerente
con ENGRAM_PPR_FUSION_FLOOR) così i comportamenti su store piccoli — e i test
storici — restano byte-identici:

  1. hub-guard: un seed PPR la cui entità linka una quota alta dei fatti del
     corpus non discrimina nulla → escluso; nessun seed informativo → [].
  2. token informativi BM25: la MATCH query usa solo i token con document
     frequency bassa; una query di soli token onnipresenti → [].
  3. dense-floor: la fusione può ESTENDERE ma mai sfrattare la testa dense
     (CE-reranked) — i primi ``protect_top`` hit restano in testa.
"""
from __future__ import annotations

from verimem.bm25_rank import bm25_fact_ids
from verimem.entity_kg import Entity, EntityStore
from verimem.ppr_seed import fuse_dense_and_ppr, ppr_seeded_fact_ids
from verimem.semantic import Fact, SemanticMemory


class _F:
    def __init__(self, fid: str) -> None:
        self.id = fid


# ---------------------------------------------------------------- hub-guard

def _kg_with_hub(tmp_path, *, n_facts: int = 60):
    """Entity-KG: 'hub' linka TUTTI gli n fatti, 'niche' ne linka 2."""
    es = EntityStore(db_path=tmp_path / "ekg.db")
    hub = es.store(Entity(canonical_name="hub_person", type="proper"))
    niche = es.store(Entity(canonical_name="niche_topic", type="code"))
    es.add_edge(hub, niche, "rel", weight=1.0)
    with es.session():
        for i in range(n_facts):
            es.link_fact(f"fact{i}", hub)
    es.link_fact("fact1", niche)
    es.link_fact("fact2", niche)
    return es


def test_hub_only_seed_returns_empty_on_large_corpus(tmp_path):
    es = _kg_with_hub(tmp_path)
    # la query risolve SOLO l'hub (linka 60/60 fatti = non-discriminante)
    assert ppr_seeded_fact_ids("what did hub_person do", es) == []


def test_niche_seed_survives_next_to_hub(tmp_path):
    es = _kg_with_hub(tmp_path)
    # query con hub + entità di nicchia: l'hub è scartato, la nicchia seeda
    ids = ppr_seeded_fact_ids("hub_person and the niche_topic plan", es)
    assert ids, "il seed di nicchia deve produrre un ranking"
    assert set(ids[:2]) <= {"fact1", "fact2"}, (
        "i fatti della nicchia devono dominare il ranking, non l'hub flood"
    )


def test_hub_guard_inactive_on_small_corpus(tmp_path):
    """Sotto il floor (corpus piccolo) nessuna esclusione: il comportamento
    storico resta identico anche se l'unica entità linka il 100% dei fatti."""
    es = EntityStore(db_path=tmp_path / "ekg.db")
    a = es.store(Entity(canonical_name="alpha_service", type="module"))
    b = es.store(Entity(canonical_name="beta_service", type="module"))
    es.add_edge(a, b, "rel", weight=1.0)
    es.link_fact("factX", a)
    assert "factX" in ppr_seeded_fact_ids("what changed in alpha_service", es)


# ------------------------------------------------- BM25 informative tokens

def _sm_with_common_token(tmp_path, *, n: int = 60):
    """Corpus dove OGNI fatto contiene 'guests'; uno solo contiene 'zanzibar'."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    rare = Fact(proposition="guests itinerary planned for zanzibar retreat",
                topic="t/r")
    sm.store(rare, embed="auto")
    for i in range(n - 1):
        sm.store(Fact(proposition=f"guests visited the property in week {i}",
                      topic="t/c"), embed="auto")
    return sm, rare


def test_bm25_all_common_tokens_returns_empty(tmp_path):
    sm, _ = _sm_with_common_token(tmp_path)
    # 'guests' appare nel 100% del corpus: match non-informativo → []
    assert bm25_fact_ids("guests", str(sm.db_path)) == []


def test_bm25_rare_token_still_ranks(tmp_path):
    sm, rare = _sm_with_common_token(tmp_path)
    ids = bm25_fact_ids("guests zanzibar", str(sm.db_path))
    assert ids and ids[0] == rare.id, (
        "il token raro deve continuare a matchare (e primo) anche col filtro df"
    )


def test_bm25_question_words_never_match(tmp_path):
    """Le question/function word ('what did … on') hanno df BASSA in un corpus
    di proposizioni dichiarative — il filtro df da solo le lascia passare e il
    loro match è rumore puro (i 3 flip residui del micro-bench). La stoplist
    linguistica le toglie SEMPRE, a prescindere dalla taglia del corpus."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    noise = Fact(proposition="note about what did happen on the day",
                 topic="t/n")
    sm.store(noise, embed="auto")
    for i in range(4):
        sm.store(Fact(proposition=f"guest visit number {i} recorded",
                      topic="t/c"), embed="auto")
    # query di soli token funzionali → nessun token informativo → []
    assert bm25_fact_ids("what did on the", str(sm.db_path)) == []
    # i token contenuto continuano a matchare
    assert bm25_fact_ids("guest visit", str(sm.db_path)) != []


def test_bm25_df_filter_inactive_on_small_corpus(tmp_path):
    """Sotto il floor il filtro df NON si applica (contratto storico)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    a = Fact(proposition="alpha baseline note", topic="t")
    sm.store(a, embed="auto")
    sm.store(Fact(proposition="alpha second note", topic="t"), embed="auto")
    # 'alpha' ha df=100% ma il corpus è minuscolo → nessun filtro
    assert bm25_fact_ids("alpha", str(sm.db_path)) != []


# ---------------------------------------------------------------- dense-floor

def test_fuse_protect_top_keeps_ce_head_intact():
    dense = [(_F(f"d{i}"), 1.0 - i * 0.05) for i in range(12)]
    # extra ranklist "rumorosa": 20 id sconosciuti che RRF-fonderebbero in testa
    noise = [f"x{i}" for i in range(20)]
    fused = fuse_dense_and_ppr(dense, [noise], lambda fid: _F(fid),
                               protect_top=6)
    head = [f.id for f, _ in fused[:6]]
    assert head == ["d0", "d1", "d2", "d3", "d4", "d5"], (
        "i primi protect_top dense hit (testa CE-verified) sono intoccabili"
    )
    tail_ids = {f.id for f, _ in fused[6:]}
    assert tail_ids & set(noise), (
        "gli extra competono comunque per gli slot di coda (extend, not evict)"
    )


def test_fuse_protect_top_zero_is_legacy_behaviour():
    dense = [(_F("d0"), 0.9), (_F("d1"), 0.8)]
    extra = ["e0"]
    legacy = fuse_dense_and_ppr(dense, [extra], lambda fid: _F(fid))
    explicit = fuse_dense_and_ppr(dense, [extra], lambda fid: _F(fid),
                                  protect_top=0)
    assert [f.id for f, _ in legacy] == [f.id for f, _ in explicit]
