"""Il punteggio e' stabile sui VERI e instabile sui FALSI: l'asimmetria separa.

    esecuzione:  python docs/stato-reale/banchi/la-stabilita-separa-dove-la-soglia-no.py

Misurato il 2026-08-26 alle 23:24, `9c0c7ea5`, fuori da pytest, store nuovo per
ogni cella, `validate="full"`, CE locale. Venti casi: i dieci di ws3
(`ws3-la-contraddizione-implicita.py`), presi nella loro versione VERA e in
quella implicita falsa. Perturbazione: tre copie di una frase NEUTRA davanti
alla fonte — parla di presenze a una riunione e non nomina niente del caso.

    classe   n    |delta| medio   max     spostamenti > 20 punti
    VERO    10          2.2      12.8            0/10
    FALSO   10         15.7      98.7            2/10

PERCHE' PUO' SERVIRE. Il gate confronta il VALORE del grounding con una soglia,
e stasera e' stato misurato due volte che la soglia non esiste: min(VERO) 97.5 <
max(VANTO) 99.3, i due si sovrappongono
(`tests/test_nessuna_soglia_separa_il_vanto_dal_fatto_vero.py`). La STABILITA'
invece separa: perturba la fonte con testo neutro e rimisura — se il punteggio
non si muove il claim e' sostenuto davvero, se salta di novanta punti il giudice
stava rispondendo a qualcosa che non e' il significato.

⛔ E NON REGGE COME VETO, il controesempio e' nello stesso campione: un VERO
scende di 12,8 punti e otto FALSI restano entro 4. Come **avviso** e' un'altra
cosa — un avviso non ha bisogno della popolazione opposta, un veto si'.

⚠️ LIMITI: venti casi, UNA sola perturbazione, solo italiano. Non e' un tasso:
e' un'asimmetria vista su una popolazione piccola — scelta apposta fra quelle
che NON ho costruito io, perche' i miei campioni di stasera erano selezionati e
uno me lo sono gia' dovuto ritirare. Il costo (una seconda chiamata al CE per
scrittura) non e' misurato. E non e' provato in inglese: la ripetizione, misurata
alle 23:17, colpisce le due lingue allo stesso modo (1/10 e 1/10), ma non do per
scontato che l'asimmetria lo faccia.

DA QUI SI ALLARGA COSI': altre perturbazioni (coda invece di testa, ripetizione
della fonte, riordino delle frasi), l'inglese, e una popolazione piu' grande.
Se l'asimmetria regge su tutte, e' un avviso implementabile; se cade su una, la
riga da scrivere e' quella.
"""

from __future__ import annotations

import importlib.util
import statistics
import tempfile
from pathlib import Path

NEUTRO = (
    "Il verbale riporta le presenze dei partecipanti alla riunione mensile "
    "del comitato tecnico. "
)
BANCO_WS3 = Path("docs/stato-reale/banchi/ws3-la-contraddizione-implicita.py")


def _casi_di_ws3():
    """I casi li IMPORTA, non li ricopia: se ws3 li corregge, questo li segue."""
    spec = importlib.util.spec_from_file_location("ws3_banco", BANCO_WS3)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CASI


def _grounding(claim: str, fonte: str) -> float | None:
    from verimem.client import Memory

    mem = Memory(str(Path(tempfile.mkdtemp()) / "stab.db"))
    ric = mem.add(claim, topic="stab/p", source=fonte, validate="full")
    return ric.get("grounding_score")


def main() -> int:
    if not BANCO_WS3.exists():
        print(f"⚠️  manca {BANCO_WS3}: il banco importa i casi da li' e non li ricopia.")
        return 2
    casi = _casi_di_ws3()
    # campi del banco di ws3: 1 fonte_it · 2 vero_it · 3 implicita_it (falsa)
    popolazione = [("VERO ", c[1], c[2]) for c in casi] + [("FALSO", c[1], c[3]) for c in casi]
    print("  perturbazione: 3 copie di una frase neutra davanti alla fonte")
    print(f"  {'classe':<7} {'senza':>8} {'con':>8} {'delta':>8}")
    delte: dict[str, list[float]] = {"VERO ": [], "FALSO": []}
    for classe, fonte, claim in popolazione:
        a = _grounding(claim, fonte)
        b = _grounding(claim, NEUTRO * 3 + fonte)
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            print(f"  {classe:<7} {'?':>8} {'?':>8}   punteggio mancante — cella non misurata")
            continue
        delte[classe].append(b - a)
        print(f"  {classe:<7} {a:>8.1f} {b:>8.1f} {b - a:>+8.1f}")
    print()
    for classe, ds in delte.items():
        if not ds:
            print(f"  {classe}  nessuna cella misurata")
            continue
        print(
            f"  {classe}  n={len(ds)}  |delta| medio {statistics.mean(abs(d) for d in ds):>6.1f}"
            f"  max {max(abs(d) for d in ds):>6.1f}"
            f"  spostamenti >20 punti: {sum(1 for d in ds if abs(d) > 20)}/{len(ds)}"
        )
    v, f = delte["VERO "], delte["FALSO"]
    if v and f:
        mv = statistics.mean(abs(d) for d in v)
        mf = statistics.mean(abs(d) for d in f)
        print()
        if mf > mv:
            print(f"  ⇒ l'asimmetria REGGE su questa popolazione: falsi {mf:.1f} contro veri {mv:.1f}")
        else:
            print(f"  ⇒ l'asimmetria NON regge qui: falsi {mf:.1f} contro veri {mv:.1f} — "
                  "e' la riga che va scritta")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
