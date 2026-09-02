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

📏📏 **E IN INGLESE (05:05, stesse cinque fonti tradotte) — IL DIVARIO DI LINGUA REGGE
SU UNA SECONDA POPOLAZIONE**::

    lingua   A avere+part   B essere+part   C agente aggiunto   totale
    IT           5/5             4/5              4/5           13 su 15   (86,7%)
    EN           2/5             1/5              3/5            6 su 15   (40,0%)
    claim VERI ammessi: 5 su 5 in ENTRAMBE le lingue

⇒ **In italiano passa il doppio abbondante delle falsita' di relazione che passano in
inglese**, con il controllo positivo perfetto da entrambe le parti (nessun falso
allarme, in nessuna lingua).
🔗 **Terza conferma dello stesso divario, e la piu' larga**::

    `W5-36`  mia, 5 coppie          IT 7/10 passano   ·  EN 3/10
    @ws1     sua, 8-10 casi         IT 9/10 passano   ·  EN 6/10
    questo   mia, 5 fonti × 3 forme IT 13/15 passano  ·  EN 6/15

⇒ **Tre popolazioni, due misuratori indipendenti, stessa direzione.** Il reperto non
dipende piu' da una scelta di casi.
⚠️ In inglese `C` (agente aggiunto) passa 3/5 contro `B` 1/5: **un indizio**, non una
separazione — cinque fonti non bastano, e il verdetto lo dice invece di concludere.

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

# ⚠️ LE STESSE CINQUE FONTI IN INGLESE. Non per completezza: `W5-36` ha misurato che il
# gate ferma piu' del doppio delle inversioni in inglese che in italiano, e **la vetrina
# del prodotto e' in inglese**. Se le inversioni passano anche qui, il «13 su 15» non e'
# un fatto dell'italiano — e riguarda gli utenti veri.
FONTI_EN = [
    ("Reviewer Bianchi rejected the proposal from Rossi in committee.",
     "Bianchi rejected the proposal from Rossi.",
     "Bianchi had the proposal rejected by Rossi.",
     "The proposal from Bianchi was rejected by Rossi.",
     "The proposal was rejected by Bianchi."),
    ("The gate of ws3 rejected 12 facts from ws4 during the night shift.",
     "The gate of ws3 rejected 12 facts from ws4.",
     "ws3 had 12 facts rejected by the gate of ws4.",
     "12 facts from ws3 were rejected by the gate of ws4.",
     "12 facts were rejected by the gate of ws4."),
    ("The payment service declined the request from customer Neri.",
     "The service declined the request from Neri.",
     "The service had the request declined by customer Neri.",
     "The request from the service was declined by customer Neri.",
     "The request was declined by customer Neri."),
    ("The Milan team beat the Turin team 3 to 1.",
     "Milan beat Turin 3 to 1.",
     "Milan had the match lost against Turin 3 to 1.",
     "Milan was beaten by the Turin team 3 to 1.",
     "The match was won by the Turin team 3 to 1."),
    ("The compiler reported 7 errors in the module written by Verdi.",
     "The compiler reported 7 errors in the module by Verdi.",
     "The compiler had 7 errors reported by the module of Verdi.",
     "7 errors of the compiler were reported by the module of Verdi.",
     "7 errors were reported by the module of Verdi."),
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
    solo = sys.argv[2].upper() if len(sys.argv) > 2 else ""
    lingue = [("IT", FONTI), ("EN", FONTI_EN)]
    if solo in ("IT", "EN"):
        lingue = [x for x in lingue if x[0] == solo]

    print("  %-4s %-4s %-9s %-13s %-15s %-18s %s"
          % ("#", "lg", "VERO", FORME[0], FORME[1], FORME[2], "fonte"))
    print("  " + "-" * 104)
    passa = {f: 0 for f in FORME}
    veri_ok = 0
    per_lingua = {}
    for lang, fonti in lingue:
        pl = {f: 0 for f in FORME}
        vl = 0
        for i, (fonte, vero, a, b, c) in enumerate(fonti, 1):
            v = una(venv, vero, fonte)
            vl += (v == "ammesso")
            es = []
            for forma, claim in zip(FORME, (a, b, c)):
                e = una(venv, claim, fonte)
                pl[forma] += (e == "ammesso")
                passa[forma] += (e == "ammesso")
                es.append(e)
            print("  %-4d %-4s %-9s %-13s %-15s %-18s %s"
                  % (i, lang, v, es[0], es[1], es[2], fonte[:30]))
        per_lingua[lang] = (vl, pl, len(fonti))
        veri_ok += vl
        print()

    n = sum(len(f) for _l, f in lingue)
    print("=== SINTESI — quante volte la falsita' PASSA ===")
    # ⚠️ PER LINGUA PRIMA CHE AGGREGATA: l'aggregato ha gia' mentito una volta stanotte
    # su questo stesso tema (`W5-36`), e non lo rifaccio.
    for lang, (vl, pl, tot) in per_lingua.items():
        det = " · ".join("%s %d/%d" % (f.split()[0], pl[f], tot) for f in FORME)
        somma = sum(pl.values())
        print("  %s   %s   →  %d su %d passano   (veri ammessi %d/%d)"
              % (lang, det, somma, 3 * tot, vl, tot))
    for f in FORME:
        print("  %-20s passa %d su %d (tutte le lingue)" % (f, passa[f], n))
    print("  claim VERI ammessi (controllo positivo): %d su %d" % (veri_ok, n))
    if len(per_lingua) > 1:
        tot_p = {l: sum(pl.values()) for l, (_v, pl, _t) in per_lingua.items()}
        tot_c = {l: 3 * t for l, (_v, _p, t) in per_lingua.items()}
        ordinate = sorted(per_lingua, key=lambda l: -tot_p[l])
        alto, basso = ordinate[0], ordinate[-1]
        print("\n  📏 INVERSIONI CHE PASSANO, PER LINGUA: %s"
              % " · ".join("%s %d/%d" % (l, tot_p[l], tot_c[l]) for l in per_lingua))
        if tot_p[alto] - tot_p[basso] >= 3:
            print("     🔴 il divario di lingua REGGE anche su questa popolazione: passano")
            print("        %d su %d in %s contro %d su %d in %s."
                  % (tot_p[alto], tot_c[alto], alto, tot_p[basso], tot_c[basso], basso))
        else:
            print("     🪞 nessun divario di lingua qui (%d contro %d): il reperto di `W5-36`"
                  % (tot_p[alto], tot_p[basso]))
            print("        NON si estende a questa popolazione, e va detto.")

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
