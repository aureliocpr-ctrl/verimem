"""Il margine della ricevuta è una proprietà CALCOLATA, e si rende com'è.

`adjudication.margin` passava da `round(score - threshold, 4)`. La ricevuta
porta `score` e `threshold` interi, e chi rifà la sottrazione dalla ricevuta
NON ritrova il campo che la ricevuta stessa dichiara: due numeri esatti e la
loro differenza arrotondata, nello stesso dizionario.

Non è un dettaglio di stampa. Il margine dice QUANTO un fatto è passato o non
è passato, e una porta lo espone come unico numero: misurato il 2026-09-21,
sulla porta MCP il campo `margine` non esiste, quindi lì il valore pieno non
è recuperabile in nessun altro modo. Arrotondare nel nucleo toglie cifre a
tutte e tre le porte insieme, e nessuna può rimetterle.

Quattro decimali non sono nemmeno una scelta leggibile: il giudice locale
produce punteggi con quindici cifre significative (`96.00531768798828`), e
il taglio cade in un posto che non corrisponde né alla precisione del
giudice né a quella che una pagina mostrerebbe.

I LIVELLI, dichiarati: la cella del margine chiama `_adjudication`, cioè la
FUNZIONE che costruisce il campo; la cella di coerenza passa dalla PORTA
(`Memory.add`). Servono tutte e due perché sulla porta del giudice iniettato
il punteggio arriva già intero — misurato: `Score: 96.005051` diventa `96.0`,
e con uno score tondo l'arrotondamento non toglierebbe niente, quindi una
cella scritta solo lì sarebbe verde senza misurare nulla.
"""
from __future__ import annotations

import os
from decimal import ROUND_DOWN, Decimal
from types import SimpleNamespace

# encoder in-process, nessun daemon condiviso: come il banco della ricevuta
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")

from verimem.client import Memory, _adjudication  # noqa: E402

# Uno score con più di quattro decimali, scelto perché a QUESTA magnitudine
# arrotondare e troncare danno due risultati diversi. Con `…535`, il caso che
# verrebbe naturale scrivere, le due operazioni COINCIDONO — il float più
# vicino a 0.00535 sta sotto — e il banco non direbbe quale delle due avviene.
SCORE = 96.005051
SOGLIA = 70.0


class _GiudiceFinto:
    """Il giudice iniettato del banco della ricevuta: punteggio fisso, nessuna
    rete, nessun modello da caricare."""

    def __init__(self, score: float) -> None:
        self._score = score

    def complete(self, system, messages, **kw):  # noqa: ANN001
        return type("R", (), {"text": f"Score: {self._score}"})()


def _tronca(x: float, n: int = 4) -> float:
    return float(Decimal(repr(x)).quantize(Decimal(f"1e-{n}"), rounding=ROUND_DOWN))


def test_il_caso_scelto_distingue_arrotondamento_da_troncamento():
    """Il controllo positivo del banco, e sta DENTRO il banco: senza, le celle
    sotto potrebbero passare con un caso in cui le due operazioni danno lo
    stesso numero — un verde che non misura niente."""
    for soglia in (SOGLIA, 40.0):
        margine = SCORE - soglia
        assert round(margine, 4) != _tronca(margine, 4), (
            f"a soglia {soglia} il caso non distingue le due letture")


def test_il_margine_e_la_differenza_dei_due_numeri_che_la_ricevuta_porta():
    """Livello: la funzione che costruisce il campo."""
    gate = SimpleNamespace(grounding_score=SCORE, threshold=SOGLIA, judge=None)
    adj = _adjudication(gate, disposition="admitted", verified_by=None,
                        warnings=[])
    atteso = float(adj["score"]) - float(adj["threshold"])
    assert adj["margin"] == atteso, (
        f"la ricevuta porta score={adj['score']} e threshold={adj['threshold']}, "
        f"ma margin={adj['margin']} invece di {atteso}")


def test_alla_porta_il_margine_resta_coerente_con_i_suoi_due_numeri(
        tmp_path, monkeypatch):
    """Livello: la porta. Non misura i decimali — il punteggio del giudice
    iniettato arriva intero — ma tiene fermo che il campo continui a essere la
    differenza dei due numeri che la ricevuta espone."""
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    m = Memory(str(tmp_path / "porta.db"), grounding_llm=_GiudiceFinto(96))
    adj = m.add("Analytics runs on Postgres.",
                source="We migrated analytics to Postgres last quarter.")["adjudication"]
    assert adj["score"] is not None and adj["threshold"] is not None
    assert adj["margin"] == float(adj["score"]) - float(adj["threshold"])
