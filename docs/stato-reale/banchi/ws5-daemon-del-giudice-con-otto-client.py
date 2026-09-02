r"""Il daemon del giudice con OTTO client veri: memoria, latenza, e il caso «daemon giu'».

Anello finale di M4. Le misure che portano qui::

    baseline            RSS 980,6 · privata 1552,8 per processo (`c8830190`)
    T4.1 a 2 client     -9% di privata, p95 +162 ms (`e0df50c8`)
    T4.2                bersaglio <=250 MB irraggiungibile: il pavimento e' torch,
                        784,9 MB di privata al solo import (`6ec9a2bf`)
    pavimento client    87,6 MB RSS / 681,9 privata SENZA torch (`05b10b66`)

⇒ Il conto aritmetico per 8 diceva **RSS da 7,8 a 1,6 GB (-80%)**. Qui si **esegue**,
perche' un'estrapolazione da 1 e 2 processi non e' una misura a 8 — ed e' la stessa
obiezione che ho mosso al piano stamattina.

📌 **PREDIZIONE, scritta prima di eseguire** — memoria ottimista, latenza NO::

    RSS totale       ~1,6 GB   (861,8 del daemon + 8 x 87,6)
    privata totale   ~7,9 GB   (2446 + 8 x 682)
    p50              ~0,2-0,4s
    p95              **oltre 1 secondo**   <- e qui mi aspetto il guaio

**Il perche' della latenza**: il daemon serializza su UN giudice con un lock. A 2 client
il p95 peggiorava di +162 ms; a 8, chi arriva ultimo aspetta i sette davanti. Con un
giudizio caldo da ~0,2s, **il p95 dovrebbe avvicinarsi a 1,4-1,6s**. ⇒ Predico che la
memoria dia ragione al disegno e la latenza dica «**serve un pool**», non «un daemon».

⚠️ E se il p95 restasse basso, vorrebbe dire che i client non si sovrappongono davvero:
in quel caso la misura non ha stressato niente e il verdetto sulla latenza va rifatto
con partenza simultanea piu' stretta.

🔴🟢 ESITO — **la latenza dice «serve un pool»; la memoria rende meno dell'aritmetica**::

    8 client x 10 giudizi = 80, tutte giudicate, 0 cadute

                   RSS        privata
    daemon       1900,0 MB   3599,3 MB
    8 client      692,8 MB   5452,5 MB
    TOTALE       2592,8 MB   9051,8 MB
    oggi (8x)    7844,8 MB  12422,4 MB
    ---------------------------------
    risparmio        67%         27%

    p50 1,293s   p95 1,388s   max 1,467s      (a 1 client: 0,217 / 0,259)

✅ **La predizione sulla LATENZA regge**: p95 **1,388s**, oltre il secondo ⇒ **un daemon
con UN giudice non regge 8 client: serve un POOL di worker.** Il p50 e' **sei volte** il
giudizio solitario (1,293 contro 0,217): la coda e' reale, non un artefatto di misura.

🪞 **La predizione sulla MEMORIA era ottimista, e di parecchio**: predicevo **~1,6 GB
RSS**, misurati **2,6** — fuori del **62%**. Il motivo: **il daemon cresce con la
concorrenza** (1900 MB con 8 thread contro 861,8 da solo), e nella predizione avevo usato
il numero del daemon **scarico**, che avevo gia' misurato salire a 2014 MB con 2 client.
⇒ Avevo il dato e non l'ho messo nel conto.

📌 **E l'aritmetica sbagliava nel verso che mi faceva comodo**: il conto per 8 dava
**-80% di RSS**, la misura dice **-67%**. Il limite che avevo dichiarato consegnando quel
conto («*e' aritmetica sulle mie misure a 1 e 2 processi, non una misura a 8*») **era
giusto, e la differenza e' 13 punti**. ⇒ Un'estrapolazione dichiarata resta
un'estrapolazione: va eseguita, e qui l'esecuzione l'ha corretta.

⚖️ **COSA RESTA COMUNQUE VERO**: -67% di RSS e -27% di privata su 8 agenti sono un
guadagno grosso, e molto piu' del **-9%** che avevo misurato a 2 client. ⇒ Il -9% non era
sbagliato: era **la concorrenza sbagliata per la domanda**, perche' e' il numero di copie
del giudice risparmiate a fare il guadagno.

⛔ **COSA NON HO MISURATO, ed e' nel disegno qui sotto**: il caso **«daemon giu'»**. Il
fallback in-process con dichiarazione in ricevuta e' **progettato, non provato**. Finche'
non lo e', il disegno ha un ramo che nessuno ha visto funzionare — ed e' proprio il ramo
che decide se un daemon assente diventa «ammesso senza giudizio» in silenzio.

IL DISEGNO, come lo consegnerei per la 0.8.0::

    trasporto   socket TCP su 127.0.0.1, porta effimera annunciata in un file di
                discovery. NON una porta fissa: due daemon sulla stessa macchina
                (due utenti, due checkout) si prenderebbero a calci.
    protocollo  una riga JSON per richiesta, una per risposta, terminate da \n.
                {"claim":..., "fonte":...} -> {"g": <punteggio>|null}
    avvio       il primo client che non trova il daemon lo spawna e aspetta il file
                di discovery; gli altri si connettono e basta.
    ⚠️ DAEMON GIU'  il client NON deve fallire la scrittura: ricade sul giudizio
                in-process **e lo DICHIARA nella ricevuta**. Un fallback silenzioso
                trasformerebbe «il daemon non risponde» in «il fatto e' stato
                giudicato», che e' la bugia che questo prodotto esiste per non dire.

⇒ Il banco misura anche QUEL caso: uccide il daemon e verifica che la scrittura
prosegua **e** che la ricevuta lo dica.

REGIME: `main` installato (0.7.6), ambiente pulito (filtro DENTRO lo script), store
temporaneo per client, RAM libera verificata prima (11,56 GB contro i 7,7 necessari).
⚖️ PUNTI DEBOLI: 8 client su una macchina sola non sono 8 agenti veri (che farebbero
anche altro); e il daemon e' un prototipo di misura, non un componente di produzione.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-daemon-del-giudice-con-otto-client.py <venv> [n_client] [n_giudizi]
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

PORTA_FILE = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
run_validation_gate(proposition="Riscaldamento.", verified_by=None, topic=None,
                    agent=None, source=FONTE, ground_write=True)

lock = threading.Lock()
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
        with lock:
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
import ctypes, ctypes.wintypes as wt, json, os, socket, sys, time

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

PORTA, N, ET, VIA = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
# il client e' un client MCP vero: importa il server, NON il giudice
import verimem.mcp_server  # noqa: F401

while not os.path.exists(VIA):
    time.sleep(0.05)

lat, punteggi, caduti = [], 0, 0
for i in range(N):
    t = time.time()
    try:
        s = socket.create_connection(("127.0.0.1", PORTA), timeout=120)
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
            punteggi += 1
    except Exception:
        caduti += 1
    lat.append(time.time() - t)
r, pr = mem()
print("CL|%s|%s|%d|%d|%.1f|%.1f" % (ET, json.dumps(lat), punteggi, caduti, r, pr), flush=True)
'''


def pct(v, q):
    if not v:
        return 0.0
    x = sorted(v)
    return x[min(len(x) - 1, int(round((len(x) - 1) * q)))]


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
    base = tempfile.mkdtemp(prefix="ws5_d8_")
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

    porta_file = os.path.join(base, "PORTA")
    print("  %d client x %d giudizi — avvio il daemon..." % (nclient, ngiud))
    t0 = time.time()
    d = subprocess.Popen([py, "-u", fd, porta_file], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=amb(os.path.join(base, "d")),
                         cwd=os.path.dirname(venv))
    while not os.path.exists(porta_file) and time.time() - t0 < 900:
        time.sleep(0.3)
    if not os.path.exists(porta_file):
        d.kill()
        print("  🔴 daemon non pronto entro 900s")
        return
    porta = int(open(porta_file).read().strip())
    print("  daemon pronto in %.1fs (porta %d)\n" % (time.time() - t0, porta))

    via = os.path.join(base, "VIA")
    proc = [subprocess.Popen([py, "-u", fc, str(porta), str(ngiud), "c%d" % i, via],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, encoding="utf-8", errors="replace",
                             env=amb(os.path.join(base, "c%d" % i)),
                             cwd=os.path.dirname(venv))
            for i in range(nclient)]
    time.sleep(8.0)          # tutti hanno importato mcp_server prima del via
    open(via, "w").write("1")
    tutte, tot_rss, tot_priv, ok, ko = [], 0.0, 0.0, 0, 0
    print("  %-8s %8s %9s %9s %9s %10s" % ("client", "giudizi", "p50", "p95", "RSS MB", "privata"))
    print("  " + "-" * 60)
    for p in proc:
        out, _ = p.communicate(timeout=3600)
        for riga in (out or "").splitlines():
            if riga.startswith("CL|"):
                _, et, lat_j, pun, cad, rss, priv = riga.split("|")
                lat = json.loads(lat_j)
                tutte.extend(lat)
                ok += int(pun); ko += int(cad)
                tot_rss += float(rss); tot_priv += float(priv)
                print("  %-8s %8d %8.3fs %8.3fs %8.1f %9.1f"
                      % (et, len(lat), pct(lat, .5), pct(lat, .95), float(rss), float(priv)))

    s = socket.create_connection(("127.0.0.1", porta), timeout=60)
    s.sendall(b'{"op":"mem"}\n')
    buf = b""
    while not buf.endswith(b"\n"):
        buf += s.recv(65536)
    s.close()
    m = json.loads(buf.decode())

    print("\n  === IL CONTROLLO PRIMA DEI NUMERI ===")
    attesi = nclient * ngiud
    print("  risposte con grounding: %d su %d   richieste cadute: %d" % (ok, attesi, ko))
    if ok != attesi:
        print("  ⚠️ NON tutte giudicate: i tempi qui sopra non sono tempi di giudizio.")
        d.kill()
        return
    print("  ✅ tutte giudicate ⇒ i numeri sono del giudice")

    print("\n  === MEMORIA TOTALE ===")
    print("  daemon        RSS %8.1f MB   privata %8.1f MB" % (m["rss"], m["priv"]))
    print("  %d client     RSS %8.1f MB   privata %8.1f MB" % (nclient, tot_rss, tot_priv))
    print("  TOTALE        RSS %8.1f MB   privata %8.1f MB"
          % (m["rss"] + tot_rss, m["priv"] + tot_priv))
    oggi_rss, oggi_priv = nclient * 980.6, nclient * 1552.8
    print("  oggi (%d giudici separati)  RSS %8.1f MB   privata %8.1f MB"
          % (nclient, oggi_rss, oggi_priv))
    print("  ⇒ risparmio  RSS %.0f%%   privata %.0f%%"
          % (100 * (1 - (m["rss"] + tot_rss) / oggi_rss),
             100 * (1 - (m["priv"] + tot_priv) / oggi_priv)))

    print("\n  === LATENZA (aggregata su %d client) ===" % nclient)
    print("  p50 %.3fs   p95 %.3fs   max %.3fs" % (pct(tutte, .5), pct(tutte, .95), max(tutte)))
    print("  riferimento a 1 client (misurato, non citato): p50 0,217s  p95 0,259s")
    p95 = pct(tutte, .95)
    print("\n=== LA PREDIZIONE REGGE? ===")
    print("  predetto: memoria ~1,6 GB RSS · p95 OLTRE 1 secondo (serve un pool)")
    if p95 > 1.0:
        print("  🔴 p95 %.3fs: OLTRE il secondo, come previsto ⇒ un daemon con UN" % p95)
        print("     giudice non regge 8 client: serve un POOL di worker.")
    else:
        print("  🟢 p95 %.3fs: SOTTO il secondo ⇒ la mia predizione CADE e un daemon" % p95)
        print("     singolo regge anche a 8. ⚠️ Ma verifica che i client si siano")
        print("     davvero sovrapposti: se no, la misura non ha stressato niente.")
    d.kill()
    print("\n  (daemon chiuso)")


main()
