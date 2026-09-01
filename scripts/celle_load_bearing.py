"""Quali celle del registro REGGONO un documento che qualcuno legge?

PERCHE'. @lead-audit (direttiva 01/09): il criterio «verde = due firme» e'
soddisfatto sul 5% delle celle, e la proposta e' di ESIGERE le due firme solo
sulle celle LOAD-BEARING — quelle citate da report, vetrina e quadro-versione.
Serve il numero: **quante sono, e quante di quelle hanno gia' due firme.**

COSA CONTA COME «CITATA», dichiarato:
  · un riferimento `SIGLA-numero` (LANT-109, W2-30, W7-89…) che compare nel
    TESTO di uno dei documenti consumatori
  · NON conta l'occorrenza dentro il registro stesso (una cella che ne cita
    un'altra non la rende load-bearing per un lettore esterno)

⚠️ GUARDIE, tutte pagate il 30-31/08:
  · **uso vs menzione**: un documento che SPIEGA la convenzione «LANT-n»
    contiene la stringa senza citare una cella. Il regex chiede un numero
    concreto, e i riferimenti a cifra sola restano fuori.
  · **il righello nuovo e' il peggiore**: stampo anche i documenti che NON
    citano nulla — se un consumatore atteso da' zero, e' il conteggio a
    essere rotto, non il documento a essere vuoto.
  · **assenza != zero**: un id citato che NON esiste nel registro e' un
    RIFERIMENTO ROTTO e va elencato, non ignorato.

    python scripts/celle_load_bearing.py
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
DOCS = RADICE / "docs" / "stato-reale"
REGISTRO = DOCS / "00-ESAME.md"

#: i documenti che un lettore ESTERNO legge (Aurelio, un analista, il cliente)
CONSUMATORI = [
    "REPORT-30-08-lo-stato-vero-del-prodotto.md",
    "quadro-decisione-versione-30-08.md",
    "punto-del-mattino-31-08.md",
    "le-quattro-promesse-sulle-porte-degli-agenti.md",
]
#: la vetrina vera e' fuori da docs/
VETRINA = [RADICE / "README.md"]

#: `LANT-109`, `W2-30`, `W7-89`, `W8-31` — sigla + numero, non la sola sigla
RIF = re.compile(r"\b((?:LANT|W\d)-\d+[a-z]?)\b")
#: ⚠️ `^\| ([\w-]+) \|` accettava QUALSIASI riga che aprisse con `| parola |`.
#: Misurato il 01/09 alle 20:28: prendeva **106 righe in piu'**, e sono tutte
#: righe numerate (`| 1 |`, `| 2 |`, …) di ALTRE TABELLE dentro lo stesso file
#: — liste di cancelli, di comandi, di verifiche. Zero avevano una sigla vera
#: che il pattern stretto non copre (categoria «Wnn-n» = 0), quindi il rischio
#: opposto non si e' materializzato: il denominatore era gonfio e basta.
#: Effetto: 695 -> 614 celle, e il tasso di load-bearing sale.
CELLA = re.compile(r"^\| ((?:LANT|W\d)-\d+[a-z]?) \|")
COLONNE = re.compile(r"(?<!\\)\|")
#: una firma nel testo della cella (euristica dichiarata, non un verdetto:
#: @ws4 ha misurato che questo criterio ha 3 classi di falsi positivi)
FIRMA = re.compile(r"(?:2ª |seconda )?firma @|controfirm", re.I)


def main() -> int:
    esistenti = {}
    for r in REGISTRO.read_text(encoding="utf-8").splitlines():
        m = CELLA.match(r)
        if m and len(COLONNE.split(r)) >= 7:
            esistenti[m.group(1)] = r

    citate: dict[str, set[str]] = defaultdict(set)
    vuoti = []
    for nome in CONSUMATORI:
        p = DOCS / nome
        if not p.exists():
            vuoti.append(f"{nome} (NON ESISTE)")
            continue
        ids = set(RIF.findall(p.read_text(encoding="utf-8")))
        if not ids:
            vuoti.append(f"{nome} (0 riferimenti)")
        for i in ids:
            citate[i].add(nome)
    for p in VETRINA:
        ids = set(RIF.findall(p.read_text(encoding="utf-8"))) if p.exists() else set()
        if not ids:
            vuoti.append(f"{p.name} (0 riferimenti)")
        for i in ids:
            citate[i].add(p.name)

    rotti = sorted(i for i in citate if i not in esistenti)
    vive = {i: v for i, v in citate.items() if i in esistenti}
    #: ⚠️ la firma NON sta in una colonna a indice fisso. Misurato il 01/09
    #: alle 20:16: le 366 righe firmate del registro distribuiscono la firma su
    #: DODICI indici diversi ({8: 48, 9: 265, 10: 16, 11: 19, 12: 4, …}), perche'
    #: le righe hanno da 10 a 40 colonne — chi scrive mette barre nel testo. La
    #: firma sta nell'ULTIMA colonna reale (il regime), non nel verdetto.
    #: Cercarla in `[6]` la vedeva quasi mai. Tengo il vecchio ACCANTO al nuovo
    #: nella stessa esecuzione: un A/B cosi' e' immune allo scorrere del file.
    con_firma_vecchio = {i for i in vive
                         if FIRMA.search(COLONNE.split(esistenti[i])[6])}
    con_firma = {i for i in vive if FIRMA.search(esistenti[i])}

    print(f"  registro: {len(esistenti)} celle")
    print(f"  celle LOAD-BEARING (citate da un documento che si legge): "
          f"{len(vive)}  = {100*len(vive)/len(esistenti):.1f}%")
    print(f"     di cui con una firma nel testo (euristica): {len(con_firma)}"
          f"  = {100*len(con_firma)/max(1,len(vive)):.1f}% delle load-bearing")
    print(f"     SENZA: {len(vive) - len(con_firma)}")
    print(f"     ⚠️ col vecchio criterio (solo colonna [6], il VERDETTO): "
          f"{len(con_firma_vecchio)} — differenza "
          f"{len(con_firma) - len(con_firma_vecchio):+d}")
    print()
    per_doc: dict[str, int] = defaultdict(int)
    for i, ds in vive.items():
        for d in ds:
            per_doc[d] += 1
    print("  chi cita quante celle:")
    for d, n in sorted(per_doc.items(), key=lambda x: -x[1]):
        print(f"     {n:>4}  {d}")
    if vuoti:
        print("\n  ⚠️ consumatori con ZERO riferimenti (guardia: è il righello "
              "o il documento?):")
        for v in vuoti:
            print(f"     {v}")
    if rotti:
        print(f"\n  🔴 {len(rotti)} riferimenti a celle CHE NON ESISTONO nel registro:")
        print(f"     {' '.join(rotti[:20])}")
    print()
    print("  ⚠️ La colonna «con firma» usa un'euristica testuale con tre classi")
    print("     note di falsi positivi (menzione, alias, autofirma — @ws4 31/08).")
    print("     È un ordine di grandezza, non un verdetto cella per cella.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
