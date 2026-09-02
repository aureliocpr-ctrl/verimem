r"""Il gate non vede le RELAZIONI: la classe vale anche sul pacchetto che si installa?

Stanotte tre istanze hanno trovato la stessa cosa da tre strade::

    @ws4  `W7-112`/`d600bc2f`  il moat vede la CIFRA e non la GRANDEZZA
                               («ran 42 test files» con fonte «finished in 42 seconds»
                               → grounding 98,06, ammesso)
    @ws1  `02124ecd`           9 frasi su 10 che cambiano SOLO IL SOGGETTO passano,
                               con gli stessi punteggi delle vere (98,05…99,98)
    io    `ff687744`           lo scambio di grandezza passa su 4 celle su 4

⇒ **Il giudice vede la somiglianza e i valori; non vede CHI fa cosa, QUALE grandezza,
QUALE esito.** Ma tutte e tre le misure sono su `main` (SDK o repo).

LA DOMANDA CHE MANCA, ed e' quella che posso chiudere io: **vale anche per chi
installa?** Il mio terreno sono i **due pacchetti installati** e le **due porte**.

⚠️ **NON riproduco i loro casi**: non ho le loro fonti verbatim, e riprodurre un
reperto altrui senza la fonte esatta e' il modo migliore per contraddirlo a torto
(@ws2 me l'ha ricordato stanotte). Uso **casi miei della stessa forma**, dichiarandolo.

I CASI — una fonte, sei claim, **entrambe le popolazioni**::

    fonte  «Il gate di ws3 ha respinto 12 fatti di ws4 durante il turno di notte.»

    V1  Il gate di ws3 ha respinto 12 fatti.              vero
    V2  ws4 ha avuto 12 fatti respinti.                   vero
    V3  Il turno di notte ha visto 12 fatti respinti.     vero
    R1  Il gate di ws4 ha respinto 12 fatti di ws3.       SOGGETTO INVERTITO
    R2  ws3 ha avuto 12 fatti respinti dal gate di ws4.   SOGGETTO INVERTITO
    R3  Il gate di ws3 ha ACCETTATO 12 fatti di ws4.      ESITO INVERTITO

⇒ V1-V3 sono la popolazione positiva: senza, un gate che ferma tutto sembrerebbe
perfetto. **La riga che conta e' dove le due popolazioni si separano.**

📌 **E applico cio' che ho appena misurato** (`W5-31`…`W5-34`): sulla porta MCP la
**prima** scrittura con fonte non torna, quindi il banco ne fa una **di riscaldamento**
e misura dalla seconda. Senza, misurerei il blocco invece del giudizio.

🔑 ESITO — **non e' che il gate non veda le relazioni: e' la FORMA a decidere**::

    caso                     porta  wheel 0.7.1  main 0.7.6  atteso    g (main/MCP)
    V1 vero                  CLI    ammesso      ammesso     ammesso
    V1 vero                  MCP    ammesso      ammesso     ammesso   99.76
    V2 vero                  CLI    ammesso      ammesso     ammesso
    V2 vero                  MCP    ammesso      ammesso     ammesso   97.86
    V3 vero                  CLI    ammesso      ammesso     ammesso
    V3 vero                  MCP    ammesso      ammesso     ammesso   89.34
    R1 soggetto invertito    CLI    fermato      fermato     fermato
    R1 soggetto invertito    MCP    ammesso 🔴    fermato     fermato   26.81
    R2 soggetto invertito    CLI    ammesso 🔴    ammesso 🔴   fermato
    R2 soggetto invertito    MCP    ammesso 🔴    ammesso 🔴   fermato   99.69
    R3 esito invertito       CLI    fermato      fermato     fermato
    R3 esito invertito       MCP    ammesso 🔴    fermato     fermato    1.17

**I VERI: 6 celle su 6 ammesse — zero falsi allarmi**, che e' la meta' buona e va detta.

🔑 **IL PEZZO NUOVO — R1 e R2 sono LA STESSA INVERSIONE, in attiva e in passiva**::

    R1  «Il gate di ws4 ha respinto 12 fatti di ws3»        attiva   FERMATO   g= 26.81
    R2  «ws3 ha avuto 12 fatti respinti dal gate di ws4»    passiva  AMMESSO   g= 99.69

⇒ **La stessa falsita', riformulata al passivo, passa da 26,8 a 99,7.** Non e' cecita'
alle relazioni: e' **sensibilita' alla FORMA in cui la relazione e' espressa**. E R2
**passa su tutte e quattro le celle** (due pacchetti × due porte).
⇒ E `R3` mostra il contrario: l'inversione dell'**esito** («respinto» → «accettato») il
gate la vede benissimo — **g = 1.17**, il punteggio piu' basso di tutto il banco.

📌 **COSA AGGIUNGE ai reperti di @ws1 e @ws4**: loro hanno stabilito **che la classe
esiste** (9 su 10 · la cifra e non la grandezza). Qui si vede **dove passa il confine**:
**la voce passiva**. E vale **sul pacchetto che si installa**, su **entrambe le porte** —
non e' un fatto di `main`.
⚠️ **E un avvertimento sulla lettura**: le celle `wheel/MCP` NON sono prove di cecita' del
giudice — su quel pacchetto il giudice **non viene mai richiesto** (`W5-30`), quindi
ammette tutto. Contarle come «il gate non vede» gonfierebbe il numero: **le celle che
provano qualcosa sono quelle dove il gate gira**, e li' il buco e' **R2**.

REGIME: due pacchetti INSTALLATI (wheel 0.7.1 · `main` 0.7.6), ambiente pulito, store
nuovo per pacchetto, CWD fuori dal repo, un processo per volta.
⚖️ PUNTI DEBOLI: sei claim su una fonte sola; l'inversione di soggetto in italiano e'
marcata dalle preposizioni («di ws3» / «di ws4»), che e' la forma piu' facile — una
lingua senza marca darebbe un altro numero.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-la-classe-delle-relazioni-vale-anche-per-chi-installa.py <dir-con-i-venv>
"""
import json
import os
import subprocess
import sys
import textwrap

