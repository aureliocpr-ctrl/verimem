r"""Sulla porta MCP il consiglio della ricevuta e' INESEGUIBILE, non incompleto.

TERZA FIRMA, chiesta da @ws2 sulla cella `W5-2`: «*serve una terza firma che
passi un `provenance_trusted` a `hippo_remember` e guardi se viene ignorato in
silenzio o rifiutato — la differenza fra le due conta, perche' un argomento
ignorato in silenzio e' peggio*». La sua firma era **statica** (`git grep`);
questa chiama il **dispatcher vero** del server (`_call_tool_impl`).
Chiude anche un limite che avevo dichiarato io: «*su MCP l'ho LETTO nel
commento, non misurato*».

    claim VERO 'La merce e' arrivata integra', porta MCP:
    A  niente (riferimento)                 status=quarantined
    B  writer_role='external_content'       RIFIUTATO - schema violation: not one of
                                            ['agent_inference','user','system_hook','trusted_hook']
    C  writer_role='user' (valore AMMESSO)  status=quarantined
    D  provenance_trusted=True da solo      status=quarantined   -> IGNORATO IN SILENZIO
    E  argomento INVENTATO (controllo)      status=quarantined   -> anche gli sconosciuti passano muti

⇒ **La risposta e' ENTRAMBE, su argomenti diversi**: il primo prerequisito e'
**rifiutato** (rumoroso, e va bene), il secondo e' **ignorato in silenzio** - la
parte che @ws2 temeva. Il **controllo E** dimostra che non e' specifico:
qualunque argomento sconosciuto passa muto, quindi non e' «`provenance_trusted`
e' stato scartato», e' «la porta non valida gli extra».

⇒ **E il reperto si rafforza oltre la firma statica**: non e' solo che l'altra
meta' non e' esprimibile - **la meta' che c'e' viene RIFIUTATA dallo schema**.
La ricevuta, sulla porta MCP, consiglia di impostare un valore che **quella
stessa porta non ammette**. Il consiglio non e' incompleto: e' **ineseguibile**,
e lo si scopre solo provandolo.
⇒ ⚠️ **Il claim vero cade in tutti e cinque i casi**: su MCP non c'e' modo di
farlo passare. La cella `W5-2`, ristretta in favore del prodotto per la porta
SDK, **sulla porta MCP resta rossa piena**.

📌 UN DATO IN PIU', che non cercavo: la porta risponde **`"ok": true`** su un
fatto con **`status=quarantined`**. Chi legge la ricevuta programmaticamente e
si ferma a `ok` **non sa di aver perso il fatto**.
📌 E la porta e' BUONA su un altro fronte: passando `content` invece di
`proposition` risponde «*these keys were not recognised and were IGNORED:
['content']. The text goes in `proposition`*» - diagnostica esemplare. **Lo
stesso server che elenca le chiavi ignorate su una chiamata, tace sulle altre.**

REGIME: build corrente · store TEMPORANEO rimosso da un `trap` · chiamata
IN-PROCESS a `_call_tool_impl`, non un client MCP su stdio.
⚖️ PUNTI DEBOLI: un solo claim, cinque varianti. Non ho verificato se un client
MCP reale riceva lo stesso errore, ne' se lo schema sia diverso su altre porte.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-sulla-porta-mcp-l-advice-e-ineseguibile.py <dir-temp>
"""
import asyncio, os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem import mcp_server as M

CLAIM = "La merce e' arrivata integra."
FONTE = "La merce e' stata spedita il 12 aprile ed e' arrivata integra."

async def chiama(et, args):
    try:
        out = await M._call_tool_impl("hippo_remember", args)
        txt = " ".join(getattr(o, "text", str(o)) for o in out)[:600].replace("\n", " ")
        print("  %-38s OK   %s" % (et, txt))
    except Exception as e:
        print("  %-38s ERRORE %s: %s" % (et, type(e).__name__, str(e)[:150]))

async def main():
    base = {"proposition": CLAIM, "topic": "banco/terzafirma", "source": FONTE}
    await chiama("A niente (riferimento)", dict(base))
    await chiama("B writer_role='external_content' (l'advice)",
                 dict(base, writer_role="external_content"))
    await chiama("C writer_role='user' (valore AMMESSO)", dict(base, writer_role="user"))
    await chiama("D provenance_trusted=True da solo",
                 dict(base, provenance_trusted=True))
    await chiama("E argomento INVENTATO (controllo)",
                 dict(base, parametro_che_non_esiste=True))

asyncio.run(main())
