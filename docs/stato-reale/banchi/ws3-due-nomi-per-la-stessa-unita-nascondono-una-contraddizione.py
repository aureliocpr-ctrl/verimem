"""Due nomi per la stessa unità nascondono una contraddizione?

Ipotesi dichiarata NON misurata in `fafd1475`, dopo aver contato **4140 unità
distinte** nel corpus con il **46% viste una volta sola**::

    «il file conta 100 righe» e «il file conta 200 linee» ricevono DUE unita'
    diverse ⇒ non vengono mai confrontati ⇒ una contraddizione VERA non viene
    vista. E' il difetto OPPOSTO a quello che il modulo dichiara
    (`quantity_match.py:153`: «una falsa unita' CREA conflitti»).

Questo banco la misura. **Non cura niente.**

IL DISEGNO, a variabile singola: la stessa fonte, la stessa contraddizione, e
cambia **solo il NOME dell'unità** nel claim.

    fonte:  «Il file wake.py conta 100 righe.»
    A  vero            «... conta 100 righe.»    -> deve passare
    B  contraddizione
       STESSA parola   «... conta 200 righe.»    -> deve essere fermata
    C  contraddizione
       SINONIMO        «... conta 200 linee.»    -> ???  <- LA CELLA

LA PREDIZIONE, scritta prima di eseguire: **B fermata, C ammessa**. Se C passa
dove B viene fermata, la contraddizione è la stessa e a cambiare è **solo il
nome dell'unità** ⇒ **la frammentazione nasconde una contraddizione vera**.

CONDIZIONE DI FALSIFICAZIONE: se C è fermata come B, l'unità non frammenta il
confronto e **l'ipotesi che ho pubblicato va ritirata**.

CONTROLLO CHE DEVE POTER FALLIRE: A deve passare in tutte le coppie. Se un
claim VERO viene fermato, sto misurando un gate rotto e non un buco.

⚠️ E un controllo sull'ESTRATTORE, perché la spiegazione non sia inventata: il
banco stampa cosa `extract_quantities` vede nei tre claim. Se «righe» e «linee»
ricevessero la **stessa** unità normalizzata, il meccanismo che ipotizzo non
esisterebbe e il risultato avrebbe un'altra causa.

REGIME: un processo, store temporaneo vuoto, porta SDK, `validate="full"`, IT.

    python docs/stato-reale/banchi/ws3-due-nomi-per-la-stessa-unita-nascondono-una-contraddizione.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

#: (etichetta, fonte, claim VERO, claim contraddittorio STESSA parola,
#:  claim contraddittorio SINONIMO)
# ⚠️ LA CELLA D E' ARRIVATA DOPO, e nasce dalla predizione CADUTA. B e C sono
# fermate entrambe 4 su 4 — ma NON perche' l'unita' conti: `L4.1` le ferma
# perche' il valore contraddittorio (200, 60, 90, 9000) NON E' NELLA FONTE
# AFFATTO, e per un valore assente l'unita' e' irrilevante. Il mio disegno non
# poteva distinguere «le unita' non frammentano» da «le unita' non sono state
# nemmeno consultate».
# 🔑 Ragionando sul PERCHE', la frammentazione fa danno nella direzione
# OPPOSTA a quella che avevo previsto: un claim VERO scritto con un SINONIMO
# porta `('linee', 100)` mentre la fonte porta `('righe', 100)` ⇒ la coppia non
# combacia ⇒ `L4.1` segnala un VERO. Non un falso NEGATIVO: un falso POSITIVO.
COPPIE = [
    ("righe/linee",
     "Il file wake.py conta 100 righe di codice.",
     "Il file wake.py conta 100 righe di codice.",
     "Il file wake.py conta 200 righe di codice.",
     "Il file wake.py conta 200 linee di codice.",
     "Il file wake.py conta 100 linee di codice."),
    ("giorni/giornate",
     "Il preavviso di recesso e' di 30 giorni.",
     "Il preavviso di recesso e' di 30 giorni.",
     "Il preavviso di recesso e' di 60 giorni.",
     "Il preavviso di recesso e' di 60 giornate.",
     "Il preavviso di recesso e' di 30 giornate."),
    ("secondi/s",
     "La procedura richiede 45 secondi.",
     "La procedura richiede 45 secondi.",
     "La procedura richiede 90 secondi.",
     "La procedura richiede 90 s.",
     "La procedura richiede 45 s."),
    ("euro/EUR",
     "La cauzione ammonta a 5000 euro.",
     "La cauzione ammonta a 5000 euro.",
     "La cauzione ammonta a 9000 euro.",
     "La cauzione ammonta a 9000 EUR.",
     "La cauzione ammonta a 5000 EUR."),
]


def _strati(ric) -> list[str]:
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415
    from verimem.quantity_match import extract_quantities  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print("    store TEMPORANEO vuoto · un processo · porta SDK · "
          "validate='full' · IT")

    # ── controllo sull'estrattore: le due parole danno DUE unita'? ──────
    print("\n  [0] COSA VEDE L'ESTRATTORE — se le due parole dessero la STESSA")
    print("      unita', il meccanismo che ipotizzo non esisterebbe")
    diverse = 0
    for et, _f, _a, b, c, _d in COPPIE:
        ub = sorted(extract_quantities(b, come_fonte=True))
        uc = sorted(extract_quantities(c, come_fonte=True))
        nb = {u for u, _v in ub}
        nc = {u for u, _v in uc}
        stessa = nb == nc
        diverse += 0 if stessa else 1
        print(f"      {et:<16} stessa-parola {str(ub):<26} sinonimo {str(uc):<26} "
              f"{'UNITA IDENTICA' if stessa else 'unita DIVERSE'}")
    print(f"      ⇒ coppie con unita' DIVERSE: {diverse} su {len(COPPIE)}")

    mem = Memory(str(Path(tempfile.mkdtemp()) / "unita.db"))

    print(f"\n  [1] {'coppia':<16} {'A vero':<14} {'B falso stessa':<16} "
          f"{'C falso sinonimo':<16} {'D VERO sinonimo':<16}")
    print("      " + "-" * 88)
    righe_out = []
    for i, (et, fonte, a, b, c, d) in enumerate(COPPIE):
        esiti = []
        for j, claim in enumerate((a, b, c, d)):
            r = mem.add(claim, topic=f"un/{i}/{j}", source=fonte, validate="full")
            st = str(r.get("status"))
            ls = _strati(r)
            esiti.append((st != "quarantined", any("L4.1" in x for x in ls),
                          float(r.get("grounding_score") or -1)))
        (a_ok, _a41, ag), (b_ok, b41, bg), (c_ok, c41, cg), (d_ok, d41, dg) = esiti
        righe_out.append((et, a_ok, b_ok, b41, c_ok, c41, d_ok, d41))
        def _f(ok: bool, l41: bool, g: float) -> str:
            return f"{'ENTRA' if ok else 'ferma'} {g:5.1f}{' L4.1' if l41 else ''}"
        print(f"      {et:<16} {_f(a_ok, False, ag):<14} {_f(b_ok, b41, bg):<16} "
              f"{_f(c_ok, c41, cg):<16} {_f(d_ok, d41, dg):<16}")

    # ── controllo che deve poter fallire ────────────────────────────────
    veri_caduti = [r[0] for r in righe_out if not r[1]]
    print(f"\n  CONTROLLO: claim VERI ammessi: "
          f"{len(righe_out) - len(veri_caduti)}/{len(righe_out)}")
    if veri_caduti:
        print(f"     CONTROLLO CADUTO: un VERO e' quarantinato ({veri_caduti}) ⇒")
        print("     misuro un gate rotto, non un buco. NESSUN VERDETTO.")
        return 1

    b_fermate = sum(1 for r in righe_out if not r[2])
    c_fermate = sum(1 for r in righe_out if not r[4])
    b_l41 = sum(1 for r in righe_out if r[3])
    c_l41 = sum(1 for r in righe_out if r[5])
    n = len(righe_out)
    print("\n  ══ LE DUE POPOLAZIONI — stessa contraddizione, nome diverso ══")
    print(f"     B  STESSA parola  fermate {b_fermate}/{n}   L4.1 parla {b_l41}/{n}")
    print(f"     C  SINONIMO       fermate {c_fermate}/{n}   L4.1 parla {c_l41}/{n}")

    d_fermate = sum(1 for r in righe_out if not r[6])
    d_l41 = sum(1 for r in righe_out if r[7])
    print(f"     D  VERO col SINONIMO  FERMATE {d_fermate}/{n}"
          f"   L4.1 parla {d_l41}/{n}   <- i FALSI POSITIVI")

    print("\n  ══ VERDETTO ══")
    if d_fermate:
        print(f"     🔴 LA FRAMMENTAZIONE PRODUCE FALSI POSITIVI: {d_fermate} claim")
        print("     VERI su " + str(n) + " sono fermati solo perche' l'unita' e'")
        print("     scritta con un SINONIMO di quella della fonte. Stesso valore,")
        print("     stessa cosa detta, parola diversa ⇒ la coppia (unita', valore)")
        print("     non combacia e L4.1 li segnala.")
        print("     ⇒ e' il difetto REALE della frammentazione, ed e' l'OPPOSTO di")
        print("       quello che avevo previsto: non un falso negativo, un falso")
        print("       POSITIVO su un claim vero.")
    else:
        print("     Nessun falso positivo dal sinonimo: le due forme sono trattate")
        print("     come equivalenti a valle, nonostante l'estrattore le separi.")

    print("\n  ══ E LA MIA PREDIZIONE ORIGINALE ══")
    if diverse == 0:
        print("     NESSUN VERDETTO SUL MECCANISMO: l'estrattore da' la STESSA")
        print("     unita' a entrambe le forme, quindi la frammentazione che")
        print("     ipotizzavo non c'e' su questi casi.")
    elif c_fermate < b_fermate:
        print("     IPOTESI RETTA: la STESSA contraddizione viene fermata quando")
        print("     l'unita' e' scritta con la parola della fonte e passa quando e'")
        print("     scritta con un SINONIMO. ⇒ la frammentazione delle unita'")
        print("     NASCONDE una contraddizione vera: e' un FALSO NEGATIVO, il")
        print("     difetto OPPOSTO a quello che il modulo dichiara.")
    elif c_fermate == b_fermate:
        print("     IPOTESI FALSIFICATA: il sinonimo viene fermato quanto la parola")
        print("     originale ⇒ l'unita' non frammenta il confronto, e l'ipotesi")
        print("     che ho pubblicato in fafd1475 VA RITIRATA.")
    else:
        print("     RISULTATO INVERSO, da spiegare: il sinonimo e' fermato PIU'")
        print("     spesso della parola originale.")

    print("\n  ⚠️ LIMITI: quattro coppie scelte da me, italiano, fonti CORTE (una")
    print("     frase). Il verdetto complessivo dipende anche dal GIUDICE, non")
    print("     solo da L4.1: riporto entrambi. E i sinonimi sono i miei — un")
    print("     elenco piu' largo lo scriverebbe meglio chi non ha in mente")
    print("     l'ipotesi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
