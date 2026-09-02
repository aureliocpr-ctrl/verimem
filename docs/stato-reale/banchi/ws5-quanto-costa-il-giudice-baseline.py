r"""BASELINE M4 — quanto costa il giudice: RSS per processo e latenza di un giudizio.

Anello ① del muro «il giudice costa»: prima di cercare modelli piu' piccoli o un
servizio condiviso, serve il numero di partenza. Senza baseline, «abbiamo migliorato»
non e' misurabile.

⚠️ **IL NUMERO EREDITATO NON E' MIO**: il mandato cita «~758 MB per processo (misura
tua)». `hippo_facts_search` non lo restituisce, e il gate dichiara «*nessun risultato
supera la soglia di rilevanza: probabilmente la risposta NON e' in memoria*». Le mie
misure della notte erano **357 MB** (processo che ASPETTAVA, giudice non ancora
caricato) e **692 MB**. ⇒ Qui lo misuro invece di ereditarlo.

COSA SI MISURA, e perche' i punti sono quattro::

    ①  RSS all'avvio dell'interprete        il pavimento: quanto costa Python e basta
    ②  RSS dopo `import verimem`            quanto costa il pacchetto senza giudicare
    ③  RSS + latenza del PRIMO giudizio     il caricamento del modello (cold)
    ④  latenza dei giudizi successivi       il costo per giudizio (warm)

⇒ **Il numero che serve alla decisione «8 agenti = 8 processi» e' il DELTA ③-②**, non
l'RSS totale: il pavimento di Python lo paghi comunque, il giudice no.
⇒ E **cold e warm vanno separati**: se il costo fosse tutto nel caricamento, un servizio
condiviso lo pagherebbe UNA volta; se fosse per-giudizio, condividerlo non aiuterebbe.

🔑 **CONTROLLO POSITIVO OBBLIGATORIO**: chiamando `run_validation_gate` direttamente
**senza `ground_write=True` il giudice NON gira**, e il segnale e' `grounding_score=None`
(reperto di @ws2 del 02/09 01:50, che per questo ha quasi pubblicato «il gate lascia
passare 14 falsi su 15»). ⇒ Se il grounding torna `None`, **questa misura non sta
misurando il giudice** e il banco lo dice invece di stampare un numero.

🪞 **E la prima esecuzione e' morta sulla FIRMA**: `run_validation_gate` ha tre
argomenti keyword-only obbligatori (`verified_by`, `topic`, `agent`) che non avevo
passato. `agent` accetta `None` — il giudice locale non ha bisogno di un LLM iniettato —
ma questo l'ho letto **dopo** il traceback invece che prima. E' il secondo errore di
firma sulla stessa API in un giorno (stanotte era `content` invece di `proposition`,
dalla porta MCP). ⇒ **La cura non e' ricordarsi le firme: e' leggerle prima di
chiamare.**

⚙️ RSS letto con `GetProcessMemoryInfo` via `ctypes` (stdlib): `psutil` non e' nel venv
e **non lo installo** — cambiare l'ambiente di misura per misurarlo e' il modo piu'
rapido di misurare un altro ambiente.

✅ ESITO — **baseline misurata, con entrambi i controlli passati**::

    punto                        RSS (MB)      durata
    ① interprete nudo               16.2          —
    ② dopo import verimem           22.8         0.2s
    ③ dopo il 1o giudizio          980.8        31.6s
    ④ dopo 5 giudizi               981.5          —

    costo del GIUDICE (delta ③-②)      957.9 MB
    costo del pacchetto (delta ②-①)      6.6 MB
    latenza 1o giudizio (COLD)           31.6s
    latenza giudizi successivi (WARM)     0.47s   (0.51, 0.57, 0.43, 0.38)

    controllo positivo: grounding 99.67 col giudice acceso  ✅
    controllo negativo: grounding None in 0.01s senza       ✅

🔑 **QUATTRO LETTURE, e la terza e' quella che orienta la ricerca**::

  ① **958 MB, non 758.** Il numero del mandato era sottostimato del **26%**, e non
     l'ho trovato fra i miei fatti. ⇒ 8 agenti = **~7,7 GB** di soli giudici.
  ② **Il pacchetto pesa 6,6 MB.** Verimem senza giudice e' leggerissimo: **il costo e'
     tutto del modello**, non del prodotto. Chi volesse alleggerire deve guardare li'.
  ③ **La memoria NON cresce coi giudizi**: 980.8 -> 981.5 dopo cinque (+0,7 MB), e la
     latenza warm e' **0,47s** contro **31,6s** del primo. ⇒ **Il costo e' tutto nel
     CARICAMENTO, non nell'uso.** E' la lettura che decide fra le due strade: un
     **servizio condiviso** eliminerebbe 7 caricamenti su 8; un **modello piu' piccolo**
     attaccherebbe una spesa (0,47s per giudizio) che gia' costa poco.
  ④ **Il COLD non e' stabile**: **93,6s** nella prima esecuzione, **31,6s** in questa,
     stesso codice e stessa macchina — dipende dalla cache del disco. ⇒ Un numero solo
     su questa riga inganna: va dato **come intervallo**, o con la cache dichiarata.

🪞 **E IL MISURATORE HA SBAGLIATO DUE VOLTE PRIMA DI DIRE IL VERO**::

    ①  non controllavo il valore di ritorno di `GetProcessMemoryInfo` -> struct vuota
       -> **0.0 MB su ogni punto**, stampati come se fossero una misura
    ②  riparato quello, `err=6` ERROR_INVALID_HANDLE: senza `restype` dichiarato,
       `ctypes` **tronca a 32 bit** lo pseudo-handle -1 di `GetCurrentProcess` su
       Windows a 64 bit

⇒ Il primo difetto era **silenzioso** (zeri plausibili a occhio), il secondo **rumoroso**
(un'eccezione). La differenza fra i due l'ha fatta **la guardia**: «*un interprete Python
non sta sotto i 5 MB*». ⇒ **Senza un controllo che DEVE accendersi, avrei consegnato
zeri.** E il misuratore riparato l'ho verificato **da solo** (14,5 MB su un Python nudo)
**prima** di ripagare i 90 secondi del caricamento.

REGIME: `main` installato come pacchetto (verimem 0.7.6), venv fuori dal repo, ambiente
senza `HIPPO_*`/`ENGRAM_*`/`VERIMEM_*` tranne quelle dichiarate, store temporaneo, un
processo per volta.
⚖️ PUNTI DEBOLI: una sola macchina e una sola CPU; un solo claim e una sola fonte (la
latenza puo' dipendere dalla LUNGHEZZA del testo, che qui non varia); e l'RSS su Windows
include pagine condivise fra processi — **il costo di 8 processi non e' 8× l'RSS**, ed e'
esattamente la domanda che l'anello ② dovra' misurare.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-quanto-costa-il-giudice-baseline.py <venv> [n_giudizi]
"""
import os
import subprocess
import sys
import tempfile
import textwrap

