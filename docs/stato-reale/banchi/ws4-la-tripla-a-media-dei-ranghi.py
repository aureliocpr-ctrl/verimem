# -*- coding: utf-8 -*-
"""L'ENSEMBLE A TRE — e il TETTO, che e' la domanda vera (mandato @lead-audit 21:10).

Il lead chiede coppie e tripla con media, media dei ranghi e max, e «la colonna che
conta: quanti dei 61 recupera ciascuna combinazione senza far salire i falsi».

MA ENUMERARE REGOLE NON RISPONDE ALLA DOMANDA. Se la media non recupera e il max
nemmeno, resta sempre il dubbio «forse un'altra regola si'». Allora oltre alle
regole chieste misuro IL TETTO: la MIGLIORE combinazione lineare dei tre
punteggi, cercata su una griglia di pesi CALIBRATA SUGLI STESSI DATI — cioe'
ottimistica per costruzione, perche' sceglie i pesi conoscendo gia' le risposte.
Se nemmeno il tetto recupera i 61 a pari falsi, la conclusione vale per QUALSIASI
regola lineare, incluse quelle che nessuno ha ancora provato.

I DATI: i punteggi di @ws3 sono versionati in `banchi/_ws3_curva_scores.json`
(`giudice` = il nostro gate 0-100, `minicheck`), i miei di FactCG stanno in
`factcg_heldout.jsonl`.
CONTROLLO DI ALLINEAMENTO, obbligatorio: `giudice` di @ws3 e il mio `score` sono
LO STESSO giudice sugli STESSI claim, quindi i valori devono COINCIDERE. Se non
coincidono i suoi array non sono nel mio ordine e ogni numero sotto e' rumore.

🔮 PREDIZIONE, scritta PRIMA di eseguire (02/09 21:16):
  ① la migliore combinazione a tre ferma fra l'88% e il 91% dei falsi a
     iso-recall (oggi: nostro 86,7 · +FactCG 88,3 · +MiniCheck 87,3)
  ② NESSUNA combinazione recupera piu' di 5 dei 61 veri sul fondo tenendo i
     falsi fermati >= 86,7%
  ③ IL TETTO (combinazione lineare ottimizzata sugli stessi dati) non supera
     10/61
  ④ RAGIONE: sui 61 il nostro punteggio e' ~0 e i due giudici esterni li fondano
     INSIEME ai falsi vicini — l'AUROC di FactCG ristretto a quella popolazione
     e' 0,715-0,723, piu' basso del suo 0,743 globale (W7-127).
  ⑤ FALSIFICATA se una qualunque combinazione recupera >= 10/61 tenendo i falsi
     fermati >= 86,7%.
"""
import io
import json

REPO = "C:/Users/aurel/Code/HippoAgent/"
S = ("C:/Users/aurel/AppData/Local/Temp/claude/"
     "C--Users-aurel-Desktop-ProgettiAI/"
     "78ba9444-dd97-498f-bd48-07ca991638a4/scratchpad/")

pu = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "wt_base/punteggi_heldout.jsonl", encoding="utf-8") if x.strip()}
fa = {json.loads(x)["i"]: json.loads(x)
      for x in io.open(S + "wt_base/factcg_heldout.jsonl", encoding="utf-8") if x.strip()}
ws3 = json.load(io.open(REPO + "docs/stato-reale/banchi/_ws3_curva_scores.json",
                        encoding="utf-8"))["truthfulqa-600"]

ordine = sorted(pu)
veri_i = [i for i in ordine if pu[i]["label"] == 1]
falsi_i = [i for i in ordine if pu[i]["label"] == 0]

# ── CONTROLLO DI ALLINEAMENTO ───────────────────────────────────────────
mie_p = [pu[i].get("score") or 0.0 for i in veri_i]
mie_n = [pu[i].get("score") or 0.0 for i in falsi_i]
ug = (sum(1 for a, b in zip(mie_p, ws3["giudice"]["pos"]) if abs(a - b) < 0.01)
      + sum(1 for a, b in zip(mie_n, ws3["giudice"]["neg"]) if abs(a - b) < 0.01))
print(f"  CONTROLLO ALLINEAMENTO: {ug}/600 valori del giudice identici"
      f"   {'ACCESO' if ug > 570 else 'SPENTO — mi fermo'}")
if ug <= 570:
    raise SystemExit(1)

# i tre punteggi, tutti in 0-1, per ogni claim
P = {}
for k, i in enumerate(veri_i):
    P[i] = {"nostro": ws3["giudice"]["pos"][k] / 100.0,
            "mini": ws3["minicheck"]["pos"][k],
            "factcg": fa[i]["p"][1], "label": 1}
