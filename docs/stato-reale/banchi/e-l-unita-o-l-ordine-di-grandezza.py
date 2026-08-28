# -*- coding: utf-8 -*-
"""IL CANDIDATO DI ws3, con la variabile che il suo disegno non separava.

@ws3 il 28/08 ha offerto un candidato, dichiarandolo NON provato (n=2 per
cella): quale UNITA' DI MISURA e' fragile allo scambio di attribuzione.
Percentuali 2/2 entrano · date 2/2 · dosaggi 3/6 · importi in euro 0/2.

Ma le due che stanno agli estremi sono confuse con un'altra variabile: gli
importi che si fermano sono 148000 e 22000 (cinque e sei cifre); le percentuali
che entrano sono 2 e 5 (una cifra). Le due spiegazioni predicono lo stesso
esito su quei dati.

Le separa un incrocio: la STESSA unita' a due grandezze, e la stessa grandezza
con unita' diverse.

  unita'        grandezza piccola        grandezza grande
  percentuale   2% e 5%                  35% e 65%
  euro          16 e 50                  148000 e 22000
  giorni        8 e 45                   (non applicabile)
  date          12 marzo / 30 aprile     (non applicabile)

  se conta l'UNITA'      -> euro piccoli e euro grandi si comportano UGUALE
  se conta la GRANDEZZA  -> euro piccoli si comportano come le percentuali piccole

Ogni coppia viene scambiata in ENTRAMBI i versi, come nel banco del 27/08:
dodici celle, non due.

CONTROLLO CHE DEVE POTER FALLIRE: ogni cifra usata deve stare nella fonte, ogni
numero della fonte dev'essere UNIVOCO (un valore ripetuto non si sa a chi il
giudice lo attribuisca), e i claim VERI devono essere ammessi.

Fonte costruita nella forma del dominio, e dichiarata.

    python docs/stato-reale/banchi/e-l-unita-o-l-ordine-di-grandezza.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FONTE = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 6 - L'acconto alla stipula e' pari al 34% del corrispettivo. "
    "Art. 7 - Il saldo alla consegna e' pari al 61% del corrispettivo. "
    "Art. 9 - I diritti di segreteria ammontano a 16 euro. "
    "Art. 11 - Le spese di registrazione ammontano a 50 euro. "
    "Art. 13 - L'importo contrattuale e' di 148000 euro. "
    "Art. 14 - La cauzione definitiva e' pari a 22000 euro. "
    "Art. 17 - Il preavviso per il recesso e' di 8 giorni. "
    "Art. 19 - Il termine per la contestazione dei vizi e' di 45 giorni. "
    "Art. 21 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 23 - Il collaudo finale e' fissato al 30 aprile 2027."
)

# (unita, grandezza, claim verso A, claim verso B, cifre che devono stare nella fonte)
COPPIE = [
    ("percentuale", "piccola",
     "La penale per il ritardo e' pari al 7% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale.",
     ("7%", "2%")),
    ("percentuale", "grande",
     "L'acconto alla stipula e' pari al 61% del corrispettivo.",
     "Il saldo alla consegna e' pari al 34% del corrispettivo.",
     ("61%", "34%")),
    ("euro", "piccola",
     "I diritti di segreteria ammontano a 50 euro.",
     "Le spese di registrazione ammontano a 16 euro.",
     ("50 euro", "16 euro")),
    ("euro", "grande",
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro.",
     ("148000", "22000")),
    ("giorni", "piccola",
     "Il preavviso per il recesso e' di 45 giorni.",
     "Il termine per la contestazione dei vizi e' di 8 giorni.",
     ("45 giorni", "8 giorni")),
    ("data", "n/a",
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il collaudo finale e' fissato al 12 marzo 2027.",
     ("30 aprile", "12 marzo")),
]

VERI = [
    "La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
    "L'importo contrattuale e' di 148000 euro.",
    "I diritti di segreteria ammontano a 16 euro.",
]


def main() -> int:
    for u, g, _a, _b, cifre in COPPIE:
        for c in cifre:
            if c not in FONTE:
                print(f"CONTROLLO CADUTO: {c!r} non e' nella fonte ({u}/{g})")
                return 1
    # Univocita' dei VALORI SCAMBIATI, non di ogni numero della fonte: al primo
    # giro il controllo e' caduto su «2027», che e' l'anno di entrambe le date ed
    # e' ripetuto legittimamente. Il criterio giusto guarda i valori che uso, non
    # il testo intero — un controllo troppo largo ferma anche cio' che va bene.
    numeri = re.findall(r"\d+", FONTE)
    valori = [c for _u, _g, _a, _b, cifre in COPPIE for c in cifre]
    doppi = sorted({v for v in valori if FONTE.count(v) > 1})
    if doppi:
        print(f"CONTROLLO CADUTO: valori scambiati non univoci nella fonte: {doppi}")
        return 1
    print(f"  CONTROLLO retto: {len(valori)} valori scambiati, ognuno una volta sola")
    print(f"  (nella fonte ci sono {len(numeri)} numeri in tutto, anni e articoli compresi)")
    print(f"  fonte: {len(FONTE)} caratteri")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "unita.db"))

    for i, prop in enumerate(VERI):
        r = mem.add(prop, topic=f"un/vero/{i}", source=FONTE, validate="full")
        if str(r.get("status")) == "quarantined":
            g = float(r.get("grounding_score") or -1)
            print(f"CONTROLLO CADUTO: il vero {prop!r} e' quarantinato (ground {g:.1f})")
            return 1
    print(f"  CONTROLLO retto: i {len(VERI)} claim VERI sono ammessi\n")

    print(f"  {'unita':<12} {'grandezza':<10} {'verso A':>15}   {'verso B':>15}")
    print("  " + "-" * 62)
    esiti = []
    for i, (u, g, a, b, _c) in enumerate(COPPIE):
        out = []
        for j, prop in enumerate((a, b)):
            ric = mem.add(prop, topic=f"un/{i}/{j}", source=FONTE, validate="full")
            sc = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            out.append((st, sc))
        (sa, ga), (sb, gb) = out
        ea = "ENTRA" if sa != "quarantined" else "ferma"
        eb = "ENTRA" if sb != "quarantined" else "ferma"
        esiti.append((u, g, ea, ga, eb, gb))
        print(f"  {u:<12} {g:<10} {ea:>8} {ga:6.1f}   {eb:>8} {gb:6.1f}")

    print("\n  -- PER UNITA")
    for u in ("percentuale", "euro", "giorni", "data"):
        righe = [e for e in esiti if e[0] == u]
        if not righe:
            continue
        n = sum(1 for e in righe for x in (e[2], e[4]) if x == "ENTRA")
        print(f"     {u:<12} {n} su {2 * len(righe)}")

    print("  -- PER ORDINE DI GRANDEZZA (solo le unita che ne hanno due)")
    for g in ("piccola", "grande"):
        righe = [e for e in esiti if e[1] == g]
        if not righe:
            continue
        n = sum(1 for e in righe for x in (e[2], e[4]) if x == "ENTRA")
        print(f"     {g:<12} {n} su {2 * len(righe)}")

    print("\n  -- IL DISCRIMINANTE: euro piccoli contro euro grandi")
    ep = [e for e in esiti if e[0] == "euro" and e[1] == "piccola"]
    eg = [e for e in esiti if e[0] == "euro" and e[1] == "grande"]
    pp = [e for e in esiti if e[0] == "percentuale" and e[1] == "piccola"]
    if ep and eg and pp:
        def riga(e):
            return f"{e[2]} {e[3]:.1f} / {e[4]} {e[5]:.1f}"
        print(f"     euro piccoli      : {riga(ep[0])}")
        print(f"     euro grandi       : {riga(eg[0])}")
        print(f"     percentuali picc. : {riga(pp[0])}")
        ep_entra = "ENTRA" in (ep[0][2], ep[0][4])
        eg_entra = "ENTRA" in (eg[0][2], eg[0][4])
        pp_entra = "ENTRA" in (pp[0][2], pp[0][4])
        if ep_entra == eg_entra:
            print("     => euro piccoli e grandi si comportano UGUALE => conta l'UNITA")
        elif ep_entra == pp_entra:
            print("     => euro piccoli come le percentuali piccole => conta la GRANDEZZA,")
            print("        e il candidato di ws3 cambia bersaglio.")
        else:
            print("     => ne l'uno ne l'altro in modo netto: guarda i numeri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
