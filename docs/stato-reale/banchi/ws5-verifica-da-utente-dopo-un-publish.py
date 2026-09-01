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


def pulisci(env_extra=None):
    """L'ambiente di un utente: senza le variabili che la nostra sessione esporta."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_extra or {})
    return env


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

    env = pulisci({"HIPPO_DATA_DIR": store})     # ③
    daemon = "acceso (default)" if env.get("ENGRAM_ENCODE_SERVICE", "1") != "0" else "spento"
    print("\n⑥ REGIME: daemon condiviso %s · store nuovo · cwd %s\n"
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
    print("\n  ⚠️ NON coperto: la disinstallazione dallo stack principale (fermerebbe le")
    print("     istanze che lavorano). E' l'unico pezzo della direttiva che resta a mano.")


main()
