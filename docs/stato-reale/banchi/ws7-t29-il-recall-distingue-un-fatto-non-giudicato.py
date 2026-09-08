"""T29: chi legge vede la differenza fra un fatto giudicato e uno che non lo e'?

LA DOMANDA CHE DECIDE IL LIVELLO
================================
T29 dice che un fatto entrato senza giudizio (`grounding_score` NULL) **resta
non giudicato per sempre**: il prodotto sana l'embedding vuoto e non il
giudizio. Il livello e' **P1** finche' il prodotto **dichiara** quello stato a
chi legge; **sale a P0** se il recall lo serve come tutti gli altri, perche'
allora chi legge non ha modo di controllare cio' che gli viene dato per buono —
la definizione di P0 in questa scheda.

COME LO MISURO, e il limite dichiarato
--------------------------------------
Due fatti nello STESSO store temporaneo, sullo stesso topic:

    A  scritto CON `source`   -> il moat gira, `grounding_score` valorizzato
    B  scritto SENZA `source` -> il moat non gira, `grounding_score` NULL

⚠️ **B non e' il caso di T29**: li' il giudizio manca per un guasto (daemon non
raggiungibile), qui per scelta di chi scrive. **Ma dal lato di chi LEGGE i due
stati sono lo stesso**: `grounding_score` NULL, `status` `model_claim`. E' la
lettura che questo banco misura, quindi la sostituzione regge — e va detta.

Poi si interroga il prodotto **dalle porte** e si guarda se la risposta:
  1. porta un campo che distingue i due (e con quale nome);
  2. li ordina diversamente.

CONTROLLO POSITIVO: A deve avere `grounding_score` non nullo e B nullo **nello
store**. Se non e' cosi', il banco non ha costruito i due casi e non misura
nulla: esce NON MISURATO invece di dare un verdetto.

    ENGRAM_ENCODE_SERVICE=0 python docs/stato-reale/banchi/ws7-t29-il-recall-distingue-un-fatto-non-giudicato.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
if str(RADICE) not in sys.path[:1]:
    sys.path.insert(0, str(RADICE))

FONTE = ("Il gate ha respinto 12 scritture su 40 durante la prova del 7 settembre, "
         "e il registro le elenca tutte.")
A = "Il gate ha respinto 12 scritture su 40 durante la prova del 7 settembre."
B = "Il gate ha respinto 31 scritture su 40 durante la prova del 7 settembre."


def _non_misurato(perche: str) -> None:
    print("\n" + "=" * 68 + "\nNON MISURATO\n" + "=" * 68)
    print(f"  {perche}")
    print("\n  Il banco NON emette numeri: un verdetto senza il suo presupposto")
    print("  accusa (o assolve) il prodotto senza prova.")
    raise SystemExit(3)


def main() -> int:
    import verimem
    from verimem import Memory

    tmp = Path(tempfile.mkdtemp(prefix="ws7_t29_"))
    db = tmp / "store.db"
    print("T29 — chi legge vede la differenza?")
    print("=" * 68)
    print(f"albero misurato : {verimem.__file__}")
    print(f"versione        : {getattr(verimem, '__version__', 'ignota')}")
    print(f"store temporaneo: {db}\n")

    mem = Memory(str(db))
    ra = mem.add(A, topic="ws7/t29", source=FONTE)
    rb = mem.add(B, topic="ws7/t29")          # nessuna fonte: il moat non gira

    def _id(r):
        return (r or {}).get("id") if isinstance(r, dict) else getattr(r, "id", None)

    ida, idb = _id(ra), _id(rb)
    with sqlite3.connect(str(db)) as cx:
        righe = {
            r[0]: (r[1], r[2]) for r in cx.execute(
                "SELECT id, status, grounding_score FROM facts WHERE id IN (?,?)",
                (ida, idb))
        }
    print("nello STORE:")
    for eti, fid in (("A con fonte ", ida), ("B senza fonte", idb)):
        st, gs = righe.get(fid, ("assente", None))
        print(f"  {eti}  id={fid}  status={st}  grounding_score={gs}")

    gsa = righe.get(ida, (None, None))[1]
    gsb = righe.get(idb, (None, None))[1]
    if gsa is None or gsb is not None:
        _non_misurato(
            "il banco non ha costruito i due casi: servono A giudicato "
            f"(grounding non nullo, ho {gsa!r}) e B non giudicato "
            f"(grounding nullo, ho {gsb!r})."
        )
    print("✅ controllo positivo: i due casi ci sono\n")

    # ── cosa vede chi LEGGE ──────────────────────────────────────────
    print("cosa torna dalla lettura (SDK):")
    try:
        hits = mem.recall("scritture respinte prova 7 settembre", k=5)
    except Exception as exc:  # noqa: BLE001
        _non_misurato(f"recall ha sollevato {type(exc).__name__}: {exc}")

    if not hits:
        _non_misurato("il recall non ha restituito nulla: senza risultati non "
                      "si puo' dire se distingua (lo store e' senza embedding, "
                      "quindi la ricerca e' solo keyword).")

    for i, h in enumerate(hits, 1):
        d = h if isinstance(h, dict) else getattr(h, "__dict__", {})
        prop = str(d.get("proposition") or d.get("text") or "")[:52]
        quale = "A" if ida and d.get("id") == ida else ("B" if idb and d.get("id") == idb else "?")
        print(f"  {i}. [{quale}] {prop!r}")
        print(f"      chiavi: {sorted(k for k in d if not k.startswith('_'))}")
        for campo in ("grounding_score", "judged", "status", "moat", "warnings"):
            if campo in d:
                print(f"      {campo} = {d[campo]!r}")

    print("\n" + "=" * 68)
    campi = set()
    for h in hits:
        d = h if isinstance(h, dict) else getattr(h, "__dict__", {})
        campi |= {k for k in d if not k.startswith("_")}
    distingue = "grounding_score" in campi
    print(f"la risposta del recall porta `grounding_score`: {distingue}")
    if not distingue:
        print("⇒ 🔴 chi legge NON ha modo di sapere se un fatto e' stato giudicato:")
        print("  T29 sale a P0. (Guardare anche le altre porte prima di dichiararlo.)")
    else:
        print("⇒ il campo c'e': T29 resta P1, e la domanda diventa se chi legge")
        print("  lo GUARDI — che e' la forma di T19 e non si misura da qui.")
    print(f"(store temporaneo in {tmp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
