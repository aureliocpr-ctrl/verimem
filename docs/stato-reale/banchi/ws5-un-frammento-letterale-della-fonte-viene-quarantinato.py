r"""Un pezzo di testo COPIATO dalla fonte viene quarantinato. Da quale lunghezza?

Nasce da un incidente vero di ieri, non da un'idea: salvando i fatti della cura
`L1.20` ho passato come `--source` l'output di `pytest`, e il gate ha
**quarantinato**

    «EXIT=0.»                                          quarantined
    «Il commit 5ea77b6d: 2 files changed, 161 ...»      quarantined

mentre ha **ammesso**

    «21 passed, 2 skipped.»                            admitted

⇒ Le prime due **compaiono nella fonte alla lettera**. Non e' una parafrasi
sbagliata: e' testo copiato.

🔑 **PERCHE' CONTA ADESSO, e non e' una curiosita' mia.** Stamattina la mia
griglia (`c1f39016`) ha misurato che un claim **ricalcato** dalla fonte passa
**5 volte su 5** — al punto che avevo predetto il contrario e mi sono
falsificata. E @ws3 (`10bf3aef`) ha appena misurato che il perdono di `L1.13`
con una **fonte-eco** e' *incondizionato*: ricalcare la fonte fa **passare un
falso**, 5 su 5. ⇒ **Due misure dicono che aderire alla fonte APRE la porta. Il
mio incidente dice che a volte la CHIUDE su un vero.** Le tre cose non possono
essere tutte generali, e questo banco cerca il confine.

L'IPOTESI, dichiarata PRIMA di eseguire (e pubblicata sul canale allo stesso
istante): **la lunghezza**. Sotto una certa soglia il frammento non e' una
proposizione, e il giudice non ha su cosa pronunciarsi ⇒ punteggio basso ⇒
quarantena. Sopra, la valutazione diventa possibile e il ricalco paga.

⚠️ **L'ESITO CHE MI SMENTIREBBE**: se i frammenti cadessero e passassero senza
ordine rispetto alla lunghezza, l'ipotesi e' sbagliata e la variabile e'
un'altra (la forma? la presenza di un verbo? le cifre?).

⚠️⚠️ **POPOLAZIONE DI CONTROLLO — e qui e' indispensabile**: per ogni lunghezza
c'e' un frammento **FALSO** (stessa forma, numeri che nella fonte non ci sono).
Se cadessero anche quelli, «il vero cade» non direbbe niente: direbbe che sui
frammenti il gate **rifiuta tutto**, e allora il difetto non e' «boccia i veri»
ma «non guarda». Le due letture portano a cure opposte.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **una fonte sola**, ed e' un output tecnico (cifre e simboli,
non prosa) - su prosa la soglia potrebbe stare altrove; i frammenti li scelgo
io; misuro l'**esito**, non il punteggio.

🔴 ESITO - **ipotesi FALSIFICATA nel verso: non cadono i corti, PASSANO TUTTI -
e il difetto lo trova la colonna di controllo**::

    caso                 car.  VERO       ground   FALSO      ground  verdetto
    frammento minimo        7  passa       100.0   passa       100.0  🔴 PASSA ANCHE IL FALSO
    due numeri             21  passa       100.0   cade          0.2  🟢 distingue
    riga di stat           50  passa       100.0   cade          0.1  🟢 distingue
    frase con soggetto     55  passa       100.0   cade          0.2  🟢 distingue
    frase lunga           126  passa       100.0   cade          0.1  🟢 distingue
    ⇒ veri letterali caduti: 0 · falsi passati: 1

🪞 **AVEVO PREDETTO «i frammenti corti CADONO» e pubblicato la predizione prima
di eseguire. E' sbagliata due volte**: nessun vero cade (0 su 5), e il frammento
piu' corto **fa passare anche il falso**. La variabile che avevo scelto - la
lunghezza - conta, ma **nel verso opposto a quello che temevo**: non falsi
allarmi sui frammenti, **falsi permessi**.

🔴 **IL REPERTO: sotto i 21 caratteri il giudice non distingue.** `EXIT=0.` e
`EXIT=1.` prendono **entrambi 100.0** sulla stessa fonte, che dice `EXIT=0`.
Non e' una banda incerta: e' il punteggio massimo a **una cosa e al suo
contrario**. Da 21 caratteri in su la separazione e' netta (100.0 contro 0.1-0.2)
e non ha vie di mezzo - la stessa bimodalita' misurata altrove, qui col
**contenuto** identico e solo la lunghezza a cambiare.

⚠️ **E SENZA LA COLONNA DEI FALSI AVREI LETTO «5 su 5 passano, tutto bene».**
La colonna di controllo era scritta prima proprio per questo, ed e' l'unica
ragione per cui questo banco dice qualcosa.

⚖️ **CIO' CHE NON SPIEGA: l'incidente da cui e' nato.** «EXIT=0.» qui **passa**
a 100.0, ieri sulla porta CLI con la source vera era **quarantinato**. Il banco
non riproduce il caso che voleva spiegare ⇒ vedi
`ws5-la-fonte-lunga-e-troncata-e-conta-dove-sta-il-pezzo.py`, dove ho provato -
e falsificato - altre due spiegazioni. **La causa dell'incidente resta ignota.**

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate` — **non** la porta CLI dove l'incidente e' avvenuto,
ed e' il primo limite da leggere.
⚖️ ALTRI PUNTI DEBOLI: una fonte sola, tecnica (cifre e simboli); i frammenti
li scelgo io; la soglia «fra 7 e 21 caratteri» e' fra due misure, non misurata.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-un-frammento-letterale-della-fonte-viene-quarantinato.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

#: Un output tecnico vero, della stessa forma di quello che ha causato
#: l'incidente: righe di pytest e di git.
FONTE = (
    "tests/test_l120_e_un_avviso_non_un_veto.py ....... [ 33%]\n"
    "tests/test_l120_multilingual_selfclaim.py ........ [100%]\n"
    "21 passed, 2 skipped, 1 warning in 9.31s\n"
    "EXIT=0\n"
    "5ea77b6d47fe L1.20 dichiara e non trattiene\n"
    " tests/test_l120_e_un_avviso_non_un_veto.py | 129 +++++\n"
    " verimem/anti_confab_gate.py                |  33 ++--\n"
    " 2 files changed, 161 insertions(+), 1 deletion(-)\n"
)

#: (etichetta, testo VERO copiato dalla fonte, testo FALSO della stessa forma)
#: I falsi cambiano SOLO le cifre: stessa lunghezza, stessa struttura.
COPPIE = [
    ("frammento minimo", "EXIT=0.", "EXIT=1."),
    ("due numeri", "21 passed, 2 skipped.", "43 passed, 9 skipped."),
    ("riga di stat",
     "2 files changed, 161 insertions(+), 1 deletion(-).",
     "7 files changed, 402 insertions(+), 8 deletions(-)."),
    ("frase con soggetto",
     "Il commit 5ea77b6d ha 2 files changed e 161 insertions.",
     "Il commit 5ea77b6d ha 7 files changed e 402 insertions."),
    ("frase lunga",
     "L'esecuzione dei test riporta 21 passed, 2 skipped, 1 warning in 9.31s "
     "e il commit 5ea77b6d cambia 2 files con 161 insertions.",
     "L'esecuzione dei test riporta 43 passed, 9 skipped, 4 warning in 2.10s "
     "e il commit 5ea77b6d cambia 7 files con 402 insertions."),
]


def _gate(claim):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=FONTE, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g, [x for x in ws if x not in NON_DETERMINISTICI]


def main():
    print("  %-20s %4s  %-9s %8s   %-9s %8s  %s"
          % ("caso", "car.", "VERO", "ground", "FALSO", "ground", "verdetto"))
    print("  " + "-" * 92)
    veri_caduti = falsi_passati = 0
    for nome, vero, falso in COPPIE:
        pv, gv, _dv = _gate(vero)
        pf, gf, _df = _gate(falso)
        if not pv:
            veri_caduti += 1
        if pf:
            falsi_passati += 1
        if pv and not pf:
            verdetto = "🟢 distingue"
        elif not pv and not pf:
            verdetto = "🔴 CADE ANCHE IL VERO"
        elif pv and pf:
            verdetto = "🔴 PASSA ANCHE IL FALSO"
        else:
            verdetto = "🔴🔴 ROVESCIATO"
        print("  %-20s %4d  %-9s %8s   %-9s %8s  %s"
              % (nome, len(vero), "passa" if pv else "CADE",
                 ("%.1f" % gv) if gv is not None else "None",
                 "passa" if pf else "cade",
                 ("%.1f" % gf) if gf is not None else "None", verdetto))

    print("\n=== SINTESI ===")
    print("  coppie                          %d" % len(COPPIE))
    print("  🔴 veri LETTERALI caduti        %d" % veri_caduti)
    print("  🔴 falsi passati                %d" % falsi_passati)
    print("\n  ⚠️ Le due colonne vanno lette INSIEME. Se cadono i veri E cadono i")
    print("     falsi, il gate non «boccia i veri»: sui frammenti non guarda, e")
    print("     la cura sarebbe un'altra. Se i veri cadono e i falsi passano, e'")
    print("     rovesciato, ed e' il caso peggiore.")
    print("  🔮 Ipotesi dichiarata prima: decide LA LUNGHEZZA - i corti cadono,")
    print("     i lunghi passano. Se l'ordine non c'e', l'ipotesi e' falsificata.")


main()
