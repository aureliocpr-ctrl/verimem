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

🪞🔴 ESITO DEFINITIVO (A/B **nella stessa esecuzione**, 04:38) — **la mia conclusione
era vera solo in ITALIANO, e il reperto grosso e' un altro**::

    lingua   veri ammessi   attive fermate   passive fermate   divario
    IT            5/5            3/5              0/5             3
    EN            5/5            4/5              3/5             1

⇒ **L'effetto-passiva e' forte in italiano e quasi assente in inglese** (4 contro 3 su
cinque coppie non e' distinguibile dal rumore).
⚠️⚠️ **E LA PRIMA VERSIONE DI QUESTO BANCO LEGGEVA L'AGGREGATO**: «7 attive contro 3
passive ⇒ la passiva e' il confine». **Falso**: somma due popolazioni che si comportano
in modo diverso. E' **la stessa forma che @ws4 ha registrato in `W7-31`** — «*la lettura
AGGREGATA dice il contrario di quella per strato*» — commessa da me, sul mio banco,
poche ore dopo averla letta. ⇒ Il verdetto ora **stampa per lingua e rifiuta di
aggregare**.

📏 **IL REPERTO PIU' SOLIDO, perche' non dipende dalla forma** — inversioni fermate in
totale (attive + passive)::

    IT   3 su 10          EN   7 su 10

⇒ **Il gate ferma piu' del DOPPIO delle inversioni in inglese che in italiano.**
✅ **Confermato indipendentemente da @ws1 alle 04:36**, su una sua popolazione diversa
(soggetto scambiato): «*9/10 passano in IT, 6/10 in EN*» — stessa direzione, e con in
piu' un suo caso citato quattro volte che **in inglese e' fermato (1,61)**.
⇒ Due misure indipendenti, due popolazioni, stessa direzione.
✅ **Controllo positivo: 10 veri su 10 ammessi**, in entrambe le lingue — zero falsi
allarmi, e va detto con la stessa forza.

--- (il primo giro, solo italiano, che aveva portato alla conclusione troppo forte) ---
🔴 **non era rumore: la passiva non viene fermata MAI** (IT)::

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

# ⚠️ DUE LINGUE, e non per completezza: il prodotto e' documentato in INGLESE, e i
# reperti di @ws1 e @ws4 sono in inglese. Una misura solo italiana direbbe di una
# lingua che i suoi utenti non usano — e «lista monolingue» e' una delle forme in cui
# ci siamo gia' sbagliati. Le coppie EN sono le stesse IT, tradotte.
# (fonte, claim VERO, inversione ATTIVA, inversione PASSIVA)
COPPIE_EN = [
    ("The gate of ws3 rejected 12 facts from ws4 during the night shift.",
     "The gate of ws3 rejected 12 facts.",
     "The gate of ws4 rejected 12 facts from ws3.",
     "ws3 had 12 facts rejected by the gate of ws4."),
    ("Reviewer Bianchi rejected the proposal from Rossi in committee.",
     "Bianchi rejected the proposal from Rossi.",
     "Reviewer Rossi rejected the proposal from Bianchi.",
     "Bianchi had the proposal rejected by Rossi."),
    ("The payment service declined the request from customer Neri.",
     "The service declined the request from Neri.",
     "Customer Neri declined the request from the payment service.",
     "The payment service had the request declined by customer Neri."),
    ("The Milan team beat the Turin team 3 to 1.",
     "Milan beat Turin 3 to 1.",
     "The Turin team beat the Milan team 3 to 1.",
     "Milan was beaten by the Turin team 3 to 1."),
    ("The compiler reported 7 errors in the module written by Verdi.",
     "The compiler reported 7 errors.",
     "The module by Verdi reported 7 errors in the compiler.",
     "The compiler had 7 errors reported by the module of Verdi."),
]

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
    solo = sys.argv[2].upper() if len(sys.argv) > 2 else ""
    lingue = [("IT", COPPIE), ("EN", COPPIE_EN)]
    if solo in ("IT", "EN"):
        lingue = [x for x in lingue if x[0] == solo]

    print("  %-4s %-6s %-9s %-9s %-9s  %s"
          % ("#", "lingua", "VERO", "ATTIVA", "PASSIVA", "fonte"))
    print("  " + "-" * 96)
    att_ferm = pas_ferm = veri_ok = 0
    per_lingua = {}
    righe = []
    for lang, coppie in lingue:
        av = pv = vv = 0
        for i, (fonte, vero, attiva, passiva) in enumerate(coppie, 1):
            v = una(venv, vero, fonte)
            a = una(venv, attiva, fonte)
            p = una(venv, passiva, fonte)
            vv += (v == "ammesso"); av += (a == "fermato"); pv += (p == "fermato")
            righe.append((i, lang, v, a, p, fonte))
            print("  %-4d %-6s %-9s %-9s %-9s  %s" % (i, lang, v, a, p, fonte[:40]))
        per_lingua[lang] = (vv, av, pv, len(coppie))
        veri_ok += vv; att_ferm += av; pas_ferm += pv
        print()

    n = sum(len(c) for _l, c in lingue)
    print("=== SINTESI ===")
    # ⚠️ per LINGUA prima che aggregata: un aggregato mescola due popolazioni e puo'
    # nascondere che una delle due si comporti all'opposto.
    for lang, (vv, av, pv, tot) in per_lingua.items():
        print("  %s   veri ammessi %d/%d · attive fermate %d/%d · passive fermate %d/%d"
              % (lang, vv, tot, av, tot, pv, tot))
    print("  --")
    print("  claim VERI ammessi (controllo positivo): %d su %d" % (veri_ok, n))
    print("  inversioni ATTIVE  fermate:              %d su %d" % (att_ferm, n))
    print("  inversioni PASSIVE fermate:              %d su %d" % (pas_ferm, n))

    print("\n=== VERDETTO ===")
    # ⚠️⚠️ IL VERDETTO SI LEGGE PER LINGUA, MAI AGGREGATO. La prima versione di questo
    # banco sommava IT+EN e concludeva «7 attive contro 3 passive ⇒ la passiva e' il
    # confine»: FALSO, perche' mescola due popolazioni che si comportano in modo
    # diverso (IT 3-vs-0, EN 4-vs-3). E' la stessa forma che @ws4 ha registrato in
    # `W7-31` — «la lettura AGGREGATA dice il contrario di quella per strato».
    if veri_ok < n:
        print("  ⚠️ IL CONTROLLO POSITIVO NON REGGE (%d/%d veri ammessi): un banco in cui" % (veri_ok, n))
        print("     cadono anche i veri non misura la forma, misura la severita'.")
        return
    forte = [l for l, (_v, av, pv, t) in per_lingua.items() if av - pv >= 3]
    debole = [l for l, (_v, av, pv, t) in per_lingua.items() if 0 <= av - pv <= 1]
    for lang, (_v, av, pv, tot) in per_lingua.items():
        verso = ("🔴 la passiva AZZERA la difesa" if av - pv >= 3
                 else "🟡 differenza di %d: su %d coppie non e' distinguibile dal rumore"
                      % (av - pv, tot))
        print("  %s   attive %d/%d · passive %d/%d   %s" % (lang, av, tot, pv, tot, verso))
    if forte and debole:
        print("  ⇒ **L'EFFETTO NON E' LO STESSO NELLE DUE LINGUE**: forte in %s, quasi"
              % ", ".join(forte))
        print("     assente in %s. Un aggregato direbbe «la passiva e' il confine» e" % ", ".join(debole))
        print("     nasconderebbe proprio questo.")
    if len(per_lingua) > 1:
        tot_ferm = {l: (av + pv) for l, (_v, av, pv, _t) in per_lingua.items()}
        tot_casi = {l: 2 * t for l, (_v, _a, _p, t) in per_lingua.items()}
        righe = ["%s %d/%d" % (l, tot_ferm[l], tot_casi[l]) for l in per_lingua]
        print("\n  📏 INVERSIONI FERMATE IN TOTALE (attive + passive): %s" % " · ".join(righe))
        vals = sorted(per_lingua, key=lambda l: tot_ferm[l])
        if tot_ferm[vals[-1]] >= 2 * max(tot_ferm[vals[0]], 1):
            print("     ⇒ 🔴 il gate ferma piu' del DOPPIO delle inversioni in %s che in %s."
                  % (vals[-1], vals[0]))
            print("        La difesa e' molto piu' debole nella lingua in cui il prodotto")
            print("        non e' stato costruito — ed e' un reperto piu' solido")
            print("        dell'effetto-passiva, perche' non dipende dalla forma.")
    # stampa CHI cade: un conteggio non si riconosce a occhio, un elenco si'
    diverse = [(i, l, a, p, f) for i, l, _v, a, p, f in righe if a != p]
    if diverse:
        print("\n  le coppie in cui attiva e passiva DIVERGONO:")
        for i, l, a, p, f in diverse:
            print("    #%d %s  attiva=%-9s passiva=%-9s  %s" % (i, l, a, p, f[:44]))


main()
