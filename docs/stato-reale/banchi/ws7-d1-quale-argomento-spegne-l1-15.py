"""Quale argomento della porta spegne `L1.15`? Quattro combinazioni, un processo.

DA DOVE VIENE
=============
07/09: le stesse sette self-claim danno **7/7 fermate** chiamando
`run_validation_gate` a mano e **1/7** passando da `Memory.add`. Leggendo
`client.py:745` il candidato sembrava `provenance_trusted=True` — **l'A/B lo ha
SCARTATO**: col flag a `True` il banco in-process ferma ancora 7/7.

⚠️ E ha scartato anche la mia frase: il banco alla porta stampava «LA PORTA NON
USA IL VERDETTO DEL GATE». **Non è così**: chiamato dalla porta, il gate `L1.15`
**non lo emette proprio** (`layers=[]` nella ricevuta). Non è una giuntura che
scarta un verdetto, è lo stesso gate che con altri argomenti decide altro.
*(Lezione: la conclusione precompilata dentro un banco parla prima della misura.
I numeri li stampa il banco, l'interpretazione viene dopo l'A/B.)*

COSA RESTA DA PROVARE, una variabile per volta
----------------------------------------------
`Memory.add` passa, oltre a `provenance_trusted`, anche `topic` e un `agent`
vero (più `documents`, `claimant`, `grounding_llm`). Qui si provano le quattro
combinazioni di **agent** e **topic** sulla stessa frase, nello stesso processo,
col giudice caricato una volta:

    agent=None  topic=None      ← il banco in-process: attesa FERMATA
    agent=None  topic="…"
    agent=mem   topic=None
    agent=mem   topic="…"       ← come la porta: attesa PASSATA

CONTROLLO POSITIVO: la coda nuda da sola dev'essere fermata in **tutte e
quattro**. Se in una non lo è, quella cella non misura e il banco lo dice.

    ENGRAM_ENCODE_SERVICE=0 python docs/stato-reale/banchi/ws7-d1-quale-argomento-spegne-l1-15.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
if str(RADICE) not in sys.path[:1]:
    sys.path.insert(0, str(RADICE))


def main() -> int:
    f = Path(__file__).with_name("ws7-d1-le-sette-forme-e-i-veri-composti.py")
    spec = importlib.util.spec_from_file_location("_d1", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    A, CP, FONTE = m.BRACCIO_A, m.CONTROLLO_POSITIVO, m.FONTE

    import verimem
    from verimem import Memory
    from verimem.anti_confab_gate import run_validation_gate
    from verimem.client import _blocking_layers

    print("Quale argomento spegne L1.15 — quattro combinazioni")
    print("=" * 68)
    print(f"albero misurato : {verimem.__file__}")
    print(f"versione        : {getattr(verimem, '__version__', 'ignota')}")

    tmp = Path(tempfile.mkdtemp(prefix="ws7_d1_arg_"))
    mem = Memory(str(tmp / "store.db"))
    print(f"store temporaneo: {tmp}")
    print()

    def layers(testo, agent, topic):
        g = run_validation_gate(
            proposition=testo, verified_by=None, topic=topic, agent=agent,
            source=FONTE, provenance_trusted=True,
        )
        return _blocking_layers(list(getattr(g, "warnings", []) or []))

    combinazioni = [
        ("agent=None  topic=None", None, None),
        ("agent=None  topic=set ", None, "ws7/d1-arg"),
        ("agent=mem   topic=None", mem, None),
        ("agent=mem   topic=set ", mem, "ws7/d1-arg"),
    ]

    nome_cp, testo_cp = CP
    print("controllo positivo (la coda nuda DEVE essere fermata ovunque)")
    cieche = set()
    for etichetta, ag, tp in combinazioni:
        L = layers(testo_cp, ag, tp)
        ok = bool(L)
        if not ok:
            cieche.add(etichetta)
        print(f"  {etichetta}   {'FERMATA' if ok else '⛔ NON FERMATA'}  layer={L or '-'}")
    print()

    print("le sette forme del braccio A")
    print(f"  {'forma':24s} " + "  ".join(e for e, _, _ in combinazioni))
    conta = {e: 0 for e, _, _ in combinazioni}
    for nome, testo in A:
        celle = []
        for etichetta, ag, tp in combinazioni:
            L = layers(testo, ag, tp)
            conta[etichetta] += bool(L)
            celle.append("FERMATA" if L else "passata")
        print(f"  {nome:24s} " + "  ".join(f"{c:^22s}" for c in celle))

    print()
    print("=" * 68)
    for etichetta, _, _ in combinazioni:
        nota = "   ⛔ cella cieca: il controllo positivo non si accende" \
            if etichetta in cieche else ""
        print(f"  {etichetta}   fermate {conta[etichetta]}/7{nota}")
    print()
    print("La cella che somiglia alla porta e' l'ultima. Se lì le fermate")
    print("crollano, l'argomento che spegne L1.15 e' fra agent e topic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
