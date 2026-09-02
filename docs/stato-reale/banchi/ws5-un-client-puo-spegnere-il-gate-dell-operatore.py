r"""Un client MCP puo' spegnere il gate che l'operatore ha acceso? Alla porta, non nel codice.

@ws8 alle 05:13 ha portato un reperto letto NEL CODICE: il commit `4a37b09d` (24/07)
introduce `VERIMEM_MCP_TRUST_GATE_KNOBS` e `gate_knobs_denied` — la politica per cui
`validate="off"` e `force_persist=True`, arrivando da **argomenti di un client**, sono
onorati **solo** col consenso dell'operatore. Il suo conteggio::

    VERIMEM_MCP_TRUST_GATE_KNOBS   0 a v0.7.0 · 0 nel treno · 4 su origin/main
    gate_knobs_denied              0 a v0.7.0 · 0 nel treno · 5 su origin/main
    ma i knob CI SONO gia' nel treno:  force_persist 3 · validate 31

⇒ Nel pacchetto **i knob che indeboliscono il gate esistono e la protezione no**.

QUESTO BANCO NON RILEGGE IL CODICE: **chiama la porta e guarda cosa succede.**
(«*il livello a cui misuri decide il verdetto: misura dove il prodotto chiama*».)

IL CASO PERICOLOSO, e va costruito con cura::

    sul wheel il gate MCP non gira comunque (`W5-30`), quindi «il falso passa» non
    direbbe niente. Il caso che conta e' l'OPERATORE CHE HA ACCESO IL GATE:

        ENGRAM_GROUNDING_WRITE=1     <- l'operatore accende il moat (misurato: funziona)
        validate="off"               <- il CLIENT prova a spegnerlo

⇒ Se il falso **passa**, un client non fidato ha spento il giudice di un operatore che
lo aveva acceso — che e' esattamente lo scenario che `4a37b09d` esiste per chiudere.

I QUATTRO BRACCI, sullo stesso claim falso e la stessa fonte::

    ①  gate ACCESO, nessun knob          (controllo: deve FERMARE)
    ②  gate ACCESO, validate="off"       (il caso pericoloso)
    ③  gate ACCESO, force_persist=True   (l'altro knob della stessa politica)
    ④  su `main` installato, validate="off"   (deve NEGARE il knob: gate_knobs_denied)

⇒ ① e' la popolazione di controllo: senza, «passa» non si distingue da «il gate non
gira». ④ e' il controllo POSITIVO sulla cura: se nemmeno `main` negasse il knob, il
reperto non sarebbe del pacchetto ma del prodotto.

📌 **E la prima chiamata di ogni sessione e' SACRIFICALE** (`W5-31`…`W5-34`: la prima
scrittura con fonte non torna), altrimenti misuro un timeout invece di un verdetto.

REGIME: wheel 0.7.1 e `main` 0.7.6 INSTALLATI, ambiente pulito, store nuovo, CWD fuori
dal repo.
⚖️ PUNTI DEBOLI: un solo claim falso; il client e' scritto da me con l'SDK `mcp`; e
«passa» qui vuol dire `status != quarantined`, non «l'utente non se ne accorge».

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-un-client-puo-spegnere-il-gate-dell-operatore.py <dir-con-i-venv>
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap

CLIENT = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE, GW, EXTRA = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
CODA = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
        "e 3 run in corso.")
FALSO = "Nella coda ci sono 7777 run in corso."

env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"
if GW:
    env["ENGRAM_GROUNDING_WRITE"] = GW

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            # prima chiamata SACRIFICALE: non torna (W5-31..W5-34)
            try:
                await asyncio.wait_for(
                    s.call_tool("hippo_remember",
                                {"proposition": "Riscaldamento.", "source": CODA}), 200)
            except Exception:
                pass
            arg = {"proposition": FALSO, "source": CODA}
            arg.update(EXTRA)
            try:
                res = await asyncio.wait_for(s.call_tool("hippo_remember", arg), 300)
                testo = "".join(str(getattr(c, "text", "")) for c in (res.content or []))
                d = json.loads(testo)
                negati = d.get("gate_knobs_denied")
                print("OUT|%s|%s|%s" % (d.get("status"), d.get("grounding_score"),
                                        negati if negati is not None else "campo assente"),
                      flush=True)
            except asyncio.TimeoutError:
                print("OUT|TIMEOUT|-|-", flush=True)
            except Exception as e:
                print("OUT|errore %s|-|-" % type(e).__name__, flush=True)

asyncio.run(main())
'''


def giro(venv, gw, extra):
    store = tempfile.mkdtemp(prefix="ws5_knob_")
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script,
                            store, gw, json.dumps(extra)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900, env=env,
                           cwd=os.path.dirname(venv))
        riga = next((x for x in (r.stdout or "").splitlines() if x.startswith("OUT|")), "")
        return riga[4:].split("|") if riga else ["nessun output", "-", "-"]
    except subprocess.TimeoutExpired:
        return ["il processo non e' tornato", "-", "-"]


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-con-i-venv>" % sys.argv[0])
        raise SystemExit(2)
    base = sys.argv[1]
    wheel = os.path.join(base, "venv_utente")
    principale = os.path.join(base, "venv_main")
    for v in (wheel, principale):
        if not os.path.exists(os.path.join(v, "Scripts", "python.exe")):
            print("  🔴 venv assente: %s" % v)
            return

    bracci = [
        ("① wheel · gate ACCESO, nessun knob", wheel, "1", {}),
        ("② wheel · gate ACCESO + validate=off", wheel, "1", {"validate": "off"}),
        ("③ wheel · gate ACCESO + force_persist", wheel, "1", {"force_persist": True}),
        ("④ main  · gate ACCESO + validate=off", principale, "1", {"validate": "off"}),
    ]
    print("  claim FALSO: «Nella coda ci sono 7777 run in corso.» — la fonte dice 3\n")
    print("  %-38s %-13s %-9s %s" % ("braccio", "status", "grounding", "gate_knobs_denied"))
    print("  " + "-" * 90)
    esiti = {}
    for nome, venv, gw, extra in bracci:
        st, g, negati = (giro(venv, gw, extra) + ["-", "-", "-"])[:3]
        print("  %-38s %-13s %-9s %s" % (nome, st, str(g)[:8], negati))
        esiti[nome[0]] = st

    print("\n=== VERDETTO ===")
    ctrl = esiti.get("①")
    if ctrl != "quarantined":
        print("  ⚠️ IL CONTROLLO ① NON FERMA IL FALSO (%s): senza di lui «passa» non si" % ctrl)
        print("     distingue da «il gate non gira», e i bracci ② ③ non sono leggibili.")
        return
    print("  ✅ ① il gate acceso FERMA il falso: il confronto e' leggibile.")
    for chiave, nome, knob in (("②", "validate=off", "validate"),
                               ("③", "force_persist", "force_persist")):
        st = esiti.get(chiave)
        if st != "quarantined":
            print("  🔴 %s SUL WHEEL il knob «%s» del CLIENT spegne il gate dell'operatore"
                  % (chiave, knob))
            print("     (status=%s) ⇒ la politica di `4a37b09d` NON e' nel pacchetto." % st)
        else:
            print("  🟢 %s il knob «%s» NON indebolisce il gate su questo pacchetto." % (chiave, knob))
    q = esiti.get("④")
    if q == "quarantined":
        print("  ✅ ④ su `main` lo stesso knob e' NEGATO: la cura esiste e funziona —")
        print("     manca solo al pacchetto. ⇒ Il reperto e' del TRENO, non del prodotto.")
    else:
        print("  ⚠️ ④ nemmeno `main` ferma il falso con validate=off (%s): allora il" % q)
        print("     reperto sarebbe del PRODOTTO, e va detto in modo molto diverso.")


main()
