"""Un rerank che sfora il budget non deve lasciarne partire un secondo.

MISURATO IL 26/07 sul corpus reale. Il rerank gira in un thread daemon con un
``join(budget)``: allo scadere il chiamante prosegue con l'ordine del
bi-encoder, ma il thread NON viene interrotto — non esiste modo di fermare un
``predict`` di torch a meta'. Finche' ogni query ne lancia uno nuovo, si
accumulano: contati 8 thread vivi dopo 8 query, uno per query, tutti dentro lo
stesso processo.

Perche' e' un guasto e non uno spreco. Il ``predict`` costa **2070 ms stabili**
su 20 coppie contro un budget di **3000**: 930 ms di margine, cioe' meno del
tempo di un secondo predict. Basta un thread concorrente e si sfora; ogni
sforamento aggiunge un thread e rende piu' probabile il successivo. Dopo cinque
sforamenti di fila scatta il breaker, che disabilita il cross-encoder **per
tutto il processo** — osservato nei log, senza profiler.

Quindi il breaker che spegne il rerank e' innescato dall'accumulo che il
breaker stesso produce, ed e' l'anello che va rotto: chi arriva mentre un
rerank e' gia' in volo prende l'ordine del bi-encoder e tira dritto. Non
aggiunge contesa, non ruba core a chi sta gia' lavorando, e soprattutto lascia
al primo thread la possibilita' di finire — rendendo il CE residente, che e'
la condizione perche' tutti i successivi rientrino nel budget.
"""
from __future__ import annotations

import threading
import time

import pytest

from verimem import semantic as sem
from verimem.semantic import Fact


def _semina(sm, n=8):
    for i in range(n):
        sm.store(Fact(proposition=f"il fatto numero {i} parla di gatti e tetti",
                      topic="test", confidence=0.9, source_episodes=[],
                      created_at=time.time()), embed="sync")


@pytest.fixture(autouse=True)
def breaker_pulito():
    sem._rerank_breaker_reset()
    yield
    sem._rerank_breaker_reset()


def _thread_di_rerank():
    return [t for t in threading.enumerate() if t.name == "hippo-rerank"]


def test_a_rerank_already_in_flight_blocks_a_second_one():
    """Il cuore: due chiamate ravvicinate, un solo thread."""
    assert sem._rerank_inflight_acquire() is True, "il primo deve poter partire"
    try:
        assert sem._rerank_inflight_acquire() is False, (
            "un secondo rerank e' partito mentre il primo era ancora in volo: "
            "i thread si accumulano e si rubano i core a vicenda")
    finally:
        sem._rerank_inflight_release()


def test_the_slot_is_free_again_once_the_first_finishes():
    """Reversibile: finito il primo, il prossimo rerank riparte davvero.
    Senza questo la cura spegnerebbe il rerank per sempre, che e' esattamente
    il guasto che sta curando."""
    assert sem._rerank_inflight_acquire() is True
    sem._rerank_inflight_release()
    assert sem._rerank_inflight_acquire() is True, (
        "lo slot non e' tornato libero: il rerank resta spento per sempre")
    sem._rerank_inflight_release()


def test_the_slot_is_released_by_the_worker_not_by_the_caller():
    """Il punto delicato. Il chiamante ABBANDONA il thread allo scadere del
    budget, quindi se fosse lui a liberare lo slot il thread successivo
    partirebbe mentre il precedente sta ancora macinando — cioe' esattamente
    l'accumulo da evitare. Lo slot appartiene al lavoro, non all'attesa."""
    partito = threading.Event()
    finisci = threading.Event()

    def _lavoro():
        try:
            partito.set()
            finisci.wait(5)
        finally:
            sem._rerank_inflight_release()

    assert sem._rerank_inflight_acquire() is True
    t = threading.Thread(target=_lavoro, name="hippo-rerank", daemon=True)
    t.start()
    assert partito.wait(5)

    # il "chiamante" ha rinunciato ad aspettare: lo slot deve restare occupato
    assert sem._rerank_inflight_acquire() is False, (
        "lo slot si e' liberato mentre il lavoro era ancora in corso")

    finisci.set()
    t.join(5)
    assert sem._rerank_inflight_acquire() is True, (
        "lo slot non e' stato liberato dal worker alla fine del lavoro")
    sem._rerank_inflight_release()


