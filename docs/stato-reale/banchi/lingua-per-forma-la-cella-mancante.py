"""LINGUA x FORMA — la cella che manca a due banchi, e nessuno dei due la copre.

Due misure di stasera si toccano senza incrociarsi:

  · un'altra istanza: **`L4.2` avvisa SOLO sulla fonte TABELLARE**, e dentro la
    tabella conta **l'ORDINE etichetta/numero** (`pallet 480` parla, `480 pallet`
    tace). Tutte le sue celle hanno **claim e fonte nella STESSA lingua**.
  · `W7-51` (mia): sulla **PROSA**, `L4.2` avvisa su **8 coppie MISTE su 8**
    (claim in una lingua, fonte nell'altra) contro **3 concordi su 8**. Tutte le
    mie celle hanno la fonte in **PROSA**.

⇒ **La cella mancante e' `fonte TABELLARE + lingue DIVERSE`**, e non e' un
dettaglio: se sulla prosa la lingua mista porta l'avviso dal 37,5% al 100%, e
sulla tabellare l'avviso c'e' gia' per la forma, allora **le due leve o si
sommano (e non si distinguono piu') o una domina l'altra**.

ATTESA DICHIARATA PRIMA DI ESEGUIRE (e le due uscite sono diverse):
  · **SATURA**: sulla tabellare l'avviso c'e' in tutte e quattro le celle
    (concordi e miste) ⇒ **la forma DOMINA la lingua**, e il mio 8-su-8 della
    prosa era la lingua che faceva da sola cio' che qui fa la forma.
  · **NON satura**: sulla tabellare CONCORDE avvisa e sulla MISTA no (o
    viceversa) ⇒ le due leve interagiscono, e il quadro e' piu' complicato di
    come lo stiamo raccontando entrambi.

  E sul PUNTEGGIO: `W7-51` ha misurato che il moat attraversa la lingua sulla
  prosa (caduta **0,1 punti**). Qui guardo se regge anche sulla **tabellare**.

CONTROLLI CHE POSSONO FALLIRE:
 (1) il claim VERO sulla fonte concorde deve PASSARE: se no, non sto misurando
     la lingua ne' la forma, sto misurando altro.
 (2) il claim FALSO deve essere fermato in TUTTE e quattro: se in qualcuna passa
     e' un VARCO, e va detto prima di ogni conteggio sugli avvisi.
 (3) i numeri del claim vero devono comparire in ENTRAMBE le fonti.

    python -u docs/stato-reale/banchi/lingua-per-forma-la-cella-mancante.py
"""

from __future__ import annotations

import re
import sys

