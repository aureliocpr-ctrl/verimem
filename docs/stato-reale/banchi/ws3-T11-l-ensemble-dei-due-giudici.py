"""T1.1 — L'ENSEMBLE dei due giudici, a costo zero di addestramento.

    python docs/stato-reale/banchi/ws3-T11-l-ensemble-dei-due-giudici.py

Nessun modello viene rieseguito: i punteggi di **entrambi** i sistemi sui 1000
casi sono gia' salvati da `ws3-T11-la-curva-minicheck-contro-il-giudice.py`
(`_ws3_curva_scores.json`, 02/09 ore 20:30). Qui e' solo aritmetica.

QUATTRO COMBINAZIONI, sui punteggi normalizzati in [0,1]:
    media · media dei RANGHI · max · min
e per ciascuna la **iso-recall**: a pari veri persi del gate (29,3% su
TruthfulQA, 19,0% su HaluEval), quanti falsi ferma.

⚠️ LA NORMALIZZAZIONE NON E' NEUTRA. I due sistemi hanno scale diverse (MiniCheck
in [0,1], il giudice in [0,100]) **e distribuzioni diverse**: il giudice
ammassa i suoi verdetti agli estremi (91,8% oltre 99 o sotto 1, misurato sul
corpus). Una media su min-max sarebbe dominata dal sistema piu' "piatto", ed e'
il motivo per cui la **media dei RANGHI** e' la combinazione che il mandato
mette al centro: i ranghi tolgono la forma della distribuzione e lasciano solo
l'ordine.

I PUNTI DI PARTENZA, dalla curva:
    TruthfulQA   giudice 87,3%   MiniCheck 72,3%    divario 15 punti
    HaluEval     giudice 62,0%   MiniCheck 68,0%    divario  6 punti

🔮 PREDIZIONE depositata sul canale PRIMA di eseguire (02/09 20:42), e
**antitetica a quella del mandato** (che dava la media dei ranghi >= del
migliore su ENTRAMBI):
  ① media dei ranghi su TruthfulQA **SOTTO 87,3%** -> il mandato cade
  ② media dei ranghi su HaluEval **SOPRA 68,0%** -> li' il mandato regge
  ③ `max` perde meno veri e ferma meno falsi, `min` l'opposto: tarature, non
     ensemble migliori
  ④ correlazione di Spearman **> 0,6** su entrambi -> errori sovrapposti ->
     guadagno dell'ensemble **sotto i 5 punti ovunque**
🔴 COME MUORE LA MIA: se la media dei ranghi supera 87,3% su TruthfulQA, ho
torto e l'ensemble e' la cura che il mandato ipotizza.

⚠️ Cosa questo calcolo NON puo' dire: se l'ensemble regga **fuori** da questi
due banchi. Due dump non sono il mondo, e su questi due i verdetti erano
gia' OPPOSTI.
"""
import json
from pathlib import Path

SCORES = Path(__file__).resolve().parent / "_ws3_curva_scores.json"


def ranghi(valori):
    """Rango medio (0..1). I pari prendono il rango medio, o due punteggi
    identici — frequentissimi in un giudice che satura a 99 — riceverebbero
    ordini arbitrari e diversi fra i due sistemi."""
    ordine = sorted(range(len(valori)), key=lambda i: valori[i])
    fuori = [0.0] * len(valori)
    i = 0
    while i < len(ordine):
        j = i
        while j + 1 < len(ordine) and valori[ordine[j + 1]] == valori[ordine[i]]:
            j += 1
        medio = (i + j) / 2.0
        for k in range(i, j + 1):
            fuori[ordine[k]] = medio / max(1, len(valori) - 1)
        i = j + 1
    return fuori


def normalizza(valori):
    lo, hi = min(valori), max(valori)
    if hi - lo == 0:
        return [0.5] * len(valori)
    return [(v - lo) / (hi - lo) for v in valori]


def spearman(a, b):
    ra, rb = ranghi(a), ranghi(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(num / (da * db), 4) if da and db else None


def iso_recall(pos, neg, quota_persi):
    """A pari veri persi: soglia dal quantile dei positivi, poi conta i negativi."""
    if not pos or not neg:
        return None
    ordinati = sorted(pos)
    idx = min(len(ordinati) - 1, max(0, int(round(quota_persi * len(ordinati)))))
    soglia = ordinati[idx]
    return (sum(1 for n in neg if n < soglia) / len(neg),
            sum(1 for p in pos if p < soglia) / len(pos))


def auroc(pos, neg):
    if not pos or not neg:
        return None
    vinte = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(vinte / (len(pos) * len(neg)), 4)


dati = json.loads(SCORES.read_text(encoding="utf-8"))
GATE = {"truthfulqa-600": (0.293, 0.867), "halueval-400": (0.190, 0.550)}

print("L'ENSEMBLE DEI DUE GIUDICI — nessun modello rieseguito\n")

for nome, blocco in dati.items():
    mc, gd = blocco["minicheck"], blocco["giudice"]
    quota, gate_ff = GATE.get(nome, (0.2, 0.0))
    # un solo vettore per banco: prima i positivi, poi i negativi
    n_pos = len(mc["pos"])
    mc_tutti = mc["pos"] + mc["neg"]
    gd_tutti = gd["pos"] + gd["neg"]

    mc_n, gd_n = normalizza(mc_tutti), normalizza(gd_tutti)
    mc_r, gd_r = ranghi(mc_tutti), ranghi(gd_tutti)

    combinazioni = {
        "MiniCheck solo": mc_n,
        "giudice solo": gd_n,
        "media": [(a + b) / 2 for a, b in zip(mc_n, gd_n)],
        "media dei ranghi": [(a + b) / 2 for a, b in zip(mc_r, gd_r)],
        "max": [max(a, b) for a, b in zip(mc_n, gd_n)],
        "min": [min(a, b) for a, b in zip(mc_n, gd_n)],
    }

    print("=" * 74)
    print(f"{nome}   (n={blocco['n']}, iso-recall a {100 * quota:.1f}% veri persi)\n")
    print("  %-18s %14s %14s %9s" % ("combinazione", "FALSI fermati",
                                     "veri persi", "AUROC"))
    migliore_singolo = 0.0
    risultati = {}
    for etichetta, vett in combinazioni.items():
        pos, neg = vett[:n_pos], vett[n_pos:]
        res = iso_recall(pos, neg, quota)
        au = auroc(pos, neg)
        risultati[etichetta] = (res[0] if res else None, au)
        if etichetta in ("MiniCheck solo", "giudice solo") and res:
            migliore_singolo = max(migliore_singolo, res[0])
        print("  %-18s %13.1f%% %13.1f%% %9s"
              % (etichetta, 100 * res[0], 100 * res[1], au))

    print(f"\n  correlazione di Spearman fra i due punteggi: "
          f"{spearman(mc_tutti, gd_tutti)}")
    print(f"  migliore SINGOLO: {100 * migliore_singolo:.1f}%   "
          f"(gate dichiarato: {100 * gate_ff:.1f}%)")
    mr = risultati["media dei ranghi"][0]
    esito = ("≥ del migliore singolo ✅" if mr >= migliore_singolo
             else "SOTTO il migliore singolo 🔴")
    print(f"  ⇒ media dei ranghi {100 * mr:.1f}% — {esito}")
    print()

print("predizione del mandato: media dei ranghi >= migliore singolo su ENTRAMBI")
print("predizione mia:         SOTTO su TruthfulQA, SOPRA su HaluEval")
