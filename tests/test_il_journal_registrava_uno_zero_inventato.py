"""Il journal registra come `best` un punteggio che nessun risultato aveva.

Il pezzo (i) della cura-pavimento ha conservato `_n_prima` e `_best_prima`
**prima** del taglio, e il suo commento (`client.py:1258-1263`) dice perché::

    «Il massimo ricalcolato dopo varrebbe `0.0` su una lista vuota, cioè un
     numero INVENTATO: il punteggio migliore esisteva, era solo sotto la soglia.»

⚠️ **Trenta righe più sotto, nella stessa funzione, il journal continua a
calcolare esattamente quel numero** (`client.py:1297`)::

    _emit_flow("flow.recall", kind="search", n=len(out),
               best=round(max(… for i in out), default=0.0), 4))

`out` è già stato riassegnato dal filtro alla riga 1269. Quando il pavimento
taglia tutto, `best` vale `0.0` — e quello zero **non è una misura**.

MISURATO SUL JOURNAL REALE (entrambe le parti, `events.jsonl` + `.jsonl.1`):

    flow.recall totali          : 2499
    letture VUOTE (n=0)         :  254 = 10.2%
    di queste, con best = 0     :  254  ← TUTTE, per costruzione

⇒ Chi analizza il journal per capire perché una lettura non ha risposto legge
**254 zeri** e conclude «non ha trovato nulla», mentre parte di quelle letture
**avevano trovato** e sono state tagliate. È la stessa distinzione che l'avviso
a valle fa correttamente e il journal no.

🔑 **La forma è la classe ①: due punti calcolano lo stesso valore, uno è stato
curato e l'altro è rimasto indietro** — e il difetto è *dichiarato nel commento*
del punto curato.

📌 `_best_prima` e `_tagliati` esistono già e sono **in scope** al punto di
emissione: la cura non aggiunge stato, usa quello che c'è.
"""
from __future__ import annotations

import pytest

import verimem.client as C
from verimem.client import Memory

DOMANDA = "quanti metri quadrati ha il magazzino K-77"


@pytest.fixture()
def registro(tmp_path):
    m = Memory(str(tmp_path / "reg.db"))
    for i in range(1, 6):
        m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
              f"metri quadrati.", topic="az/mag")
    return m


@pytest.fixture()
def eventi(monkeypatch):
    """Cattura ciò che il prodotto scrive nel journal, senza toccare il file."""
    raccolti: list[tuple] = []
    monkeypatch.setattr(C, "_emit_flow",
                        lambda nome, **kw: raccolti.append((nome, kw)))
    return raccolti


def _recall_event(eventi):
    ev = [kw for nome, kw in eventi if nome == "flow.recall"]
    assert ev, "nessun flow.recall emesso"
    return ev[-1]


def test_il_PRESUPPOSTO_la_soglia_taglia_tutto(registro):
    """Verificato, non assunto: se un giorno la soglia smettesse di svuotare,
    il test sotto passerebbe per la ragione sbagliata."""
    assert len(registro.recall(DOMANDA, k=5, min_relevance=0.99)) == 0
    assert len(registro.recall(DOMANDA, k=5, min_relevance=0.0001)) > 0


def test_il_journal_non_registra_uno_zero_inventato(registro, eventi):
    """IL CUORE: la soglia ha tagliato tutto, ma un punteggio migliore
    ESISTEVA. Il journal deve riportarlo, non lo zero della lista vuota."""
    registro.recall(DOMANDA, k=5, min_relevance=0.99)
    kw = _recall_event(eventi)
    assert kw.get("n") == 0
    assert kw.get("best"), (
        "il journal registra best=0 su una lettura in cui qualcosa era stato "
        f"trovato e poi tagliato: {kw}"
    )


def test_il_journal_dice_QUANTI_ne_sono_stati_tagliati(registro, eventi):
    """Senza questo, `n=0` e `best>0` restano due numeri che il lettore deve
    interpretare. Il conteggio c'è già (`_tagliati`) e costa una chiave."""
    registro.recall(DOMANDA, k=5, min_relevance=0.99)
    kw = _recall_event(eventi)
    assert kw.get("tagliati"), kw


def test_una_lettura_SERVITA_registra_il_best_servito(registro, eventi):
    """IL PRESIDIO: dove non si taglia niente, il campo non cambia
    significato. Resta verde anche senza la cura."""
    r = registro.recall(DOMANDA, k=5, min_relevance=0.0001)
    kw = _recall_event(eventi)
    atteso = max(float(i.get("score") or 0.0) for i in r)
    assert kw.get("n") == len(r)
    assert abs(float(kw.get("best") or 0.0) - atteso) < 0.001, kw


def test_una_ricerca_che_non_trova_NULLA_registra_zero(tmp_path, eventi):
    """L'ALTRO PRESIDIO, e separa i due significati dello zero: su uno store
    vuoto non c'è niente da tagliare, e lo zero è vero."""
    m = Memory(str(tmp_path / "vuoto.db"))
    m.recall(DOMANDA, k=5)
    kw = _recall_event(eventi)
    assert kw.get("n") == 0
    assert not kw.get("best")
    assert not kw.get("tagliati")
