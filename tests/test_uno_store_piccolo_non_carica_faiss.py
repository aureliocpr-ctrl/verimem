"""Aprire lo store non deve caricare l'indice ANN che a questa scala resta spento.

Trovato il 2026-07-31 leggendo i 38 trace in `~/.engram/hang-traces/` — file che
il watchdog scrive quando una chiamata sfonda il budget, e che nessuno aveva mai
aperto. Contando i MODULI in corso di import nel momento in cui lo stack e'
stato dumpato (non i frame: i frame dell'import machinery dicono solo «si sta
importando qualcosa»)::

    387  faiss
    129  verimem/ann_index.py
    129  verimem/ann_cache.py
     72  torch

e i tool piu' colpiti sono i piu' LEGGERI: `hippo_health` 13 trace su 38,
`hippo_stats` 10. Tool che non toccano modelli, appesi a caricare la libreria di
un indice vettoriale.

La catena e' tutta strutturale, e sta in tre righe:

* `SemanticMemory.__init__` faceva `from verimem.ann_cache import ANNCache` e
  costruiva la cache — incondizionatamente, per ogni store aperto;
* `ann_cache` importa `ann_index` a livello di modulo;
* `ann_index` importa `faiss` a livello di modulo.

Quindi APRIRE lo store caricava faiss. Due numeri misurati su questa macchina
scarica, e vanno tenuti distinti perche' il primo e' quello che si cita e il
secondo e' quello che si risparmia:

* `import faiss` da un interprete vuoto costa **925,2 ms** contro **276,5 ms**,
  cioe' ~649 ms;
* aprire lo store costa **978,8 ms** con faiss e **704,2 ms** senza — il
  risparmio vero e' **274,6 ms**, piu' basso perche' numpy, che e' meta' di
  quell'import, allo store serve comunque.

E' il secondo il numero onesto da riportare. In piu' la DLL AVX2 va cercata e
mappata: sotto carico e' la coda di quella distribuzione che si vede nei trace,
non la mediana.

E il punto che rende il costo puro spreco: l'ANN e' **dormiente sotto 100.000
fatti** (`_ANN_MIN_N`), mentre il corpus reale ne ha 6517. Si pagava il
caricamento di una libreria per una capacita' che a questa scala non si attiva
mai — la stessa classe di difetto che il prodotto gia' cura per l'embedder e per
il cross-encoder del moat (delegate-only, warm in background), su un terzo sito.

I due presidi che questo file inchioda:

1. aprire lo store e fare una recall su un corpus piccolo non importa faiss;
2. l'ordine dei gate: la soglia sulla DIMENSIONE si valuta prima della domanda
   «faiss e' disponibile?», perche' la prima e' un confronto fra interi che ho
   gia' in mano e la seconda costa mezzo secondo. Invertirli non cambia il
   risultato di una sola query e cambia il costo di ognuna.

E cio' che NON cambia, che e' la parte che vale: sopra la soglia l'ANN si
costruisce e si usa esattamente come prima. La capacita' non si tocca, si sposta
solo il momento in cui la si paga.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap


def _in_un_processo_pulito(codice: str) -> str:
    """Il test DEVE girare in un interprete suo: nella suite intera faiss e'
    quasi certamente gia' in `sys.modules` per via di un altro file, e un
    controllo in-process misurerebbe l'ordine dei test invece del prodotto."""
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(codice)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"il sottoprocesso e' fallito:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def test_aprire_lo_store_non_carica_faiss(tmp_path):
    out = _in_un_processo_pulito(f"""
        import sys
        from pathlib import Path
        from verimem.semantic import SemanticMemory
        SemanticMemory(db_path=Path(r"{tmp_path / 'semantic.db'}"))
        print("faiss" in sys.modules)
    """)
    assert out == "False", (
        "aprire lo store ha caricato faiss: ~275 ms e una DLL nativa mappata "
        "per un indice che sotto 100k fatti non viene mai costruito")


def test_una_recall_sotto_la_soglia_non_carica_faiss(tmp_path):
    """Il caso che si paga davvero: non l'apertura, ma OGNI processo che legge.

    Un corpus di due fatti e' quattro ordini di grandezza sotto il gate: la
    risposta e' identica con o senza ANN, quindi la libreria non serve.

    Salta senza modello in cache: `store(embed="sync")` e la recall lo caricano
    davvero, e in CI (warm `--no-gate`, rete chiusa) finiva in
    `LocalEntryNotFoundError`. Il primo test del file — quello che conta di
    piu', «aprire lo store non carica faiss» — NON ha bisogno di modelli e
    resta attivo ovunque."""
    import pytest as _pt

    from tests._real_model import real_model_cached
    if not real_model_cached():
        _pt.skip("modello di embedding non in cache: questo test scrive e "
                 "richiama davvero")
    out = _in_un_processo_pulito(f"""
        import sys
        from pathlib import Path
        from verimem.semantic import Fact, SemanticMemory
        m = SemanticMemory(db_path=Path(r"{tmp_path / 'semantic.db'}"))
        m.store(Fact(proposition="Il database di produzione e' PostgreSQL.",
                     topic="infra/db"), embed="sync")
        m.store(Fact(proposition="Il cluster gira su tre nodi.",
                     topic="infra/db"), embed="sync")
        res = m.recall("database di produzione", k=3)
        assert res, "recall vuota: il test non ha esercitato il path"
        print("faiss" in sys.modules)
    """)
    assert out == "False", (
        "una recall su due fatti ha caricato faiss: il gate sulla dimensione "
        "va valutato PRIMA di chiedere se la libreria e' disponibile")


def test_sopra_la_soglia_l_ann_si_usa_ancora(tmp_path, monkeypatch):
    """Controprova, ed e' la meta' che conta: se i due test sopra passassero
    perche' l'ANN e' stato spento, la cura sarebbe una rimozione travestita.

    Si abbassa il gate con `ENGRAM_ANN_MIN_N` (la stessa env che il prodotto
    espone per il deploy) e si verifica che l'indice venga costruito davvero."""
    import time as _t

    import pytest
    pytest.importorskip("faiss")

    monkeypatch.setenv("ENGRAM_ANN_RECALL", "1")
    monkeypatch.setenv("ENGRAM_ANN_MIN_N", "50")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")

    from verimem.semantic import Fact, SemanticMemory
    m = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    # Stesso seeding di test_ann_recall_equivalence: frasi distinte e
    # incorporabili, e un corpus sopra il gate abbassato — HNSW su una manciata
    # di righe non e' un banco, e' rumore.
    servizi = ["python", "postgres", "redis", "docker", "kafka", "rust"]
    for i in range(60):
        m.store(Fact(proposition=f"nota {i}: il servizio {servizi[i % 6]} e' "
                                 f"stato configurato con il valore {i}",
                     topic="infra/nodi"), embed="sync")
    m._ann_cache.min_n = 50
    m.recall("quale servizio usa redis", k=8)   # innesca il build in background
    t0 = _t.time()
    while m._ann_cache.building and _t.time() - t0 < 30:
        _t.sleep(0.05)
    assert m._ann_cache.builds == 1, (
        f"sopra la soglia l'indice ANN non e' stato costruito "
        f"(builds={m._ann_cache.builds}): la cura ha spento la capacita' "
        f"invece di rimandarne il costo")
    assert m.recall("quale servizio usa redis", k=8), (
        "recall vuota col pool ANN attivo")
