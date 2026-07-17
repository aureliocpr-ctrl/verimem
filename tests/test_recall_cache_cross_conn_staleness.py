"""FALSIFICAZIONE buco cache-coherence cross-connessione (sorelle loop 2026-06-03).

Il buco (trovato leggendo semantic.py):
  ``SemanticMemory`` ha una hot-path cache di ``recall(topic=None)`` invalidata
  SOLO da un contatore in-memory ``self._cache_version`` bumpato dai metodi
  mutanti della STESSA istanza. Non c'e' alcun check di versione su disco
  (nessun ``PRAGMA data_version`` / mtime). Percio' se un ALTRO writer
  (altro processo, o qui un'altra connessione/istanza sullo stesso file)
  committa un fatto nuovo, l'istanza con cache calda continua a servire la
  matrice STANTIA: non vede il fatto nuovo.

Simulazione fedele di 2 processi nello stesso processo Python: due istanze
``SemanticMemory`` sullo STESSO db. Ognuna apre connessioni sqlite effimere
proprie (``_connect``) e ha un ``_cache_version`` indipendente — esattamente
come due processi distinti.

Stato atteso:
  * ``test_cross_conn_recall_sees_committed_fact``  -> RED OGGI (cache stantia),
    deve diventare VERDE quando C wira ``PRAGMA data_version`` nel gate cache.
  * ``test_cold_instance_sees_committed_fact``      -> CONTROL, VERDE oggi:
    prova che il fatto E' su disco e recuperabile (isola il bug alla cache,
    non a store/query). Se questo fallisse, il RED sopra sarebbe un falso
    positivo (problema di scrittura/retrieval, non di staleness).
  * ``test_data_version_moves_cross_connection``    -> SANITY del primitivo
    scelto, VERDE oggi: documenta che su QUESTO build sqlite ``data_version``
    si muove davvero per un commit di un'altra connessione (altrimenti il fix
    proposto sarebbe nullo).

Hermetic: db in tmp_path, nessuna rete (oltre all'encoder locale gia' usato
dagli altri test recall del repo). Nessun edit a semantic.py.
"""
from __future__ import annotations

import re
import sqlite3
import threading
import time

from verimem.semantic import Fact, SemanticMemory

# Query == proposition del fatto nuovo => cosine ~1.0 => garantito in top-k
# su un corpus minuscolo (seed + F2). Stringa distintiva per evitare collisioni
# semantiche con il seed.
_PROP_F2 = "ZX9-CROSSCONN-MARKER fatto nuovo scritto dalla connessione B"
_QUERY = _PROP_F2
_SEED = "QW1-SEED-MARKER fatto seed non correlato del tutto"


def _props(recall_result) -> list[str]:
    # recall() ritorna list[tuple(Fact, score)] quando trust_signals=False.
    return [t[0].proposition for t in recall_result]


def test_cross_conn_recall_sees_committed_fact(tmp_path):
    """RED oggi: istanza A con cache calda NON vede il fatto committato da B."""
    db = tmp_path / "hippo.db"
    mem_a = SemanticMemory(db)
    mem_b = SemanticMemory(db)  # "secondo processo" sullo stesso file

    # Corpus non vuoto + cache di A costruita (topic=None => cache-eligible).
    mem_a.store(Fact(proposition=_SEED, topic="project/x", status="model_claim"))
    warm = mem_a.recall(_QUERY)
    assert _PROP_F2 not in _props(warm), "pre-condizione: F2 non esiste ancora"

    # B scrive+committa F2 sulla SUA connessione. Non tocca mem_a._cache_version.
    mem_b.store(Fact(proposition=_PROP_F2, topic="project/x", status="model_claim"))

    # A rifa recall: deve vedere F2. OGGI fallisce (cache stantia) = RED.
    again = mem_a.recall(_QUERY)
    assert _PROP_F2 in _props(again), (
        "recall di A serve cache stantia: non vede il fatto committato da "
        "un'altra connessione. Atteso VERDE dopo il wiring di PRAGMA data_version."
    )


def test_cold_instance_sees_committed_fact(tmp_path):
    """CONTROL (verde oggi): un'istanza fredda vede F2 -> e' su disco.

    Isola il bug alla cache calda di A, non a store/query/embedding.
    """
    db = tmp_path / "hippo.db"
    mem_a = SemanticMemory(db)
    mem_b = SemanticMemory(db)

    mem_a.store(Fact(proposition=_SEED, topic="project/x", status="model_claim"))
    mem_b.store(Fact(proposition=_PROP_F2, topic="project/x", status="model_claim"))

    mem_cold = SemanticMemory(db)  # cache vergine -> build da disco ora
    res = mem_cold.recall(_QUERY)
    assert _PROP_F2 in _props(res), (
        "il fatto deve essere su disco e recuperabile da un'istanza fredda; "
        "se no il RED sarebbe un falso positivo"
    )


