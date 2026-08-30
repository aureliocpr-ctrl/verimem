r"""C3 - la colonna che manca alla scacchiera: MCP su STDIO, senza il giudice.

🔍 **memoria**: prima di misurare ho riletto i miei tre banchi C3 e il reperto
stdio. Lo stato della scacchiera **prima** di questo banco:

    operazione                    gate   SDK   MCP in-proc   MCP stdio
    scrittura con source           ✅     ✅       ✅          🔴 non risponde (190s)
    scrittura senza source         ✅     ✅       ✅          ✅ 3.8s
    writer_role='user'             ✅     ✅       ✅          ❓ MAI MISURATA
    writer_role='external_content' ✅     ✅    🔴 rifiutato   ❓ MAI MISURATA
    supersessione                  -      ✅    🔴 non sup.    ❓ MAI MISURATA
    hippo_search / recall          -      ✅       ✅          ❓ MAI MISURATA
    hippo_facts_search             -      -        ✅          ❓ MAI MISURATA

⇒ **La colonna stdio e' quasi tutta vuota**, e non per pigrizia: la scrittura
**con** source li' non torna entro 190 secondi (`95772fc3`), quindi ogni banco
che passa dal giudice si blocca.

🔑 **L'IDEA CHE SBLOCCA LA COLONNA**: la scrittura **senza** source risponde in
3.8 secondi, perche' **non chiama il giudice**. ⇒ Tutte le operazioni che non
hanno bisogno del grounding sono misurabili su stdio **adesso**, e sono
esattamente quelle su cui le due porte MCP potrebbero divergere: la
**validazione dello schema**, la **supersessione**, le **letture**.

⚠️ **LA CELLA CHE VALE PIU' DELLE ALTRE**: `writer_role='external_content'`.
In-process e' **rifiutato dallo schema** («*not one of [agent_inference, user,
system_hook, trusted_hook]*»), ed e' un reperto che ho consegnato e che sta nel
report. **Ma la validazione in-process e quella di un client vero possono
stare in punti diversi del percorso.** Se su stdio passasse, il mio reperto
sarebbe vero solo per la porta che nessun utente usa.

⚠️ **POPOLAZIONE DI CONTROLLO**: la scrittura semplice senza source, che ho gia'
misurato **identica** sulle due vie (3.7s contro 3.8s, stesso esito). Se qui
divergesse, la differenza non sarebbe l'operazione: sarebbe il banco.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) condiviso dalle due
vie · server stdio come processo figlio, chiuso dal context manager ·
**nessuna operazione passa dal giudice**, per costruzione.
⚖️ PUNTI DEBOLI: client ufficiale del pacchetto `mcp`, non Claude Code o Cursor;
un caso per operazione; le letture girano su uno store con **pochi** fatti e
**zero** episodi, quindi un `[]` va letto come «cerca altro», non come «e'
rotta» - il confronto qui e' **fra le due porte**, non contro un atteso.

✅ ESITO - **8 operazioni su 8 IDENTICHE. Le due porte MCP divergono in UN
punto solo, ed e' il giudice**::

    operazione                       MCP in-process         MCP su STDIO
    CONTROLLO scrittura nuda         model_claim sup=False  model_claim sup=False  ✔
    writer_role='user'               model_claim sup=False  model_claim sup=False  ✔
    writer_role='external_content'   RIFIUTATO              RIFIUTATO              ✔
    supersessione 1a                 model_claim sup=False  model_claim sup=False  ✔
    supersessione 2a                 model_claim sup=False  model_claim sup=False  ✔
    lettura hippo_search             lista=0                lista=0                ✔
    lettura hippo_recall             lista=0                lista=0                ✔
    lettura hippo_facts_search       items=8                items=8                ✔

🔑 **LA CELLA CHE VALEVA PIU' DELLE ALTRE RISPONDE, E A MIO SFAVORE NON LO E'**:
`writer_role='external_content'` e' **RIFIUTATO su ENTRAMBE**. ⇒ Il reperto che
ho consegnato e che sta nel report - «*su MCP il valore che la ricevuta consiglia
e' rifiutato dallo schema*» - **non era un artefatto della porta in-process**:
un client vero, con framing JSON-RPC e processo separato, lo rifiuta uguale.

📌 **VALIDA RETROATTIVAMENTE TRE MIEI BANCHI.** In `37bc7a9a`, `c90143cb` e
`2ed804bd` avevo scritto lo stesso limite - «*MCP in-process, non un client su
stdio: se qualcuna ha stdio, la sua misura batte questa*». **Adesso quella misura
c'e' ed e' la mia**: su tutto cio' che non passa dal giudice, in-process **e'**
la porta vera. Il limite non va piu' letto come un dubbio su quei referti.

🔑 **E RESTRINGE IL REPERTO STDIO A UN PUNTO SOLO.** Da `95772fc3` sapevo che una
scrittura **con** source non torna entro 190s mentre **senza** source risponde in
3.8s. Ora si aggiunge che **tutto il resto e' identico**: protocollo, validazione
dello schema, supersessione, tre vie di lettura. ⇒ **La disparita' fra le due
porte MCP non e' nel trasporto ne' nella validazione: e' interamente nel percorso
del grounding.** E' una frase molto piu' stretta di «le porte divergono», ed e'
quella che regge.

📌 Conferma anche, da una terza direzione, che **MCP non supersede** (`sup=False`
alla seconda scrittura su entrambe le vie): concorda con `37bc7a9a` e con la
riproduzione indipendente di `W2-2`.

REGIME: build corrente · store TEMPORANEO condiviso dalle due vie · server stdio
come processo figlio · **nessuna operazione passa dal giudice**, per costruzione.
⚖️ PUNTI DEBOLI: client ufficiale del pacchetto `mcp`, non Claude Code o Cursor;
un caso per operazione; le letture girano su uno store con pochi fatti e **zero
episodi**, quindi `lista=0` va letto come «cerca altro» - qui il confronto e'
**fra le due porte**, non contro un atteso.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C3-la-colonna-stdio-della-scacchiera.py <dir-temp>
"""
import asyncio
import json
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
TEMP = sys.argv[1]
os.environ["HIPPO_DATA_DIR"] = TEMP

