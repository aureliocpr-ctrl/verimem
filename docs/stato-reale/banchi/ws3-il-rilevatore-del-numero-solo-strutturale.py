"""Il rilevatore del numero solo-strutturale regge su ENTRAMBE le popolazioni?

Misura `_numero_solo_strutturale.avviso_numero_solo_strutturale` prima di
proporne la promozione. **Misurare prima di curare**: stanotte su tre cure
misurate prima, **una sola** e' sopravvissuta alla propria misura.

⚠️ **DUE POPOLAZIONI, e la seconda e' quella che uccide i criteri.** Sui soli
casi che deve prendere ogni criterio sembra ottimo; il prezzo si vede su quelli
che deve **lasciar stare**:

    A  DEVE SEGNALARE   il numero c'e' nella fonte, ma solo come «Art. N»
    B  DEVE ASTENERSI   il claim parla della SEZIONE («l'articolo 7 prevede»)
    C  DEVE TACERE      il numero e' un valore VERO, affermato dalla fonte
    D  DEVE TACERE      il numero non c'e' affatto -> e' affare di L4.1

CONTROLLO CHE DEVE POTER FALLIRE: **A deve segnalare**. Se non segnala, il
rilevatore e' inerte e nessun «zero falsi positivi» su B/C/D significa niente —
e' la trappola in cui sono caduto due volte stanotte: *uno zero non e' leggibile
finche' non provi che lo strumento vede*.

SECONDO CONTROLLO: **se spengo l'astensione ①, B deve diventare un falso
positivo.** Se B resta pulito anche senza la regola, quella regola non sta
facendo niente e il suo «funziona» e' un caso. 🔑 *La prova che un criterio
serve e' che TOGLIENDOLO il numero cambi.*

Il caso A e' quello **vero**, preso dal sorgente del banco che lo trovo'
(`101b6f08`), non ricopiato a mano.

    python docs/stato-reale/banchi/ws3-il-rilevatore-del-numero-solo-strutturale.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _numero_solo_strutturale import (  # noqa: E402
    avviso_numero_solo_strutturale,
)

BANCO = Path(__file__).with_name(
    "ws3-il-giudice-e-ingannato-dalla-stessa-numerazione.py")

FONTE_VALORI = (
    "Art. 3 - La penale e' fissata in 500 euro per ogni giorno di ritardo.\n"
    "Art. 6 - Il termine di consegna e' di 30 giorni dalla firma."
)


def _fonte_vera() -> str | None:
    if not BANCO.exists():
        return None
    k = {n.targets[0].id: n.value.value for n in ast.parse(
        BANCO.read_text(encoding="utf-8")).body
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
        and isinstance(n.value.value, str) and isinstance(n.targets[0], ast.Name)}
    return k.get("FONTE_A")


def main() -> int:
    vera = _fonte_vera()
    if not vera:
        print("  FONTE_A non recuperata dal banco originale — NESSUN VERDETTO")
        return 1
    print(f"  fonte vera del caso ingannato ({len(vera)} char):")
    print(f"    «{vera[:96].replace(chr(10), ' / ')}…»")

    casi = [
        ("A1 numero = numero d'articolo", "SEGNALA",
         "La penale prevista dal contratto e' di 3 giorni.", vera),
        ("A2 idem, altra sezione       ", "SEGNALA",
         "Il termine di consegna e' di 6 giorni.", vera),
        ("B1 claim SULLA sezione       ", "TACE",
         "L'articolo 3 prevede una penale.", vera),
        ("B2 claim sulla riga          ", "TACE",
         "La riga 3 del contratto e' quella della penale.", vera),
        ("C1 valore VERO nella fonte   ", "TACE",
         "La penale e' di 500 euro al giorno.", FONTE_VALORI),
        ("C2 secondo valore vero       ", "TACE",
         "Il termine di consegna e' di 30 giorni.", FONTE_VALORI),
        ("D1 numero ASSENTE (L4.1)     ", "TACE",
         "La penale e' di 91 euro.", FONTE_VALORI),
        ("D2 fonte senza numerazione   ", "TACE",
         "La penale e' di 3 giorni.",
         "La penale e' fissata in 500 euro per ogni giorno di ritardo."),
    ]

    print(f"\n  {'caso':<32} {'atteso':<9} {'esito':<9} {'ok?'}")
    print("  " + "-" * 62)
    ok = 0
    esiti: dict[str, bool] = {}
    for et, atteso, claim, src in casi:
        a = avviso_numero_solo_strutturale(claim, src)
        esito = "SEGNALA" if a else "TACE"
        giusto = esito == atteso
        esiti[et.strip()] = bool(a)
        ok += giusto
        det = ""
        if a:
            s = a["sospetti"][0]
            det = f"   [{s['numero']} in «{s['contesto']}»]"
        print(f"  {et:<32} {atteso:<9} {esito:<9} "
              f"{'si' if giusto else 'NO'}{det}")

    # ⚠️ la chiave si estrae in una variabile: un backslash dentro una f-string
    # e' SINTASSI INVALIDA su Python 3.10, che e' il target del progetto — e il
    # file gira lo stesso qui, perche' il runtime locale e' piu' nuovo. Terza
    # volta che ci inciampo: il verde locale non dice niente sul target.
    _a1 = esiti["A1 numero = numero d'articolo"]
    print(f"\n  [1] CONTROLLO POSITIVO — A1 segnala? {_a1}")
    if not _a1:
        print("      CONTROLLO CADUTO: il rilevatore non prende nemmeno il caso")
        print("      che l'ha motivato ⇒ e' INERTE, e gli zeri su B/C/D non")
        print("      significano niente. NESSUN VERDETTO.")
        return 1

    # [2] La prova che l'ASTENSIONE serve: togliendola, B deve sporcarsi.
    import _numero_solo_strutturale as mod  # noqa: PLC0415
    salvato = mod._RIFERIMENTO_RE
    class _MaiTrovato:  # noqa: N801
        @staticmethod
        def search(_s):
            return None
        def finditer(self, s):
            return salvato.finditer(s)
    mod._RIFERIMENTO_RE = _MaiTrovato()
    senza = [avviso_numero_solo_strutturale(c, s) is not None
             for et, _a, c, s in casi if et.startswith("B")]
    mod._RIFERIMENTO_RE = salvato
    print(f"  [2] SPENGO l'astensione ① -> i casi B diventano falsi positivi? "
          f"{senza}")
    if not any(senza):
        print("      CONTROLLO CADUTO: i casi B restano puliti ANCHE senza la")
        print("      regola di astensione ⇒ quella regola non sta facendo")
        print("      niente, e il suo «funziona» qui e' un caso. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     {ok}/{len(casi)} celle come atteso")
    if ok == len(casi):
        print("     RETTA su entrambe le popolazioni, con i due controlli in")
        print("     piedi: prende il caso vero, e l'astensione e' NECESSARIA")
        print("     (spegnendola i casi B si sporcano).")
        print("     ⇒ PROPONIBILE. Non promosso: serve una misura sul CORPUS")
        print("       vero, dove i falsi positivi si contano a mano.")
    else:
        print("     NON RETTA: qualche cella non fa quello che deve. Il")
        print("     rilevatore NON e' proponibile cosi'.")

    print("\n  ⚠️ LIMITI: otto casi costruiti, una fonte vera e una sintetica,")
    print("     italiano. NON misurato sul corpus: quanti avvisi darebbe su")
    print("     5368 fonti reali — ed e' la misura che stanotte ha gia' ucciso")
    print("     `L4.3` (27 falsi positivi su 28).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
