r"""Stanotte misuriamo `main`. Chi installa riceve un altro pacchetto: quanto coincide?

Otto istanze hanno prodotto decine di reperti sul gate, **tutti misurati sul repo**.
Ma un utente installa un **pacchetto**, e io ho gia' trovato un caso in cui i due non
si comportano uguale (`W5-30`: sul pacchetto la porta MCP ammette un claim che la sua
fonte smentisce, su `main` no). ⇒ **Quel caso e' isolato o e' una classe?**

LA MISURA, senza il confondente «repo contro installato» — **due PACCHETTI INSTALLATI**::

    venv_utente   verimem 0.7.1   il wheel che verrebbe pubblicato
    venv_main     verimem 0.7.6   `pip install .` da main (SHA dichiarato sotto)

Stessi casi, stesse fonti, store nuovo per misura, ambiente pulito, CWD fuori dal repo.
**Due porte**, perche' il reperto che ha aperto la domanda era una disparita' di porta::

    CLI   verimem remember <claim> --source <fonte>
    MCP   hippo_remember(proposition=..., source=...)   una sessione per pacchetto

I CASI — cinque classi di comportamento del gate, fonti mie, **entrambe le popolazioni**::

    ①  numero VERO           la fonte lo dice          atteso: ammesso
    ②  numero INVENTATO      la fonte dice altro       atteso: fermato
    ③  scambio di grandezza  «completati» per «attesa» atteso: fermato
    ④  fonte TABELLARE       claim vero su tabella     atteso: ammesso
    ⑤  claim di COMPLETAMENTO senza source             atteso: fermato (L1.13)

⇒ ① e ④ sono la **popolazione positiva**: senza di loro un pacchetto che ferma tutto
sembrerebbe perfetto.

ESITO — **3 celle su 10 differiscono, e sono TUTTE sulla porta MCP** (zero sulla CLI)::

    caso                   porta   wheel 0.7.1   main 0.7.6   atteso
    ① numero VERO          CLI     ammesso       ammesso      ammesso
    ① numero VERO          MCP     ammesso       (timeout)    ammesso   🔴 diversi
    ② numero INVENTATO     CLI     fermato       fermato      fermato
    ② numero INVENTATO     MCP     ammesso 🔴     fermato      fermato   🔴 diversi
    ③ scambio grandezza    CLI     ammesso 🔴     ammesso 🔴    fermato
    ③ scambio grandezza    MCP     ammesso 🔴     ammesso 🔴    fermato
    ④ fonte TABELLARE      CLI     fermato 🔴     fermato 🔴    ammesso
    ④ fonte TABELLARE      MCP     ammesso       fermato 🔴    ammesso   🔴 diversi
    ⑤ COMPLETAMENTO        CLI     fermato       fermato      fermato
    ⑤ COMPLETAMENTO        MCP     fermato       fermato      fermato

⚠️ **LA COLONNA «atteso» E' MIA, non del prodotto**: dove il prodotto non la soddisfa
c'e' un **disaccordo fra me e lui**, non automaticamente un difetto. Il dato **solido**
e' il confronto **wheel contro main**, che e' una misura e non un giudizio.

TRE COSE CHE NE ESCONO, in ordine di quanto reggono::

  🔴 **③ passa OVUNQUE — 4 celle su 4.** «2557 run in attesa» quando la fonte dice
     «2557 **completati**, 149 in attesa»: **nessuna versione e nessuna porta lo ferma.**
     E' un difetto **del prodotto**, non del pacchetto — l'unico caso qui che non
     dipende da cosa pubblichi. **Lo scambio di grandezza usa i numeri VERI della
     fonte**, quindi i controlli sui numeri non hanno niente da segnalare.
  🔴 **④ costa un fatto VERO su entrambe le CLI.** «Un test su tre e' fallito» con una
     tabella che mostra 3 test e 1 FAIL viene **quarantinato**. Chi salva l'output di
     `pytest` — cioe' chiunque segua `O3` — paga questo.
  🟡 **② e' il reperto `W5-30`, riconfermato con due pacchetti INSTALLATI**: il wheel
     ammette il falso, `main` lo ferma.

⇒ **La disparita' e' concentrata su UNA porta**: 3 celle diverse su 5 su MCP, **0 su 5
sulla CLI**. Chi misura dalla CLI ottiene lo stesso verdetto sui due pacchetti; chi
misura da MCP no.

⚠️⚠️ **LA CELLA ① E' SUB JUDICE, e finche' non e' chiusa il «3 su 10» non e' definitivo.**
Quel «(timeout)» non e' un verdetto del prodotto: e' **la mia misura che non ha
risposta**. Ricostruito dal journal degli eventi dello store (`events.jsonl`, che a
differenza dello stdout **non e' bufferizzato**)::

    ① SENZA source      risponde in   3.4s   (`audit_tool_call latency_ms=3357`)
    ② CON  source       nessun evento oltre  900s

⇒ Il controllo senza source **torna**, quindi non e' il trasporto ne' l'avvio: e' il
percorso che la **source** attiva. Ma **c'e' un confondente che puo' spiegare tutto e
che sto misurando a parte**: il mio venv e' vergine e **non e' isolato** — la scoperta
del daemon di encode passa da `DISCOVERY_PATH`, **hardcoded** a
`~/.engram/encode_service.json` (`encode_service.py:41`), che **non deriva da
`HIPPO_DATA_DIR`** (mio reperto `fdd6df83`). Quel daemon (pid 18160, vivo, porta che
accetta in 0.00s) lo stanno usando **otto istanze**. ⇒ Il test che puo' falsificarmi e'
la stessa scrittura con `ENGRAM_ENCODE_SERVICE=0`: **se cosi' torna, la causa e' il mio
ambiente e non il prodotto.**

🪞 E qui il mio righello ha sbagliato una quarta volta: per venti minuti ho letto lo
**stdout vuoto** del sottoprocesso come «e' bloccato». Era **bufferizzato** — l'handshake
e la prima scrittura erano gia' avvenuti. **Il journal lo diceva, lo stdout no.**

⚖️ PUNTI DEBOLI dichiarati: cinque casi non sono un censimento dei reperti di stanotte —
sono **cinque classi scelte da me**; le fonti sono mie e brevi; e un verdetto uguale
**non prova** che il codice sia lo stesso, prova che su questo caso si comportano uguale.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-quanto-di-cio-che-misuriamo-vale-per-chi-installa.py <dir-con-i-venv>
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap

TABELLA = ("test                         esito   durata\n"
           "test_gate_ferma_il_falso     PASS    0.42s\n"
           "test_gate_ammette_il_vero    PASS    1.19s\n"
           "test_moat_non_gira_senza     FAIL    0.03s")
CODA = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
        "e 3 run in corso.")

CASI = [
    ("① numero VERO", "Nella coda ci sono 149 run in attesa.", CODA, "ammesso"),
    ("② numero INVENTATO", "Nella coda ci sono 7777 run in attesa.", CODA, "fermato"),
    ("③ scambio grandezza", "Nella coda ci sono 2557 run in attesa.", CODA, "fermato"),
    ("④ fonte TABELLARE", "Un test su tre e' fallito.", TABELLA, "ammesso"),
    ("⑤ COMPLETAMENTO", "Ho verificato tutto e il gate funziona correttamente.", "", "fermato"),
]

CLIENT = r'''
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE = sys.argv[1]
CASI = json.loads(open(sys.argv[2], encoding="utf-8").read())

env = {k: v for k, v in os.environ.items()
       if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
env["HIPPO_DATA_DIR"] = STORE
env["PYTHONDONTWRITEBYTECODE"] = "1"

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 180)
            tl = await s.list_tools()
            scrivi = next((t.name for t in tl.tools if t.name.endswith("remember")), None)
            for etichetta, claim, fonte, _atteso in CASI:
                arg = {"proposition": claim}
                if fonte:
                    arg["source"] = fonte
                try:
                    # (!) call_tool TORNA un errore senza sollevarlo: si legge il contenuto
                    res = await asyncio.wait_for(s.call_tool(scrivi, arg), 300)
                    testo = "".join(str(getattr(c, "text", "")) for c in (res.content or []))
                    d = json.loads(testo)
                    stato = d.get("status")
                    esito = "fermato" if stato in ("quarantined", "rejected") else "ammesso"
                    print("MCP|%s|%s|%s|%s" % (etichetta, esito, stato,
                                               len(d.get("anti_confab_warnings") or [])))
                except Exception as e:
                    print("MCP|%s|errore|%s|0" % (etichetta, type(e).__name__))

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


def via_cli(venv, claim, fonte):
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    store = tempfile.mkdtemp(prefix="ws5_vale_")
    args = [exe, "remember", claim] + (["--source", fonte] if fonte else [])
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900, env=ambiente(store),
                       cwd=os.path.dirname(venv))
    out = (r.stdout or "") + (r.stderr or "")
    return "fermato" if "quarantin" in out or "reject" in out else "ammesso"


def via_mcp(venv):
    py = os.path.join(venv, "Scripts", "python.exe")
    store = tempfile.mkdtemp(prefix="ws5_vale_mcp_")
    script = os.path.join(store, "_c.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(CLIENT))
    dati = os.path.join(store, "_casi.json")
    with open(dati, "w", encoding="utf-8") as f:
        json.dump(CASI, f)
    r = subprocess.run([py, script, store, dati], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800,
                       env=ambiente(store), cwd=os.path.dirname(venv))
    fuori = {}
    for riga in (r.stdout or "").splitlines():
        if riga.startswith("MCP|"):
            p = riga.split("|")
            fuori[p[1]] = p[2]
    return fuori


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-con-i-venv>" % sys.argv[0])
        raise SystemExit(2)
    base = sys.argv[1]
    pacchetti = [("wheel", os.path.join(base, "venv_utente")),
                 ("main", os.path.join(base, "venv_main"))]
    for _n, v in pacchetti:
        if not os.path.exists(os.path.join(base, os.path.basename(v), "Scripts", "python.exe")):
            print("  🔴 venv assente: %s" % v)
            return
    versioni = {n: versione(v) for n, v in pacchetti}
    print("  pacchetti a confronto: %s" % " · ".join("%s=verimem %s" % (n, versioni[n])
                                                     for n, _ in pacchetti))
    print("  (entrambi INSTALLATI: niente confondente repo-contro-pacchetto)\n")

    esiti = {}
    for nome, venv in pacchetti:
        for etichetta, claim, fonte, _a in CASI:
            esiti[(nome, "CLI", etichetta)] = via_cli(venv, claim, fonte)
        for etichetta, val in via_mcp(venv).items():
            esiti[(nome, "MCP", etichetta)] = val

    print("  %-22s %-9s %-11s %-11s %s" % ("caso", "porta", "wheel 0.7.1", "main", "atteso"))
    print("  " + "-" * 78)
    diversi, sbagliati = [], []
    for etichetta, _c, _f, atteso in CASI:
        for porta in ("CLI", "MCP"):
            a = esiti.get(("wheel", porta, etichetta), "?")
            b = esiti.get(("main", porta, etichetta), "?")
            segno = ""
            if a != b:
                segno = "  🔴 DIVERSI"
                diversi.append((etichetta, porta, a, b))
            for chi, val in (("wheel", a), ("main", b)):
                if val != atteso and val != "?":
                    sbagliati.append((chi, porta, etichetta, val, atteso))
            print("  %-22s %-9s %-11s %-11s %s%s" % (etichetta, porta, a, b, atteso, segno))

    print("\n=== VERDETTO ===")
    tot = len(CASI) * 2
    print("  celle confrontate: %d   diverse fra i due pacchetti: %d" % (tot, len(diversi)))
    if diversi:
        # stampa CHI cade, non solo quanti: un conteggio non si riconosce a occhio
        print("  🔴 dove i due pacchetti NON danno lo stesso verdetto:")
        for e, p, a, b in diversi:
            print("     %-22s %-5s  wheel=%-9s main=%s" % (e, p, a, b))
        print("  ⇒ un reperto misurato su main NON si trasferisce automaticamente")
        print("     a chi installa: su queste celle il pacchetto si comporta diverso.")
    else:
        print("  🟢 i due pacchetti concordano su tutte le celle di questo campione")
        print("     ⇒ su queste cinque classi, misurare main dice il vero anche per l'utente.")
    if sbagliati:
        print("\n  ⚠️ e dove un pacchetto sbaglia rispetto all'ATTESO:")
        for chi, p, e, val, att in sbagliati:
            print("     %-6s %-5s %-22s %s (atteso %s)" % (chi, p, e, val, att))


main()
