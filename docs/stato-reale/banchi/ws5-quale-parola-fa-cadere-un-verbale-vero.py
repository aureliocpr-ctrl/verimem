r"""Quale PAROLA fa cadere un verbale vero? Una fonte sola, dieci verbi.

Chiude la domanda che ho lasciato aperta un'ora fa dichiarando che il mio
disegno non la reggeva: nel banco `ws5-chi-ferma-i-verbali-veri-a-grounding-99`
tre coppie su cinque **non erano iso-contenuto** (la forma A aggiungeva un
esito), quindi non potevo dire se a far cadere il claim fosse **la parola** o
**il contenuto in piu'**. ⇒ Qui la variabile e' UNA SOLA.

IL DISEGNO: **una fonte, una frase, dieci verbi**. La fonte dichiara sia lo
svolgimento sia l'esito, cosi' **ogni verbo della lista e' VERO e sostenuto** -
e chi cade, cade per la parola, non per il contenuto.

    fonte:  «Il collaudo della linea 3 si e' concluso il 12 marzo con esito
             positivo e la linea e' stata approvata dalla commissione.»
    claim:  «Il collaudo della linea 3 e' stato <VERBO> il 12 marzo.»

⚠️ **POPOLAZIONE DI CONTROLLO, e senza di lei il banco e' cieco**: tre claim
sulla stessa fonte che sono **FALSI** (`respinto`, `rinviato`, `sospeso`).
**Devono cadere.** Se non cadessero, un «tutto passa» sui veri non direbbe che
il gate e' equilibrato: direbbe che non guarda.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **una fonte sola** - un verbo che qui cade potrebbe passare
altrove, e viceversa; i verbi sono scelti da me fra quelli d'ufficio;
`L4-grounding`/`L4-review` esclusi dai layer perche' sono il giudice.

ESITO - **SI', E' LA PAROLA. Quattro veri su dieci cadono, e il controllo
scopre il difetto opposto sulla stessa fonte**::

    verbo        atteso    azione       ground  layer                 esito
    concluso     passa     persist       99.90  -                     🟢 passa
    completato   passa     downgrade     99.86  L1.13, L4-relazione   🔴 CADE UN VERO
    ultimato     passa     persist       99.85  -                     🟢 passa
    effettuato   passa     persist       99.86  -                     🟢 passa
    eseguito     passa     persist       99.85  -                     🟢 passa
    svolto       passa     persist       99.86  -                     🟢 passa
    superato     passa     persist       99.41  -                     🟢 passa
    approvato    passa     downgrade     99.83  L1.16                 🔴 CADE UN VERO
    validato     passa     downgrade     99.40  L1.15                 🔴 CADE UN VERO
    verificato   passa     downgrade     99.72  L1.15                 🔴 CADE UN VERO
    --- CONTROLLO (la fonte dice il contrario) ---
    respinto     cade      downgrade      0.54  -                     🟢 fermato
    rinviato     cade      downgrade     15.67  -                     🟢 fermato
    sospeso      cade      persist       98.64  -                     🔴 PASSA UN FALSO

🔑 **LA DOMANDA E' CHIUSA: e' LA PAROLA.** Stessa fonte, stessa frase, stesso
fatto: cambia **una parola** e quattro claim veri su dieci vengono declassati.
I quattro che cadono - `completato`, `approvato`, `validato`, `verificato` -
sono **parole di attestazione**, quelle che i layer `L1.x` cercano nei
**self-claim**. ⇒ **Il presidio anti-autocertificazione scatta su un verbale di
TERZI**: non e' l'agente che dice «*ho verificato*», e' la commissione che ha
approvato - **ma il gate legge il verbo, non chi parla**.

🔴🔴 **E IL CONTROLLO SCOPRE IL DIFETTO OPPOSTO, SULLA STESSA IDENTICA FONTE:
`sospeso` PASSA a 98.64** - mentre la fonte dice che il collaudo **si e'
concluso ed e' stato approvato**. ⇒ Sulla stessa frase, nello stesso istante:

    verificato  VERO,  sostenuto dalla fonte      → FERMATO a 99.72
    sospeso     FALSO, contraddetto dalla fonte   → PASSA   a 98.64

⇒ **Il gate non guarda la dimensione su cui il claim sbaglia.** E' severo sulla
**forma della parola** (dove non serve: il soggetto e' un terzo) e cieco sulla
**contraddizione col contenuto** (dove servirebbe). Nessun layer prende
`sospeso`, e il giudice gli da' 98.64.

📌 **Convergenza indipendente con @ws4** («*il gate e' severo sulla DIMENSIONE
sbagliata*», W7-55) e con @ws2 (W2-67, il gate butta i veri): qui la stessa cosa
esce **a variabile singola, con le due popolazioni sulla stessa fonte e la
stessa frase** - il disegno piu' stretto che ho potuto costruire.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **una fonte sola** - un verbo che qui cade potrebbe passare
altrove; 10 verbi + 3 di controllo scelti da me; non ho misurato se
`writer_role`/`provenance_trusted` salvino i quattro (la cura che esiste per la
collisione di dominio potrebbe valere anche qui, ed e' la prossima domanda).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quale-parola-fa-cadere-un-verbale-vero.py <dir-temp>
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

# tutti VERI e sostenuti dalla fonte: svolgimento + esito positivo + approvazione
VERI = ["concluso", "completato", "ultimato", "effettuato", "eseguito",
        "svolto", "superato", "approvato", "validato", "verificato"]

# CONTROLLO: la fonte dice il contrario. Devono cadere.
FALSI = ["respinto", "rinviato", "sospeso"]


def _gate(claim):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=FONTE, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, [x for x in ws if x not in NON_DETERMINISTICI]


def _riga(verbo, atteso):
    az, g, det = _gate(CLAIM % verbo)
    fermato = az != "persist"
    if atteso == "passa":
        segno = "🔴 CADE UN VERO" if fermato else "🟢 passa"
    else:
        segno = "🟢 fermato" if fermato else "🔴 PASSA UN FALSO"
    print("  %-12s %-9s %-10s %8s  %-26s %s"
          % (verbo, atteso, az, ("%.2f" % g) if g is not None else "None",
             ", ".join(det) if det else "-", segno))
    return fermato, det


def main():
    print("  %-12s %-9s %-10s %8s  %-26s %s"
          % ("verbo", "atteso", "azione", "ground", "layer", "esito"))
    print("  " + "-" * 92)

    caduti, attrib = [], {}
    for v in VERI:
        fermato, det = _riga(v, "passa")
        if fermato:
            caduti.append(v)
            for d in det:
                attrib[d] = attrib.get(d, 0) + 1

    print("  " + "-" * 92 + "\n  POPOLAZIONE DI CONTROLLO (la fonte dice il contrario):")
    passati = [v for v in FALSI if not _riga(v, "cade")[0]]

    print("\n=== SINTESI ===")
    print("  veri sostenuti dalla fonte    %d" % len(VERI))
    print("  🔴 caduti lo stesso           %d  %s" % (len(caduti), ", ".join(caduti) or ""))
    print("  falsi (controllo)             %d" % len(FALSI))
    print("  🔴 passati lo stesso          %d  %s" % (len(passati), ", ".join(passati) or ""))
    if attrib:
        print("\n  chi fa cadere i veri (giudice escluso):")
        for k, v in sorted(attrib.items(), key=lambda kv: -kv[1]):
            print("      %-24s %d volte" % (k, v))
    print("\n  ⚠️ Una sola variabile: stessa fonte, stessa frase, cambia il VERBO.")
    print("     Chi cade qui cade PER LA PAROLA - il contenuto e' identico.")
    print("     E se il controllo passasse, un 'tutto ok' sui veri non varrebbe nulla.")


main()
