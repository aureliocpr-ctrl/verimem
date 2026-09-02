r"""Il daemon cade a meta' corsa: la scrittura prosegue? E la ricevuta lo DICHIARA?

Il ramo che ho dichiarato quattro volte e mai provato. E' il piu' importante del disegno,
perche' un fallback **silenzioso** trasformerebbe «il daemon non risponde» in «il fatto e'
stato giudicato» — la bugia che questo prodotto esiste per non dire.

⚠️ **E il prototipo del fallback NON esisteva**: nei banchi precedenti il client parlava
col daemon e basta. Qui la logica c'e' — prova il socket, se cade carica in-process — e
**si misura anche quanto costa**, che e' il numero che nessuno ha ancora.

📌 **PREDIZIONE, scritta prima**::

    ①  la scrittura PROSEGUE                        (il fallback funziona)
    ②  la ricevuta lo dichiara                      (perche' lo scrivo io: e' il punto)
    ③  la PRIMA richiesta dopo la caduta costa
        **16-54 secondi**, non 0,15                 <- il costo nascosto

**Il perche' della ③**: il client che ricade in-process paga il caricamento del modello
(16,2-54,1 s misurati in `c8830190` e `e0df50c8`). ⇒ Un daemon che muore non degrada
dolcemente: **trasforma una richiesta da 0,15 s in una da mezzo minuto**, e ogni client
che ricade ne carica **una copia propria** — cioe' torna esattamente il costo di memoria
che il daemon esisteva per togliere.
⇒ Se mi sbaglio e il fallback costa poco, il daemon e' piu' robusto di quanto pensi.
⇒ Se ho ragione, il disegno per la 0.8.0 ha bisogno di una riga in piu': **cosa fare
quando il daemon cade sotto carico** — riavviarlo, o accettare che N client carichino N
modelli.

IL DISEGNO DELLA MISURA::

    ①  daemon caldo, client che fa 8 richieste
    ②  dopo la 4a, il daemon viene UCCISO
    ③  le richieste 5-8 devono: riuscire · dichiarare il fallback · e si misura il tempo

🔑 **I due controlli che rendono leggibile il verdetto**::

    la ricevuta porta `via` = "daemon" | "in-process"    <- senza, «ha funzionato» non
                                                            distingue chi ha giudicato
    il claim FALSO resta fermato ANCHE nel fallback       <- un fallback che ammette
                                                            tutto e' peggio di un errore

🟢🔴 ESITO — **il fallback funziona e GIUDICA; ma il daemon che cade non degrada
dolcemente**::

    #   durata      via          grounding   layers          atteso
    1    0,158s   daemon            0,53     L4-grounding    fermato
    2    0,160s   daemon           99,24     -               ammesso
    3    0,159s   daemon            0,53     L4-grounding    fermato
    4    0,159s   daemon           99,67     -               ammesso
        ⚡ daemon UCCISO
    5   16,195s   in-process        0,53     L4-grounding    fermato
    6    2,192s   in-process       99,24     -               ammesso
    7    2,283s   in-process        0,53     L4-grounding    fermato
    8    2,267s   in-process       99,67     -               ammesso

✅ **① la scrittura prosegue**: 4 servite dal daemon, 4 dal fallback, **zero perdite**.
✅ **② la ricevuta lo dichiara**: ogni riga porta `via` = `daemon` | `in-process`. Senza
   quel campo «ha funzionato» non direbbe **chi** ha giudicato — ed e' tutto il punto.
✅ **④ e il fallback GIUDICA, non risponde soltanto**: i falsi restano a **0,53** con
   `L4-grounding`, i veri a **99,24** e **99,67** senza layer. Un fallback che rispondesse
   ammettendo tutto sarebbe peggio di un errore, perche' l'errore almeno si vede.

🔴 **③ IL COSTO, ed e' il reperto**::

    via daemon (media)          0,159s
    PRIMA in-process           16,195s     <- paga il caricamento del modello
    successive in-process       2,247s     <- e restano 14 VOLTE il daemon

⇒ **Un daemon che muore trasforma una richiesta da 0,16s in una da 16s**, cento volte. E
il costo non finisce li': **ogni client che ricade carica una copia PROPRIA del modello**
⇒ torna esattamente la spesa di memoria che il daemon esisteva per togliere. Con 8 client
che ricadono insieme, si passa da 1 copia a 8 nel giro di una richiesta.
📌 E il dato che non avevo previsto: **anche a regime** il fallback in-process costa
**2,25s contro 0,16s**. Il daemon non e' solo un risparmio di memoria: e' piu' veloce
**quattordici volte** a parita' di modello caricato.

⇒ **IL DISEGNO 0.8.0 HA BISOGNO DI UNA RIGA IN PIU'**: cosa fare quando il daemon cade
sotto carico. Le tre vie, e nessuna e' gratis:
  · **riavviarlo** (chi? il primo client che lo trova morto? e gli altri sette intanto?)
  · **accettare N copie** (torna il costo di memoria, ma il servizio non si ferma)
  · **rifiutare la scrittura** (mai: il prodotto ammetterebbe di non sapere giudicare)

🪞 **E il banco ha sbagliato al primo giro, contro il prodotto**: generavo i claim «veri»
come `149 + i` — cioe' **150, 152, 154** — mentre la fonte dice **149**. Erano falsi anche
quelli, il gate li fermava giustamente, e il verdetto stampava «**4 verdetti sbagliati**»
che erano **miei**. ⇒ I claim veri devono citare i numeri della fonte **esatti**, non
numeri vicini: un numero adiacente non e' una verita' piu' debole, e' una falsita'.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-fallback-quando-il-daemon-cade.py <venv>
"""
import json
import os
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
        conn.sendall((json.dumps({
            "g": getattr(g, "grounding_score", None),
            "layers": [str(w.get("layer")) for w in (g.warnings or [])
                       if isinstance(w, dict)]}) + "\n").encode())
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
PORTA, N, UCCIDI_DOPO = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
SEGNALE = sys.argv[4]
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")

