"""Un consiglio che la porta stampa dev'essere eseguibile SU QUELLA PORTA.

MISURATO il 2026-09-20 sulla stessa build, due lati:

    la ricevuta di `hippo_remember` dice
        «set writer_role='external_content' to route it to the document policy»
    e la stessa porta risponde
        {"error": "input validation failed: schema violation:
          'external_content' is not one of ['agent_inference', 'user',
          'system_hook', 'trusted_hook']"}

L'utente fa cio' che il prodotto gli dice e il prodotto lo respinge. Il
consiglio nasce una volta sola nel gate (`gate_router.py`) e vale per la CLI,
dove quel valore si puo' passare; l'enum della porta MCP e' scritto A MANO e
piu' stretto. Lo stesso testo attraversa due porte con regole diverse.

LA CURA (decisione (c1) del 2026-09-20): l'enum si GENERA dalle liste
canoniche di `gate_router` — `_EXTERNAL_ROLES`, `_TRUSTED_ROLES` e i valori
base — cosi' se domani quelle liste cambiano l'enum segue da solo.

⚠️ PERCHE' ALLARGARE L'ENUM E' ACCETTABILE ORA E NON LO ERA IERI: fino a #99
bastava dichiarare un ruolo per comprare il perdono di L1.13 (misurato: eco +
`user` -> `model_claim`). Con #99 nel ramo l'eco NON compra il perdono con
NESSUN ruolo, e la cella negativa qui sotto lo fissa: e' la condizione che
rende questa cura sicura, non un dettaglio.

⚠️ La cella positiva NON scrive a mano il valore consigliato: lo ESTRAE dal
consiglio che la porta ha appena stampato. Se domani il gate consiglia un
valore diverso, la cella segue — perche' la proprieta' difesa e' «cio' che
dici si puo' fare», non una stringa.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap

from tests._esito import esito
from verimem import gate_router, mcp_server


def _schema_di_remember() -> list[str]:
    """I valori che la porta accetta per `writer_role`, LETTI DALLO SCHEMA VIVO.

    ⚠️ NON dal sorgente. La prima stesura faceva `inspect.getsource` e cercava
    la lista letterale: avrebbe misurato la FORMA del codice, e dopo questa
    cura — in cui l'enum si GENERA — non l'avrebbe piu' trovata pur essendo
    la cura a rendere vero cio' che difende. E' l'errore che un'altra cella
    ha gia' pagato stamattina (T73).
    """
    import asyncio
    strumenti = asyncio.run(mcp_server.list_tools())
    for s in strumenti:
        if s.name.endswith("remember"):
            campo = (s.inputSchema or {}).get("properties", {}).get(
                "writer_role", {})
            return list(campo.get("enum") or [])
    raise AssertionError("la porta non espone piu' uno strumento remember")


def test_l_enum_della_porta_contiene_i_ruoli_canonici():
    """L'enum non e' piu' una lista scritta a mano che puo' divergere."""
    ammessi = set(_schema_di_remember())
    canonici = set(gate_router._EXTERNAL_ROLES) | set(gate_router._TRUSTED_ROLES)
    mancanti = canonici - ammessi
    assert not mancanti, (
        f"la porta non accetta ruoli che il prodotto considera validi: "
        f"{sorted(mancanti)}")


def _porta(args: dict) -> str:
    codice = textwrap.dedent(r"""
        import asyncio, json, os, sys, tempfile
        d = tempfile.mkdtemp()
        for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
            os.environ[v] = d
        os.environ["ENGRAM_EVENT_LOG"] = os.path.join(d, "eventi.jsonl")
        from verimem import mcp_server as M
        args = json.loads(sys.argv[1])
        async def uno():
            b = await M.call_tool("hippo_remember", args)
            print("RISPOSTA=" + " ".join(
                " ".join(getattr(x, "text", "").split()) for x in b))
        asyncio.run(uno())
    """)
    r = subprocess.run([sys.executable, "-c", codice, json.dumps(args)],
                       capture_output=True, text=True, timeout=900)
    testo = esito(r)
    for riga in testo.splitlines():
        if riga.startswith("RISPOSTA="):
            return riga[len("RISPOSTA="):]
    raise AssertionError(f"la porta non ha risposto:\n{testo}")


# ⚠️ FORMA PASSIVA, e non e' un dettaglio di stile: e' quella che il
# rilevatore di completamento riconosce. Con «si e' concluso» la porta non
# emette nessun avviso e la ricevuta torna «NOT JUDGED», cioe' il banco
# misurerebbe il silenzio invece del consiglio. Questa coppia e' la stessa
# gia' usata dal banco di T144, che in CI passa senza alcun daemon.
PROP = "Il collaudo della linea 3 e' stato concluso il 12 marzo."
FONTE = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito "
         "positivo e la linea e' stata approvata dalla commissione.")


def test_il_valore_che_la_porta_consiglia_la_porta_lo_accetta():
    """LA CELLA POSITIVA: cio' che il prodotto consiglia, la porta lo accetta.

    ⚠️ Il valore NON e' scritto qui: si estrae dal consiglio che il prodotto
    genera (`gate_router.attribution_question`). Se domani il gate consigliera'
    un altro ruolo, questa cella lo seguira' — la proprieta' difesa e' «cio'
    che dici si puo' fare», non una stringa.

    ⚠️ E si legge dalla FUNZIONE, non dalla ricevuta di una scrittura vera: la
    ricevuta porta il consiglio solo quando il moat ha dato un verdetto, e
    dove non c'e' un daemon raggiungibile torna «NOT JUDGED». Misurato qui
    stamattina: la stessa coppia che ieri notte faceva comparire il consiglio
    oggi dava `"judged": false`. Una cella che dipende da quel regime
    misurerebbe il silenzio dell'ambiente invece della proprieta' del prodotto.
    """
    consiglio = gate_router.attribution_question(gate_router.AGENT_CLAIM)
    valori = re.findall(r"writer_role='([a-z_]+)'", consiglio)
    assert valori, (
        f"il consiglio non nomina piu' nessun writer_role: {consiglio}")

    ammessi = set(_schema_di_remember())
    rifiutati = [v for v in valori if v not in ammessi]
    assert not rifiutati, (
        f"il prodotto consiglia {rifiutati} e la porta li rifiuta: un utente "
        f"che fa cio' che gli diciamo riceve «schema violation». "
        f"Ammessi: {sorted(ammessi)}")


def test_alla_porta_il_valore_consigliato_non_da_schema_violation():
    """E lo stesso valore, passato ALLA PORTA, non viene respinto.

    La cella sopra confronta due liste; questa esercita la porta. Non dipende
    dal giudice: guarda solo che la richiesta sia ACCETTATA.
    """
    consiglio = gate_router.attribution_question(gate_router.AGENT_CLAIM)
    for valore in sorted(set(re.findall(r"writer_role='([a-z_]+)'", consiglio))):
        risposta = _porta({"proposition": PROP + f" ({valore})",
                           "source": FONTE, "topic": "prova/t165",
                           "writer_role": valore})
        assert "schema violation" not in risposta, (
            f"la porta consiglia writer_role='{valore}' e poi lo RIFIUTA: "
            f"{risposta[:240]}")


def test_l_eco_con_external_content_resta_fermata():
    """Il negativo, ed e' la condizione che rende sicura questa cura.

    Allargare l'enum senza questa sarebbe stato pericoloso: prima di #99
    bastava dichiarare un ruolo per comprare il perdono di L1.13.
    """
    risposta = _porta({"proposition": PROP, "source": PROP,
                       "topic": "prova/t165eco",
                       "writer_role": "external_content"})
    assert "schema violation" not in risposta, risposta[:240]
    stato = re.search(r'"status":\s*"([^"]+)"', risposta)
    assert stato, risposta[:240]
    assert stato.group(1) == "quarantined", (
        f"l'eco con un ruolo dichiarato e' entrata SERVIBILE: {stato.group(1)}")
