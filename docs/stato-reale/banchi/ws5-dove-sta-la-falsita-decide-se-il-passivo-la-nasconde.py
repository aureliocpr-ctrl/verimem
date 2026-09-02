r"""Il passivo nasconde una falsita' di RELAZIONE, non una di VALORE. Matrice 2×2.

Stanotte due misure hanno dato numeri opposti sulla stessa ipotesi::

    io    (`d918c647`)  inversioni riscritte al passivo: **0 su 5 fermate**
    @ws1  (`18748ec5`)  sue frasi gia' fermate, riscritte al passivo: **7 su 8 restano
                        fermate** — ma l'unica che passa salta da **0,70 a 99,13**
                        aggiungendo l'agente (**+98,43**)

@ws1 ne ha tratto la lettura migliore: «*il passivo con agente e' UNA delle formulazioni
capaci di ribaltare l'esito, non il confine che separa le due popolazioni*». **Ha
ragione.** Ma allora **quale e' il confine?**

L'IPOTESI, e viene dalla differenza fra le due popolazioni::

    i miei casi   la falsita' sta nella RELAZIONE   (chi ha fatto cosa a chi)
    i suoi casi   la falsita' sta nel VALORE        (un numero sbagliato)

⇒ **Il passivo altera la struttura relazionale della frase, non i suoi numeri.** Dove la
falsita' STA nella relazione, riscriverla al passivo la nasconde; dove sta nel valore,
il numero resta sbagliato e il giudice lo vede comunque.

PREDIZIONE, scritta PRIMA di eseguire, cosi' l'esito puo' smentirla::

    relazione + attiva    fermata
    relazione + passiva   PASSA        <- l'unica cella che deve cadere
    valore    + attiva    fermata
    valore    + passiva   fermata

⇒ Se cadono **due** celle su quattro (anche `valore+passiva`), l'ipotesi e' sbagliata e
il passivo nasconde tutto. Se non ne cade **nessuna**, il fenomeno non e' in queste
fonti e va cercato altrove.

LA MISURA: **tre fonti**, ognuna con due entita' che possono scambiarsi e un numero.
Per ogni fonte **cinque claim**: un VERO (controllo positivo) e le quattro celle.

REGIME: `main` installato (0.7.6), porta CLI, ambiente pulito, store nuovo per claim,
CWD fuori dal repo.
⚖️ PUNTI DEBOLI: tre fonti in italiano; «passiva» e' **una** costruzione (con agente
esplicito); e le due dimensioni non sono perfettamente indipendenti — una frase con la
relazione invertita e' anche, in un certo senso, «un altro fatto».

RIPRODUCI:
  python docs/stato-reale/banchi/ws5-dove-sta-la-falsita-decide-se-il-passivo-la-nasconde.py <venv>
"""
import os
import subprocess
import sys
import tempfile

# (fonte, vero, relazione+attiva, relazione+passiva, valore+attiva, valore+passiva)
FONTI = [
    ("Il revisore Bianchi ha respinto 12 proposte di Rossi in commissione.",
     "Il revisore Bianchi ha respinto 12 proposte di Rossi.",
     "Il revisore Rossi ha respinto 12 proposte di Bianchi.",
     "12 proposte di Bianchi sono state respinte dal revisore Rossi.",
     "Il revisore Bianchi ha respinto 99 proposte di Rossi.",
     "99 proposte di Rossi sono state respinte dal revisore Bianchi."),
    ("Il censimento ha classificato 128 artefatti come VESTITO su 372 totali.",
     "Il censimento ha classificato 128 artefatti come VESTITO.",
     "Gli artefatti hanno classificato 128 censimenti come VESTITO.",
     "128 censimenti sono stati classificati VESTITO dagli artefatti.",
     "Il censimento ha classificato 999 artefatti come VESTITO.",
     "999 artefatti sono stati classificati VESTITO dal censimento."),
    ("Il gate di ws3 ha respinto 12 fatti di ws4 durante il turno di notte.",
     "Il gate di ws3 ha respinto 12 fatti di ws4.",
     "Il gate di ws4 ha respinto 12 fatti di ws3.",
     "12 fatti di ws3 sono stati respinti dal gate di ws4.",
     "Il gate di ws3 ha respinto 77 fatti di ws4.",
     "77 fatti di ws4 sono stati respinti dal gate di ws3."),
]