DENTRO = r'''
import ctypes, ctypes.wintypes as wt, json, os, sys, time

class _PMC(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]

def rss_mb():
    """RSS del processo CORRENTE. (!) La PRIMA versione non controllava il valore di
    ritorno: la chiamata falliva e leggevo una struct VUOTA, stampando 0.0 MB su ogni
    punto. Un misuratore che non sa dire «ho fallito» stampa zero e sembra una misura.
    Ora: due vie (kernel32 K32..., poi psapi), return controllato, e il chiamante ha
    una GUARDIA — un interprete Python non puo' stare sotto i 5 MB."""
    c = _PMC(); c.cb = ctypes.sizeof(_PMC)
    # (!) SECONDO difetto dello stesso misuratore: senza `restype` dichiarato, ctypes
    # tratta il ritorno come c_int (32 bit) e TRONCA lo pseudo-handle -1 di
    # GetCurrentProcess su Windows a 64 bit -> err=6 ERROR_INVALID_HANDLE.
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    ok = 0
    for dll, nome in ((ctypes.windll.kernel32, "K32GetProcessMemoryInfo"),
                      (ctypes.windll.psapi, "GetProcessMemoryInfo")):
        fn = getattr(dll, nome, None)
        if fn is None:
            continue
        fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMC), wt.DWORD]
        fn.restype = wt.BOOL
        ok = fn(h, ctypes.byref(c), c.cb)
        if ok:
            break
    if not ok:
        raise OSError("GetProcessMemoryInfo ha fallito: err=%d"
                      % ctypes.windll.kernel32.GetLastError())
    return c.WorkingSetSize / (1024 * 1024)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
CLAIM = ["Nella coda ci sono %d run in attesa." % (149 + i) for i in range(N)]

out = {"punti": [], "warm": []}
out["punti"].append(("① interprete nudo", rss_mb(), None))

t = time.time()
from verimem.anti_confab_gate import run_validation_gate
out["punti"].append(("② dopo import verimem", rss_mb(), time.time() - t))

# ③ il PRIMO giudizio: qui il modello si carica
t = time.time()
g1 = run_validation_gate(proposition=CLAIM[0], verified_by=None, topic=None,
                         agent=None, source=FONTE, ground_write=True)
d1 = time.time() - t
out["punti"].append(("③ dopo il 1o giudizio", rss_mb(), d1))
out["grounding_primo"] = getattr(g1, "grounding_score", None)

# ④ i successivi: il modello e' caldo
for c in CLAIM[1:]:
    t = time.time()
    g = run_validation_gate(proposition=c, verified_by=None, topic=None,
                            agent=None, source=FONTE, ground_write=True)
    out["warm"].append((time.time() - t, getattr(g, "grounding_score", None)))
out["punti"].append(("④ dopo %d giudizi" % N, rss_mb(), None))

# CONTROLLO NEGATIVO: senza ground_write il giudice non deve girare (grounding None)
t = time.time()
g0 = run_validation_gate(proposition=CLAIM[0], verified_by=None, topic=None,
                         agent=None, source=FONTE)
out["senza_ground_write"] = (time.time() - t, getattr(g0, "grounding_score", None))

print("JSON|" + json.dumps(out), flush=True)
'''


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv> [n_giudizi]" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    n = sys.argv[2] if len(sys.argv) > 2 else "5"
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        return
    ver = ""
    o = subprocess.run([os.path.join(venv, "Scripts", "pip.exe"), "show", "verimem"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace").stdout
    for riga in o.splitlines():
        if riga.lower().startswith("version:"):
            ver = riga.split(":", 1)[1].strip()

    store = tempfile.mkdtemp(prefix="ws5_costo_")
    script = os.path.join(store, "_dentro.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(DENTRO))
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print("  pacchetto: verimem %s   giudizi: %s" % (ver, n))
    print("  RSS via GetProcessMemoryInfo (stdlib), campionato DENTRO il processo\n")
    r = subprocess.run([py, "-u", script, n], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=3600,
                       env=env, cwd=os.path.dirname(venv))
    riga = next((x for x in (r.stdout or "").splitlines() if x.startswith("JSON|")), "")
    if not riga:
        print("  🔴 nessun risultato. Ultime righe di stderr:")
        for x in [y for y in (r.stderr or "").splitlines() if y.strip()][-6:]:
            print("     %s" % x[:120])
        return
    import json as _j
    d = _j.loads(riga[5:])

    # IL CONTROLLO PRIMA DEL NUMERO: se il giudice non e' girato, non c'e' niente da dire
    g1 = d.get("grounding_primo")
    if g1 is None:
        print("  ⚠️ IL GIUDICE NON E' GIRATO: `grounding_score` e' None sul primo giudizio.")
        print("     Questa misura NON sta misurando il giudice — non pubblicare i MB.")
        print("     (e' il reperto di @ws2 del 02/09 01:50: senza `ground_write=True` il")
        print("      gate e' SPENTO, e il segnale e' esattamente questo `None`.)")
        return
    print("  ✅ controllo positivo: il primo giudizio ha grounding %.2f ⇒ il giudice gira\n" % g1)

    # GUARDIA sul misuratore: un interprete Python non sta sotto i 5 MB. Se ci sta,
    # non ho misurato la memoria — ho letto una struct vuota (mi e' successo).
    _primo = d["punti"][0][1]
    if _primo < 5.0:
        print("  🔴 IL MISURATORE DI RSS E' ROTTO: l'interprete nudo risulta %.1f MB." % _primo)
        print("     Un Python vuoto non sta sotto i 5 MB ⇒ non sto leggendo la memoria.")
        print("     I TEMPI sotto restano validi; i MB NON vanno pubblicati.")
        print()
    print("  %-26s %10s %12s" % ("punto", "RSS (MB)", "durata"))
    print("  " + "-" * 52)
    rss = {}
    for nome, mb, dur in d["punti"]:
        rss[nome[0]] = mb
        print("  %-26s %9.1f %11s" % (nome, mb, ("%.1fs" % dur) if dur else "—"))

    warm = [w[0] for w in d["warm"]]
    print("\n  === I DUE NUMERI CHE SERVONO ===")
    delta = rss.get("③", 0) - rss.get("②", 0)
    print("  costo del GIUDICE (delta ③-②):      %8.1f MB" % delta)
    print("  costo del pacchetto (delta ②-①):    %8.1f MB" % (rss.get("②", 0) - rss.get("①", 0)))
    print("  RSS TOTALE con giudice caricato:     %8.1f MB" % rss.get("③", 0))
    if warm:
        print("  latenza 1o giudizio (COLD):          %8.1fs" % d["punti"][2][2])
        print("  latenza giudizi successivi (WARM):   %8.2fs   (%s)"
              % (sum(warm) / len(warm), ", ".join("%.2f" % w for w in warm)))
        rapporto = d["punti"][2][2] / (sum(warm) / len(warm)) if warm else 0
        print("  il primo costa %.0f volte un giudizio caldo" % rapporto)

    dur0, g0 = d.get("senza_ground_write", (0, None))
    print("\n  === CONTROLLO NEGATIVO (senza ground_write) ===")
    if g0 is None:
        print("  ✅ grounding None in %.2fs ⇒ il giudice NON gira, come atteso." % dur0)
        print("     ⇒ i numeri sopra sono davvero del giudice, non di altro.")
    else:
        print("  ⚠️ grounding %.2f anche SENZA ground_write: il default e' cambiato," % g0)
        print("     e il confronto cold/warm va riletto.")


main()
