"""Il censimento: OGNI superficie che restituisce fatti porta il verdetto?

Sette difetti in due giorni, una sola forma — un valore calcolato bene in un
punto e non propagato alle superfici che lo devono mostrare:

    il moat girava da CLI             e non da MCP           (7b8af116)
    il verdetto usciva da 1 lettura   e non dalle altre 3    (ca85cb0a)
    l'astensione era accesa su MCP    e spenta su SDK/console/gateway
    l'ingest giudicava da SDK         e non dal comando import
    il backup seguiva un path fisso   e non lo store in uso
    tip e recent mostravano lo status e non il verdetto      (beea3057)

Ogni cura e' stata puntuale, e ogni volta ne e' saltata fuori un'altra. La
matrice promesse x canali e' lo stesso strumento coi canali scritti a mano: se
nasce una superficie nuova, non se ne accorge.

Questo file chiude la classe invece dell'ottava istanza. Il censimento chiama i
tool su uno store con UN fatto giudicato e usa un criterio operativo, non
un'euristica sul nome: se nella risposta compare il CONTENUTO di quel fatto,
e' una superficie che restituisce fatti, e allora deve portare anche il
verdetto.

Il criterio e' costato due correzioni, e vanno tenute a mente perche' sono il
modo in cui uno strumento del genere mente. Cercare l'id sbagliava in entrambe
le direzioni: intercettava `justified_audit`, che restituisce solo una lista di
identificativi e a cui il verdetto per-fatto non si chiede, e MANCAVA
`recall_history`, che stampa la proposizione senza l'id — una superficie di
recall vera, rimasta invisibile finche' il criterio non e' stato corretto.

Misurato il 2026-07-30 su 241 tool, mentre la cura procedeva:

    4 portano il verdetto, 11 no      (prima)
    9 portano                          (contratto unico nei moduli)
    13 portano                         (recall_history, briefing, topics)
    14 portano,  1 no                  (aggregato con n_judged)

L'ultima non e' un difetto ed e' dichiarata con il perche'.
`test_le_scoperte_sono_ancora_quelle_dichiarate` fallisce sia se ne nasce una
in piu' sia se ne viene curata una senza spostarla: un elenco che si aggiorna
solo quando peggiora non presidia niente.
"""
from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path

import pytest

FATTO = "Il servizio di fatturazione ascolta sulla porta 8443."
SOURCE = "Runbook di produzione: il servizio di fatturazione ascolta sulla porta 8443."
QUERY = "su quale porta ascolta il servizio di fatturazione"
VERDETTO = 88.5

#: Superfici che restituiscono fatti E portano il verdetto. Curate a mano, una
#: per volta, ed e' esattamente il motivo per cui questo file esiste.
PORTANO = {
    # Le quattro curate a mano, una per volta, prima che esistesse un contratto.
    "hippo_facts_search",
    "hippo_facts_list",
    "hippo_facts_recall",
    "hippo_trust_report",
    # Guarite insieme dal contratto unico (fact_contract.fact_payload) cablato
    # nei MODULI dietro di loro, non nei tool: 4 -> 9.
    "hippo_facts_recent",
    "hippo_facts_by_confidence",
    "hippo_fact_priority",
    "hippo_rank_facts_trust",
    "hippo_facts_export_all",
    # 9 -> 14. Ognuna con la forma che il suo canale richiede, non col payload
    # copiato ovunque: `recall_history` restituisce righe di TESTO per un
    # modello, quindi marca solo i fatti giudicati (marcare l'assenza su quasi
    # ogni riga sommergerebbe il segnale); `facts_cluster_by_topic` e' un
    # aggregato, quindi dice n_judged e la media sui soli giudicati; il
    # briefing alimenta anche la dashboard, che e' guarita di conseguenza.
    "hippo_briefing",
    "hippo_dashboard_overview",
    "hippo_facts_topics",
    "hippo_recall_history",
    "hippo_facts_cluster_by_topic",
}

