"""`holographic_memory.py` (21) e `resonator_memory.py` (16): due memorie
**senza database** — un vettore aggregato e un codice, invece delle righe.

Sono le due parti più teoriche della mia porzione (Plate 1995, Frady 2020) e
proprio per questo la mappa deve dire **cosa reggono davvero**, non cosa citano:
  · `remember` + `recall` si provano sul giro completo — scrivo N coppie e
    guardo quante ne ritrovo, non se la funzione «gira»;
  · `contains` promette «False = certamente assente, True = probabilmente
    presente»: il lato che conta è il **False su una cosa mai messa**;
  · `save`/`load` si provano confrontando lo stato **dopo il giro su disco**.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-vett-"))
import numpy as np  # noqa: E402

from verimem import holographic_memory as HM  # noqa: E402
from verimem import resonator_memory as RS  # noqa: E402

print("=" * 74)
print("A. holographic_memory.py")
print("=" * 74)
print("_seed_from_text: deterministico?",
      HM._seed_from_text("capannone") == HM._seed_from_text("capannone"),
      "| diverso per testi diversi:",
      HM._seed_from_text("capannone") != HM._seed_from_text("canone"))
f1, f2 = HM._filler("capannone", 512), HM._filler("capannone", 512)
f3 = HM._filler("canone", 512)
print("_filler: stesso testo -> stesso vettore:", bool(np.allclose(f1, f2)),
      "| norma unitaria:", round(float(np.linalg.norm(f1)), 6),
      "| quasi ortogonale a un altro testo:", round(float(f1 @ f3), 4))
a, b = HM._filler("a", 256), HM._filler("b", 256)
legato = HM._circular_conv(a, b)
sciolto = HM._circular_corr(a, legato)
print("_circular_conv/_circular_corr: corr(a, conv(a,b)) somiglia a b?",
      "coseno =", round(float(sciolto @ b / (np.linalg.norm(sciolto) * np.linalg.norm(b))), 4))
sp = HM._circular_shift(a, 1)
print("_circular_shift(k=1): cambia il vettore:", not bool(np.allclose(sp, a)),
      "| norma conservata:", round(float(np.linalg.norm(sp)), 6))

print("\n_BloomFilter:")
bf = HM._BloomFilter(n_bits=1024, k=3)
bf.add("uno")
bf.add("due")
print("  'uno' dentro:", "uno" in bf, "| 'tre' (mai aggiunto):", "tre" in bf)
blob = bf.to_bytes()
bf2 = HM._BloomFilter.from_bytes(blob, 1024, 3)
print("  round-trip byte:", len(blob), "byte ·  'uno' ancora dentro:", "uno" in bf2)

print("\nHolographicMemory: il giro completo")
hm = HM.HolographicMemory(d=1024)
coppie = [("canone", "5900 euro"), ("consegna", "3 marzo"), ("indirizzo", "via Roma")]
for t, p in coppie:
    hm.remember(t, p)
print("  scritte", len(coppie), "coppie · stats:", {k: str(v)[:40] for k, v in hm.stats().items()})
ritrovate = 0
for t, p in coppie:
    r = hm.recall(t, top_k=1)
    primo = (r[0][0] if isinstance(r[0], (list, tuple)) else r[0]) if r else None
    ok = primo == p
    ritrovate += ok
    print(f"  recall({t!r}) -> {str(r)[:70]} · giusta: {ok}")
print("  >>> ritrovate", ritrovate, "su", len(coppie))
print("  contains(scritta):", hm.contains("canone", "5900 euro"),
      "| contains(MAI scritta):", hm.contains("canone", "9999 euro"),
      "(False = certamente assente)")
hm.forget("canone", "5900 euro")
print("  dopo forget('canone'): recall ->", str(hm.recall("canone", top_k=1))[:70])
p = tmp / "olo.bin"
scritto = hm.save(p)
hm2 = HM.HolographicMemory.load(p)
print("  save ->", scritto, "| load: stats uguali:",
      hm2.stats().get("n_cleanup") == hm.stats().get("n_cleanup"))

print("\n" + "=" * 74)
print("B. resonator_memory.py")
print("=" * 74)
print("_build_alphabet(3 ruoli, 8 atomi, d=256):")
cb = RS._build_alphabet(3, 8, 256, 42)
print("  codici:", len(cb), "· forma del primo:", cb[0].shape,
      "· righe a norma 1:", round(float(np.linalg.norm(cb[0][0])), 6))
x = cb[0][3]
idx, atomo, punteggio = RS._project_to_codebook(x, cb[0])
print("_project_to_codebook (argmax duro): indice", idx, "atteso 3 ·",
      "punteggio", round(float(punteggio), 4))
idxs, morbido, top = RS._soft_project_to_codebook(x, cb[0], 10.0)
print("_soft_project_to_codebook (softmax): indice", idxs, "· punteggio", round(float(top), 4))
rm = RS.ResonatorMemory(n_roles=3, atoms_per_role=8, d=1024, seed=7)
rm.remember_tuple((1, 2, 3))
print("_residual_norm della tupla giusta:",
      round(float(RS._residual_norm(rm.aggregate, (1, 2, 3), rm.codebooks)), 4),
      "· di una sbagliata:",
      round(float(RS._residual_norm(rm.aggregate, (7, 7, 7), rm.codebooks)), 4))
print("  >>> il residuo della tupla giusta e' MINORE:",
      RS._residual_norm(rm.aggregate, (1, 2, 3), rm.codebooks)
      < RS._residual_norm(rm.aggregate, (7, 7, 7), rm.codebooks))

print("\nResonatorMemory: memorizza e fattorizza")
print("  stats:", {k: str(v)[:40] for k, v in rm.stats().items()})
print("  recall_tuple():", rm.recall_tuple(n_iter=100, seed=1))
print("  recall_tuple_multi_restart():",
      rm.recall_tuple_multi_restart(n_restarts=5, n_iter=100))
rm2 = RS.ResonatorMemory(n_roles=3, atoms_per_role=8, d=1024, seed=7)
for t in ((1, 2, 3), (4, 5, 6)):
    rm2.remember_tuple(t)
print("  con DUE tuple, recall_all_via_matching_pursuit:",
      rm2.recall_all_via_matching_pursuit(max_facts=3))
pp = tmp / "res.npz"
rm2.save(pp)
rm3 = RS.ResonatorMemory.load(pp)
print("  save/load: aggregato identico:",
      bool(np.allclose(rm3.aggregate, rm2.aggregate)),
      "| file:", pp.name, "esiste:", pp.exists())
print("text_to_indices('il canone e 5900 euro'):",
      RS.text_to_indices("il canone e 5900 euro", 3, 8),
      "· deterministico:",
      RS.text_to_indices("il canone e 5900 euro", 3, 8)
      == RS.text_to_indices("il canone e 5900 euro", 3, 8))
