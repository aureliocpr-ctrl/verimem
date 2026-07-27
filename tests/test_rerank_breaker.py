"""Rerank circuit-breaker (task #16) — TDD.

Observed live 2026-07-10 (external read-path runs): on a loaded CPU the CE
predict exceeds the 3s budget on EVERY query — each recall pays the full
budget in wasted wall-clock and keeps bi-encoder order anyway. The breaker
turns systematic overruns into a one-time decision: after N consecutive
overruns the CE is disabled for the session (explicit log), recall stops
waiting. A successful rerank resets the count (transient contention must not
permanently disable the measured R@1 lift).

All tests inject a fake scorer — no model, no RAM.
"""
from __future__ import annotations

import threading
import time

import pytest

from verimem import semantic
from verimem.client import Memory


def _cerca(mem, query="tower", k=3):
    """Una ricerca che lascia finire il rerank prima di ritornare.

    Dal 26/07 il rerank ha uno SLOT unico per processo: chi arriva mentre un
    predict e' ancora in volo prende l'ordine del bi-encoder e prosegue, senza
    accodare un secondo thread e senza contare uno sforamento. Serviva perche'
    i thread abbandonati si accumulavano (8 dopo 8 query) e la contesa fra loro
    faceva sforare i successivi, cioe' il breaker veniva innescato dall'accumulo
    che il breaker stesso produceva.

    Di conseguenza N ricerche ravvicinate NON sono piu' N sforamenti — la prima
    sfora, le altre saltano. Questi test misurano il breaker, quindi devono
    produrre sforamenti VERI, e per farlo aspettano il worker. Il breaker
    continua a scattare quando il CE e' lento davvero, ed e' quello che deve
    fare; cio' che non fa piu' e' scattare per la contesa autoinflitta da un
    gruppo di query ravvicinate — vedi
    test_close_together_queries_skip_instead_of_tripping.
    """
    out = mem.search(query, k=k)
    for t in [t for t in threading.enumerate() if t.name == "hippo-rerank"]:
        t.join(10)
    return out

FACTS = [
    "The Eiffel Tower is a wrought-iron lattice tower in Paris.",
    "Marie Curie won two Nobel Prizes for her work on radioactivity.",
    "The Amazon River discharges more water than any other river.",
]


@pytest.fixture(autouse=True)
def _fresh_breaker():
    semantic._rerank_breaker_reset()
    yield
    semantic._rerank_breaker_reset()


def _mem(tmp_path, monkeypatch, *, scorer_delay: float, budget: str = "0.2"):
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setenv("HIPPO_RECALL_RERANK_BUDGET_S", budget)
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BUDGET_S", budget)
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_N", "3")

    def slow_scorer():
        def score(pairs):
            time.sleep(scorer_delay)
            return [0.5] * len(pairs)
        return score

    monkeypatch.setattr(semantic, "_load_reranker", slow_scorer)
    # the ready-check gates the cold budget; pretend the CE is resident so
    # the configured budget applies deterministically
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: True)
    mem = Memory(tmp_path / "m.db")
    for f in FACTS:
        mem.add(f, topic="brk", verified_by=["source-doc:t"])
    return mem


def test_breaker_trips_after_consecutive_overruns(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)  # >> 0.2s budget
    for _ in range(3):
        _cerca(mem, "where is the tower")
    assert semantic._RERANK_BREAKER["tripped"] is True
    t0 = time.time()
    mem.search("where is the tower", k=3)
    assert time.time() - t0 < 0.15, (
        "tripped breaker must skip the rerank wait entirely")


