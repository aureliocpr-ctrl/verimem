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

🟡 ESITO — **la predizione regge su tre punti; il bersaglio <1s NON e' centrato**::

    worker      p50       p95    giudizi/s   daemon RSS   giudicate
    1        1,546s    2,664s        4,7       1901,7       80/80
    2        0,929s    1,404s        7,4       1910,7       80/80
    4        1,011s    1,809s        6,8       1920,8       80/80

✅ **memoria invariata**: +9 MB con 2 worker, +19 con 4. Il pool A non costa nulla.
✅ **p95 non scende sotto 1s**: il migliore e' **1,404s**. Bersaglio mancato.
✅ **da 2 a 4 non si guadagna, si PERDE** (1,404 -> 1,809): i core finiscono, come
   previsto. Il pool non moltiplica la CPU.
🪞 **sbagliavo sull'entita'**: predicevo «meno del 40%», misurato **-47%** con 2 worker.

📌 **E il guadagno e' VERO, non attesa spalmata**: il throughput sale da **4,7 a 7,4
giudizi/s** (+57%). Il controllo che avevo messo apposta — «*se il p95 scende ma il
throughput non sale, ho solo spalmato*» — **non si accende**. ⇒ Due worker sono un
miglioramento reale a costo zero.

⚠️⚠️ **MA IL NUMERO ASSOLUTO E' INSTABILE, E VA DETTO PRIMA DEL RESTO**: la stessa
configurazione a **1 worker** ha dato **p95 1,388s** nel banco precedente (`481a2eb3`,
21:07) e **2,664s** qui (21:07 dello stesso giorno, macchina piu' carica). ⇒ **Quasi il
doppio, stesse condizioni nominali.**
⇒ Il **rapporto** fra le tre configurazioni, misurate nella STESSA esecuzione, e' il dato
solido; il **valore assoluto** no. ⇒ **«p95 <1s» non e' un criterio stabile su questa
macchina**: prima di dichiarare il bersaglio mancato per sempre andrebbe rimisurato a
macchina scarica. Con il p95 a 1 worker che varia del 92%, un bersaglio fissato al
decimo di secondo misura il rumore quanto il pool.

🪞🔴 **SECONDA ESECUZIONE (21:49, CPU 29% invece di 68%) — LA RACCOMANDAZIONE CADE**::

                  esecuzione 1 (CPU 68%)      esecuzione 2 (CPU 29%)
    worker      p50      p95   giud/s       p50      p95   giud/s
    1        1,546s  2,664s     4,7      1,283s  1,707s     5,8
    2        0,929s  1,404s     7,4      1,153s  2,115s     4,6
    4        1,011s  1,809s     6,8      1,165s  1,617s     6,0

    varianza del p95 fra le due esecuzioni:  1 worker 56%  ·  2 worker 51%  ·  4 worker 12%
    il «guadagno» che avevo misurato:        -47%

⇒ **A 2 worker il p95 passa da 1,404s a 2,115s: da MIGLIORE a PEGGIORE.** ⇒ **La
differenza fra configurazioni e' piu' piccola della differenza fra due esecuzioni della
stessa configurazione**: con due punti il rumore domina il segnale, e **«pool a 2 worker»
va RITIRATO**.
📌 E a 2 worker il **max** e' **5,988s** contro un p95 di 2,115: una richiesta ha aspettato
quasi sei secondi. Instabilita' vera, non solo dispersione.

🪞 **L'ERRORE MIO, e non e' «i numeri ballano»**: nella prima stesura avevo gia' scritto
l'avvertenza giusta — «*il valore assoluto non e' stabile, il RAPPORTO dentro la stessa
esecuzione e' il dato solido*» — **e poi ho raccomandato 2 worker proprio su quel
rapporto**. Avevo la premessa e ne ho tratto la conclusione sbagliata: **se il rumore
muove i tempi del 50%, muove anche i loro rapporti.** Un rapporto misurato una volta non
e' piu' solido di un valore misurato una volta.

✅ **COSA SOPRAVVIVE**, perche' confermato in ENTRAMBE le esecuzioni::

    la memoria non cambia col pool:  +9 e +14 MB su ~1900   (due misure concordi)

⚠️ E il **-67% del daemon contro 8 giudici separati** e' misurato **una volta sola**: la
memoria e' molto piu' stabile della latenza e le due esecuzioni la confermano, ma sta
sullo stesso piano metodologico e va detto.

⇒ **Per dire qualcosa sul pool servono N ripetizioni per configurazione**, non una. Con
la varianza al 50%, distinguere un guadagno del 20% dal rumore vuole almeno 5 giri per
configurazione (~45 minuti di macchina). Senza quelli, la conclusione onesta e' **«su
questa macchina il pool non mostra un guadagno misurabile»**.

--- (la raccomandazione della PRIMA esecuzione, ora ritirata) ---
⇒ ~~Cosa consegno come raccomandazione~~: **pool a 2 worker**, perche' e' gratis in
memoria, dimezza il p95 e aumenta il throughput del 57%. **Non 4.** E il bersaglio <1s
resta aperto: con il pool A non si raggiunge qui, e il pool B (N istanze del giudice)
costerebbe ~640 MB di modello per worker — a quel punto il conto della memoria, che era
il motivo del daemon, va rifatto da capo.

REGIME: `main` installato (0.7.6), ambiente pulito (filtro DENTRO lo script), 8 client
veri che importano `mcp_server`, store temporaneo per client, RAM verificata prima.
⚖️ PUNTI DEBOLI: una macchina sola; il pool A e' un prototipo (nessuna gestione di
saturazione o back-pressure); e 80 giudizi non sono un carico di produzione.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-il-pool-del-giudice-porta-il-p95-sotto-il-secondo.py <venv> [n_client] [n_giudizi]
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


