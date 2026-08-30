"""Col ranking degradato, un pavimento svuotava `hippo_recall_history`.

MISURATO ALLE PORTE il 2026-08-31 alle 00:24, cinque fatti nello store,
pavimento 0.5, degrado simulato spegnendo `semantic._encode_prepared_within_budget`::

    regime      hippo_recall_history      hippo_facts_recall (gemella)
    a caldo     n=5                       n=5
    degradato   n=0   ← si svuotava       n=5
    degradato, SENZA pavimento: recall_history n=5

⇒ Le tre celle reggono insieme: a caldo entrambe rispondono (controllo), senza
pavimento il degrado non svuota (popolazione opposta), e la gemella nello STESSO
degrado risponde (attribuzione). **La differenza e' la guardia, non il degrado.**

PERCHE'. Il ramo keyword assegna `score 0.0` a TUTTI i risultati: non «nessuna
somiglianza» ma somiglianza **NON MISURATA**. Confrontarla con una soglia di
somiglianza e' un errore di categoria. `git grep _recall_degraded_count`::

    client.py:1126 · mcp_server.py:13764 · proactive_step_injector.py:114
    temporal_context.py   NESSUNA   ← e li' c'e' il pavimento

⇒ **Il quarto consumatore.** Ed e' l'unico in cui il filtro sta nella FUNZIONE
invece che nell'handler — il commento accanto spiega perche' (a valle lo score
non esiste piu') — quindi la guardia scritta nell'handler gemello non poteva
raggiungerlo nemmeno volendo.

⚠️ E' un'astensione FALSA su un canale letto da modelli, che non hanno modo di
sospettarla.

🪞 CORREZIONE DI UNA MIA MISURA DI VENTI MINUTI PRIMA. Nel commit `e24d25d5` ho
scritto che questa porta «applicava il pavimento (`n:0` con 0.5)»: quel `n=0`
era il mio conteggio su una chiave che non esiste (`results` invece di
`context`). **A caldo la porta NON taglia**: n=5. La cura di allora — il campo
`min_relevance` nella ricevuta — resta giusta, la ricevuta davvero non lo
portava; era sbagliata la ragione. Il taglio esiste, ma solo nel degrado, ed e'
il difetto curato qui.

Banco: ``docs/stato-reale/banchi/ws3-il-quarto-consumatore-che-non-conosce-il-degrado.py``
"""

from __future__ import annotations

import asyncio
import json

import pytest

import verimem.semantic as sem
from verimem import mcp_server

DOMANDA = "quanti metri quadrati ha il magazzino K-77"
#: Qualunque valore > 0: nel degrado OGNI punteggio vale 0.0, quindi e' il
#: FATTO di avere un pavimento a tagliare, non quanto sia alto.
PAVIMENTO = 0.5


def _chiama(nome: str, args: dict) -> dict:
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)


def _righe(d: dict, nome: str) -> list:
    """La chiave la si LEGGE, non la si indovina: `context` di qua, `items` di
    la'. Il banco ne aveva indovinata una terza e ogni cella della gemella
    dava zero."""
    chiave = "context" if nome == "hippo_recall_history" else "items"
    assert chiave in d, f"{nome}: {chiave} assente, ricevuta {sorted(d)}"
    return d.get(chiave) or []


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    for i in range(1, 6):
        _chiama("hippo_remember", {
            "proposition": f"Il magazzino K-{70 + i} di Rovigo ha "
                           f"{4000 + i * 100} metri quadrati.",
            "source": f"Registro immobili, scheda K-{70 + i}: superficie "
                      f"{4000 + i * 100} metri quadrati.",
            "topic": "deg/mag"})
    return tmp_path


@pytest.fixture
def degradato(monkeypatch):
    monkeypatch.setattr(sem, "_encode_prepared_within_budget",
                        lambda *a, **k: None)


# ⚠️ IL CONTROLLO «a caldo col pavimento la porta risponde» NON e'
# presidiabile qui: **sotto pytest l'embedder e' uno stub** e a caldo
# `sm.recall` non restituisce NULLA su questa domanda, quindi non c'e'
# risposta da tagliare e un verde non proverebbe niente. Sta nel banco, che
# gira fuori da pytest: a caldo n=5 con lo stesso pavimento.
# 🔑 Cio' che RESTA misurabile qui e' il ramo degradato, dove i punteggi
# valgono 0.0 per costruzione e non dipendono dall'embedder.


