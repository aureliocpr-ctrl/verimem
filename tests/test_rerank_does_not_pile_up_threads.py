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

IL LEASE, e perche' non c'era nella prima versione. Due revisioni avversarie
indipendenti hanno indicato la stessa lacuna: un worker che si BLOCCA — un
deadlock di torch, non un'eccezione, che il ``finally`` copre gia' — terrebbe
lo slot per sempre, e siccome un salto non e' uno sforamento nemmeno il breaker
lo annuncerebbe piu'. Sarebbe stato scambiare un guasto rumoroso con uno muto,
cioe' la stessa classe che ha tenuto nascosto per sei settimane lo sforamento
della fusione. Ora lo slot ha una scadenza, molto oltre il budget perche' un
predict LENTO deve tenerselo, e chi lo requisisce lo dice nel log.
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
def stato_pulito():
    sem._rerank_breaker_reset()
    sem._RERANK_SLOT.update({"lease": 0, "since": 0.0, "skipped": 0})
    yield
    sem._rerank_breaker_reset()
    sem._RERANK_SLOT.update({"lease": 0, "since": 0.0, "skipped": 0})


def _thread_di_rerank():
    return [t for t in threading.enumerate() if t.name == "hippo-rerank"]


def _attendi_thread(timeout=6.0):
    for t in _thread_di_rerank():
        t.join(timeout)


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


# --- lo slot ----------------------------------------------------------------

def test_a_rerank_already_in_flight_blocks_a_second_one():
    """Il cuore: due chiamate ravvicinate, un solo thread."""
    lease = sem._rerank_inflight_acquire()
    assert lease, "il primo deve poter partire"
    try:
        assert not sem._rerank_inflight_acquire(), (
            "un secondo rerank e' partito mentre il primo era ancora in volo: "
            "i thread si accumulano e si rubano i core a vicenda")
    finally:
        sem._rerank_inflight_release(lease)


def test_the_slot_is_free_again_once_the_first_finishes():
    """Reversibile: finito il primo, il prossimo rerank riparte davvero.
    Senza questo la cura spegnerebbe il rerank per sempre, che e' esattamente
    il guasto che sta curando."""
    primo = sem._rerank_inflight_acquire()
    assert primo
    sem._rerank_inflight_release(primo)
    secondo = sem._rerank_inflight_acquire()
    assert secondo, "lo slot non e' tornato libero: il rerank resta spento"
    sem._rerank_inflight_release(secondo)


def test_the_slot_is_released_by_the_worker_not_by_the_caller():
    """Il punto delicato. Il chiamante ABBANDONA il thread allo scadere del
    budget, quindi se fosse lui a liberare lo slot il thread successivo
    partirebbe mentre il precedente sta ancora macinando — cioe' esattamente
    l'accumulo da evitare. Lo slot appartiene al lavoro, non all'attesa."""
    partito = threading.Event()
    finisci = threading.Event()
    lease = sem._rerank_inflight_acquire()
    assert lease

    def _lavoro():
        try:
            partito.set()
            finisci.wait(5)
        finally:
            sem._rerank_inflight_release(lease)

    t = threading.Thread(target=_lavoro, name="hippo-rerank", daemon=True)
    t.start()
    assert partito.wait(5)

    # il "chiamante" ha rinunciato ad aspettare: lo slot deve restare occupato
    assert not sem._rerank_inflight_acquire(), (
        "lo slot si e' liberato mentre il lavoro era ancora in corso")

    finisci.set()
    t.join(5)
    dopo = sem._rerank_inflight_acquire()
    assert dopo, "lo slot non e' stato liberato dal worker a lavoro finito"
    sem._rerank_inflight_release(dopo)


def test_skipping_is_not_an_overrun():
    """Chi salta perche' lo slot e' occupato non ha sforato niente: contarlo
    verso il breaker significherebbe che cinque query ravvicinate spengono il
    cross-encoder senza che nessun rerank sia mai stato lento."""
    prima = sem._rerank_breaker_overruns_in_window()
    lease = sem._rerank_inflight_acquire()
    assert lease
    try:
        for _ in range(6):
            assert not sem._rerank_inflight_acquire()
    finally:
        sem._rerank_inflight_release(lease)
    assert sem._rerank_breaker_overruns_in_window() == prima, (
        "un salto per slot occupato ha contato come sforamento")
    assert not sem._RERANK_BREAKER["tripped"]


# --- il lease: cio' che le revisioni avversarie hanno guadagnato -------------

def test_a_wedged_worker_loses_the_slot_after_the_lease(monkeypatch, caplog):
    """La lacuna trovata da due revisioni indipendenti: un worker che si blocca
    terrebbe lo slot per sempre, e siccome un salto non e' uno sforamento
    nemmeno il breaker lo annuncerebbe. Il rerank resterebbe spento in silenzio
    per tutta la vita del processo."""
    monkeypatch.setenv("ENGRAM_RERANK_SLOT_LEASE_S", "0.2")
    lease = sem._rerank_inflight_acquire()
    assert lease
    assert not sem._rerank_inflight_acquire(), "prima della scadenza si aspetta"

    time.sleep(0.3)
    with caplog.at_level("WARNING", logger=sem._LOG.name):
        nuovo = sem._rerank_inflight_acquire()
    assert nuovo, (
        "lo slot non e' stato requisito dopo la scadenza: un worker incastrato "
        "spegne il cross-encoder per sempre, e in silenzio")
    assert any("wedged" in r.message or "wedged" in r.getMessage()
               for r in caplog.records), (
        "la requisizione non e' stata dichiarata: un guasto muto e' peggio di "
        "uno rumoroso, ed e' la classe che ha nascosto lo sforamento della "
        "fusione per sei settimane")
    sem._rerank_inflight_release(nuovo)


