"""T-MAP-11, seconda meta': la soglia 40 dell'ingest separa i fatti DETTI dalle
invenzioni PLAUSIBILI?

PREDIZIONE, scritta prima di eseguire (post di stand-up delle 22:52 sul canale):
la soglia da sola NON separa -> sovrapposizione fra le due popolazioni > 0.
Se la sovrapposizione e' ZERO la predizione e' falsa e la cura e' un numero.

Popolazioni (dati che NON abbiamo scritto noi: HaluEval QA, MIT, RUCAIBox —
benchmark/data/external/README.md; disciplina del repo: `dev` si ispeziona,
`heldout` si ESEGUE e non si legge):
  NEGATIVI  = `hallucinated_answer`: frase plausibile costruita sul contesto e
              che il contesto NON dice. E' esattamente il mio caso «il capannone
              12 e' stato venduto nel 2019».
  POSITIVI  = la prima frase del `knowledge`: un fatto che la fonte dice ALLA
              LETTERA. E' il caso PIU' FACILE per il giudice, quindi la
              separabilita' che misuro qui e' un LIMITE SUPERIORE ottimistico:
              se anche cosi' le due popolazioni si sovrappongono, a maggior
              ragione si sovrappongono con positivi parafrasati. La stima e'
              scelta CONTRO la mia tesi apposta.

Livello dichiarato: la FUNZIONE `_grounds`/`try_local_score`, non la porta —
qui misuro il GIUDICE, non il percorso (il percorso e' il test alla porta,
commit ab8e8e6f).

    python ws3_soglia_ingest.py <wt> --split dev --n 100
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

SOGLIA_OGGI = 40.0


def prima_frase(testo: str, minimo: int = 40) -> str | None:
    pezzi = re.split(r"(?<=[.!?])\s+", (testo or "").strip())
    for p in pezzi:
        p = p.strip()
        if len(p) >= minimo:
            return p
    return None


def auroc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney U / (n_pos*n_neg): la probabilita' che un positivo preso a
    caso prenda piu' di un negativo preso a caso. 0.5 = il giudice non sa."""
    if not pos or not neg:
        return float("nan")
    tutti = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranghi: dict[int, float] = {}
    i = 0
    somma_pos = 0.0
    while i < len(tutti):
        j = i
        while j + 1 < len(tutti) and tutti[j + 1][0] == tutti[i][0]:
            j += 1
        rango_medio = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranghi[k] = rango_medio
            if tutti[k][1] == 1:
                somma_pos += rango_medio
        i = j + 1
    n1, n2 = len(pos), len(neg)
    u = somma_pos - n1 * (n1 + 1) / 2.0
    return u / (n1 * n2)


def quantili(v: list[float]) -> str:
    if not v:
        return "(vuoto)"
    s = sorted(v)
    def q(p):
        return s[min(len(s) - 1, int(p * (len(s) - 1)))]
    return (f"min {s[0]:6.2f} · q10 {q(0.10):6.2f} · mediana {q(0.50):6.2f} · "
            f"q90 {q(0.90):6.2f} · max {s[-1]:6.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("wt")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()

    wt = pathlib.Path(a.wt).resolve()
    sys.path.insert(0, str(wt))
    from verimem.local_grounding import try_local_score  # noqa: E402

    campione = wt / "benchmark" / "data" / "external" / f"halueval_qa_{a.split}.jsonl"
    righe = [json.loads(x) for x in campione.read_text(encoding="utf-8").splitlines() if x.strip()]
    righe = righe[: a.n]
    print(f"== campione: {campione.name} · {len(righe)} item · soglia di oggi {SOGLIA_OGGI}")

    pos: list[float] = []
    neg: list[float] = []
    passati: list[tuple[float, str]] = []
    persi: list[tuple[float, str]] = []
    saltati = 0
    t0 = time.time()
    cut_config = None
    for r in righe:
        ctx = (r.get("knowledge") or "").strip()
        inv = (r.get("hallucinated_answer") or "").strip()
        det = prima_frase(ctx)
        if not ctx or not inv or not det:
            saltati += 1
            continue
        s_neg = try_local_score(ctx, inv)
        s_pos = try_local_score(ctx, det)
        if s_neg is None or s_pos is None:
            print("!! il giudice locale non e' disponibile: try_local_score -> None")
            print("   (fail-open: e' esattamente il caso in cui l'ingest ammette tutto)")
            return
        cut_config = s_neg[1]
        neg.append(float(s_neg[0]))
        pos.append(float(s_pos[0]))
        if float(s_neg[0]) >= SOGLIA_OGGI:
            passati.append((float(s_neg[0]), inv[:90]))
        if float(s_pos[0]) < SOGLIA_OGGI:
            persi.append((float(s_pos[0]), det[:90]))
    dt = time.time() - t0
    n = len(pos)
    if not n:
        print("nessuna coppia utilizzabile")
        return

    print(f"== tempo: {dt:.1f}s per {2*n} giudizi = {1000*dt/(2*n):.0f} ms per fatto"
          f" · saltati {saltati} · cut di config del giudice: {cut_config}")
    print(f"POSITIVI (la fonte lo dice alla lettera) n={n}: {quantili(pos)}")
    print(f"NEGATIVI (plausibile e non detto)      n={n}: {quantili(neg)}")
    print(f"AUROC positivi-vs-negativi: {auroc(pos, neg):.4f}")
    print(f">> ALLA SOGLIA DI OGGI ({SOGLIA_OGGI}): invenzioni AMMESSE "
          f"{len(passati)}/{n} = {100*len(passati)/n:.1f}% · "
          f"veri PERSI {len(persi)}/{n} = {100*len(persi)/n:.1f}%")
    sovrapposizione = sum(1 for v in neg if v >= min(pos)) if pos else 0
    print(f">> SOVRAPPOSIZIONE: il positivo piu' basso vale {min(pos):.2f}; "
          f"{sovrapposizione}/{n} negativi stanno sopra quel valore")
    print("== se la soglia fosse ...  (invenzioni fermate · veri persi)")
    for t in (40, 50, 60, 70, 80, 90, 95, 99):
        fermate = sum(1 for v in neg if v < t)
        persi_t = sum(1 for v in pos if v < t)
        print(f"   {t:5.1f} -> invenzioni fermate {fermate:4d}/{n} ({100*fermate/n:5.1f}%) · "
              f"veri persi {persi_t:4d}/{n} ({100*persi_t/n:5.1f}%)")
    if a.split == "dev":
        print("== le cinque invenzioni col punteggio piu' alto (solo su dev: heldout non si legge)")
        for s, t in sorted(passati, reverse=True)[:5]:
            print(f"   {s:6.2f}  {t}")
        print("== i cinque veri col punteggio piu' basso")
        for s, t in sorted(persi)[:5]:
            print(f"   {s:6.2f}  {t}")


if __name__ == "__main__":
    main()
