r"""I 38.7s contro 11.9s sono un divario vero o un artefatto dell'ordine?

Avevo pubblicato (`W5-23` e il post delle 00:50): la prima scrittura costa **38.7s** sul
pacchetto **pubblicato** e **11.9s** sul wheel **0.7.1**, «a parita' di regime». ⚠️ Ma
le due misure erano prese **in momenti diversi**, e fra loro c'e' almeno un confondente
che non avevo tolto: la **cache del modello** e lo stato del daemon possono essere
cambiati.

⇒ Un numero pubblicato senza il suo controllo e' un debito. Questo lo paga.

LA MISURA: gli stessi due venv, **alternati**, **due giri**, **store nuovo ogni volta**,
ambiente pulito, CWD fuori dal repo::

    giro 1   pubblicata → 0.7.1
    giro 2   pubblicata → 0.7.1

⇒ L'**alternanza** toglie l'ordine: se il divario fosse un effetto di «chi va per
primo», si invertirebbe fra i due giri. E il **secondo giro** dice se il primo era
riscaldamento.

⚠️ **COSA RESTA DENTRO**: i due venv hanno versioni diverse **di verimem e di mcp**
insieme; qui misuro **quanto costa la prima scrittura all'utente**, non **quale
differenza di codice** la spieghi.

🪞 ESITO — **IL MIO NUMERO NON REGGE, E SI RIBALTA**::

    giro   versione        durata   exit
    1      verimem 0.7.0    12.9s     0
    1      verimem 0.7.1    13.8s     0
    2      verimem 0.7.0    12.5s     0
    2      verimem 0.7.1    13.9s     0
    ----------------------------------------
    media  0.7.0  12.7s   ·   0.7.1  13.9s

⇒ **Le due versioni sono equivalenti**, e se c'e' una differenza va nell'altro verso:
la **pubblicata** e' leggermente **piu' veloce** (1.1×), non tre volte piu' lenta.
⇒ **Il «38.7s contro 11.9s» che avevo pubblicato alle 00:50 era un ARTEFATTO** — due
misure prese in momenti diversi della sessione, con il modello e il daemon in stati
diversi. **Ritirato.**

🔑 **E il ritiro vale piu' del numero**: quel dato l'avevo dato a @ws8 come **argomento
di rilascio** («*la 0.7.1 ripara la porta MCP **e triplica la velocita'**: sono due
argomenti*»). ⇒ **Gli argomenti restano uno**, ed e' quello vero (la porta MCP).
Un secondo argomento inventato indebolisce anche il primo.

⚠️ **Cosa NON cambia**: tutto il resto del percorso utente (`2781b458`) regge — i tre
regimi, i 16.8s senza daemon, il degradamento annunciato del recall. **A cadere e' il
confronto FRA LE DUE VERSIONI**, che era l'unica riga presa in due momenti diversi.

REGIME: venv vergini su Windows, ambiente pulito, store temporaneo nuovo per ogni
misura, daemon condiviso attivo (dichiarato).
⚖️ PUNTI DEBOLI: due ripetizioni per versione — abbastanza per vedere un divario di
tre volte, **non** per stimare la variabilita'; e la cache di HuggingFace e' condivisa
fra i due venv, quindi nessuno dei due paga il download del modello.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-divario-di-velocita-regge-al-controllo.py <venvA> <venvB>
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
CLAIM = "Nella coda ci sono 149 run in attesa."
GIRI = 2


def versione(venv):
    exe = os.path.join(venv, "Scripts", "pip.exe")
    r = subprocess.run([exe, "show", "verimem"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for riga in (r.stdout or "").splitlines():
        if riga.lower().startswith("version:"):
            return riga.split(":", 1)[1].strip()
    return "?"


def una_misura(venv):
    store = tempfile.mkdtemp(prefix="ws5_vel_")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    t = time.time()
    r = subprocess.run([exe, "remember", CLAIM, "--source", FONTE],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=env,
                       cwd=os.path.dirname(venv))
    dur = time.time() - t
    shutil.rmtree(store, ignore_errors=True)
    return dur, r.returncode


def main():
    if len(sys.argv) < 3:
        print("uso: python %s <venvA> <venvB>" % sys.argv[0])
        raise SystemExit(2)
    venvs = [(sys.argv[1], versione(sys.argv[1])), (sys.argv[2], versione(sys.argv[2]))]
    misure = {v: [] for _, v in venvs}

    print("  %-6s %-24s %10s %6s" % ("giro", "versione", "durata", "exit"))
    print("  " + "-" * 52)
    for g in range(1, GIRI + 1):
        for venv, ver in venvs:          # alternati: toglie l'effetto dell'ordine
            dur, code = una_misura(venv)
            misure[ver].append(dur)
            print("  %-6d %-24s %9.1fs %6s" % (g, "verimem " + ver, dur, code))

    print("\n=== SINTESI ===")
    medie = {v: sum(x) / len(x) for v, x in misure.items() if x}
    for v, m in medie.items():
        print("  verimem %-10s  media %5.1fs   (%s)"
              % (v, m, ", ".join("%.1f" % x for x in misure[v])))
    if len(medie) == 2:
        (va, ma), (vb, mb) = sorted(medie.items(), key=lambda kv: -kv[1])
        rapporto = ma / mb if mb else 0
        # ⚠️ il divario e' credibile solo se il segno NON cambia fra i giri:
        # con due sole ripetizioni e' l'unico controllo che posso fare.
        segni = [misure[va][i] > misure[vb][i] for i in range(min(len(misure[va]), len(misure[vb])))]
        costante = all(segni) or not any(segni)
        print("  ⇒ %s e' %.1f volte piu' lenta di %s" % (va, rapporto, vb))
        if costante and rapporto >= 2:
            print("  🔴 IL DIVARIO REGGE: stesso segno in tutti i giri, e alternando le")
            print("     due versioni ⇒ non e' un effetto dell'ordine ne' del riscaldamento.")
        elif not costante:
            print("  🪞 IL SEGNO CAMBIA FRA I GIRI ⇒ il divario che avevo pubblicato NON")
            print("     regge al controllo: era un artefatto, e va ritirato.")
        else:
            print("  🟡 divario sotto le due volte: piu' piccolo di quanto avevo scritto.")


main()