def test_skipping_is_not_an_overrun():
    """Chi salta perche' lo slot e' occupato non ha sforato niente: contarlo
    verso il breaker significherebbe che cinque query ravvicinate spengono il
    cross-encoder senza che nessun rerank sia mai stato lento."""
    prima = sem._RERANK_BREAKER["consecutive"]
    assert sem._rerank_inflight_acquire() is True
    try:
        for _ in range(6):
            assert sem._rerank_inflight_acquire() is False
    finally:
        sem._rerank_inflight_release()
    assert sem._RERANK_BREAKER["consecutive"] == prima, (
        "un salto per slot occupato ha contato come sforamento")
    assert not sem._RERANK_BREAKER["tripped"]


@pytest.fixture()
def rerank_vivo(monkeypatch):
    """Un recall che TENTA davvero il rerank, con uno scorer lento e finto.

    Serve perche' il conftest della suite imposta ``ENGRAM_RECALL_RERANK=0``
    per tutti i test, e senza riabilitarlo il ramo in esame non viene mai
    eseguito: la prima versione di questi test passava per quel motivo, e la
    mutazione "togli del tutto il gate dal recall" NON veniva rilevata. E' la
    stessa trappola gia' incontrata il 25/07 con ``ENGRAM_ENCODE_SERVICE=0``
    sul daemon — un interruttore globale del conftest che fa passare i test
    senza eseguire il codice che dovrebbero misurare.

    Lo scorer dorme invece di calcolare: il thread resta in volo quanto basta
    per osservarlo, e nessun cross-encoder vero viene caricato."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "1")
    monkeypatch.setattr(sem, "_recall_rerank_budget_s", lambda: 0.15)
    monkeypatch.setattr(sem, "_reranker_ready", lambda: True)

    def _scorer_lento():
        def _scorer(pairs):
            time.sleep(1.5)
            return [0.5] * len(pairs)
        return _scorer

    monkeypatch.setattr(sem, "_load_reranker", _scorer_lento)
    return None


def _attendi_thread(timeout=6.0):
    for t in _thread_di_rerank():
        t.join(timeout)


def test_a_recall_that_skips_the_rerank_still_returns_results(tmp_path, rerank_vivo):
    """Saltare il rerank e' una rinuncia all'ORDINE migliore, mai ai
    risultati: il recall resta quello del bi-encoder, come per ogni altro
    fail-soft di questo modulo."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    assert sem._rerank_inflight_acquire() is True   # slot occupato da altri
    try:
        hits = sm.recall("gatti", k=5)
    finally:
        sem._rerank_inflight_release()
    assert hits, "il recall non ha restituito nulla perche' il rerank era occupato"


def test_no_thread_is_left_behind_when_the_slot_is_busy(tmp_path, rerank_vivo):
    """La misura che ha fatto nascere questo file: con lo slot occupato, un
    recall non deve far nascere nessun thread di rerank."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    assert sem._rerank_inflight_acquire() is True
    try:
        prima = len(_thread_di_rerank())
        sm.recall("gatti", k=5)
        time.sleep(0.3)
        dopo = len(_thread_di_rerank())
    finally:
        sem._rerank_inflight_release()
    assert dopo == prima, (
        f"con lo slot occupato sono nati {dopo - prima} thread di rerank: "
        "l'accumulo continua")
    _attendi_thread()


def test_the_pile_up_is_gone_across_several_queries(tmp_path, rerank_vivo):
    """La misura originale, in piccolo: otto recall di fila producevano otto
    thread vivi, uno per query. Ora il primo lavora e gli altri passano oltre,
    quindi non se ne accumula mai piu' di uno."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    massimo = 0
    for _ in range(6):
        sm.recall("gatti", k=5)
        massimo = max(massimo, len(_thread_di_rerank()))
    assert massimo <= 1, (
        f"con sei recall sono arrivati a {massimo} thread di rerank vivi "
        "insieme: i predict si rubano i core e sforano il budget a vicenda")
    _attendi_thread()


