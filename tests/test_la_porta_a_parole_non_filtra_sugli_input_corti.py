"""`hippo_facts_search` sbaglia la promessa dell'astensione nei DUE versi.

DA DOVE VIENE. La riga ④ del Summary promette *«abstention instead of
hallucination»*. Sulla porta a parole avevo documentato UN SOLO verso: la query
fuori corpus torna `[]`, che SEMBRA un'astensione e non lo e' — e' un miss di
sottostringa. ⚠️ Mancava il verso opposto, e lo ha aperto @ws2 (W2-359) col
COUNT sulla tabella, dichiarando lui stesso il limite: *«i 16.273 sono un COUNT
sull'intera tabella»*, cioe' non dicono cosa riceve chi CHIAMA.

MISURATO ALLA PORTA il 2026-08-31 alle 06:09, chiamando lo strumento MCP come
lo chiamerebbe un agente (nessuna scrittura)::

    query "l", limit=200   ->  200 righe su 200: IL TETTO SATURO
                               160289 caratteri, abbastanza da ECCEDERE la
                               finestra del client MCP che l'ha chiesta
    query "l", limit=3     ->  3 righe, ricevuta: ordinati_per created_at DESC
    parola inventata       ->  0 righe

⇒ 🔑 **La stessa porta, sulla stessa promessa, sbaglia nei due versi opposti**:
su input inventato da' un vuoto che sembra astensione; su input CORTO da' il
tetto — e non c'e' rilevanza, c'e' RECENCY. Chi chiede una lettera riceve i
fatti piu' NUOVI, che non hanno relazione con la domanda.

🪞 LA DESCRIZIONE DICHIARAVA META' DEL COMPORTAMENTO: *«Empty query returns
most-recent facts»*. E' vero, ed e' incompleto — l'ordinamento e' `created_at
DESC` SEMPRE, anche con una query non vuota. Chi legge lo schema conclude che
solo il caso degenere (query vuota) sia cronologico. Questa e' la cura: dire
alla porta di dichiarare l'ordinamento che usa davvero.

⚖️ COSA QUESTO FILE NON FA: non cambia il comportamento. Ordinare per rilevanza
richiederebbe una nozione di rilevanza che questa porta non ha (e' `SQL LIKE`);
introdurla e' una decisione di gruppo, non una correzione silenziosa. Qui si
chiude lo scarto fra cio' che la porta FA e cio' che DICE.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server


@pytest.fixture(scope="module")
def descrizione() -> str:
    for t in asyncio.run(mcp_server.list_tools()):
        if t.name == "hippo_facts_search":
            return str(t.description or "")
    pytest.fail("hippo_facts_search non e' fra gli strumenti listati")


def test_la_descrizione_dice_che_l_ordine_e_sempre_cronologico(descrizione):
    """IL CUORE: prima, chi leggeva lo schema credeva che solo la query VUOTA
    tornasse i piu' recenti."""
    assert "created_at DESC" in descrizione, descrizione[:400]
    assert "NEWEST" in descrizione or "newest" in descrizione, descrizione[:400]


def test_dice_anche_che_su_input_corto_NON_filtra(descrizione):
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: «ordinato per data» da solo non
    avvisa nessuno. Il pericolo e' che il chiamante si aspetti un'astensione e
    riceva il tetto."""
    assert "16273" in descrizione, descrizione[:400]
    assert "200" in descrizione, descrizione[:400]


def test_la_ricevuta_espone_l_ordinamento_usato(tmp_path, monkeypatch):
    """⚠️ PRESIDIA LA VIA D'USCITA: la descrizione rimanda alla ricevuta
    (`ricerca.ordinati_per`). Se quel campo sparisse, l'avviso indicherebbe
    qualcosa che non c'e' — e sarebbe peggio del silenzio."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "s"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "s"))
    out = asyncio.run(mcp_server._call_tool_impl(
        "hippo_facts_search", {"query": "canone", "limit": 3}))
    ric = json.loads(out[0].text)
    assert "ricerca" in ric, ric
    assert ric["ricerca"].get("ordinati_per") == "created_at DESC", ric["ricerca"]


def test_alla_porta_una_lettera_non_si_astiene(tmp_path, monkeypatch):
    """LA MISURA, ripetibile su store TEMPORANEO.

    ⚠️ IL CONTROLLO CHE DEVE POTER FALLIRE: la scrittura deve riuscire e la
    parola PIENA deve ritrovare il fatto. Se non lo ritrovasse, lo zero della
    parola inventata direbbe «lo store e' vuoto», non «la porta non trova».
    """
    scritto = asyncio.run(mcp_server._call_tool_impl("hippo_remember", {
        "proposition": "Il canone del contratto Rossi e' 900 euro al mese.",
        "source": "Contratto Rossi: canone 900 euro al mese.",
        "topic": "corti/x"}))
    assert json.loads(scritto[0].text).get("status"), scritto[0].text

    def righe(q: str) -> int:
        out = asyncio.run(mcp_server._call_tool_impl(
            "hippo_facts_search", {"query": q, "limit": 50}))
        return len(json.loads(out[0].text).get("items") or [])

    piena = righe("canone")
    assert piena >= 1, "la parola piena non ritrova il fatto: banco da rivedere"

    assert righe("zqxjkv") == 0, (
        "una parola inventata torna righe: il banco non sta misurando LIKE")

    # 🔑 UNA LETTERA CONTENUTA NEL FATTO: la porta non si astiene, e non
    # filtra — restituisce quanto la parola piena, o piu'.
    assert righe("o") >= piena, (
        "una sola lettera restituisce MENO della parola piena: il filtro si "
        "comporta diversamente da quanto misurato alla porta reale, "
        "rimisurare prima di fidarsi della descrizione.")
