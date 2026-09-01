r"""Sul pacchetto INSTALLATO, la stessa scrittura e' giudicata dalla CLI e non da MCP.

Nato per chiudere due limiti che avevo dichiarato — ① `25d8441b`: «*misuro l'AVVIO del
server, non una sessione MCP completa*»; ② `W5-8`: una scrittura con source su stdio
non tornava entro 190s, **causa dichiarata IGNOTA**. Li chiude entrambi, e per strada
trova qualcosa di piu' grosso.

LA DOMANDA: un claim che la sua fonte **smentisce** viene fermato da tutte le porte?

    fonte   «La coda della CI contiene 2557 run completati, 149 run in attesa
             e 3 run in corso.»
    claim   «Nella coda ci sono 7777 run in corso.»        ⇒ la fonte dice 3

STESSO venv, stessa frase, stessa source, store nuovo, ambiente pulito. **L'unica
variabile e' la PORTA.**

🔴 ESITO — **LE DUE PORTE NON DANNO LO STESSO VERDETTO**::

    porta / regime               status         dettaglio                durata
    CLI  (default utente)        quarantined ✅  layers=['L4-grounding']   18.9s
    MCP  (default utente)        model_claim 🔴  g=None warn=0 moat=False   7.8s
    MCP  + GROUNDING_WRITE=1     quarantined ✅  (controllo a var. singola) 8.5s

⇒ **Da MCP il falso ENTRA, con `ok: true` e la ricevuta muta.** Da CLI viene fermato.
⇒ **La terza riga isola la causa**: accendendo quella sola manopola, MCP lo ferma.

⚠️ `moat=False` non e' un verdetto: e' **l'assenza del campo `moat`** dalla risposta.
La ricevuta non dice «non ho giudicato» — **non dice niente**, ed e' la meta' peggiore
del difetto: un client che legge `ok: true` non ha modo di accorgersene.
📌 `warn=0` e' misurato **alla porta**; nello stderr del server compare invece
`coherence_warning numbers=[7777.0] vs [3.0]` ⇒ **qualcosa se ne accorge e non
arriva alla ricevuta**. E' la forma «*un campo stampato e non letto e' un campo
assente*», qui nella variante «*calcolato e non consegnato*».

Nel sorgente **installato** (`site-packages/verimem/mcp_server.py`), `ground_write=`
compare **ZERO volte**: il server non lo passa mai a `run_validation_gate`, che ricade
sull'env. La CLI invece lo deriva dalla source — `cli.py:1989`::

    source=source, ground_write=True if source else None

📌 **E LA CURA ESISTE GIA' IN `main`**, dal commit `7b8af116` del 29/07/2026 05:35,
il cui messaggio la nomina: «*feat(mcp): a source given to the MCP channel is now
actually checked*». In `mcp_server.py` di `main`::

    _gw_env = os.environ.get("ENGRAM_GROUNDING_WRITE", "").strip().lower()
    if _gw_env in ("0", "off", "false", "no"):  _ground_write = False
    elif _source:                               _ground_write = True
    else:                                       _ground_write = None

⇒ **Non e' un difetto di build**: il tag `v0.7.0` e' del **22/07**, la cura del **29/07**
— il pacchetto e' coerente, e' solo **piu' vecchio della cura di sette giorni**.

⚠️ **PERCHE' TOCCA IL RILASCIO IN CORSO**: il wheel **0.7.1** porta lo **stesso**
`mcp_server.py` della 0.7.0 (13488 righe in entrambi, `ground_write=` zero in entrambi).
Oggi il difetto e' **inaccessibile** perche' su 0.7.0 il server MCP **non parte**
(`25d8441b`). L'hotfix ripara l'AVVIO ⇒ **consegnerebbe una porta che parte e non
giudica**. Il tag che contiene la cura e' `v0.7.6`.
⛔ **La decisione non e' mia**: porto la misura, non la scelta di cosa pubblicare.

🪞 E QUESTO BANCO HA SBAGLIATO TRE VOLTE PRIMA DI DIRE IL VERO::

    ①  chiamavo il tool col parametro `content`; il server rispondeva «'proposition'
       is a required property» — messaggio CHIARO — ma `call_tool` **torna** un errore
       senza **sollevarlo**, e il banco stampava «ok» in 0.0s su chiamate fallite.
    ②  ho letto `layers=[]` come «il gate non e' girato» e stavo per annunciare che il
       wheel 0.7.1 non esegue il gate. L'A/B fra le due versioni l'ha smentito: sul
       claim VERO **entrambe** dicono `layers=[]` e ammettono; sul FALSO **entrambe**
       accendono `L4-grounding` e quarantinano. `layers=[]` significa «nessun presidio
       si e' acceso», non «nessun presidio esiste».
    ③  il grep che dichiarava assente `ground_write=` non era leggibile finche' non ho
       messo un **controllo positivo** (`run_validation_gate`, 4 occorrenze): senza,
       «zero risultati» e «sto guardando il file sbagliato» sono indistinguibili.

⇒ Due volte su tre il righello sbagliava **contro** il prodotto (allarme falso). Il
reperto e' sopravvissuto solo perche' ogni passo aveva il suo controllo.

📖 **NON E' NUOVO COME FAMIGLIA, e va detto**: `W2-24` di @ws2 (`00-ESAME.md`) ha gia'
registrato che «*con `ENGRAM_GROUNDING_WRITE=0` una porta smette di giudicare e due
no*». Quello che qui e' nuovo: ① la disparita' si vede **al default**, senza spegnere
niente, **sul pacchetto che un utente installa**; ② il costo e' **un falso ammesso**,
non un campo diverso; ③ nella ricevuta MCP del pacchetto **non c'e' nessun campo
`moat`** — W2-24 lodava MCP perche' il suo `moat` «nomina perfino la variabile».

REGIME: Windows, venv vergini (`pip install verimem` e wheel 0.7.1), ambiente senza
`HIPPO_*`/`ENGRAM_*`/`VERIMEM_*`, store nuovo per misura, CWD fuori dal repo, un
processo per volta.
⚖️ PUNTI DEBOLI: **un solo claim falso**, di tipo numerico — non so se la disparita'
tenga su una smentita non numerica; e il client MCP e' scritto da me con l'SDK `mcp`,
non e' Claude Code.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-le-due-porte-del-pacchetto-non-giudicano-uguale.py <venv>
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import time

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
FALSO = "Nella coda ci sono 7777 run in corso."

CLIENT = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE, FALSO, FONTE = sys.argv[1], sys.argv[2], sys.argv[3]
GW = sys.argv[4] if len(sys.argv) > 4 else ""

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
            await asyncio.wait_for(s.initialize(), 120)
            tl = await s.list_tools()
            nomi = [t.name for t in tl.tools]
            scrivi = next((n for n in nomi if n.endswith("remember")), None)
            if not scrivi:
                print("MCPOUT|nessuno strumento di scrittura"); return
            # (!) `call_tool` TORNA un errore senza sollevarlo: si legge il CONTENUTO.
            res = await asyncio.wait_for(s.call_tool(scrivi, {"proposition": FALSO,
                                                              "source": FONTE}), 300)
            testo = "".join(str(getattr(c, "text", "")) for c in (res.content or []))
            try:
                d = json.loads(testo)
                print("MCPOUT|%s|%s|%s|%s|%s" % (
                    d.get("status"), d.get("grounding_score"),
                    len(d.get("anti_confab_warnings") or []),
                    "moat" in d, len(nomi)))
            except Exception:
                print("MCPOUT|non-json: %s" % testo[:70])

asyncio.run(main())
'''


def ambiente(store, extra=None):
    e = {k: v for k, v in os.environ.items()
         if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    e["HIPPO_DATA_DIR"] = store
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e.update(extra or {})
    return e


def via_cli(venv, gw=None):
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    store = tempfile.mkdtemp(prefix="ws5_porte_cli_")
    t = time.time()
    r = subprocess.run([exe, "remember", FALSO, "--source", FONTE],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900,
                       env=ambiente(store, {"ENGRAM_GROUNDING_WRITE": gw} if gw else None),
                       cwd=os.path.dirname(venv))
    out = (r.stdout or "") + (r.stderr or "")
    lay = next((tok[7:] for tok in out.replace("\n", " ").split()
                if tok.startswith("layers=")), "")
    stato = "quarantined" if "quarantin" in out else "admitted" if "admitted" in out else "?"
    return stato, lay[:22], time.time() - t


def via_mcp(venv, gw=""):
    py = os.path.join(venv, "Scripts", "python.exe")
    store = tempfile.mkdtemp(prefix="ws5_porte_mcp_")
    script = os.path.join(store, "_client.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    t = time.time()
    r = subprocess.run([py, script, store, FALSO, FONTE, gw], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900,
                       env=ambiente(store), cwd=os.path.dirname(venv))
    riga = next((x for x in (r.stdout or "").splitlines() if x.startswith("MCPOUT|")), "")
    return riga[7:].split("|"), time.time() - t


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    if not os.path.exists(os.path.join(venv, "Scripts", "python.exe")):
        print("  🔴 venv assente: %s" % venv)
        return
    ver = ""
    out = subprocess.run([os.path.join(venv, "Scripts", "pip.exe"), "show", "verimem"],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout
    for riga in out.splitlines():
        if riga.lower().startswith("version:"):
            ver = riga.split(":", 1)[1].strip()

    print("  pacchetto: verimem %s" % ver)
    print("  claim FALSO: «%s»" % FALSO)
    print("  la fonte dice: 3 run in corso\n")
    print("  %-30s %-14s %-24s %8s" % ("porta / regime", "status", "dettaglio", "durata"))
    print("  " + "-" * 84)

    stato, lay, dur = via_cli(venv)
    print("  %-30s %-14s layers=%-17s %7.1fs" % ("CLI  (default utente)", stato, lay, dur))

    campi, dur = via_mcp(venv)
    if len(campi) >= 5:
        print("  %-30s %-14s g=%-5s warn=%-2s moat=%-4s %7.1fs"
              % ("MCP  (default utente)", campi[0], campi[1], campi[2], campi[3], dur))
        print("       (%s strumenti esposti)" % campi[4])
    else:
        print("  %-30s %s" % ("MCP  (default utente)", "|".join(campi)[:60]))

    campi_on, dur_on = via_mcp(venv, "1")
    if len(campi_on) >= 3:
        print("  %-30s %-14s %-24s %7.1fs"
              % ("MCP  + GROUNDING_WRITE=1", campi_on[0], "(controllo a var. singola)", dur_on))

    # il sorgente INSTALLATO: chi passa `ground_write` al gate?
    # ⚠️ con CONTROLLO POSITIVO, o «zero risultati» e «file sbagliato» si confondono.
    src = os.path.join(venv, "Lib", "site-packages", "verimem", "mcp_server.py")
    print("\n  --- il sorgente installato (%s) ---" % ("presente" if os.path.exists(src) else "🔴 ASSENTE"))
    if os.path.exists(src):
        testo = open(src, encoding="utf-8", errors="replace").read()
        for pat, atteso in (("run_validation_gate", "DEVE esserci (controllo positivo)"),
                            ("ENGRAM_GROUNDING_WRITE", "DEVE esserci (controllo positivo)"),
                            ("ground_write=", "se ZERO, il gate non lo riceve mai")):
            n = testo.count(pat)
            print("    %-26s %2d×   %s" % (pat, n, atteso))

    print("\n=== VERDETTO ===")
    mcp_stato = campi[0] if campi else "?"
    if stato == "quarantined" and mcp_stato != "quarantined":
        print("  🔴 LE DUE PORTE NON DANNO LO STESSO VERDETTO: la CLI ferma il falso,")
        print("     MCP lo ammette. Stesso pacchetto, stessa source, stesso claim.")
        if campi_on and campi_on[0] == "quarantined":
            print("  🔑 E con ENGRAM_GROUNDING_WRITE=1 MCP lo ferma ⇒ causa isolata a")
            print("     UNA manopola, che la CLI deriva dalla source e MCP no.")
    elif stato == mcp_stato:
        print("  🟢 le due porte concordano (%s): la disparita' non si riproduce qui." % stato)
    else:
        print("  🟡 esito non classificabile: CLI=%s MCP=%s" % (stato, mcp_stato))


main()
