"""T79 — la scomposizione dei ritiri non dice se una voce è un tasso o un evento.

Misurato sul corpus di casa il 13 settembre 2026::

    autohook-snapshot      1463   in 35,9 SECONDI   (2 luglio, 23:37:14→23:37:50)
    exact-text dedup        202   in 1 giorno       (lo stesso 2 luglio)
    same-source evolution   530   su 36 giorni
    heal_contradictions     202   su 32 giorni

⇒ **1665 dei 3828 fatti perduti — il 43,5% — vengono da 36 secondi di una
notte di luglio**, su fatti scritti in una settimana di maggio. La stessa
tabella li elenca accanto a voci che descrivono ciò che succede ogni giorno, e
chi la legge somma un evento chiuso con un tasso in corso.

Il dato per distinguerli **c'è già**: la scomposizione calcola `first_at` e
`last_at` per ogni voce. Non li espone e la riga di comando non li stampa,
quindi la distinzione esiste nel database e non arriva a chi legge.

⚠️ NESSUNA SOGLIA INVENTATA. «Evento» qui significa una cosa sola e verificabile:
**tutti i ritiri di quella voce cadono in un giorno solo**. Niente finestre in
secondi da tarare — una soglia scelta a tavolino sarebbe un numero nostro in
mezzo ai numeri del corpus. Il caso misto (due giorni, il 99% in uno) lo
racconta `quota_giorno_max`, che si legge accanto e non decide niente.

E il DENOMINATORE accanto al numero: `1463` da solo non dice niente finché non
si sa su quanti. La quota sta nella stessa riga di chi la genera, non nella
testa di chi legge.

Ticket: T79.
"""

from __future__ import annotations

import pathlib
import sqlite3
import tempfile
import time

import pytest

from verimem.retirement_log import retirement_breakdown

GIORNO = 86400.0


class _Store:
    """Il minimo che `retirement_breakdown` legge: una tabella `facts`.

    Costruito a mano e non dal prodotto di proposito — questo banco misura
    COME si racconta una scomposizione, non come nasce un ritiro, e farlo
    passare dal gate ci metterebbe dentro il giudice e mezz'ora di modello.
    """

    def __init__(self, db: pathlib.Path) -> None:
        self.db_path = db

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con


@pytest.fixture(scope="module")
def store() -> _Store:
    """Due popolazioni, ed è il punto: una voce fatta tutta in un giorno e una
    distribuita su tre. Con una sola delle due, qualunque criterio sembra
    funzionare — è la lezione del banco misurato su una popolazione sola."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="t79-"))
    db = d / "semantic.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE facts (id TEXT PRIMARY KEY, proposition TEXT, topic TEXT,"
        " status TEXT, created_at REAL, superseded_by TEXT, superseded_at REAL,"
        " superseded_reason TEXT, grounding_score REAL)")
    con.execute("CREATE TABLE audit_mutations (resource_id TEXT, action TEXT,"
                " principal TEXT, ts REAL)")
    ora = time.time()
    righe = []
    # L'EVENTO: dieci ritiri nello stesso minuto, un giorno solo.
    for i in range(10):
        righe.append((f"ev{i}", "una potatura", "t", "model_claim", ora - 40 * GIORNO,
                      "vincitore", ora - 30 * GIORNO + i, "potatura di manutenzione"))
    # IL TASSO: sei ritiri su tre giorni diversi.
    for i in range(6):
        righe.append((f"ta{i}", "una evoluzione", "t", "model_claim", ora - 20 * GIORNO,
                      "vincitore", ora - (5 + i % 3) * GIORNO, "evoluzione della stessa fonte"))
    righe.append(("vincitore", "il nuovo", "t", "model_claim", ora, None, None, None))
    con.executemany(
        "INSERT INTO facts (id, proposition, topic, status, created_at,"
        " superseded_by, superseded_at, superseded_reason) VALUES (?,?,?,?,?,?,?,?)",
        righe)
    con.commit()
    con.close()
    return _Store(db)


def _voce(bd: dict, motivo: str) -> dict:
    for v in bd["by_reason"]:
        if v["reason"] == motivo:
            return v
    raise AssertionError(f"voce {motivo!r} assente: "
                         f"{[v['reason'] for v in bd['by_reason']]}")


def test_CONTROLLO_la_scomposizione_vede_tutte_e_due_le_popolazioni(store):
    """⚠️ SENZA QUESTO le asserzioni sotto potrebbero passare su una tabella
    che il breakdown non ha nemmeno letto: zero voci non contraddicono
    nessuna attesa formulata su «ogni voce»."""
    bd = retirement_breakdown(store)
    assert bd["total_retired"] == 16, bd["total_retired"]
    assert _voce(bd, "potatura di manutenzione")["n"] == 10
    assert _voce(bd, "evoluzione della stessa fonte")["n"] == 6


def test_ogni_voce_dice_in_quanti_giorni_e_stata_fatta(store):
    """Il fatto grezzo da cui si legge tutto il resto."""
    bd = retirement_breakdown(store)
    evento = _voce(bd, "potatura di manutenzione")
    tasso = _voce(bd, "evoluzione della stessa fonte")
    assert evento.get("giorni") == 1, (
        "la voce fatta tutta in un giorno non dichiara in quanti giorni è "
        f"stata fatta: {evento}")
    assert tasso.get("giorni") == 3, (
        f"la voce distribuita su tre giorni non li dichiara: {tasso}")


def test_ogni_voce_dice_se_e_un_tasso_o_un_evento(store):
    """LA PROMESSA: chi legge la tabella non deve dedurlo."""
    bd = retirement_breakdown(store)
    assert _voce(bd, "potatura di manutenzione").get("forma") == "evento", (
        "una voce fatta tutta in un giorno non è dichiarata evento, e in una "
        "tabella si somma con le voci che descrivono ogni giorno")
    assert _voce(bd, "evoluzione della stessa fonte").get("forma") == "tasso", (
        "una voce distribuita su più giorni è dichiarata evento: il criterio "
        "non distingue le due popolazioni")


def test_ogni_voce_porta_il_proprio_denominatore(store):
    """«1463» non dice niente finché non si sa su quanti."""
    bd = retirement_breakdown(store)
    evento = _voce(bd, "potatura di manutenzione")
    assert evento.get("quota") == pytest.approx(10 / 16, abs=0.001), (
        f"la voce non porta la propria quota sul totale dei ritiri: {evento}")
    assert evento.get("quota_giorno_max") == pytest.approx(1.0, abs=0.001), (
        "la voce non dice quanta parte di sé cade nel giorno più denso — è il "
        f"numero che racconta il caso misto senza bisogno di una soglia: {evento}")
