# -*- coding: utf-8 -*-
"""Lo STESSO claim falso, scritto «8» o «otto»: cambia il verdetto del gate?

`L4.1` vede il numero **solo col glifo 0-9** (lezione di ws5, 27/08). Sul corpus
reale questo si legge in modo netto: fra i fatti che portano una quantità,
`L4.1` ne ferma **18 su 1344** quando c'è una cifra e **0 su 359** quando la
quantità è scritta solo a parole.

⚠️ MA IL CORPUS DICE ANCHE IL CONTRARIO DI CIÒ CHE SEMBRA: i fatti in sole
lettere sono quarantinati **di più** (24,0% contro 8,0%), e a fermarli è il
`moat` (47/86 contro 26/108). ⇒ L'ipotesi «scrivere in lettere aggira il
controllo» è **falsificata dal corpus**, e l'ipotesi di ricambio è che il `moat`,
essendo semantico, non guardi la forma del numero.

Entrambe però sono LETTURE DI UNA CORRELAZIONE: i due gruppi non sono gli stessi
claim, e i fatti discorsivi possono differire per mille altre cose. Questo banco
li rende gli STESSI: ogni caso è una coppia — identica fonte, identica frase,
**una sola variabile: `8` contro `otto`**.

COSA DECIDE:
  i due bracci hanno lo stesso esito  -> la forma del numero NON conta: il moat copre
  la cifra e' fermata e la parola no  -> il buco di L4.1 arriva alla porta

⛔ Store ISOLATO in tempdir: non tocca lo store di Aurelio.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws6_cifra_parola_")
os.environ["HIPPO_DATA_DIR"] = _tmp          # per primo: è l'handle esplicito
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)     # o il RuntimeWarning ci avverte, giustamente

from verimem import Memory  # noqa: E402

# (fonte, frase col NUMERO come segnaposto, valore vero, valore FALSO)
CASI = [
    ("Il registro elenca i lotti A1, A2 e A3 usciti dal deposito il 9 giugno.",
     "I lotti usciti dal deposito sono {n}.", "tre", "otto"),
    ("Il collaudo ha verificato le affermazioni 1, 2, 3, 4 e 5 del manuale.",
     "Le affermazioni verificate nel collaudo sono {n}.", "cinque", "nove"),
    ("La squadra di turno era composta da Rossi, Bianchi, Verdi e Neri.",
     "Gli operai della squadra di turno sono {n}.", "quattro", "dieci"),
    ("Il modulo e' importato da parser.py, engine.py e report.py.",
     "I file che importano il modulo sono {n}.", "tre", "sette"),
    ("Il verbale cita le sedi di Torino e di Genova.",
     "Le sedi citate nel verbale sono {n}.", "due", "sette"),
    ("Nel magazzino restano i pallet numero 4 e numero 7.",
     "I pallet rimasti in magazzino sono {n}.", "due", "otto"),
]
PAROLA_CIFRA = {"due": "2", "tre": "3", "quattro": "4", "cinque": "5",
                "sette": "7", "otto": "8", "nove": "9", "dieci": "10"}

# ── SECONDA META', aggiunta alle 04:58 per chiudere il limite piu' serio della
# prima: nei casi qui sopra il VERO e' sempre un CONTEGGIO, cioe' proprio la
# classe che `L4.1` ferma per costruzione. Qui il VERO **COPIA** il numero dalla
# fonte. Se il `6/6` di falsi allarmi fosse una proprieta' dello strato, dovrebbe
# ripresentarsi; se era il disegno, deve sparire. UNA sola dimensione in piu'.
CASI_COPIA = [
    ("Il magazzino ha ricevuto tre bancali il 9 giugno.",
     "I bancali ricevuti dal magazzino sono {n}.", "tre", "otto"),
    ("Il verbale registra cinque presenti alla riunione.",
     "I presenti registrati nel verbale sono {n}.", "cinque", "nove"),
    ("La squadra e' composta da quattro operai.",
     "Gli operai della squadra sono {n}.", "quattro", "dieci"),
    ("Il modulo e' importato da tre file del pacchetto.",
     "I file che importano il modulo sono {n}.", "tre", "sette"),
    ("Il verbale cita due sedi dell'azienda.",
     "Le sedi citate nel verbale sono {n}.", "due", "sette"),
    ("Nel magazzino restano due pallet.",
     "I pallet rimasti in magazzino sono {n}.", "due", "otto"),
]

m = Memory()
print("LO STESSO CLAIM, DUE FORME DEL NUMERO — una sola variabile\n")
print("%-34s %-6s %-9s %-11s %s" % ("frase", "forma", "verita'", "esito", "chi ferma"))
print("-" * 92)

conta = {}
for gruppo, casi in (("conteggio", CASI), ("copia", CASI_COPIA)):
    print("\n=== il VERO e' un %s ===" % gruppo.upper())
    for i, (fonte, tmpl, vero, falso) in enumerate(casi, 1):
        for verita, val in (("VERO", vero), ("falso", falso)):
            for forma in ("parola", "cifra"):
                n = val if forma == "parola" else PAROLA_CIFRA[val]
                prop = tmpl.format(n=n)
                r = m.add(prop, topic="ws6/cp-%s-%d" % (gruppo, i), source=fonte)
                st = (r.get("status") or "?") if isinstance(r, dict) else "?"
                qb = ",".join(str(w.get("layer","?")) for w in (r.get("warnings") or [])) if isinstance(r, dict) else "-"
                k = (gruppo, verita, forma)
                conta[k] = conta.get(k, 0) + (1 if st == "quarantined" else 0)
                print("%-34s %-6s %-9s %-11s %s" % (prop[:34], forma, verita, st, qb))

print("=" * 92)
print("FERMATI su 6 casi per cella:")
for gruppo in ("conteggio", "copia"):
    print("  il VERO e' un %s:" % gruppo)
    for verita in ("falso", "VERO"):
        print("    %-6s   parola %d/6   cifra %d/6"
              % (verita, conta.get((gruppo, verita, "parola"), 0),
                 conta.get((gruppo, verita, "cifra"), 0)))
print("\n  falso: piu' alto e' meglio (il gate deve fermare)")
print("  VERO : piu' basso e' meglio (sono i falsi allarmi)")
