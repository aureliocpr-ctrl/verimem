r"""C3 - la LETTURA: quattro vie, una domanda sola. Cosa risponde ciascuna?

Secondo pezzo di C3 («parita' porte», claim `f7eca18c246f`). Il primo pezzo
(`ws5-C3-le-stesse-operazioni-sulle-due-porte.py`) ha misurato le SCRITTURE:
4 operazioni su 6 uguali, il gate di base **coerente**.
Qui le **letture**, che @ws8 indica come il candidato piu' grosso: «*`recall` ha
DUE SIGNIFICATI OPPOSTI - nell'SDK cerca i FATTI, su MCP gli EPISODI*».

**Il lato SDK e' gia' confermato leggendo il codice**: `client.py:3125` dice
`recall = search` - non un metodo che somiglia, **lo stesso oggetto**
(`Client.recall is Client.search` -> True).

LE QUATTRO VIE, sulla **stessa domanda** e lo **stesso corpus temporaneo**:
    SDK  `search` (== `recall`)
    MCP  `hippo_search`
    MCP  `hippo_recall`
    MCP  `hippo_facts_search`

⚠️ **POPOLAZIONE DI CONTROLLO**: scrivo un fatto e poi lo cerco con **le sue
stesse parole**. Una via che non lo trova non e' «configurata diversamente»:
non risponde alla domanda. E' il controllo che distingue «due nomi per due cose»
da «una delle due e' rotta».

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
MCP in-process via `_call_tool_impl`, **non** stdio.
⚖️ PUNTI DEBOLI: un fatto e una query; conto i **risultati** e guardo se il
fatto scritto c'e', non valuto il ranking; e un corpus appena creato non ha
episodi, quindi una via che cerca **episodi** trovera' zero **per costruzione** -
e va letto come «cerca altro», non come «e' rotta».

ESITO - **2 vie su 4 trovano il fatto appena scritto**, e la forma dell'assenza
e' il reperto::

    via di lettura              risultati   trova?   risposta grezza
    SDK  search (== recall)     1           SI
    MCP  hippo_search           -           no       **`[]`**
    MCP  hippo_recall           -           no       **`[]`**
    MCP  hippo_facts_search     1           SI       chiave `items`, col fatto dentro

🔑 **NON E' UN ERRORE: E' UNA LISTA VUOTA IN SILENZIO.** `hippo_search` e
`hippo_recall` cercano **episodi** - che in uno store appena creato non
esistono - e rispondono `[]` **senza dire niente**: nessun errore, nessun
avviso, nessun «*qui non ci sono episodi: i fatti si cercano con
`hippo_facts_search`*».
⇒ **Il danno non e' «`recall` e' rotto»**: e' che un agente che chiama
`hippo_recall` per cercare un fatto riceve `[]` e conclude **«la memoria non lo
sa»**, mentre il fatto **c'e'** ed e' raggiungibile con un altro tool. Lo stesso
nome, sulle due porte, risponde a **due domande diverse** e la piu' povera non
lo dichiara.
📌 Conferma end-to-end il reperto di @ws8 («*`recall` ha due significati
opposti*»), che sul lato SDK e' gia' leggibile nel codice: `client.py:3125`
dice `recall = search` - **lo stesso oggetto**, non un metodo che somiglia.
📌 **Stessa classe** del mio reperto sulla ricevuta MCP che risponde `ok: true`
su uno `status=quarantined`: il prodotto dice qualcosa di **formalmente
corretto** che il chiamante legge come **un'altra cosa**. E della lezione in
memoria «*una misura che non c'e' si legge come una misura perfetta*»: qui
**una lista vuota si legge come «non esiste»**.

⚖️ E IL LIMITE CHE TIENE ONESTO IL REFERTO: uno store appena creato **non ha
episodi**, quindi quelle due vie tornano `[]` **per costruzione**. Non ho
misurato cosa fanno su un corpus **con** episodi - li' potrebbero rispondere
benissimo. ⇒ Il difetto che affermo non e' «non trovano»: e' **«non dicono che
stanno cercando altro»**, e quello vale a corpus vuoto come a corpus pieno.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C3-la-lettura-quattro-vie-una-domanda.py <dir-temp>
"""
import asyncio
import json
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem import Client  # noqa: E402
from verimem import mcp_server as M  # noqa: E402

FATTO = "Il canone mensile dell'immobile di via Roma e' di 1200 euro."
FONTE = "Il conduttore corrisponde per l'immobile di via Roma un canone mensile di 1200 euro."
QUERY = "canone mensile immobile via Roma"


def _trova(testo, atteso="via Roma"):
    """il fatto scritto compare nella risposta?"""
    return atteso.lower() in (testo or "").lower()


async def _mcp_tool(nome, args):
    try:
        out = await M._call_tool_impl(nome, args)
        return " ".join(getattr(o, "text", str(o)) for o in out)
    except Exception as e:  # noqa: BLE001 - il banco deve dire COSA e' successo
        return "ERRORE %s: %s" % (type(e).__name__, str(e)[:80])


async def main():
    c = Client()
    r = c.add(FATTO, topic="c3/lettura", source=FONTE)
    fid = (r if isinstance(r, dict) else {}).get("id")
    print("  fatto scritto: id=%s" % fid)
    print("  query: «%s»\n" % QUERY)

    print("  %-34s %-9s %-8s %s" % ("via di lettura", "risultati", "trovato", "nota"))
    print("  " + "-" * 84)
    righe = []

    # --- SDK -----------------------------------------------------------------
    try:
        res = c.search(QUERY, k=5)
        n = len(res) if hasattr(res, "__len__") else -1
        txt = str(res)
        righe.append(("SDK  search (== recall)", n, _trova(txt), ""))
    except Exception as e:  # noqa: BLE001
        righe.append(("SDK  search (== recall)", -1, False, "%s" % type(e).__name__))

    # --- MCP -----------------------------------------------------------------
    for tool, args in (("hippo_search", {"query": QUERY}),
                       ("hippo_recall", {"query": QUERY}),
                       ("hippo_facts_search", {"query": QUERY})):
        txt = await _mcp_tool(tool, args)
        nota = ""
        n = -1
        try:
            d = json.loads(txt)
            if isinstance(d, dict) and "error" in d:
                nota = "ERRORE: " + str(d["error"])[:40]
            for k in ("results", "facts", "episodes", "items", "matches"):
                if isinstance(d, dict) and isinstance(d.get(k), list):
                    n = len(d[k])
                    nota = nota or ("chiave '%s'" % k)
                    break
        except Exception:
            nota = "risposta non-JSON"
        righe.append(("MCP  " + tool, n, _trova(txt), nota))

    for nome, n, trovato, nota in righe:
        print("  %-34s %-9s %-8s %s"
              % (nome, n if n >= 0 else "?", "SI" if trovato else "no", nota))

    print("\n=== SINTESI ===")
    trovanti = [n for n, _c, t, _x in righe if t]
    print("  vie che TROVANO il fatto appena scritto: %d su %d" % (len(trovanti), len(righe)))
    for n, _c, t, _x in righe:
        if not t:
            print("      NON lo trova: %s" % n)
    print("\n  ⚠️ Una via che cerca EPISODI non trova un FATTO per costruzione:")
    print("     va letta come «cerca altro», non come «e' rotta». Il punto di C3")
    print("     e' che due nomi uguali facciano cose diverse SENZA dirlo.")


asyncio.run(main())
