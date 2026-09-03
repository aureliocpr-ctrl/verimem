"""Due frasi della stessa forma, entrambe vere: 99,95 e 15,66. Cosa le separa?

    python docs/stato-reale/banchi/ws6-due-frasi-gemelle-due-verdetti.py

⚠️ REPERTO, trovato per caso il 03/09 mentre scrivevo un test sulla scadenza —
il fatto «vivo» del test veniva quarantinato e il recall tornava vuoto:

    A  «...ospita quattromilaseicento pallet di ricambi.»
       fonte «Inventario: ...ospita 4600 pallet di ricambi.»      99,95  AMMESSO
    B  «...ospita duemila pallet di imballaggi.»
       fonte «Inventario: ...ospita 2000 pallet di imballaggi.»   15,66  QUARANTINED

Stessa struttura, stessa forma di fonte, **entrambe vere**. Non e' rumore del
giudice: in casa e' gia' misurato deterministico (*«chiamando
fact_grounding_score_ex due volte sulla stessa source minima il punteggio e'
99.869 entrambe le volte»*). Quindi qualcosa **nei casi** li separa.

DISEGNO — una variabile per volta, che e' l'unico modo perche' il confronto non
menta. A e B differiscono per DUE cose insieme (il numero e l'oggetto), quindi
si costruiscono le due celle incrociate:

    A   quattromilaseicento / 4600   ricambi        <- ammesso
    A1  duemila / 2000               ricambi
    A2  quattromilaseicento / 4600   imballaggi
    B   duemila / 2000               imballaggi     <- quarantinato

Se cade A1 e non A2 → e' il NUMERO. Se cade A2 e non A1 → e' l'OGGETTO.
Se cadono entrambe o nessuna → e' un'interazione, e la domanda va rifatta.

⚠️ CONTROLLO POSITIVO, senza il quale il banco non misura niente: una coppia
**falsa** (la fonte dice un numero diverso da quello della proposizione) deve
prendere un punteggio BASSO. Se anche quella passasse, il punteggio non
starebbe leggendo il rapporto fra fonte e proposizione e i quattro numeri
sopra non direbbero nulla.

⚠️ E UN SECONDO CONTROLLO, sulla ripetibilita': la cella A viene giudicata DUE
volte. Se i due punteggi differiscono, tutto il disegno cade — la differenza
sarebbe rumore, non struttura, e l'ho dato per assodato leggendo una lezione
invece di misurarlo qui.

⛔ Store isolato in tempdir: non tocca lo store di casa.

═══ ESITO (03/09 20:11) — e ribalta la domanda di partenza ═══

Separa IL NUMERO, non l'oggetto: A2 (cambiato l'oggetto) resta 99,95, A1
(cambiato il numero) crolla a 10,46. E le celle diagnostiche dicono quale
proprieta':

    PAROLA -> CIFRA                     STESSA FORMA
      quattromilaseicento/4600  99,95     duemila/duemila           99,31
      duemila/2000              10,46     quattromilaseicento/idem  99,80
      tremila/3000               4,58     4600/4600                 99,46
      millecento/1100            1,40     2000/2000                 99,38

🔑 Il difetto e' la CONVERSIONE parola->cifra: 3 fatti veri su 4 cadono, e le
stesse parole passano a ~99 quando non c'e' nulla da convertire.

⚠️ E i punteggi sono DA FALSITA', non «bassi»: la coppia deliberatamente falsa
prende 0,69, `millecento/1100` prende 1,40 e `tremila/3000` 4,58.

🪞 L'anomalia era `quattromilaseicento/4600`, l'unico che passa — e il banco era
nato dandolo per la norma. Perche' passi NON si sa: non e' spiegato qui.

Documento: `docs/stato-reale/83-il-gate-non-converte-i-numeri-scritti-in-parola.md`
"""
import os
import sys
import tempfile

#: ⚠️ `python docs/.../banco.py` mette in `sys.path[0]` la cartella del BANCO,
#: non la radice: senza questa riga si importa il `verimem` installato e non
#: quello dell'albero in cui si sta lavorando — e non fallisce, risponde con
#: l'altro codice. Convenzione gia' fissata per i banchi di questa cartella.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

