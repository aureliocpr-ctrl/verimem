r"""C3 - le STESSE operazioni sulle DUE porte: cosa differisce e cosa deve restare uguale.

C3 del contratto di uscita («parita' porte»), claim `f7eca18c246f`. Nasce da tre
disparita' misurate stanotte **senza cercarle**, piu' i reperti di @ws2 (19
argomenti al gate, 13 differenti; 95 test su 98 su una porta depotenziata) e di
@ws8 («*recall* ha due significati opposti»).

⚠️ **LA POPOLAZIONE DI CONTROLLO E' META' DEL BANCO.** Una lista di differenze
senza le uguaglianze non dice se il prodotto e' **incoerente** o solo
**configurato diversamente**: per ogni operazione c'e' un esito che **deve**
essere identico sulle due porte, e se lo e' la differenza altrove pesa meno.

COME SI LEGGE:
    ✔ UGUALI   l'operazione da' lo stesso esito su SDK e MCP
    🔴 DIVERSI  esiti diversi ⇒ chi misura su una porta non sa cosa succede sull'altra

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
MCP chiamato **in-process** via `_call_tool_impl`, **non** un client su stdio.
⚖️ PUNTI DEBOLI: (1) la porta MCP in-process potrebbe comportarsi diversamente
da un client vero - se qualcuna ha stdio, la sua misura batte questa; (2) un
solo caso per operazione; (3) confronto lo **stato finale** (status, superseded),
non tutti i campi della ricevuta.

ESITO - **4 operazioni su 6 danno lo STESSO esito**, e la popolazione di
controllo REGGE::

    operazione                        SDK                    MCP                  verdetto
    CONTROLLO claim VERO con source   model_claim g=98.5     model_claim g=98.5   ✔ UGUALI
    CONTROLLO claim FALSO (inventata) quarantined g=0.7      quarantined g=0.7    ✔ UGUALI
    scrittura SENZA source            model_claim g=None     model_claim g=None   ✔ UGUALI
    writer_role='user'                model_claim g=98.5     model_claim g=98.5   ✔ UGUALI
    writer_role='external_content'    model_claim g=98.5     **RIFIUTATO**        🔴 DIVERSI
    supersessione (2a scrittura)      sup=**True**           sup=**False**        🔴 DIVERSI

🟢 **IL CONTROLLO E' LA NOTIZIA PRINCIPALE**: il claim vero passa identico
(98.5 su entrambe) e il falso e' quarantinato identico (0.7 su entrambe). ⇒ **Il
gate di base e' COERENTE fra le porte.** Le porte non sono «due prodotti
diversi»: divergono su **due comportamenti specifici**, e questo e' molto meno
grave di un'incoerenza di fondo. Senza il controllo, le due righe rosse
sembrerebbero la punta di un iceberg che non c'e'.

🔴 **LE DUE DIFFERENZE**:
① `writer_role='external_content'` - **il valore che la RICEVUTA consiglia** - e'
   accettato dall'SDK e **rifiutato dallo schema MCP** («*not one of
   [agent_inference, user, system_hook, trusted_hook]*»). Gia' mio, ora nel
   confronto diretto.
② **La supersessione**: la seconda scrittura sullo stesso topic **supersede su
   SDK e NON su MCP**. ⇒ **Riproduzione indipendente di `W2-2` di @ws2** («*la
   porta MCP non supersede perche' non le arriva `validate='full'`*»): lei
   l'ha isolata con un A/B a un fattore, io ci arrivo da un confronto di
   operazioni senza cercarla.

🪞 **E QUI RAFFINO UN MIO REPERTO DEL 28/08.** Avevo scritto che «*lo stesso
claim VERO passa su SDK e cade su MCP, 5 varianti su 5*». **Qui il claim vero
passa su ENTRAMBE.** La differenza: quel claim era «*la merce e' arrivata
integra*», che innesca `L1.20` (collisione di dominio); questo e' «*il canone
mensile e' di 1200 euro*», che non innesca nessun `L1.x`.
⇒ **Formulazione corretta**: la porta MCP **non fa cadere i claim veri in
generale**. Li fa cadere **quando un layer `L1.x` si attiva** e il routing di
provenienza - che su MCP non arriva - avrebbe potuto salvarli. La disparita' e'
**condizionata**, non sistematica.

REGIME: SHA `6c2394c6` · store TEMPORANEO da `trap` · MCP in-process via
`_call_tool_impl`.
⚖️ PUNTI DEBOLI: sei operazioni, un caso ciascuna; MCP **non** su stdio;
confronto sullo **stato finale** (`status`, `superseded`), non su tutti i campi
della ricevuta - e i campi hanno **nomi diversi** fra le porte (`warnings` su
SDK, `anti_confab_warnings` su MCP, reperto di @ws3).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C3-le-stesse-operazioni-sulle-due-porte.py <dir-temp>
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

VERO = "Il canone mensile e' di 1200 euro."
FONTE = "Il conduttore corrisponde un canone mensile di 1200 euro."
FALSO = "Il canone mensile e' di 3400 euro."
AGGIORNA = "Il canone mensile e' di 1300 euro."
FONTE_AGG = "Il conduttore corrisponde un canone mensile di 1300 euro."


def _sdk(claim, topic, source=None, wr=None):
    c = Client()
    kw = {"topic": topic}
    if source:
        kw["source"] = source
    if wr:
        kw["writer_role"] = wr
    r = c.add(claim, **kw)
    d = r if isinstance(r, dict) else getattr(r, "__dict__", {})
    return {"status": d.get("status") or d.get("action"),
            "grounding": round(d.get("grounding_score"), 1) if d.get("grounding_score") else None,
            "superseded": bool(d.get("superseded") or d.get("replaced"))}


async def _mcp(claim, topic, source=None, wr=None):
    args = {"proposition": claim, "topic": topic}
    if source:
        args["source"] = source
    if wr:
        args["writer_role"] = wr
    out = await M._call_tool_impl("hippo_remember", args)
    txt = " ".join(getattr(o, "text", str(o)) for o in out)
    try:
        d = json.loads(txt)
    except Exception:
        return {"status": "PARSE-FAIL", "grounding": None, "superseded": None}
    if "error" in d:
        return {"status": "RIFIUTATO", "grounding": None, "superseded": None}
    return {"status": d.get("status"),
            "grounding": round(d.get("grounding_score"), 1) if d.get("grounding_score") else None,
            "superseded": bool(d.get("replaced"))}


def _fmt(d):
    return "%-12s g=%-6s sup=%s" % (d.get("status"), d.get("grounding"), d.get("superseded"))


async def main():
    print("  %-40s %-30s %-30s %s"
          % ("operazione", "SDK (Client.add)", "MCP (hippo_remember)", "verdetto"))
    print("  " + "-" * 116)
    righe = []

    # ---- POPOLAZIONE DI CONTROLLO: questi DEVONO dare lo stesso esito -------
    casi = [
        ("CONTROLLO claim VERO con source", VERO, "c3/a", FONTE, None),
        ("CONTROLLO claim FALSO (cifra inventata)", FALSO, "c3/b", FONTE, None),
        ("scrittura SENZA source", VERO, "c3/c", None, None),
        ("writer_role='user' (ammesso su MCP)", VERO, "c3/d", FONTE, "user"),
        ("writer_role='external_content' (l'advice)", VERO, "c3/e", FONTE, "external_content"),
    ]
    for nome, claim, topic, src, wr in casi:
        a = _sdk(claim, topic + "-sdk", src, wr)
        b = await _mcp(claim, topic + "-mcp", src, wr)
        uguali = (a.get("status") == b.get("status"))
        righe.append((nome, uguali))
        print("  %-40s %-30s %-30s %s"
              % (nome[:40], _fmt(a), _fmt(b), "✔ UGUALI" if uguali else "🔴 DIVERSI"))

    # ---- SUPERSESSIONE: due scritture sullo stesso topic --------------------
    _sdk(VERO, "c3/sup-sdk", FONTE)
    a = _sdk(AGGIORNA, "c3/sup-sdk", FONTE_AGG)
    await _mcp(VERO, "c3/sup-mcp", FONTE)
    b = await _mcp(AGGIORNA, "c3/sup-mcp", FONTE_AGG)
    uguali = (a.get("superseded") == b.get("superseded"))
    righe.append(("supersessione (2a scrittura stesso topic)", uguali))
    print("  %-40s %-30s %-30s %s"
          % ("supersessione (2a scrittura)", _fmt(a), _fmt(b),
             "✔ UGUALI" if uguali else "🔴 DIVERSI"))

    print("\n=== SINTESI ===")
    ug = sum(1 for _n, u in righe if u)
    print("  operazioni confrontate  %d" % len(righe))
    print("  ✔ stesso esito          %d" % ug)
    print("  🔴 esito DIVERSO        %d" % (len(righe) - ug))
    for n, u in righe:
        if not u:
            print("      DIVERSE: %s" % n)
    print("\n  ⚠️ Le prime due righe sono la POPOLAZIONE DI CONTROLLO: se differissero")
    print("     anche quelle, il problema non sarebbe la configurazione ma il prodotto.")


asyncio.run(main())
