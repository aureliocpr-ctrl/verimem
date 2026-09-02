r"""LA PROCEDURA: verificare da utente vero un pacchetto appena pubblicato. Un comando.

Esegue la direttiva di Aurelio (22:04 del 01/09, verbatim via @ws4): «*quando pubblicate
qualcosa voglio che fate backup del nostro attuale stack, disinstallate verimem e
installate come un normale utente se serve a provare che funziona tutto*».

Stanotte quella verifica l'ho fatta a mano su tre venv, e **ogni passo mi ha morso una
volta**. Questo script e' quei morsi messi in fila, cosi' al prossimo publish si lancia
e basta::

    python ws5-verifica-da-utente-dopo-un-publish.py <dir-lavoro> [versione]

I SEI PASSI, e perche' ognuno c'e'::

    ①  venv NUOVO                  altrimenti non e' un'installazione, e' la tua
    ②  `cd` FUORI dal repo         dentro, Python importa il SORGENTE (`sys.path[0]`
                                   e' la CWD) e misuri il repo credendo il pacchetto
    ③  ambiente PULITO             la nostra sessione esporta 9 variabili `HIPPO_*`
                                   / `ENGRAM_*`; una (`HIPPO_ENCODE_DELEGATE_ONLY=1`)
                                   fa CRASHARE `remember` con un traceback
    ④  `pip install verimem`       senza versione: e' quello che scrive un utente
    ⑤  il percorso completo        --help · doctor · remember · recall · stats · mcp
    ⑥  il REGIME dichiarato        daemon condiviso acceso o spento cambia i tempi
                                   di un caricamento del modello (~22s)

⚠️ **COSA QUESTO SCRIPT NON FA, e va detto**: non disinstalla verimem dallo stack
principale. Aurelio lo chiede ed e' la prova piu' forte — ma su questa macchina lo stack
e' condiviso da otto istanze che lo stanno usando: **quel passo va fatto quando sono
ferme**, ed e' l'unico pezzo della direttiva che resta scoperto.

⚠️ E **non** giudica la qualita' delle risposte: verifica che i comandi partano, che una
scrittura sia ammessa e che la lettura la ritrovi. E' uno **smoke**, non un banco.

✅ ESEGUITA DAVVERO — **uno script di procedura mai eseguito non e' una procedura**::

    pip install verimem              exit 0 in 415s
    installati                       verimem 0.7.0 · mcp 2.1.1
    REGIME                           daemon acceso · store nuovo · cwd fuori dal repo

    passo               exit    durata   esito letto
    --help                0      3.1s
    doctor                1      5.7s
    remember (vero)       0     40.6s    ammesso        ✔
    remember (falso)      0     25.2s    quarantinato   ✔
    recall                0      1.8s    trova il fatto ✔
    stats                 0      1.8s
    mcp (server)          1      4.2s    🔴 NON PARTE

    VERDETTO: il vero e' ammesso ✔ · il falso e' quarantinato ✔
              🔴 PASSI ROTTI: mcp (server)

🔑 **Ha riprodotto il reperto della porta MCP da sola**, partendo da zero e senza
sapere cosa cercare: e' la prova che la procedura **funziona come procedura**, non solo
come racconto di cio' che avevo gia' trovato a mano.

✅ **E il verdetto e' della forma giusta**: non dice «funziona» ne' «e' rotto» — dice
**quale passo cade**. Chi la esegue dopo un publish sa cosa scrivere nelle note.

📌 **Due numeri per chi legge**: l'installazione costa **7 minuti** (415s, con la cache
di pip gia' calda) e la **prima scrittura decine di secondi** — non il «2-second
quickstart» dell'help.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-verifica-da-utente-dopo-un-publish.py <dir> [versione]
"""
import os
import subprocess
import sys
import time

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
VERO = "Nella coda ci sono 149 run in attesa."
FALSO = "Nella coda ci sono 7777 run in attesa."


def pulisci(env_extra=None, home=None):
    """L'ambiente di un utente: senza le variabili che la nostra sessione esporta.

    ⑦ E con la HOME ISOLATA quando `home` e' dato. Non e' zelo: la scoperta del daemon
    di encode passa da `DISCOVERY_PATH`, **hardcoded** a `~/.engram/encode_service.json`
    (`encode_service.py:41`), che NON deriva da `HIPPO_DATA_DIR` (reperto `fdd6df83`).
    ⇒ Senza HOME pulita, un venv «vergine» parla comunque col daemon dello stack
    principale, e non stai misurando l'utente: stai misurando noi.
    """
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if home:
        env["HOME"] = home
        env["USERPROFILE"] = home
    env.update(env_extra or {})
    return env


