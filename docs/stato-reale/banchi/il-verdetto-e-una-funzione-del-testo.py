"""IL VERDETTO E' UNA FUNZIONE DEL TESTO? — il presupposto che 14 ipotesi davano per buono.

Il dossier ⑬ elenca **quattordici** ipotesi cadute nel tentativo di predire
quali scambi di attribuzione entrano: sovrapposizione lessicale, troncamento,
posizione della smentita, natura del contorno, specie della grandezza, verso
dello scambio, struttura sintattica, lingua, unita' di misura… e conclude:
«*nessuna regola sui testi predice il verdetto*».

⚠️ **Tutte e quattordici davano per buono lo stesso presupposto**: che il
verdetto sia una FUNZIONE del testo — cioe' che la stessa coppia (claim, fonte),
giudicata due volte, dia lo stesso risultato. **Nessuna l'ha verificato.**

Se il giudizio NON e' ripetibile, allora:
· nessuna regola sul testo potra' mai predirlo, e le 14 cadute hanno **una sola
  spiegazione** invece di quattordici;
· e ogni misura di soglia fatta con una sola esecuzione — comprese le mie —
  porta una barra d'errore che non abbiamo mai dichiarato.

Se INVECE e' ripetibile, il risultato e' altrettanto utile: la variabile e' nel
testo, non l'ho trovata, e il fronte resta aperto **sapendo dove NON e'**.

COME: la stessa coppia, N volte, nello stesso processo. Misuro la dispersione di
`grounding_score` e se il verdetto (`action`) cambia.

⚠️⚠️ **IL LIMITE PIU' IMPORTANTE, e va letto PRIMA del risultato**: questo banco
interroga il giudice che il percorso normale usa — il **CE locale**, che e' un
modello deterministico, **quindi la ripetibilita' e' il risultato ATTESO e non
dice niente sull'altro giudice**. La *band escalation* usa `claude -p`, e la
cella W7-26 ha misurato che quel comando gira **senza `--model`**: li' la
ripetibilita' non e' garantita, **non e' misurata qui**, e non la si deduca da
questo numero.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se il giudice non viene interpellato affatto (nessun `grounding_score`),
     sto misurando il percorso lessicale e non il giudice: lo dico e mi fermo.
 (2) DUE coppie, non una: una che il gate ammette e una che ferma. Se la
     dispersione c'e' solo su una delle due, e' un'informazione in piu'; se la
     misurassi su una sola non saprei distinguerle.
 (3) l'ordine: alterno le due coppie invece di fare cinque volte la prima e poi
     cinque la seconda, cosi' una deriva nel tempo si vede come rumore su
     entrambe e non come differenza fra loro.

    python -u docs/stato-reale/banchi/il-verdetto-e-una-funzione-del-testo.py
"""

from __future__ import annotations

import statistics
import sys

N = 5

# La coppia che il gate AMMETTE: claim vero, fonte che lo sostiene.
FONTE = ("Art. 3 - La penale per il ritardo nella consegna e' pari al 2% "
         "dell'importo contrattuale per ogni settimana di ritardo. "
         "Art. 7 - L'importo contrattuale e' di 148000 euro. "
         "Art. 8 - La cauzione definitiva e' pari a 22000 euro.")
COPPIE = [
    ("VERO   (deve entrare)",
     "L'importo contrattuale e' di 148000 euro."),
    ("SCAMBIO (la famiglia aperta)",
     "La cauzione definitiva e' pari a 148000 euro."),
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    esiti = {nome: [] for nome, _ in COPPIE}
    print(f"  {N} ripetizioni per coppia, ALTERNATE (controllo 3)")
    for giro in range(N):
        for nome, claim in COPPIE:
            g = run_validation_gate(proposition=claim, verified_by=[],
                                    topic=None, agent=None, source=FONTE,
                                    ground_write=True)
            score = getattr(g, "grounding_score", None)
            azione = getattr(g, "action", None)
            layers = tuple(sorted(str((w or {}).get("layer") or "")
                                  for w in (getattr(g, "warnings", None) or [])))
            esiti[nome].append((score, azione, layers))
            print(f"     giro {giro + 1}  {nome:<26} score={score!r}"
                  f"  action={azione!r}")

    print("\n  -- CONTROLLO (1): il giudice e' stato interpellato?")
    tutti_none = all(s is None for v in esiti.values() for s, _a, _l in v)
    if tutti_none:
        print("     CADUTO - nessuna esecuzione ha un `grounding_score`: sto")
        print("     misurando il percorso lessicale, non il giudice. Mi fermo.")
        return 1
    print("     retto - almeno una esecuzione porta un punteggio")

    print("\n  == LA DISPERSIONE, per coppia")
    ripetibile = True
    for nome, v in esiti.items():
        punteggi = [s for s, _a, _l in v if s is not None]
        azioni = {a for _s, a, _l in v}
        layers = {l for _s, _a, l in v}
        if punteggi:
            lo, hi = min(punteggi), max(punteggi)
            sd = statistics.pstdev(punteggi) if len(punteggi) > 1 else 0.0
            print(f"     {nome}")
            print(f"        score  min={lo:.4f}  max={hi:.4f}"
                  f"  ampiezza={hi - lo:.4f}  sd={sd:.4f}")
        else:
            print(f"     {nome}: nessun punteggio")
        print(f"        action distinte : {azioni}")
        print(f"        layer distinti  : {len(layers)} combinazione/i")
        if len(azioni) > 1 or len(layers) > 1:
            ripetibile = False
        if punteggi and (max(punteggi) - min(punteggi)) > 0.01:
            ripetibile = False

    print("\n  -- IL RISULTATO")
    if ripetibile:
        print("     RIPETIBILE - stessa coppia, stesso verdetto e stesso")
        print("     punteggio a meno di 0.01. ⇒ Il presupposto delle 14 ipotesi")
        print("     REGGE: la variabile e' nel testo, e non l'ho trovata.")
        print("     Il fronte resta aperto, ma sappiamo dove NON e'.")
    else:
        print("     NON RIPETIBILE - la stessa coppia da' esiti o punteggi")
        print("     diversi. ⇒ Nessuna regola sul testo puo' predire il")
        print("     verdetto, e le 14 ipotesi cadute hanno UNA spiegazione")
        print("     invece di quattordici. ⚠️ E ogni soglia misurata con UNA")
        print("     esecuzione — comprese le mie — ha una barra d'errore che")
        print("     non abbiamo mai dichiarato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
