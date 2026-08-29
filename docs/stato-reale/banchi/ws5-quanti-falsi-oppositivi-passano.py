r"""Il buco sul verso opposto: quanti verbi che CONTRADDICONO la fonte passano?

Simmetrico esatto di `ws5-quale-parola-fa-cadere-un-verbale-vero.py`, con lo
stesso disegno gia' validato contro il confondente dell'ordine
(`ws5-e-il-verbo-o-la-posizione-nel-processo.py`): **una fonte, una frase,
cambia solo il verbo**.

Li' ho misurato i VERI che cadono (4 su 10) e ho trovato di striscio, nella
popolazione di controllo, che **`sospeso` PASSA a 98.64** su una fonte che dice
«*si e' concluso... approvato*». ⚠️ **Tre falsi non fanno una classe**: con
`respinto` a 0.54 e `rinviato` a 15.67 accanto, `sospeso` poteva benissimo
essere **un caso isolato**.

⇒ LA DOMANDA, e ha due esiti opposti che valgono cose diverse:
    passa SOLO `sospeso`      → e' un caso, e il buco e' stretto
    ne passano diversi        → e' una CLASSE, e il gate e' cieco alla
                                contraddizione su un'intera famiglia di verbi

    fonte:  «Il collaudo della linea 3 si e' concluso il 12 marzo con esito
             positivo e la linea e' stata approvata dalla commissione.»
    claim:  «Il collaudo della linea 3 e' stato <VERBO> il 12 marzo.»

⚠️ **POPOLAZIONE DI CONTROLLO**: accanto ai falsi rimetto i **sei verbi VERI**
che passavano nel banco originale. Se passassero **tutti**, veri e falsi, il
banco non direbbe «il gate e' cieco»: direbbe che su questa fonte il gate ha
smesso di guardare, e allora il numero sui falsi non varrebbe niente. **Serve
che i veri passino E che qualche falso cada.**

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: una fonte sola; i verbi sono scelti da me fra quelli che
**negano il completamento**; non misuro se un umano concorderebbe che ogni
verbo contraddice la fonte - lo assumo, ed e' un'assunzione mia.

ESITO - **il buco e' STRETTO (2 su 12), il mio timore era sbagliato, e sotto
c'e' un reperto piu' piccolo e piu' duro**::

    sospeso        98.64  🔴 PASSA        rimandato      93.74  🔴 PASSA
    rinviato       15.67  🟢 fermato      interrotto      8.06  🟢 fermato
    annullato       0.77  🟢 fermato      bloccato        1.41  🟢 fermato
    revocato        1.16  🟢 fermato      negato          0.73  🟢 fermato
    fallito         1.18  🟢 fermato      abbandonato     0.64  🟢 fermato
    rifiutato       0.62  🟢 fermato      respinto        0.54  🟢 fermato
    --- CONTROLLO: i sei veri, tutti PASSATI (99.41 - 99.90), 0 caduti ---

🪞 **PRIMA COSA: IL MIO TIMORE ERA SBAGLIATO, E LO DICO PRIMA DEL RESTO.**
Avevo scritto la domanda cosi': «*se ne passano diversi e' una CLASSE, e il gate
e' cieco alla contraddizione su un'intera famiglia*». **Non lo e': 2 su 12.**
Dieci verbi oppositivi su dodici sono fermati, **e con punteggi bassissimi**
(0.54-15.67). ⇒ Il buco che avevo trovato di striscio e' **stretto**, non
sistemico, e chi avesse letto il mio `sospeso` di un'ora fa come «il gate non
vede le contraddizioni» avrebbe generalizzato da un caso. **Il controllo tiene
in piedi il numero**: 0 veri caduti su 6, quindi il gate non ha smesso di
guardare - i dieci fermati sono fermati davvero.

🔑 **MA SOTTO C'E' LA COSA CHE CONTA, ED E' UNA COPPIA DI SINONIMI**::

    rinviato    15.67   🟢 FERMATO
    rimandato   93.74   🔴 PASSATO
                        ⇒ 78 punti di differenza

**«*Il collaudo e' stato rinviato*» e «*il collaudo e' stato rimandato*» dicono
la stessa identica cosa**, sono false allo stesso modo sulla stessa fonte, e
stanno nella stessa frase. Il giudice ne ferma una a 15.67 e ammette l'altra a
93.74. ⇒ **Non e' una soglia da tarare: e' che il punteggio non misura la
relazione col contenuto**, altrimenti due sinonimi non potrebbero distare 78
punti.

📐 **E LA DISTRIBUZIONE E' BIMODALE, il che conferma @ws3 per un'altra strada**:
dei dodici falsi, **dieci stanno sotto 16 e due sopra 93. Zero in mezzo.** ⇒ E'
il suo «*la banda 40-80 non puo' riempirsi: il CE decide, non gradua*»
(`c466d298`), qui su una popolazione costruita in modo del tutto diverso -
**dodici verbi su una fonte fissa** invece del corpus. Il giudice non e' poco
sicuro sui due che sbaglia: **e' sicurissimo, dalla parte sbagliata**.

📌 I due che passano (`sospeso`, `rimandato`) indicano **rinvio temporaneo**;
i dieci fermati indicano **negazione o fallimento**. ⇒ L'ipotesi - e resta
**un'ipotesi non misurata** - e' che il giudice tratti «rinviato nel tempo» come
compatibile con «concluso», invece che come una contraddizione. `rinviato` a
15.67 la incrina: e' della stessa famiglia e viene fermato.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **una fonte sola** - la coppia sinonima andrebbe rifatta su
altre fonti prima di chiamarla una legge; i verbi sono scelti da me; **assumo
io** che ognuno dei dodici contraddica la fonte, e su `sospeso`/`rimandato`
qualcuno potrebbe dissentire (ma allora dovrebbe dissentire anche su
`rinviato`, che il gate ferma).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quanti-falsi-oppositivi-passano.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

FONTE = ("Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
         "e la linea e' stata approvata dalla commissione.")
CLAIM = "Il collaudo della linea 3 e' stato %s il 12 marzo."

# FALSI: ognuno nega che il collaudo si sia concluso con esito positivo
OPPOSITIVI = ["sospeso", "respinto", "rinviato", "annullato", "interrotto",
              "bloccato", "rimandato", "revocato", "negato", "fallito",
              "abbandonato", "rifiutato"]

# CONTROLLO: i veri che passavano nel banco originale. DEVONO ancora passare.
VERI = ["concluso", "ultimato", "effettuato", "eseguito", "svolto", "superato"]


def _gate(verbo):
    r = run_validation_gate(proposition=CLAIM % verbo, verified_by=None, topic=None,
                            agent=None, source=FONTE, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az != "persist", g, [x for x in ws if x not in NON_DETERMINISTICI]


def main():
    print("  %-14s %-10s %8s  %-22s %s"
          % ("verbo", "atteso", "ground", "layer", "esito"))
    print("  " + "-" * 78)
    passati = []
    for v in OPPOSITIVI:
        fermato, g, det = _gate(v)
        if not fermato:
            passati.append((v, g))
        print("  %-14s %-10s %8s  %-22s %s"
              % (v, "cade", ("%.2f" % g) if g is not None else "None",
                 ", ".join(det) or "-",
                 "🟢 fermato" if fermato else "🔴 PASSA UN FALSO"))

    print("  " + "-" * 78 + "\n  CONTROLLO - i veri che devono ancora passare:")
    veri_caduti = []
    for v in VERI:
        fermato, g, det = _gate(v)
        if fermato:
            veri_caduti.append(v)
        print("  %-14s %-10s %8s  %-22s %s"
              % (v, "passa", ("%.2f" % g) if g is not None else "None",
                 ", ".join(det) or "-",
                 "🔴 CADE UN VERO" if fermato else "🟢 passa"))

    print("\n=== SINTESI ===")
    print("  falsi oppositivi provati      %d" % len(OPPOSITIVI))
    print("  🔴 PASSATI lo stesso          %d  %s"
          % (len(passati), ", ".join("%s (%.1f)" % (v, g or -1) for v, g in passati) or "-"))
    print("  controllo: veri caduti        %d/%d  %s"
          % (len(veri_caduti), len(VERI), ", ".join(veri_caduti) or "-"))
    print("\n  ⚠️ Come si legge: se passassero TUTTI (falsi e veri), il gate avrebbe")
    print("     smesso di guardare su questa fonte e il numero non varrebbe nulla.")
    print("     Il reperto esiste solo se i veri passano E qualche falso cade.")


main()
