r"""Perché `delibera` è l'unica che NON cade: il confine della forma tabellare.

Paga il limite che ho dichiarato consegnando `ws5-la-cella-CD-allargata-a-cinque-fonti.py`:
«*`delibera` non cade e non ho indagato perché — è il caso che direbbe dove sta
il confine*». Su cinque fonti in forma `C+D` (colonne + simboli) il claim VERO
cade quattro volte; su `delibera` passa a **80.5**.

🔍 **Guardando i cinque claim, `delibera` è l'unico con una differenza di
FORMA DEL NUMERO fra claim e fonte**::

    suite       claim «EXIT=0»              fonte «exit=0»           cifra / cifra
    collaudo    claim «il 12 marzo»         fonte «data=12-marzo»    cifra / cifra
    fornitura   claim «200 unita'»          fonte «unita=200»        cifra / cifra
    pagamento   claim «fattura 118»         fonte «fattura=118»      cifra / cifra
    delibera    claim «sul punto TRE»       fonte «punto=3»          **PAROLA / cifra**

⇒ 🔮 **PREDIZIONE, scritta e committata PRIMA di eseguire**: `delibera` non cade
**perché il suo claim scrive il numero a parole**. L'estrattore non vede i
numerali a parole (è la classe `numerale-a-parole` già misurata in C2, bucata in
entrambe le lingue) ⇒ **`L4.1` non ha un valore da confrontare e non si
pronuncia** ⇒ decide il solo giudice, che sulla forma `C+D` dà 80.5: basso, ma
sopra la soglia.
⇒ **Cambiando «tre» in «3», `delibera` deve cadere come le altre quattro.**

⚠️ **L'ESITO CHE MI SMENTISCE**: se «punto 3» passa comunque, il numerale non
c'entra e il confine è altrove — e resto senza spiegazione, che va scritto.

IL DISEGNO, a variabile singola: **la stessa fonte, lo stesso significato, cambia
solo la FORMA DEL NUMERO nel claim**::

    delibera-parola   «...sul punto tre il 9 maggio»   (come nel banco originale)
    delibera-cifra    «...sul punto 3 il 9 maggio»     ← unica differenza

⚠️ **POPOLAZIONE DI CONTROLLO, due**: ① le stesse due varianti in **prosa** —
devono passare entrambe, altrimenti la causa è il claim e non la forma;
② un caso che **cade già** (`pagamento`) rifatto **col numero a parole**
(«fattura centodiciotto»): se il numerale a parole è davvero ciò che salva,
**deve smettere di cadere**. È la prova nel verso opposto, ed è quella che rende
il banco falsificabile invece che confermativo.

📐 **E registro i LAYER**, che nel banco precedente non avevo guardato: dicono
*chi* fa cadere le quattro, e se su `delibera` tace davvero qualcuno.

🩺 Regime verificato prima di misurare: daemon **attivo**; **nessun `None`** deve
comparire nel grounding.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: due fonti (`delibera`, `pagamento`) e quattro varianti; «numero
a parole» in italiano ha forme che non provo (`terzo`, `III`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-perche-delibera-non-cade.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

Z_PROSA = ("Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
           "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
           "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
           "leggibile, poi prepara le strutture in memoria. ")
Z_CD = ("verimem/ingestione.py | percorso=normalizzato ++ esito=ok -- durata_ms=4 | "
        "al 100% [ ok ] verimem/avvio.py | cartella=scrivibile ++ config=leggibile "
        "-- esito=ok | al 100% [ ok ]\n")

RIGA_DELIB_PROSA = "Il consiglio ha deliberato all'unanimita' sul punto tre il 9 maggio."
RIGA_DELIB_CD = "consiglio/sedute | punto=3 ++ esito=unanimita -- data=9-maggio | al 100% [ ok ]"
RIGA_PAG_CD = "contabilita/pagamenti | fattura=118 ++ importo=4300 -- data=20-giugno | al 100% [ ok ]"

#: (etichetta, fonte, claim, atteso-secondo-la-predizione)
CASI = [
    ("delibera PAROLA  · C+D", Z_CD * 12 + RIGA_DELIB_CD + "\n",
     "Il consiglio ha deliberato sul punto tre il 9 maggio.", "passa"),
    ("delibera CIFRA   · C+D", Z_CD * 12 + RIGA_DELIB_CD + "\n",
     "Il consiglio ha deliberato sul punto 3 il 9 maggio.", "CADE"),
    ("delibera PAROLA  · prosa (CTRL)", Z_PROSA * 12 + RIGA_DELIB_PROSA + "\n",
     "Il consiglio ha deliberato sul punto tre il 9 maggio.", "passa"),
    ("delibera CIFRA   · prosa (CTRL)", Z_PROSA * 12 + RIGA_DELIB_PROSA + "\n",
     "Il consiglio ha deliberato sul punto 3 il 9 maggio.", "passa"),
    ("pagamento CIFRA  · C+D", Z_CD * 12 + RIGA_PAG_CD + "\n",
     "Il pagamento della fattura 118 e' stato eseguito il 20 giugno.", "CADE"),
    ("pagamento PAROLA · C+D (verso opposto)", Z_CD * 12 + RIGA_PAG_CD + "\n",
     "Il pagamento della fattura centodiciotto e' stato eseguito il 20 giugno.", "passa"),
]


def main():
    print("  %-38s %-9s %-8s %8s  %s"
          % ("caso", "atteso", "esito", "ground", "layer deterministici"))
    print("  " + "-" * 96)
    giusti = 0
    visto_none = False
    for nome, fonte, claim, atteso in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
              if isinstance(w, dict)]
        det = [x for x in ws if x not in NON_DETERMINISTICI]
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        esito = "passa" if az == "persist" else "CADE"
        if g is None:
            visto_none = True
        if esito == atteso:
            giusti += 1
        print("  %-38s %-9s %-8s %8s  %s %s"
              % (nome, atteso, esito, ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", "✔" if esito == atteso else "🔴 NON come predetto"))

    print("\n=== SINTESI ===")
    print("  celle                                %d" % len(CASI))
    print("  esiti come predetto                  %d su %d" % (giusti, len(CASI)))
    print("\n  ⇒ %s" % ("✅ LA PREDIZIONE REGGE: il confine e' la FORMA DEL NUMERO nel\n"
                        "     claim — a parole l'estrattore non lo vede, e senza L4.1\n"
                        "     resta solo il giudice, che sulla forma C+D non basta."
                        if giusti == len(CASI) else
                        "🔴 LA PREDIZIONE NON REGGE su tutte le celle: leggi riga per\n"
                        "     riga quali hanno smentito, e NON riscrivere l'ipotesi\n"
                        "     per farcela stare."))
    if visto_none:
        print("\n  ⚠️ C'E' UN None NEL GROUNDING: quella riga misura il daemon.")


main()