def test_data_version_moves_cross_connection(tmp_path):
    """SANITY del primitivo (verde oggi): data_version cambia per un commit
    di un'altra connessione sullo STESSO file. Se questo fallisse, il fix
    basato su PRAGMA data_version sarebbe void su questa piattaforma."""
    db = tmp_path / "hippo.db"
    mem = SemanticMemory(db)  # crea schema + tabella facts

    probe = sqlite3.connect(db, timeout=10.0)
    try:
        v0 = probe.execute("PRAGMA data_version").fetchone()[0]
        # commit da un'ALTRA connessione (l'istanza mem usa connessioni effimere)
        mem.store(Fact(proposition="dv-bump", topic="t", status="model_claim"))
        v1 = probe.execute("PRAGMA data_version").fetchone()[0]
    finally:
        probe.close()

    assert v1 != v0, (
        "PRAGMA data_version non si muove cross-connessione su questo build "
        "sqlite -> il meccanismo di cache-invalidation proposto non funziona qui"
    )


# ---------------------------------------------------------------------------
# CONTESA multi-thread reale (sorelle loop 2026-06-03): N reader concorrenti
# sulla STESSA istanza (condividono _corpus_cache / _dv_conn / _dv_lock) mentre
# un writer su una connessione SEPARATA scrive+committa. Sonda: (a) nessun
# crash/eccezione (race su _dv_conn o coppia facts/matrix affiora come errore),
# (b) nessun deadlock sul lock, (c) visibilita' MONOTONA per reader (una cache
# piu' vecchia non puo' essere servita dopo una piu' fresca = stale), (d)
# consistenza finale (tutti i fatti visti a fine corsa).
# ---------------------------------------------------------------------------

_CONT_QUERY = "CONTESA-MARKER fatto concorrente scritto sotto contesa"
_IDX_RE = re.compile(r"idx=(\d+)")


def _max_idx_seen(recall_result) -> int:
    """Massimo indice 'idx=NNNN' presente nello snapshot di recall. -1 se vuoto."""
    mx = -1
    for fact, _score in recall_result:
        m = _IDX_RE.search(fact.proposition)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def _run_contention(db_path, *, n_facts: int = 40, n_readers: int = 8,
                    n_filler: int = 0):
    """Esegue il workload di contesa e ritorna (errors, threads, seqs, n_facts).

    Topologia: una istanza ``reader_mem`` CONDIVISA da ``n_readers`` thread
    (condividono ``_corpus_cache`` / ``_dv_conn`` / ``_dv_lock``), e una
    istanza ``writer_mem`` su connessione SEPARATA (path data_version) che
    scrive+committa ``n_facts`` fatti con indice crescente.

    ``n_filler`` pre-semina N fatti "rumore" (senza idx): allargano il corpus
    cosi' OGNI rebuild deserializza molti embedding -> la finestra del torn-read
    (tra validazione e re-lettura di _corpus_cache nel ramo cache-hit) si allarga
    e la race diventa riproducibile in modo affidabile, non intermittente.
    """
    reader_mem = SemanticMemory(db_path)
    writer_mem = SemanticMemory(db_path)

    for j in range(n_filler):
        writer_mem.store(Fact(proposition=f"FILLER rumore corpus n={j:04d}",
                              topic="project/x", status="model_claim"))
    # idx=0 seed: corpus non vuoto, cache costruibile.
    writer_mem.store(Fact(proposition=f"{_CONT_QUERY} idx=0000",
                          topic="project/x", status="model_claim"))
    # Warm-up encoder + prima build cache PRIMA dei thread: una eventuale
    # lazy-init non-thread-safe del modello embedding non deve inquinare il
    # test (isoliamo la race sulla NOSTRA cache, non quella del modello).
    reader_mem.recall(_CONT_QUERY, k=500)

    errors: list[tuple[str, BaseException]] = []
    errors_lock = threading.Lock()
    writer_done = threading.Event()
    seqs: dict[int, list[int]] = {}

    def writer() -> None:
        try:
            for i in range(1, n_facts + 1):
                writer_mem.store(Fact(
                    proposition=f"{_CONT_QUERY} idx={i:04d}",
                    topic="project/x", status="model_claim"))
                time.sleep(0.005)
        except Exception as exc:  # noqa: BLE001
            with errors_lock:
                errors.append(("writer", exc))
        finally:
            writer_done.set()

    def reader(tid: int) -> None:
        seq: list[int] = []
        try:
            while not writer_done.is_set():
                seq.append(_max_idx_seen(reader_mem.recall(_CONT_QUERY, k=500)))
            seq.append(_max_idx_seen(reader_mem.recall(_CONT_QUERY, k=500)))
        except Exception as exc:  # noqa: BLE001
            with errors_lock:
                errors.append((f"reader-{tid}", exc))
        finally:
            seqs[tid] = seq

    threads = [threading.Thread(target=writer, name="writer")]
    threads += [
        threading.Thread(target=reader, args=(t,), name=f"reader-{t}")
        for t in range(n_readers)
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=60)
    return errors, threads, seqs, n_facts, reader_mem