def bimodale(lat):
    """Le latenze sono UNA popolazione o DUE? Perche' la mediana di una miscela non
    dice niente — e sarebbe la terza volta che ci casco.

    Lezione `dfe9425ca057` (26/07): «*il thread che carica il cross-encoder tiene lo slot
    per piu' di 24 query e OGNI query salta il rerank … quando invece il CE arriva a
    girare, quelle query pagano +2067 ms. Le due popolazioni si mescolano dentro la stessa
    misura e la mediana balla*». Riguardava il read path, quindi qui e' un'IPOTESI, non un
    trasferimento — ma la si controlla invece di darla per esclusa.

    Il criterio, deliberatamente grezzo: si ordina, si cerca il salto piu' grande fra due
    valori consecutivi, e lo si confronta con la dispersione tipica. Un salto che vale
    piu' di un terzo dell'intervallo totale, con almeno 3 valori da entrambe le parti,
    e' una firma di due gruppi — non una prova, un allarme che chiede di guardare.
    """
    if len(lat) < 8:
        return None
    x = sorted(lat)
    salti = [(x[i + 1] - x[i], i) for i in range(len(x) - 1)]
    salto, i = max(salti)
    ampiezza = x[-1] - x[0]
    if ampiezza <= 0:
        return None
    if salto > ampiezza / 3.0 and (i + 1) >= 3 and (len(x) - i - 1) >= 3:
        return {"salto": salto, "sotto": i + 1, "sopra": len(x) - i - 1,
                "confine": (x[i] + x[i + 1]) / 2,
                "med_sotto": x[i // 2], "med_sopra": x[i + 1 + (len(x) - i - 1) // 2]}
    return None


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


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [n_client] [n_giudizi]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    nclient = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    ngiud = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        return
    attesi = nclient * ngiud
    print("  %d client x %d giudizi = %d, per ogni configurazione di pool\n"
          % (nclient, ngiud, attesi))
    print("  %-8s %9s %9s %9s %11s %12s %11s"
          % ("worker", "p50", "p95", "max", "giudizi/s", "daemon RSS", "giudicate"))
    print("  " + "-" * 76)
    esiti = []
    for w in (1, 2, 4):
        r = un_giro(py, venv, w, nclient, ngiud)
        if r is None:
            print("  %-8d 🔴 il daemon non e' diventato pronto" % w)
            continue
        esiti.append(r)
        tput = len(r["lat"]) / r["durata"] if r["durata"] else 0
        print("  %-8d %8.3fs %8.3fs %8.3fs %10.1f %11.1f %6d/%d"
              % (w, pct(r["lat"], .5), pct(r["lat"], .95), max(r["lat"]),
                 tput, r["rss"], r["ok"], attesi))

    # ⚠️ PRIMA di confrontare le configurazioni: le latenze sono UNA popolazione?
    print("")
    print("=== LE LATENZE SONO UNA POPOLAZIONE SOLA? ===")
    sospette = []
    for r in esiti:
        b = bimodale(r["lat"])
        if b:
            sospette.append(r["worker"])
            print("  🔴 %d worker: DUE GRUPPI — %d richieste sotto %.3fs (mediana %.3f) e"
                  % (r["worker"], b["sotto"], b["confine"], b["med_sotto"]))
            print("     %d sopra (mediana %.3f), separati da un salto di %.3fs"
                  % (b["sopra"], b["med_sopra"], b["salto"]))
        else:
            print("  ✅ %d worker: una sola popolazione (nessun salto dominante)" % r["worker"])
    if sospette:
        print("  ⇒ Dove ci sono due gruppi la MEDIANA NON descrive niente: mescola due")
        print("     regimi. Il confronto fra configurazioni qui sotto va letto sapendo")
        print("     che almeno una riga misura una miscela.")

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


main()
