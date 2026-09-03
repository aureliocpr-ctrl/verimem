r"""Il pool del giudice: 1, 2 e 4 worker con 8 client. Il p95 scende sotto il secondo?

Il daemon con UN giudice e 8 client da' **p95 1,388s** (`481a2eb3`) — la coda e' reale:
il p50 e' sei volte il giudizio solitario. @lead-audit fissa il bersaglio: **p95 <1s**.

⚠️ **«POOL» E' AMBIGUO, E LA DIFFERENZA COSTA GIGABYTE**::

    pool A  il LOCK viene tolto: N thread chiamano lo STESSO scorer
            memoria: invariata (una copia del modello)
    pool B  N istanze separate del giudice, una per worker
            memoria: N x 640 MB del modello

⇒ Questo banco misura **A**, che e' quello che non costa nulla in memoria. Se A basta,
B non serve; se A non basta, il costo di B e' il prezzo del bersaglio, e va detto.

📌 **PREDIZIONE, scritta prima — e NON e' ottimista**::

    memoria    invariata o quasi (una sola copia del modello)
    p95        NON scende sotto 1s con A, e migliora poco (meno del 40%)

**Il perche', falsificabile**: `torch` parallelizza gia' l'inferenza sui core, e il GIL
limita cio' che i thread Python aggiungono sopra. Togliere il lock permette a piu'
richieste di entrare insieme nello scorer, ma non moltiplica la CPU disponibile: se il
giudizio e' CPU-bound e torch usa gia' i core, il tempo TOTALE per 80 giudizi non
cambia — cambia solo come si distribuisce l'attesa. ⇒ Predico p95 fra 0,9 e 1,3s con 2
worker e **nessun ulteriore guadagno** a 4, perche' i core finiscono.
⇒ Se mi sbaglio e A porta il p95 a 0,4s, il collo di bottiglia era il lock e non la CPU:
**e' l'esito che mi piacerebbe, ed e' quello che credo di meno.**

⚠️ **E c'e' un controllo che devo tenere**: se il p95 scende ma il numero di giudizi
completati per secondo NON sale, non ho migliorato niente — ho solo spalmato l'attesa.
⇒ Si misura anche il **throughput** (giudizi/s complessivi), non solo i percentili.

🔴🟢 ESITO DEL 02/09 — **RITIRATO IL 03/09, ERA DI UNA SOLA ESECUZIONE SU MACCHINA
CARICA**. Diceva: «2 worker dimezza il p95 (-47%), 4 PEGGIORA perche' i core finiscono,
bersaglio <1s mancato». Le tre ripetizioni del 03/09 a macchina quieta lo ribaltano::

    (02/09, 1 esecuzione)   1: p95 2,664s   2: p95 1,404s   4: p95 1,809s
    (03/09, 3 ripetizioni)  1: p95 1,932s   2: p95 1,436s   4: p95 0,801s   <- mediane

🟢 ESITO P1 — **VINCE 4, IL BERSAGLIO <1s E' CENTRATO, E NON E' L'ORDINE**::

    worker    p95 med    p95 min    p95 max     range    posizioni   giudizi/s
    1          1,932s     1,924s     1,994s    0,070s    1, 3, 3       4,1-5,2
    2          1,436s     1,232s     1,645s    0,413s    2, 2, 1       6,3-7,2
    4          0,801s     0,720s     0,809s    0,089s    3, 1, 2      10,3-11,2

    daemon RSS 1399,9 -> 1432,7 MB   (+33 MB da 1 a 4 worker)
    tutte le configurazioni: 80/80 giudicate, in tutte e tre le ripetizioni

✅ **P1.d REGGE**: differenza fra le mediane 0,496s > range piu' largo 0,413s.
🟠 **P1.a META' REGGE E META' CADE**, e vanno lette separate:
   REGGE la parte che contava — lo stesso braccio vince in posizione 3, 1 e 2, quindi
   **NON e' l'effetto d'ordine a decidere**, che era il sospetto depositato in P1;
   CADE la predizione — atteso 2, vince **4**.
🟡 **P1.b**: rapporto p95(1)/p95(2) = 1,56 / 1,21 / 1,35, sotto la forchetta 1,5-2,2
   ma sopra 1,15. Il guadagno di 2 su 1 c'e', l'entita' predetta no.
🔴 **P1.c FALSIFICATA**: predicevo «4 resta peggiore di 2 in tutte e tre». Vince tutte
   e tre. «I core finiscono» era la spiegazione di un dato che non esisteva.
🔴 **P1.f FALSIFICATA, ed e' la notizia**: predicevo «il p95 non scende sotto 1s nemmeno
   a macchina quieta». **0,801s.** Il bersaglio fissato da @lead-audit e' raggiunto dal
   pool A — una sola copia del modello, +33 MB. Il pool B non serve.

⚠️ **PERCHE' IL 02/09 DICEVA IL CONTRARIO**: non e' cambiato il codice, e' cambiata la
macchina. Quella misura fu presa mentre altre istanze giravano; questa con RAM libera
11,3 GB su 31,3 e CPU al 4%, verificate a mano prima di partire. Il p95 a 1 worker passa
da 2,664s a 1,932s fra le due, e a 4 worker il crollo e' molto piu' grande: **il carico
non penalizza i bracci in modo uguale**, e proprio il braccio piu' parallelo e' quello
che una macchina satura punisce di piu'. ⇒ Un banco di prestazioni senza il carico
registrato accanto non e' impreciso: misura un esperimento diverso ogni volta.
⇒ Da qui il criterio d'ingresso: il banco RIFIUTA di partire sotto 8 GB liberi o sopra
il 50% di CPU.

⚠️ **E IL CRITERIO D'INGRESSO NON HA FUNZIONATO IN QUESTA ESECUZIONE**: PowerShell su
locale italiana stampa «11,38» e `float()` ha sollevato, quindi il banco ha dichiarato
«carico NON MISURABILE» ed e' partito lo stesso — il presidio anti-silenzio ha retto, il
criterio no. La condizione era comunque buona (misurata a mano). Curato: la virgola si
traduce. Il numero riportato sopra viene dalla misura manuale, non dal banco.

⚠️ **E IL VERDETTO STAMPO' «✅ P1.a REGGE»**, che era falso: guardava se il vincitore
fosse COSTANTE, non se fosse quello ATTESO. Curato, e il caso E del banco che prova il
verdetto ora lo copre — non c'era perche' nei miei casi finti il vincitore costante era
sempre 2, e le due proprieta' non si separavano mai.

⇒ **RACCOMANDAZIONE per la 0.8.0: pool a 4 worker**, non 2. p95 0,801s (sotto il
bersaglio), throughput 10,3-11,2 giudizi/s contro 4,1-5,2, e +33 MB. Resta aperto se
oltre 4 si continui a guadagnare: **non e' stato misurato** e su questa macchina (20
core logici) 8 varrebbe la prova.

REGIME: `main` installato (0.7.6), ambiente pulito (filtro DENTRO lo script), 8 client
veri che importano `mcp_server`, store temporaneo per client, RAM verificata prima.
⚖️ PUNTI DEBOLI: una macchina sola; il pool A e' un prototipo (nessuna gestione di
saturazione o back-pressure); e 80 giudizi non sono un carico di produzione.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-il-pool-del-giudice-porta-il-p95-sotto-il-secondo.py <venv> [n_client] [n_giudizi] [ripetizioni]
  (ripetizioni=1 e' il banco del 02/09; =3 esegue il protocollo P1 con l'ordine alternato)
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time

DAEMON = r'''
import ctypes, ctypes.wintypes as wt, json, socket, sys, threading

class _P(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("pf", wt.DWORD)] + [
        (n, ctypes.c_size_t) for n in
        ("pk", "ws", "qpp", "qp", "qpnp", "qnp", "pfu", "ppfu", "priv")]

def mem():
    c = _P(); c.cb = ctypes.sizeof(_P)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_P), wt.DWORD]; fn.restype = wt.BOOL
    fn(h, ctypes.byref(c), c.cb)
    return c.ws / 1048576.0, c.priv / 1048576.0

PORTA_FILE, WORKER = sys.argv[1], int(sys.argv[2])
from verimem.anti_confab_gate import run_validation_gate
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
run_validation_gate(proposition="Riscaldamento.", verified_by=None, topic=None,
                    agent=None, source=FONTE, ground_write=True)

# IL POOL: `WORKER` permessi in volo insieme. Con 1 e' il lock di prima; con N>1
# piu' richieste entrano nello STESSO scorer (una copia sola del modello).
sem = threading.Semaphore(WORKER)

def servi(conn):
    try:
        d = b""
        while not d.endswith(b"\n"):
            p = conn.recv(65536)
            if not p:
                return
            d += p
        req = json.loads(d.decode("utf-8"))
        if req.get("op") == "mem":
            r, pr = mem()
            conn.sendall((json.dumps({"rss": r, "priv": pr}) + "\n").encode())
            return
        with sem:
            g = run_validation_gate(proposition=req["claim"], verified_by=None,
                                    topic=None, agent=None, source=req["fonte"],
                                    ground_write=True)
        conn.sendall((json.dumps({"g": getattr(g, "grounding_score", None)}) + "\n").encode())
    except Exception as e:
        try:
            conn.sendall((json.dumps({"errore": str(e)[:60]}) + "\n").encode())
        except Exception:
            pass
    finally:
        conn.close()

s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(128)
open(PORTA_FILE, "w").write(str(s.getsockname()[1]))
while True:
    c, _ = s.accept()
    threading.Thread(target=servi, args=(c,), daemon=True).start()
'''

CLIENT = r'''
import json, os, socket, sys, time
PORTA, N, ET, VIA = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
import verimem.mcp_server  # noqa: F401  (un client MCP vero)
while not os.path.exists(VIA):
    time.sleep(0.05)
lat, ok = [], 0
t_start = time.time()
for i in range(N):
    t = time.time()
    try:
        s = socket.create_connection(("127.0.0.1", PORTA), timeout=180)
        s.sendall((json.dumps({"claim": "Nella coda ci sono %d run in attesa." % (149 + i),
                               "fonte": FONTE}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            p = s.recv(65536)
            if not p:
                break
            buf += p
        s.close()
        if json.loads(buf.decode()).get("g") is not None:
            ok += 1
    except Exception:
        pass
    lat.append(time.time() - t)
print("CL|%s|%s|%d|%.3f" % (ET, json.dumps(lat), ok, time.time() - t_start), flush=True)
'''


def pct(v, q):
    if not v:
        return 0.0
    x = sorted(v)
    return x[min(len(x) - 1, int(round((len(x) - 1) * q)))]


def un_giro(py, venv, worker, nclient, ngiud):
    base = tempfile.mkdtemp(prefix="ws5_pool%d_" % worker)
    fd, fc = os.path.join(base, "_d.py"), os.path.join(base, "_c.py")
    for f, t in ((fd, DAEMON), (fc, CLIENT)):
        with open(f, "w", encoding="utf-8") as h:
            h.write(textwrap.dedent(t))

    def amb(store):
        e = {k: v for k, v in os.environ.items()
             if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
        e["HIPPO_DATA_DIR"] = store
        e["PYTHONDONTWRITEBYTECODE"] = "1"
        return e

    pf = os.path.join(base, "PORTA")
    t0 = time.time()
    d = subprocess.Popen([py, "-u", fd, pf, str(worker)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=amb(os.path.join(base, "d")),
                         cwd=os.path.dirname(venv))
    while not os.path.exists(pf) and time.time() - t0 < 900:
        time.sleep(0.3)
    if not os.path.exists(pf):
        d.kill()
        return None
    porta = int(open(pf).read().strip())
    via = os.path.join(base, "VIA")
    proc = [subprocess.Popen([py, "-u", fc, str(porta), str(ngiud), "c%d" % i, via],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, encoding="utf-8", errors="replace",
                             env=amb(os.path.join(base, "c%d" % i)),
                             cwd=os.path.dirname(venv))
            for i in range(nclient)]
    time.sleep(8.0)
    t_via = time.time()
    open(via, "w").write("1")
    tutte, ok = [], 0
    for p in proc:
        out, _ = p.communicate(timeout=3600)
        for riga in (out or "").splitlines():
            if riga.startswith("CL|"):
                _, _et, lat_j, k, _dur = riga.split("|")
                tutte.extend(json.loads(lat_j))
                ok += int(k)
    durata_tot = time.time() - t_via
    s = socket.create_connection(("127.0.0.1", porta), timeout=60)
    s.sendall(b'{"op":"mem"}\n')
    buf = b""
    while not buf.endswith(b"\n"):
        buf += s.recv(65536)
    s.close()
    m = json.loads(buf.decode())
    d.kill()
    return {"worker": worker, "lat": tutte, "ok": ok, "rss": m["rss"],
            "priv": m["priv"], "durata": durata_tot}


# Gli ordini delle ripetizioni per il protocollo P1. NON sono tre permutazioni a caso:
# ogni braccio deve girare in una posizione DIVERSA fra le tre ripetizioni, altrimenti
# «posizione» ed «effetto del pool» restano confusi esattamente come prima.
#
#     ripetizione 1:  1 2 4      il braccio 1 gira 1a, 3a, 3a
#     ripetizione 2:  4 2 1      il braccio 2 gira 2a, 2a, 1a   <- l'unico fisso in mezzo
#     ripetizione 3:  2 4 1      il braccio 4 gira 3a, 1a, 2a
#
# ⚠️ Il braccio «2» capita due volte in seconda posizione: e' il limite di tre sole
# ripetizioni su tre bracci, e va DETTO invece di lasciarlo credere bilanciato. Se P1.a
# regge, questo limite non morde; se «2» vincesse sempre e solo in seconda posizione,
# servirebbe una quarta ripetizione con 2 in prima o in terza per separarli davvero.
ORDINI = [(1, 2, 4), (4, 2, 1), (2, 4, 1)]


def carico_macchina():
    """RAM libera (GB), CPU (%), numero di processi python e loro RSS totale (GB).

    Via PowerShell perche' `psutil` non e' fra le dipendenze del prodotto e un banco
    non deve chiedere di installare nulla per poter misurare.
    """
    ps = (
        "$p=Get-Process python,python3,pythonw -ErrorAction SilentlyContinue;"
        "$o=Get-CimInstance Win32_OperatingSystem;"
        "$c=(Get-CimInstance Win32_Processor|Measure-Object -Property LoadPercentage"
        " -Average).Average;"
        "'{0} {1} {2} {3}' -f [math]::Round($o.FreePhysicalMemory/1MB,2),$c,"
        "@($p).Count,[math]::Round((($p|Measure-Object WorkingSet64 -Sum).Sum)/1GB,2)"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        libera, cpu, n, rss = r.stdout.split()
        # ⚠️ LA VIRGOLA. PowerShell formatta secondo la LOCALE della macchina: su una
        # italiana stampa «11,38», e `float()` solleva. Il 03/09 alle 20:27 questo ha
        # spento il criterio d'ingresso al primo giro vero del banco — che e' partito
        # dichiarando «carico NON MISURABILE», quindi il presidio anti-silenzio ha
        # retto, ma il criterio no. E' la stessa classe gia' pagata dal gate sui numeri
        # italiani: chi formatta e chi legge non parlano la stessa lingua.
        virgola = str.maketrans({",": "."})
        return (float(libera.translate(virgola)),
                int(float(cpu.translate(virgola))),
                int(n),
                float(rss.translate(virgola)))
    except Exception as e:
        # ⚠️ NON si finge un carico basso quando non lo si sa misurare: si dichiara.
        # Restituire (99, 0, ...) farebbe passare il criterio d'ingresso in silenzio.
        print("  ⚠️ carico NON MISURABILE (%s): il criterio d'ingresso non puo' "
              "decidere e il banco parte comunque — dillo nella cella." % str(e)[:60])
        return 99.0, 0, 0, 0.0


def mediana(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def verdetto_p1(esiti, nrip):
    """Il verdetto del protocollo P1 (docs/stato-reale/ws5-P1-predizione-pool-ripetibile.md).

    ⚠️ Qui NON si stampa un numero solo per configurazione. Il difetto che questo blocco
    esiste per non ripetere e' proprio quello: il 02/09 ho consegnato «2 worker, -47%»
    da UNA esecuzione, in un banco che nello stesso respiro dichiarava una varianza del
    92% sul valore assoluto. Un rapporto misurato una volta non e' piu' solido di un
    valore misurato una volta.
    """
    per_worker = {}
    for r in esiti:
        per_worker.setdefault(r["worker"], []).append(r)

    print("\n" + "=" * 78)
    print("=== P1 — IL VERDETTO SU %d RIPETIZIONI ===" % nrip)
    print("  %-8s %10s %10s %10s %10s   %s"
          % ("worker", "p95 med", "p95 min", "p95 max", "range", "posizioni"))
    print("  " + "-" * 74)
    med = {}
    rng = {}
    for w in sorted(per_worker):
        p95s = [pct(r["lat"], .95) for r in per_worker[w]]
        med[w] = mediana(p95s)
        rng[w] = max(p95s) - min(p95s)
        print("  %-8d %9.3fs %9.3fs %9.3fs %9.3fs   %s"
              % (w, med[w], min(p95s), max(p95s), rng[w],
                 ", ".join(str(r["posizione"]) for r in per_worker[w])))

    print("\n  --- P1.a: l'ORDINE cambia il verdetto? ---")
    vincitori = []
    for rip in range(1, nrip + 1):
        della_rip = [r for r in esiti if r["ripetizione"] == rip]
        if not della_rip:
            continue
        v = min(della_rip, key=lambda r: pct(r["lat"], .95))
        vincitori.append(v["worker"])
        print("     ripetizione %d: vince %d worker (girava in posizione %d)"
              % (rip, v["worker"], v["posizione"]))
    # ⚠️ DUE DOMANDE, NON UNA — e il 03/09 alle 20:36 questo blocco ne ha risposta una
    # sola, stampando «P1.a REGGE» mentre la predizione (2 vince) era falsificata: a
    # vincere era 4. Il codice guardava solo se il vincitore fosse COSTANTE. Costante e
    # ATTESO sono due cose diverse, e la seconda e' quella che era stata predetta.
    # Il mio banco di prova non l'ha visto perche' in tutti i casi che avevo scritto il
    # vincitore costante era sempre 2: non avevo mai provato «costante ma un altro».
    ATTESO = 2
    if len(set(vincitori)) != 1:
        print("     🔴 P1.a CADE: vincitori diversi %s — l'ordine (o il rumore) decide,"
              % vincitori)
        print("        non il pool. La raccomandazione di ieri NON e' ripetibile.")
    elif vincitori[0] == ATTESO:
        print("     ✅ P1.a REGGE: %d worker vince in tutte, a ordini diversi." % ATTESO)
    else:
        print("     🟠 P1.a: META' REGGE e META' CADE, e vanno lette separate.")
        print("        REGGE la parte che contava: il vincitore e' lo STESSO in tutte e")
        print("        tre a ordini diversi, quindi NON e' l'effetto d'ordine a decidere.")
        print("        CADE la predizione: attesi %d worker, vince %d."
              % (ATTESO, vincitori[0]))
        print("        ⇒ La raccomandazione precedente e' FALSIFICATA, non confermata.")

    print("\n  --- P1.b: il RAPPORTO p95(1)/p95(2) sta fra 1,5 e 2,2? ---")
    rapporti = []
    for rip in range(1, nrip + 1):
        uno = next((r for r in esiti if r["ripetizione"] == rip and r["worker"] == 1), None)
        due = next((r for r in esiti if r["ripetizione"] == rip and r["worker"] == 2), None)
        if not uno or not due or not pct(due["lat"], .95):
            continue
        q = pct(uno["lat"], .95) / pct(due["lat"], .95)
        rapporti.append(q)
        print("     ripetizione %d: %.2f" % (rip, q))
    if rapporti and all(1.5 <= q <= 2.2 for q in rapporti):
        print("     ✅ P1.b REGGE.")
    elif rapporti and any(q < 1.15 for q in rapporti):
        print("     🔴 P1.b CADE sotto 1,15: il guadagno non e' distinguibile dal rumore.")
    elif rapporti:
        print("     🟡 P1.b fuori dalla forchetta ma sopra 1,15: il guadagno c'e', "
              "l'entita' predetta no.")

    print("\n  --- P1.d: il RANGE e' minore della differenza fra 1 e 2 worker? ---")
    if 1 in med and 2 in med:
        differenza = abs(med[1] - med[2])
        peggiore = max(rng.get(1, 0), rng.get(2, 0))
        print("     differenza fra le mediane: %.3fs" % differenza)
        print("     range piu' largo fra i due bracci: %.3fs" % peggiore)
        if peggiore < differenza:
            print("     ✅ P1.d REGGE: la differenza sopravvive alla dispersione.")
        else:
            print("     🔴 P1.d CADE: il range COPRE la differenza.")
            print("        ⇒ Si scrive «su questa macchina il guadagno del pool non e'")
            print("           distinguibile», col numero accanto — NON «il pool non serve».")
            print("           Sono due affermazioni diverse e solo la prima e' misurata.")
    print("=" * 78)


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [n_client] [n_giudizi] [ripetizioni]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    nclient = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    ngiud = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    # 1 = il banco del 02/09, identico e riproducibile. 3 = il protocollo P1.
    nrip = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        return
    # ── I DUE RIGHELLI, PRIMA DI QUALSIASI NUMERO ───────────────────────────
    # ① DA DOVE importa il python che misura. Un banco lanciato dentro il repo puo'
    #    importare `verimem` dall'albero invece che dal pacchetto installato, e allora
    #    misura codice diverso da quello che credi. Righello istituito sul canale il
    #    03/09 dopo che due istanze ci sono cadute.
    # ② SOTTO CHE CARICO. Il 02/09 lo stesso braccio a 1 worker ha dato p95 1,388s e
    #    2,664s a 23 minuti di distanza, e nessuno dei due banchi registrava la
    #    condizione: «non ripetibile» era la diagnosi sbagliata di un esperimento di
    #    cui non si sapeva quale fosse. Un numero senza la sua condizione non si
    #    confronta con niente.
    da_dove = subprocess.run(
        [py, "-c", "import verimem,sys; print(verimem.__file__)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("  verimem importato da: %s" % (da_dove.stdout or da_dove.stderr).strip())
    libera_gb, cpu_pct, n_py, rss_py = carico_macchina()
    print("  carico PRIMA: RAM libera %.1f GB · CPU %d%% · %d processi python "
          "(%.2f GB RSS)" % (libera_gb, cpu_pct, n_py, rss_py))
    # ⚠️ RIFIUTA invece di produrre un numero che sembra buono. Una misura di
    # prestazioni presa su una macchina satura non e' «meno precisa»: e' di un altro
    # esperimento.
    if libera_gb < 8.0 or cpu_pct > 50:
        print("\n  🔴 NON PARTO: serve RAM libera >8 GB e CPU <50%%, misurati "
              "%.1f GB e %d%%." % (libera_gb, cpu_pct))
        print("     Il board che dice «slot libero» non basta: il 03/09 alle 19:55")
        print("     diceva liberi entrambi con 3,4 GB liberi e CPU all'87%.")
        raise SystemExit(3)

    attesi = nclient * ngiud
    print("  %d client x %d giudizi = %d, per ogni configurazione di pool\n"
          % (nclient, ngiud, attesi))
    print("  %-8s %9s %9s %9s %11s %12s %11s"
          % ("worker", "p50", "p95", "max", "giudizi/s", "daemon RSS", "giudicate"))
    print("  " + "-" * 76)
    esiti = []
    for rip, ordine in enumerate(ORDINI[:nrip], 1):
        if nrip > 1:
            print("  --- ripetizione %d/%d, ordine dei bracci %s ---"
                  % (rip, nrip, "->".join(str(x) for x in ordine)))
        for posizione, w in enumerate(ordine, 1):
            r = un_giro(py, venv, w, nclient, ngiud)
            if r is None:
                print("  %-8d 🔴 il daemon non e' diventato pronto" % w)
                continue
            # P1.a si decide su QUESTI due campi: senza sapere in che POSIZIONE
            # ha girato un braccio, l'effetto d'ordine resta un sospetto e basta.
            r["ripetizione"], r["posizione"] = rip, posizione
            esiti.append(r)
            tput = len(r["lat"]) / r["durata"] if r["durata"] else 0
            print("  %-8d %8.3fs %8.3fs %8.3fs %10.1f %11.1f %6d/%d"
                  % (w, pct(r["lat"], .5), pct(r["lat"], .95), max(r["lat"]),
                     tput, r["rss"], r["ok"], attesi))

    # IL CONTROLLO: se non sono tutte giudicate, i percentili non sono di giudizi
    incompleti = [r for r in esiti if r["ok"] != attesi]
    print("\n=== IL CONTROLLO PRIMA DEL VERDETTO ===")
    if incompleti:
        print("  ⚠️ configurazioni con giudizi mancanti: %s"
              % ", ".join(str(r["worker"]) for r in incompleti))
        print("     i percentili di quelle righe NON sono tempi di giudizio.")
    else:
        print("  ✅ tutte le configurazioni hanno giudicato %d su %d" % (attesi, attesi))

    if not esiti:
        return
    if nrip > 1:
        verdetto_p1(esiti, nrip)
        return
    base = next((r for r in esiti if r["worker"] == 1), esiti[0])
    print("\n=== LA PREDIZIONE REGGE? ===")
    print("  predetto: memoria invariata · p95 NON sotto 1s · nessun guadagno da 2 a 4")
    for r in esiti:
        if r["worker"] == 1:
            continue
        p95 = pct(r["lat"], .95)
        gua = 100 * (1 - p95 / pct(base["lat"], .95)) if pct(base["lat"], .95) else 0
        tput_b = len(base["lat"]) / base["durata"] if base["durata"] else 0
        tput_r = len(r["lat"]) / r["durata"] if r["durata"] else 0
        print("  %d worker: p95 %.3fs (%+.0f%%)  throughput %.1f -> %.1f giudizi/s  "
              "RSS %+.0f MB"
              % (r["worker"], p95, -gua, tput_b, tput_r, r["rss"] - base["rss"]))
        # il controllo che separa «migliorato» da «spalmato»
        if p95 < pct(base["lat"], .95) * 0.9 and tput_r <= tput_b * 1.05:
            print("       ⚠️ p95 sceso ma throughput fermo: l'attesa e' stata SPALMATA,")
            print("          non ridotta. Non e' un miglioramento.")
    migliore = min(esiti, key=lambda r: pct(r["lat"], .95))
    p95m = pct(migliore["lat"], .95)
    if p95m < 1.0:
        print("\n  🟢 BERSAGLIO CENTRATO con %d worker: p95 %.3fs < 1s ⇒ la mia predizione"
              % (migliore["worker"], p95m))
        print("     CADE e il pool A (modello condiviso, memoria invariata) BASTA.")
    else:
        print("\n  🔴 BERSAGLIO MANCATO: il p95 migliore e' %.3fs con %d worker."
              % (p95m, migliore["worker"]))
        print("     ⇒ Il pool A non basta: il collo di bottiglia e' la CPU, non il lock.")
        print("     Per scendere servirebbe il pool B (N istanze del giudice), che costa")
        print("     ~640 MB di modello per worker — e allora il conto della memoria")
        print("     va rifatto.")


# Protetto perche' il banco va PROVATO prima di fidarsi dei suoi numeri:
# senza questa riga, importarlo per testare `verdetto_p1` lo farebbe partire.
if __name__ == "__main__":
    main()