SESSIONE_MCP = r'''
import asyncio, json, os, sys, time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

STORE = sys.argv[1]
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
env = dict(os.environ); env["HIPPO_DATA_DIR"] = STORE

async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "verimem.mcp_server"], env=env)
    t0 = time.time()
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            print("MCP|initialize|ok|%.1fs" % (time.time() - t0), flush=True)
            tl = await asyncio.wait_for(s.list_tools(), 120)
            print("MCP|tools/list|%d strumenti|-" % len(tl.tools), flush=True)
            # la PRIMA chiamata e' sacrificale: su questa porta non torna (W5-31..34)
            try:
                await asyncio.wait_for(s.call_tool("hippo_remember",
                    {"proposition": "Riscaldamento.", "source": FONTE}), 120)
            except Exception:
                pass
            # il claim FALSO: la fonte dice 3, il claim dice 7777
            t = time.time()
            try:
                res = await asyncio.wait_for(s.call_tool("hippo_remember",
                    {"proposition": "Nella coda ci sono 7777 run in corso.",
                     "source": FONTE}), 300)
                d = json.loads("".join(str(getattr(c, "text", "")) for c in (res.content or [])))
                print("MCP|write falso|status=%s grounding=%s|%.1fs"
                      % (d.get("status"), d.get("grounding_score"), time.time() - t), flush=True)
            except asyncio.TimeoutError:
                print("MCP|write falso|TIMEOUT|%.1fs" % (time.time() - t), flush=True)

asyncio.run(main())
'''