def test_col_degrado_il_pavimento_non_svuota_piu(store, degradato):
    """IL CUORE: prima della cura, n=0."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5,
                                         "min_relevance": PAVIMENTO})
    assert len(_righe(d, "hippo_recall_history")) > 0, d


def test_il_degrado_da_solo_non_svuota(store, degradato):
    """⚠️ LA POPOLAZIONE OPPOSTA: senza pavimento la risposta era gia' piena.
    Se si svuotasse anche qui, la causa non sarebbe il pavimento e la cura
    curerebbe la cosa sbagliata."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5})
    assert len(_righe(d, "hippo_recall_history")) > 0, d


def test_la_porta_dichiara_di_aver_sospeso_il_pavimento(store, degradato):
    """Non basta non svuotare: una lista piena NONOSTANTE un pavimento alto e'
    inspiegabile da fuori. La ricevuta deve dire perche'."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5,
                                         "min_relevance": PAVIMENTO})
    assert d.get("ranking_degraded") is True, sorted(d.items())


def test_a_caldo_non_si_dichiara_un_degrado_che_non_c_e(store):
    """⚠️ L'ALTRA META' DEL PRESIDIO: un campo che dicesse sempre «degradato»
    passerebbe il test qui sopra senza dire niente di vero."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5,
                                         "min_relevance": PAVIMENTO})
    assert d.get("ranking_degraded") is None, sorted(d.items())


# ⚠️ LA CELLA CHE ATTRIBUISCE — «la porta gemella nello STESSO degrado e
# con lo STESSO pavimento risponde» — NON e' presidiabile qui: sotto lo stub
# quella porta restituisce `items: []` gia' a caldo, quindi un suo verde non
# proverebbe nulla e un suo rosso non sarebbe il prodotto. Sta nel banco, che
# gira fuori da pytest, e li' vale n=5 contro n=0.


# ─────────────────────────────────────────────────────────────────────────────
# IL PRESIDIO PIU' IMPORTANTE, e non passa da nessuna porta: la cura toglie il
# taglio SOLO sul ramo degradato. Se avesse spento il pavimento in generale,
# avrei curato un'astensione falsa creando un'astensione MANCATA. Alle porte
# non e' verificabile sotto pytest (lo stub non produce punteggi a caldo), e
# allora si misura la funzione con un doppio: punteggi decisi da me, contatore
# del degrado deciso da me, nessun embedder di mezzo.
# ─────────────────────────────────────────────────────────────────────────────

class _Fatto:
    def __init__(self, i: int) -> None:
        self.id = f"f{i}"
        self.proposition = f"proposizione {i}"


class _SM:
    """Il minimo che `recall_with_history` tocca. `db_path` inesistente: le
    dispute sono un arricchimento e cadono nel loro try/except."""

    db_path = "/non/esiste/x.db"

    def __init__(self, punteggi: list[float], *, degrada: bool) -> None:
        self._punteggi = punteggi
        self._degrada = degrada
        self._recall_degraded_count = 0

    def recall(self, query: str, k: int = 5):
        if self._degrada:
            self._recall_degraded_count += 1
        return [(_Fatto(i), p) for i, p in enumerate(self._punteggi)]


def test_col_ranking_buono_il_pavimento_taglia_ancora():
    """Due sopra, due sotto: devono restarne due."""
    from verimem.temporal_context import recall_with_history
    sm = _SM([0.9, 0.8, 0.2, 0.1], degrada=False)
    assert len(recall_with_history(sm, "q", min_relevance=0.5)) == 2


def test_col_ranking_degradato_non_taglia_nessuno():
    """Gli stessi punteggi, ma il recall ha dichiarato il degrado: nessun
    taglio, perche' `0.0` li' significa NON MISURATO."""
    from verimem.temporal_context import recall_with_history
    sm = _SM([0.0, 0.0, 0.0, 0.0], degrada=True)
    assert len(recall_with_history(sm, "q", min_relevance=0.5)) == 4


def test_senza_pavimento_nulla_cambia_in_nessuno_dei_due_regimi():
    """⚠️ L'ULTIMA POPOLAZIONE: la guardia non deve fare NIENTE quando nessun
    pavimento e' stato chiesto."""
    from verimem.temporal_context import recall_with_history
    for degrada in (False, True):
        sm = _SM([0.9, 0.1], degrada=degrada)
        assert len(recall_with_history(sm, "q")) == 2, degrada
