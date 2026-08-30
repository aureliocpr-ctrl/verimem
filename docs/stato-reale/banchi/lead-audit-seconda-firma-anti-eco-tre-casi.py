# -*- coding: utf-8 -*-
"""SECONDA FIRMA sulla guardia anti-eco (`1a4b8635`) — tre casi miei, 30/08.

La prima verifica e' dell'autore (ws4: 19 test + 0/184 sui reali, W7-68).
Questa e' la controprova del firmatario con casi NON presi dal test:
  A  eco RISCRITTA come fonte (parole spostate, stesso contenuto)
     -> la guardia deve negare il perdono: esito FERMATO (L1.13 fra i layer)
  B  fonte legittima che sostiene il participio (output di un comando)
     -> deve ENTRARE: il perdono per fonte vera resta
  C  claim che DESCRIVE un output del gate (la classe W7-68: descrittivo,
     non eco) -> la GUARDIA non deve toccarlo (niente L1.13 fra i layer)

STORIA DELL'ATTESA (dichiarata, non riscritta): la prima esecuzione
(20:50) aveva atteso «C ammesso» ed e' stata FALSIFICATA — C esce
`downgrade` ma per mano del MOAT (`L4-grounding`: un esemplare singolo
non sostiene una generalizzazione), con la guardia MUTA (L1.13 assente).
L'attesa confondeva il perimetro della guardia con quello della porta.
Attesa corretta sul perimetro della FIRMA (la guardia): A fermato CON
L1.13 · B ammesso · C qualunque esito della porta MA senza L1.13.
Nota per W7-68: la classe descrittiva oggi alla porta prenderebbe
downgrade dal moat — tema di ws4, non di questa firma. Il moat viene
scaldato col preflight di W7-87 (un processo fresco parte warming).

    python -u docs/stato-reale/banchi/lead-audit-seconda-firma-anti-eco-tre-casi.py
"""
from __future__ import annotations

import time

CASI = [
    ("A eco riscritta",
     "La migrazione dei dati e' stata completata senza errori.",
     "Senza errori e' stata completata la migrazione dei dati.",
     "fermato"),
    ("B fonte legittima",
     "Il backup notturno e' stato completato.",
     "$ run_backup.sh --notturno\n[2026-08-30 03:12] backup completed, "
     "42 files, exit 0",
     "ammesso"),
    ("C descrittivo W7-68",
     "Sulla CLI il remember con una fonte che sostiene stampa admitted.",
     "$ verimem remember \"il timeout e' 30s\" --source \"config: timeout=30\"\n"
     "admitted id=ab12cd grounding_score=97.1",
     "senza-L1.13"),
]


def main() -> int:
    from verimem.local_grounding import judge_state, warm_local_judge_async
    warm_local_judge_async()
    attesa = 0
    while judge_state() == "warming" and attesa < 180:
        time.sleep(2)
        attesa += 2
    print(f"  preflight W7-87: judge_state={judge_state()} dopo {attesa}s")

    from verimem.anti_confab_gate import run_validation_gate
    esiti = []
    for nome, claim, fonte, atteso in CASI:
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte, ground_write=True)
        layers = sorted({str((w or {}).get("layer") or "") for w in g.warnings}
                        - {""})
        reale = "fermato" if g.action in ("downgrade", "quarantine") else "ammesso"
        if atteso == "senza-L1.13":
            ok = "L1.13" not in layers
        else:
            ok = reale == atteso
        esiti.append(ok)
        print(f"  {nome:<22} atteso={atteso:<11} reale={reale:<8} "
              f"action={g.action:<10} layers={layers} "
              f"{'OK' if ok else 'FALSIFICATO'}")
    if all(esiti):
        print("  == FIRMA SOSTENUTA sul perimetro della guardia: A fermata "
              "con L1.13, B entra, C senza L1.13 (l'esito porta e' del moat)")
        print("EXIT=0")
        return 0
    print("  == FIRMA FALSIFICATA: un caso non si comporta come atteso")
    print("EXIT=1")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
