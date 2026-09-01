"""I documenti su cui si DECIDE citano celle il cui verdetto e' cambiato dopo?

PERCHE'. Il censimento (`LANT-140`) dice che 35 celle sono load-bearing: le
citano `REPORT-30-08`, `quadro-decisione-versione-30-08`, `punto-del-mattino-31-08`
e `le-quattro-promesse`. Quei documenti hanno una DATA nel nome. Le celle si
aggiornano di continuo — oggi ne ho corrette tre io stessa, e una l'ho RITIRATA.

⇒ Se una cella citata da un documento del 30/08 porta una revisione del 01/09,
il documento sta appoggiandosi a un verdetto che non c'e' piu'. **Chi decide
legge il documento, non la cella.**

COSA MISURA. Per ogni cella load-bearing: la data piu' RECENTE che compare nel
suo testo, contro la data del documento che la cita. Non e' un verdetto sul
contenuto — e' un elenco di posti dove andare a guardare.

LIMITE DICHIARATO. Le date le leggo dal TESTO della cella (`gg/mm`), non da git:
una revisione che non si e' datata non la vedo, e una data citata per altro
motivo (l'incidente del 20/08) la conto come revisione. ⇒ **Sovrastima. E' un
setaccio, non un verdetto** — il numero utile e' quante celle NON hanno bisogno
di essere guardate.
"""
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
ESAME = RADICE / "docs/stato-reale/00-ESAME.md"
DOCS = RADICE / "docs/stato-reale"

CONSUMATORI = {
    "REPORT-30-08-lo-stato-vero-del-prodotto.md": (8, 30),
    "quadro-decisione-versione-30-08.md": (8, 30),
    "punto-del-mattino-31-08.md": (8, 31),
    "le-quattro-promesse-sulle-porte-degli-agenti.md": (8, 31),
}

CELLA = re.compile(r"^\| ((?:LANT|W\d)-\d+[a-z]?) \|")
RIF = re.compile(r"\b((?:LANT|W\d)-\d+[a-z]?)\b")
DATA = re.compile(r"\b(\d{2})/(\d{2})\b")


def main() -> int:
    if not ESAME.exists():
        print("  registro non trovato (esegui dalla radice del repo)")
        return 2

    celle = {}
    for r in ESAME.read_text(encoding="utf-8").splitlines():
        m = CELLA.match(r)
        if m:
            celle[m.group(1)] = r

    citate: dict[str, set[str]] = {}
    for nome in CONSUMATORI:
        p = DOCS / nome
        if not p.exists():
            print(f"  ⚠️ consumatore assente: {nome}")
            continue
        for i in RIF.findall(p.read_text(encoding="utf-8")):
            citate.setdefault(i, set()).add(nome)

    vive = {i: d for i, d in citate.items() if i in celle}
    print(f"  {len(vive)} celle load-bearing · {len(citate)-len(vive)} riferimenti a celle inesistenti\n")

    dopo, prima, senza = [], [], []
    for cid, docs in sorted(vive.items()):
        #: ⚠️ `10/11` nel testo era «10 SU 11», una frazione, non il 10 novembre:
        #: il limite che avevo dichiarato copriva le date citate per altro motivo,
        #: NON le frazioni — un falso positivo di classe che non avevo previsto.
        #: Il progetto vive fra luglio e settembre: fuori da li' e' quasi certo
        #: che sia un rapporto. Restringere e' arbitrario e lo dichiaro, ma
        #: sbaglia meno del contare qualsiasi coppia di numeri come una data.
        date = [(int(mm), int(gg)) for gg, mm in DATA.findall(celle[cid])
                if 7 <= int(mm) <= 9 and 1 <= int(gg) <= 31]
        if not date:
            senza.append(cid)
            continue
        ultima = max(date)
        soglia = min(CONSUMATORI[d] for d in docs)
        (dopo if ultima > soglia else prima).append((cid, ultima, sorted(docs)[0][:26]))

    print(f"  🔴 revisionate DOPO il documento che le cita: {len(dopo)}")
    for cid, (mm, gg), d in dopo:
        print(f"       {cid:<10} ultima data nel testo {gg:02d}/{mm:02d}  ·  citata da {d}")
    print(f"\n  🟢 nessuna revisione successiva: {len(prima)}")
    print(f"  ⚪ nessuna data nel testo (non giudicabili cosi'): {len(senza)}"
          f"  {', '.join(senza[:10])}")
    print("\n  ⇒ i 🔴 sono POSTI DOVE GUARDARE, non errori accertati: la data nel")
    print("    testo puo' essere citata per altro. Il numero che vale e' il 🟢.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
