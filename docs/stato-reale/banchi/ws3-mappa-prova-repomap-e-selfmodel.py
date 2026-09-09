"""`repomap.py` (13) e `self_model.py` (11).

Le due domande che decidono:
  · `render_repomap` promette una mappa «sotto un budget di token»: il budget si
    prova SUPERANDOLO, non stando sotto per caso.
  · `SelfModelStore` ha un'eccezione dedicata al superamento del limite di byte:
    quella eccezione deve **accendersi** su un contenuto grande e **restare
    spenta** su uno normale, o il limite non è un limite.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-rm-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
from verimem import repomap as RM  # noqa: E402
from verimem import self_model as SM  # noqa: E402

print("=" * 74)
print("A. repomap.py — la mappa del repository sotto un budget")
print("=" * 74)
repo = tmp / "repo"
(repo / "pkg").mkdir(parents=True)
(repo / "pkg" / "grande.py").write_text(
    "\n".join([f"def funzione_{i}(a, b):\n    return a + b\n" for i in range(30)]),
    encoding="utf-8")
(repo / "pkg" / "piccolo.py").write_text("def sola(a):\n    return a\n", encoding="utf-8")
(repo / "app.js").write_text("function uno(){}\nfunction due(){}\n", encoding="utf-8")
(repo / "note.txt").write_text("non e' codice\n", encoding="utf-8")

print("_walk_files:", sorted(pathlib.Path(p).name for p, _m, _s in RM._walk_files(str(repo))))
e = RM._scan_file(repo / "pkg" / "grande.py", repo, 0.0, 100)  # vuole Path, non str
print("_scan_file(grande.py): simboli trovati:", len(e.symbols),
      "| primi tre:", [s.name for s in e.symbols[:3]])
d = RM._entry_to_cache(e)
e2 = RM._entry_from_cache(d)
print("_entry_to_cache/_entry_from_cache round-trip: simboli uguali:",
      [s.name for s in e2.symbols] == [s.name for s in e.symbols])
cp = RM._default_cache_path(repo)  # anche questa vuole Path
print("_default_cache_path:", cp.name, "| sotto data_dir:", str(tmp) in str(cp))

t0 = time.perf_counter()
entries = RM.scan_repo(repo, max_files=50, use_cache=True, cache_path=cp)
t1 = time.perf_counter()
entries2 = RM.scan_repo(repo, max_files=50, use_cache=True, cache_path=cp)
t2 = time.perf_counter()
print(f"scan_repo: {len(entries)} file · prima passata {t1 - t0:.3f}s · "
      f"seconda (con cache) {t2 - t1:.3f}s · file di cache creato:",
      cp.exists())
print("  i file trovati:", sorted(pathlib.Path(x.path).name for x in entries))
print("_load_cache: chiavi in cache:", len(RM._load_cache(cp) or {}))

classifica = RM.rank_files(entries, recent_skill_paths=[], now=time.time())
print("rank_files (senza skill recenti):",
      [(pathlib.Path(x.path).name, round(getattr(x, 'score', 0.0), 2)) for x in classifica])
# il confronto è `e.path in recent_skill_paths` (riga 277) e `e.path` è il path
# RELATIVO alla root: passare l'assoluto non aggancia nulla — il primo giro,
# con l'assoluto, lasciava i punteggi identici, ed era un caso sbagliato MIO.
rel_piccolo = next(x.path for x in entries if x.path.endswith("piccolo.py"))
print("  (il path come lo tiene FileEntry:", repr(rel_piccolo), ")")
cl2 = RM.rank_files(entries, recent_skill_paths={rel_piccolo}, now=time.time())
print("rank_files (con piccolo.py fra le skill recenti, path RELATIVO):",
      [(pathlib.Path(x.path).name, round(getattr(x, 'score', 0.0), 2)) for x in cl2])
print("  >>> il file citato è salito in cima:",
      pathlib.Path(cl2[0].path).name == "piccolo.py")
cl3 = RM.rank_files(entries, recent_skill_paths={str(repo / "pkg" / "piccolo.py")},
                    now=time.time())
print("  con il path ASSOLUTO (come avevo sbagliato io):",
      [(pathlib.Path(x.path).name, round(getattr(x, 'score', 0.0), 2)) for x in cl3])

lungo = RM.render_repomap(classifica, max_chars=4000)
corto = RM.render_repomap(classifica, max_chars=120)
print(f"render_repomap: con 4000 caratteri -> {len(lungo)} · con 120 -> {len(corto)}")
print("  >>> il budget stretto viene RISPETTATO:", len(corto) <= 120)
print("  estratto:", repr(corto[:100]))
tutto = RM.build_repomap(repo, recent_skill_paths=[], max_files=50,
                          max_chars=500, use_cache=False, cache_path=cp)
print("build_repomap (scan+rank+render):", len(tutto), "caratteri, <= 500:", len(tutto) <= 500)

print("\n" + "=" * 74)
print("B. self_model.py — il modello di sé, versionato e con un tetto")
print("=" * 74)
st = SM.SelfModelStore(str(tmp / "self.db"), max_bytes=2000)
print("get() su uno store nuovo:", st.get(), "(None = mai scritto, non un vuoto finto)")
r1 = st.update({"focus": "la mappa di client.py", "goal": ["chiudere i 20 file"]},
               actor="ws3")
print("update #1 -> versione", r1.get("version"), "| attore:", r1.get("actor"))
r2 = st.update({"focus": "gateway.py", "goal": ["87 funzioni"]}, actor="ws3")
print("update #2 -> versione", r2.get("version"))
print("get() ora:", {k: str(v)[:60] for k, v in (st.get() or {}).items()})
h = st.history()
print("history:", [(x.get("version"), str(x.get("content"))[:40]) for x in h],
      "| dalla piu' vecchia:", [x.get("version") for x in h] == sorted(
          x.get("version") for x in h))

print("\nil TETTO: si accende dove deve, e resta spento dove non deve?")
try:
    st.update({"focus": "x" * 5000}, actor="ws3")
    print("  contenuto da 5000 byte -> NESSUNA eccezione (il tetto non morde)")
except SM.SelfModelTooLarge as ex:
    print("  contenuto da 5000 byte -> SelfModelTooLarge:", str(ex)[:90])
except Exception as ex:  # noqa: BLE001
    print("  contenuto da 5000 byte ->", type(ex).__name__, str(ex)[:90])
try:
    r3 = st.update({"focus": "corto"}, actor="ws3")
    print("  contenuto corto -> versione", r3.get("version"), "(il tetto NON ha bloccato)")
except Exception as ex:  # noqa: BLE001
    print("  contenuto corto ->", type(ex).__name__, str(ex)[:90])

print("\nrender_for_injection:")
print("  con None ->", repr(SM.render_for_injection(None)))
blocco = SM.render_for_injection(st.get())
print("  con un record ->", repr(blocco[:120]))

print("\nrender_anchor_block (serve un EntityStore: lo chiamo con sem=None)")
try:
    b = SM.render_anchor_block(st, sem=None, max_bytes=500)
    print("  ->", repr(str(b)[:120]))
except Exception as ex:  # noqa: BLE001
    print("  ->", type(ex).__name__, str(ex)[:120])
