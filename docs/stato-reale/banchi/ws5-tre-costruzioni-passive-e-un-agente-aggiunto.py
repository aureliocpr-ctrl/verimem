r"""Quale costruzione passiva fa passare una falsita' di relazione? Tre forme, cinque fonti.

Chiude il debito che avevo dichiarato in `080e4e27`: «*2 su 3 contro 1 su 3 non e'
distinguibile dal rumore ⇒ l'ipotesi «voce passiva» resta NON dimostrata; chi vuole
chiuderla ha la popolazione giusta: stessa inversione, tre costruzioni, ≥10 fonti*».
Avevo scritto «non lo faccio stanotte»: **il tempo c'e', e allora lo faccio** — con
cinque fonti, non dieci, e lo dichiaro.

LE TRE COSTRUZIONI, tutte con **la stessa inversione di relazione** e la stessa fonte::

    A  avere + participio          «Bianchi ha avuto la proposta bocciata da Rossi»
    B  essere + participio         «La proposta di Bianchi e' stata bocciata da Rossi»
    C  essere + AGENTE AGGIUNTO    da una frase che l'agente non ce l'aveva

⇒ **C e' la forma del caso estremo di @ws1** (`18748ec5`): «*128 artefatti sono
classificati VESTITO*» (0,70) → «*128 artefatti **sono stati** classificati VESTITO
**dal censimento***» (99,13), **+98,43 punti**. Li' l'agente non c'era e viene aggiunto.

⚠️ **PERCHE' TRE E NON DUE**: nei miei due banchi precedenti avevo usato **A** in uno e
**B** nell'altro **senza accorgermene**, e i due esiti divergevano. Quella era una mia
variabile libera: qui diventa la variabile misurata.

+ un claim **VERO** per fonte (popolazione positiva): senza, una forma che ferma tutto
sembrerebbe la piu' sicura.

🪞 ESITO — **LA MIA IPOTESI E' FALSIFICATA, e il dato che ne esce e' piu' forte**::

    #   VERO      A avere+part  B essere+part  C agente aggiunto  fonte
    1   ammesso   ammesso       fermato        ammesso            Bianchi / Rossi
    2   ammesso   ammesso       ammesso        ammesso            gate ws3 / ws4
    3   ammesso   ammesso       ammesso        ammesso            servizio / Neri
    4   ammesso   ammesso       ammesso        fermato            Milano / Torino
    5   ammesso   ammesso       ammesso        ammesso            compilatore / Verdi

    A avere+part        passa 5 su 5
    B essere+part       passa 4 su 5
    C agente aggiunto   passa 4 su 5
    claim VERI ammessi (controllo positivo)   5 su 5

⇒ **Le tre costruzioni si comportano UGUALE** (divario 1 su 5). ⇒ **La costruzione NON
era la variabile**, e la spiegazione che avevo dato della divergenza fra i miei due
banchi precedenti — «*avevo cambiato costruzione senza accorgermene*» — **cade**. Era
un'ipotesi ragionevole e sbagliata.

🔑 **MA IL TOTALE DICE LA COSA CHE CONTA: 13 falsita' di relazione su 15 PASSANO**, in
qualunque forma passiva, con il controllo positivo a **5 su 5**. ⇒ **Conferma ① della
matrice** (`080e4e27`: il gate protegge i valori e non le relazioni) su una popolazione
piu' grande e in modo **piu' netto** — li' erano 3 su 6, qui 13 su 15.

⚠️ **E QUELLO CHE NON SO, dopo aver falsificato la mia spiegazione**: **quale** caso
venga fermato. Le due celle che cadono (1B e 4C) non hanno in comune la costruzione, e
la stessa fonte 1 in un altro banco si comportava all'opposto. ⇒ **La variabile e' la
FONTE, o il caso** — e con cinque fonti non lo distinguo. Lo lascio aperto **nominato**,
non spiegato: una spiegazione ragionevole l'ho gia' data una volta stanotte, ed era
falsa.

REGIME: `main` installato (0.7.6), porta CLI, ambiente pulito, store nuovo per claim,
CWD fuori dal repo, un processo per volta.
⚖️ PUNTI DEBOLI: cinque fonti (non dieci), italiano, e «agente aggiunto» richiede una
frase di partenza senza agente — quindi C non e' la stessa frase di A e B, e' la stessa
FALSITA' in una frase diversa. Va letto come tale.

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-tre-costruzioni-passive-e-un-agente-aggiunto.py <venv>
"""
import os
import subprocess
import sys
import tempfile

