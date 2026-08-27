# -*- coding: utf-8 -*-
r"""Q4-quater: il giudice distingue una fonte che AFFERMA da una che NEGA?

CATENA E DUE FALSIFICAZIONI MIE, dichiarate. Q4-bis (20:41): il costo di un write
giudicato NON scala con la lunghezza della fonte, e' piatto da 10 a 10.000 parole -
la mia ipotesi cade. Q4-ter (20:43): non e' un troncamento posizionale, con l'ancora in
CODA il punteggio non crolla - la mia predizione cade. Resta un fatto deterministico:

    parole   200 -> 99.985710      300 -> 99.029007      500/1000/3000 -> 99.029007

⇒ oltre ~250 parole la coda non muove il giudizio di una cifra sulla dodicesima.
⚠️ E la PRIMA versione di questo banco era sbagliata: metteva il claim E la sua
negazione nella stessa fonte, quindi la fonte conteneva il claim verbatim e giudicarla
«sostenente» era corretto. Il confondente era mio. Qui la fonte che nega **non contiene
il claim**.

TRE POPOLAZIONI, non due (una sola direbbe che ogni criterio e' ottimo):
    A  SOSTIENE     la frase del claim + N parole di riempitivo
    B  NEGA         SOLO la negazione  + N parole di riempitivo   <- niente claim dentro
    C  NEUTRA       solo il riempitivo, che del registro non parla

PREDIZIONE DICHIARATA PRIMA DI ESEGUIRE:
  A alto - B **basso**, ed e' il CONTROLLO POSITIVO: una fonte che dice il contrario
  non puo' sostenere il claim. Se B esce alto quanto A, **il giudice non distingue
  affermazione da negazione**, e nessun numero di vetrina sul grounding regge.
  C fa da pavimento: dice quanto vale «la fonte non ne parla».

A/B/C NELLA STESSA ESECUZIONE: stesso processo, stessa build, stesso store, claim
identico in tutte e tre. Cambia solo la fonte.

REGIME: `Memory(path=...)` su store temporaneo · FUORI da pytest · un processo ·
riempitivo = `docs/BENCHMARKS.md`, documento vero.

RIPRODUCI:  python docs/stato-reale/banchi/ws6-Q4quater-la-contraddizione-lontana.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DISTANZE = [0, 50, 200, 1000, 3000]
CLAIM = "Il registro {n} elenca le misure del progetto."
NEGA = "Il registro {n} non elenca nessuna misura: e' vuoto, e del progetto non conserva niente."


def main() -> None:
    parole = (REPO / "docs" / "BENCHMARKS.md").read_text(encoding="utf-8").split()
    from verimem.client import Memory
    mem = Memory(str(Path(tempfile.mkdtemp()) / "q4q2.db"))
    for i in range(2):
        mem.add(f"Il registro WARMUP{i} elenca le misure.", topic="q4q2/warmup",
                source=f"Il registro WARMUP{i} elenca le misure.")

    def g(claim, src, topic):
        r = mem.add(claim, topic=topic, source=src) or {}
        return (r.get("grounding", r.get("grounding_score")), r.get("status", "?"),
                r.get("warnings"))

    print(f"{'riemp.':>7}  {'A SOSTIENE':>12}  {'B NEGA':>12}  {'C NEUTRA':>12}   "
          f"{'B-A':>8}   status di B")
    for D in DISTANZE:
        coda = " ".join(parole[:D])
        n = "ALFA"
        claim, nega = CLAIM.format(n=n), NEGA.format(n=n)
        ga, _, _ = g(claim, f"{claim}\n\n{coda}".strip(), f"q4q2/A-{D}")
        gb, sb, wb = g(claim, f"{nega}\n\n{coda}".strip(), f"q4q2/B-{D}")
        gc, _, _ = g(claim, (coda or "Testo che del registro non parla."),
                     f"q4q2/C-{D}")
        print(f"{D:>7}  {ga:>12.6f}  {gb:>12.6f}  {gc:>12.6f}   {gb-ga:>+8.3f}   "
              f"{str(sb)[:12]:<12} {wb if wb else ''}")


if __name__ == "__main__":
    main()