TAB_IT = (
    "Verbale di magazzino - Verona\n"
    "voce            quantita\n"
    "pallet          480\n"
    "bancali          75\n"
    "colli           312\n"
    "data          12 marzo\n"
)
TAB_EN = (
    "Warehouse report - Verona\n"
    "item            quantity\n"
    "pallets         480\n"
    "crates           75\n"
    "parcels         312\n"
    "date          March 12\n"
)
CLAIM = {
    ("it", "vero"): "Il magazzino di Verona contiene 480 pallet.",
    ("en", "vero"): "The Verona warehouse holds 480 pallets.",
    ("it", "falso"): "Il magazzino di Verona contiene 940 pallet.",
    ("en", "falso"): "The Verona warehouse holds 940 pallets.",
}
FONTI = {"it": TAB_IT, "en": TAB_EN}
NUM = re.compile(r"\d+")


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    print("  -- CONTROLLO (3): i numeri dei VERI sono in entrambe le fonti?")
    fuori = [(lg, n) for (lg, t), c in CLAIM.items() if t == "vero"
             for n in NUM.findall(c) if any(n not in f for f in FONTI.values())]
    if fuori:
        print(f"     CADUTO - {fuori}: misurerei L4.1, non la forma.")
        return 1
    print("     retto")

    print("\n  == FONTE TABELLARE, 2 lingue del claim x 2 della fonte x vero/falso")
    print(f"     {'claim':>6} {'fonte':>6} {'tipo':>6} {'score':>8}  {'esito':<11} layer")
    esiti = {}
    for tipo in ("vero", "falso"):
        for lc in ("it", "en"):
            for lf in ("it", "en"):
                g = run_validation_gate(
                    proposition=CLAIM[(lc, tipo)], verified_by=[], topic=None,
                    agent=None, source=FONTI[lf], ground_write=True)
                sc = getattr(g, "grounding_score", None)
                az = getattr(g, "action", None)
                ws = getattr(g, "warnings", None) or []
                lay = ",".join(sorted({str((w or {}).get("layer") or "?")
                                       for w in ws})) or "-"
                esiti[(lc, lf, tipo)] = (sc, az, lay)
                s = "n/d" if sc is None else f"{float(sc):.1f}"
                marca = "  " if lc == lf else " *"
                print(f"    {marca}{lc:>5} {lf:>6} {tipo:>6} {s:>8}  {str(az):<11} {lay}")

    def has42(k):
        return "4.2" in esiti[k][2]

    conc_v = [("it", "it", "vero"), ("en", "en", "vero")]
    mist_v = [("it", "en", "vero"), ("en", "it", "vero")]
    n_conc = sum(1 for k in conc_v if has42(k))
    n_mist = sum(1 for k in mist_v if has42(k))

    print("\n  -- CONTROLLO (1): il VERO concorde passa?")
    passa = all(str(esiti[k][1]) == "persist" for k in conc_v)
    print(f"     {'retto' if passa else 'CADUTO'} - esiti "
          f"{[str(esiti[k][1]) for k in conc_v]}")
    if not passa:
        print("     Non sto misurando lingua ne' forma: mi fermo.")
        return 1

    print("\n  -- CONTROLLO (2): il FALSO e' fermato in tutte e quattro?")
    falsi = [(lc, lf) for lc in ("it", "en") for lf in ("it", "en")
             if str(esiti[(lc, lf, "falso")][1]) == "persist"]
    if falsi:
        print(f"     🚨 VARCO: il falso PASSA in {falsi} — va detto prima di")
        print("     qualunque conteggio sugli avvisi.")
    else:
        print("     retto - fermato 4 su 4")

    print("\n  == LA RISPOSTA: `L4.2` sulla tabellare SATURA?")
    print(f"     VERI concordi con `L4.2`: {n_conc} su 2")
    print(f"     VERI MISTE   con `L4.2`: {n_mist} su 2")
    if n_conc == 2 and n_mist == 2:
        print("     🔑 SATURA: la FORMA domina la lingua. L'avviso c'e' comunque,")
        print("     quindi sulla tabellare la lingua non aggiunge niente — e il")
        print("     mio 8-su-8 della PROSA era la lingua che faceva da sola cio'")
        print("     che qui fa la forma.")
    elif n_conc == n_mist:
        print("     ⇒ Le due celle si comportano UGUALE: la lingua non muove")
        print("     l'avviso sulla tabellare, qualunque sia il livello.")
    else:
        print("     ⇒ NON satura: le due leve interagiscono, e il quadro e' piu'")
        print("     complicato di come lo raccontiamo. Il numero e' questo, e non")
        print("     lo forzo in nessuna direzione.")

    cv = [float(esiti[k][0] or -1) for k in conc_v]
    mv = [float(esiti[k][0] or -1) for k in mist_v]
    print(f"\n  == E IL PUNTEGGIO, come in W7-51 ma sulla tabellare")
    print(f"     veri concordi {cv}   veri MISTI {mv}")
    print(f"     caduta massima {min(cv) - min(mv):+.1f} punti")
    print("     (sulla PROSA, in W7-51, la caduta era 0,1)")

    print("\n  ⚠️ COSA NON DICE: una tabella, una coppia di lingue, un claim per")
    print("  cella. E la traduzione della tabella cambia ANCHE le etichette")
    print("  (`pallet`->`pallets`): lingua e lessico si muovono insieme, come in")
    print("  ogni traduzione vera — separarli richiederebbe una tabella con le")
    print("  etichette identiche nelle due lingue, che non e' una tabella vera.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
