"""La porta MCP non ha una parola per dire «questa fonte e' di terzi».

Il gate distingue QUATTRO classi di provenienza e su una di esse fonda una
cura: `external_content` toglie giurisdizione ai detector L1.x, che gradano la
sincerita' dell'AGENTE e non hanno niente da dire su un documento ingerito. Il
codice del gate la suggerisce a chi scrive, con queste parole in
`client.py`: «la strada che il gate stesso SUGGERISCE a chi scrive (`set
writer_role='external_content'`) era irraggiungibile».

⚠️ MISURATO IL 2026-09-03: dalla porta MCP quella strada e' ancora
irraggiungibile, e non per attrito — per costruzione. Lo schema che il server
PUBBLICA ai client elenca quattro valori e `external_content` non e' fra
quelli; la sua descrizione non nomina mai documenti ne' contenuto esterno; e
l'enum e' applicato dal server, quindi un valore fuori lista non arriva
nemmeno al gate.

    enum pubblicato : ['agent_inference', 'user', 'system_hook', 'trusted_hook']
    default         : 'agent_inference'                        -> agent_claim

    cio' che il ROUTER sa distinguere, e che l'enum non sa dire:
        external_content  -> external_content
        document          -> external_content
        document_ingest   -> external_content

⇒ Sul corpus vivo, contato in sola lettura lo stesso giorno, i fatti con
`writer_role='external_content'` sono **0 su 17.411**. Non e' una cura poco
adottata: e' una cura che dalla porta principale non si puo' chiedere.

⚖️ PERCHE' NON LA ACCENDO QUI. Aggiungere il valore all'enum CAMBIA il
comportamento del prodotto e indebolisce una guardia votata (l'anti-eco del
2026-08-30: quando parla l'agente, la sua `source` puo' essere un'eco della sua
stessa frase, misurato 5 su 5). Un client MCP e' per definizione non fidato, e
`writer_role` e' un suo argomento: pubblicare `external_content` significa
lasciargli spegnere L1.x dichiarandosi documento. La domanda aperta — e non la
riempio — e' **chi puo' attestare che una fonte e' di terzi**, e la risposta
non puo' essere «chi scrive lo dice».
Questo file percio' non propone la cura: FISSA il debito, in modo che il
giorno in cui qualcuno cambia l'enum se ne accorga qualcuno.
"""
from __future__ import annotations

import asyncio

import pytest

from verimem import gate_router, mcp_server

#: le classi che il router distingue, ognuna con un valore che la raggiunge
CLASSI = {
    "agent_claim": "agent_inference",
    "user_input": "user",
    "trusted_hook": "system_hook",
    "external_content": "external_content",
}


def _schema_di(nome_strumento: str) -> dict:
    """Lo schema che il server ANNUNCIA, non quello che il codice contiene."""
    from mcp.types import ListToolsRequest

    async def _leggi():
        handler = mcp_server.server.request_handlers[ListToolsRequest]
        res = await handler(ListToolsRequest(method="tools/list"))
        for t in (res.root if hasattr(res, "root") else res).tools:
            if t.name == nome_strumento:
                return (getattr(t, "inputSchema", None) or {}).get("properties") or {}
        return {}

    return asyncio.run(_leggi())


def test_il_router_distingue_davvero_quattro_classi():
    """Il controllo che deve reggere: senza, la cella sotto non misura niente.

    Se un giorno il router collassasse due classi in una, l'asserzione
    sull'enum diventerebbe vera per la ragione sbagliata.
    """
    ottenute = {gate_router.classify_provenance(v, []) for v in CLASSI.values()}
    assert ottenute == set(CLASSI), (
        f"il router non distingue piu' quattro classi: {sorted(ottenute)}"
    )


def test_l_enum_pubblicato_dalla_porta_mcp_e_quello_misurato():
    """Fissa cio' che i client vedono OGGI, cosi' un cambiamento si nota."""
    wr = _schema_di("hippo_remember").get("writer_role") or {}
    assert wr, "hippo_remember non pubblica piu' writer_role"
    assert wr.get("enum") == ["agent_inference", "user",
                              "system_hook", "trusted_hook"]
    assert wr.get("default") == "agent_inference"


@pytest.mark.xfail(
    strict=True,
    reason="DEBITO DICHIARATO, non difetto da correggere qui: la porta MCP non "
    "pubblica `external_content`, quindi un client non puo' dire che la fonte "
    "e' di terzi e la cura del 2026-08-28 resta irraggiungibile (0 fatti su "
    "17.411 sul corpus vivo). Accenderla e' un cambiamento di comportamento "
    "che indebolisce la guardia anti-eco del 30/08 e va deciso, non fatto di "
    "straforo: il giorno in cui l'enum cambia, `strict` fa tornare rossa "
    "questa cella e la decisione diventa visibile.",
)
def test_ogni_classe_di_provenienza_e_raggiungibile_dalla_porta_mcp():
    pubblicati = set((_schema_di("hippo_remember").get("writer_role") or {}).get("enum") or [])
    irraggiungibili = {
        classe for classe, valore in CLASSI.items() if valore not in pubblicati
    }
    assert not irraggiungibili, (
        f"classi che il gate distingue ma la porta MCP non sa dire: "
        f"{sorted(irraggiungibili)}"
    )


def test_la_descrizione_non_dice_a_chi_ingerisce_documenti_cosa_fare():
    """Il gate dice una cosa nel codice e un'altra ai client, ed e' il difetto
    piu' economico da riparare: e' prosa, non comportamento.

    ⚠️ Questa cella e' verde e descrive uno stato SBAGLIATO — sta qui perche'
    il giorno in cui la descrizione imparasse a nominare i documenti, il
    fallimento direbbe «bene, ora aggiorna anche l'enum».
    """
    wr = _schema_di("hippo_remember").get("writer_role") or {}
    testo = (wr.get("description") or "").lower()
    assert "external" not in testo and "document" not in testo, (
        "la descrizione ora nomina documenti/contenuto esterno: se la strada "
        "e' stata aperta, aggiorna anche l'enum e la cella xfail qui sopra"
    )
