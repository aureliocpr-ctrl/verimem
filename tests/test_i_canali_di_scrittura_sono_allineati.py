"""Quello che un canale di scrittura accetta, lo accettano tutti.

Il censimento delle LETTURE ha chiuso a 14 superfici su 15. Questo e' lo stesso
difetto dall'altro lato, e si vede meglio: non «un campo non esce», ma «un
campo non si puo' nemmeno mettere».

Misurato il 2026-07-30:

    campo           SDK Memory.add   MCP hippo_remember   CLI verimem save
    asserted_at           si                si                  no*
    valid_until           NO                si                  no
    derives_from          NO                si                  no
    epistemic             NO                NO                  no

    * curato in 83d65ccc

Il canale MCP e' il piu' ricco e l'SDK — quello che il README propone agli
sviluppatori — e' il piu' povero. Il corpus vivo, scritto quasi tutto da CLI e
SDK, ha `valid_until` e `derives_from` vuoti su TUTTI e 6457 i fatti.

Non e' un dettaglio di comodita': `hippo_justified_audit` pubblicizza quattro
trigger di ritrattazione, e due si reggono su quelle due colonne — «stale
(valid_until passed)» e la cascata, che la descrizione del tool chiama «the
capability no agent-memory product ships». Provato sul corpus vivo:

    n_facts 3000 · served 2571 · would_retract_ids 429 (i superseded)
    would_stale_ids 0 · would_contest_ids 0

Il tool non mente e la supersessione funziona davvero. Ma stale e cascata non
possono scattare, e non perche' il corpus e' sano: perche' dai canali che lo
riempiono quelle colonne non sono raggiungibili.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

from verimem.client import Memory

RADICE = Path(__file__).resolve().parent.parent

#: Campi che il tool MCP accetta e l'SDK no, con il perche'. Ogni voce e' una
#: divergenza spiegata; quelle senza spiegazione vanno sanate.
#:
#: I primi quattro sono argomenti che un chiamante NON deve poter usare per
#: raccontare di se': provati il 2026-07-30 contro il gate, e infatti non
#: servono a niente — writer_role=trusted_hook, status=verified e force_persist
#: finiscono `quarantined` come una scrittura qualunque
#: (tests/test_un_chiamante_non_si_dichiara_fidato.py). Restano nello schema
#: MCP per compatibilita'; darli anche all'SDK aggiungerebbe solo un'altra
#: superficie a cui chiedere di essere creduti.
DIVERGENZE_AMMESSE: dict[str, str] = {
    "writer_role": "chi scrive non dichiara il proprio ruolo per saltare le "
                   "difese: il gate lo ignora, e non serve una seconda porta",
    "status": "auto-attribuirsi lo status e' l'atto che il prodotto impedisce",
    "force_persist": "scavalcare il gate non e' un parametro dell'SDK",
    "source_signature": "impronta interna anti-tamper, la stampa il write-path",
    "agent_id": "scoping multi-tenant: l'SDK lo prende dal costruttore, "
                "non da ogni singola scrittura",
    "user_id": "come agent_id",
    "run_id": "come agent_id",
}


def _campi_di_hippo_remember() -> set[str]:
    """Le proprieta' dello schema del tool, chieste al SERVER.

    La prima versione le cercava con una regex su una finestra di sorgente e
    tirava dentro gli schemi dei tool successivi — `query`, `k`, `min_status`
    non c'entravano niente. E' il terzo criterio grezzo che oggi ha prodotto un
    falso positivo (l'id invece del contenuto nel censimento, la parola invece
    del dato sulle etichette): quando si misura una struttura, si interroga la
    struttura.
    """
    import asyncio

    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    for t in tools:
        if t.name == "hippo_remember":
            schema = getattr(t, "inputSchema", None) or {}
            return set(schema.get("properties") or {})
    raise AssertionError("hippo_remember non trovato: tool rinominato?")


def test_l_sdk_accetta_quello_che_accetta_il_tool_mcp():
    firma = set(inspect.signature(Memory.add).parameters)
    mcp = _campi_di_hippo_remember()
    # `proposition` sull'uno e `content` sull'altro sono lo stesso argomento
    mcp.discard("proposition")
    mancanti = {c for c in mcp if c not in firma} - set(DIVERGENZE_AMMESSE)
    assert not mancanti, (
        f"il tool MCP accetta campi che l'SDK non ha: {sorted(mancanti)}\n"
        f"un canale piu' ricco dell'altro significa che il corpus si riempie "
        f"in modo diverso a seconda di chi scrive — aggiungili a Memory.add, "
        f"oppure dichiara il perche' in DIVERGENZE_AMMESSE.")


def test_i_campi_che_alimentano_l_audit_sono_scrivibili_dall_sdk():
    """I due su cui si reggono `stale` e la cascata di hippo_justified_audit.

    Sono nominati a parte perche' non sono comodita': senza di loro due dei
    quattro trigger dichiarati dal tool non possono scattare, mai.
    """
    firma = set(inspect.signature(Memory.add).parameters)
    for campo in ("valid_until", "derives_from"):
        assert campo in firma, (
            f"{campo} non e' scrivibile dall'SDK: il trigger di "
            f"hippo_justified_audit che lo usa non potra' mai scattare sui "
            f"fatti scritti da li'")


def test_quello_che_l_sdk_scrive_arriva_davvero_nella_riga(tmp_path):
    """Che la firma li accetti non basta: devono finire nello store."""
    import sqlite3
    m = Memory(path=tmp_path / "semantic" / "semantic.db")
    r = m.add("Il contratto scade a fine anno.", topic="prova",
              valid_until=4102444800.0, derives_from=["aaaaaaaaaaaa"])
    fid = r.get("id") if isinstance(r, dict) else getattr(r, "id", "")
    con = sqlite3.connect(str(m.semantic.db_path))
    riga = con.execute("SELECT valid_until, derives_from FROM facts "
                       "WHERE id = ?", (fid,)).fetchone()
    con.close()
    assert riga and riga[0] == 4102444800.0, f"valid_until non persistito: {riga}"
    assert riga[1] and "aaaaaaaaaaaa" in (
        riga[1] if isinstance(riga[1], str) else json.dumps(riga[1])), riga
