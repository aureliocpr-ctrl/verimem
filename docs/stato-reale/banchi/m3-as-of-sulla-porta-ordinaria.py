"""M3 — `hippo_facts_recall` accetta `as_of` e lo IGNORA, o lo rifiuta?

    python docs/stato-reale/banchi/m3-as-of-sulla-porta-ordinaria.py

`as_of` sulla porta MCP esiste solo come TOOL SEPARATO (`hippo_recall_as_of`,
chiave `when`). La porta ordinaria del recall dei fatti non lo dichiara nello
schema. Ma dentro `_call_tool_impl` il thin tier lo elenca fra i filtri che
BLOCCANO la delega al server remoto:

    any(arguments.get(_s) is not None for _s in
        ("user_id", "agent_id", "run_id", "topic", "as_of", "min_status"))

cioè quel ramo **assume che `as_of` possa arrivare qui**. Le due cose non
stanno insieme, e la differenza per chi usa il prodotto è tutta:

    RIFIUTATO  -> il chiamante impara che deve usare l'altro tool. Onesto.
    IGNORATO   -> il chiamante crede di aver chiesto il passato e riceve il
                  PRESENTE, senza un segno che glielo dica. È la classe di
                  `asserted_at` su `hippo_remember` («ACCEPTED WITHOUT ERROR
                  AND IGNORED»), e in lettura è peggio che in scrittura:
                  una risposta sbagliata sembra una risposta.

═══════════════════════════════════════════════════════════════════════════
LA PREDIZIONE, DEPOSITATA QUI PRIMA DI ESEGUIRE (ws2, 03/09 ore 21:30)
═══════════════════════════════════════════════════════════════════════════

**Predico ACCETTATO E IGNORATO.** La ragione: `_drop_none_args` toglie i
`null`, non i numeri; la validazione dello schema è descritta nel codice come
«lenient type/enum schemas auto-derived» — controlla i tipi dei campi noti, non
vieta i campi ignoti; e l'handler legge `arguments.get(...)` solo per le chiavi
che conosce. Quindi `as_of` attraverserebbe tutto senza toccare niente.

**Mi falsifica**: un errore esplicito («input validation failed»), oppure una
risposta che cambia davvero quando cambia `as_of`.

⚠️ Le mie ultime due predizioni sono cadute, entrambe pessimistiche sul
prodotto. Se cade anche questa, non è un caso: è una taratura mia da correggere.

═══════════════════════════════════════════════════════════════════════════
SECONDA PREDIZIONE, DEPOSITATA IL 04/09 ore 18:52 — LA PORTA GEMELLA
═══════════════════════════════════════════════════════════════════════════

Il thin tier elenca `as_of` fra i filtri che bloccano la delega per DUE tool:
`hippo_facts_recall` **e** `hippo_facts_search`. Il secondo non lo dichiara
nello schema (campi: query, limit, topic, user_id, agent_id, run_id,
include_shared) — misurato leggendo il sorgente, non dedotto.

**Predico che anche `hippo_facts_search` accetti `as_of` e lo ignori**, per la
stessa ragione: la validazione è lenient sui campi ignoti e l'handler legge
solo le chiavi che conosce.

**Perché conta per il voto in corso:** se il difetto è su DUE porte, l'opzione
(B) «rifiutarlo» va scritta due volte e (A) «esporlo» diventa più conveniente.
Se invece la porta gemella lo rifiuta già, allora (B) è la strada che rende il
prodotto COERENTE con se stesso, e la mia preferenza per (A) va rivista.
⇒ **Questa misura può ribaltare il mio stesso voto, ed è per questo che la
faccio prima di implementare.**
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

_D = tempfile.mkdtemp(prefix="m3aop_")
os.environ["HIPPO_DATA_DIR"] = _D          # PRIMA dell'import: è tutto il punto
os.environ.pop("ENGRAM_DATA_DIR", None)

#: ⚠️ `python docs/.../questo.py` mette in `sys.path[0]` la directory DELLO
#: SCRIPT: in un `git worktree` `import verimem` prenderebbe l'albero
#: installato, cioè quello di qualcun altro.
_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import asyncio  # noqa: E402
import json  # noqa: E402

import verimem  # noqa: E402
from verimem import mcp_server  # noqa: E402

_QUALE = pathlib.Path(verimem.__file__).resolve()
#: REGOLA A-5 del 04/09: il banco DICHIARA in testa quale albero sta misurando.
#: Non basta il guardiano qui sotto — chi legge l'output deve poterlo vedere
#: senza rileggere il sorgente.
print(f"  verimem misurato: {_QUALE}")
if _ROOT not in _QUALE.parents:
    raise SystemExit(
        f"⛔ sto per misurare {_QUALE}\n"
        f"   invece del repo {_ROOT}: il verdetto non direbbe niente.")

VECCHIO = "Il prezzo di listino del modello Y è 900 euro."
NUOVO = "Il prezzo di listino del modello Y è 1100 euro."
QUERY = "qual è il prezzo di listino del modello Y"


async def chiama(nome: str, args: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    res = await mcp_server.server.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call",
                        params=CallToolRequestParams(name=nome, arguments=args)))
    p = res.root if hasattr(res, "root") else res
    t = next(c.text for c in p.content if hasattr(c, "text"))
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {"raw": t}


def ids_dei_risultati(risposta: dict) -> set:
    """Gli id dei fatti RESTITUITI, non ogni id che compare nella risposta.

    ⚠️ La ricerca per sottostringa mente: il record porta `superseded_by`,
    cioè l'id del SOSTITUTO. Un banco gemello ha accusato il prodotto per
    questo il 03/09 alle 20:52.
    """
    out = set()
    for r in (risposta.get("facts") or risposta.get("items") or []):
        v = r.get("id") if isinstance(r, dict) else None
        if v:
            out.add(v)
    return out


def main() -> int:
    ag = mcp_server._ag()
    assert "m3aop_" in str(ag.semantic.db_path), "non è la dir temporanea"

    prima_di_tutto = time.time() - 86400        # ieri: qui non c'era NIENTE
    a = asyncio.run(chiama("hippo_remember", {
        "proposition": VECCHIO, "topic": "banco/m3aop",
        "source": "Listino: modello Y, 900 euro."}))
    b = asyncio.run(chiama("hippo_remember", {
        "proposition": NUOVO, "topic": "banco/m3aop",
        "source": "Listino rev.2: modello Y, 1100 euro."}))
    vid, nid = a.get("id"), b.get("id")
    ag.semantic.supersede(vid, nid, principal="banco:m3aop", reason="listino rev.2")
    print(f"  scritti: vecchio {vid} · nuovo {nid} (ritira il primo)")

    senza = asyncio.run(chiama("hippo_facts_recall", {"query": QUERY, "k": 5}))
    con = asyncio.run(chiama("hippo_facts_recall",
                             {"query": QUERY, "k": 5, "as_of": prima_di_tutto}))
    # e la porta che il passato lo sa fare davvero, per confronto
    vero = asyncio.run(chiama("hippo_recall_as_of",
                              {"query": QUERY, "when": prima_di_tutto, "k": 5}))

    # LA PORTA GEMELLA: hippo_facts_search usa `limit`, non `k`
    s_senza = asyncio.run(chiama("hippo_facts_search", {"query": QUERY, "limit": 5}))
    s_con = asyncio.run(chiama("hippo_facts_search",
                               {"query": QUERY, "limit": 5, "as_of": prima_di_tutto}))

    id_senza, id_con, id_vero = (ids_dei_risultati(x) for x in (senza, con, vero))
    rifiutato = "validation failed" in json.dumps(con, ensure_ascii=False).lower()

    #: ⚠️ «SENZA UN CAMPO CHE LO DICHIARI» E' UN'AFFERMAZIONE, e va MISURATA:
    #: se la risposta portasse un avviso, il difetto sarebbe molto minore —
    #: un filtro non applicato ma DICHIARATO lascia al chiamante il modo di
    #: accorgersene. Quindi si stampano le chiavi, invece di dire che non
    #: c'e' nulla.
    _kc, _ks = set(con.keys()), set(senza.keys())
    print()
    print(f"  chiavi della risposta CON as_of : {sorted(_kc)}")
    print(f"  chiavi in piu' rispetto a senza : {sorted(_kc - _ks) or 'NESSUNA'}")
    _avvisi = [k for k in _kc if any(t in k.lower() for t in
               ("warn", "ignor", "unsupport", "as_of", "asof", "notice", "degrad"))]
    print(f"  chiavi che potrebbero avvisare  : {_avvisi or 'NESSUNA'}")
    id_s_senza, id_s_con = ids_dei_risultati(s_senza), ids_dei_risultati(s_con)
    s_rifiutato = "validation failed" in json.dumps(s_con, ensure_ascii=False).lower()
    print()
    print("  LA PORTA GEMELLA — hippo_facts_search")
    print(f"     risultati senza as_of  : {len(id_s_senza)}")
    print(f"     risultati CON as_of=ieri: {len(id_s_con)}  (rifiutato? {s_rifiutato})")
    print(f"     stessi id con e senza?  : {id_s_con == id_s_senza and bool(id_s_senza)}")
    print()
    print("  CONTROLLO POSITIVO — senza as_of la porta risponde? ", bool(id_senza))
    print(f"     risultati senza as_of : {len(id_senza)}")
    print(f"     risultati CON as_of=ieri: {len(id_con)}  (rifiutato? {rifiutato})")
    print(f"     il tool DEDICATO, stesso istante: {len(id_vero)}")
    print()

    if not id_senza:
        print("  ⛔ CONTROLLO POSITIVO SPENTO: la porta non risponde nemmeno")
        print("     senza il filtro. Nulla qui dice niente.")
        return 1
    if id_vero:
        print("  ⛔ il tool DEDICATO restituisce fatti a un istante in cui non")
        print("     esistevano: il banco non ha un riferimento buono. Indecidibile.")
        return 1
    if rifiutato:
        print("  🟢 LA MIA PREDIZIONE È FALSIFICATA: la porta RIFIUTA `as_of`")
        print("     invece di ignorarlo. Chi lo passa impara che deve usare")
        print("     `hippo_recall_as_of`, e nessuno riceve il presente credendo")
        print("     di aver chiesto il passato.")
        return 0
    if id_con == id_senza:
        print("  🔴 PREDIZIONE CONFERMATA — ACCETTATO E IGNORATO.")
        print("     La porta restituisce gli STESSI fatti con e senza `as_of`,")
        print("     senza errore e senza un campo che dichiari il filtro non")
        print("     applicato. Il tool dedicato, allo stesso istante, ne")
        print("     restituisce 0: la risposta giusta era «niente».")
        print("     ⇒ chi chiede il passato da questa porta riceve il PRESENTE.")
        return 1
    print("  🟡 la risposta cambia con `as_of` ma non coincide col tool")
    print(f"     dedicato: senza={sorted(id_senza)} con={sorted(id_con)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
