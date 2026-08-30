"""`hippo_recall_history` non diceva quale pavimento avesse usato.

📌 Questo file si chiamava `test_la_porta_applicava_il_pavimento_senza_dirlo.py`
(commit `e24d25d5`): il nome affermava un taglio che a caldo non avviene —
vedi la correzione qui sotto.

MISURATO ALLA PORTA il 2026-08-31 alle 00:12, store temporaneo con UN fatto,
giudice locale assente per costruzione::

    porta                  argomento             ricevuta
    hippo_facts_recall     min_relevance=0.5     min_relevance=0.5
    hippo_recall_history   min_relevance=0.5     ['context', 'n']   ← muta

⇒ **La porta accettava il pavimento e non lo riportava.** Chi legge quella
ricevuta non puo' distinguere «il corpus non ha risposte» da «un pavimento le
ha tagliate» — la distinzione che la porta gemella dichiara esplicitamente di
garantire nel proprio schema (*«a short list from a poor corpus and a short
list from a high floor stay distinguishable»*).

🚨 CORREZIONE, 00:30 dello stesso giorno. La prima stesura di questo docstring
diceva «lo applicava (`n: 0`)» e quel numero era **il mio conteggio su una
chiave inesistente** (`results` invece di `context`): il misuratore, non il
prodotto. Rimisurato con la chiave letta dalla ricevuta, **a caldo la porta NON
taglia** (n=5 su cinque fatti). La lacuna curata qui — il campo assente — era
reale e resta; era sbagliata la ragione. Il taglio esiste ma solo col ranking
DEGRADATO, ed e' un difetto diverso, curato in
``test_il_quarto_consumatore_non_conosceva_il_degrado.py``.

📌 SESTA GENERAZIONE DELLA STESSA CURA, e le prime cinque sono scritte nei
commenti di `mcp_server.py`: hanno fatto ARRIVARE il pavimento su questa porta —
una alla volta, ogni volta perche' la precedente non la raggiungeva. Nessuna lo
ha fatto DIRE. 🔑 *Far funzionare un meccanismo e far dire alla porta cosa ha
fatto sono due lavori diversi, e il secondo non viene gratis col primo.*

⚠️ COSA QUESTA CURA NON FA, dichiarato: non cambia nessun valore esistente e
non tocca il filtro. Aggiunge il campo con la stessa convenzione delle porte
gemelle — il pavimento che ha davvero filtrato, oppure `null`.

🪞 REPERTO APERTO E NON CURATO QUI, misurato nella stessa esecuzione:
`hippo_facts_recall` con `min_relevance="auto"` riporta `null`, perche' lo store
calcola `_auto_relevance_floor() == 0.0` e zero e' falsy. ⇒ Chi chiede il
pavimento auto-calibrato riceve una ricevuta IDENTICA a chi non ha chiesto
nulla. La causa e' il pavimento che vale zero — fronte @ws2/@ws6, misurato
indipendentemente da loro sul corpus reale — e la cura non e' in questo file.

Banco: ``docs/stato-reale/banchi/ws3-il-tipo-dichiarato-e-la-parola-auto.py``
"""

from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server

DOMANDA = "quanto e' la penale del contratto Rossi"
FATTO = "La penale del contratto Rossi e' 120 euro al giorno."
FONTE = "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."


def _chiama(nome: str, args: dict) -> dict:
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    _chiama("hippo_remember", {"proposition": FATTO, "source": FONTE,
                               "topic": "pav/hist"})
    return tmp_path


def test_la_ricevuta_porta_il_pavimento_che_ha_filtrato(store):
    """IL CUORE: il campo esiste e vale cio' che e' stato passato."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5,
                                         "min_relevance": 0.5})
    assert "min_relevance" in d, sorted(d.keys())
    assert d["min_relevance"] == pytest.approx(0.5), d


def test_senza_pavimento_la_ricevuta_dice_null(store):
    """⚠️ LA POPOLAZIONE OPPOSTA: se il campo riportasse sempre un numero,
    «nessun pavimento» e «pavimento zero» tornerebbero indistinguibili — lo
    stesso difetto spostato di un passo. La convenzione delle porte gemelle e'
    `null` quando nessun pavimento ha filtrato."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5})
    assert "min_relevance" in d, sorted(d.keys())
    assert d["min_relevance"] is None, d


def test_i_campi_di_prima_sono_ancora_li(store):
    """La cura e' ADDITIVA: se avesse cambiato `context` o `n` avrei curato la
    ricevuta trasformandola in un'altra cosa."""
    d = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5})
    for campo in ("context", "n"):
        assert campo in d, sorted(d.keys())


def test_la_porta_gemella_usa_la_stessa_convenzione(store):
    """⚠️ PRESIDIA LA PREMESSA, non solo la cura: il valore di questo campo sta
    nell'essere LO STESSO campo, con lo stesso nome e la stessa convenzione,
    delle altre porte del pavimento. Se domani la gemella cambiasse convenzione,
    questo presidio resterebbe verde mentre la coerenza — che e' il punto —
    sarebbe rotta."""
    a = _chiama("hippo_facts_recall", {"query": DOMANDA, "k": 5,
                                       "min_relevance": 0.5})
    b = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5,
                                         "min_relevance": 0.5})
    assert a.get("min_relevance") == b.get("min_relevance") == pytest.approx(0.5)
    senza_a = _chiama("hippo_facts_recall", {"query": DOMANDA, "k": 5})
    senza_b = _chiama("hippo_recall_history", {"query": DOMANDA, "k": 5})
    assert senza_a.get("min_relevance") is senza_b.get("min_relevance") is None