def test_the_slot_comes_back_after_a_real_recall(tmp_path, rerank_vivo):
    """Il rilascio dev'essere quello del worker VERO, non solo quello chiamato
    a mano nei test qui sopra: se il ``finally`` del thread sparisse, il primo
    recall spegnerebbe il rerank per il resto del processo."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    sm.recall("gatti", k=5)          # sfora il budget da 0,15 s e abbandona
    _attendi_thread()                # ma il thread finisce per conto suo
    assert sem._rerank_inflight_acquire() is True, (
        "dopo un recall che ha sforato, lo slot e' rimasto occupato: nessuna "
        "query successiva potra' mai piu' usare il cross-encoder")
    sem._rerank_inflight_release()


def test_a_thread_that_never_starts_does_not_keep_the_slot(tmp_path, rerank_vivo,
                                                           monkeypatch):
    """Se ``Thread.start`` fallisce — esaurimento di thread di sistema — il
    worker non gira mai, quindi non c'e' nessun ``finally`` a liberare lo
    slot. Senza il rilascio dal lato del chiamante il rerank resterebbe
    spento per sempre, e il guasto sarebbe indistinguibile da quello curato."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    vero_start = threading.Thread.start

    def _start_rotto(self):
        # solo il thread di rerank: rompere start GLOBALMENTE colpirebbe anche
        # quello della fusione PPR, che e' un altro percorso con un altro
        # difetto (vedi test_a_recall_survives_a_fusion_thread_that_cannot_start)
        if self.name == "hippo-rerank":
            raise RuntimeError("can't start new thread")
        return vero_start(self)

    monkeypatch.setattr(threading.Thread, "start", _start_rotto)
    hits = sm.recall("gatti", k=5)
    assert hits, "il recall non ha restituito nulla con lo start rotto"
    assert sem._rerank_inflight_acquire() is True, (
        "uno start fallito ha tenuto lo slot: il rerank non riparte piu'")
    sem._rerank_inflight_release()


def test_a_recall_survives_a_fusion_thread_that_cannot_start(tmp_path, monkeypatch):
    """Difetto trovato di rimbalzo, mentre si testava lo slot del rerank.

    Il modulo dichiara che il recall degrada e non si rompe mai: ogni percorso
    a budget cattura i guasti del proprio lavoro. Ma lo ``start`` del thread di
    fusione era l'unico del read path senza niente attorno, quindi una macchina
    a corto di thread di sistema — cioe' precisamente il momento in cui la
    promessa conta — faceva sollevare il recall invece di fargli saltare i
    segnali grafo e lessicali."""
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")   # solo la fusione in gioco
    # senza questo la fusione esce prima di creare il thread: sotto i 50 fatti
    # non viene nemmeno tentata, e il test passerebbe senza eseguire la riga
    # in esame — la mutazione lo aveva rilevato subito
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    vero_start = threading.Thread.start

    def _start_rotto(self):
        if self.name == "hippo-ppr-fusion":
            raise RuntimeError("can't start new thread")
        return vero_start(self)

    monkeypatch.setattr(threading.Thread, "start", _start_rotto)
    hits = sm.recall("gatti", k=5)
    assert hits, (
        "il recall e' esploso perche' non e' riuscito ad avviare il thread "
        "della fusione: doveva restituire l'ordine che aveva gia'")