def test_the_lease_covers_a_first_model_download():
    """La soglia va confrontata con il caso PEGGIORE, non con quello misurato.

    Il caricamento del cross-encoder costa 43,6 s su questa macchina — dentro i
    60 s della prima versione, ma a cache HuggingFace CALDA. Al primo avvio il
    modello va scaricato (~1 GB) e il lease scadrebbe mentre il primo thread sta
    ancora caricando: lo slot requisito, un secondo thread a caricare un'altra
    copia, cioe' la contesa che lo slot impedisce — su due modelli invece di uno.

    E' la stessa classe di errore che una revisione avversaria trovo' nella
    grazia del lock del daemon (120 s tarati a cache calda, portati a 600), e la
    soglia si allinea a quella per la stessa ragione. Il test la pinna: se
    qualcuno la riabbassa sotto il tempo di un download reale, lo dice."""
    assert sem._rerank_slot_lease_s() >= 300, (
        "il lease e' tornato sotto i cinque minuti: un primo download del "
        "modello lo supera e due thread caricheranno due copie")


def test_a_slow_predict_keeps_its_slot():
    """L'altro lato: la scadenza serve per chi e' INCASTRATO, non per chi e'
    lento. Con la scadenza di produzione (60 s) un predict da 2 s non perde
    niente, altrimenti la cura reintrodurrebbe la contesa che ha eliminato."""
    lease = sem._rerank_inflight_acquire()
    assert lease
    try:
        time.sleep(0.3)
        assert not sem._rerank_inflight_acquire(), (
            "un predict di pochi secondi si e' visto togliere lo slot")
    finally:
        sem._rerank_inflight_release(lease)


def test_a_seized_slot_is_not_freed_by_the_worker_that_lost_it(monkeypatch):
    """Perche' lo slot porta un numero. Se il worker incastrato, tornando,
    liberasse lo slot di chi lo ha sostituito, l'accumulo rientrerebbe
    dall'altro lato: due worker in volo e nessuno che tiene il posto."""
    monkeypatch.setenv("ENGRAM_RERANK_SLOT_LEASE_S", "0.2")
    perso = sem._rerank_inflight_acquire()
    assert perso
    time.sleep(0.3)
    nuovo = sem._rerank_inflight_acquire()
    assert nuovo and nuovo != perso

    sem._rerank_inflight_release(perso)      # il vecchio worker si risveglia
    assert not sem._rerank_inflight_acquire(), (
        "il worker sostituito ha liberato lo slot del suo successore")
    sem._rerank_inflight_release(nuovo)


def test_the_lease_can_be_disabled():
    """Zero disattiva la scadenza, per chi preferisce un blocco visibile a una
    requisizione: e' la stessa forma degli altri interruttori del modulo."""
    import os
    os.environ["ENGRAM_RERANK_SLOT_LEASE_S"] = "0"
    try:
        lease = sem._rerank_inflight_acquire()
        assert lease
        sem._RERANK_SLOT["since"] -= 10_000     # tenuto da un'eternita'
        assert not sem._rerank_inflight_acquire(), (
            "con la scadenza a zero lo slot e' stato requisito comunque")
        sem._rerank_inflight_release(lease)
    finally:
        os.environ.pop("ENGRAM_RERANK_SLOT_LEASE_S", None)


# --- il recall vero ---------------------------------------------------------

def test_a_recall_that_skips_the_rerank_still_returns_results(tmp_path, rerank_vivo):
    """Saltare il rerank e' una rinuncia all'ORDINE migliore, mai ai
    risultati: il recall resta quello del bi-encoder, come per ogni altro
    fail-soft di questo modulo."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    lease = sem._rerank_inflight_acquire()
    assert lease
    try:
        hits = sm.recall("gatti", k=5)
    finally:
        sem._rerank_inflight_release(lease)
    assert hits, "il recall non ha restituito nulla perche' il rerank era occupato"


def test_no_thread_is_left_behind_when_the_slot_is_busy(tmp_path, rerank_vivo):
    """La misura che ha fatto nascere questo file: con lo slot occupato, un
    recall non deve far nascere nessun thread di rerank."""
    sm = sem.SemanticMemory(db_path=tmp_path / "s.db")
    _semina(sm)

    lease = sem._rerank_inflight_acquire()
    assert lease
    try:
        prima = len(_thread_di_rerank())
        sm.recall("gatti", k=5)
        time.sleep(0.3)
        dopo = len(_thread_di_rerank())
    finally:
        sem._rerank_inflight_release(lease)
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
    lease = sem._rerank_inflight_acquire()
    assert lease, (
        "dopo un recall che ha sforato, lo slot e' rimasto occupato: nessuna "
        "query successiva potra' mai piu' usare il cross-encoder")
    sem._rerank_inflight_release(lease)


def test_a_thread_that_never_starts_does_not_keep_the_slot(tmp_path, rerank_vivo,
                                                           monkeypatch):
    """Se ``Thread.start`` fallisce — esaurimento di thread di sistema — il
    worker non gira mai, quindi non c'e' nessun ``finally`` a liberare lo
    slot. Senza il rilascio dal lato del chiamante il rerank resterebbe
    spento fino alla scadenza del lease, per un guasto che si conosce subito."""
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
    lease = sem._rerank_inflight_acquire()
    assert lease, "uno start fallito ha tenuto lo slot: il rerank non riparte"
    sem._rerank_inflight_release(lease)


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
