"""T1.1 — la media semplice resta ≥ del migliore singolo A TUTTE LE SOGLIE?

    python docs/stato-reale/banchi/ws3-T11-la-media-regge-a-tutte-le-soglie.py

⚡ COSTO ZERO: nessun modello, nessun caricamento, nessuna inferenza. Solo
aritmetica su `_ws3_curva_scores.json` (40 KB), gia' prodotto il 02/09 alle
20:30. Scritto durante il fermo-carico: e' l'unico pezzo del giudice doppio
che si puo' misurare senza accendere niente.

PERCHE' SERVE. La decisione «giudice doppio in 0.8.0» poggia su **un punto per
banco**: la media semplice non sta sotto il migliore singolo a **29,3%** di veri
persi su TruthfulQA e a **19,0%** su HaluEval. Ma una combinazione che vince in
un punto **puo' perdere altrove**, e il punto di lavoro del prodotto non e'
detto che resti quello. Qui si guarda **tutta la curva**: per ogni quota di veri
persi da 5% a 60%, quanti falsi ferma ciascuna combinazione.

IL CRITERIO, dichiarato prima di guardare i numeri: la media «regge» se **non
sta MAI sotto il migliore dei due sistemi singoli** oltre il rumore di un caso
(1/300 = 0,33 punti su TruthfulQA, 1/200 = 0,5 su HaluEval). Se sta sotto anche
in un solo punto, va detto DOVE — perche' quello e' il regime in cui il giudice
doppio sarebbe peggiore di uno dei due da solo.

🔮 PREDIZIONE, depositata prima di eseguire: la media resta ≥ **su almeno il 90%
delle soglie** di entrambi i banchi, e dove cede lo fa **a quote basse** di veri
persi (< 15%), dove la soglia taglia sulla coda e pochi casi spostano molto.
🔴 COME MUORE: se cede su un intervallo ampio o alle quote centrali (20-35%,
dove il prodotto lavora), l'ensemble non e' la cura semplice che sembra.
"""
import json
from pathlib import Path

SCORES = Path(__file__).resolve().parent / "_ws3_curva_scores.json"
QUOTE = [round(0.05 + 0.05 * i, 2) for i in range(12)]      # 0,05 .. 0,60


def normalizza(v):
    lo, hi = min(v), max(v)
    return [0.5] * len(v) if hi == lo else [(x - lo) / (hi - lo) for x in v]


def ranghi(v):
    ordine = sorted(range(len(v)), key=lambda i: v[i])
    fuori = [0.0] * len(v)
    i = 0
    while i < len(ordine):
        j = i
        while j + 1 < len(ordine) and v[ordine[j + 1]] == v[ordine[i]]:
            j += 1
        for k in range(i, j + 1):
            fuori[ordine[k]] = (i + j) / 2.0 / max(1, len(v) - 1)
        i = j + 1
    return fuori


def iso(pos, neg, quota):
    """Falsi fermati quando si accetta di perdere `quota` dei veri."""
    ordinati = sorted(pos)
    idx = min(len(ordinati) - 1, max(0, int(round(quota * len(ordinati)))))
    s = ordinati[idx]
    return sum(1 for n in neg if n < s) / len(neg)


dati = json.loads(SCORES.read_text(encoding="utf-8"))
print("LA MEDIA REGGE A TUTTE LE SOGLIE? — costo zero, punteggi del 02/09 20:30\n")

for nome, blocco in dati.items():
    mc, gd = blocco["minicheck"], blocco["giudice"]
    n_pos = len(mc["pos"])
    mc_n = normalizza(mc["pos"] + mc["neg"])
    gd_n = normalizza(gd["pos"] + gd["neg"])
    mc_r = ranghi(mc["pos"] + mc["neg"])
    gd_r = ranghi(gd["pos"] + gd["neg"])
    comb = {
        "MiniCheck": mc_n,
        "giudice": gd_n,
        "media": [(a + b) / 2 for a, b in zip(mc_n, gd_n)],
        "ranghi": [(a + b) / 2 for a, b in zip(mc_r, gd_r)],
    }
    rumore = 1.0 / len(mc["neg"])          # un caso solo

    print("=" * 72)
    print(f"{nome}   (rumore di un caso = {100 * rumore:.2f} punti)\n")
    print("  %-8s %10s %9s %9s %9s   %s"
          % ("quota", "MiniCheck", "giudice", "MEDIA", "ranghi", "media vs migliore"))
    sotto_media, sotto_ranghi = [], []
    for q in QUOTE:
        v = {k: iso(vv[:n_pos], vv[n_pos:], q) for k, vv in comb.items()}
        migliore = max(v["MiniCheck"], v["giudice"])
        d_media = v["media"] - migliore
        d_ranghi = v["ranghi"] - migliore
        if d_media < -rumore:
            sotto_media.append((q, 100 * d_media))
        if d_ranghi < -rumore:
            sotto_ranghi.append((q, 100 * d_ranghi))
        segno = ("✅" if d_media >= -rumore else "🔴")
        print("  %-8.0f%% %9.1f%% %8.1f%% %8.1f%% %8.1f%%   %+.1f %s"
              % (100 * q, 100 * v["MiniCheck"], 100 * v["giudice"],
                 100 * v["media"], 100 * v["ranghi"], 100 * d_media, segno))

    print(f"\n  MEDIA sotto il migliore singolo: {len(sotto_media)}/{len(QUOTE)} soglie"
          + (f"  -> {[(f'{100*q:.0f}%', f'{d:+.1f}') for q, d in sotto_media]}"
             if sotto_media else "  -> mai"))
    print(f"  RANGHI sotto il migliore singolo: {len(sotto_ranghi)}/{len(QUOTE)} soglie"
          + (f"  -> {[(f'{100*q:.0f}%', f'{d:+.1f}') for q, d in sotto_ranghi]}"
             if sotto_ranghi else "  -> mai"))
    print()

print("predizione: media >= su almeno il 90% delle soglie; se cede, a quote < 15%")
print("il prodotto lavora attorno al 20-35% di veri persi: e' li' che conta")
