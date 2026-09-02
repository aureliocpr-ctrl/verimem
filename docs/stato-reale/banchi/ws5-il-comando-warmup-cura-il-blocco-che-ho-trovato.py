r"""Il prodotto ha un comando `warmup`. Cura il blocco della prima scrittura MCP?

Ho misurato (`W5-31`…`W5-33`) che la prima scrittura MCP con una fonte non torna, e che
il frame bloccante e' **l'import di `scipy.linalg.blas`** — 8 hang indipendenti, 8 volte
lo stesso frame, letti dal watchdog del prodotto.

Poi ho letto l'`--help`, ed esisteva gia' un comando che sembra fatto per questo::

    warmup   Pre-load (and download on first run) the models Verimem needs.

⇒ **Se lo cura, la cura c'e' gia' e manca solo una riga di documentazione.**
⇒ **Se NON lo cura, il prodotto ha un comando che sembra rispondere e non risponde** —
   e chi lo esegue crede di aver preparato il terreno.

⚠️ **PERCHE' HO UN DUBBIO SERIO PRIMA DI MISURARE, e lo dichiaro**: `warmup` gira in un
**altro processo**, che poi muore. Il beneficio che sopravvive e' la **cache su disco**
(il download). Ma il costo che ho misurato **non e' il download** — la cache
HuggingFace era gia' 23 GB e `sentence-transformers` gia' installato: e' **l'import in
memoria**, che ogni processo rifa' da capo. ⇒ **La mia predizione e' che NON curi.**
E la scrivo prima di eseguire, cosi' l'esito puo' smentirmi.

L'A/B, nella stessa esecuzione::

    A   sessione MCP fresca                       -> prima scrittura con fonte
    B   `verimem warmup` PRIMA, poi sessione MCP  -> prima scrittura con fonte

🔴 ESITO — **la predizione regge, e il dato piu' importante e' un altro**::

    A  senza warmup                        prima scrittura   240.0s   TIMEOUT
    B  `verimem warmup` exit=0 in 21.7s    prima scrittura   240.0s   TIMEOUT

⇒ `warmup` **fa quello che promette** — gira, esce 0, in **21.7 secondi** — ma il
pre-load **non attraversa il confine del processo**: e' un altro processo, e muore.
⚠️ **Non e' che il comando menta**: la promessa letterale («*pre-load (and download on
first run) the models*») e' mantenuta. E' che **l'effetto per cui uno lo esegue e'
per-processo**, e il processo che conta e' un altro. ⇒ Forma precisa:
**un comando che mantiene la promessa e non produce l'effetto per cui esiste.**

🔑 **E IL NUMERO NUOVO, che vale piu' del verdetto**: lo **stesso caricamento** costa

    21.7s   nel processo della CLI (`verimem warmup`, exit 0)
    >240s   nel processo del server MCP

**stesso pacchetto, stessa macchina, stesso momento** ⇒ un rapporto di **almeno 11 volte**.
⇒ Non e' «l'import di scipy e' lento»: e' che **in quel processo** quell'import e'
drammaticamente piu' lento. L'import avviene in un **thread secondario** mentre gira
l'event loop asyncio (il frame `anyio/_backends/_asyncio.py` e' nel dump accanto).
⛔ **Perche' proprio li' sia cosi' lento non l'ho isolato** — non lo dichiaro.

📌 **Conseguenza operativa, per chi usa il prodotto oggi**: il costo si paga **una volta
per processo del server**. Chi tiene il server MCP **vivo a lungo** lo paga una volta e
poi ha 0.3-4.1s; chi lo riavvia spesso lo paga ogni volta. E `warmup` **non aiuta**.

⚖️ PUNTI DEBOLI: un giro per braccio; se `warmup` fallisse o non toccasse il giudice, B
misurerebbe «non ha fatto niente» e non «non serve» — **exit 0 in 21.7s dice che ha
lavorato**, ma non che abbia toccato lo stesso codice del giudice; e resta il caso di un
utente che tiene il server **vivo a lungo**, dove il costo si paga una volta sola.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-comando-warmup-cura-il-blocco-che-ho-trovato.py <venv> [timeout]
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import time

CLIENT = r'''
import asyncio, json, os, sys, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
STORE, TMO = sys.argv[1], float(sys.argv[2])
CODA = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
        "e 3 run in corso.")
env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            t = time.time()
            try:
                res = await asyncio.wait_for(
                    s.call_tool("hippo_remember",
                                {"proposition": "Nella coda ci sono 149 run in attesa.",
                                 "source": CODA}), TMO)
                d = json.loads("".join(str(getattr(c, "text", "")) for c in (res.content or [])))
                print("ESITO|%.1f|%s|%s" % (time.time() - t, d.get("status"),
                                            d.get("grounding_score")), flush=True)
            except asyncio.TimeoutError:
                print("ESITO|%.1f|TIMEOUT|-" % (time.time() - t), flush=True)
asyncio.run(main())
'''


def ambiente(store):
    e = {k: v for k, v in os.environ.items()
         if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    e["HIPPO_DATA_DIR"] = store
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return e


def warmup(venv, store):
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    t = time.time()
    r = subprocess.run([exe, "warmup"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=2400, env=ambiente(store),
                       cwd=os.path.dirname(venv))
    return r.returncode, time.time() - t, ((r.stdout or "") + (r.stderr or ""))[-160:]


def sessione(venv, store, tmo):
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    env = ambiente(store)
    del env["HIPPO_DATA_DIR"]
    try:
        r = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script,
                            store, str(tmo)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=tmo + 400, env=env,
                           cwd=os.path.dirname(venv))
        riga = next((x for x in (r.stdout or "").splitlines() if x.startswith("ESITO|")), "")
        return riga[6:].split("|") if riga else ["-", "nessun output", "-"]
    except subprocess.TimeoutExpired:
        return ["-", "il processo non e' tornato", "-"]


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [timeout]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 240.0
    print("  timeout per braccio: %.0fs\n" % tmo)
    esiti = {}
    for nome, con_warmup in (("A  senza warmup", False), ("B  CON warmup prima", True)):
        store = tempfile.mkdtemp(prefix="ws5_warm_")
        if con_warmup:
            code, dur, coda = warmup(venv, store)
            print("  %s: `verimem warmup` exit=%s in %.1fs   %s"
                  % (nome, code, dur, coda.strip().replace("\n", " ")[:70]))
        campi = sessione(venv, store, tmo)
        dur, stato, g = (campi + ["-", "-", "-"])[:3]
        try:
            print("  %-22s prima scrittura %8.1fs   status=%-12s g=%s"
                  % (nome, float(dur), stato, g))
        except ValueError:
            print("  %-22s %s" % (nome, stato))
        esiti[nome[0]] = stato
        print()

    print("=== VERDETTO ===")
    a, b = esiti.get("A"), esiti.get("B")
    if a == "TIMEOUT" and b and b != "TIMEOUT":
        print("  🟢 `warmup` CURA il blocco: dopo averlo eseguito la prima scrittura")
        print("     torna. ⇒ La cura ESISTE gia' come comando — manca la riga che lo")
        print("     dice a chi installa. La mia predizione era sbagliata.")
    elif a == "TIMEOUT" and b == "TIMEOUT":
        print("  🔴 `warmup` NON cura: la prima scrittura si blocca lo stesso.")
        print("     ⇒ Il comando prepara la CACHE SU DISCO, ma il costo e' l'import IN")
        print("        MEMORIA, che ogni processo rifa'. Chi lo esegue crede di aver")
        print("        preparato il terreno e non ha cambiato niente su questo caso.")
    elif a and a != "TIMEOUT":
        print("  ⚠️ IL BRACCIO A NON SI BLOCCA in questo giro (%s) ⇒ il confronto non e'" % a)
        print("     leggibile: senza il blocco da una parte, l'altra non dice niente.")
    else:
        print("  ⚠️ esito non classificabile: A=%s B=%s" % (a, b))


main()