def test_a_success_keeps_a_healthy_rerank_alive(tmp_path, monkeypatch):
    """La proprieta' che questo test protegge dal 10/07 — una contesa
    transitoria non deve disabilitare per sempre il lift misurato di R@1 —
    espressa senza dipendere da COME e' contata.

    Si chiamava ``test_success_resets_consecutive_count`` e asseriva
    ``_RERANK_BREAKER["consecutive"] == 0``: cioe' fissava l'implementazione, e
    quell'implementazione aveva un buco che il test non poteva vedere perche'
    lo *codificava* (26/07: una query in budget ogni cinque teneva il breaker
    disarmato mentre 80 rerank su 100 sforavano). Ora si chiede quello che
    conta: dopo due sforamenti e un successo il rerank e' ancora vivo — e il
    successo e' stato REGISTRATO, non usato per cancellare la memoria.
    """
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    for _ in range(2):
        _cerca(mem)  # 2 sforamenti veri
    assert semantic._rerank_breaker_overruns_in_window() == 2
    # ora uno scorer veloce rientra nel budget
    monkeypatch.setattr(
        semantic, "_load_reranker",
        lambda: (lambda pairs: [0.5] * len(pairs)))
    _cerca(mem, "tower")
    assert semantic._rerank_breaker_tripped() is False, (
        "due sforamenti e un successo hanno disabilitato un rerank sano")
    assert len(semantic._RERANK_BREAKER["window"]) == 3, (
        "il successo non e' stato registrato nella finestra: se cancella "
        "invece di contare, un successo ogni N sforamenti disarma il breaker "
        "per sempre")


def test_an_alternating_load_still_trips_the_breaker():
    """IL DIFETTO, misurato sul codice del 25/07 prima di curarlo: un carico
    che alterna sforamenti e successi non arriva mai a N di fila, quindi il
    breaker non scattava MENTRE meta' o piu' delle query bruciava il budget
    intero. Numeri di allora: O-S-O-S 10 sforamenti su 20 → picco del contatore
    1, non scattava; 30 su 40 → non scattava; **80 su 100 → non scattava**.
    Bastava una query in budget ogni cinque per disarmarlo a tempo
    indeterminato.

    E' lo stesso difetto che due revisioni avversarie indipendenti (glm-5.2,
    deepseek-v4-pro) avevano trovato nel breaker della FUSIONE il 25/07, curato
    solo la' — con una nota qui accanto che diceva "same blind spot, not touched
    here". Sweep del pattern mancato, non regola mancante.
    """
    for nome, quante, sfora_se in (
            ("alternato", 20, lambda i: i % 2 == 0),
            ("3 su 4", 40, lambda i: i % 4 != 3),
            ("4 su 5", 100, lambda i: i % 5 != 4),
            ("5 di fila", 5, lambda i: True),        # il caso del 10/07
    ):
        semantic._rerank_breaker_reset()
        for i in range(quante):
            semantic._rerank_breaker_record(sfora_se(i))
        assert semantic._rerank_breaker_tripped(), (
            f"carico '{nome}': il breaker non e' scattato mentre la maggior "
            "parte dei rerank sforava il budget")
    semantic._rerank_breaker_reset()


def test_scattered_overruns_do_not_disable_a_healthy_session():
    """L'altra metà, e va tenuta insieme alla prima: la finestra non deve
    degenerare in un contatore cumulativo, che spegnerebbe il rerank dopo N
    sforamenti sparsi in una sessione lunga e sana.

    OGNI CARICO QUI HA PIU' DI N SFORAMENTI IN TOTALE, e non e' un dettaglio:
    la prima versione di questo test usava al massimo 4 sforamenti — sotto la
    soglia di 5 — quindi passava anche con un contatore cumulativo, cioe' non
    falsificava proprio la degenerazione che dice di escludere. Trovato dalla
    mutazione "finestra illimitata", che il test non rilevava. Ora ogni caso ha
    abbastanza sforamenti da far scattare un totale cumulativo (8, 10, 20) ma
    mai piu' di 1-2 dentro una finestra di 10.
    """
    for nome, quante, sfora_se in (
            ("8 sforamenti ogni 25 query", 200, lambda i: i % 25 == 0),
            ("10 sforamenti ogni 20 query", 200, lambda i: i % 20 == 0),
            ("20 coppie distanziate", 400, lambda i: i % 20 in (0, 1)),
    ):
        semantic._rerank_breaker_reset()
        for i in range(quante):
            semantic._rerank_breaker_record(sfora_se(i))
        assert not semantic._rerank_breaker_tripped(), (
            f"carico '{nome}': sforamenti sparsi hanno disabilitato un rerank "
            "sano — la finestra sta contando come un totale cumulativo")
    semantic._rerank_breaker_reset()


