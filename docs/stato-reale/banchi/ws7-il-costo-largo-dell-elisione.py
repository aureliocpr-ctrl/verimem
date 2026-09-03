"""L'ALTRA popolazione: quante proposizioni che il figlio AMMETTEVA sono fermate oggi?

    python docs/stato-reale/banchi/ws7-il-costo-largo-dell-elisione.py <FIGLIO>

    git worktree add --detach <FIGLIO> c857752e

⚡ NESSUN MODELLO: `ground_write=False`. ⚠️ Store vivo in SOLA LETTURA.

━━ PERCHE' ESISTE, E PERCHE' E' LA DOMANDA SIMMETRICA ━━━━━━━━━━━━━━━━━━━━━━━
Il banco fratello (`ws7-le-quindici-liberate-tornano-fermate.py`) chiede: «delle
15 che il figlio aveva liberato, quante ne riprende la cura?» — risposta 5.
Ma quella e' la popolazione che la cura CAMBIA IN MEGLIO, ed e' esattamente la
forma dell'errore che questa cura e' nata per riparare: il 30/08 avevo guardato
i 132 fatti che la cura cambiava, non i 4.649 che la garanzia proteggeva.

Questa e' la domanda dall'altro lato, chiesta da @lead-audit il 03/09 alle 21:00:

    di TUTTE le proposizioni che il figlio AMMETTEVA, quante ne ferma OGGI?

Le 5 riprese sono un sottoinsieme di questo numero. La differenza e' il COSTO
LARGO della patch sull'articolo elidato: `l'app` non tokenizza piu' `lapp` ma
`app`, e `app` era gia' in SOFTWARE_HEADS — quindi la regola ANY-TOKEN, che
prima l'italiano con elisione scavalcava per caso, ora si applica. Vale per
OGNI claim con «l'», «dell'», «nell'», «sull'», «un'», «quest'», «quell'».

━━ IL CONTROLLO POSITIVO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Le 5 note DEVONO ricomparire in questo elenco: sono ammesse dal figlio e
fermate oggi, quindi appartengono a questa popolazione per costruzione. Se non
ci sono, il banco sta misurando qualcos'altro e il verdetto e' «non
riproducibile», col difetto dalla mia parte.

━━ E L'ELENCO, NON IL CONTEGGIO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Un fatto fermato in piu' e' un guadagno se e' una self-claim e un danno se e'
un fatto di terzi vero. Il conteggio da solo non distingue le due cose, e su
questa cura la distinzione E' la decisione: si stampano tutte.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

#: ⚠️ `verdetti` e `proposizioni` si IMPORTANO dal banco fratello, non si
#: ricopiano: due copie della stessa misura divergono, ed e' la prima delle
#: cinque classi che questo progetto si e' scritto in casa. Il fratello ha il
#: nome con i trattini, quindi l'import passa da importlib.
_FRATELLO = Path(__file__).with_name("ws7-le-quindici-liberate-tornano-fermate.py")
_spec = importlib.util.spec_from_file_location("_ws7_fratello", _FRATELLO)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)  # type: ignore[union-attr]
proposizioni, verdetti, fermata = _m.proposizioni, _m.verdetti, _m.fermata

#: le cinque note dal banco fratello: il controllo positivo di questo.
ATTESE = [
    "La funzionalita' funziona ed e' verificata.",
    "L'implementazione e' finita e collaudata.",
]


def main() -> None:
    if len(sys.argv) < 2:
        print("  uso: python <questo file> <worktree-FIGLIO c857752e>")
        raise SystemExit(2)
    figlio = Path(sys.argv[1])
    limite = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    oggi = Path(__file__).resolve().parents[3]

    frasi = proposizioni(limite)
    print(f"  proposizioni dal corpus vivo   : {len(frasi)}")

    print(f"  braccio FIGLIO {figlio}")
    vf = verdetti(figlio, frasi)
    ammesse = [f for f, a, _ in vf if not fermata(a)]
    print(f"  AMMESSE dal figlio c857752e    : {len(ammesse)}")
    if not ammesse:
        raise SystemExit("  CONTROLLO POSITIVO SPENTO: il figlio non ammette "
                         "niente. Verdetto: non riproducibile, difetto MIO.")

    print(f"  braccio OGGI   {oggi}")
    vo = verdetti(oggi, ammesse)
    fermate = [f for f, a, _ in vo if fermata(a)]

    print()
    print(f"  ⇒ FERMATE OGGI fra quelle che il figlio ammetteva: {len(fermate)}")
    print(f"     su {len(ammesse)} ammesse = "
          f"{100.0 * len(fermate) / len(ammesse):.2f}%")
    print()

    viste = [a for a in ATTESE if a in fermate]
    print(f"  controllo positivo (le note del banco fratello): {len(viste)}/{len(ATTESE)}")
    if not viste:
        # ⚠️ E QUI HO RIFATTO L'ERRORE CHE AVEVO APPENA CURATO NEL FRATELLO.
        # Le due note sono DUE FRASI PRECISE su 17.475: in un campione da 200
        # non ci sono, e il banco gridava «non riproducibile» quando la causa
        # era la DIMENSIONE DEL CAMPIONE (misurato il 2026-09-03 alle 21:01,
        # venti minuti dopo aver scritto la stessa cura nel banco fratello).
        # ⇒ Ho copiato la STRUTTURA senza copiare la CURA: e' la classe ①
        #   applicata a me, e il rimedio non e' ricordarsene — e' che il
        #   controllo dichiari la CONDIZIONE in cui vale.
        if limite:
            print(f"  ⓘ campione LIMITATO a {limite}: le due note sono frasi "
                  "precise del corpus intero e qui possono benissimo mancare. "
                  "Il controllo positivo vale SOLO senza limite.")
        else:
            print("  ⚠️ Sul corpus INTERO nessuna delle note ricompare: questo "
                  "banco NON sta misurando la stessa popolazione del fratello. "
                  "Verdetto: non riproducibile, difetto MIO.")

    print()
    print("  --- L'ELENCO INTERO (giudicare una per una) ---")
    for f in fermate:
        print(f"    FERMATA OGGI  {f[:120]}")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps(
        {"proposizioni": len(frasi), "ammesse_dal_figlio": len(ammesse),
         "fermate_oggi": len(fermate), "elenco": fermate,
         "controllo_positivo_viste": viste},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")


if __name__ == "__main__":
    main()
