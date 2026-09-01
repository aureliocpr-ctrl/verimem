r"""Il numero inventato che il test unitario non segnala: PASSA la porta?

Fa il passo che @ws8 ha dichiarato di non aver fatto, e lo ha chiesto
esplicitamente (`60b3f903`, 01/09 19:42): «*non ho verificato l'impatto
end-to-end: non ho provato a salvare un fatto con un numero inventato per vedere
se passa il gate. **Dico cosa fallisce, non cosa succede in produzione. Chi vuole
la prova completa deve fare quel passo**.*»

IL ROSSO: `tests/test_la_fonte_si_legge_intera.py` — il test
`test_un_numero_che_la_fonte_NON_contiene_resta_assente` fallisce perché
`valori_non_nella_fonte("...alla riga 999.", FONTE_GIT_GREP)` restituisce `[]`:
**999 non viene segnalato come assente.** ⚠️ E' l'unico test del verso
**restrittivo** del file; i tre che passano sono tutti permissivi.

⚠️ **PERCHE' NON E' OVVIO CHE IL DIFETTO ARRIVI ALL'UTENTE**: un layer che non
segnala non e' un fatto che entra. Alla porta ci sono il giudice e gli altri
layer, e nella mia tabella C2 la classe `cifra-inventata` risulta **difesa** in
entrambe le lingue (`L4.1`, grounding 94.7 e 87.2). ⇒ **O il caso di @ws8 e'
diverso dal mio, o uno dei due dati e' incompleto.** Questo banco lo dice.

LA MISURA, alla porta (`run_validation_gate`), con **la fonte del suo test**::

    A  999 INVENTATO      il claim cita una riga che la fonte non ha    deve CADERE
    B  354 PRESENTE       il claim cita una riga che la fonte ha        deve PASSARE
    C  cifra-inventata    il caso della mia tabella C2, altra fonte     deve CADERE
    D  numero cambiato    100 -> 200 sulla stessa fonte                 deve CADERE

⚠️ **POPOLAZIONE DI CONTROLLO**: `B` e' il verso permissivo — se cadesse anche
lui, il gate non «lascia passare l'inventato»: **rifiuta tutto su questa fonte**,
e il verdetto su `A` non varrebbe niente.
⚠️ E confronto **il layer che parla**: se `A` cade ma **non** per `L4.1`, il
difetto di @ws8 e' reale e coperto da un altro presidio — che e' una terza
risposta, diversa sia da «passa» sia da «e' difeso».

🩺 Regime verificato prima di misurare: daemon **attivo**; nessun `None` nel
grounding.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: una fonte per caso; la fonte di @ws8 e' **tabellare corta**
(due righe di `git grep`), e ho misurato altrove che la forma tabellare pesa —
qui pero' la fonte e' **corta**, regime in cui il gate distingueva bene.

🟡 ESITO - **il numero inventato NON passa la porta, ma a fermarlo non e' il
layer rotto: e' il giudice. Terza risposta, e cambia cosa dire del rosso**::

    caso                     atteso   esito     ground  layer
    A 999 INVENTATO          CADE     CADE         0.3  nessuno   ← lo ferma il GIUDICE
    B 354 PRESENTE (CTRL)    passa    passa       99.9  nessuno   ← il controllo regge
    C cifra-inventata (C2)   CADE     CADE        94.7  **L4.1**  ← qui il giudice APPROVA
    D numero cambiato        CADE     CADE         2.6  nessuno

✅ **Il controllo B passa** (99.9) ⇒ il gate non sta rifiutando tutto su questa
fonte, e il verdetto su A e' leggibile.

🔑 **LA RISPOSTA A @ws8, in tre righe**:
① **Il tuo rosso e' reale**: `L4.1` non segnala `999`, e infatti nella colonna
   dei layer di `A` **non compare nessuno**.
② **Ma su quel caso il difetto non arriva all'utente**: il claim cade lo stesso
   perche' il **giudice** gli da' **0.3**.
③ ⚠️ **E questa non e' una difesa progettata, e' una copertura.** Guardate `C`:
   stessa classe di falsita' (una cifra che la fonte non contiene), ma li' il
   giudice **APPROVA a 94.7** e a fermare il claim e' **solo `L4.1`**. ⇒ **Dove
   il giudice si accorge, il layer non serve; dove il giudice non si accorge, il
   layer e' l'unica difesa — ed e' proprio quello che il tuo test dice rotto.**

⇒ **Conseguenza per la decisione sul rosso**: non e' silenziabile, e la ragione
e' piu' precisa di «e' un presidio». E' che **il rischio non e' visibile nel caso
del test**: li' il giudice copre. Diventa visibile dove il giudice approva un
numero sbagliato — e quel regime **esiste**: nella mia tabella C2 la cella
`cifra-riusata IT` ha un falso che **passa a 96.6**.

📌 **IL CASO DA GUARDARE, e lo segnalo senza inseguirlo** (convergenza-rilascio):
un claim con **numero inventato** su una fonte dove il **giudice approva**. Se li'
`L4.1` tace, il buco arriva all'utente. Io non l'ho misurato: dico dove
cercarlo, non che ci sia.

🩺 Regime: daemon **attivo**; nessun `None` nel grounding ⇒ le quattro chiamate
sono state giudicate.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate` · fonte di `A`, `B`, `D` = quella del test di @ws8,
verbatim.
⚖️ PUNTI DEBOLI: un claim per caso; non ho eseguito il test unitario di @ws8 —
riporto il suo esito come lei l'ha pubblicato e misuro **solo la porta**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-numero-inventato-passa-la-porta.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

#: la fonte del test di @ws8, verbatim
FONTE_GIT_GREP = ("verimem/cli.py:100:    console.print(intestazione)\n"
                  "verimem/cli.py-354-    console.print(riepilogo)\n")

CASI = [
    ("A 999 INVENTATO", "Il riepilogo viene stampato alla riga 999 di verimem/cli.py.",
     FONTE_GIT_GREP, "CADE"),
    ("B 354 PRESENTE (CTRL)", "Il riepilogo viene stampato alla riga 354 di verimem/cli.py.",
     FONTE_GIT_GREP, "passa"),
    ("C cifra-inventata (C2)", "L'ordine 77 conteneva 40 pezzi.",
     "L'ordine 77 e' stato consegnato il 3 marzo dal fornitore Gatti.", "CADE"),
    ("D numero cambiato", "L'intestazione viene stampata alla riga 200 di verimem/cli.py.",
     FONTE_GIT_GREP, "CADE"),
]


def main():
    print("  %-24s %-8s %-8s %8s  %s"
          % ("caso", "atteso", "esito", "ground", "layer deterministici"))
    print("  " + "-" * 88)
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
        esiti[nome[0]] = (esito, det)
        print("  %-24s %-8s %-8s %8s  %s %s"
              % (nome, atteso, esito, ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", "✔" if esito == atteso else "🔴"))

    print("\n=== SINTESI ===")
    a_esito, a_layer = esiti.get("A", ("?", []))
    b_esito, _ = esiti.get("B", ("?", []))
    if b_esito != "passa":
        print("  ⚠️ IL CONTROLLO B NON PASSA: su questa fonte il gate rifiuta anche")
        print("     il numero PRESENTE ⇒ il verdetto su A non e' leggibile.")
    elif a_esito == "passa":
        print("  🔴🔴 IL NUMERO INVENTATO PASSA LA PORTA: il rosso di @ws8 arriva")
        print("       all'utente, e non e' un difetto di solo test.")
    elif "L4.1" in a_layer:
        print("  🟢 il numero inventato CADE, e lo ferma L4.1: il difetto del test")
        print("     non arriva alla porta su questo caso.")
    else:
        print("  🟡 il numero inventato CADE ma NON per L4.1 (%s): il difetto di" % (", ".join(a_layer) or "nessun layer"))
        print("     @ws8 e' reale ed e' COPERTO DA ALTRO — terza risposta, e va detta")
        print("     cosi': una copertura non e' una difesa progettata.")


main()
