"""Il fronte ② poggia su un meccanismo che non gira: `select_relevant_span`.

Avevo attribuito l'inganno del giudice (100.0 -> 0.4 togliendo solo «Art. N -»,
commit `101b6f08`) al **selettore di span**, che ordina le unita' della fonte
per **sovrapposizione di token col claim**: il `3` del claim inventato pesca il
`3` del numero d'articolo. Il meccanismo e' plausibile — e **non l'avevo
misurato**.

`grounding_gate.py:371` apre con::

    if not source or len(source) <= budget:
        return source

⇒ **il selettore non fa NIENTE quando la fonte sta nel budget.** La fonte del
caso ingannato e' di **227 caratteri**; il budget di default e' **1500**
(`local_grounding.py:52`). ⇒ **su quel caso `select_relevant_span` non e' mai
stata eseguita**, e l'intero delta di 99,4 punti nasce da cio' che il giudice
**LEGGE**, non da cio' che il selettore **SCEGLIE**.

CONTROLLO CHE DEVE POTER FALLIRE: lo strumento deve **saper cambiare** qualcosa,
altrimenti «span == fonte» non distingue «non gira» da «gira e non cambia
niente». Percio' il banco misura anche una fonte **sopra** il budget.

CONSEGUENZE, e una e' a mio sfavore due volte:

1. La cura proposta — «togliere la numerazione **dallo span**, in forma
   condizionale» — **non puo' funzionare** sul caso che l'ha motivata: li' non
   c'e' nessuna selezione di span. Applicarla vorrebbe dire togliere la
   numerazione dal **testo mostrato al giudice**, cioe' **alterare l'evidenza**:
   una proposta molto piu' seria, e non una cura tecnica.

2. Mi ero **rimproverato** che «il banco misurava la `source` invece dello
   span». **Quel rimprovero era sbagliato**: sotto i 1500 caratteri la `source`
   **e'** cio' che il giudice vede, e su quella popolazione il banco misurava
   esattamente la cosa giusta. Le due grandezze divergono **solo** oltre il
   budget. 🔑 *Anche l'autocritica e' una misura, e va falsificata come le
   altre: mi sono corretto un difetto che non avevo, il che e' un modo di
   sbagliare che si traveste da rigore.*

3. Resta NON MISURATO — e non lo posso misurare dallo store — **quale frazione
   delle fonti reali superi i 1500 caratteri**, cioe' su quanta parte del
   traffico il selettore giri davvero. Il campo `facts.grounding_span` **non
   serve**: e' troncato a 400 caratteri per la persistenza, e il codice lo dice
   gia' a `grounding_gate.py:410-415` («*quel campo dice cosa e' stato SALVATO,
   non cosa il giudice ha VISTO*»). **La lezione era gia' scritta nel file.**

    python docs/stato-reale/banchi/ws3-lo-span-selector-non-gira-affatto-sul-caso-ingannato.py
"""

from __future__ import annotations

import ast
from pathlib import Path

from verimem.grounding_gate import select_relevant_span
from verimem.local_grounding import _DEFAULT_FOCUS_BUDGET

CLAIM = "La penale prevista dal contratto e di 3 giorni."
BANCO = Path(__file__).with_name(
    "ws3-il-giudice-e-ingannato-dalla-stessa-numerazione.py")


def _costanti(p: Path) -> dict[str, str]:
    """Le fonti del banco originale, prese dal SORGENTE: riscriverle a mano
    qui vorrebbe dire misurare la mia trascrizione, non quel caso."""
    testo = p.read_text(encoding="utf-8")
    return {n.targets[0].id: n.value.value
            for n in ast.parse(testo).body
            if isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)
            and isinstance(n.targets[0], ast.Name)}


def main() -> int:
    if not BANCO.exists():
        print(f"  banco originale non trovato: {BANCO.name} — NESSUN VERDETTO")
        return 1
    k = _costanti(BANCO)
    fonte = k.get("FONTE_A")
    if not fonte:
        print("  FONTE_A non trovata nel banco originale — NESSUN VERDETTO")
        return 1

    b = _DEFAULT_FOCUS_BUDGET
    print(f"  budget di default del giudice ... {b}  (local_grounding.py:52)")
    print(f"  FONTE_A del caso ingannato ...... {len(fonte)} caratteri")

    span = select_relevant_span(fonte, CLAIM, budget=b)
    intatta = span == fonte
    print(f"\n  [1] lo span e' la fonte INTERA? {intatta}  (len span {len(span)})")

    lunga = (fonte + "\n") * 12
    span_l = select_relevant_span(lunga, CLAIM, budget=b)
    cambia = span_l != lunga
    print(f"  [2] CONTROLLO POSITIVO: fonte {len(lunga)} char > budget "
          f"-> span {len(span_l)} char, diverso? {cambia}")
    if not cambia:
        print("      CONTROLLO CADUTO: il selettore non cambia niente NEMMENO")
        print("      sopra il budget ⇒ «span == fonte» non distingue «non gira»")
        print("      da «gira a vuoto». NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if intatta:
        print("     CONFERMATO: sul caso che ha motivato il fronte ②, il selettore")
        print("     di span NON VIENE MAI ESEGUITO. Il delta di 99,4 punti nasce da")
        print("     cio' che il giudice LEGGE, non da cio' che il selettore SCEGLIE.")
        print("     ⇒ «togliere la numerazione dallo span» non e' applicabile li';")
        print("       l'unica forma sarebbe ALTERARE L'EVIDENZA mostrata al giudice,")
        print("       che e' una decisione di design, non una cura tecnica.")
    else:
        print("     PREDIZIONE FALSIFICATA: il selettore tocca la fonte anche")
        print("     sotto il budget ⇒ ho letto male il primo `if` e il fronte ②")
        print("     resta in piedi come l'avevo formulato.")

    print("\n  ⚠️ LIMITI: un caso, un budget (quello di default: "
          "ENGRAM_GROUNDING_FOCUS_CHARS puo' cambiarlo). NON misurato: quale")
    print("     frazione delle fonti reali superi il budget — e NON e' misurabile")
    print("     da `facts.grounding_span`, troncato a 400 per la persistenza.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