def test_concurrent_recall_no_crash_no_deadlock_final_consistency(tmp_path):
    """GARANZIE ROBUSTE sotto contesa (devono SEMPRE valere):

    (a) nessuna eccezione nei thread — una race sulla connessione persistente
        ``_dv_conn`` (sqlite "recursive use" / "closed database") affiorerebbe
        qui come errore. La sicurezza di ``_dv_conn``/``_dv_lock`` e' totale:
        ``_db_data_version`` e' interamente sotto lock e self-contained.
    (b) nessun deadlock sul ``_dv_lock`` (tutti i thread terminati entro join);
    (c) ogni reader ha effettivamente iterato;
    (d) consistenza FINALE POST-JOIN (single-thread, deterministica): a writer
        concluso e thread terminati, una recall fresca vede TUTTI i fatti — la
        data_version forza il rebuild e senza concorrenza non c'e' torn-read.
        (NB: NON si asserisce ``seq[-1]`` dei reader: la recall finale fatta
        DURANTE il drain concorrente e' soggetta al torn-read documentato dal
        test xfail sotto, quindi puo' transitoriamente vedere < n_facts.)
    """
    errors, threads, seqs, n_facts, reader_mem = _run_contention(tmp_path / "hippo.db")

    assert not errors, f"eccezioni nei thread (race su _dv_conn/_dv_lock?): {errors}"
    assert all(not th.is_alive() for th in threads), "deadlock: thread vivo dopo join"
    assert seqs and all(seqs.values()), "reader senza iterazioni"
    # Consistenza finale verificata SENZA concorrenza (deterministica).
    final = _max_idx_seen(reader_mem.recall(_CONT_QUERY, k=500))
    assert final == n_facts, (
        f"recall finale post-join vede idx={final}, atteso {n_facts}: "
        "staleness PERMANENTE (non solo transitoria) = invalidazione rotta")


def test_concurrent_recall_monotonic_visibility_no_torn_read(tmp_path):
    """Invariante di NON-staleness sotto contesa: lo snapshot servito a un
    reader non deve mai REGREDIRE (max-idx non-decrescente).

    Esponeva la race torn-read di ``_get_corpus_cache`` (il ramo cache-hit
    validava ``self._corpus_cache`` e poi RI-leggeva l'attributo nel return:
    un rebuild concorrente lento poteva riassegnarlo a una snapshot piu'
    vecchia tra validazione e return → max-idx che regredisce).

    Strategia per RED AFFIDABILE: corpus PICCOLO/veloce (recall rapide → molti
    cache-HIT, che e' la condizione del torn-read) + molti reader + molti TRIAL.
    Il torn-read scatta ~45%/trial; con N trial la probabilita' che almeno uno
    lo esponga → ~1. Pre-fix: RED (NON tollerante). Post-fix (snapshot atomico
    sotto lock): GREEN su tutti i trial.
    """
    trials = 12
    for t in range(trials):
        _errors, _threads, seqs, _n, _mem = _run_contention(
            tmp_path / f"hippo_{t}.db",
            n_facts=40, n_readers=10, n_filler=0,
        )
        for tid, seq in seqs.items():
            observed = [x for x in seq if x >= 0]
            for a, b in zip(observed, observed[1:], strict=False):
                assert b >= a, (
                    f"trial {t} reader-{tid}: max-idx regredito {a}->{b} "
                    "= snapshot STANTIA servita sotto contesa (torn read di "
                    "_corpus_cache)")