#: Superfici che restituiscono fatti SENZA il verdetto. Il motivo per cui una
#: sta qui non e' «va bene»: e' «non e' ancora curata». Vanno lette come una
#: lista di lavoro, con la piu' grave in cima.
SCOPERTE = {
    "hippo_facts_topic_merge":
        "non e' una lettura: FONDE piu' proposizioni in un fatto nuovo. Il "
        "verdetto dei fatti d'origine non si eredita — un merge di cinque "
        "fatti verificati non e' verificato — e giudicare il risultato e' "
        "un'altra decisione, non un campo da propagare. Resta qui perche' il "
        "censimento lo intercetta e l'elenco deve dire perche', non tacere.",
}

CENSITE = PORTANO | set(SCOPERTE)


@pytest.fixture()
def store(tmp_path_factory) -> tuple[object, str]:
    """Uno store con UN fatto, verdetto scritto a mano.

    Il punteggio non passa dal giudice: su una macchina senza il modello CE il
    test misurerebbe la presenza del giudice invece della propagazione del
    verdetto, e confondere le due cose e' il difetto che qui si vuole trovare.

    NIENTE `scope="module"`, ed e' la riga che teneva rossa la CI dal 30/07
    (15 errori, `LocalEntryNotFoundError`, su tutte e sei le piattaforme).
    Lo stub di embedding del conftest e' `autouse` ma **function**-scoped, e
    pytest istanzia le fixture a scope piu' largo PRIMA: quando questa girava
    `_stub_embedding_model` non era ancora attivo, quindi `m.add()` caricava il
    modello VERO — che in CI non c'e'. In locale invisibile, perche' qui il
    modello e' in cache: la stessa forma del marker `xdist_group` che mancava
    e di ogni altro caso in cui il presidio non copre il percorso.

    Il costo dello scope stretto e' ricostruire lo store per ciascuna
    parametrizzazione; con lo stub attivo e' una scrittura in memoria, e
    l'isolamento fra i casi si guadagna invece di perderlo.
    """
    d = Path(tempfile.mkdtemp(prefix="censimento_", dir=tmp_path_factory.mktemp("c")))
    from verimem.client import Memory
    m = Memory(path=d / "semantic" / "semantic.db")
    rec = m.add(FATTO, topic="censimento/prova", source=SOURCE)
    fid = rec.get("id") if isinstance(rec, dict) else getattr(rec, "id", "")
    con = sqlite3.connect(str(m.semantic.db_path))
    con.execute("UPDATE facts SET grounding_score = ?", (VERDETTO,))
    con.commit()
    con.close()
    return m.semantic, fid


def _chiama(sm, nome: str, args: dict) -> str:
    from mcp.types import CallToolRequest, CallToolRequestParams

    from verimem import mcp_server

    class _A:
        def __init__(s):
            s.semantic = sm
    # `MonkeyPatch.context()` e non un'assegnazione: questa e' una helper e non
    # riceve la fixture, ma `_ag` e' una funzione di MODULO — sostituirla senza
    # ripristino la lascia sostituita per tutta la sessione pytest, e ogni test
    # successivo che passa dal server MCP riceve questo doppio (5 rossi in una
    # suite intera, misurati il 2026-07-30, in test che non avevano nulla che
    # non andasse).
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(mcp_server, "_ag", lambda: _A())
        h = mcp_server.server.request_handlers[CallToolRequest]
        res = asyncio.run(h(CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name=nome, arguments=args))))
    payload = res.root if hasattr(res, "root") else res
    return "".join(c.text for c in payload.content if hasattr(c, "text"))


#: Frammento distintivo della proposizione. E' IL criterio: «la risposta
#: contiene il contenuto del fatto». Cercare l'id sbagliava in due direzioni —
#: intercettava justified_audit, che restituisce solo una lista di
#: identificativi e a cui il verdetto per-fatto non si chiede, e mancava
#: recall_history, che stampa la proposizione senza l'id.
MARCA = "8443"