def via_daemon(claim):
    s = socket.create_connection(("127.0.0.1", PORTA), timeout=30)
    s.sendall((json.dumps({"claim": claim, "fonte": FONTE}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        p = s.recv(65536)
        if not p:
            raise ConnectionError("il daemon ha chiuso senza rispondere")
        buf += p
    s.close()
    return json.loads(buf.decode())

def in_process(claim):
    # IL FALLBACK: costa il caricamento del modello, ed e' il punto della misura
    from verimem.anti_confab_gate import run_validation_gate
    g = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=FONTE, ground_write=True)
    return {"g": getattr(g, "grounding_score", None),
            "layers": [str(w.get("layer")) for w in (g.warnings or [])
                       if isinstance(w, dict)]}

# alterna VERO e FALSO: un fallback che ammette tutto va visto, non solo uno che risponde.
# (!) La prima versione generava `149 + i` per i claim "veri" — cioe' 150, 152, 154...
# mentre la fonte dice 149. Erano FALSI anche quelli, il gate li fermava giustamente, e il
# banco segnalava «4 verdetti sbagliati» che erano MIEI. I claim veri devono citare i
# numeri della fonte ESATTI, non numeri vicini.
CLAIM = []
_VERI = ["Nella coda ci sono 149 run in attesa.",
         "Nella coda ci sono 3 run in corso.",
         "Nella coda ci sono 2557 run completati.",
         "Nella coda ci sono 149 run in attesa."]
for i in range(N):
    CLAIM.append("Nella coda ci sono 7777 run in corso." if i % 2 == 0
                 else _VERI[(i // 2) % len(_VERI)])

for i, c in enumerate(CLAIM, 1):
    if i == UCCIDI_DOPO + 1:
        open(SEGNALE, "w").write("1")     # chiedo al padre di uccidere il daemon
        time.sleep(2.0)                    # ...e gli do' il tempo di farlo
    t = time.time()
    via, errore = "daemon", ""
    try:
        d = via_daemon(c)
    except Exception as e:
        errore = type(e).__name__
        try:
            d = in_process(c)
            via = "in-process"             # <- LA DICHIARAZIONE, che e' il punto
        except Exception as e2:
            d = {"g": None, "layers": []}
            via = "FALLITA(%s)" % type(e2).__name__
    atteso = "fermato" if "7777" in c else "ammesso"
    print("R|%d|%.3f|%s|%s|%s|%s|%s" % (
        i, time.time() - t, via, d.get("g"),
        ",".join(d.get("layers") or []) or "-", atteso, errore), flush=True)
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
    base = tempfile.mkdtemp(prefix="ws5_fb_")
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

    pf, segnale = os.path.join(base, "PORTA"), os.path.join(base, "UCCIDI")
    print("  avvio il daemon...")
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
    porta = int(open(pf).read().strip())
    print("  daemon caldo in %.1fs — verra' UCCISO dopo la 4a richiesta\n" % (time.time() - t0))

    cp = subprocess.Popen([py, "-u", fc, str(porta), "8", "4", segnale],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, encoding="utf-8", errors="replace",
                          env=amb(os.path.join(base, "c")), cwd=os.path.dirname(venv))
    # il padre aspetta il segnale e uccide il daemon a due gambe
    ucciso_a = None
    t0 = time.time()
    while cp.poll() is None and time.time() - t0 < 1800:
        if os.path.exists(segnale) and ucciso_a is None:
            d.kill()
            d.wait(timeout=30)
            ucciso_a = time.time()
            print("  ⚡ daemon UCCISO (pid morto: %s)\n" % (d.poll() is not None))
        time.sleep(0.2)
    out, _ = cp.communicate(timeout=300)
    if d.poll() is None:
        d.kill()

    righe = [x.split("|") for x in (out or "").splitlines() if x.startswith("R|")]
    if not righe:
        print("  🔴 il client non ha prodotto risposte")
        return
    print("  %-4s %10s %-12s %11s %-16s %-9s %s"
          % ("#", "durata", "via", "grounding", "layers", "atteso", "errore"))
    print("  " + "-" * 82)
    for c in righe:
        print("  %-4s %9.3fs %-12s %11s %-16s %-9s %s"
              % (c[1], float(c[2]), c[3], (c[4] or "")[:10], c[5][:16], c[6], c[7]))

    prima_del_calo = [r for r in righe if r[3] == "daemon"]
    dopo = [r for r in righe if r[3] != "daemon"]
    print("\n=== ① LA SCRITTURA PROSEGUE? ===")
    fallite = [r for r in righe if r[3].startswith("FALLITA")]
    if fallite:
        print("  🔴 %d richieste FALLITE del tutto: il fallback non ha retto." % len(fallite))
    elif dopo:
        print("  ✅ si': %d richieste servite dal daemon, %d dal fallback in-process,"
              % (len(prima_del_calo), len(dopo)))
        print("     zero perdite.")
    else:
        print("  ⚠️ nessuna richiesta e' passata dal fallback: il daemon non e' stato")
        print("     ucciso in tempo, e la misura NON ha provato il ramo che voleva.")
        return

    print("\n=== ② LA RICEVUTA LO DICHIARA? ===")
    print("  ✅ ogni riga porta `via`: %s"
          % ", ".join(sorted({r[3] for r in righe})))
    print("  ⇒ chi legge la ricevuta distingue CHI ha giudicato. Senza questo campo,")
    print("     «ha funzionato» non direbbe se il giudice c'era davvero.")

    print("\n=== ③ QUANTO COSTA IL FALLBACK? ===")
    t_daemon = [float(r[2]) for r in prima_del_calo]
    t_primo_fb = float(dopo[0][2])
    t_dopo = [float(r[2]) for r in dopo[1:]]
    print("  via daemon (media):        %7.3fs" % (sum(t_daemon) / len(t_daemon) if t_daemon else 0))
    print("  PRIMA in-process:          %7.3fs   <- paga il caricamento" % t_primo_fb)
    if t_dopo:
        print("  successive in-process:     %7.3fs" % (sum(t_dopo) / len(t_dopo)))
    if t_primo_fb > 10:
        print("  🔴 il daemon che cade NON degrada dolcemente: una richiesta da %.2fs"
              % (sum(t_daemon) / len(t_daemon) if t_daemon else 0))
        print("     diventa da %.0fs. E ogni client che ricade carica una copia PROPRIA" % t_primo_fb)
        print("     del modello ⇒ torna il costo di memoria che il daemon toglieva.")
        print("  ⇒ Il disegno 0.8.0 ha bisogno di una riga in piu': cosa fare quando il")
        print("     daemon cade sotto carico (riavviarlo? accettare N copie?).")
    else:
        print("  🟢 il fallback costa %.2fs: il daemon e' piu' robusto di quanto predicessi."
              % t_primo_fb)

    print("\n=== IL CONTROLLO CHE CONTA PIU' DI TUTTI ===")
    sbagliate = [r for r in righe
                 if (r[6] == "fermato" and not r[5].strip("-"))
                 or (r[6] == "ammesso" and r[5].strip("-"))]
    if sbagliate:
        print("  🔴 %d richieste col verdetto SBAGLIATO:" % len(sbagliate))
        for r in sbagliate:
            print("     #%s via %s: atteso %s, layers=%s" % (r[1], r[3], r[6], r[5]))
        print("  ⇒ Un fallback che risponde ma NON separa e' peggio di un errore.")
    else:
        print("  ✅ tutti i verdetti corretti, ANCHE nel fallback: i claim falsi restano")
        print("     fermati e i veri passano. Il fallback giudica, non solo risponde.")


main()
