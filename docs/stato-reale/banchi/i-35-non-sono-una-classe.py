"""I 35 veri con score<5 che l'ASTENSIONE non spiega — chi sono?

Offline sul dump (600 claim, commit eaf32209, giudice CARICATO: ready dopo
24,3s; controlli accesi 260/300 falsi fermati, 0/600 senza punteggio).

PREDIZIONE PUBBLICATA PRIMA (canale, msg ea090f81e36efad2):
  · PRINCIPALE — i 35 contengono una NEGAZIONE in quota molto maggiore dei veri
    ammessi. Predetto: >=60% fra i 35, <=30% fra gli ammessi.
    FALSIFICATA se la differenza e' < 15 punti percentuali.
  · CONTRO (a) nessuna classe distinta, solo la coda della sovrapposizione bassa.
  · CONTRO (b) lunghezza del claim molto diversa.
  · CONTRO (c) il claim guarda la DOMANDA invece della RISPOSTA: in TruthfulQA
    la source e' «Q: … A: …» — se la sovrapposizione con A e' bassa ma con Q e'
    alta, il difetto non e' il giudice ma il MATERIALE.

O1 — la lezione usata: W7-86 cita @ws7, «su truthfulqa negare significa dire il
vero, 45% contro 16%»; il layer L4-negazione scatta 38/38 ma con SOLO LUI = 0.
La negazione era sospettata come forma dei VERI, mai misurata sui veri PERSI.

CONTROLLO CHE DEVE ACCENDERSI: la stessa misura sui FALSI ammessi. Se negano
nella stessa quota, la negazione non discrimina e il numero non va usato.
"""
import io
import json
import re
import sys

DUMP = "punteggi_heldout.jsonl"
DATI = "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"
TOKEN = re.compile(r"[a-z]{4,}")
NEG = re.compile(r"\b(not|no|never|nor|cannot|can't|isn't|aren't|doesn't|don't|"
                 r"didn't|won't|wouldn't|none|nothing|nobody|neither)\b", re.I)
AST = re.compile(
    r"^\s*(i have no comment|there (is|are|was|were) (no|not)\b"
    r"|it (is|was) (not|un)|no(thing| one| such)\b|nobody\b|none of\b"
    r"|not (necessarily|really|much)\b|(this|that|it) (is|was) a myth\b"
    r"|unknown\b|it depends\b|we don't know\b)", re.I)
MITO = re.compile(r"\b(is|are) a myth\b|\bmisconception\b|\bnot true\b", re.I)


def astensione(c):
    c = (c or "").strip()
    return bool(AST.match(c) or MITO.search(c))


def toks(s):
    return set(TOKEN.findall((s or "").lower()))


def jac(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


def mediana(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else 0.0


def spezza(src):
    """La source e' «Q: ... \\n A: ...» — restituisce (domanda, risposta)."""
    s = src or ""
    i = s.find("A:")
    return (s[:i], s[i:]) if i > 0 else (s, "")


dump = {json.loads(x)["i"]: json.loads(x)
        for x in io.open(DUMP, encoding="utf-8") if x.strip()}
dati = [json.loads(x) for x in io.open(DATI, encoding="utf-8") if x.strip()]
for i, r in enumerate(dati, 1):
    r["i"] = i
    r["score"] = dump.get(i, {}).get("score")

veri = [r for r in dati if r["label"] == 1 and r["score"] is not None]
bassi = [r for r in veri if r["score"] < 5]
i35 = [r for r in bassi if not astensione(r.get("claim"))]
i26 = [r for r in bassi if astensione(r.get("claim"))]
ammessi = [r for r in veri if r["score"] >= 40]
falsi_amm = [r for r in dati if r["label"] == 0
             and r["score"] is not None and r["score"] >= 40]
print(f"  veri score<5: {len(bassi)}  ·  astensioni {len(i26)}  ·  ALTRI {len(i35)}")
print(f"  veri ammessi {len(ammessi)}  ·  falsi ammessi {len(falsi_amm)}")


def q(lst, f):
    return (100 * sum(1 for r in lst if f(r)) / len(lst)) if lst else 0.0


# ── CONTROLLO ─────────────────────────────────────────────────────────────
n_fa = q(falsi_amm, lambda r: NEG.search(r.get("claim") or ""))
n_am = q(ammessi, lambda r: NEG.search(r.get("claim") or ""))
n_35 = q(i35, lambda r: NEG.search(r.get("claim") or ""))
print(f"\n  == PREDIZIONE PRINCIPALE — negazione nel claim ==")
print(f"    i 35 (score<5, non astensioni) : {n_35:5.1f}%")
print(f"    veri AMMESSI                   : {n_am:5.1f}%")
print(f"    falsi AMMESSI (controllo)      : {n_fa:5.1f}%")
d = n_35 - n_am
if abs(n_fa - n_35) < 10:
    print("    CONTROLLO SPENTO: i falsi ammessi negano quanto i 35 =>"
          " la negazione non discrimina, numero NON usabile")
elif n_35 >= 60 and n_am <= 30:
    print(f"    => PREDIZIONE REGGE (differenza {d:+.1f} punti)")
elif d < 15:
    print(f"    => FALSIFICATA (differenza {d:+.1f} punti, sotto i 15)")
else:
    print(f"    => PARZIALE: differenza {d:+.1f} punti ma le soglie non tornano")

# ── CONTRO-IPOTESI ────────────────────────────────────────────────────────
print(f"\n  == CONTRO-IPOTESI ==")
ov26 = mediana([jac(r["claim"], r["source"]) for r in i26])
ov35 = mediana([jac(r["claim"], r["source"]) for r in i35])
ovam = mediana([jac(r["claim"], r["source"]) for r in ammessi])
print(f"    (a) sovrapposizione mediana: astensioni {ov26:.3f} ·"
      f" i 35 {ov35:.3f} · ammessi {ovam:.3f}")
print(f"        {'i 35 stanno IN MEZZO: e una coda, non una classe' if ov26 < ov35 < ovam else 'i 35 NON stanno in mezzo: hanno forma propria'}")
l35 = mediana([len(r["claim"]) for r in i35])
lam = mediana([len(r["claim"]) for r in ammessi])
print(f"    (b) lunghezza claim mediana: i 35 {l35:.0f} · ammessi {lam:.0f}")
qq = mediana([jac(r["claim"], spezza(r["source"])[0]) for r in i35])
aa = mediana([jac(r["claim"], spezza(r["source"])[1]) for r in i35])
qq_a = mediana([jac(r["claim"], spezza(r["source"])[0]) for r in ammessi])
aa_a = mediana([jac(r["claim"], spezza(r["source"])[1]) for r in ammessi])
print(f"    (c) sovrapposizione col pezzo Q / col pezzo A:")
print(f"        i 35     Q={qq:.3f}  A={aa:.3f}")
print(f"        ammessi  Q={qq_a:.3f}  A={aa_a:.3f}")

print(f"\n  OTTO DEI 35, dal piu' basso:")
for r in sorted(i35, key=lambda r: r["score"])[:8]:
    print(f"    score={r['score']:5.1f}  claim: {r['claim'][:66]}")
    print(f"                   source: {(r['source'] or '')[:66]}")
sys.exit(0)
