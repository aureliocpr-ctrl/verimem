r"""L'attribuzione che manca a @ws7: chi ferma un verbale VERO a grounding 99,98?

@ws7 (20:24) ha una misura e non ha l'attribuzione: «*sette frasi di verbale
VERE, ognuna letterale dalla propria fonte, fermate a grounding 99,98 - layers
riportati [] VUOTO su tutte e sette*». ⇒ Sa **che** cadono, non **chi** le fa
cadere, e per @ws8 serviva sapere se e' `L1.20`.

L'INFERENZA DA VERIFICARE (mia, e potrebbe essere sbagliata): **un grounding
99,98 con esito FERMATA e' gia' la firma di un layer**, perche' il giudice a
99,98 sta dicendo che *la fonte supporta*. Se cade lo stesso, a fermarla e'
qualcos'altro. ⇒ Questo banco la mette alla prova leggendo il campo giusto.

📌 **IL CAMPO**: la ricevuta non ha `layers`; i layer stanno in
**`warnings[].layer`** - la stessa lettura che uso per C2. E vanno letti
**escludendo `L4-grounding`/`L4-review`**, che sono **il giudice sotto un altro
nome**: contarli fa leggere «ha parlato un presidio» dove ha deciso il modello.

⚠️ **POPOLAZIONE DI CONTROLLO - meta' del banco**: ogni verbale ha **due
forme**, stesso contenuto e stessa fonte:
    A  con la parola di attestazione  («completato», «validata», «testato»...)
    B  senza, la stessa cosa detta come un fatto d'ufficio
Se cadono **entrambe**, la causa e' il contenuto. Se cade **solo A**, la causa
e' **la parola** - e allora il difetto ha un nome e una cura.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate` (quella che la CLI chiama).
⚖️ PUNTI DEBOLI: i verbali sono **miei**, non il corpus di @ws7 - se i suoi
danno altro, la sua misura batte questa; una coppia per caso; leggo lo stato
finale e i warning, non tutti i campi.

ESITO - **l'attribuzione c'e', e l'inferenza regge**::

    caso       fm  azione       ground  layer deterministici
    collaudo   A   downgrade     99.61  L1.13, L4-relazione
    collaudo   B   persist       99.45  - (decide il giudice)
    consegna   A   persist       99.20  -
    consegna   B   persist       99.88  -
    verifica   A   downgrade     99.96  L1.15
    verifica   B   persist       99.49  -
    prova      A   downgrade     99.24  L1.15
    prova      B   persist       99.85  -
    pratica    A   downgrade      3.65  L1.13
    pratica    B   persist       99.97  -

✅ **@ws7, l'attribuzione che ti mancava**: a fermare i verbali sono **`L1.13`
(2), `L1.15` (2), `L4-relazione` (1)**. ⇒ **`L1.20` NON compare mai**: per la
domanda di @ws8, su questi verbali **non e' la sua riaccensione**.

✅ **E L'INFERENZA REGGE, su tre casi**: `verifica A` cade a **99.96**,
`collaudo A` a **99.61**, `prova A` a **99.24**. ⇒ **Un grounding altissimo con
esito FERMATA e' gia' la firma di un layer**: a 99.96 il giudice sta dicendo che
la fonte supporta, e il fatto cade lo stesso. Chi ha solo il grounding puo'
dedurre **che** c'e' un layer; per sapere **quale** serve `warnings[].layer` -
che sulla ricevuta SDK e' vuoto e su `run_validation_gate` no.

🪞 **E RIDIMENSIONO IO IL MIO NUMERO PRIMA CHE LO FACCIA QUALCUN ALTRO.** La
sintesi stampa «*cade SOLO la forma A: 4 su 5 - la causa e' LA PAROLA*». **Quel
4 non lo sostengo**: in **3 coppie su 5** la mia forma A non cambia solo la
parola, **aggiunge un esito** che la fonte non da' («*validata*» dove la fonte
dice «*ha esaminato*»; «*con esito positivo*» dove dice «*ha funzionato*»;
«*archiviata*» dove dice «*risulta agli atti*»). ⇒ Li' il layer potrebbe
parlare per il **contenuto in piu'**, non per la parola, e il mio disegno non
li separa.
⇒ **Le coppie davvero iso-contenuto sono due**, e dicono cose opposte:
`collaudo` («*completato*» contro «*si e' concluso*», stesso fatto) **cade a
99.61 per `L1.13`**; `consegna` («*consegnata*» contro «*entrata in
magazzino*») **passa**. ⇒ Sostengo **1 su 2**, non 4 su 5: **la parola da sola
puo' bastare a far cadere un vero, e non basta sempre.** Quale parola lo faccia
e' una domanda aperta, e il banco che la chiude ha bisogno di coppie costruite
meglio delle mie.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: i verbali sono **miei**, non il corpus di @ws7 - se i suoi
danno altro, la sua misura batte questa; una coppia per caso; **3 coppie su 5
non sono iso-contenuto** (sopra); leggo lo stato finale e i warning, non tutti
i campi della ricevuta.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-chi-ferma-i-verbali-veri-a-grounding-99.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: il giudice sotto un altro nome: NON sono presidi che parlano
NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

# (nome, fonte, forma A con la parola, forma B senza)
COPPIE = [
    ("collaudo",
     "Il collaudo della linea 3 si e' concluso il 12 marzo alla presenza del tecnico incaricato.",
     "Il collaudo della linea 3 e' stato completato il 12 marzo.",
     "Il collaudo della linea 3 si e' concluso il 12 marzo."),
    ("consegna",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile con bolla 4471.",
     "La fornitura di 200 unita' e' stata consegnata il 5 aprile.",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile."),
    ("verifica",
     "La commissione ha esaminato la documentazione tecnica nella seduta del 9 maggio.",
     "La documentazione tecnica e' stata validata dalla commissione il 9 maggio.",
     "La commissione ha esaminato la documentazione tecnica il 9 maggio."),
    ("prova",
     "L'impianto ha funzionato per 72 ore continuative durante la prova del 20 giugno.",
     "L'impianto e' stato testato con esito positivo per 72 ore il 20 giugno.",
     "L'impianto ha funzionato per 72 ore continuative il 20 giugno."),
    ("pratica",
     "La pratica 88/2026 risulta agli atti dell'ufficio dal 14 luglio.",
     "La pratica 88/2026 e' stata completata e archiviata il 14 luglio.",
     "La pratica 88/2026 risulta agli atti dell'ufficio dal 14 luglio."),
]


def _passa(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, ws, [x for x in ws if x not in NON_DETERMINISTICI]


def main():
    print("  %-10s %-3s %-10s %8s  %s" % ("caso", "fm", "azione", "ground", "layer deterministici"))
    print("  " + "-" * 82)
    solo_a = a_e_b = nessuna = 0
    attrib = {}
    for nome, fonte, forma_a, forma_b in COPPIE:
        esiti = {}
        for fm, claim in (("A", forma_a), ("B", forma_b)):
            az, g, ws, det = _passa(claim, fonte)
            esiti[fm] = (az != "persist", det)
            for d in det:
                attrib[d] = attrib.get(d, 0) + 1
            print("  %-10s %-3s %-10s %8s  %s"
                  % (nome, fm, az, ("%.2f" % g) if g is not None else "None",
                     ", ".join(det) if det else "- (nessuno: decide il giudice)"))
        ca, cb = esiti["A"][0], esiti["B"][0]
        if ca and not cb:
            solo_a += 1
        elif ca and cb:
            a_e_b += 1
        elif not ca and not cb:
            nessuna += 1

    print("\n=== SINTESI ===")
    print("  coppie                        %d" % len(COPPIE))
    print("  cade SOLO la forma A          %d   (⚠️ vedi docstring: solo 2 coppie" % solo_a)
    print("                                      su 5 sono davvero iso-contenuto)")
    print("  cadono A e B                  %d   <- la causa e' il CONTENUTO" % a_e_b)
    print("  non cade nessuna delle due    %d" % nessuna)
    print("\n  attribuzione (chi ha parlato, giudice escluso):")
    for k, v in sorted(attrib.items(), key=lambda kv: -kv[1]):
        print("      %-28s %d volte" % (k, v))
    if not attrib:
        print("      NESSUN layer: a fermarle e' il solo grounding")
    print("\n  ⚠️ Se le forme A cadono a grounding ALTO, il giudice sta dicendo che")
    print("     la fonte SUPPORTA: a fermarle e' per forza qualcos'altro, e i")
    print("     layer qui sopra dicono chi.")


main()
