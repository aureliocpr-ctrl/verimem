# -*- coding: utf-8 -*-
"""LA PREDIZIONE DI ws3, MESSA ALLA PROVA IN SETTE SCRITTURE.

ws3 il 27/08 alle 20:05 ha pubblicato una lettura di `anti_confab_gate.py:2455`
e, cosa piu' rara, la PREDIZIONE FALSIFICABILE che ne discende:

    «quella classe non deve mostrare nessun gradiente per scrittura — piatta in
     tutte le lingue, perche' il layer non riceve niente da cercare.
     Se la misuri in sei scritture e trovi un gradiente, la mia lettura e'
     sbagliata e va detto.»

La classe e' la VAGHEZZA MINIMIZZANTE: la fonte dice «30 su 40», il claim dice
«pochi». Nessuna cifra NEL CLAIM ⇒ `valori_non_nella_fonte(proposition, source)`
torna vuoto per costruzione ⇒ L4.1 muto.

QUELLO CHE IL BANCO PUO' DIRE, E QUELLO CHE NON PUO'
----------------------------------------------------
«L4.1 e' muto» e «l'esito e' piatto» NON sono la stessa affermazione, ed e' qui
che la predizione puo' rompersi senza che la lettura del codice sia sbagliata:
il verdetto finale non lo emette L4.1 da solo. Se un gradiente compare, la
domanda successiva e' DA QUALE layer viene — e la risposta la da' la ricevuta,
non io. Percio' il banco non stampa solo ammesso/quarantinato: stampa il layer
che ha deciso e il grounding, che e' un numero continuo e puo' avere un
gradiente anche dove il verdetto e' identico in tutte e sette le celle.

IL CONTROLLO CHE PUO' FALLIRE (due, in realta')
-----------------------------------------------
① Ogni cella porta un GEMELLO con la cifra nel claim («solo 3 pezzi»), che in
   ogni scrittura deve essere fermato. Se il gemello non scatta, non ho
   misurato l'assenza di un gradiente: ho misurato un banco rotto.
② Un controllo di INTEGRITA' del testo: ogni cella dichiara il blocco Unicode
   che si aspetta e le due cifre della fonte. Sette lingue passate attraverso
   una heredoc e un tool sono sette occasioni di mojibake, e un testo corrotto
   verrebbe letto come «quella scrittura si comporta diversamente».

SI ESEGUE FUORI DA pytest: sotto pytest l'embedder e' uno stub su SHA-256
(`conftest._stub_embedding_model`), e il grounding qui e' proprio la grandezza
in esame. `HIPPO_DATA_DIR` non serve: `Memory(path)` scrive dove gli si dice.

    python docs/stato-reale/banchi/la-vaghezza-minimizzante-ha-un-gradiente-per-scrittura.py

Esce 1 se un controllo cade (banco rotto), 0 altrimenti — il verdetto sulla
predizione lo stampa, non lo impone: non e' un presidio, e' una misura.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

# (nome, blocco unicode atteso, fonte, claim VAGO minimizzante, gemello CON cifra)
CASI = [
    (
        "latina-IT",
        (0x0041, 0x007A),
        "Su 40 pezzi controllati, 30 sono risultati difformi.",
        "Pochi pezzi sono risultati difformi.",
        "Solo 3 pezzi sono risultati difformi.",
    ),
    (
        "latina-EN",
        (0x0041, 0x007A),
        "Of 40 parts inspected, 30 were found non-conforming.",
        "Few parts were found non-conforming.",
        "Only 3 parts were found non-conforming.",
    ),
    (
        "han-ZH",
        (0x4E00, 0x9FFF),
        "在检查的 40 个零件中，有 30 个不合格。",
        "少数零件不合格。",
        "只有 3 个零件不合格。",
    ),
    (
        "kana-JA",
        (0x3040, 0x30FF),
        "検査した 40 個の部品のうち、30 個が不適合でした。",
        "少数の部品が不適合でした。",
        "3 個の部品だけが不適合でした。",
    ),
    (
        "hangul-KO",
        (0xAC00, 0xD7AF),
        "검사한 40개 부품 중 30개가 부적합했습니다.",
        "소수의 부품이 부적합했습니다.",
        "단 3개의 부품만 부적합했습니다.",
    ),
    (
        "araba-AR",
        (0x0600, 0x06FF),
        "من بين 40 قطعة تم فحصها، كانت 30 قطعة غير مطابقة.",
        "عدد قليل من القطع كان غير مطابق.",
        "3 قطع فقط كانت غير مطابقة.",
    ),
    (
        "devanagari-HI",
        (0x0900, 0x097F),
        "जाँची गई 40 वस्तुओं में से 30 अनुरूप नहीं थीं।",
        "कुछ ही वस्तुएँ अनुरूप नहीं थीं।",
        "केवल 3 वस्तुएँ अनुरूप नहीं थीं।",
    ),
]


# IL DISCRIMINANTE FRA DUE DIAGNOSI OPPOSTE (aggiunto dopo il primo giro, che
# ha dato al claim VAGO un grounding di 99.8 con `layers=[]`).
#   se il contrario ESPLICITO prende anche lui ~99 ⇒ il giudice non giudica
#     l'implicazione, misura la pertinenza, e «grounding» e' un nome che
#     promette piu' di quanto il numero valga;
#   se il contrario esplicito crolla ⇒ il giudice SA bocciare, e allora la
#     vaghezza non gli sfugge per debolezza: non la confronta affatto.
# Le due diagnosi chiedono cure opposte, e costano un giro solo.
CONTRARIO = {
    "latina-IT": "Tutti i pezzi sono risultati conformi.",
    "latina-EN": "All parts were found conforming.",
    "han-ZH": "所有零件均合格。",
    "kana-JA": "すべての部品が適合でした。",
    "hangul-KO": "모든 부품이 적합했습니다.",
    "araba-AR": "كانت جميع القطع مطابقة.",
    "devanagari-HI": "सभी वस्तुएँ अनुरूप थीं।",
}


def _integrita() -> list[str]:
    """Il testo e' arrivato intero? Un mojibake si legge come una differenza."""
    rotte = []
    for nome, (lo, hi), fonte, vago, gemello in CASI:
        if "�" in fonte + vago + gemello:
            rotte.append(f"{nome}: carattere di sostituzione U+FFFD nel testo")
        if not any(lo <= ord(c) <= hi for c in vago):
            rotte.append(f"{nome}: il claim vago non ha caratteri in U+{lo:04X}-U+{hi:04X}")
        cifre = set(re.findall(r"\d+", fonte))
        if not {"40", "30"} <= cifre:
            rotte.append(f"{nome}: la fonte non porta 40 e 30, ha {sorted(cifre)}")
        if "3" not in re.findall(r"\d+", gemello):
            rotte.append(f"{nome}: il gemello non porta la cifra 3")
    return rotte


