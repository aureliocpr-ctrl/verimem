r"""Che cosa, nella forma «tabellare», rovescia il gate? Quattro proprietà, una alla volta.

Chiude la domanda che avevo lasciato aperta consegnando `W5-5`
(`ws5-la-cella-che-mancava-lunga-per-tabellare.py`): su fonte **lunga e
tabellare pura** il claim VERO cade a **52.0** e il FALSO entra a **98.9** —
ma «tabellare» è un sacco che contiene almeno quattro cose diverse, e non
sapevo quale pesasse.

🔍 **memoria**: `LANT-75` di @ws7 dice «*il gate premia le fonti in PROSA e
penalizza quelle TABELLARI*» e ne dà la ragione **semantica** (il verbale
enuncia la relazione, l'uscita di uno script la mostra in due righe separate).
`quantity_match.py:676` la dichiara da una terza direzione (27 falsi positivi su
28). ⇒ **Nessuna delle due dice QUALE proprietà tipografica pesi**, ed è
l'unica cosa che misuro qui.

LE QUATTRO PROPRIETÀ, ognuna da sola, stesso contenuto e stessa lunghezza::

    A  prosa piena                     (controllo: deve DISTINGUERE)
    B  righe SPEZZATE                  la stessa prosa, a capo ogni ~40 caratteri
    C  SIMBOLI                         prosa piena + | + % ++ -- nei punti giusti
    D  COLONNE                         coppie chiave=valore allineate, niente frasi
    E  tabellare piena (B+C+D)         (controllo: deve ROVESCIARSI)

⇒ Se solo **E** si rovescia, la causa è la **combinazione** e nessuna proprietà
da sola basta. Se si rovescia **D**, è la perdita della frase. Se **B**, è
l'andare a capo. Se **C**, sono i simboli.

⚠️ **POPOLAZIONE DI CONTROLLO — due, e sono agli estremi**: `A` (prosa) deve
distinguere e `E` (tabellare piena) deve rovesciarsi, perché sono le due celle
già misurate in `W5-5`. **Se A o E non riproducono, il banco non è leggibile** e
i verdetti su B, C, D non valgono niente.
⚠️ Su ogni forma viaggiano **un claim VERO e uno FALSO**: senza i falsi, «il
vero cade» non distingue un gate severo da uno rovesciato.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: le cinque zeppe sono **mie** e non sono lunghe uguali al
carattere (stesso ordine di grandezza, ~2500-3400); un vero e un falso per
forma; «prosa» e «colonne» sono giudizi miei — un linguista dividerebbe
diversamente.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quale-proprieta-della-forma-tabellare-pesa.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

VERO = "La suite termina con EXIT=0."
FALSO = "La suite termina con EXIT=1."

#: la riga che sostiene il claim, nelle due forme estreme
RIGA_PROSA = "La suite riporta 21 passed e 2 skipped, e termina con EXIT=0.\n"
RIGA_TAB = ("tests/test_uno.py ....... [ 33%]\n"
            "21 passed, 2 skipped, 1 warning in 9.31s\n"
            "EXIT=0\n")

#: A — prosa piena: frasi complete, nessun simbolo, nessun a capo forzato
Z_PROSA = (
    "Il modulo di ingestione normalizza i percorsi prima di aprirli e registra "
    "ogni apertura nel giornale delle operazioni. La procedura di avvio verifica "
    "che la cartella dei dati sia scrivibile e che il file di configurazione sia "
    "leggibile, poi prepara le strutture in memoria. "
)

#: B — le STESSE parole, spezzate a capo ogni ~40 caratteri
def _spezza(t, n=40):
    parole, riga, out = t.split(), "", []
    for p in parole:
        if len(riga) + len(p) + 1 > n:
            out.append(riga)
            riga = p
        else:
            riga = (riga + " " + p).strip()
    out.append(riga)
    return "\n".join(out) + "\n"


Z_SPEZZATA = _spezza(Z_PROSA)

#: C — le stesse frasi, con i simboli tipici di un output di script
Z_SIMBOLI = (
    "Il modulo di ingestione | normalizza i percorsi prima di aprirli e registra "
    "ogni apertura nel giornale ++ delle operazioni. La procedura di avvio -- verifica "
    "che la cartella dei dati sia scrivibile al 100% e che il file di configurazione "
    "sia leggibile [ ok ], poi prepara le strutture in memoria. "
)

#: D — solo coppie chiave=valore allineate: nessuna frase, nessun verbo
Z_COLONNE = (
    "verimem/ingestione.py    percorso=normalizzato   esito=ok      durata_ms=4\n"
    "verimem/avvio.py         cartella=scrivibile     config=ok     durata_ms=7\n"
    "verimem/giornale.py      rotazione=attiva        soglia=64     durata_ms=2\n"
)

#: E — tabellare piena: spezzata, con simboli, a colonne (come nell'incidente)
Z_TABELLARE = (
    "verimem/ingestione.py:112 percorso=normalizzato esito=ok durata_ms=4\n"
    "verimem/avvio.py:57 cartella=scrivibile config=leggibile esito=ok\n"
    " verimem/giornale.py    |  18 ++--\n"
    " verimem/rotazione.py   |   7 +-\n"
)

FORME = [
    ("A prosa (CONTROLLO)", Z_PROSA * 12 + RIGA_PROSA),
    ("B righe spezzate", Z_SPEZZATA * 12 + RIGA_PROSA),
    ("C simboli", Z_SIMBOLI * 12 + RIGA_PROSA),
    ("D colonne chiave=valore", Z_COLONNE * 12 + RIGA_PROSA),
    ("E tabellare (CONTROLLO)", Z_TABELLARE * 12 + RIGA_TAB),
]


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g


def main():
    print("  %-26s %6s   %-9s %8s   %-9s %8s  %s"
          % ("forma della zeppa", "car.", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 96)
    esiti = {}
    for nome, fonte in FORME:
        pv, gv = _gate(VERO, fonte)
        pf, gf = _gate(FALSO, fonte)
        if pv and not pf:
            verdetto = "🟢 distingue"
        elif not pv and pf:
            verdetto = "🔴🔴 ROVESCIATO"
        elif not pv and not pf:
            verdetto = "🔴 cade anche il vero"
        else:
            verdetto = "🔴 passa anche il falso"
        esiti[nome[0]] = verdetto
        print("  %-26s %6d   %-9s %8s   %-9s %8s  %s"
              % (nome, len(fonte), "passa" if pv else "CADE",
                 ("%.1f" % gv) if gv is not None else "None",
                 "passa" if pf else "cade",
                 ("%.1f" % gf) if gf is not None else "None", verdetto))

    print("\n=== COME SI LEGGE ===")
    ok_controlli = ("distingue" in esiti.get("A", "")) and ("ROVESCIATO" in esiti.get("E", ""))
    print("  controlli (A distingue, E rovesciato): %s"
          % ("✅ riprodotti — i verdetti su B, C, D sono leggibili" if ok_controlli
             else "🔴 NON riprodotti — il banco non è leggibile, e i verdetti su B/C/D non valgono"))
    rovesciate = [k for k, v in esiti.items() if "ROVESCIATO" in v and k != "E"]
    print("  proprietà che da SOLE rovesciano: %s"
          % (", ".join(rovesciate) if rovesciate else "nessuna ⇒ è la COMBINAZIONE"))
    print("  ⚠️ Se nessuna delle tre da sola rovescia, la cura non può essere")
    print("     «togliere i simboli» o «non andare a capo»: serve agire sul")
    print("     giudizio, non sulla tipografia.")


main()