# (fonte, vero, A avere+part, B essere+part, C essere+agente AGGIUNTO)
FONTI = [
    ("Il revisore Bianchi ha bocciato la proposta di Rossi in commissione.",
     "Bianchi ha bocciato la proposta di Rossi.",
     "Bianchi ha avuto la proposta bocciata da Rossi.",
     "La proposta di Bianchi e' stata bocciata da Rossi.",
     "La proposta e' stata bocciata da Bianchi."),
    ("Il gate di ws3 ha respinto 12 fatti di ws4 durante il turno di notte.",
     "Il gate di ws3 ha respinto 12 fatti di ws4.",
     "ws3 ha avuto 12 fatti respinti dal gate di ws4.",
     "12 fatti di ws3 sono stati respinti dal gate di ws4.",
     "12 fatti sono stati respinti dal gate di ws4."),
    ("Il servizio di pagamento ha rifiutato la richiesta del cliente Neri.",
     "Il servizio ha rifiutato la richiesta di Neri.",
     "Il servizio ha avuto la richiesta rifiutata dal cliente Neri.",
     "La richiesta del servizio e' stata rifiutata dal cliente Neri.",
     "La richiesta e' stata rifiutata dal cliente Neri."),
    ("La squadra di Milano ha battuto la squadra di Torino per 3 a 1.",
     "Milano ha battuto Torino per 3 a 1.",
     "Milano ha avuto la partita persa contro Torino per 3 a 1.",
     "Milano e' stata battuta dalla squadra di Torino per 3 a 1.",
     "La partita e' stata vinta dalla squadra di Torino per 3 a 1."),
    ("Il compilatore ha segnalato 7 errori nel modulo scritto da Verdi.",
     "Il compilatore ha segnalato 7 errori nel modulo di Verdi.",
     "Il compilatore ha avuto 7 errori segnalati dal modulo di Verdi.",
     "7 errori del compilatore sono stati segnalati dal modulo di Verdi.",
     "7 errori sono stati segnalati dal modulo di Verdi."),
]

FORME = ["A avere+part", "B essere+part", "C agente aggiunto"]


def una(venv, claim, fonte):
    store = tempfile.mkdtemp(prefix="ws5_costr_")
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
    print("  %-4s %-9s %-13s %-15s %-18s %s"
          % ("#", "VERO", FORME[0], FORME[1], FORME[2], "fonte"))
    print("  " + "-" * 100)
    passa = {f: 0 for f in FORME}
    veri_ok = 0
    righe = []
    for i, (fonte, vero, a, b, c) in enumerate(FONTI, 1):
        v = una(venv, vero, fonte)
        veri_ok += (v == "ammesso")
        es = []
        for forma, claim in zip(FORME, (a, b, c)):
            e = una(venv, claim, fonte)
            passa[forma] += (e == "ammesso")
            es.append(e)
        righe.append((i, v, es, fonte))
        print("  %-4d %-9s %-13s %-15s %-18s %s" % (i, v, es[0], es[1], es[2], fonte[:34]))

    n = len(FONTI)
    print("\n=== SINTESI — quante volte la falsita' PASSA (su %d fonti) ===" % n)
    for f in FORME:
        print("  %-20s passa %d su %d" % (f, passa[f], n))
    print("  claim VERI ammessi (controllo positivo): %d su %d" % (veri_ok, n))

    print("\n=== VERDETTO ===")
    if veri_ok < n:
        print("  ⚠️ CONTROLLO POSITIVO NON REGGE (%d/%d): il banco misura la severita'," % (veri_ok, n))
        print("     non la costruzione.")
        return
    ordinate = sorted(FORME, key=lambda f: -passa[f])
    peggiore, migliore = ordinate[0], ordinate[-1]
    divario = passa[peggiore] - passa[migliore]
    for f in FORME:
        print("  %-20s %s" % (f, "█" * passa[f] + "·" * (n - passa[f])))
    # ⚠️ con n=5 un divario di 1 o 2 non separa: dirlo, invece di ordinare e concludere
    if divario >= n - 1:
        print("  🔴 LE COSTRUZIONI NON SONO EQUIVALENTI: «%s» fa passare %d su %d,"
              % (peggiore, passa[peggiore], n))
        print("     «%s» solo %d. ⇒ La variabile che avevo lasciato libera fra i due"
              % (migliore, passa[migliore]))
        print("        banchi precedenti E' una variabile: cambiava l'esito.")
    elif divario >= 2:
        print("  🟡 divario di %d su %d fonti fra «%s» e «%s»: e' un INDIZIO, non una"
              % (divario, n, peggiore, migliore))
        print("     separazione. Con cinque fonti non lo chiamo risultato.")
    else:
        print("  🪞 LE TRE COSTRUZIONI SI COMPORTANO UGUALE (divario %d su %d):" % (divario, n))
        print("     la costruzione NON era la variabile, e la divergenza fra i miei due")
        print("     banchi va spiegata altrove — le fonti, o il caso.")


main()
