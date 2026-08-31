"""`asserted_at` passato a `hippo_remember`: accettato senza errore, e ignorato.

DA DOVE VIENE. @ws7 ha misurato (03:38 del 2026-08-31) che il tempo dell'evento
non e' popolato; io ho verificato in sola lettura sullo store reale alle 03:47::

    TOTALE                16805
    asserted_at IS NULL   16805      ← MAI valorizzato (non «= 0»)

⚠️ La differenza fra NULL e 0 non e' pedanteria: `recall_as_of` fa
`born = asserted_at if asserted_at is not None else created_at`, quindi con NULL
**il ripiego scatta sempre e il viaggio nel tempo FUNZIONA** — misurato alla
porta SDK su tre celle (`92f73123`). ⇒ La frase difendibile non e' «non c'e'
storia bi-temporale» (falsificabile in trenta secondi), ma: **delle due
dimensioni promesse una non e' mai popolata, e ogni interrogazione temporale
ricade sul tempo di SCRITTURA**.

🔑 PERCHE' NESSUNO LA POPOLA — misurato agli schemi e alla porta:

    asserted_at nello schema MCP      hippo_ingest_conversation    1 porta su ~5
    hippo_remember                    NON lo espone
    CLI `verimem remember --help`     non lo nomina (0 occorrenze)
    SDK `Memory.add`                  lo accetta (client.py:447)

⇒ **La porta di scrittura PRINCIPALE non lo chiede**, e chi passa dalla CLI
nemmeno. Ma il punto peggiore e' un altro, misurato ALLA PORTA::

    hippo_remember(..., asserted_at=<marzo>)  →  status=model_claim, error=None
    riga nello store                          →  asserted_at NULL

⇒ 🔑 **Accettato in SILENZIO e IGNORATO.** Nemmeno il validatore lo ferma: lo
schema lenient controlla i campi DICHIARATI e ammette gli altri. Un chiamante
che passa quel campo — cosa ragionevole, visto che esiste nel modello e su
un'altra porta — **crede di aver impostato il tempo dell'evento e non l'ha
fatto**, senza alcun segnale.

⚖️ COSA QUESTA CURA FA E NON FA: fa dire alla descrizione cio' che la porta fa
davvero. **NON** aggiunge il parametro: accettarlo su `hippo_remember`
cambierebbe il contratto della porta principale ⇒ decisione di gruppo, proposta
lasciata sul canale.
"""

from __future__ import annotations

import asyncio

import pytest

from verimem import mcp_server


@pytest.fixture(scope="module")
def descrizione() -> str:
    for t in asyncio.run(mcp_server.list_tools()):
        if t.name == "hippo_remember":
            return str(t.description or "")
    pytest.fail("hippo_remember non e' fra gli strumenti listati")


def test_la_descrizione_dice_che_il_tempo_dell_evento_non_si_imposta_qui(
        descrizione):
    """IL CUORE: prima, chi passava `asserted_at` non riceveva nessun segnale —
    né dalla porta né dalla descrizione."""
    assert "asserted_at" in descrizione, descrizione[-400:]
    assert "IGNORED" in descrizione or "ignored" in descrizione, descrizione[-400:]


def test_dice_anche_DOVE_si_puo_impostare(descrizione):
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: dire «qui no» senza dire «là sì»
    lascia credere che il prodotto non lo supporti affatto."""
    assert "hippo_ingest_conversation" in descrizione, descrizione[-400:]


def test_e_che_le_letture_temporali_FUNZIONANO_lo_stesso(descrizione):
    """⚠️ LA PARTE CHE EVITA LA LETTURA CATASTROFICA: senza questa riga, chi
    legge conclude che il viaggio nel tempo sia rotto. Non lo è — ricade sul
    tempo di scrittura, cioè lavora su un asse invece che su due."""
    assert "still work" in descrizione or "one axis" in descrizione, descrizione[-400:]


def test_asserted_at_passato_a_remember_resta_NULL(tmp_path, monkeypatch):
    """LA MISURA, ripetibile: la porta accetta il campo e lo store non lo vede.

    ⚠️ CONTROLLO CHE DEVE POTER FALLIRE: la scrittura deve RIUSCIRE. Se
    fallisse, il NULL a valle direbbe «la scrittura non è avvenuta», non «il
    campo è stato ignorato».
    """
    import json
    import sqlite3
    import time

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "s"))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path / "s"))
    marzo = time.time() - 150 * 86400
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", {
        "proposition": "Il canone Verdi e' 700 euro al mese.",
        "source": "Contratto Verdi: canone 700 euro al mese.",
        "topic": "at/x", "asserted_at": marzo}))
    ricevuta = json.loads(out[0].text)
    assert ricevuta.get("status"), f"la scrittura non e' riuscita: {ricevuta}"

    con = sqlite3.connect(
        f"file:{mcp_server._ag().semantic.db_path}?mode=ro", uri=True)
    righe = con.execute("SELECT asserted_at FROM facts").fetchall()
    con.close()
    assert righe, "nessun fatto scritto: il controllo non regge"
    assert all(r[0] is None for r in righe), (
        f"asserted_at ORA arriva allo store ({righe}): la porta ha smesso di "
        "ignorarlo e la descrizione va aggiornata — è la cura che era stata "
        "proposta al gruppo.")