for k, i in enumerate(falsi_i):
    P[i] = {"nostro": ws3["giudice"]["neg"][k] / 100.0,
            "mini": ws3["minicheck"]["neg"][k],
            "factcg": fa[i]["p"][1], "label": 0}

i61 = [i for i in veri_i if (pu[i].get("score") or 0) < 5 and pu[i].get("fermato")]
BERSAGLIO = 88
BASE_FF = 260


def ranghi(campo):
    """rango normalizzato 0-1 (1 = punteggio piu' alto)."""
    o = sorted(P, key=lambda i: P[i][campo])
    return {i: k / (len(o) - 1) for k, i in enumerate(o)}


R = {c: ranghi(c) for c in ("nostro", "mini", "factcg")}


def valuta(punteggio):
    """A PARI veri persi: falsi fermati e quanti dei 61 sono recuperati."""
    o = sorted(veri_i, key=punteggio)
    s = punteggio(o[BERSAGLIO - 1]) + 1e-12
    ff = sum(1 for i in falsi_i if punteggio(i) < s)
    rec = sum(1 for i in i61 if punteggio(i) >= s)
    return ff, rec


REGOLE = []
for nome, campi in (("giudice+FactCG", ("nostro", "factcg")),
                    ("giudice+MiniCheck", ("nostro", "mini")),
                    ("giudice+Mini+FactCG", ("nostro", "mini", "factcg"))):
    REGOLE.append((nome + " · media", lambda i, c=campi: sum(P[i][x] for x in c) / len(c)))
    REGOLE.append((nome + " · ranghi", lambda i, c=campi: sum(R[x][i] for x in c) / len(c)))
    REGOLE.append((nome + " · max", lambda i, c=campi: max(P[i][x] for x in c)))

print(f"\n  {'combinazione':<32} {'falsi fermati':>15} {'dei 61':>9}")
print(f"  {'il nostro giudice da solo':<32} {BASE_FF:>4}/300 {100*BASE_FF/300:>6.1f}%"
      f" {0:>6}/61")
for nome, f in REGOLE:
    ff, rec = valuta(f)
    segno = "🟢" if ff >= BASE_FF else "  "
    print(f"  {nome:<32} {ff:>4}/300 {100*ff/300:>6.1f}% {rec:>6}/61 {segno}")

# ── IL TETTO: la migliore combinazione lineare, calibrata sui dati stessi ──
print("\n  == IL TETTO: migliore combinazione lineare (pesi scelti CONOSCENDO le"
      " risposte, quindi ottimistica) ==")
migl_ff = (-1, None)
migl_rec = (-1, None)
passo = 0.1
w = 0.0
combinazioni = []
n = int(1 / passo) + 1
for a in range(n):
    for b in range(n - a):
        c = n - 1 - a - b
        pesi = (a * passo, b * passo, c * passo)
        if sum(pesi) < 0.99:
            continue
        f = (lambda i, p=pesi: p[0] * P[i]["nostro"] + p[1] * P[i]["mini"]
             + p[2] * P[i]["factcg"])
        ff, rec = valuta(f)
        combinazioni.append((pesi, ff, rec))
        if ff > migl_ff[0]:
            migl_ff = (ff, pesi, rec)
        if rec > migl_rec[0] and ff >= BASE_FF:
            migl_rec = (rec, pesi, ff)
print(f"    combinazioni provate: {len(combinazioni)}  (pesi su nostro/mini/factcg)")
print(f"    massimo FALSI FERMATI: {migl_ff[0]}/300 = {100*migl_ff[0]/300:.1f}%"
      f"  pesi {tuple(round(x,1) for x in migl_ff[1])}  · dei 61 ne recupera {migl_ff[2]}")
if migl_rec[1] is None:
    print("    massimo RECUPERATI tenendo i falsi >= 86,7%: NESSUNA combinazione ci arriva")
    tetto = 0
else:
    tetto = migl_rec[0]
    print(f"    massimo RECUPERATI tenendo i falsi >= 86,7%: {tetto}/61"
          f"  pesi {tuple(round(x,1) for x in migl_rec[1])}"
          f"  (falsi {migl_rec[2]}/300)")

pf = 100 * migl_ff[0] / 300
print("\n  == I VERDETTI, col vincolo nel codice ==")
print(f"    ① miglior tripla fra 88 e 91%: {'REGGE' if 88 <= pf <= 91 else 'FALSIFICATA'}"
      f"  ({pf:.1f}%)")
print(f"    ③ il TETTO non supera 10/61: {'REGGE' if tetto <= 10 else 'FALSIFICATA'}"
      f"  ({tetto}/61)")
print(f"    ⑤ FALSIFICATA se una combinazione recupera >=10/61 coi falsi >=86,7%:"
      f"  {'SI, falsificata' if tetto >= 10 else 'no'}")