CLAIM = "Il canone mensile dell'immobile di via Roma e' di 1200 euro."
AGGIORNA = "Il canone mensile dell'immobile di via Roma e' di 1300 euro."
QUERY = "canone mensile immobile via Roma"

#: (etichetta, tool, argomenti) — nessuna porta il campo `source`, per non
#: chiamare il giudice: e' la condizione che rende la colonna stdio misurabile.
OPERAZIONI = [
    ("CONTROLLO scrittura nuda", "hippo_remember",
     {"proposition": CLAIM, "topic": "c3col/a"}),
    ("writer_role='user'", "hippo_remember",
     {"proposition": CLAIM, "topic": "c3col/b", "writer_role": "user"}),
    ("writer_role='external_content'", "hippo_remember",
     {"proposition": CLAIM, "topic": "c3col/c", "writer_role": "external_content"}),
    ("supersessione 1a", "hippo_remember",
     {"proposition": CLAIM, "topic": "c3col/sup"}),
    ("supersessione 2a", "hippo_remember",
     {"proposition": AGGIORNA, "topic": "c3col/sup"}),
    ("lettura hippo_search", "hippo_search", {"query": QUERY}),
    ("lettura hippo_recall", "hippo_recall", {"query": QUERY}),
    ("lettura hippo_facts_search", "hippo_facts_search", {"query": QUERY}),
]

ATTESA = 60   #: nessuna di queste chiama il giudice: se supera, e' un difetto


def _riduci(txt, errore=False):
    """riduce una risposta a un esito confrontabile fra le due vie"""
    if errore:
        return "RIFIUTATO"
    try:
        d = json.loads(txt)
    except Exception:
        return "non-JSON"
    if isinstance(d, dict) and "error" in d:
        return "RIFIUTATO"
    if isinstance(d, dict):
        if "status" in d:
            return "%s sup=%s" % (d.get("status"), bool(d.get("replaced")))
        for k in ("results", "facts", "episodes", "items", "matches"):
            if isinstance(d.get(k), list):
                return "%s=%d" % (k, len(d[k]))
    if isinstance(d, list):
        return "lista=%d" % len(d)
    return str(d)[:26]


async def via_in_process(tool, args):
    from verimem import mcp_server as M
    try:
        out = await M._call_tool_impl(tool, dict(args))
    except Exception as e:  # noqa: BLE001 - il banco deve dire COSA e' successo
        return "ECCEZIONE:" + type(e).__name__
    return _riduci(" ".join(getattr(o, "text", str(o)) for o in out))


async def via_stdio(ses, tool, args):
    try:
        res = await asyncio.wait_for(ses.call_tool(tool, dict(args)), timeout=ATTESA)
    except asyncio.TimeoutError:
        return "NESSUNA RISPOSTA"
    except Exception as e:  # noqa: BLE001
        return "ECCEZIONE:" + type(e).__name__
    txt = " ".join(getattr(c, "text", str(c)) for c in (res.content or []))
    return _riduci(txt, errore=bool(getattr(res, "isError", False)))


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = TEMP
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    params = StdioServerParameters(command=sys.executable,
                                   args=["-m", "verimem.mcp_server"], env=env)

    print("  %-32s %-24s %-24s %s"
          % ("operazione", "MCP in-process", "MCP su STDIO", "verdetto"))
    print("  " + "-" * 98)
    righe = []
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as ses:
            await asyncio.wait_for(ses.initialize(), timeout=120)
            for nome, tool, args in OPERAZIONI:
                a = await via_in_process(tool, dict(args, topic=args.get("topic", "") + "-ip")
                                         if "topic" in args else args)
                b = await via_stdio(ses, tool, dict(args, topic=args.get("topic", "") + "-st")
                                    if "topic" in args else args)
                uguale = (a == b)
                righe.append((nome, uguale, a, b))
                print("  %-32s %-24s %-24s %s"
                      % (nome[:32], a[:24], b[:24],
                         "✔ UGUALI" if uguale else "🔴 DIVERSI"))

    print("\n=== SINTESI ===")
    ug = sum(1 for _n, u, _a, _b in righe if u)
    print("  operazioni confrontate   %d" % len(righe))
    print("  ✔ stesso esito           %d" % ug)
    print("  🔴 esito DIVERSO         %d" % (len(righe) - ug))
    for n, u, a, b in righe:
        if not u:
            print("      %-32s in-proc=%-18s stdio=%s" % (n, a, b))
    ctrl = [u for n, u, _a, _b in righe if n.startswith("CONTROLLO")]
    print("\n  controllo concorde: %s" % ("SI" if all(ctrl) else "NO - il banco non e' leggibile"))
    print("  ⚠️ Nessuna operazione passa dal giudice: se una supera %ds, e' un" % ATTESA)
    print("     difetto suo, non il costo del grounding.")


asyncio.run(main())