def _layer(ric: dict) -> str:
    """Chi ha deciso. La ricevuta cambia forma: chiedo, non presumo."""
    for chiave in ("quarantined_by", "blocked_by", "layer", "gate_layer"):
        v = ric.get(chiave)
        if v:
            return f"{chiave}={v}"
    return "-"


def main() -> int:
    rotte = _integrita()
    if rotte:
        print("CONTROLLO ① INTEGRITA': CADUTO — il banco non misura niente")
        for r in rotte:
            print("   ", r)
        return 1
    print(f"CONTROLLO (1) integrita' del testo: 7 celle intere, 40/30 in tutte\n")

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    # DOVE STA IL CODICE CHE MISURO. Il primo tentativo ha rivelato che
    # `verimem.memory` si risolveva sotto Code\HippoAgent mentre
    # `verimem.__init__` veniva dal worktree: due alberi, e il referto
    # deve dire quale ha parlato.
    print(f"  codice sotto misura: {_client.__file__}")
    print()

    mem = Memory(str(Path(tempfile.mkdtemp()) / "scritture.db"))

    print("  cella           | claim VAGO «pochi»      | gemello CON cifra       | contrario ESPLICITO")
    print("  " + "-" * 94)
    vaghi, gemelli, contrari, chiavi_viste = [], [], [], None
    for nome, _blocco, fonte, vago, gemello in CASI:
        riga = []
        for prop in (vago, gemello, CONTRARIO[nome]):
            ric = mem.add(prop, topic=f"scritture/{nome}", source=fonte, validate="full")
            if chiavi_viste is None:
                chiavi_viste = sorted(ric.keys())
            g = ric.get("grounding_score")
            riga.append((str(ric.get("status")), g, _layer(ric)))
        vaghi.append((nome, *riga[0]))
        gemelli.append((nome, *riga[1]))
        contrari.append((nome, *riga[2]))
        (s1, g1, _l1), (s2, g2, _l2), (s3, g3, _l3) = riga
        f = lambda g: "None" if g is None else f"{float(g):.1f}"
        print(
            f"  {nome:<15} | {s1:<12} {f(g1):>6} | {s2:<12} {f(g2):>6} | {s3:<12} {f(g3):>6}"
        )

    print(f"\n  chiavi della ricevuta: {chiavi_viste}")

    # ── IL DISCRIMINANTE: il giudice sa bocciare una contraddizione esplicita?
    gc = [g for _n, _s, g, _l in contrari if g is not None]
    sc = {s for _n, s, _g, _l in contrari}
    print("\nIL DISCRIMINANTE — il contrario ESPLICITO sulla stessa fonte:")
    print(f"   verdetti {sorted(sc)}, grounding min {min(gc):.1f} max {max(gc):.1f}")
    gv = [g for _n, _s, g, _l in vaghi if g is not None]
    if gc and gv and max(gc) < min(gv) - 20:
        print("   ⇒ il giudice SA bocciare: crolla sull'esplicito e premia il vago.")
        print("      Non e' debolezza del giudizio: la quantita' vaga non viene")
        print("      confrontata con la fonte, e passa col punteggio dei fatti veri.")
    elif gc and gv and min(gc) > 50:
        print("   ⇒ anche il contrario esplicito e' alto: quel numero misura la")
        print("      PERTINENZA, non l'implicazione — e si chiama «grounding».")
    else:
        print("   ⇒ ne' l'uno ne' l'altro: guarda i numeri, non fidarti di questa riga.")

    # ── CONTROLLO ②: il gemello con la cifra deve essere fermato ovunque.
    passati = [n for n, s, _g, _l in gemelli if s == "admitted"]
    print("\nCONTROLLO (2) il gemello CON cifra e' fermato in tutte le scritture:")
    if passati:
        print(f"   CADUTO — passa in {passati}: il banco non prova l'assenza di un gradiente")
        return 1
    print(f"   retto — 7 su 7 fermati, layer: {sorted({l for _n, _s, _g, l in gemelli})}")

    # ── LA PREDIZIONE DI ws3.
    stati = {s for _n, s, _g, _l in vaghi}
    print("\nLA PREDIZIONE DI ws3 — «nessun gradiente per scrittura»:")
    print(f"   verdetti distinti sul claim vago: {sorted(stati)}")
    gs = [g for _n, _s, g, _l in vaghi if g is not None]
    if len(stati) > 1:
        print("   ⇒ FALSIFICATA sul VERDETTO: la stessa classe non ha lo stesso esito")
        for n, s, g, l in vaghi:
            print(f"        {n:<15} {s:<11} {l}")
    elif gs and (max(gs) - min(gs)) >= 5.0:
        print(f"   ⇒ verdetto piatto ({stati}), ma il GROUNDING no:")
        print(f"        min {min(gs):.1f}  max {max(gs):.1f}  ampiezza {max(gs) - min(gs):.1f}")
        print("        un numero continuo puo' avere un gradiente dove il verdetto non l'ha")
    else:
        amp = f"{max(gs) - min(gs):.1f}" if gs else "n/d"
        print(f"   ⇒ REGGE: verdetto unico {stati}, ampiezza del grounding {amp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
