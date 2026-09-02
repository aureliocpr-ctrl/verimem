r"""T4.1, il DENOMINATORE: due giudici insieme costano il doppio, o si spartiscono?

La baseline (`c8830190`) ha dato **957,9 MB per processo**, misurato su un processo **da
solo**. Ma nel mio stesso banco avevo dichiarato il limite: *«l'RSS su Windows include
pagine CONDIVISE fra processi — il costo di 8 processi non e' 8x l'RSS»*.

⇒ Senza questo numero, la predizione di T4.1 («*RSS totale <=1,2 GB contro ~3 GB*») non
ha una base misurata: si confronta con una stima moltiplicativa, non con la realta'.

📌 **PREDIZIONE, scritta PRIMA di misurare**::

    predico che due giudici insieme costino QUASI IL DOPPIO in memoria PRIVATA,
    cioe' che la condivisione NON aiuti sul modello.

**Il perche', falsificabile**: le pagine condivise fra processi Python sono il **codice**
(le DLL, i .pyd di torch), non i **dati**. I pesi di un modello vengono allocati
nell'heap di ciascun processo — sono dati privati, non mappature di file condivise. ⇒ Se
ho ragione, la memoria **privata** di 2 processi ~= 2x quella di 1, e il risparmio di un
servizio condiviso e' **reale e quasi lineare**. ⇒ Se ho torto (le pagine si spartiscono),
il guadagno di T4.1 e' molto minore di quanto il piano assume, e **va ridimensionato
prima di costruire il daemon**.

COME SI MISURA, e perche' due grandezze e non una::

    WorkingSetSize        l'RSS: include pagine CONDIVISE con altri processi
    PrivateUsage          la memoria che quel processo NON spartisce con nessuno

⇒ **E' la seconda a rispondere alla domanda.** Un RSS che raddoppia potrebbe essere due
processi che mappano le stesse DLL; la memoria privata no.

IL DISEGNO — un solo processo, poi due in PARALLELO, stessa macchina::

    ①  UN giudice da solo         privata + RSS dopo il caricamento
    ②  DUE giudici insieme        privata + RSS di ciascuno, nello stesso istante

⚠️ **Due, non otto**: su questa macchina Aurelio sta lavorando e otto giudici
significherebbero ~8 GB. Due bastano a distinguere «raddoppia» da «si spartisce», che e'
la domanda; la forma esatta della curva a 8 e' un'altra misura, e non la faccio.

🟢 ESITO — **la predizione REGGE, e per strada esce un numero che cambia le soglie**::

    regime           processo     RSS (MB)   privata (MB)
    1 giudice              g0        980.6        1552.8
    2 giudici              g0        980.2        1572.4
    2 giudici              g1        979.8        1571.9
    ----------------------------------------------------
    1 giudice                        980.6        1552.8
    2 insieme                       1960.0        3144.3
    fattore sulla PRIVATA                          2.02x

⇒ **Due giudici costano 2,02x uno: la memoria del modello NON si spartisce.** ⇒ La
stima «N x per-processo» del piano e' **corretta**, e il risparmio di un servizio
condiviso e' **quasi lineare**. T4.1 vale quanto promette.

🔑 **E IL NUMERO CHE CAMBIA LE SOGLIE**: la memoria **privata** e' **1552,8 MB**, non
958. ⇒ **L'RSS sottostima il costo vero del 60%.** Sono due grandezze diverse e servono
a due domande diverse::

    RSS       980,6 MB  quanto sta in RAM fisica ora   ->  8 agenti = ~7,8 GB
    privata  1552,8 MB  quanto il sistema deve GARANTIRE ->  8 agenti = ~12,4 GB

⇒ E' la terza cifra diversa per «quanto costa il giudice» in una giornata: **758**
(ereditata, mai trovata fra i miei fatti), **958** (RSS, mia baseline), **1553**
(privata, qui). Le ultime due **non si contraddicono**: misurano cose diverse. ⇒ **Un
numero senza la sua base inganna**, e su questa riga il piano ne aveva scelta una sola.

📌 **Per T4.1**: la predizione «*RSS totale <=1,2 GB contro ~3 GB*» va riscritta
dichiarando **quale** grandezza, e con il riferimento giusto — che per 4 client e'
**~6,2 GB di privata** (4 x 1552,8), non ~3 GB.

⚙️ **Il dettaglio che rende la misura valida**: i due processi si segnalano a vicenda
quando il giudice e' caricato e misurano **solo dopo che entrambi sono pronti**. Senza
quella sincronizzazione il secondo fotograferebbe un istante in cui il primo ha gia'
liberato, e il fattore uscirebbe **piu' basso del vero** — cioe' l'errore andrebbe
proprio nel verso che fa sembrare T4.1 inutile.

REGIME: `main` installato (verimem 0.7.6), ambiente pulito, store temporaneo per
processo, un solo banco per volta, claim RAM dichiarato sul canale.
⚖️ PUNTI DEBOLI: due punti non sono una curva; e la memoria privata su Windows include
l'heap dell'interprete, che qui vale ~16 MB e non cambia il verdetto.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-t41-quanto-costano-due-giudici-insieme.py <venv>
"""
import os
import subprocess
import sys
import tempfile
import textwrap
import time