def esegui(exe, args, env, cwd, tmo=600, stdin_vuoto=True):
    t = time.time()
    try:
        r = subprocess.run([exe] + args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=tmo,
                           env=env, cwd=cwd,
                           stdin=subprocess.DEVNULL if stdin_vuoto else None)
        return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t
    except subprocess.TimeoutExpired:
        # ⚠️ per un SERVER il timeout e' un SUCCESSO: significa che era in ascolto
        return "TIMEOUT", "", time.time() - t


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <dir-lavoro> [versione]" % sys.argv[0])
        raise SystemExit(2)
    base = os.path.abspath(sys.argv[1])
    spec = "verimem==" + sys.argv[2] if len(sys.argv) > 2 else "verimem"
    venv = os.path.join(base, "venv")
    store = os.path.join(base, "store")
    neutra = os.path.join(base, "cwd")          # ② mai dentro il repo
    for d in (base, store, neutra):
        os.makedirs(d, exist_ok=True)

    print("① creo un venv NUOVO in %s" % venv)
    subprocess.run([sys.executable, "-m", "venv", venv], check=True,
                   capture_output=True)
    pip = os.path.join(venv, "Scripts", "pip.exe")
    exe = os.path.join(venv, "Scripts", "verimem.exe")

    print("④ pip install %s   (puo' volere minuti: tira torch)" % spec)
    t = time.time()
    r = subprocess.run([pip, "install", spec], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=3600)
    print("   exit %s in %.0fs" % (r.returncode, time.time() - t))
    if r.returncode != 0:
        print("   🔴 INSTALLAZIONE FALLITA — un utente si ferma qui.")
        print("   %s" % (r.stderr or "")[-300:])
        return
    if not os.path.exists(exe):
        print("   🔴 `verimem` non e' sul PATH del venv: l'utente installa e non trova")
        print("      il comando.")
        return

    ver = ""
    out = subprocess.run([pip, "show", "verimem"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    for riga in out.splitlines():
        if riga.lower().startswith("version:"):
            ver = riga.split(":", 1)[1].strip()
    mcp = subprocess.run([pip, "show", "mcp"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    vmcp = ""
    for riga in mcp.splitlines():
        if riga.lower().startswith("version:"):
            vmcp = riga.split(":", 1)[1].strip()
    print("   installati: verimem %s · mcp %s" % (ver, vmcp))

    # ⑦ HOME isolata: senza, il venv «vergine» parla col daemon dello stack principale
    home = os.path.join(base, "home")
    os.makedirs(home, exist_ok=True)
    env = pulisci({"HIPPO_DATA_DIR": store}, home=home)     # ③ + ⑦

    # l'import da Python e le versioni COME LE VEDE il pacchetto installato, non pip
    print("⑤ import e versioni dal PACCHETTO (non da `pip show`)")
    codice = ("import verimem, mcp, sys;"
              "print('verimem', getattr(verimem,'__version__','?'));"
              "print('mcp', getattr(mcp,'__version__','?'));"
              "print('da', verimem.__file__)")
    t = time.time()
    r_imp = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-c", codice],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300, env=env, cwd=neutra)
    print("   exit %s in %.1fs" % (r_imp.returncode, time.time() - t))
    for riga in (r_imp.stdout or "").splitlines():
        print("   %s" % riga)
    if r_imp.returncode != 0:
        for riga in [x for x in (r_imp.stderr or "").splitlines() if x.strip()][-3:]:
            print("   🔴 %s" % riga[:110])

    daemon = "acceso (default)" if env.get("ENGRAM_ENCODE_SERVICE", "1") != "0" else "spento"
    print("\n⑥ REGIME: daemon condiviso %s · store nuovo · HOME isolata · cwd %s\n"
          % (daemon, os.path.basename(neutra)))

    passi = [
        ("--help", ["--help"], 60),
        ("doctor", ["doctor"], 300),
        ("remember (vero)", ["remember", VERO, "--source", FONTE], 900),
        ("remember (falso)", ["remember", FALSO, "--source", FONTE], 900),
        ("recall", ["recall", "quanti run sono in attesa?"], 900),
        ("stats", ["stats"], 300),
        ("mcp (server)", ["mcp"], 25),
    ]
    esiti = {}
    print("  %-20s %-9s %8s  %s" % ("passo", "exit", "durata", "esito letto"))
    print("  " + "-" * 86)
    for nome, args, tmo in passi:
        code, out, dur = esegui(exe, args, env, neutra, tmo)
        letto = ""
        if nome.startswith("remember"):
            letto = ("quarantinato" if "quarantined" in out
                     else "ammesso" if "admitted" in out else "?")
        elif nome == "recall":
            letto = "trova il fatto" if VERO[:28] in out else "🔴 NON lo trova"
        elif nome == "mcp (server)":
            # per un server il TIMEOUT e' il successo: era in ascolto
            letto = ("🔴 NON PARTE" if "Traceback" in out or "Error" in out
                     else "parte (timeout = in ascolto)")
        elif "Traceback" in out:
            letto = "🔴 traceback"
        esiti[nome] = (code, letto)
        print("  %-20s %-9s %7.1fs  %s" % (nome, code, dur, letto))

    # ⑧ LA PORTA MCP DA DENTRO: `verimem mcp` dice solo se il processo PARTE.
    # Una sessione vera (initialize + tools/list + una scrittura) dice se SERVE.
    print("\n⑧ sessione MCP via stdio (initialize + tools/list + un claim FALSO)")
    script = os.path.join(base, "_mcp.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(SESSIONE_MCP)
    t = time.time()
    r_mcp = subprocess.run([os.path.join(venv, "Scripts", "python.exe"), "-u", script, store],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800, env=env, cwd=neutra)
    print("   exit %s in %.0fs" % (r_mcp.returncode, time.time() - t))
    righe_mcp = [x for x in (r_mcp.stdout or "").splitlines() if x.startswith("MCP|")]
    for x in righe_mcp:
        p = x.split("|")
        print("   %-14s %-34s %s" % (p[1], p[2], p[3] if len(p) > 3 else ""))
    if not righe_mcp:
        print("   🔴 la sessione MCP non ha prodotto nessuna riga")
        for x in [y for y in (r_mcp.stderr or "").splitlines() if y.strip()][-4:]:
            print("      %s" % x[:110])
    giudizio_mcp = next((x.split("|")[2] for x in righe_mcp if "write falso" in x), "")

    print("\n=== VERDETTO ===")
    rotti = [n for n, (c, l) in esiti.items() if "🔴" in l]
    vero_ok = esiti.get("remember (vero)", ("", ""))[1] == "ammesso"
    falso_ok = esiti.get("remember (falso)", ("", ""))[1] == "quarantinato"
    print("  il claim VERO e' ammesso:        %s" % ("SI ✔" if vero_ok else "NO 🔴"))
    print("  il claim FALSO e' quarantinato:  %s" % ("SI ✔" if falso_ok else "NO 🔴"))
    if rotti:
        print("  🔴 PASSI ROTTI: %s" % ", ".join(rotti))
        print("  ⇒ NON dichiarare «funziona tutto»: dire QUALE passo cade.")
    elif vero_ok and falso_ok:
        print("  🟢 lo smoke da utente PASSA: si installa, scrive, distingue, rilegge,")
        print("     e il server MCP parte.")
    else:
        print("  🟡 i comandi partono ma il gate non distingue come dovrebbe.")
    # il confronto che conta: la CLI e la porta MCP danno lo STESSO verdetto sul falso?
    cli_falso = esiti.get("remember (falso)", ("", ""))[1]
    print("\n  --- le DUE PORTE sullo stesso claim falso ---")
    print("  CLI: %-14s   MCP: %s" % (cli_falso or "?", giudizio_mcp or "?"))
    if cli_falso == "quarantinato" and giudizio_mcp and "quarantined" not in giudizio_mcp:
        print("  🔴 LE DUE PORTE NON CONCORDANO sul pacchetto PUBBLICATO: la CLI ferma il")
        print("     falso, MCP no. E' `W5-30` misurato sul wheel, ora sul servito da PyPI.")
    elif cli_falso == "quarantinato" and "quarantined" in (giudizio_mcp or ""):
        print("  🟢 entrambe le porte fermano il falso: la disparita' di `W5-30` NON si")
        print("     riproduce su questo pacchetto.")

    print("\n  ⚠️ NON coperto: la disinstallazione dallo stack principale (fermerebbe le")
    print("     istanze che lavorano). E' l'unico pezzo della direttiva che resta a mano.")


main()
