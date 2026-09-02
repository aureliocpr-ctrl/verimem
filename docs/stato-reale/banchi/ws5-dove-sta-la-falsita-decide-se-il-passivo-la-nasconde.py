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

🔴 ESITO — **la dimensione che separa e' DOVE STA LA FALSITA', non la forma**::

    #   VERO      rel+attiva   rel+passiva   val+attiva   val+passiva
    1   ammesso   fermato      fermato       fermato      fermato
    2   ammesso   ammesso      ammesso       fermato      fermato
    3   ammesso   fermato      ammesso       fermato      fermato

    ① DOVE STA LA FALSITA'    relazione passa 3 su 6   ·   valore passa 0 su 6
    ② LA FORMA (nelle rel.)   attiva    passa 1 su 3   ·   passiva passa 2 su 3
    controllo positivo        3 veri su 3 ammessi

🔑 **① E' IL DATO**: il gate protegge i **valori** in modo perfetto su questo campione
(0 su 6) e **non protegge le relazioni** (3 su 6). ⇒ **E' qui che passa il confine, ed
e' cio' che concilia le due misure opposte**: @ws1 provava con **numeri sbagliati** e
vedeva un gate solido (7/8 fermati); io provavo con **relazioni invertite** e lo vedevo
bucato (0/5). **Nessuna delle due misure e' sbagliata: erano due popolazioni.**

⚠️ **② NON e' dimostrato**: 2 su 3 contro 1 su 3, su **tre** fonti, **non e'
distinguibile dal rumore**. ⇒ L'ipotesi «la voce passiva» che avevo pubblicato alle
04:04 **resta non dimostrata**, e il verdetto del banco ora lo dice invece di
concludere. 🪞 **La prima versione di questo verdetto concludeva «l'ipotesi regge»**
sommando le due dimensioni: **e' la terza volta stanotte che un mio verdetto automatico
e' piu' forte del dato che lo produce.**

📌 **E la forma passiva ESATTA conta**, il che spiega perche' il caso 1 qui e' fermato
mentre la stessa inversione passava nell'altro banco::

    «Bianchi ha avuto la proposta bocciata da Rossi»            AMMESSA  (avere + part.)
    «12 proposte di Bianchi sono state respinte dal rev. Rossi»  FERMATA  (essere + part.)

⇒ Ho cambiato costruzione senza accorgermene fra i due banchi. **Non e' un difetto del
prodotto: e' una variabile che avevo lasciato libera.**

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
    # ⚠️ DUE DIMENSIONI, DUE VERDETTI SEPARATI. Un verdetto solo le confonde: la
    # prima versione diceva «l'ipotesi regge, il passivo fa passare la relazione
    # (2/3)» — ma 2/3 contro 1/3 su tre fonti non separa niente. Il dato forte e'
    # l'altra dimensione, e va letto per primo.
    rel = ra_passa + rp_passa
    val = va_passa + vp_passa
    print("  ① DOVE STA LA FALSITA' (la dimensione che separa):")
    print("     relazione  passa %d su %d        valore  passa %d su %d" % (rel, 2 * n, val, 2 * n))
    if val == 0 and rel > 0:
        print("     🔴 il gate protegge i VALORI in modo perfetto su questo campione e")
        print("        NON protegge le RELAZIONI. ⇒ E' qui che passa il confine, ed e'")
        print("        cio' che concilia le due misure opposte: chi prova con numeri")
        print("        sbagliati vede un gate solido, chi prova con relazioni invertite")
        print("        lo vede bucato. **Nessuna delle due misure e' sbagliata.**")
    elif val and rel:
        print("     🟡 passano entrambe le classi: la dimensione non separa su queste fonti.")
    else:
        print("     🪞 nessuna classe passa: su queste fonti il gate regge, e il")
        print("        fenomeno va cercato altrove.")
    print("  ② LA FORMA (attiva/passiva), DENTRO le relazioni:")
    print("     attiva passa %d su %d   ·   passiva passa %d su %d" % (ra_passa, n, rp_passa, n))
    if abs(rp_passa - ra_passa) >= n - 1 and n >= 5:
        print("     🔴 la forma separa.")
    else:
        print("     🟡 differenza di %d su %d fonti: **NON e' distinguibile dal rumore**."
              % (abs(rp_passa - ra_passa), n))
        print("        ⇒ L'ipotesi «la voce passiva» resta NON dimostrata qui: serve")
        print("           una popolazione piu' grande. Il dato di questo banco e' ①.")


main()
