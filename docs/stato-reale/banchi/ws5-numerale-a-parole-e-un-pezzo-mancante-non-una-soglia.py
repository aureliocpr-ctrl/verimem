r"""`numerale-a-parole` e' aperta per un PEZZO MANCANTE, non per una soglia - e il pezzo e' mio.

Ultima cella rossa aperta del mio claim C2. Era 4/4 bucata in EN e 3/4 in IT, e
la scelta era «allargarla a 8 casi o dichiararla chiusa». **Nessuna delle due:
la causa e' isolabile, e con la causa 4 su 4 vale piu' di 8 su 8**::

    A  l'estrattore vede i numerali a parole nel claim?
       'Il fatturato annuo e' di settantamila euro.'   -> []
       'The annual revenue is seventy thousand euro.'  -> []
       'I dipendenti assunti sono dodici.'             -> []
       'Twelve employees were hired.'                  -> []
       'Il fatturato annuo e' di 70000 euro.'          -> [('euro', 70000.0)]

    B  e quindi `L4.1` ha qualcosa da controllare?
       claim A PAROLE, fonte senza numero   ->  **NIENTE DA DIRE**
       claim IN CIFRE, fonte senza numero   ->  segnala ['70000']
       claim IN CIFRE, fonte A PAROLE       ->  segnala ['70000']

⇒ **Un claim che inventa un numero scrivendolo a parole non porta NESSUN valore**,
quindi `L4.1` non ha nulla su cui pronunciarsi. Non e' una soglia da tarare ne'
un caso limite: e' **il pezzo che manca**.

🔑 **E IL PRODOTTO COPRE IL VERSO OPPOSTO**, il che rende la lacuna piu' netta:
`assenti_che_la_fonte_scrive_a_parole` (`L4.1-a-parole`) gestisce «*la FONTE
scrive a parole, il claim ha la cifra*» e serve a **declassare** da veto ad
avviso. ⇒ La copertura e' **asimmetrica per costruzione**: da cifra a parole
si', da parole a cifra no.

📌 **E IL PEZZO HA UN NOME E UN PROPRIETARIO: sono io.** Nel design doc F1 di
@ws3 sta scritto fra i prerequisiti: «`norm(v)` - **normalizzatore di numerali**
(*«settantamila» -> 70000*): pezzo **separato, di @ws5**, che serve **anche a
`L4.1`**». Non l'ho mai scritto. ⇒ La cella non e' «rossa e basta»: e' **rossa
in attesa di un pezzo che mi ero presa**.

⇒ **DICHIARO LA CELLA CHIUSA COME DIAGNOSI** (causa isolata, verso coperto e
verso scoperto misurati) **e APERTA COME CURA**. Allargarla a otto casi non
aggiungerebbe niente: aggiungerebbe otto volte lo stesso zero.

REGIME: build corrente · **nessun modello caricato** (funzioni pure
`extract_quantities` e `valori_non_nella_fonte`).
⚖️ PUNTI DEBOLI: quattro numerali per lingua, tutti «grandi» (settantamila,
dodici, seventy thousand, twelve). **Non ho provato i piccoli** («tre», «due»),
dove un normalizzatore rischia gli omonimi - ed e' precisamente il motivo per
cui `L4.1-a-parole` **declassa** invece di vietare. Chi scrivera' `norm(v)`
parta da li'.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-numerale-a-parole-e-un-pezzo-mancante-non-una-soglia.py
"""
import sys
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.quantity_match import extract_quantities as EQ
from verimem.valore_non_nella_fonte import valori_non_nella_fonte as L41

print("=== A: l'estrattore vede i numerali a PAROLE nel claim? ===")
for t in ("Il fatturato annuo e' di settantamila euro.",
          "The annual revenue is seventy thousand euro.",
          "I dipendenti assunti sono dodici.",
          "Twelve employees were hired.",
          "Il fatturato annuo e' di 70000 euro.",
          "The annual revenue is 70000 euro."):
    print("  %-46s -> %s" % ("'" + t[:44] + "'", sorted(EQ(t))))

print("\n=== B: e quindi L4.1 ha qualcosa da controllare? ===")
COPPIE = [
 ("claim A PAROLE, fonte senza numero (il MIO caso)",
  "Il fatturato annuo e' di settantamila euro.",
  "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("claim IN CIFRE, fonte senza numero (controllo)",
  "Il fatturato annuo e' di 70000 euro.",
  "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("claim IN CIFRE, fonte A PAROLE (il verso COPERTO)",
  "Il fatturato annuo e' di 70000 euro.",
  "Il fatturato annuo e' di settantamila euro."),
]
for nome, c, f in COPPIE:
    a = L41(c, f)
    print("  %-48s L4.1: %s" % (nome[:48],
          ("segnala " + str([x.come_scritto() for x in a])) if a else "NIENTE DA DIRE"))
