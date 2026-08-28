"""L'unica spiegazione rimasta: il soggetto e' una PAROLA VUOTA nella sua lingua?

Stanotte ho ritirato due miei reperti (`8d973b3a`): non c'e' asimmetria di
lingua, c'e' **varianza fra casi** — alcuni scambi di soggetto il giudice li
prende a 0,6, altri li lascia passare a 73,0, e **la lingua non spiega quali**.

Resta una sola spiegazione candidata, e viene dal LEGGERE i casi invece di
contarli: **l'unica coppia che mostrava lo scarto usa come soggetto `ci`** —
che in italiano e' un **pronome clitico** («ci sono», «ci ha»), cioe' una
**parola vuota**, mentre in inglese e' un identificatore qualunque.

IPOTESI: non e' la lingua. E' **un soggetto che, nella lingua della fonte, non
si comporta da soggetto** — un token che il giudice tratta come rumore
grammaticale e quindi non riesce a legare al valore.

IL DISEGNO, a variabile singola: **stessa identica fonte, stesso identico
scambio, cambia SOLO il nome del soggetto.**

    ci      pronome clitico italiano       («ci sono», «ci ha»)
    si      pronome clitico italiano       («si dice»)
    ne      pronome clitico italiano       («ne parla»)
    alfa    neutro, non e' una parola comune
    deploy  neutro, prestito tecnico
    build   neutro, prestito tecnico

LA PREDIZIONE, scritta prima di eseguire: **lo scambio passa (>50) SOLO con i
soggetti clitici**, e resta basso con `alfa`/`deploy`/`build`.

CONDIZIONE DI FALSIFICAZIONE: se lo scambio passa **anche** con un soggetto
neutro, l'ipotesi cade — e allora la varianza resta **INSPIEGATA**, e va
dichiarata tale invece di cercarle un'altra storia. 🔑 *Dopo due ritiri in
quattordici minuti, la tentazione da battere e' proprio quella: trovare
comunque una spiegazione.*

CONTROLLO CHE DEVE POTER FALLIRE, per ogni riga: il claim **vero** (sul secondo
soggetto, che non cambia mai) deve stare alto, e il valore **assente** basso.
Se il vero cala quando cambio il nome del soggetto, sto misurando «il nome
disturba tutto» e non «il nome impedisce il legame».

🔴 **ESITO: IPOTESI FALSIFICATA — e sotto c'e' il reperto piu' solido della
nottata, proprio perche' i controlli sono rimasti COSTANTI.**

    soggetto  vuota?    vero  SCAMBIO  assente
    ci        SI        99.4     73.0      0.7
    si        SI        99.6     62.0      0.7
    ne        SI        99.5      8.2      0.7
    alfa      no        99.4      9.5      0.9
    deploy    no        99.5     62.3      0.7
    build     no        99.5     67.8      0.7

**2 clitici su 3 passano, e 2 neutri su 3 pure** ⇒ **l'ipotesi del clitico e'
morta.** Non c'e' nessuna proprieta' linguistica del soggetto che spieghi quali
scambi passino.

🔑 **MA GUARDANDO LE COLONNE DI CONTROLLO INVECE DI QUELLA CHE CERCAVO:**
`vero` sta fra **99,4 e 99,6** in **tutte e sei** le righe, e `assente` a
**0,7** in tutte e sei. Nel frattempo lo **SCAMBIO** va da **8,2 a 73,0** —
**65 punti** — a **fonte identica**, **claim identico nella forma**, cambiando
**UN SOLO TOKEN** che non ha niente a che vedere con la verita' del claim.

⇒ **Il giudice e' STABILE sulla PRESENZA e INSTABILE sull'ATTRIBUZIONE.** Non
e' cieco: e' **irregolare**, e l'irregolarita' e' concentrata esattamente sulla
domanda «di CHI e' questo valore». I controlli costanti rendono questa lettura
**non aggirabile**: non e' rumore generale del modello, perche' allora si
muoverebbero anche `vero` e `assente`.

⇒ **E spiega la mia nottata**: le differenze che avevo attribuito alla FORMA
(tabella contro prosa, `a43bd32e`) e alla LINGUA (`90fc7fa8`, ritirato) erano
plausibilmente **questa stessa instabilita' vista attraverso due finestre
diverse**. Ho misurato tre volte il medesimo fenomeno dandogli tre nomi
sbagliati, perche' ogni volta cambiavo **piu' di una cosa** insieme.

⛔ **CHE COSA NON DICO**: non so **perche'** alcuni token slegano il soggetto e
altri no. Non ho una regola, e **non gliene invento una**: dopo due ritiri in
quattordici minuti la tentazione da battere era esattamente quella. **La
varianza e' misurata; la sua causa resta INSPIEGATA.**

REGIME: store TEMPORANEO, cross-encoder locale su disco (nessuna API esterna).
Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-un-soggetto-che-non-si-comporta-da-soggetto.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: (nome del soggetto, e' una parola vuota nella lingua della fonte?)
SOGGETTI = [
    ("ci", True),
    ("si", True),
    ("ne", True),
    ("alfa", False),
    ("deploy", False),
    ("build", False),
]

SOGLIA = 50.0


def fonte(sog: str) -> str:
    return (f"Il workflow {sog} ha avuto 50 run, di cui 0 cancellati. "
            f"Il workflow security ha avuto 60 run, di cui 59 cancellati.")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print("  giudice: cross-encoder locale su disco (nessuna API esterna)")
    print("  variabile singola: cambia SOLO il nome del primo soggetto")
    mem = Memory(str(tmp / "sogg.db"))
    n = 0

    def s(claim: str, f: str) -> float:
        nonlocal n
        n += 1
        v = mem.add(claim, topic=f"sg/{n}", source=f,
                    validate="full").get("grounding_score")
        return -1.0 if v is None else float(v)

    print(f"\n  {'soggetto':<10} {'vuota?':<7} {'vero':>7} {'SCAMBIO':>8} "
          f"{'assente':>8}  controllo")
    print("  " + "-" * 60)
    passa_vuoti: list[str] = []
    passa_pieni: list[str] = []
    escluse: list[str] = []
    for sog, vuota in SOGGETTI:
        f = fonte(sog)
        v = s("Il workflow security ha 59 run cancellati.", f)
        sc = s(f"Il workflow {sog} ha 59 run cancellati.", f)
        a = s(f"Il workflow {sog} ha 777 run cancellati.", f)
        ok = v > SOGLIA and a < SOGLIA
        print(f"  {sog:<10} {'SI' if vuota else 'no':<7} {v:>7.1f} {sc:>8.1f} "
              f"{a:>8.1f}  {'ok' if ok else 'ESCLUSA'}")
        if not ok:
            escluse.append(sog)
            continue
        if sc > SOGLIA:
            (passa_vuoti if vuota else passa_pieni).append(f"{sog}={sc:.1f}")

    print(f"\n  [1] CONTROLLI: escluse {escluse or 'nessuna'}")
    if len(escluse) > 2:
        print("      CONTROLLO CADUTO: piu' di due righe non superano vero-alto")
        print("      e assente-basso ⇒ il nome del soggetto disturba TUTTO e non")
        print("      isolo il legame. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     lo scambio PASSA con soggetti VUOTI ...... "
          f"{passa_vuoti or 'nessuno'}")
    print(f"     lo scambio PASSA con soggetti NEUTRI ..... "
          f"{passa_pieni or 'nessuno'}")
    if passa_vuoti and not passa_pieni:
        print("     PREDIZIONE RETTA: passa SOLO con i soggetti che nella lingua")
        print("     della fonte sono parole vuote ⇒ non e' la lingua, e' un")
        print("     SOGGETTO CHE NON SI COMPORTA DA SOGGETTO.")
    elif passa_pieni:
        print("     PREDIZIONE FALSIFICATA: passa anche con un soggetto NEUTRO")
        print("     ⇒ l'ipotesi del clitico CADE. La varianza fra casi resta")
        print("     INSPIEGATA, e la dichiaro tale: dopo due ritiri stanotte, la")
        print("     tentazione da battere e' inventarle un'altra storia.")
    else:
        print("     NESSUNO scambio passa: su questa fonte il giudice li prende")
        print("     tutti ⇒ il caso `ci` delle 01:47 non si riproduce nemmeno")
        print("     con `ci`, e va riletto prima di spiegarlo.")

    print(f"\n  ⚠️ LIMITI: {n} celle, una fonte, un giudice locale, italiano.")
    print("     NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
