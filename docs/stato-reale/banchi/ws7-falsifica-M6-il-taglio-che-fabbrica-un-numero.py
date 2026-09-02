"""Falsificazione di M6 (@ws6): L4.1 accusa perche' manca la prova, o perche' il
taglio FABBRICA un numero che nella prova non c'era?

COSA VERIFICO. @ws6 il 02/09 ha chiuso M6 con un reperto forte: sugli STESSI
fatti, tagliare lo span porta L4.1 da 2/12 a 9/12 — a punteggio invariato. La
sua predizione «il punteggio cade» era stata falsificata (mediana 0.02 e 0.00),
e guardando lo STATUS invece del punteggio ha trovato il vero effetto.

Il suo taglio e' `span[:200]`: BRUTALE, a carattere fisso. E un taglio a
carattere fisso puo' cadere in mezzo a un numero: «1.250 euro» diventa «1.2».
⇒ IPOTESI FALSIFICANTE: L4.1 confronta i numeri del claim con quelli della
fonte. Se il taglio SPEZZA un numero, la fonte tagliata contiene un numero
DIVERSO da quello del claim — e L4.1 accusa GIUSTAMENTE, ma non perche' manchi
la prova: perche' il taglio ne ha fabbricata una falsa.

IL CAMPO DIVERSO, e non e' una ripetizione: stessa query, stessi 12 fatti,
stesso TAGLIO=200, ma TRE bracci invece di due.
  intero            lo span come sta                       (controllo)
  tagliato_brutale  span[:200]                             (il braccio di @ws6)
  tagliato_parola   span[:200] arretrato all'ultimo spazio (il mio)

🔑 IL TERZO BRACCIO HA MENO PROVA DEL SECONDO, non di piu': arretrando fino allo
spazio si perdono altri caratteri. ⇒ Se il braccio con MENO informazione accusa
MENO, la causa non puo' essere la perdita di prova. E' la forma del taglio.

═══ PREDIZIONE, scritta prima di eseguire ═══
P1 `intero`           L4.1 basso, ~2/12 — se non riproduco il suo controllo, il
   mio banco non e' il suo e il verdetto e' «non riproducibile».
P2 `tagliato_brutale` L4.1 alto, ~9/12 — CONTROLLO POSITIVO: devo riprodurre il
   suo risultato prima di poterlo discutere.
P3 `tagliato_parola`  L4.1 SENSIBILMENTE PIU' BASSO di brutale. Se scende verso
   il livello di `intero`, il reperto va riletto: non «tagliare la prova fa
   accusare i veri» ma «tagliare A META' DI UN TOKEN fa accusare i veri», e la
   cura diventa una riga invece di un'architettura.
COME MUORE P3: se `tagliato_parola` accusa quanto `brutale`, l'artefatto non
c'e' e il reperto di @ws6 regge cosi' com'e' scritto.

⚠️ n=12, una esecuzione, e i fatti sono quelli che la sua query seleziona: se il
corpus e' cambiato dalle 13, i fatti possono non essere gli stessi. Lo dichiaro
e lo stampo.
⚠️ Store di Aurelio in SOLA LETTURA; il rigiudizio scrive in un tempdir.
⚠️ COSTA RAM: carica il giudice. 36 chiamate, un processo solo.
"""
import os
import sqlite3
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws7_m6_taglio_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

CASA = os.path.expanduser(os.path.join("~", ".engram", "semantic", "semantic.db"))
N, TAGLIO = 12, 200


def taglio_su_parola(s: str, n: int) -> str:
    """span[:n] arretrato all'ultimo spazio: nessun token spezzato a meta'."""
    t = s[:n]
    i = t.rfind(" ")
    return t[:i] if i > 0 else t


def main() -> int:
    ro = sqlite3.connect("file:%s?mode=ro" % CASA.replace(os.sep, "/"), uri=True)
    righe = ro.execute(
        "SELECT id, proposition, grounding_span, grounding_score FROM facts "
        "WHERE grounding_span IS NOT NULL "
        "  AND length(grounding_span) BETWEEN 300 AND 399 "
        "  AND grounding_score >= 95 ORDER BY created_at DESC LIMIT ?",
        (N,)).fetchall()
    ro.close()
    if not righe:
        print("  la query non restituisce fatti: non riproducibile")
        return 2

    m = Memory()
    conta = {"intero": 0, "brutale": 0, "parola": 0}
    spezzati = 0
    print(f"  fatti selezionati: {len(righe)} (la stessa query di @ws6)\n")
    print(f"  {'fatto':<14} {'car.':>5} {'intero':>8} {'brutale':>9} {'parola':>8}"
          f"  {'taglio spezza un token?':>24}")

    for fid, prop, span, score in righe:
        varianti = (("intero", span),
                    ("brutale", span[:TAGLIO]),
                    ("parola", taglio_su_parola(span, TAGLIO)))
        # il taglio brutale spezza un token se il carattere al bordo non e' uno
        # spazio e nemmeno lo e' quello subito dopo
        spezza = (len(span) > TAGLIO and span[TAGLIO - 1] != " "
                  and span[TAGLIO] != " ")
        spezzati += 1 if spezza else 0
        esiti = {}
        for nome, testo in varianti:
            r = m.add(prop, topic=f"ws7/M6-{nome}-{fid}", source=testo)
            w = r.get("warnings") if isinstance(r, dict) else getattr(r, "warnings", None)
            strati = sorted({str(x.get("layer", "?")) for x in (w or [])})
            acc = any(s.startswith("L4.1") for s in strati)
            esiti[nome] = "L4.1" if acc else "-"
            if acc:
                conta[nome] += 1
        print(f"  {fid[:14]:<14} {len(span):>5} {esiti['intero']:>8}"
              f" {esiti['brutale']:>9} {esiti['parola']:>8}"
              f"  {'SI' if spezza else 'no':>24}")

    n = len(righe)
    print(f"\n  L4.1 accusa:  intero {conta['intero']}/{n}"
          f"   ·  taglio BRUTALE {conta['brutale']}/{n}"
          f"   ·  taglio SU PAROLA {conta['parola']}/{n}")
    print(f"  tagli che spezzano un token: {spezzati}/{n}")

    if conta["brutale"] <= conta["intero"]:
        print("\n  ⚠️ NON RIPRODUCO il risultato di @ws6 (brutale non accusa piu'")
        print("     dell'intero) ⇒ verdetto «non riproducibile», difetto MIO o")
        print("     corpus cambiato. Non discuto un reperto che non ho ottenuto.")
        return 1
    if conta["parola"] < conta["brutale"]:
        print("\n  🔑 P3 REGGE: il taglio su confine di parola accusa MENO, pur")
        print("     avendo MENO prova ⇒ una parte dell'effetto e' ARTEFATTO del")
        print("     troncamento, non perdita di prova.")
    else:
        print("\n  ✅ P3 CADE: anche tagliando su parola L4.1 accusa uguale ⇒")
        print("     l'effetto e' la perdita di prova, e il reperto di @ws6 regge")
        print("     esattamente come l'ha scritto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
