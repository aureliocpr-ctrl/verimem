"""Il moat sa distinguere una smentita VERA da una FALSA?

`W2-69` (mia, 05/08) misurava le negazioni **FALSE**: col flip acceso una
di quelle entra a grounding 0.4. Il commit `e4b8c53b` dello stesso giorno
dichiara l'altro verso — «il moat boccia le smentite VERE» — e quella
popolazione **non l'avevo mai misurata**: una popolazione sola, che e' la
trappola scritta in casa («misura ENTRAMBE le popolazioni»).

Il caso che riapre la questione e' reale: il 30/08 il gate ha
quarantinato un mio fatto — «nell'elenco degli status provisional non e'
presente» — con `L4-negazione`, **ed era vero** (verificato: `provisional`
non compare fra i 29 status che il codice assegna).

DISEGNO — quattro coppie SPECULARI: stessa identica frase, fonte
cambiata. Cosi' il controllo non e' un'altra popolazione, e' la stessa
frase con la verita' rovesciata, e nessuna differenza di forma puo'
spiegare un verdetto diverso.

PREDIZIONE DICHIARATA PRIMA (falsificabile):
  se il layer che vede la negazione e' SINTATTICO (cerca il negatore),
  ferma tutte e otto ⇒ 4 falsi positivi su 4, e il segnale e' inutile
  come discriminante.
  Se invece il moat legge la fonte, le quattro VERE passano.
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()   # PRIMA dell'import


#: (fonte, claim, la smentita e' VERA?)
COPPIE = [
    ("Gli status assegnati dal codice sono: model_claim, quarantined, verified.",
     "Fra gli status assegnati dal codice non compare provisional.", True),
    ("Gli status assegnati dal codice sono: model_claim, quarantined, provisional.",
     "Fra gli status assegnati dal codice non compare provisional.", False),

    ("La suite ha dato 12 passed, 0 failed.",
     "La suite non ha prodotto fallimenti.", True),
    ("La suite ha dato 12 passed, 3 failed.",
     "La suite non ha prodotto fallimenti.", False),

    ("Il file elenca tre voci: alfa, beta, gamma.",
     "Il file non elenca delta.", True),
    ("Il file elenca tre voci: alfa, beta, delta.",
     "Il file non elenca delta.", False),

    ("Il test e' stato eseguito senza il flag strict.",
     "Il test non e' stato eseguito con il flag strict.", True),
    ("Il test e' stato eseguito con il flag strict.",
     "Il test non e' stato eseguito con il flag strict.", False),
]


def main() -> int:
    from verimem.client import Memory

    mem = Memory(os.path.join(os.environ["HIPPO_DATA_DIR"], "banco.db"))
    print(f"  store: {os.environ['HIPPO_DATA_DIR']}")
    print(f"  {'verita''':<9}{'esito':<14}{'grounding':>10}  {'layers'}")
    esiti = []
    for i, (fonte, claim, vera) in enumerate(COPPIE):
        r = mem.add(claim, topic=f"neg/{i}", source=fonte, validate="full")
        st = str(r.get("status"))
        gs = r.get("grounding_score")
        lay = ",".join(w.get("layer", "?") for w in (r.get("warnings") or []))
        esiti.append((vera, st, gs, lay))
        print(f"  {'VERA' if vera else 'FALSA':<9}{st:<14}"
              f"{(f'{gs:.1f}' if isinstance(gs, (int, float)) else '-'):>10}  {lay[:52]}")

    ammesse_vere = sum(1 for v, s, _, _ in esiti if v and s != "quarantined")
    ammesse_false = sum(1 for v, s, _, _ in esiti if not v and s != "quarantined")
    tot_v = sum(1 for v, *_ in esiti if v)
    tot_f = len(esiti) - tot_v
    print("\n  == LE DUE POPOLAZIONI, UNA ACCANTO ALL'ALTRA")
    print(f"     smentite VERE ammesse : {ammesse_vere}/{tot_v}"
          f"   (dovrebbero passare TUTTE)")
    print(f"     smentite FALSE ammesse: {ammesse_false}/{tot_f}"
          f"   (dovrebbero cadere TUTTE)")
    print(f"\n  la predizione era: se il layer e' SINTATTICO ferma tutte e otto"
          f" ⇒ vere ammesse = 0")
    print(f"  esito: vere ammesse = {ammesse_vere} ⇒ "
          f"{'PREDIZIONE CONFERMATA' if ammesse_vere == 0 else 'PREDIZIONE FALSIFICATA'}")
    # IL CONTROESEMPIO che falsifica la mia stessa spiegazione. Se la
    # differenza fosse «e' un elenco», nulla la cambierebbe; se invece e'
    # «la fonte ENUNCIA o OMETTE», basta scrivere l'assenza perche' lo
    # STESSO claim passi. Stessa lista, una frase in piu'.
    print()
    print('  == CONTROESEMPIO: stessa lista, assenza DETTA non mostrata')
    for k, (fonte, claim) in enumerate([
        ("Il file elenca tre voci: alfa, beta, gamma. "
         "Delta non e' presente nel file.", 'Il file non elenca delta.'),
        ('Gli status assegnati sono model_claim, quarantined, verified. '
         "Provisional non e' fra gli status assegnati.",
         'Fra gli status assegnati non compare provisional.'),
    ]):
        rc = mem.add(claim, topic=f'ctrl/{k}', source=fonte, validate='full')
        gc = rc.get('grounding_score')
        _g = f'{gc:.1f}' if isinstance(gc, (int, float)) else '-'
        print(f"     {str(rc.get('status')):<14}{_g:>8}   assenza ENUNCIATA")

    print("\n  ⚠️ COSA NON DICE: otto casi costruiti, non un campione del")
    print("  corpus. Dice se il meccanismo distingue, non quanto spesso")
    print("  capiti. E il regime e' quello di default del giudice locale.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