_tmp = tempfile.mkdtemp(prefix="ws6_gemelle_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

BASE = "Il deposito di Verona ospita %s pallet di %s."
FONTE = "Inventario: il deposito di Verona ospita %s pallet di %s."

CELLE = [
    ("A   4600  ricambi   ", "quattromilaseicento", "4600", "ricambi", "ricambi"),
    ("A1  2000  ricambi   ", "duemila", "2000", "ricambi", "ricambi"),
    ("A2  4600  imballaggi", "quattromilaseicento", "4600", "imballaggi", "imballaggi"),
    ("B   2000  imballaggi", "duemila", "2000", "imballaggi", "imballaggi"),
    ("A-bis (ripetizione) ", "quattromilaseicento", "4600", "ricambi", "ricambi"),
    ("FALSA (controllo)   ", "quattromilaseicento", "17", "ricambi", "ricambi"),
    #: ⚠️ LE CELLE CHE DICONO *PERCHE'*. Il quadro sopra dice che separa IL
    #: NUMERO, non quale sua proprieta'. Due sospetti, e si distinguono
    #: togliendo la conversione: se «duemila» contro una fonte che dice
    #: «duemila» PASSA, il difetto e' nel tradurre parola→cifra; se cade
    #: anche li', il difetto e' in quella parola comunque scritta.
    ("duemila vs duemila  ", "duemila", "duemila", "ricambi", "ricambi"),
    ("4600 in cifra vs4600", "4600", "4600", "ricambi", "ricambi"),
    ("2000 in cifra vs2000", "2000", "2000", "ricambi", "ricambi"),
    ("quattromila vs idem ", "quattromilaseicento", "quattromilaseicento", "ricambi", "ricambi"),
    ("tremila / 3000      ", "tremila", "3000", "ricambi", "ricambi"),
    ("millecento / 1100   ", "millecento", "1100", "ricambi", "ricambi"),
]

m = Memory()
print("DUE FRASI GEMELLE, DUE VERDETTI — cosa li separa\n")
print("  %-22s %8s  %-12s %s" % ("cella", "ground.", "status", "proposizione"))

esiti = {}
for et, parola, cifra, ogg_p, ogg_f in CELLE:
    p = BASE % (parola, ogg_p)
    s = FONTE % (cifra, ogg_f)
    try:
        r = m.add(p, topic="gemelle/%s" % et.split()[0].lower(), source=s)
        f = m.semantic.get(r["id"])
        g = getattr(f, "grounding_score", None)
        st = getattr(f, "status", "?")
    except Exception as e:                    # noqa: BLE001 — il banco misura
        g, st = None, "ERRORE: %s" % str(e)[:30]
    esiti[et.strip()] = (g, st)
    print("  %-22s %8s  %-12s %s" % (
        et, ("%.2f" % g) if isinstance(g, (int, float)) else "-", st, p[:46]))

print("\n  ── LETTURA ──")
a = esiti.get("A   4600  ricambi")
abis = esiti.get("A-bis (ripetizione)")
falsa = esiti.get("FALSA (controllo)")

if a and abis and isinstance(a[0], float) and isinstance(abis[0], float):
    d = abs(a[0] - abis[0])
    print("  ripetibilita': A=%.2f  A-bis=%.2f  scarto=%.2f  %s" % (
        a[0], abis[0], d,
        "OK, il disegno regge" if d < 0.01 else
        "⛔ IL GIUDICE NON RIPETE: la differenza e' rumore, il disegno CADE"))
if falsa and isinstance(falsa[0], float):
    print("  controllo positivo: la coppia FALSA prende %.2f  %s" % (
        falsa[0],
        "OK, il punteggio legge davvero il rapporto fonte/proposizione"
        if falsa[0] < 50 else
        "⛔ ANCHE LA FALSA PASSA: il punteggio non misura quel rapporto,"
        " e i quattro numeri sopra non dicono nulla"))
