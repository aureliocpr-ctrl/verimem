r"""La stessa falsita' passa se la scrivi al passivo? Un caso non basta: cinque coppie.

In `ws5-la-classe-delle-relazioni-...` ho trovato **un** caso in cui la stessa inversione
di soggetto viene fermata in forma **attiva** e ammessa in forma **passiva**::

    R1  «Il gate di ws4 ha respinto 12 fatti di ws3»       attiva   FERMATO   g= 26.81
    R2  «ws3 ha avuto 12 fatti respinti dal gate di ws4»   passiva  AMMESSO   g= 99.69

**Un caso non e' una classe.** @ws1 stanotte se l'e' detto e ha costruito la popolazione:
faccio lo stesso, prima di consegnare l'ipotesi «la voce passiva e' il confine».

LA MISURA — **cinque coppie**, ognuna la STESSA inversione scritta due volte::

    per ogni coppia:   A) attiva invertita     B) passiva invertita
    + per ogni fonte:  V) un claim VERO        (popolazione positiva)

⇒ Se il confine e' la forma, le B passano e le A no, **sistematicamente**.
⇒ Se invece passano un po' l'una e un po' l'altra, **il mio caso era rumore** e la
   spiegazione «voce passiva» va ritirata prima ancora di essere pubblicata.

PORTA: **CLI su `main` installato** — la piu' sfavorevole alla mia ipotesi, perche' e'
li' che il gate ferma di piu' (nel banco precedente la CLI fermava R1 e R3 e lasciava
passare solo R2).

🔴 ESITO — **non era rumore: la passiva non viene fermata MAI**::

    #   VERO      ATTIVA    PASSIVA   fonte
    1   ammesso   fermato   ammesso   Il gate di ws3 ha respinto 12 fatti di ws4…
    2   ammesso   fermato   ammesso   Il revisore Bianchi ha bocciato la proposta…
    3   ammesso   ammesso   ammesso   Il servizio di pagamento ha rifiutato…
    4   ammesso   fermato   ammesso   La squadra di Milano ha battuto Torino 3 a 1
    5   ammesso   ammesso   ammesso   Il compilatore ha segnalato 7 errori…

    claim VERI ammessi (controllo positivo)   5 su 5   ✅
    inversioni ATTIVE  fermate                3 su 5
    inversioni PASSIVE fermate                0 su 5

⇒ **La stessa falsita', riscritta al passivo, passa cinque volte su cinque.** In forma
attiva il gate ne ferma tre. **La voce passiva azzera la difesa.**

⚠️ **E il gate non e' comunque affidabile sulle attive**: 2 coppie su 5 (#3 e #5) passano
in **entrambe** le forme. ⇒ La passiva e' **peggiore**, non e' **l'unica** falla — dirla
come «l'unica» sarebbe piu' forte di cio' che ho misurato.

✅ **Il controllo positivo regge (5/5)**: il banco non e' semplicemente severo, separa.
E le tre coppie che divergono sono elencate una per una: **un conteggio non si riconosce
a occhio, un elenco si'.**

⚖️ PUNTI DEBOLI: cinque coppie non sono un corpus; le fonti sono mie e in italiano;
e «passiva» qui e' una costruzione con «ha avuto … da / e' stato … da», non l'unica
forma passiva possibile — un'altra costruzione potrebbe dare un altro numero.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-voce-passiva-e-il-confine-o-era-un-caso.py <venv>
"""
import os
import subprocess
import sys
import tempfile

