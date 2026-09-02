"""Anello ① — CHI SONO I 61 veri che il moat giudica falsita' piene (score < 5).

Offline sul dump `punteggi_heldout.jsonl` (600 claim, commit eaf32209, giudice
CARICATO: judge_state=ready dopo 24,3s; controlli accesi 260/300 falsi fermati e
0/600 senza punteggio). Zero carichi del giudice.

O1 — LA LEZIONE ESISTEVA GIA', e questo banco parte da li':
`benchmark/quale_popolazione_e_sana.py:147` — «veri persi, perche' li' la
sovrapposizione claim/fonte predice la classe al 93%».

PREDIZIONE PUBBLICATA PRIMA (canale 02/09 17:2xZ, msg 71b6f24adf165a0c):
  · PRINCIPALE — la classe e' la SOVRAPPOSIZIONE LESSICALE BASSA fra claim e
    source. Misura: Jaccard sui token di contenuto (>=4 lettere, minuscolo).
    Predetto: MEDIANA dei veri score<5 <= META di quella dei veri ammessi.
    FALSIFICATA se le due mediane differiscono di meno del 20% relativo.
  · CONTRO (a) lunghezza source / troncamento a 400: predetto NON dominante.
  · CONTRO (b) presenza di numeri: predetto non discriminante.
  · CONTRO (c) kind/category: predetta concentrazione DEBOLE.
  · LIMITE dichiarato prima: la LINGUA non e' misurabile — TruthfulQA e' tutto
    inglese. Chi vuole quel campo deve cambiare popolazione.

CONTROLLO CHE DEVE ACCENDERSI: i FALSI ammessi (score >= 40) devono avere una
sovrapposizione ALTA. Se anche loro l'hanno bassa, la sovrapposizione non
discrimina niente e il numero principale non va usato.
"""
import io
import json
import re
import sys
from collections import Counter

DUMP = "punteggi_heldout.jsonl"
DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
TOKEN = re.compile(r"[a-zàèéìòù]{4,}")
NUMERO = re.compile(r"\d")


def toks(s):
    return set(TOKEN.findall((s or "").lower()))


def jac(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


def mediana(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0.0


dump = {json.loads(x)["i"]: json.loads(x)
        for x in io.open(DUMP, encoding="utf-8") if x.strip()}
dati = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
for i, r in enumerate(dati, 1):
    r["i"] = i
    d = dump.get(i, {})
    r["score"] = d.get("score")
    r["ov"] = jac(r.get("claim"), r.get("source"))

veri = [r for r in dati if r["label"] == 1 and r["score"] is not None]
bassi = [r for r in veri if r["score"] < 5]
ammessi = [r for r in veri if r["score"] >= 40]
falsi_amm = [r for r in dati
             if r["label"] == 0 and r["score"] is not None and r["score"] >= 40]
print(f"  veri {len(veri)} · di cui score<5 {len(bassi)} · ammessi(>=40) {len(ammessi)}")
print(f"  falsi ammessi (>=40): {len(falsi_amm)}")

# ── CONTROLLO: la sovrapposizione discrimina? ──────────────────────────────
m_fa = mediana([r["ov"] for r in falsi_amm])
m_am = mediana([r["ov"] for r in ammessi])
print(f"\n  CONTROLLO — mediana sovrapposizione:")
print(f"    veri AMMESSI   {m_am:.3f}")
print(f"    falsi AMMESSI  {m_fa:.3f}")
if m_am <= 0:
    print("  CONTROLLO SPENTO: i veri ammessi hanno sovrapposizione nulla")
    sys.exit(1)

# ── PREDIZIONE PRINCIPALE ─────────────────────────────────────────────────
m_ba = mediana([r["ov"] for r in bassi])
rel = (m_am - m_ba) / m_am * 100 if m_am else 0
print(f"\n  == PREDIZIONE PRINCIPALE — sovrapposizione claim/source ==")
print(f"    veri con score<5 : mediana {m_ba:.3f}")
print(f"    veri ammessi     : mediana {m_am:.3f}")
print(f"    differenza relativa: {rel:.1f}%")
if m_ba <= m_am / 2:
    esito = "REGGE (mediana <= meta')"
elif rel < 20:
    esito = "FALSIFICATA (differenza < 20% relativo)"
else:
    esito = "PARZIALE (differenza c'e' ma non e' meta')"
print(f"    => {esito}")

# ── CONTRO-IPOTESI ────────────────────────────────────────────────────────
print(f"\n  == CONTRO-IPOTESI ==")
ls_ba = mediana([len(r.get("source") or "") for r in bassi])
ls_am = mediana([len(r.get("source") or "") for r in ammessi])
tr_ba = sum(1 for r in bassi if len(r.get("source") or "") > 400)
tr_am = sum(1 for r in ammessi if len(r.get("source") or "") > 400)
print(f"    (a) lunghezza source  mediana: score<5 {ls_ba:.0f} · ammessi {ls_am:.0f}")
print(f"        source oltre 400 char (span TRONCATO): score<5 {tr_ba}/{len(bassi)}"
      f" · ammessi {tr_am}/{len(ammessi)}")
n_ba = sum(1 for r in bassi if NUMERO.search(r.get("claim") or ""))
n_am = sum(1 for r in ammessi if NUMERO.search(r.get("claim") or ""))
print(f"    (b) claim con NUMERI: score<5 {n_ba}/{len(bassi)}"
      f" ({100*n_ba/len(bassi):.0f}%) · ammessi {n_am}/{len(ammessi)}"
      f" ({100*n_am/len(ammessi):.0f}%)")
ck = Counter(r.get("kind") for r in bassi)
cc = Counter(r.get("category") for r in bassi)
print(f"    (c) kind dei 61: {dict(ck)}")
print(f"        categorie distinte fra i {len(bassi)}: {len(cc)}"
      f" · le 5 piu' numerose: {cc.most_common(5)}")
top2 = sum(n for _, n in cc.most_common(2))
print(f"        quota nelle 2 categorie maggiori: {top2}/{len(bassi)}"
      f" = {100*top2/len(bassi):.0f}%  (concentrazione)")

# ── i piu' bassi, per guardarli ───────────────────────────────────────────
print(f"\n  I SEI CON SOVRAPPOSIZIONE PIU' BASSA (score<5):")
for r in sorted(bassi, key=lambda r: r["ov"])[:6]:
    print(f"    ov={r['ov']:.2f} score={r['score']:.1f}  claim: {r['claim'][:64]}")
    print(f"                          source: {(r['source'] or '')[:64]}")
sys.exit(0)
