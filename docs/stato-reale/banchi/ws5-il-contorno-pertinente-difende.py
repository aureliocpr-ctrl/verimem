# -*- coding: utf-8 -*-
r"""A struttura fissa il CONTENUTO decide: 69.0 contro 99.9 con tre frasi in tutte.

    burocratico  (14 parole)  VERO=persist 99.2   FALSO=persist    84.2
    temporale    (15 parole)  VERO=persist 99.6   FALSO=persist    99.9
    logistico    (13 parole)  VERO=persist 99.8   FALSO=downgrade  69.0   <- difende
    estraneo     (21 parole)  VERO=persist 99.7   FALSO=persist    99.5
    negativo     (15 parole)  VERO=persist 99.9   FALSO=persist    99.8

Claim identico: «La consegna e' prevista per LUNEDI'» contro una fonte che dice
GIOVEDI'. **Sempre TRE frasi di riempimento**, lunghezza simile (13-15 parole salvo
l'estraneo): cambia solo di COSA parlano. Il VERO passa ovunque: il banco separa.

PAGA IL DEBITO di `ws5-basta-un-intestazione.py`: «non so cosa governi la zona
instabile (50-85); servirebbe variare il CONTENUTO a struttura fissa».

⇒ ① IL CONTENUTO GOVERNA, e di molto: **da 69.0 a 99.9 a parita' di struttura**. La
zona «instabile» misurata prima non era rumore: era **contenuto non controllato**.
⇒ ② E IL VERSO E' ROVESCIATO rispetto all'intuizione: **l'unico riempimento che
DIFENDE e' il piu' PERTINENTE al claim** — «merce in magazzino, furgone disponibile,
corriere avvisato» (69.0). Il piu' estraneo (mensa, parcheggio, scale) copre quasi
del tutto (99.5).
⇒ ③ LETTURA: se le altre frasi parlano di **consegne**, il giudice ha materiale per
valutare «giovedi' contro lunedi'»; se parlano della **mensa**, il claim resta l'unica
cosa a tema e non ha con cosa essere confrontato. ⇒ **Il contorno pertinente da'
appigli, quello estraneo li toglie.**
⚠️ E il riempimento **temporale** («registrato a marzo, protocollato il mattino,
verificato in settimana») e' fra i peggiori (99.9) pur parlando di TEMPO come il
claim: **la dimensione condivisa non basta, serve la pertinenza al FATTO.**

❌ RITIRO LA LETTURA ③ — la scala graduata la FALSIFICA. Debito pagato subito::

    0 estraneo        (20 parole)  FALSO=persist    98.1
    1 ufficio         (16 parole)  FALSO=downgrade  11.8
    2 logistica       (18 parole)  FALSO=downgrade  57.9
    3 consegna        (19 parole)  FALSO=downgrade   4.1
    4 quasi-identico  (18 parole)  FALSO=persist   100.0

⇒ **NON E' MONOTONO**: 98.1 → 11.8 → 57.9 → 4.1 → 100.0. **«Piu' pertinente = piu'
difende» non regge come scala**, e il 57.9 in mezzo a 11.8 e 4.1 non lo spiego.
⚠️ **E IL GRADINO 4 E' ROTTO DA UN ERRORE MIO**: «La spedizione parte mercoledi'. Il
ritiro avviene venerdi'. **Il reso e' lunedi'.**» — **contiene «lunedi'»**, il valore
che il claim inventa. Non e' «quasi identico»: e' **COLLISIONE**, la stessa misurata
sui numeri (`ws5-Q2bis-la-rarita-del-numero-decide.py`) ma su un valore NON numerico.
⇒ **Salva meta' della lettura e ne uccide meta'**: il gradino 0 copre per **estraneita'**,
il 4 copre per **collisione**. Sono due meccanismi diversi, e io li avevo messi sulla
stessa scala.
✅ **CIO' CHE RESTA MISURATO**: a struttura e lunghezza simili il punteggio del falso va
da **4.1 a 100.0** ⇒ **il contenuto del contorno decide, e di molto**. Il **come** non lo
so, e non lo scrivo.

⚖️ PUNTO DEBOLE: cinque contenuti, un claim, un tipo di valore. **La lettura del ③ e'
un'INTERPRETAZIONE, non una misura**: per provarla servirebbe una scala di pertinenza
graduata (dal totalmente estraneo al quasi-identico) e verificare che il punteggio
scenda in modo monotono. **Non l'ho fatta.** E l'«estraneo» ha 21 parole contro 13-15
degli altri: **lunghezza e contenuto sono confusi in quella cella.**

REGIME: build corrente · python 3.13.12 · store temporaneo · `run_validation_gate`
(porta della CLI, `cli.py:1867`) · letti i `warnings`, non `layers`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-contorno-pertinente-difende.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

ANC = "La consegna e' prevista per giovedi'."
RIEMP = [
 ("burocratico", "Nota interna. Documento di servizio. Copia per archivio."),
 ("temporale",   "Registrato a marzo. Protocollato il mattino. Verificato in settimana."),
 ("logistico",   "Merce in magazzino. Furgone disponibile. Corriere avvisato."),
 ("estraneo",    "La mensa apre a mezzogiorno. Il parcheggio e' sul retro. Le scale sono a destra."),
 ("negativo",    "Nessun ritardo segnalato. Nessuna contestazione aperta. Nessun reclamo ricevuto."),
]
CLAIM = [("VERO", "La consegna e' prevista per giovedi'."),
         ("FALSO", "La consegna e' prevista per lunedi'.")]
print("")
for eti, r_ in RIEMP:
    src = r_ + " " + ANC
    out = []
    for e2, claim in CLAIM:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=src, grounding_llm=None, ground_write=True)
        g = getattr(r, "grounding_score", None)
        out.append("%s=%-9s g=%5s" % (e2[:5], getattr(r, "action", "?")[:9],
                   ("%.1f" % g) if isinstance(g, (int, float)) else "-"))
    print("   %-13s (%2d parole)  %s" % (eti, len(src.split()), "  ".join(out)))
