r"""Il blocco della prima scrittura MCP e' del prodotto, o della NOSTRA macchina a otto istanze?

Ho misurato (`7e886848`) che su `main` installato la prima scrittura MCP con una fonte
non torna: **>90s**, poi **>420s**, poi **>11 minuti** senza mai completare. Stavo per
consegnarlo come difetto del prodotto. **Prima di lasciarlo li', questo banco prova a
falsificarlo.**

L'INDIZIO CHE LO MOTIVA: il processo aspetta a **CPU 0% e RAM 357 MB** — non ha caricato
il cross-encoder (sarebbe 1-2 GB) ⇒ **aspetta PRIMA di caricare**. E in `verimem` ci
sono **tre path condivisi hardcoded su `Path.home()`**, che **otto istanze** su questa
macchina usano insieme::

    encode_service.py:41    DISCOVERY_PATH      ~/.engram/encode_service.json
    encode_service.py:573   _SPAWN_LOCK_PATH    ~/.engram/encode_service.spawn.lock
    encode_service.py:583   DAEMON_LOCK_PATH    ~/.engram/encode_service.daemon.lock

⇒ **Nessuno dei tre deriva da `HIPPO_DATA_DIR`** (mio reperto `fdd6df83`): un venv
vergine **non e' isolato**. E i lock portano la data del daemon dello stack principale.

L'A/B, **nella stessa esecuzione** (o i due bracci non sono confrontabili)::

    braccio A   HOME normale     i path condivisi sono quelli delle otto istanze
    braccio B   HOME isolato     `USERPROFILE`/`HOME` in una dir temporanea
                                 ⇒ `Path.home()` punta altrove: zero contesa

⚠️ **E la cache dei modelli resta quella vera** (`HF_HOME` verso `~/.cache/huggingface`,
23 GB): senza, il braccio B ri-scaricherebbe il modello e misurerei un download.

    se B torna VELOCE   ⇒ la causa e' la CONTESA fra le nostre istanze, non il prodotto:
                          il reperto va ridimensionato al nostro regime
    se B si blocca      ⇒ il blocco e' del prodotto e vale per un utente solo

⚖️ PUNTI DEBOLI: cambiare HOME sposta **tutti** i path condivisi in una volta — se B
torna, so **che** sono loro, non **quale** dei tre; e un solo giro per braccio.

🔴 ESITO — **la mia ipotesi assolutoria CADE: si blocca anche isolato**::

    braccio                  handshake   prima scritt.   status
    A  HOME normale               2.0s          300.0s   TIMEOUT
    B  HOME isolato               1.9s          300.0s   TIMEOUT

⇒ **Non e' la contesa fra le nostre istanze.** Il fenomeno vale per un utente solo.
⚠️ **E due timeout non sono la stessa causa solo perche' sono due timeout**: il braccio
B potrebbe bloccarsi per un motivo suo. Quello che rende la lettura solida non e' questo
A/B da solo — e' che il blocco si e' riprodotto **cinque volte** con finestre diverse
(90s · 300s · 420s · 300s isolato · oltre 11 minuti), e mai una volta e' tornato.

✅ **E IL LAVORO FINISCE LO STESSO — prova diretta, non inferenza.** Nel banco a tre
scritture (`7e886848`) la prima ando' in TIMEOUT lato client; lo store, letto dopo,
contiene **3 fatti su 3**, e il primo — «*Nella coda ci sono 149 run in attesa*» — c'e'
con **`grounding_score = 99.67`**::

    5602dba60bfb  Nella coda ci sono 149 run in attesa.    g=99.67   <- il TIMEOUT
    be65810cd309  Nella coda ci sono 3 run in corso.       g=99.43
    9e0d0c5500aa  Nella coda ci sono 2557 run completati.  g=99.24

🔑 ⇒ **Il server scrive e GIUDICA; e' la RISPOSTA che non torna al client.** Non e' un
blocco del giudizio ne' un deadlock del lavoro: e' il canale di risposta di **quella
sola chiamata** — la prima che richiede il giudice.
📌 **Prima avevo dedotto la stessa cosa dal journal, che pero' non basta**: sei eventi
per tre scritture non dicono **di chi** siano. Il righello giusto era **contare i fatti
nello store**, e li' il primo c'e' col suo punteggio.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-blocco-e-nostro-o-del-prodotto.py <venv> [timeout]
"""
import os
import subprocess
import sys
import tempfile
import textwrap