def test_breaker_disabled_with_zero_threshold(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_N", "0")
    for _ in range(5):
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is False


# --- F1 C1 (task #25): cold-load overruns must NOT trip the steady breaker.
# Observed on the MuSiQue virgin-corpus run 2026-07-10: the CE cold-load
# (~33s) overran the 0.25s cold budget 5 times in the first recalls of a
# fresh process and TRIPPED the breaker — rerank (worth +0.29 R@1) stayed
# off for the whole session. A cold overrun is transient by definition; only
# a STEADY overrun (CE resident but too slow) signals a real problem.


def test_cold_overruns_do_not_trip_steady_breaker(tmp_path, monkeypatch):
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: False)  # cold
    for _ in range(5):  # >> breaker N=3
        mem.search("tower", k=3)
    assert semantic._RERANK_BREAKER["tripped"] is False, (
        "cold-load overruns are transient — they must never trip the breaker")
    assert semantic._rerank_breaker_overruns_in_window() == 0, (
        "cold overruns must not count toward the steady trip")
    assert len(semantic._RERANK_BREAKER["window"]) == 0, (
        "a cold overrun landed in the steady window at all: it must not be "
        "recorded there, not even as a success")


def test_cold_overruns_have_their_own_bounded_trip(tmp_path, monkeypatch):
    # pathological never-warms process (broken CE install): a SEPARATE,
    # much more generous cold threshold still bounds the waste.
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    monkeypatch.setattr(semantic, "_reranker_ready", lambda: False)
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BREAKER_N", "3")
    for _ in range(3):
        _cerca(mem)
    assert semantic._RERANK_BREAKER["tripped"] is True


def test_steady_overruns_still_trip_after_warm(tmp_path, monkeypatch):
    # regression guard: the C1 fix must not weaken the original breaker —
    # a WARM reranker that systematically overruns still trips at N.
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)  # ready=True fixture
    for _ in range(3):
        _cerca(mem)
    assert semantic._RERANK_BREAKER["tripped"] is True


def test_close_together_queries_skip_instead_of_tripping(tmp_path, monkeypatch):
    """Il comportamento NUOVO, dichiarato invece di lasciarlo implicito.

    Tre ricerche ravvicinate su un CE lento: la prima sfora, le altre due
    trovano lo slot occupato e prendono l'ordine del bi-encoder. Un salto non
    e' uno sforamento — nessuno e' stato lento, lo slot era preso — quindi il
    breaker NON scatta. Prima scattava, e scattava per la contesa che quelle
    stesse tre query si infliggevano a vicenda: il cross-encoder restava spento
    per tutto il processo per un guasto che non c'era."""
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    for _ in range(3):
        mem.search("tower", k=3)          # senza aspettare il worker
    assert semantic._rerank_breaker_overruns_in_window() == 1, (
        "tre ricerche ravvicinate hanno prodotto piu' di uno sforamento: i "
        "thread si stanno di nuovo accumulando")
    assert semantic._RERANK_BREAKER["tripped"] is False, (
        "il breaker e' scattato per contesa autoinflitta, non per un CE lento")
    for t in [t for t in threading.enumerate() if t.name == "hippo-rerank"]:
        t.join(10)


# --- Re-arm after cooldown (2026-07-27) --------------------------------------
# The trip was a PROCESS sentence: "restart or _rerank_breaker_reset() to
# re-arm" — in a long-lived daemon that means a transient contention (a gaming
# session, an antivirus scan) disables the measured CE lift FOREVER, which is
# the exact property the breaker's own docstring promised to protect. After
# ENGRAM_RERANK_BREAKER_COOLDOWN_S (default 600, the CE lease constant) the
# breaker re-arms with a CLEAN window: a persistent fault re-trips after N
# fresh overruns (bounded waste: N*budget per cooldown), a healed session
# gets its rerank back. 0 opts out (the old permanent trip).