DENTRO = r'''
import ctypes, ctypes.wintypes as wt, json, os, sys, time

class _PMCEX(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]

def mem():
    """(RSS, privata) in MB. restype dichiarato: senza, lo pseudo-handle -1 viene
    troncato a 32 bit su Windows a 64 e la chiamata torna err=6 (mi e' successo)."""
    c = _PMCEX(); c.cb = ctypes.sizeof(_PMCEX)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMCEX), wt.DWORD]
    fn.restype = wt.BOOL
    if not fn(h, ctypes.byref(c), c.cb):
        raise OSError("GetProcessMemoryInfo err=%d" % ctypes.windll.kernel32.GetLastError())
    return c.WorkingSetSize / 1048576.0, c.PrivateUsage / 1048576.0

ETICHETTA, PRONTO, VIA = sys.argv[1], sys.argv[2], sys.argv[3]
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
from verimem.anti_confab_gate import run_validation_gate
g = run_validation_gate(proposition="Nella coda ci sono 149 run in attesa.",
                        verified_by=None, topic=None, agent=None,
                        source=FONTE, ground_write=True)
open(PRONTO, "w").write("1")            # dico che il giudice e' caricato
while not os.path.exists(VIA):          # aspetto che lo siano ANCHE gli altri
    time.sleep(0.2)
rss, priv = mem()                       # ...e SOLO ALLORA misuro: e' il punto
print("MEM|%s|%.1f|%.1f|%s" % (ETICHETTA, rss, priv,
                               getattr(g, "grounding_score", None)), flush=True)
'''


def avvia(py, script, etichetta, pronto, via, env, cwd):
    return subprocess.Popen([py, "-u", script, etichetta, pronto, via],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8", errors="replace",
                            env=env, cwd=cwd)


def giro(venv, quanti, tmo=1800):
    """Avvia `quanti` giudici e li misura TUTTI nello stesso istante."""
    py = os.path.join(venv, "Scripts", "python.exe")
    base = tempfile.mkdtemp(prefix="ws5_t41_")
    script = os.path.join(base, "_g.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(DENTRO))
    via = os.path.join(base, "VIA")
    proc, pronti = [], []
    for i in range(quanti):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
        env["HIPPO_DATA_DIR"] = os.path.join(base, "store%d" % i)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_file = os.path.join(base, "PRONTO%d" % i)
        pronti.append(p_file)
        proc.append(avvia(py, script, "g%d" % i, p_file, via, env, os.path.dirname(venv)))
    # aspetto che TUTTI abbiano caricato, poi do il via: cosi' la foto e' simultanea
    t0 = time.time()
    while time.time() - t0 < tmo and not all(os.path.exists(x) for x in pronti):
        time.sleep(0.5)
    if not all(os.path.exists(x) for x in pronti):
        for p in proc:
            p.kill()
        return []
    open(via, "w").write("1")
    fuori = []
    for p in proc:
        out, _ = p.communicate(timeout=300)
        for riga in (out or "").splitlines():
            if riga.startswith("MEM|"):
                c = riga.split("|")
                fuori.append((c[1], float(c[2]), float(c[3]), c[4]))
    return fuori


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    if not os.path.exists(os.path.join(venv, "Scripts", "python.exe")):
        print("  🔴 venv assente: %s" % venv)
        return
    print("  predizione: due giudici costano QUASI IL DOPPIO in memoria privata\n")
    print("  %-22s %10s %12s %12s" % ("regime", "processo", "RSS (MB)", "privata (MB)"))
    print("  " + "-" * 60)
    risultati = {}
    for quanti in (1, 2):
        r = giro(venv, quanti)
        if not r:
            print("  🔴 il regime con %d processi non e' arrivato in fondo" % quanti)
            return
        # CONTROLLO: se il giudice non ha girato, i MB non sono del giudice
        if any(x[3] in ("None", "") for x in r):
            print("  ⚠️ grounding None: il giudice NON e' girato ⇒ i MB non sono suoi.")
            return
        risultati[quanti] = r
        for et, rss, priv, g in r:
            print("  %-22s %10s %11.1f %11.1f" % ("%d giudice/i" % quanti, et, rss, priv))

    p1 = risultati[1][0][2]
    p2 = sum(x[2] for x in risultati[2])
    r1 = risultati[1][0][1]
    r2 = sum(x[1] for x in risultati[2])
    print("\n  === IL DENOMINATORE DI T4.1 ===")
    print("  memoria PRIVATA:  1 giudice %7.1f MB   ·   2 insieme %7.1f MB" % (p1, p2))
    print("  RSS:              1 giudice %7.1f MB   ·   2 insieme %7.1f MB" % (r1, r2))
    fattore = p2 / p1 if p1 else 0
    print("  fattore sulla privata: %.2f×   (2,00 = nessuna condivisione)" % fattore)
    print("\n=== LA PREDIZIONE REGGE? ===")
    if fattore >= 1.8:
        print("  🟢 REGGE: due giudici costano %.2f× uno ⇒ la memoria del modello NON si" % fattore)
        print("     spartisce. Il risparmio di un servizio condiviso e' quasi lineare,")
        print("     e la stima «N × per-processo» del piano e' corretta.")
    elif fattore <= 1.3:
        print("  🔴 CADE: due giudici costano solo %.2f× uno ⇒ le pagine SI SPARTISCONO," % fattore)
        print("     e il guadagno di T4.1 e' molto minore di quanto il piano assume.")
        print("     ⇒ Va ridimensionato PRIMA di costruire il daemon.")
    else:
        print("  🟡 fattore %.2f×: condivisione PARZIALE. Il risparmio esiste ma non e'" % fattore)
        print("     quello della stima moltiplicativa — serve la curva, non due punti.")


main()