CLIENT = r'''
import asyncio, json, os, sys, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE, TMO = sys.argv[1], float(sys.argv[2])
CODA = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
        "e 3 run in corso.")
env = dict(os.environ)
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    t0 = time.time()
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            hs = time.time() - t0
            t = time.time()
            try:
                res = await asyncio.wait_for(
                    s.call_tool("hippo_remember",
                                {"proposition": "Nella coda ci sono 149 run in attesa.",
                                 "source": CODA}), TMO)
                d = json.loads("".join(str(getattr(c, "text", "")) for c in (res.content or [])))
                print("ESITO|%.1f|%.1f|%s|%s" % (hs, time.time() - t, d.get("status"),
                                                 d.get("grounding_score")), flush=True)
            except asyncio.TimeoutError:
                print("ESITO|%.1f|%.1f|TIMEOUT|-" % (hs, time.time() - t), flush=True)

asyncio.run(main())
'''


def giro(venv, isolato, tmo):
    store = tempfile.mkdtemp(prefix="ws5_home_")
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    casa = ""
    if isolato:
        casa = tempfile.mkdtemp(prefix="ws5_casa_")
        env["USERPROFILE"] = casa          # Path.home() su Windows
        env["HOME"] = casa
        env["HOMEDRIVE"] = os.path.splitdrive(casa)[0]
        env["HOMEPATH"] = os.path.splitdrive(casa)[1]
        # ⚠️ la cache dei modelli resta la VERA, o misuro un download
        vera = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        env["HF_HOME"] = vera
        env["HUGGINGFACE_HUB_CACHE"] = os.path.join(vera, "hub")
        env["TRANSFORMERS_CACHE"] = os.path.join(vera, "hub")
    try:
        r = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script,
                            store, str(tmo)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=tmo + 400, env=env,
                           cwd=os.path.dirname(venv))
        riga = next((x for x in (r.stdout or "").splitlines() if x.startswith("ESITO|")), "")
        return (riga[6:].split("|") if riga else ["-", "-", "nessun output", "-"]), casa
    except subprocess.TimeoutExpired:
        return ["-", "-", "il processo non e' tornato", "-"], casa


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [timeout]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    print("  timeout per braccio: %.0fs\n" % tmo)
    print("  %-22s %11s %13s  %-14s %s"
          % ("braccio", "handshake", "prima scritt.", "status", "grounding"))
    print("  " + "-" * 76)
    esiti = {}
    for nome, iso in (("A  HOME normale", False), ("B  HOME isolato", True)):
        campi, casa = giro(venv, iso, tmo)
        hs, dur, stato, g = (campi + ["-", "-", "-", "-"])[:4]
        try:
            print("  %-22s %10.1fs %12.1fs  %-14s %s"
                  % (nome, float(hs), float(dur), stato, g))
        except ValueError:
            print("  %-22s %11s %13s  %-14s %s" % (nome, hs, dur, stato, g))
        esiti[nome[0]] = stato

    print("\n=== VERDETTO ===")
    a, b = esiti.get("A"), esiti.get("B")
    if a == "TIMEOUT" and b and b != "TIMEOUT":
        print("  🪞 IL BLOCCO E' NOSTRO, NON DEL PRODOTTO: con HOME isolato la prima")
        print("     scrittura torna. La causa e' la CONTESA sui path condivisi in")
        print("     `~/.engram/` fra le otto istanze ⇒ un utente solo non lo vede.")
        print("  ⇒ Il reperto va RIDIMENSIONATO al nostro regime, e detto pubblicamente.")
    elif a == "TIMEOUT" and b == "TIMEOUT":
        print("  🔴 SI BLOCCA ANCHE ISOLATO: la contesa non c'entra, il difetto e' del")
        print("     prodotto e vale per un utente solo.")
    elif a and a != "TIMEOUT":
        print("  ⚠️ IL BRACCIO A NON SI BLOCCA in questo giro (%s): il fenomeno e'" % a)
        print("     INTERMITTENTE ⇒ dipende da cosa fanno le altre istanze in quel")
        print("     momento, e una singola misura non basta a dichiararlo.")
    else:
        print("  ⚠️ esito non classificabile: A=%s B=%s" % (a, b))


main()
