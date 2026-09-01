r"""Cosa distingue lo scambio di grandezza che il moat FERMA da quello che passa?

Due misure in contraddizione apparente, entrambe di oggi::

    @ws4 (canale, 20:00)   claim «i run ci completed sono 895»
                           span  «coda: completed=1167 · queued=895 · in_progress=13»
                           ⇒ FERMATO, g=2.12 — «il moat NON e' cieco su questa
                             popolazione»

    ws5 (`00f8a18b`)       claim «I quarantinati sono 14304»
                           fonte tabella con `ammessi … 14304` e `quarantinati … 2679`
                           ⇒ PASSA, g=99.9 — e in prosa 100.0

⇒ Stessa classe di falsita' — **il numero giusto attaccato alla grandezza sbagliata** —
e due esiti opposti. Uno dei due casi ha qualcosa che l'altro non ha.

LA PREDIZIONE, scritta PRIMA di eseguire e falsificabile: **la differenza e' la
DISTANZA fra le due grandezze nella fonte.** Nel caso di @ws4 stanno **nella stessa
riga**, separate da un punto medio; nel mio stanno **su righe diverse** di una tabella.
Se il moat confronta un contesto locale, il primo gli mette le due grandezze sotto gli
occhi insieme e il secondo no.

L'INCROCIO che la mette alla prova::

                              claim SCAMBIATO        claim CORRETTO
    grandezze STESSA RIGA     deve CADERE            deve passare
    grandezze RIGHE DIVERSE   ?                      deve passare

⇒ I due «claim CORRETTO» sono la **popolazione di controllo**: se cadessero anche
loro, il banco misurerebbe un gate che rifiuta tutto e la predizione non sarebbe
verificabile.
⇒ E includo **il caso di @ws4 verbatim** come controllo positivo esterno: se non cade,
non sto riproducendo la sua misura e ogni confronto e' vuoto.

🔴 ESITO — **la mia predizione cade, e sotto c'e' qualcosa di piu' importante: il
«controllo positivo» da cui partivo non e' un controllo positivo**::

    caso                           esito    ground   layer
    A stessa riga, SCAMBIO         passa      97.6   L4.2          🪞 doveva CADERE
    B stessa riga, corretto        passa      99.5   L4.2
    C righe diverse, SCAMBIO       passa     100.0   L4.2
    D righe diverse, corretto      passa      99.9   L4.2
    E caso @ws4 (CTRL+)            CADE        0.9   L1.13, L4.1, L4.2
    F caso @ws4 CORRETTO           CADE        0.5   L1.13, L4.1, L4.2   🔴 il VERO
    G @ws4 senza orario, SCAMBIO   CADE        4.0   L1.13, L4.2
    H @ws4 senza orario, corretto  CADE        0.9   L1.13, L4.2         🔴 il VERO

🪞 **① LA MIA PREDIZIONE E' FALSIFICATA.** Avevo scritto, prima di eseguire, che il
confine fosse **la distanza fra le due grandezze nella fonte**. Lo scambio **passa in
entrambe le forme**: stessa riga **97.6**, righe diverse **100.0**. ⇒ Non e' la
distanza, e **la classe passa in tutte e quattro le forme che ho provato finora**
(qui due, piu' tabella e prosa in `00f8a18b`).

🔴🔴 **② E IL CONTROLLO POSITIVO DI @ws4 NON E' UN CONTROLLO POSITIVO.** Sulla sua
fonte cade il falso (`E`, g=0.9 — riproduco il suo fermato) **ma cade anche il claim
VERO** (`F`, g=**0.5**): «*i run ci completed sono 1167*» e' cio' che la fonte dice
**alla lettera**. ⇒ **Li' il gate non «becca lo scambio»: rifiuta la fonte.** Un
`g=2.12` sul falso, senza il valore sul vero accanto, non distingue «il moat vede
l'errore» da «il moat non vede niente su questa fonte».

⇒ E **non e' la marca temporale**: togliendo «*Alle 21:47 del 30/08*» il claim vero
cade lo stesso (`H`, g=0.9). **La causa per cui quella fonte rifiuta tutto NON
l'ho isolata** — il candidato e' che sia **telegrafica e in inglese** mentre il claim
e' in italiano, ma non l'ho misurato e non lo dichiaro.

✅ **③ CONFERMA INDIPENDENTE DI `W5-11`, e non la cercavo**: `L4.1` compare in `E` ed
`F` (col claim che dice «*Alle 21:47 del 30/08*») e **sparisce** in `G` ed `H`, che
sono identici meno l'orario. ⇒ **La marca temporale non sostenuta fa scattare `L4.1`**,
come misurato in `3b4360d7` — qui su una fonte diversa, in un banco che serviva ad
altro.

⇒ **PER LA DECISIONE SUL CUT**: @ws4 stava usando quel caso come prova che «*su questa
popolazione il moat NON e' cieco*». Il suo dato resta vero; **cio' che non regge e' la
lettura**, perche' manca la riga del claim corretto — e quando c'e', dice che su quella
fonte il moat **non distingue**, non che distingue bene. **Chi decide sul cut deve
avere tutte e due le righe.**

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · **un solo processo** per tutte le chiamate (protocollo RAM
delle 20:47: il giudice costa 758 MB e tutto al primo uso) · claim `ram/giudice` preso.
⚖️ PUNTI DEBOLI: un claim per cella; le fonti sono costruite da me per isolare la
distanza, quindi differiscono anche in altro (lunghezza, punteggiatura); e **il caso di
@ws4 lo riporto dal suo messaggio**, non dalla sua esecuzione.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-lo-scambio-di-grandezza-e-la-distanza-fra-le-due.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

#: le due grandezze SULLA STESSA RIGA, come nella fonte di @ws4
STESSA_RIGA = "conteggio: ammessi=14304 · quarantinati=2679 · in_revisione=13"

#: le stesse due grandezze su RIGHE DIVERSE, come nella mia tabella
RIGHE_DIVERSE = (
    "  popolazione                          totale\n"
    "  ---------------------------------------------\n"
    "  ammessi                               14304\n"
    "  quarantinati                           2679\n")

#: la fonte di @ws4, verbatim dal suo messaggio delle 20:00
FONTE_WS4 = "coda: completed=1167 · queued=895 · in_progress=13"

CASI = [
    ("A stessa riga, SCAMBIO", "I quarantinati sono 14304.", STESSA_RIGA, "CADE"),
    ("B stessa riga, corretto", "Gli ammessi sono 14304.", STESSA_RIGA, "passa"),
    ("C righe diverse, SCAMBIO", "I quarantinati sono 14304.", RIGHE_DIVERSE, "?"),
    ("D righe diverse, corretto", "Gli ammessi sono 14304.", RIGHE_DIVERSE, "passa"),
    # controllo positivo ESTERNO: il caso che @ws4 ha misurato fermato a g=2.12.
    # Se non cade, non sto riproducendo la sua misura e il confronto e' vuoto.
    ("E caso @ws4 (CTRL+)", "Alle 21:47 del 30/08 i run ci completed sono 895.",
     FONTE_WS4, "CADE"),
    ("F caso @ws4 corretto", "Alle 21:47 del 30/08 i run ci completed sono 1167.",
     FONTE_WS4, "passa"),
    # G e H tolgono UNA cosa sola dal claim di @ws4: la marca temporale «Alle 21:47
    # del 30/08», che la sua fonte non contiene. Se bastasse quella a far cadere sia
    # il vero sia il falso, il suo «controllo positivo sul moat» sarebbe spiegato dal
    # reperto W5-11 (orari e date brevi non potati) e NON direbbe nulla sullo scambio.
    ("G @ws4 SENZA orario, SCAMBIO", "I run ci completed sono 895.", FONTE_WS4, "?"),
    ("H @ws4 SENZA orario, corretto", "I run ci completed sono 1167.", FONTE_WS4, "passa"),
]


def main():
    print("  %-28s %-8s %8s  %-20s %s"
          % ("caso", "esito", "ground", "layer", "atteso"))
    print("  " + "-" * 84)
    esiti = {}
    for nome, claim, fonte, atteso in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
              if isinstance(w, dict)]
        det = [x for x in ws if x not in NON_DETERMINISTICI]
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        esito = "passa" if az == "persist" else "CADE"
        esiti[nome[0]] = (esito, g, det)
        segno = "✔" if atteso == "?" or esito == atteso else "🔴"
        print("  %-28s %-8s %8s  %-20s %s %s"
              % (nome, esito, ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", atteso, segno))

    print("\n=== SINTESI ===")
    a, b, cc, d, e, f, g, h = (esiti.get(k, ("?", None, [])) for k in "ABCDEFGH")
    if e[0] != "CADE":
        print("  ⚠️ IL CONTROLLO POSITIVO ESTERNO NON CADE (caso @ws4, g=%s): non sto"
              % (("%.1f" % e[1]) if e[1] is not None else "?"))
        print("     riproducendo la sua misura ⇒ nessun confronto e' leggibile.")
        return
    if f[0] != "passa":
        print("  🔴🔴 SULLA FONTE DI @ws4 CADE ANCHE IL CLAIM VERO (F, g=%.1f):"
              % (f[1] or 0.0))
        print("       «completed sono 1167» e' cio' che la fonte dice ALLA LETTERA.")
        print("       ⇒ li' il gate non «becca lo scambio»: RIFIUTA LA FONTE, e il")
        print("         g=2.12 sul falso non e' un controllo positivo sul moat.")
        if h[0] == "passa" and g[0] == "passa":
            print("  🔑 E LA CAUSA E' LA MARCA TEMPORALE: togliendo «Alle 21:47 del 30/08»")
            print("     passano ENTRAMBI (G scambio %.1f, H corretto %.1f) ⇒ a far cadere"
                  % (g[1] or 0.0, h[1] or 0.0))
            print("     quel caso era l'ORARIO non sostenuto (reperto W5-11), non lo scambio.")
        elif h[0] == "passa":
            print("  🔑 Senza l'orario il VERO passa (%.1f) e lo scambio cade: allora su"
                  % (h[1] or 0.0))
            print("     quella fonte il moat lo scambio lo becca davvero.")
        else:
            print("  ⚠️ anche senza orario il claim vero cade (H=%s): la causa e' un'altra"
                  % h[0])
            print("     e non l'ho isolata.")
        return
    if b[0] != "passa" or d[0] != "passa":
        print("  ⚠️ UN CLAIM CORRETTO CADE (B=%s D=%s): il gate rifiuta troppo in"
              % (b[0], d[0]))
        print("     questo regime e la predizione non e' verificabile.")
        return
    if a[0] == "CADE" and cc[0] == "passa":
        print("  🟢 PREDIZIONE CONFERMATA: lo scambio CADE quando le due grandezze stanno")
        print("     nella STESSA RIGA (g=%.1f) e PASSA quando stanno su righe diverse (g=%.1f)."
              % (a[1] or 0.0, cc[1] or 0.0))
        print("     ⇒ il confine e' la DISTANZA nella fonte, non la classe di falsita'.")
    elif a[0] == "CADE" and cc[0] == "CADE":
        print("  🪞 PREDIZIONE FALSIFICATA: cadono ENTRAMBI ⇒ non e' la distanza.")
        print("     La differenza col mio caso precedente sta in qualcos'altro della fonte.")
    elif a[0] == "passa":
        print("  🔴🔴 PASSA ANCHE SULLA STESSA RIGA (g=%.1f): lo scambio non e' fermato"
              % (a[1] or 0.0))
        print("       nemmeno nel regime in cui @ws4 lo ha visto fermare ⇒ a distinguere")
        print("       i due casi e' qualcosa del CONTENUTO, non della forma.")
    else:
        print("  ⚠️ esito inatteso: A=%s C=%s" % (a[0], cc[0]))


main()
