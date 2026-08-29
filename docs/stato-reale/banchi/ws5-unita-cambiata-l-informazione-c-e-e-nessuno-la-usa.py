r"""`unita-cambiata`: **l'informazione c'e' e nessun layer la usa.**

Ultima cella rossa che avevo dichiarato «non indagata a fondo» nella tabella C2
(`docs/stato-reale/C2-tabella-classi-core.md`). Chiusa con la **causa**, come
`numerale-a-parole`, invece che con piu' casi::

    caso                            unita' nel claim          unita' nella fonte        layer
    IT  30 mesi contro 30 giorni    [('meso', 30.0)]          [('giorno', 30.0)]        NESSUNO
    EN  30 months vs 30 days        [('month', 30.0)]         [('day', 30.0)]           NESSUNO
    IT  1200 euro/giorno vs /mese   [('euro', 1200.0)]        [('euro', 1200.0)]        NESSUNO
    IT  15 km contro 15 metri       [('chilometro', 15.0)]    [('metro', 15.0)]         NESSUNO
    IT  500 g contro 500 mg         [('grammo', 500.0)]       [('milligrammo', 500.0)]  NESSUNO

🔑 **L'ESTRATTORE RICONOSCE CORRETTAMENTE LE UNITA' DIVERSE** - `meso` contro
`giorno`, `chilometro` contro `metro`, `grammo` contro `milligrammo`. **L'informazione
c'e'.** E **nessun layer deterministico la usa**: `L4.1` tace perche' il **valore**
(30, 15, 500) **e' nella fonte**, e confronta **i valori, non le coppie
(unita', valore)**.
📌 **E il prodotto lo DICHIARA GIA'**, nel docstring di `vicinato_del_valore`:
«*`valori_non_nella_fonte` confronta i VALORI e non le coppie (unita', valore),
e il suo docstring lo dichiarava - «l'unita' in un testo libero e' la parola che
segue, troppo fragile per farci poggiare un veto»*». ⇒ Non e' una svista: e' una
**scelta motivata**, misurata qui sul verso che quella scelta lascia scoperto.

🔴 **E CI SONO DUE SOTTOCLASSI, non una:**
① **unita' diverse riconosciute** (meso/giorno, grammo/milligrammo): l'estrattore
   le distingue, **il confronto le ignora** ⇒ curabile con l'informazione che
   gia' esiste.
② **stesso token di unita', periodo diverso** (`1200 euro al giorno` contro
   `1200 euro al mese`): l'estrattore vede `('euro', 1200.0)` **da entrambe le
   parti** ⇒ **l'informazione non c'e' nemmeno**, e nessuna cura sul confronto
   puo' bastare. Sono due difetti con due costi diversi.

⚖️ **E SPIEGA PERCHE' LA CELLA EN RISULTA DIFESA E LA IT NO** nella tabella C2:
qui **nessun layer parla in NESSUNA delle due lingue**. ⇒ La difesa inglese
misurata nel primo referto (grounding 2.1) **non viene da un layer
deterministico: viene dal GIUDICE**. La cella EN e' verde per il giudice, non
per una difesa strutturale — e un verde che dipende dal giudice **non e' una
garanzia**, e' una fortuna misurata su un caso.

REGIME: build corrente · **nessun modello caricato** (funzioni pure
`extract_quantities`, `valori_non_nella_fonte`, `valori_riusati_da_altro_contesto`).
⚖️ PUNTI DEBOLI: cinque casi, tutti costruiti; misuro i **layer deterministici**,
non la porta - alla porta il giudice puo' salvare o affondare il caso, e infatti
in EN lo salva. Chi vuole il verdetto end-to-end usi `run_validation_gate`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-unita-cambiata-l-informazione-c-e-e-nessuno-la-usa.py
"""
import sys
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.quantity_match import extract_quantities as EQ
from verimem.valore_non_nella_fonte import valori_non_nella_fonte as L41
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto as L42

CASI = [
 ("IT  30 mesi contro 30 giorni",
  "Il termine di consegna e' di 30 mesi.",
  "Il termine di consegna e' di 30 giorni dalla firma."),
 ("EN  30 months vs 30 days (difesa)",
  "The delivery term is 30 months.",
  "The delivery term is 30 days from signature."),
 ("IT  1200 euro/giorno contro /mese",
  "Il canone e' di 1200 euro al giorno.",
  "Il canone e' di 1200 euro al mese."),
 ("IT  15 km contro 15 metri",
  "La distanza e' di 15 chilometri.",
  "La distanza dal deposito e' di 15 metri."),
 ("IT  500 g contro 500 mg",
  "La dose e' di 500 grammi.",
  "La dose prescritta e' di 500 milligrammi al giorno."),
]
print("  %-34s %-26s %-26s %s" % ("caso", "unita' nel claim", "unita' nella fonte", "layer che parlano"))
for nome, c, f in CASI:
    qc, qf = sorted(EQ(c)), sorted(EQ(f, come_fonte=True))
    a41 = [x.come_scritto() for x in (L41(c, f) or [])]
    a42 = [(x.valore, x.nel_claim, x.nella_fonte) for x in (L42(c, f) or [])]
    lay = []
    if a41: lay.append("L4.1 %s" % a41)
    if a42: lay.append("L4.2 %s" % a42[:1])
    print("  %-34s %-26s %-26s %s" % (nome[:34], str(qc)[:26], str(qf)[:26], "; ".join(lay) or "NESSUNO"))
