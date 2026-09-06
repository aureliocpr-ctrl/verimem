"""Il righello lessicale sul corpus VERO: quanti fermati dal moat portano parole che la fonte non ha?

Segue il banco delle negazioni (0c0714c5): sulle 5 coppie di stanotte la polarita'
pesava +0,1 e il lessico fuori fonte +95. Qui la stessa domanda sul corpus intero,
SENZA giudice: per ogni fatto con `grounding_span` (cio' che il giudice ha letto)
si misura la QUOTA DI PAROLE DI CONTENUTO DEL CLAIM ASSENTI DALLO SPAN, e si
confrontano ENTRAMBE le popolazioni — fermati dal moat (quarantined_by='moat') e
ammessi — e dentro i fermati, quelli con un negatore e quelli senza.

Righello: token alfabetici di almeno 4 lettere, minuscoli, meno una stoplist
corta; un token e' «presente» se lo span contiene lui o il suo prefisso di 5
lettere (assorbe le flessioni: invocazione/invocazioni). Quota = assenti/totale.
Il negatore si legge in DUE modi, e si stampano tutti e due: quello del prodotto
(negation_scope.e_un_claim_negativo, che non vede «nessun») e uno esteso
(+ nessun/nessuna/nessuno/mai/niente/nulla).

PREDIZIONI, depositate in questo commit PRIMA di eseguire (l'ora e' nel commit):
  P-L1  la quota mediana dei FERMATI e' almeno il doppio di quella degli AMMESSI.
        Se il rapporto e' sotto 1,5 il lessico fuori fonte non e' la firma del
        fermo sul corpus e il risultato delle 5 coppie non si generalizza.
  P-L2  l'AUROC della quota come separatore fermati/ammessi e' >= 0,75: un
        righello senza modello che «prevede» il verdetto e' il muro M5 misurato.
        Sotto 0,65 il giudice fa qualcosa che il lessico non spiega.
  P-L3  fra i FERMATI, la quota mediana con negatore NON supera quella senza di
        piu' di 0,10: la polarita' non aggiunge lessico. Se la supera di 0,20 o
        piu', le negazioni cadono per un'altra strada.
Composizione per status stampata PRIMA di misurare (regola di casa: un rango
bimodale e' la firma di una popolazione mista). Store di Aurelio aperto SOLO in
lettura (mode=ro), nessuna scrittura, nessun modello caricato. Esecuzione: secondi.
"""
from __future__ import annotations

import re
import sqlite3
import sys

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
STOP = set("""
    della delle dello degli dalla dalle dallo dagli nella nelle nello negli sulla
    sulle sullo sugli come dopo prima anche solo sono stato stata stati state
    essere avere hanno viene vengono questo questa questi queste quello quella
    ogni tutti tutte with that this from into have been were will than then
    which there their they them what when where does
""".split())
_NEG_ESTESO = re.compile(r"(?<![\w-])(?:non|nessun[oa]?|mai|niente|nulla|ne')(?![-\w])", re.I)


def contenuto(testo: str) -> list[str]:
    return [t for t in re.findall(r"[a-zà-ÿ]{4,}", testo.lower()) if t not in STOP]


def quota_fuori_fonte(claim: str, span: str) -> float | None:
    parole = contenuto(claim)
    if not parole:
        return None
    s = span.lower()
    assenti = sum(1 for p in parole if p not in s and p[:5] not in s)
    return assenti / len(parole)


