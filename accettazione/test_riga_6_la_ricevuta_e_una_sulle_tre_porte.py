"""RIGA 6 — la ricevuta è UNA sulle tre porte.

LA PROMESSA. Lista chiusa della 0.7.7, riga 6 (21/09 21:5x); invariante I4 del piano del
15/09 («le tre porte, SDK, CLI e MCP, danno lo stesso verdetto sullo stesso ingresso»). Il
README (quickstart Python, CLI e MCP) presenta tre porte sullo STESSO prodotto e sullo
stesso store. `verimem.core.ricevuta.CHIAVI` e' il contratto: «le chiavi che ogni porta
DEVE rendere: ne' una di piu', ne' una di meno».

COSA VEDE L'UTENTE. Scrive lo stesso fatto con la stessa fonte dall'SDK, dal comando
`verimem remember --json` e dallo strumento `verimem_remember`: chi legge la ricevuta deve
trovare gli stessi nomi, lo stesso esito e lo stesso punteggio, qualunque porta abbia
usato. Il 16/09 le chiavi erano 14 (SDK), 24 (MCP, con `anti_confab_warnings` al posto
di `warnings`), 11 (CLI); il 21/09 sul tronco f0064788 i nomi del nucleo pieni erano MCP
3/14, CLI 12/14, SDK 12/14.

LA PROVA. Tre utenti, tre store (una scrittura ripetuta nello stesso store sarebbe un
duplicato, non la stessa scrittura). Controllo positivo: la porta SDK deve rendere tutte le
14 chiavi, altrimenti il confronto misurerebbe un contratto che nessuno rispetta.

CHI LA CHIUDE: 1b.3 (una porta sola: CLI e MCP passano da `Memory.add`), T183. Oggi: ROSSA.
"""
from __future__ import annotations

import json

from conftest import json_di

FATTO = "Analytics runs on Postgres."
FONTE = "We migrated the analytics store to Postgres last quarter."

CODICE_SDK = r'''
import json
from verimem import Memory
from verimem.core.ricevuta import CHIAVI
r = Memory().add(FATTO_QUI, source=FONTE_QUI, topic="accettazione")
print("ESITO " + json.dumps({"chiavi": list(CHIAVI), "ricevuta": r}, default=str))
'''.replace("FATTO_QUI", repr(FATTO)).replace("FONTE_QUI", repr(FONTE))


def test_riga_6_sdk_cli_e_mcp_rendono_la_stessa_ricevuta(nuovo_utente):
    sdk = nuovo_utente("sdk").python(CODICE_SDK)
    righe = [r for r in sdk.stdout.splitlines() if r.startswith("ESITO ")]
    assert righe, f"porta SDK: {sdk.stderr[-800:]}"
    dati = json.loads(righe[-1][len("ESITO "):])
    chiavi, ricevute = dati["chiavi"], {"sdk": dati["ricevuta"]}
    assert len(chiavi) == 14 and set(chiavi) <= set(ricevute["sdk"]), (
        f"CONTROLLO POSITIVO SPENTO: la porta SDK non rende le 14 chiavi del contratto: "
        f"mancano {sorted(set(chiavi) - set(ricevute['sdk']))}")

    cli = nuovo_utente("cli").cli("remember", FATTO, "--source", FONTE,
                                  "--topic", "accettazione", "--json")
    ricevute["cli"] = json_di(cli)

    with nuovo_utente("mcp").mcp() as sessione:
        ricevute["mcp"] = sessione.chiama("verimem_remember", {
            "proposition": FATTO, "source": FONTE, "topic": "accettazione"})

    mancanti = {porta: sorted(set(chiavi) - set(r)) for porta, r in ricevute.items()}
    assert not any(mancanti.values()), (
        f"le porte non rendono il contratto della ricevuta: chiavi mancanti {mancanti}")
    esiti = {porta: r.get("esito") for porta, r in ricevute.items()}
    assert len(set(esiti.values())) == 1, f"lo stesso ingresso, tre esiti: {esiti}"
    punteggi = {porta: r.get("punteggio") for porta, r in ricevute.items()}
    valori = [p for p in punteggi.values() if p is not None]
    assert len(valori) == 3 and max(valori) - min(valori) < 1e-6, (
        f"lo stesso ingresso, punteggi diversi o assenti: {punteggi}")