FONTE = "Il gate di ws3 ha respinto 12 fatti di ws4 durante il turno di notte."
CASI = [
    ("V1 vero", "Il gate di ws3 ha respinto 12 fatti.", "ammesso"),
    ("V2 vero", "ws4 ha avuto 12 fatti respinti.", "ammesso"),
    ("V3 vero", "Il turno di notte ha visto 12 fatti respinti.", "ammesso"),
    ("R1 soggetto invertito", "Il gate di ws4 ha respinto 12 fatti di ws3.", "fermato"),
    ("R2 soggetto invertito", "ws3 ha avuto 12 fatti respinti dal gate di ws4.", "fermato"),
    ("R3 esito invertito", "Il gate di ws3 ha accettato 12 fatti di ws4.", "fermato"),
]

CLIENT = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
STORE = sys.argv[1]
FONTE = sys.argv[2]
CASI = json.loads(open(sys.argv[3], encoding="utf-8").read())
env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            # RISCALDAMENTO: la PRIMA scrittura con fonte non torna (W5-31..W5-34).
            # Si sacrifica una chiamata, o si misura il blocco invece del giudizio.
            try:
                await asyncio.wait_for(
                    s.call_tool("hippo_remember",
                                {"proposition": "Riscaldamento della sessione.",
                                 "source": FONTE}), 200)
            except Exception:
                pass
            print("WARM|fatto", flush=True)
            for et, claim, _a in CASI:
                try:
                    res = await asyncio.wait_for(
                        s.call_tool("hippo_remember",
                                    {"proposition": claim, "source": FONTE}), 240)
                    d = json.loads("".join(str(getattr(c, "text", "")) for c in (res.content or [])))
                    st = d.get("status")
                    print("R|%s|%s|%s" % (et, "fermato" if st in ("quarantined", "rejected")
                                          else "ammesso", d.get("grounding_score")), flush=True)
                except asyncio.TimeoutError:
                    print("R|%s|TIMEOUT|-" % et, flush=True)
