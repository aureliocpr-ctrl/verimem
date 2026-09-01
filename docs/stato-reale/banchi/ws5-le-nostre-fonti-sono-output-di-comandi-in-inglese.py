r"""Una fonte TELEGRAFICA e in INGLESE fa cadere un claim VERO scritto in italiano?

Paga il debito lasciato aperto da `91511982`: li' un claim **vero** cadeva a g=0.5 su
`coda: completed=1167 · queued=895 · in_progress=13`, e la causa era **dichiarata non
isolata**. Il candidato era «telegrafica **e** in inglese, mentre il claim e' in
italiano» — due variabili in una, che e' il modo tipico di non spiegare niente.

⚠️ **PERCHE' LA DOMANDA CONTA PIU' DEL CASO**: le nostre `--source` sono quasi tutte
**output di comandi** — `admitted id=… grounding_score=…`, `git log`, `pytest`,
righe di coda CI. Sono **telegrafiche e in inglese**, e i claim che ci appoggiamo sopra
sono **in italiano**. Se quel regime facesse cadere il vero, non sarebbe un caso
particolare: sarebbe **la forma in cui scriviamo la maggior parte dei fatti**.

L'INCROCIO, stessa informazione, stesso numero, claim sempre VERO::

                        fonte in INGLESE        fonte in ITALIANO
    TELEGRAFICA         A                       B
    PROSA               C                       D

⇒ E per ogni cella la coppia **claim vero / claim scambiato**, perche' un numero
solo sul vero non dice se il gate distingue (e' la lezione di `91511982`: senza la
riga del vero, un basso punteggio sul falso non significa niente).

⚠️ **La lingua del CLAIM resta l'italiano in tutte e otto le celle**: cambia solo la
fonte. Cosi' la variabile e' una.

🔴 ESITO — **due reperti, e nessuno dei due era la domanda che avevo posto**::

    fonte                claim VERO            claim SCAMBIATO       VERO riformulato
    A telegrafica EN     CADE g=0.8    L1.13   CADE g=9.9    L1.13   CADE g=0.5    L1.13
    B telegrafica IT     CADE g=0.8    L1.13   CADE g=30.6   L1.13   CADE g=1.0    L1.13
    C prosa EN           CADE g=100.0  L1.13   CADE g=2.4    L1.13   CADE g=99.8   L1.13
    D prosa IT           CADE g=99.7   L1.13   CADE g=1.5    L1.13   CADE g=99.4   L1.13
    (in tutte le celle compare anche `L4.2`, tranne l'ultima)

🔴🔴 **① IN FORMA TELEGRAFICA IL GIUDICE DA' AL FALSO PIU' CHE AL VERO.** In prosa
separa benissimo — `C` **100.0** contro **2.4**, `D` **99.7** contro **1.5** — e in
telegrafica **si rovescia**: `A` vero **0.8** contro falso **9.9**, `B` vero **0.8**
contro falso **30.6** (trentotto volte tanto). ⇒ Non e' «severo sulle telegrafiche»:
**preferisce il falso al vero**, e sono due difetti che portano a cure opposte. E'
la stessa forma di `W5-5` (lunga+tabellare), qui su fonti **corte**.
⚠️ **La lingua non c'entra**: EN e IT si comportano uguale in tutte e due le forme.

🔴 **② E TUTTO CADE LO STESSO, ANCHE A GROUNDING 100.0**, per `L1.13`. Letto il
codice invece di continuare a variare: `L1.13` e' il **completion claim detector** —
«*Closes A1 ANTI-CONFAB gap per «task done/complete/finished» claims*»
(`anti_confab_gate.py:1462`, `l1_completion_detector`). ⇒ **A farlo scattare e' la
parola «completati» / «completed»**, che qui **non afferma un lavoro finito: qualifica
un conteggio di run**. Il claim «*I run completati sono 1167*» e' un **dato numerico**,
e la fonte lo sostiene alla lettera (il giudice dice 100.0).

🪞 **La mia domanda di partenza — «e' la lingua? e' la forma telegrafica?» — era la
domanda sbagliata**, e tre varianti del claim non l'hanno mai toccata: a decidere era
**una parola**. ⇒ Tre giri di banco per arrivare dove **una lettura del codice**
arrivava subito. E' la terza volta stasera che leggere batte variare.

⇒ **PERCHE' CI RIGUARDA**: «*i test completati sono N*», «*i run completed sono N*» e'
**il modo in cui scriviamo i fatti di misura**. ⚠️ **NON propongo di declassare
`L1.13`**: su handoff veri scatta 68 volte su 80 (`W5-7`) e li' serve. La domanda da
misurare e' un'altra — **`L1.13` distingue l'auto-affermazione «il task e' completato»
dal dato «i run completati sono 1167»?** Se non la distingue, il falso positivo cade
proprio sulla classe che usiamo di piu'. **Non l'ho misurato qui.**

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · **un solo processo** (protocollo RAM delle 20:47) ·
claim `ram/giudice` preso.
⚖️ PUNTI DEBOLI: un claim per cella; le quattro fonti dicono la stessa cosa ma non
sono traduzioni parola per parola l'una dell'altra — la prosa e' piu' lunga della
telegrafica **per costruzione**, e quella lunghezza e' un confondente che non tolgo.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-le-nostre-fonti-sono-output-di-comandi-in-inglese.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

FONTI = {
    "A telegrafica EN": "queue: completed=1167 · queued=895 · in_progress=13",
    "B telegrafica IT": "coda: completati=1167 · in_attesa=895 · in_corso=13",
    "C prosa EN": ("The queue currently holds 1167 completed runs, 895 runs waiting "
                   "in the queue and 13 runs still in progress."),
    "D prosa IT": ("La coda contiene in questo momento 1167 run completati, 895 run "
                   "in attesa e 13 run ancora in corso."),
}

#: il claim e' SEMPRE in italiano: a cambiare e' solo la fonte
VERO = "I run completati sono 1167."
SCAMBIATO = "I run completati sono 895."
#: stessa affermazione, riformulata — isola se a fermare sia il LAYER o la FORMA
#: del claim: se `L1.13` sparisce qui, non era la fonte ne' il numero, era la frase.
VERO_ALTRO = "La coda contiene 1167 run completati."


def main():
    print("  %-20s %-26s %-26s %-26s"
          % ("fonte", "claim VERO", "claim SCAMBIATO", "VERO riformulato"))
    print("  " + "-" * 102)
    esiti = {}
    for nome, fonte in FONTI.items():
        riga = []
        for etichetta, claim in (("vero", VERO), ("scambiato", SCAMBIATO),
                                 ("vero2", VERO_ALTRO)):
            r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                    agent=None, source=fonte, grounding_llm=None,
                                    ground_write=True)
            g = getattr(r, "grounding_score", None)
            ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
                  if isinstance(w, dict)]
            det = [x for x in ws if x not in NON_DETERMINISTICI]
            az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
            esito = "passa" if az == "persist" else "CADE"
            esiti[(nome[0], etichetta)] = (esito, g, det)
            riga.append("%-5s g=%-6s %s" % (esito, ("%.1f" % g) if g is not None else "None",
                                            ",".join(det) or "-"))
        print("  %-20s %-26s %-26s %-26s" % (nome, riga[0], riga[1], riga[2]))

    print("\n=== SINTESI ===")
    # ⚠️ due domande DISTINTE, e vanno tenute separate: il gate ACCETTA il vero?
    # e SEPARA il vero dal falso? Una fonte puo' fare la prima e non la seconda.
    accetta = [k for k in "ABCD" if esiti.get((k, "vero"), ("?",))[0] == "passa"]
    separa = [k for k in "ABCD"
              if esiti.get((k, "vero"), ("?",))[0] == "passa"
              and esiti.get((k, "scambiato"), ("?",))[0] == "CADE"]
    print("  il claim VERO passa su: %s" % (", ".join(accetta) or "NESSUNA fonte"))
    print("  il gate SEPARA vero e falso su: %s" % (", ".join(separa) or "NESSUNA fonte"))

    en_vero = [k for k in "AC" if esiti.get((k, "vero"), ("?",))[0] == "passa"]
    it_vero = [k for k in "BD" if esiti.get((k, "vero"), ("?",))[0] == "passa"]
    tel_vero = [k for k in "AB" if esiti.get((k, "vero"), ("?",))[0] == "passa"]
    pro_vero = [k for k in "CD" if esiti.get((k, "vero"), ("?",))[0] == "passa"]
    if len(accetta) == 4:
        print("  🟢 il vero passa su TUTTE e quattro ⇒ ne' la lingua ne' la forma")
        print("     telegrafica, da sole, fanno cadere un claim vero: il caso di")
        print("     `91511982` dipende da qualcos'altro di quella fonte.")
    elif not accetta:
        print("  🔴🔴 IL CLAIM VERO CADE SU TUTTE E QUATTRO: il difetto non e' la fonte,")
        print("       e' questo claim o questo numero — e va cercato li'.")
    else:
        if len(en_vero) < len(it_vero):
            print("  🔴 LA LINGUA PESA: il vero passa su %d fonti IT e %d EN."
                  % (len(it_vero), len(en_vero)))
        if len(tel_vero) < len(pro_vero):
            print("  🔴 LA FORMA PESA: il vero passa su %d fonti in prosa e %d telegrafiche."
                  % (len(pro_vero), len(tel_vero)))
        print("  ⇒ celle in cui il vero passa: %s" % ", ".join(accetta))
    v2 = [k for k in "ABCD" if esiti.get((k, "vero2"), ("?",))[0] == "passa"]
    if v2 and not accetta:
        print("  🔑 MA IL VERO RIFORMULATO PASSA su %s: non era la fonte ne' il numero," % ", ".join(v2))
        print("     era LA FRASE. Il layer lessicale ferma una formulazione e non l'altra,")
        print("     a parita' di verita' e di fonte.")
    elif not v2 and not accetta:
        print("  ⚠️ cade anche il vero riformulato: la causa non e' la forma della frase")
        print("     e resta non isolata.")
    if accetta and not separa:
        print("  ⚠️ E dove il vero passa, il falso passa con lui: il gate ACCETTA ma")
        print("     non SEPARA — sono due proprieta' diverse e qui solo la prima regge.")


main()
