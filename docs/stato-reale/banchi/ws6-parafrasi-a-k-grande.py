"""A parole proprie il fatto entra nel pool, solo oltre il decimo posto?

@ws1 ha misurato (02:56) che con domande **a parole proprie** il fatto atteso non
è nemmeno fra i primi dieci — **0/10** — e ne ha tratto: *«né k, né il rerank, né
una soglia possono curarlo: il fatto non entra nel pool»*, girando a @ws3 la
domanda sul **richiamo dell'indice a k grande**.

Il mio `ws6-ranking-o-assenza` quella domanda l'aveva posta a `k=200`, ma con
domande costruite col **vocabolario del fatto**: là **0 recuperi fra 11 e 200**,
il rango è binario. **Le parafrasi sono un'altra popolazione.**

⚠️ DUE ERRORI MIEI PRIMA DI ARRIVARE QUI, e sono la ragione di come è scritto:

1. Il primo tentativo cercava il fatto **per parole** dentro il testo dei
   risultati: parole come «il» e «viene» matchano ovunque, e un fatto su LoCoMo
   è stato contato come recupero. ⇒ **Il match è per `id`, mai per parole.**
2. Il secondo cercava «un fatto qualsiasi che contenga il termine tecnico», e i
   bersagli erano **55, 437, 87, 278, 789**. Trovarne uno fra 789 entro `k=200`
   è tutt'altra cosa dal trovare **il** fatto atteso, che è il caso di @ws1.
   ⇒ **Un bersaglio SOLO per caso, dichiarato per `id`.**

⚠️ LE PARAFRASI SONO MIE: riscrivono il fatto **senza riusarne un solo termine
tecnico**, come farebbe chi ricorda il concetto e non le parole. Sei casi non
sono un tasso, e un'altra persona ne scriverebbe altre.

SOLA LETTURA sullo store.
"""
import os

DB = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))

# (id ESATTO del fatto atteso, parafrasi a parole proprie)
CASI = [
    ("17eab2845513",
     "se davanti alla cifra c'e' una parola generica il controllo non trova "
     "riscontro e declassa"),
    ("9678aab2ccf2",
     "aggiungendo due righe in piu' al testo di partenza un'affermazione "
     "sbagliata passa da poco credibile a molto credibile"),
    ("05ee15f036ca",
     "quando il testo di partenza e' una tabella lunga l'affermazione falsa "
     "risulta piu' convincente di quella giusta"),
    ("f9f86a1d5923",
     "quale valore di sbarramento e quale valutatore compaiono nell'esito "
     "del controllo"),
    ("64e259c420f4",
     "allungando di una parola la descrizione dell'oggetto il verdetto cambia "
     "da conservare a declassare"),
    ("60540fcd8859",
     "se la descrizione dell'oggetto e' piu' dettagliata il verdetto peggiora"),
]

from verimem.client import Memory   # noqa: E402

m = Memory(DB)

print("PARAFRASI A k GRANDE — un bersaglio solo, match per ID")
print("(la domanda che @ws1 ha girato a @ws3 alle 02:56)\n")

entro10 = fra11e200 = mai = 0
for fid, parafrasi in CASI:
    res = m.recall(parafrasi, k=200, as_of=None)
    rango = None
    for i, it in enumerate(res or [], 1):
        if isinstance(it, dict) and it.get("id") == fid:
            rango = i
            break
    if rango is None:
        mai += 1
        esito = "MAI — nemmeno a k=200"
    elif rango <= 10:
        entro10 += 1
        esito = "entro i primi 10 (rango %d)" % rango
    else:
        fra11e200 += 1
        esito = "RECUPERATO da k grande (rango %d)" % rango
    print("  %s  %-52s %s" % (fid, parafrasi[:52], esito))

n = entro10 + fra11e200 + mai
print()
print("Su %d parafrasi, bersaglio unico:" % n)
print("  entro i primi 10                   : %d" % entro10)
print("  fra 11 e 200 → il pool LO CONTIENE : %d" % fra11e200)
print("  MAI, nemmeno a k=200               : %d" % mai)
print()
print("Se l'ultima riga domina, «il fatto non entra nel pool» regge e la leva")
print("e' nell'embedding. Se domina quella di mezzo, il pool lo contiene e a")
print("nasconderlo e' il ranking: due cure diverse.")
