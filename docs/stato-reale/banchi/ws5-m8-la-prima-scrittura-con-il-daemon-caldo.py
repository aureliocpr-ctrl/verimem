r"""M8 — la prima scrittura con il giudice gia' caldo in un altro processo: quanto costa?

Due reperti indipendenti dicono la stessa cosa da due lati::

    @ws3   sulla porta MCP il warmup del giudice completa **5 volte su 694** in cinque
           giorni: l'import pigro di `transformers` nel thread manda in timeout la prima
           scrittura.
    io     `W5-31`..`W5-34`: la prima scrittura MCP con fonte **non torna entro 90s**
           (import di `scipy` sullo stesso frame), mentre la seconda costa 0,2s.

⇒ **Un daemon che carica UNA volta e' anche la cura di quel difetto**, non solo del costo
di memoria. Qui si misura quanto costa la PRIMA richiesta di un client nuovo quando il
giudice e' gia' caricato **in un altro processo**.

📌 **PREDIZIONE, scritta prima**: **sotto il secondo**. Il modello e' gia' in memoria
altrove; al client resta un socket e l'attesa dell'inferenza (0,18-0,47s misurati). ⇒ Se
esce sotto 1s, il daemon **abbatte di due ordini di grandezza** il costo che oggi manda in
timeout la prima scrittura.
⇒ Se invece uscisse sopra i 10s, ci sarebbe un costo di connessione che non ho previsto e
la cura varrebbe meno di quanto sembra.

⚠️ **COSA QUESTA MISURA NON E', e va detto prima del numero**: il client qui e' un client
**socket**, non il server MCP del prodotto — che oggi NON parla col daemon, perche' quel
collegamento non esiste ancora. ⇒ Misuro **la componente** che oggi costa >90s (procurarsi
un giudizio la prima volta), non il percorso MCP completo. Il confronto e' onesto solo su
quella componente, e chi legge deve saperlo.

IL DISEGNO::

    ①  il daemon carica il giudice e dichiara la porta        (il costo, UNA volta)
    ②  un client NUOVO si connette e chiede il PRIMO giudizio  <- la misura
    ③  lo stesso client ne chiede altri quattro                (il riferimento a caldo)

⇒ Il ③ serve a distinguere «la prima costa come le altre» da «la prima paga qualcosa».

🟢 ESITO — **da >90s a 0,150s: il daemon cancella il costo della prima scrittura**::

    richiesta    durata     grounding    layers
    #1  (FALSO)  0,150s        0,53      L4-grounding
    #2  (vero)   0,148s       99,67      -
    #3           0,170s        5,60      L4-grounding
    #4           0,155s        1,31      L4-grounding
    #5           0,160s        1,00      L4-grounding

    prima 0,150s   ·   media delle successive 0,158s
    riferimento SENZA daemon (`W5-31`..`34`): la prima scrittura con fonte
    NON torna entro 90s

🔑 **La prima richiesta costa quanto le altre.** Il salto e' di **oltre 600 volte**, e
soprattutto **sparisce la discontinuita'**: oggi il primo write paga un caricamento che le
successive non pagano, ed e' quella asimmetria a mandare in timeout i client. ⇒ Cura il
reperto di @ws3 (**il warmup completa 5 volte su 694 in cinque giorni**) e i miei
`W5-31`..`W5-34`, non solo il costo di memoria.

✅ **E SEPARA, non risponde solo in fretta**: il claim FALSO della prima richiesta prende
**0,53** e accende `L4-grounding`; quello vero prende **99,67** e nessun layer. Un daemon
velocissimo che ammettesse tutto sarebbe un peggioramento travestito da cura — e' la forma
di difetto che ho trovato tre volte oggi, quindi il banco la controlla.

⚠️ **COSA RESTA FUORI DALLA MISURA, e va sottratto all'entusiasmo**::

    import di `verimem.mcp_server` nel client       2,3s   <- NON curato dal daemon
    caricamento del giudice nel daemon              una volta, all'avvio

⇒ Il daemon cancella il costo del **giudice**, non quello del **server MCP**: un client
nuovo paga comunque i suoi 2,3s di import (i 40 moduli non-stdlib di `05b10b66`). ⇒ «Da 90s
a 0,15s» vale per **la componente del giudizio**; il tempo totale del primo write per un
processo nuovo resta ~2,5s. **Che e' comunque due ordini di grandezza meglio di oggi.**

⚖️ E il client qui e' un client **socket**, non il server MCP del prodotto — che oggi NON
parla col daemon, perche' quel collegamento non esiste ancora. Il numero misura cosa
COSTEREBBE, non cosa fa oggi il prodotto.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-m8-la-prima-scrittura-con-il-daemon-caldo.py <venv>
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
import json, socket, sys, threading
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
        with lock:
            g = run_validation_gate(proposition=req["claim"], verified_by=None,
                                    topic=None, agent=None, source=req["fonte"],
                                    ground_write=True)
        conn.sendall((json.dumps({"g": getattr(g, "grounding_score", None),
                                  "layers": [str(w.get("layer")) for w in (g.warnings or [])
                                             if isinstance(w, dict)]}) + "\n").encode())
    except Exception as e:
        try:
            conn.sendall((json.dumps({"errore": str(e)[:60]}) + "\n").encode())
        except Exception:
            pass
    finally:
        conn.close()
s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(32)
open(PORTA_FILE, "w").write(str(s.getsockname()[1]))
while True:
    c, _ = s.accept()
    threading.Thread(target=servi, args=(c,), daemon=True).start()
'''

CLIENT = r'''
import json, socket, sys, time
PORTA, N = int(sys.argv[1]), int(sys.argv[2])
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
# un client MCP vero importa il server: il costo c'e' e va incluso nella PRIMA
t_imp = time.time()
import verimem.mcp_server  # noqa: F401
imp = time.time() - t_imp
# il claim FALSO: cosi' si vede anche se il giudizio SEPARA, non solo se risponde
CLAIM = ["Nella coda ci sono 7777 run in corso."] + [
    "Nella coda ci sono %d run in attesa." % (149 + i) for i in range(N - 1)]
for i, c in enumerate(CLAIM):
    t = time.time()
    s = socket.create_connection(("127.0.0.1", PORTA), timeout=300)
    s.sendall((json.dumps({"claim": c, "fonte": FONTE}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        p = s.recv(65536)
        if not p:
            break
        buf += p
    s.close()
    d = json.loads(buf.decode())
    print("R|%d|%.3f|%s|%s" % (i + 1, time.time() - t, d.get("g"),
                               ",".join(d.get("layers") or []) or "-"), flush=True)
print("IMP|%.3f" % imp, flush=True)
'''


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        return
    base = tempfile.mkdtemp(prefix="ws5_m8_")
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
    print("  ① il daemon carica il giudice (il costo, UNA volta)...")
    t0 = time.time()
    d = subprocess.Popen([py, "-u", fd, pf], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=amb(os.path.join(base, "d")),
                         cwd=os.path.dirname(venv))
    while not os.path.exists(pf) and time.time() - t0 < 900:
        time.sleep(0.3)
    if not os.path.exists(pf):
        d.kill()
        print("  🔴 daemon non pronto entro 900s")
        return
    carico = time.time() - t0
    porta = int(open(pf).read().strip())
    print("     daemon caldo in %.1fs\n" % carico)

    r = subprocess.run([py, "-u", fc, str(porta), "5"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800,
                       env=amb(os.path.join(base, "c")), cwd=os.path.dirname(venv))
    d.kill()
    righe = [x.split("|") for x in (r.stdout or "").splitlines() if x.startswith("R|")]
    imp = next((float(x.split("|")[1]) for x in (r.stdout or "").splitlines()
                if x.startswith("IMP|")), 0.0)
    if not righe:
        print("  🔴 il client non ha prodotto risposte")
        for x in [y for y in (r.stderr or "").splitlines() if y.strip()][-4:]:
            print("     %s" % x[:110])
        return

    print("  ② e ③ le richieste di un client NUOVO (import di mcp_server: %.1fs)\n" % imp)
    print("  %-12s %10s %12s  %s" % ("richiesta", "durata", "grounding", "layers"))
    print("  " + "-" * 58)
    for c in righe:
        print("  %-12s %9.3fs %12s  %s" % ("#" + c[1], float(c[2]), c[3][:10], c[4]))

    prima = float(righe[0][2])
    dopo = [float(c[2]) for c in righe[1:]]
    media_dopo = sum(dopo) / len(dopo) if dopo else 0
    print("\n=== LA PREDIZIONE REGGE? ===")
    print("  predetto: la PRIMA richiesta sotto il secondo")
    print("  misurato: prima %.3fs   ·   media delle successive %.3fs" % (prima, media_dopo))
    print("  riferimento SENZA daemon (W5-31..34): la prima scrittura MCP con fonte")
    print("                                        NON torna entro 90s")
    if prima < 1.0:
        print("\n  🟢 SOTTO IL SECONDO: il daemon abbatte di due ordini di grandezza il")
        print("     costo che oggi manda in timeout la prima scrittura. ⇒ Cura anche il")
        print("     reperto di @ws3 (warmup che completa 5 volte su 694), non solo la")
        print("     memoria.")
    elif prima < 10.0:
        print("\n  🟡 %.1fs: molto meglio dei >90s di oggi, ma non gratis: c'e' un costo" % prima)
        print("     di prima connessione che va nominato.")
    else:
        print("\n  🔴 %.1fs: la prima richiesta costa comunque. Il daemon sposta il" % prima)
        print("     problema invece di curarlo, e la predizione cade.")
    if righe[0][4] not in ("-", ""):
        print("\n  ✅ e il claim FALSO della prima richiesta ha acceso: %s" % righe[0][4])
        print("     ⇒ il daemon non risponde solo in fretta: SEPARA.")
    else:
        print("\n  ⚠️ la prima richiesta (claim FALSO) non ha acceso nessun layer:")
        print("     veloce ma non giudicante — il numero non vale.")


main()