def mediana(v: list[float]) -> float:
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def quartili(v: list[float]) -> tuple[float, float, float]:
    v = sorted(v)
    n = len(v)
    return v[n // 4], mediana(v), v[(3 * n) // 4]


def auroc(pos: list[float], neg: list[float]) -> float:
    """Quota ALTA = fermato: la probabilita' che un fermato abbia quota maggiore di un ammesso."""
    vinte = sum(1.0 if p > q else 0.5 if p == q else 0.0 for p in pos for q in neg)
    return vinte / (len(pos) * len(neg))


def main() -> int:
    sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
    from verimem.negation_scope import e_un_claim_negativo as neg_prodotto

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("COMPOSIZIONE per status e quarantined_by (fatti con grounding_span, non superseded):")
    for st, qb, n in con.execute(
            "SELECT status, quarantined_by, COUNT(*) FROM facts "
            "WHERE superseded_by IS NULL AND grounding_span IS NOT NULL "
            "GROUP BY status, quarantined_by ORDER BY n DESC"):
        print(f"   {str(st):14s} {str(qb):16s} {n:6d}")
    righe = con.execute(
        "SELECT id, proposition, status, quarantined_by, grounding_score, grounding_span FROM facts "
        "WHERE superseded_by IS NULL AND grounding_span IS NOT NULL AND grounding_score IS NOT NULL"
    ).fetchall()

    fermati, ammessi = [], []
    ferm_neg_p, ferm_pos_p, ferm_neg_e, ferm_pos_e = [], [], [], []
    esempi_alti: list[tuple[float, str, str]] = []
    for fid, prop, st, qb, g, span in righe:
        q = quota_fuori_fonte(prop, span)
        if q is None:
            continue
        if st == "quarantined" and qb == "moat":
            fermati.append(q)
            (ferm_neg_p if neg_prodotto(prop) else ferm_pos_p).append(q)
            (ferm_neg_e if _NEG_ESTESO.search(prop) else ferm_pos_e).append(q)
            if q >= 0.5:
                esempi_alti.append((q, fid, prop[:90]))
        elif st != "quarantined":
            ammessi.append(q)
    print(f"\nrighe con span e punteggio: {len(righe)} · fermati dal moat: {len(fermati)} · ammessi: {len(ammessi)}")
    if len(fermati) < 20 or len(ammessi) < 20:
        print("popolazioni troppo piccole: NESSUN VERDETTO")
        return 1

    qf, qa = quartili(fermati), quartili(ammessi)
    print(f"quota fuori fonte — FERMATI  q1 {qf[0]:.2f}  mediana {qf[1]:.2f}  q3 {qf[2]:.2f}")
    print(f"quota fuori fonte — AMMESSI  q1 {qa[0]:.2f}  mediana {qa[1]:.2f}  q3 {qa[2]:.2f}")
    rapporto = qf[1] / qa[1] if qa[1] > 0 else float("inf")
    print(f"P-L1 rapporto delle mediane fermati/ammessi: {rapporto:.2f}  "
          f"{'REGGE (>= 2)' if rapporto >= 2 else ('🔴 FALSIFICATA (< 1,5)' if rapporto < 1.5 else 'indeciso')}")
    a = auroc(fermati, ammessi)
    print(f"P-L2 AUROC della quota come separatore: {a:.3f}  "
          f"{'REGGE (>= 0,75)' if a >= 0.75 else ('🔴 FALSIFICATA (< 0,65)' if a < 0.65 else 'indeciso')}")
    for nome, neg, pos in (("prodotto", ferm_neg_p, ferm_pos_p), ("esteso", ferm_neg_e, ferm_pos_e)):
        if neg and pos:
            d = mediana(neg) - mediana(pos)
            print(f"P-L3 fermati, negatore {nome:8s}: con {len(neg):4d} mediana {mediana(neg):.2f} · "
                  f"senza {len(pos):4d} mediana {mediana(pos):.2f} · differenza {d:+.2f}  "
                  f"{'REGGE (<= 0,10)' if d <= 0.10 else ('🔴 FALSIFICATA (>= 0,20)' if d >= 0.20 else 'indeciso')}")
    print(f"\nfermati con quota >= 0,50: {len(esempi_alti)}/{len(fermati)}; i primi 8 per quota:")
    for q, fid, prop in sorted(esempi_alti, reverse=True)[:8]:
        print(f"   {q:.2f} {fid} {prop}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
