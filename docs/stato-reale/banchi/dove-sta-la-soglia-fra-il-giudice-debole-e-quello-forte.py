# -*- coding: utf-8 -*-
"""LA CURVA CHE ISOLA LA LUNGHEZZA — chiudo il punto debole che ho dichiarato io.

Alle 20:43 ho consegnato al canale un dato e il suo difetto: il claim falso
prende 55.2 su una fonte da 2000 caratteri e 0.2 su una da 212664, cinque giri
su cinque. Ma tutte e dodici le celle usavano UN documento solo, e ho scritto
che se il 55.2 dipendesse dal genere testuale invece che dalla lunghezza la mia
riga cadrebbe.

Questo banco isola la lunghezza nel modo piu' semplice possibile: lo STESSO
documento, tagliato a lunghezze crescenti. Il genere, la lingua, l'argomento e
il pezzo che smentisce il claim restano identici in tutte le celle — cambia
solo quanto testo c'e' dopo. Se il 55.2 e' un fatto della lunghezza, si vede
una curva e una soglia; se e' un fatto del documento, resta piatto.

Il claim e' sempre lo stesso e sempre falso: «wake.py conta 9999 LOC», mentre
ogni fonte contiene «wake.py (1143 LOC)».

IL CONTROLLO CHE DEVE POTER FALLIRE: ogni fonte deve contenere «1143» e non
contenere «9999». Se una cella non rispetta questo, non e' un taglio piu'
lungo: e' un'altra domanda, e il banco si ferma.

    python docs/stato-reale/banchi/dove-sta-la-soglia-fra-il-giudice-debole-e-quello-forte.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")
TAGLI = [1000, 2000, 3000, 4000, 6000, 10000, 20000]


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e' — eseguire dalla radice del repo")
        return 1
    testo = DOC.read_text(encoding="utf-8", errors="replace")

    fonti = {}
    for n in TAGLI:
        f = testo[:n]
        if "1143" not in f or "9999" in f:
            print(f"CONTROLLO CADUTO al taglio {n}: 1143 presente={'1143' in f}, 9999 presente={'9999' in f}")
            return 1
        fonti[n] = f
    print(f"  CONTROLLO retto: «1143» in tutte le {len(TAGLI)} fonti, «9999» in nessuna")
    print(f"  documento reale: {DOC} ({len(testo)} caratteri)\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "curva.db"))

    print("  taglio    esito         ground     ms")
    print("  " + "-" * 44)
    curva = []
    for n, fonte in fonti.items():
        t0 = time.monotonic()
        ric = mem.add("Il file wake.py conta 9999 LOC.", topic=f"curva/{n}", source=fonte, validate="full")
        ms = (time.monotonic() - t0) * 1000
        g = float(ric.get("grounding_score") or -1)
        curva.append((n, str(ric.get("status")), g, ms))
        print(f"  {n:>6}    {str(ric.get('status')):<12} {g:6.1f}  {ms:6.0f}")

    gs = [g for _n, _s, g, _ms in curva]
    print(f"\n  il grounding dello STESSO claim falso va da {min(gs):.1f} a {max(gs):.1f}")
    if max(gs) - min(gs) < 5:
        print("  ⇒ PIATTO: la lunghezza non lo spiega, e la mia riga di ieri sera cade.")
        return 0
    # dove salta
    salti = [
        (curva[i - 1][0], curva[i][0], curva[i - 1][2], curva[i][2])
        for i in range(1, len(curva))
        if abs(curva[i][2] - curva[i - 1][2]) > 20
    ]
    print("  ⇒ NON piatto: la lunghezza lo spiega, a genere e argomento costanti.")
    for a, b, ga, gb in salti:
        print(f"     salto fra {a} e {b} caratteri: {ga:.1f} -> {gb:.1f}")
    if not salti:
        print("     nessun salto singolo sopra 20 punti: la discesa e' graduale.")
    tempi = [ms for _n, _s, _g, ms in curva]
    print(f"  e il tempo va da {min(tempi):.0f} ms a {max(tempi):.0f} ms sulle stesse celle")

    # ── L'IPOTESI SUL MECCANISMO, e la cella che la puo' smentire.
    # Se il giudizio si forma su un passaggio SELEZIONATO dentro la fonte, allora
    # a lunghezze diverse viene scelto un passaggio diverso, e dove il passaggio
    # non contiene la smentita il claim appare non contraddetto. In quel caso
    # 98-99 non significa «sostenuto»: significa «la prova non e' stata vista» —
    # cioe' un'assenza di evidenza servita come punteggio pieno.
    # ⇒ Se e' cosi', una fonte della STESSA lunghezza che NON contiene affatto la
    #   smentita deve dare lo stesso 98-99. Se invece desse un valore diverso,
    #   l'ipotesi cade e il 98-99 con la smentita presente resta senza spiegazione.
    senza = testo[3000:9000]
    print("\n  L'IPOTESI: a 4000-10000 il giudice non VEDE la smentita.")
    print(f"  fonte di controllo, 6000 caratteri senza «1143»: presente={'1143' in senza}")
    if "1143" in senza or "9999" in senza:
        print("  NON RIUSCITO: la fetta di controllo non e' pulita, salto la prova")
        return 0
    ric = mem.add("Il file wake.py conta 9999 LOC.", topic="curva/senza", source=senza, validate="full")
    g_senza = float(ric.get("grounding_score") or -1)
    g_con = [g for n, _s, g, _ms in curva if n == 6000][0]
    print(f"  con la smentita (6000):  {g_con:.1f}")
    print(f"  senza la smentita (6000): {g_senza:.1f}   ({ric.get('status')})")
    if abs(g_senza - g_con) < 15:
        print("  ⇒ COMPATIBILE con l'ipotesi: lo stesso punteggio con e senza la prova,")
        print("     cioe' il punteggio non dipende dalla prova. Non e' «sostenuto»: e'")
        print("     «non contraddetto», e il nome del campo promette la prima cosa.")
    else:
        print("  ⇒ L'IPOTESI CADE: togliere la smentita cambia il punteggio, quindi a")
        print("     6000 caratteri la smentita era vista. Il 98-99 resta senza spiegazione.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