def test_a_tripped_breaker_rearms_after_the_cooldown(monkeypatch):
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_COOLDOWN_S", "0.3")
    for _ in range(5):
        semantic._rerank_breaker_record(True)
    assert semantic._rerank_breaker_tripped(), "before the cooldown the trip stands"
    time.sleep(0.35)
    assert not semantic._rerank_breaker_tripped(), "cooldown elapsed -> re-armed"
    semantic._rerank_breaker_record(True)
    assert not semantic._rerank_breaker_tripped(), (
        "the window is CLEAN after re-arm: one overrun must not re-trip")
    for _ in range(4):
        semantic._rerank_breaker_record(True)
    assert semantic._rerank_breaker_tripped(), "a persistent fault re-trips"


def test_cooldown_zero_keeps_the_trip_standing(monkeypatch):
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_COOLDOWN_S", "0")
    for _ in range(5):
        semantic._rerank_breaker_record(True)
    time.sleep(0.05)
    assert semantic._rerank_breaker_tripped(), "0 opts out: permanent trip"


def test_cold_trip_rearms_and_forgets_the_cold_count(monkeypatch):
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_COOLDOWN_S", "0.3")
    monkeypatch.setenv("ENGRAM_RERANK_COLD_BREAKER_N", "3")
    for _ in range(3):
        semantic._rerank_breaker_cold_overrun()
    assert semantic._rerank_breaker_tripped()
    time.sleep(0.35)
    assert not semantic._rerank_breaker_tripped()
    semantic._rerank_breaker_cold_overrun()
    assert not semantic._rerank_breaker_tripped(), (
        "the cold count restarts from zero after a re-arm")


def test_fusion_breaker_rearms_after_the_cooldown(monkeypatch):
    semantic._fusion_breaker_reset()
    monkeypatch.setenv("ENGRAM_FUSION_BREAKER_COOLDOWN_S", "0.3")
    for _ in range(5):
        semantic._fusion_breaker_record(True)
    assert semantic._fusion_breaker_tripped()
    time.sleep(0.35)
    assert not semantic._fusion_breaker_tripped(), "fusion twin re-arms too"
    semantic._fusion_breaker_record(True)
    assert not semantic._fusion_breaker_tripped(), "clean window after re-arm"
    for _ in range(4):
        semantic._fusion_breaker_record(True)
    assert semantic._fusion_breaker_tripped()


def test_the_recall_gate_sees_the_rearm(tmp_path, monkeypatch):
    """The production gate (semantic.py:3952) read the RAW field, not the
    function — a re-arm implemented only in _rerank_breaker_tripped() would be
    invisible to the very code path it exists for. This test never calls the
    function between cooldown and queries: only the gate itself can re-arm.
    With the gate on the function: query 1 re-arms, reranks, overruns; three
    overruns re-trip (BREAKER_N=3), and the assert runs INSIDE the fresh
    cooldown -> True. With the gate on the field: no query ever re-arms or
    reranks, the final assert's own call re-arms (cooldown long elapsed) ->
    False -> caught.

    Cooldown 2 s, NOT 0.3: the overrun is recorded by the CALLER at the
    0.2 s budget timeout (semantic.py, join(_budget)) while _cerca then joins
    the worker to completion (~0.8 s more) — a 0.3 s cooldown expires inside
    that join and the sanity assert itself re-arms. Found exactly that way."""
    monkeypatch.setenv("ENGRAM_RERANK_BREAKER_COOLDOWN_S", "2.0")
    mem = _mem(tmp_path, monkeypatch, scorer_delay=1.0)
    for _ in range(3):
        _cerca(mem)
    assert semantic._rerank_breaker_tripped(), "sanity: tripped on slow CE"
    time.sleep(2.1)
    for _ in range(3):
        _cerca(mem)
    assert semantic._rerank_breaker_tripped(), (
        "after the cooldown the GATE must re-arm and rerank again — three "
        "fresh overruns re-trip; if this is False the gate never consulted "
        "the re-arming function")
