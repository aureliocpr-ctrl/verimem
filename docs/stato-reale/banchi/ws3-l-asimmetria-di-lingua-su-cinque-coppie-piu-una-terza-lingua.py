"""L'asimmetria di lingua e' una proprieta' o era una coppia di frasi fortunata?

Alle 01:40 (`90fc7fa8`) ho misurato che **lo stesso scambio di soggetto** prende
**100,0 in italiano e 5,3 in inglese**, e ne ho tratto una frase pesante: *la
protezione del gate dipende dalla lingua, e la lingua in cui scriviamo di piu'
e' quella debole*. Quella frase poggia su **UNA coppia di frasi**. Prima che
entri in un contratto di uscita va **allargata o ristretta**.

CINQUE COPPIE, non una: domini diversi, soggetti diversi, tipi di valore
diversi (interi, decimali, percentuali, durate, denaro). Se lo scarto comparisse
in **una sola** coppia sarebbe **un caso**, non una proprieta'.

E UNA TERZA LINGUA (spagnolo), perche' «italiano» e «non-inglese» sono **due
tesi molto diverse** e i miei dati finora non le separano.

LA PREDIZIONE, scritta prima di eseguire:
    lo scarto (IT alto, EN basso) compare in **almeno 4 coppie su 5**, e lo
    spagnolo si comporta **come l'italiano** (⇒ la tesi giusta e'
    «non-inglese», non «italiano»).

CONDIZIONE DI FALSIFICAZIONE:
    · se lo scarto compare in **≤2 coppie su 5** ⇒ il reperto delle 01:40 era
      **una coppia fortunata** e va **RITIRATO**;
    · se lo spagnolo si comporta come l'**inglese** ⇒ la tesi e' «italiano»,
      non «non-inglese», e va detta cosi'.

CONTROLLO CHE DEVE POTER FALLIRE, per OGNI cella: il claim **vero** deve stare
alto e il valore **assente** basso. Una coppia in cui il vero non passa non
misura la cecita': misura una fonte scritta male. Le celle che non passano il
controllo vengono **ESCLUSE e dichiarate**, non silenziosamente contate.

🔴 **ESITO: PREDIZIONE FALSIFICATA. IL REPERTO DELLE 01:40 E' RITIRATO.**

    coppia               vero(it)  SCAMBIO(it)   vero(en)  SCAMBIO(en)
    workflow/interi          99.4         73.0       99.7          2.0
    citta/abitanti           99.9          0.6       99.7          0.9
    server/percentuali      100.0          0.9       99.9          0.9
    corsi/durate             99.9          2.4      100.0          1.6
    fornitori/denaro         99.9         18.0       99.9         61.1
    SPAGNOLO workflow        99.6          6.8   ·   citta 99.8    1.1

**Controlli retti su 5 coppie su 5** (vero alto, assente basso ovunque), quindi
il nullo e' leggibile. E lo scarto «passa in italiano, non in inglese» compare
in **1 coppia su 5** — **l'unica** e' proprio quella su cui avevo costruito il
reperto. In `fornitori/denaro` la direzione e' **OPPOSTA** (18,0 in italiano
contro 61,1 in inglese).

⇒ **NON esiste un'asimmetria di lingua: esiste VARIANZA FRA CASI.** Alcuni
scambi il giudice li prende benissimo (0,6) e altri no (73,0), e **la lingua non
spiega quali**. La terza lingua conferma la demolizione: lo spagnolo si comporta
come l'**inglese** (6,8 e 1,1), quindi cade anche il ripiego «non-inglese».

🔑 **E CADE ANCHE IL TITOLO DELLE 01:34**: su queste cinque fonti — piu' corte e
piu' regolari — lo scambio viene **preso** quasi sempre. Il «il giudice non vede
l'attribuzione» valeva su **quella** fonte, non sul giudice.

💡 **L'IPOTESI CHE RESTA, e non e' misurata**: l'unica coppia che mostra lo
scarto usa come soggetti `ci` e `security`. **`ci` in italiano e' un pronome
clitico** («ci sono», «ci ha») — un token che in inglese e' un identificatore e
in italiano e' una parola vuota. Se il difetto fosse questo, non sarebbe «la
lingua»: sarebbe **un soggetto che nella lingua della fonte non si comporta da
soggetto**. ⚠️ **NON misurato**: e' la prossima domanda, non una conclusione.

REGIME: store TEMPORANEO, cross-encoder locale su disco (nessuna API esterna).
Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-l-asimmetria-di-lingua-su-cinque-coppie-piu-una-terza-lingua.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: (nome, fonte, claim VERO, claim SCAMBIATO, claim ASSENTE)
COPPIE: list[tuple[str, dict[str, tuple[str, str, str, str]]]] = [
    ("workflow/interi", {
        "it": (
            "Il workflow ci ha avuto 50 run, di cui 0 cancellati. Il workflow "
            "security ha avuto 60 run, di cui 59 cancellati.",
            "Il workflow security ha 59 run cancellati.",
            "Il workflow ci ha 59 run cancellati.",
            "Il workflow ci ha 777 run cancellati."),
        "en": (
            "The ci workflow had 50 runs, 0 of them cancelled. The security "
            "workflow had 60 runs, 59 of them cancelled.",
            "The security workflow had 59 cancelled runs.",
            "The ci workflow had 59 cancelled runs.",
            "The ci workflow had 777 cancelled runs."),
    }),
    ("citta/abitanti", {
        "it": (
            "Bologna conta 390 mila abitanti. Firenze conta 360 mila "
            "abitanti. Genova conta 560 mila abitanti.",
            "Genova conta 560 mila abitanti.",
            "Firenze conta 560 mila abitanti.",
            "Firenze conta 902 mila abitanti."),
        "en": (
            "Bologna has 390 thousand inhabitants. Florence has 360 thousand "
            "inhabitants. Genoa has 560 thousand inhabitants.",
            "Genoa has 560 thousand inhabitants.",
            "Florence has 560 thousand inhabitants.",
            "Florence has 902 thousand inhabitants."),
    }),
    ("server/percentuali", {
        "it": (
            "Il server alfa ha una disponibilita' del 99,9 per cento. Il "
            "server beta ha una disponibilita' del 97,2 per cento.",
            "Il server beta ha una disponibilita' del 97,2 per cento.",
            "Il server alfa ha una disponibilita' del 97,2 per cento.",
            "Il server alfa ha una disponibilita' del 41,8 per cento."),
        "en": (
            "The alfa server has an availability of 99.9 per cent. The beta "
            "server has an availability of 97.2 per cent.",
            "The beta server has an availability of 97.2 per cent.",
            "The alfa server has an availability of 97.2 per cent.",
            "The alfa server has an availability of 41.8 per cent."),
    }),
    ("corsi/durate", {
        "it": (
            "Il corso di base dura 12 ore. Il corso avanzato dura 30 ore. Il "
            "corso di aggiornamento dura 4 ore.",
            "Il corso avanzato dura 30 ore.",
            "Il corso di base dura 30 ore.",
            "Il corso di base dura 88 ore."),
        "en": (
            "The basic course lasts 12 hours. The advanced course lasts 30 "
            "hours. The refresher course lasts 4 hours.",
            "The advanced course lasts 30 hours.",
            "The basic course lasts 30 hours.",
            "The basic course lasts 88 hours."),
    }),
    ("fornitori/denaro", {
        "it": (
            "Il fornitore Rossi ha fatturato 12500 euro. Il fornitore Bianchi "
            "ha fatturato 8400 euro. Il fornitore Verdi ha fatturato 3100 euro.",
            "Il fornitore Bianchi ha fatturato 8400 euro.",
            "Il fornitore Rossi ha fatturato 8400 euro.",
            "Il fornitore Rossi ha fatturato 6700 euro."),
        "en": (
            "Supplier Rossi invoiced 12500 euros. Supplier Bianchi invoiced "
            "8400 euros. Supplier Verdi invoiced 3100 euros.",
            "Supplier Bianchi invoiced 8400 euros.",
            "Supplier Rossi invoiced 8400 euros.",
            "Supplier Rossi invoiced 6700 euros."),
    }),
]

#: la TERZA lingua, su due coppie: separa «italiano» da «non-inglese»
SPAGNOLO = [
    ("workflow/interi", (
        "El workflow ci tuvo 50 ejecuciones, 0 de ellas canceladas. El "
        "workflow security tuvo 60 ejecuciones, 59 de ellas canceladas.",
        "El workflow security tuvo 59 ejecuciones canceladas.",
        "El workflow ci tuvo 59 ejecuciones canceladas.",
        "El workflow ci tuvo 777 ejecuciones canceladas.")),
    ("citta/abitanti", (
        "Bolonia tiene 390 mil habitantes. Florencia tiene 360 mil "
        "habitantes. Genova tiene 560 mil habitantes.",
        "Genova tiene 560 mil habitantes.",
        "Florencia tiene 560 mil habitantes.",
        "Florencia tiene 902 mil habitantes.")),
]

SOGLIA = 50.0


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print("  giudice: cross-encoder locale su disco (nessuna API esterna)")
    mem = Memory(str(tmp / "lingue.db"))
    n = 0

    def s(claim: str, fonte: str) -> float:
        nonlocal n
        n += 1
        v = mem.add(claim, topic=f"lg/{n}", source=fonte,
                    validate="full").get("grounding_score")
        return -1.0 if v is None else float(v)

    def blocco(fonte, vero, scambio, assente):
        return s(vero, fonte), s(scambio, fonte), s(assente, fonte)

    print(f"\n  {'coppia':<20} {'lingua':<3} {'vero':>7} {'SCAMBIO':>8} "
          f"{'assente':>8}  controllo")
    print("  " + "-" * 66)
    scarti = 0
    valide = 0
    escluse: list[str] = []
    for nome, per_lingua in COPPIE:
        riga: dict[str, tuple[float, float, float]] = {}
        for lg in ("it", "en"):
            fonte, vero, scambio, assente = per_lingua[lg]
            v, sc, a = blocco(fonte, vero, scambio, assente)
            riga[lg] = (v, sc, a)
            ok = v > SOGLIA and a < SOGLIA
            print(f"  {nome:<20} {lg:<3} {v:>7.1f} {sc:>8.1f} {a:>8.1f}"
                  f"  {'ok' if ok else 'ESCLUSA'}")
        ok_it = riga["it"][0] > SOGLIA and riga["it"][2] < SOGLIA
        ok_en = riga["en"][0] > SOGLIA and riga["en"][2] < SOGLIA
        if not (ok_it and ok_en):
            escluse.append(nome)
            continue
        valide += 1
        # lo SCARTO che cerco: lo scambio passa in italiano e NON in inglese
        if riga["it"][1] > SOGLIA and riga["en"][1] < SOGLIA:
            scarti += 1

    print(f"\n  [1] CONTROLLI: coppie valide {valide}/{len(COPPIE)}"
          + (f"  ESCLUSE: {', '.join(escluse)}" if escluse else ""))
    if valide < 3:
        print("      CONTROLLO CADUTO: meno di 3 coppie superano vero-alto e")
        print("      assente-basso ⇒ non misuro la cecita', misuro fonti")
        print("      scritte male. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     coppie in cui lo scambio PASSA in italiano e NON in inglese: "
          f"{scarti}/{valide}")
    if scarti >= 4:
        print("     PREDIZIONE RETTA: l'asimmetria e' una PROPRIETA', non una")
        print("     coppia fortunata.")
    elif scarti <= 2:
        print("     PREDIZIONE FALSIFICATA: il reperto delle 01:40 poggiava su")
        print("     una coppia FORTUNATA ⇒ va RITIRATO come proprieta' generale.")
    else:
        print("     ZONA GRIGIA: 3 su 5. Non si consegna ne' come proprieta' ne'")
        print("     come caso: serve una popolazione piu' larga.")

    # ── LA TERZA LINGUA: «italiano» o «non-inglese»? ─────────────────────
    print("\n  ── TERZA LINGUA (spagnolo): separa «italiano» da «non-inglese»")
    es_scarti = 0
    es_valide = 0
    for nome, (fonte, vero, scambio, assente) in SPAGNOLO:
        v, sc, a = blocco(fonte, vero, scambio, assente)
        ok = v > SOGLIA and a < SOGLIA
        print(f"  {nome:<20} es  {v:>7.1f} {sc:>8.1f} {a:>8.1f}"
              f"  {'ok' if ok else 'ESCLUSA'}")
        if ok:
            es_valide += 1
            if sc > SOGLIA:
                es_scarti += 1
    if es_valide == 0:
        print("     nessuna cella spagnola valida ⇒ la terza lingua NON risponde.")
    elif es_scarti == es_valide:
        print("     lo spagnolo si comporta come l'ITALIANO ⇒ la tesi giusta e'")
        print("     «NON-INGLESE», non «italiano».")
    elif es_scarti == 0:
        print("     lo spagnolo si comporta come l'INGLESE ⇒ la tesi e'")
        print("     «ITALIANO», e va detta cosi'.")
    else:
        print(f"     spagnolo misto ({es_scarti}/{es_valide}): non separa le due")
        print("     tesi. Resta aperto.")

    print(f"\n  ⚠️ LIMITI: {n} celle, un giudice (cross-encoder locale), fonti")
    print("     corte e costruite. NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