CELLE = ["relazione+attiva", "relazione+passiva", "valore+attiva", "valore+passiva"]
ATTESO = {"relazione+attiva": "fermato", "relazione+passiva": "PASSA (predetto)",
          "valore+attiva": "fermato", "valore+passiva": "fermato"}


def una(venv, claim, fonte):
    store = tempfile.mkdtemp(prefix="ws5_2x2_")
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

    print("  %-4s %-9s %-18s %-18s %-16s %s"
          % ("#", "VERO", CELLE[0], CELLE[1], CELLE[2], CELLE[3]))
    print("  " + "-" * 96)
    conta = {c: 0 for c in CELLE}      # quante volte la cella e' AMMESSA (= passa)
    veri_ok = 0
    for i, (fonte, vero, ra, rp, va, vp) in enumerate(FONTI, 1):
        v = una(venv, vero, fonte)
        veri_ok += (v == "ammesso")
        esiti = []
        for cella, claim in zip(CELLE, (ra, rp, va, vp)):
            e = una(venv, claim, fonte)
            conta[cella] += (e == "ammesso")
            esiti.append(e)
        print("  %-4d %-9s %-18s %-18s %-16s %s" % (i, v, esiti[0], esiti[1], esiti[2], esiti[3]))

    n = len(FONTI)
    print("\n=== SINTESI — quante volte la cella PASSA (su %d fonti) ===" % n)
    for c in CELLE:
        print("  %-20s passa %d su %d   (atteso: %s)" % (c, conta[c], n, ATTESO[c]))
    print("  claim VERI ammessi (controllo positivo): %d su %d" % (veri_ok, n))

    print("\n=== VERDETTO ===")
    if veri_ok < n:
        print("  ⚠️ IL CONTROLLO POSITIVO NON REGGE (%d/%d): un banco in cui cadono anche" % (veri_ok, n))
        print("     i veri misura la severita', non la struttura.")
        return
    rp_passa, vp_passa = conta["relazione+passiva"], conta["valore+passiva"]
    ra_passa, va_passa = conta["relazione+attiva"], conta["valore+attiva"]
    if rp_passa >= n - 1 and vp_passa <= 1:
        print("  🔴 L'IPOTESI REGGE: il passivo fa passare la falsita' di RELAZIONE")
        print("     (%d su %d) e NON quella di VALORE (%d su %d)." % (rp_passa, n, vp_passa, n))
        print("     ⇒ Il confine non e' la forma passiva: e' DOVE STA LA FALSITA'.")
        print("        Il passivo altera la struttura relazionale, non i numeri — e i")
        print("        due numeri opposti miei e di @ws1 si spiegano con le due")
        print("        popolazioni, senza che nessuna delle due misure sia sbagliata.")
    elif rp_passa and vp_passa >= n - 1:
        print("  🪞 IPOTESI SMENTITA: passa anche `valore+passiva` (%d su %d)." % (vp_passa, n))
        print("     Il passivo nasconde TUTTO, non solo le relazioni.")
    elif not rp_passa:
        print("  🪞 IPOTESI SMENTITA NELL'ALTRO VERSO: `relazione+passiva` NON passa su")
        print("     queste fonti ⇒ il mio 0/5 dipendeva dalle fonti, non dalla struttura.")
    else:
        print("  🟡 quadro misto: rel+pass %d/%d · val+pass %d/%d · rel+att %d/%d · val+att %d/%d"
              % (rp_passa, n, vp_passa, n, ra_passa, n, va_passa, n))
        print("     Tre fonti non bastano a decidere: serve una popolazione piu' grande.")


main()