asyncio.run(main())
'''


def ambiente(store):
    e = {k: v for k, v in os.environ.items()
         if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    e["HIPPO_DATA_DIR"] = store
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return e


def versione(venv):
    r = subprocess.run([os.path.join(venv, "Scripts", "pip.exe"), "show", "verimem"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for riga in (r.stdout or "").splitlines():
        if riga.lower().startswith("version:"):
            return riga.split(":", 1)[1].strip()
    return "?"


def via_cli(venv, base, claim):
    # (!) `"cli_%d" % x % 10**8` NON e' quello che sembra: il `%` di formattazione ha
    # la stessa precedenza del modulo, quindi Python calcola `("cli_..." ) % 10**8`
    # e alza TypeError. Il banco moriva in 0.0s, e il mio `2>/dev/null` nascondeva
    # il traceback: sopprimere stderr fa leggere un errore come «finito subito».
    store = os.path.join(base, "cli_%d" % (abs(hash(claim)) % 10**8))
    os.makedirs(store, exist_ok=True)
    r = subprocess.run([os.path.join(venv, "Scripts", "verimem.exe"), "remember", claim,
                        "--source", FONTE], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900,
                       env=ambiente(store), cwd=os.path.dirname(venv))
    out = (r.stdout or "") + (r.stderr or "")
    return "fermato" if "quarantin" in out or "reject" in out else "ammesso"


def via_mcp(venv, base):
    store = os.path.join(base, "mcp_%s" % os.path.basename(venv))
    os.makedirs(store, exist_ok=True)
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    dati = os.path.join(store, "_casi.json")
    with open(dati, "w", encoding="utf-8") as f:
        json.dump(CASI, f)
    env = ambiente(store)
    del env["HIPPO_DATA_DIR"]
    try:
        r = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script,
                            store, FONTE, dati],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=2400, env=env,
                           cwd=os.path.dirname(venv))
        fuori = {}
        for riga in (r.stdout or "").splitlines():
            if riga.startswith("R|"):
                p = riga.split("|")
                fuori[p[1]] = (p[2], p[3] if len(p) > 3 else "-")
        return fuori
    except subprocess.TimeoutExpired:
        return {}


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-con-i-venv>" % sys.argv[0])
        raise SystemExit(2)
    base = sys.argv[1]
    pacchetti = [("wheel", os.path.join(base, "venv_utente")),
                 ("main", os.path.join(base, "venv_main"))]
    print("  fonte: «%s»\n" % FONTE)
    esiti = {}
    for nome, venv in pacchetti:
        if not os.path.exists(os.path.join(venv, "Scripts", "python.exe")):
            print("  🔴 venv assente: %s" % venv)
            return
        for et, claim, _a in CASI:
            esiti[(nome, "CLI", et)] = (via_cli(venv, base, claim), "-")
        for et, val in via_mcp(venv, base).items():
            esiti[(nome, "MCP", et)] = val

    ver = {n: versione(v) for n, v in pacchetti}
    print("  %-24s %-6s %-11s %-11s %-9s %s"
          % ("caso", "porta", "wheel " + ver["wheel"], "main " + ver["main"], "atteso", ""))
    print("  " + "-" * 84)
    sbagliati = []
    for et, _c, atteso in CASI:
        for porta in ("CLI", "MCP"):
            a = esiti.get(("wheel", porta, et), ("?", "-"))[0]
            b, gb = esiti.get(("main", porta, et), ("?", "-"))
            nota = ""
            for chi, val in (("wheel", a), ("main", b)):
                if val not in ("?", atteso):
                    sbagliati.append((chi, porta, et, val, atteso))
                    nota = "  🔴"
            print("  %-24s %-6s %-11s %-11s %-9s%s  g=%s" % (et, porta, a, b, atteso, nota, gb))

    print("\n=== VERDETTO ===")
    rel = [c for c in CASI if c[2] == "fermato"]
    passati = [(chi, p, e) for chi, p, e, v, a in sbagliati if a == "fermato"]
    persi = [(chi, p, e) for chi, p, e, v, a in sbagliati if a == "ammesso"]
    celle = len(rel) * 2 * 2
    print("  celle sulle INVERSIONI: %d (3 casi × 2 porte × 2 pacchetti)" % celle)
    print("  inversioni che PASSANO: %d su %d" % (len(passati), celle))
    if persi:
        print("  ⚠️ e %d celle costano un claim VERO:" % len(persi))
        for chi, p, e in persi:
            print("     %-6s %-5s %s" % (chi, p, e))
    if len(passati) == celle:
        print("  🔴 LA CLASSE VALE ANCHE PER CHI INSTALLA: nessuna porta e nessun")
        print("     pacchetto ferma un'inversione di soggetto o di esito.")
        print("     ⇒ Il reperto di @ws1 e @ws4 non e' un fatto di `main`: e' del prodotto")
        print("        che si scarica, su entrambe le superfici.")
    elif passati:
        print("  🟡 la classe passa in ALCUNE celle:")
        for chi, p, e in passati:
            print("     %-6s %-5s %s" % (chi, p, e))
    else:
        print("  🟢 tutte le inversioni sono fermate su tutte le celle: sul pacchetto")
        print("     la classe NON si riproduce — e allora va capito cosa cambia.")


main()