# (fonte, claim VERO, inversione ATTIVA, inversione PASSIVA)
COPPIE = [
    ("Il gate di ws3 ha respinto 12 fatti di ws4 durante il turno di notte.",
     "Il gate di ws3 ha respinto 12 fatti.",
     "Il gate di ws4 ha respinto 12 fatti di ws3.",
     "ws3 ha avuto 12 fatti respinti dal gate di ws4."),
    ("Il revisore Bianchi ha bocciato la proposta di Rossi in commissione.",
     "Bianchi ha bocciato la proposta di Rossi.",
     "Il revisore Rossi ha bocciato la proposta di Bianchi.",
     "Bianchi ha avuto la proposta bocciata da Rossi."),
    ("Il servizio di pagamento ha rifiutato la richiesta del cliente Neri.",
     "Il servizio ha rifiutato la richiesta di Neri.",
     "Il cliente Neri ha rifiutato la richiesta del servizio di pagamento.",
     "Il servizio di pagamento ha avuto la richiesta rifiutata dal cliente Neri."),
    ("La squadra di Milano ha battuto la squadra di Torino per 3 a 1.",
     "Milano ha battuto Torino per 3 a 1.",
     "La squadra di Torino ha battuto la squadra di Milano per 3 a 1.",
     "Milano e' stata battuta dalla squadra di Torino per 3 a 1."),
    ("Il compilatore ha segnalato 7 errori nel modulo scritto da Verdi.",
     "Il compilatore ha segnalato 7 errori.",
     "Il modulo di Verdi ha segnalato 7 errori nel compilatore.",
     "Il compilatore ha avuto 7 errori segnalati dal modulo di Verdi."),
]


def una(venv, claim, fonte):
    store = tempfile.mkdtemp(prefix="ws5_voce_")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([os.path.join(venv, "Scripts", "verimem.exe"), "remember", claim,
                        "--source", fonte], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env,
                       cwd=os.path.dirname(venv))
    out = (r.stdout or "") + (r.stderr or "")
    return "fermato" if "quarantin" in out or "reject" in out else "ammesso"


def main():
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    if not os.path.exists(os.path.join(venv, "Scripts", "verimem.exe")):
        print("  🔴 venv assente: %s" % venv)
        return
    print("  %-4s %-9s %-9s %-9s  %s" % ("#", "VERO", "ATTIVA", "PASSIVA", "fonte"))
    print("  " + "-" * 92)
    att_ferm = pas_ferm = veri_ok = 0
    righe = []
    for i, (fonte, vero, attiva, passiva) in enumerate(COPPIE, 1):
        v = una(venv, vero, fonte)
        a = una(venv, attiva, fonte)
        p = una(venv, passiva, fonte)
        veri_ok += (v == "ammesso")
        att_ferm += (a == "fermato")
        pas_ferm += (p == "fermato")
        righe.append((i, v, a, p, fonte))
        print("  %-4d %-9s %-9s %-9s  %s" % (i, v, a, p, fonte[:44]))

    n = len(COPPIE)
    print("\n=== SINTESI ===")
    print("  claim VERI ammessi (controllo positivo): %d su %d" % (veri_ok, n))
    print("  inversioni ATTIVE  fermate:              %d su %d" % (att_ferm, n))
    print("  inversioni PASSIVE fermate:              %d su %d" % (pas_ferm, n))

    print("\n=== VERDETTO ===")
    if veri_ok < n:
        print("  ⚠️ IL CONTROLLO POSITIVO NON REGGE (%d/%d veri ammessi): un banco in cui" % (veri_ok, n))
        print("     cadono anche i veri non misura la forma, misura la severita'.")
    elif att_ferm - pas_ferm >= 3:
        print("  🔴 LA VOCE PASSIVA E' IL CONFINE: %d attive fermate contro %d passive."
              % (att_ferm, pas_ferm))
        print("     ⇒ Riscrivere la stessa falsita' al passivo la fa passare. Non e'")
        print("        cecita' alle relazioni: e' sensibilita' alla FORMA.")
    elif att_ferm == pas_ferm:
        print("  🪞 NESSUNA DIFFERENZA (%d e %d): il mio caso singolo era RUMORE." % (att_ferm, pas_ferm))
        print("     L'ipotesi «la voce passiva» si ritira qui, prima di essere pubblicata.")
    else:
        print("  🟡 differenza piccola (%d attive contro %d passive): su cinque coppie non"
              % (att_ferm, pas_ferm))
        print("     basta a chiamarla classe. Serve una popolazione piu' grande, oppure")
        print("     la spiegazione e' un'altra.")
    # stampa CHI cade: un conteggio non si riconosce a occhio, un elenco si'
    diverse = [(i, a, p, f) for i, _v, a, p, f in righe if a != p]
    if diverse:
        print("\n  le coppie in cui attiva e passiva DIVERGONO:")
        for i, a, p, f in diverse:
            print("    #%d  attiva=%-9s passiva=%-9s  %s" % (i, a, p, f[:46]))


main()
