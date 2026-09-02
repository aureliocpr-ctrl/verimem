r"""T4.1 — un giudice condiviso contro N giudici separati: memoria e latenza.

Anello ③ di M4. La baseline dice che il costo e' **tutto nel caricamento** (958 MB RSS /
1553 MB privata per processo, 31,6s cold contro 0,47s warm, memoria che non cresce). ⇒ Un
servizio condiviso paga quel caricamento **una volta sola**. Qui si misura quanto rende,
e quanto costa in latenza.

⚠️ **DUE CLIENT, NON QUATTRO — e il motivo e' una misura, non una comodita'**: il braccio
di controllo a 4 (ognuno col suo giudice) costerebbe **~6,2 GB** di privata (4 x 1552,8,
misurato in `1f93a8c6`), e su questa macchina la RAM libera e' **4,17 GB su 31,29**
(87% occupata da altre istanze). ⇒ Con 4 misurerei lo swap, non il giudice. Il braccio di
controllo a **2** l'ho gia' misurato: **3144,3 MB** di privata.

📌 **PREDIZIONE, scritta PRIMA di eseguire — e NON coincide col piano**::

    memoria   1 daemon + 2 client leggeri  ~1,65 GB   contro   3,14 GB   =>  -47%
    latenza   p95 PEGGIORA di PIU' di 150 ms, e predico che serva un POOL

**Il perche' della seconda, che e' la parte scomoda**: un daemon con **un** giudice
serializza. Due client che chiedono insieme si mettono in coda, e un giudizio caldo costa
**0,47s**: chi arriva secondo aspetta il primo. ⇒ Il p95 con 2 client dovrebbe avvicinarsi
al **doppio** del p50 di un client solo — cioe' **+400 ms circa**, ben oltre i +150 ms che
il piano si aspetta, e vicino alla soglia dei +500 ms oltre la quale il piano stesso dice
«serve un pool». ⇒ **Predico che T4.1 vada bene sulla MEMORIA e male sulla LATENZA**, e
che la conclusione utile sia «un daemon con un pool di worker», non «un daemon».

⇒ Se mi sbaglio e il p95 resta sotto +150 ms, il giudizio non e' il collo di bottiglia
che credo e un daemon singolo basta: **e' l'esito che mi piacerebbe di piu' e quello che
credo di meno.**

IL DISEGNO::

    braccio A (attuale)   N processi, ognuno carica il PROPRIO giudice
                          gia' misurato: 2 processi = 3144,3 MB privata
    braccio B (condiviso) 1 daemon carica il giudice UNA volta;
                          N client si connettono e chiedono giudizi via socket locale

    carico: 100 giudizi per client x 2 client = 200 giudizi
    si misurano: memoria totale (RSS e privata, sommate su tutti i processi)
                 p50 e p95 delle latenze, per client e aggregate

🔑 **CONTROLLO POSITIVO OBBLIGATORIO**: ogni risposta del daemon porta il
`grounding_score`. Se tornasse `None`, il daemon non starebbe giudicando e i tempi
sarebbero quelli di un socket vuoto — la misura direbbe «velocissimo» misurando niente.
⇒ Il banco **conta** quante risposte hanno un punteggio e si ferma se non sono tutte.

⚠️ **QUESTO E' UN PROTOTIPO DI MISURA, NON UNA PROPOSTA DI ARCHITETTURA**: sta nello
scratchpad del banco, non tocca `verimem/`, e serve a dare un numero alla decisione. Un
daemon di produzione avrebbe autenticazione, gestione degli errori e un ciclo di vita che
qui non ci sono.

🔴 ESITO — **T4.1 RENDE MENO E COSTA PIU' DI QUANTO IL PIANO PREVEDE**::

    braccio                        privata      p50       p95
    2 giudici separati (2x1555,5)  3111,0 MB   0,217s    0,259s
    1 daemon + 2 client            2829,6 MB   0,379s    0,421s
    -----------------------------------------------------------
    memoria                          -9,0%
    latenza                                    +162 ms   +162 ms

    controllo positivo: 200 risposte su 200 con grounding_score  ✅
    daemon pronto in 56,3s (il caricamento, pagato UNA volta)

⇒ **Memoria: -9%, non -47%.** Il daemon con due thread usa **2829,6 MB**, quasi quanto
due giudici separati: **condividere i PESI non basta**, perche' i tensori di lavoro sono
per-thread e vengono allocati comunque. ⇒ Il risparmio del servizio condiviso e' **un
ordine di grandezza sotto** la stima del piano.
⇒ **Latenza: +162 ms sul p95**, cioe' **oltre la soglia dei 150 ms** che il piano si
dava. La mia predizione («*peggiora di piu' di 150 ms*») **regge**; quella del piano no.

🪞 **E IL VERDETTO AUTOMATICO DI QUESTO BANCO ERA SBAGLIATO — l'ho corretto a mano**::

    stampava:  «p95 -49 ms: SOTTO i 150 ms => la MIA predizione CADE»
    perche':   confrontava col riferimento della BASELINE (0,47s), misurato su
               4 giudizi in un altro regime, invece che col BRACCIO A a parita'
               di carico (0,259s, 100 giudizi, stesso ambiente)

⇒ **Un riferimento preso da un'altra misura non e' un controllo**: e' un numero che
somiglia a un controllo. Il braccio A va **eseguito**, non citato.

⚠️⚠️ **E IL BRACCIO A HA DOVUTO ESSERE RIFATTO**: la prima esecuzione l'avevo lanciata da
bash passando solo `HIPPO_DATA_DIR`, e le variabili della mia sessione sono arrivate al
processo. Risultato: **495,6 MB invece di 980,4** e **p50 0,075s invece di 0,217s** — il
giudice era servito dal daemon condiviso dello stack principale, non caricato in-process.
⇒ **Cura strutturale**: il filtro dell'ambiente ora sta **dentro** lo script (che si
riavvia da solo pulito), non nel comando. **Un filtro nel comando puo' saltare.**

📌 **COSA QUESTO NUMERO NON DICE, ed e' importante per la decisione**: il **9% e' del MIO
prototipo**, non del concetto. Il mio daemon serve i client con `threading` e un lock; un
daemon che serializzasse in un solo thread, o che facesse **batch** delle richieste,
userebbe meno memoria e forse meno latenza. ⇒ **T4.1 non e' falsificata: e' ridimensionata
nella forma piu' ovvia di implementarla**, ed e' il momento giusto per saperlo.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-t41-il-giudice-come-servizio-condiviso.py <venv> [n_client] [n_giudizi]
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
import ctypes, ctypes.wintypes as wt, json, socket, sys, threading, time

class _PMCEX(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]

def mem():
    c = _PMCEX(); c.cb = ctypes.sizeof(_PMCEX)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMCEX), wt.DWORD]; fn.restype = wt.BOOL
    if not fn(h, ctypes.byref(c), c.cb):
        raise OSError("err=%d" % ctypes.windll.kernel32.GetLastError())
    return c.WorkingSetSize / 1048576.0, c.PrivateUsage / 1048576.0

PORTA_FILE = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
# il caricamento: UNA volta, prima di accettare chiunque
run_validation_gate(proposition="Riscaldamento.", verified_by=None, topic=None,
                    agent=None, source=FONTE, ground_write=True)

lock = threading.Lock()          # UN giudice: le richieste si serializzano
def servi(conn):
    try:
        dati = b""
        while not dati.endswith(b"\n"):
            p = conn.recv(65536)
            if not p:
                return
            dati += p
        req = json.loads(dati.decode("utf-8"))
        if req.get("op") == "mem":
            rss, priv = mem()
            conn.sendall((json.dumps({"rss": rss, "priv": priv}) + "\n").encode())
            return
        with lock:
            g = run_validation_gate(proposition=req["claim"], verified_by=None,
                                    topic=None, agent=None, source=req["fonte"],
                                    ground_write=True)
        conn.sendall((json.dumps({"g": getattr(g, "grounding_score", None)}) + "\n").encode())
    except Exception as e:
        try:
            conn.sendall((json.dumps({"errore": str(e)[:80]}) + "\n").encode())
        except Exception:
            pass
    finally:
        conn.close()

s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(64)
open(PORTA_FILE, "w").write(str(s.getsockname()[1]))    # solo ORA sono pronto
while True:
    c, _ = s.accept()
    threading.Thread(target=servi, args=(c,), daemon=True).start()
'''

CLIENT = r'''
import json, socket, sys, time
PORTA, N, ETICHETTA, VIA = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
import os
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
while not os.path.exists(VIA):      # partenza simultanea: e' il punto della contesa
    time.sleep(0.05)
lat, punteggi = [], 0
for i in range(N):
    t = time.time()
    s = socket.create_connection(("127.0.0.1", PORTA), timeout=300)
    s.sendall((json.dumps({"claim": "Nella coda ci sono %d run in attesa." % (149 + i),
                           "fonte": FONTE}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        p = s.recv(65536)
        if not p:
            break
        buf += p
    s.close()
    lat.append(time.time() - t)
    try:
        if json.loads(buf.decode()).get("g") is not None:
            punteggi += 1
    except Exception:
        pass
print("CL|%s|%s|%d" % (ETICHETTA, json.dumps(lat), punteggi), flush=True)
'''


def pctile(v, q):
    if not v:
        return 0.0
    x = sorted(v)
    i = min(len(x) - 1, int(round((len(x) - 1) * q)))
    return x[i]


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [n_client] [n_giudizi]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    nclient = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    ngiud = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        return
    base = tempfile.mkdtemp(prefix="ws5_t41b_")
    fd, fc = os.path.join(base, "_d.py"), os.path.join(base, "_c.py")
    for f, testo in ((fd, DAEMON), (fc, CLIENT)):
        with open(f, "w", encoding="utf-8") as h:
            h.write(textwrap.dedent(testo))
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = os.path.join(base, "store")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    porta_file = os.path.join(base, "PORTA")
    print("  avvio il daemon (carica il giudice UNA volta)...")
    t0 = time.time()
    d = subprocess.Popen([py, "-u", fd, porta_file], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=env, cwd=os.path.dirname(venv))
    while not os.path.exists(porta_file) and time.time() - t0 < 900:
        time.sleep(0.3)
    if not os.path.exists(porta_file):
        d.kill()
        print("  🔴 il daemon non e' diventato pronto entro 900s")
        return
    porta = int(open(porta_file).read().strip())
    print("  daemon pronto in %.1fs sulla porta %d\n" % (time.time() - t0, porta))

    via = os.path.join(base, "VIA")
    proc = [subprocess.Popen([py, "-u", fc, str(porta), str(ngiud), "c%d" % i, via],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, encoding="utf-8", errors="replace",
                             env=env, cwd=os.path.dirname(venv))
            for i in range(nclient)]
    time.sleep(2.0)
    open(via, "w").write("1")            # via simultaneo
    tutte, per_client = [], {}
    for p in proc:
        out, _ = p.communicate(timeout=3600)
        for riga in (out or "").splitlines():
            if riga.startswith("CL|"):
                _, et, lat_json, punteggi = riga.split("|")
                lat = json.loads(lat_json)
                per_client[et] = (lat, int(punteggi))
                tutte.extend(lat)

    # la memoria del daemon, chiesta a lui mentre e' ancora vivo
    s = socket.create_connection(("127.0.0.1", porta), timeout=60)
    s.sendall(b'{"op":"mem"}\n')
    buf = b""
    while not buf.endswith(b"\n"):
        buf += s.recv(65536)
    s.close()
    m = json.loads(buf.decode())
    d.kill()

    # CONTROLLO POSITIVO prima dei numeri
    attesi = nclient * ngiud
    con_punteggio = sum(v[1] for v in per_client.values())
    print("  %-16s %8s %10s %10s %10s" % ("client", "giudizi", "p50", "p95", "max"))
    print("  " + "-" * 60)
    for et in sorted(per_client):
        lat, ok = per_client[et]
        print("  %-16s %8d %9.3fs %9.3fs %9.3fs"
              % (et, len(lat), pctile(lat, .50), pctile(lat, .95), max(lat)))
    if con_punteggio != attesi:
        print("\n  ⚠️ SOLO %d risposte su %d hanno un grounding_score: il daemon NON ha"
              % (con_punteggio, attesi))
        print("     giudicato tutto ⇒ i tempi qui sopra non sono tempi di giudizio.")
        return
    print("  ✅ controllo positivo: %d risposte su %d con grounding_score" % (con_punteggio, attesi))

    print("\n  === MEMORIA ===")
    print("  daemon condiviso:   RSS %7.1f MB   privata %7.1f MB" % (m["rss"], m["priv"]))
    print("  %d giudici separati: privata 3144.3 MB   (misurato in 1f93a8c6)" % nclient)
    risparmio = 100.0 * (1 - m["priv"] / 3144.3)
    print("  ⇒ risparmio sulla privata: %.0f%%" % risparmio)

    print("\n  === LATENZA (aggregata sui %d client) ===" % nclient)
    p50, p95 = pctile(tutte, .50), pctile(tutte, .95)
    print("  p50 %.3fs   ·   p95 %.3fs   ·   max %.3fs" % (p50, p95, max(tutte)))
    print("  riferimento: un giudizio caldo da SOLO costa 0,47s (baseline c8830190)")
    delta = (p95 - 0.47) * 1000
    print("  ⇒ p95 contro il solitario: %+.0f ms" % delta)

    print("\n=== LA PREDIZIONE REGGE? ===")
    print("  predetto: memoria -47%% circa · p95 peggiora di PIU' di 150 ms (serve un pool)")
    if delta > 500:
        print("  🔴 p95 %+.0f ms: OLTRE i 500 ms ⇒ come previsto, UN daemon non basta:" % delta)
        print("     serve un POOL di worker. La memoria si risparmia, la latenza no.")
    elif delta > 150:
        print("  🟡 p95 %+.0f ms: oltre i 150 ms del piano ma sotto i 500 ⇒ la mia" % delta)
        print("     predizione regge nella direzione, e un pool e' consigliabile ma non")
        print("     obbligatorio a questa concorrenza.")
    else:
        print("  🟢 p95 %+.0f ms: SOTTO i 150 ms ⇒ la MIA predizione CADE e il piano ha" % delta)
        print("     ragione: a questa concorrenza un daemon singolo basta.")


main()