def _args(nome: str) -> dict:
    a: dict = {}
    if nome in ("hippo_facts_search", "hippo_facts_recall",
                "hippo_trust_report", "hippo_briefing",
                "hippo_recall_history"):
        a["query"] = QUERY
    if nome == "hippo_facts_topic_merge":
        a["topic"] = "censimento/prova"
    return a


@pytest.mark.parametrize("nome", sorted(PORTANO))
def test_le_superfici_curate_portano_il_verdetto(nome: str, store):
    sm, _fid = store
    testo = _chiama(sm, nome, _args(nome))
    assert MARCA in testo, (
        f"{nome} non restituisce piu' il contenuto del fatto: il censimento "
        f"non lo copre piu', ricontrollalo")
    assert "grounding_score" in testo or str(VERDETTO) in testo, (
        f"REGRESSIONE: {nome} restituisce il fatto senza il verdetto.\n"
        f"{testo[:400]}")


def test_le_scoperte_sono_ancora_quelle_dichiarate(store):
    """Il debito non cresce e non marcisce.

    Fallisce in due direzioni: se una superficie scoperta viene curata va
    spostata in PORTANO, e se ne compare una nuova va classificata. Un elenco
    che si aggiorna solo quando peggiora e' un elenco che non presidia niente.
    """
    sm, _fid = store
    guarite, sparite = [], []
    for nome in sorted(SCOPERTE):
        try:
            testo = _chiama(sm, nome, _args(nome))
        except Exception as exc:  # noqa: BLE001
            sparite.append(f"{nome}: {type(exc).__name__}")
            continue
        if MARCA not in testo:
            sparite.append(f"{nome}: non restituisce piu' il fatto")
        elif "grounding_score" in testo or str(VERDETTO) in testo:
            guarite.append(nome)
    assert not guarite, (
        f"queste sono state curate: spostale da SCOPERTE a PORTANO — {guarite}")
    assert not sparite, (
        f"queste non si comportano piu' come censite, ricontrolla — {sparite}")


@pytest.mark.slow
def test_nessuna_superficie_sfugge_al_censimento(store):
    """Il gate vero: chiama TUTTI i tool e non ne lascia scoprire uno nuovo.

    Lento (~5 min, chiama l'intero server), quindi marcato slow. E' quello che
    rende questo file diverso da una lista scritta a mano: un tool nuovo che
    restituisce fatti senza verdetto qui fallisce da solo, senza che nessuno si
    ricordi di aggiungerlo.
    """
    from verimem import mcp_server
    tools = asyncio.run(mcp_server._list_tools_unfiltered())
    sm, _fid = store
    noti = {"query": QUERY, "q": QUERY, "text": QUERY, "question": QUERY,
            "limit": 5, "k": 5, "top_k": 5, "n": 5, "max_results": 5,
            "topic": "censimento/prova", "hours": 24, "days": 7}
    scoperte_nuove, non_censiti = [], 0
    for tool in tools:
        schema = getattr(tool, "inputSchema", None) or {}
        req = set(schema.get("required") or [])
        if req - set(noti):
            non_censiti += 1
            continue
        args = {k: noti[k] for k in req}
        for k in ("query", "limit", "k", "topic"):
            if k in (schema.get("properties") or {}) and k not in args:
                args[k] = noti[k]
        try:
            testo = _chiama(sm, tool.name, args)
        except Exception:  # noqa: BLE001
            non_censiti += 1
            continue
        if MARCA not in testo:
            continue
        if "grounding_score" in testo or str(VERDETTO) in testo:
            continue
        if tool.name not in CENSITE:
            scoperte_nuove.append(tool.name)
    assert not scoperte_nuove, (
        f"superfici che restituiscono fatti senza verdetto e non dichiarate: "
        f"{scoperte_nuove}\nclassificale in PORTANO o SCOPERTE.")
    # `non_censiti` NON e' un ok: sono tool che non ho saputo chiamare. Il
    # numero resta stampato perche' un censimento che tace su cosa non ha
    # misurato e' il difetto che questo file esiste per trovare.
    print(f"\nnon censiti (argomenti sconosciuti o errore): {non_censiti}"
          f" su {len(tools)}")
