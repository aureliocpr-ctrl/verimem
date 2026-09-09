"""Due cose lasciate a metà su `skill.py`.

1. `retire_dormant_candidates` non ha ritirato **niente**, nemmeno la skill con
   zero prove e dormiente da 90 giorni. Ma il suo docstring lo dice:
   «Ultima attività = `updated_at` … `last_used_at` NON è persistito in
   tabella». Il mio caso metteva `last_used_at`: era sbagliato **il caso**.
   Qui invecchio la riga NELLA TABELLA e riprovo — così il controllo positivo
   può accendersi davvero.
2. `find_duplicates(0.99)` ha reso `[]` anche con due skill dal trigger
   IDENTICO. Guardo i coseni veri prima di chiamarlo difetto.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
import tempfile
import time

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-sk2-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import numpy as np  # noqa: E402

from verimem import skill as SK  # noqa: E402

adesso = time.time()
lib = SK.SkillLibrary(dir_path=tmp / "sk", db_path=tmp / "sk.db")
lib.store(SK.Skill(id="z1", name="zombie", trigger="t1", body="b",
                   trials=0, successes=0, status="candidate"))
lib.store(SK.Skill(id="z2", name="usata ieri", trigger="t2", body="b",
                   trials=0, successes=0, status="candidate"))
lib.store(SK.Skill(id="z3", name="vecchia ma provata", trigger="t3", body="b",
                   trials=9, successes=9, status="candidate"))

con = sqlite3.connect(str(tmp / "sk.db"))
con.execute("UPDATE skills SET updated_at = ?, created_at = ? WHERE id IN ('z1','z3')",
            (adesso - 86400 * 90, adesso - 86400 * 90))
con.execute("UPDATE skills SET updated_at = ?, created_at = ? WHERE id = 'z2'",
            (adesso - 86400, adesso - 86400))
con.commit()
for r in con.execute("SELECT id, trials, status, updated_at FROM skills"):
    eta = (adesso - float(r[3])) / 86400.0
    print(f"  {r[0]}: prove={r[1]} status={r[2]} · ferma da {eta:.0f} giorni")
con.close()

ritirate = lib.retire_dormant_candidates(max_age_days=30, cap=10, min_trials=3,
                                         now=adesso)
print("\nretire_dormant_candidates(max_age_days=30, min_trials=3) ->", ritirate)
lib.invalidate_cache()
for i in ("z1", "z2", "z3"):
    print(f"   {i}: {lib.get(i).status}")
print("  >>> ritirata SOLO la zombie (0 prove, 90 giorni):", ritirate == ["z1"])

print("\n=== il cap tiene il ritiro graduale?")
lib2 = SK.SkillLibrary(dir_path=tmp / "sk2", db_path=tmp / "sk2.db")
for i in range(5):
    lib2.store(SK.Skill(id=f"c{i}", name=f"zombie{i}", trigger=f"t{i}", body="b",
                        trials=0, successes=0, status="candidate"))
con = sqlite3.connect(str(tmp / "sk2.db"))
con.execute("UPDATE skills SET updated_at = ?, created_at = ?",
            (adesso - 86400 * 90, adesso - 86400 * 90))
con.commit()
con.close()
print("  con cap=2 su 5 zombie ->", lib2.retire_dormant_candidates(
    max_age_days=30, cap=2, min_trials=3, now=adesso))

print("\n=== find_duplicates: i coseni VERI fra due trigger identici")
lib3 = SK.SkillLibrary(dir_path=tmp / "sk3", db_path=tmp / "sk3.db")
lib3.store(SK.Skill(id="d1", name="uno", trigger="calcolare il canone di un capannone",
                    body="a"))
lib3.store(SK.Skill(id="d2", name="due", trigger="calcolare il canone di un capannone",
                    body="b"))
lib3.store(SK.Skill(id="d3", name="tre", trigger="gestire i turni del portiere", body="c"))
lib3.invalidate_cache()
con = sqlite3.connect(str(tmp / "sk3.db"))
righe = con.execute("SELECT id, trigger_embedding FROM skills").fetchall()
con.close()
vettori = {}
for i, blob in righe:
    if blob is None:
        print(f"  {i}: trigger_embedding NULLO")
        continue
    v = np.frombuffer(blob, dtype=np.float32)
    vettori[i] = v
    print(f"  {i}: embedding di {len(v)} valori, norma {float(np.linalg.norm(v)):.4f}")
if "d1" in vettori and "d2" in vettori:
    cos = float(vettori["d1"] @ vettori["d2"]
                / (np.linalg.norm(vettori["d1"]) * np.linalg.norm(vettori["d2"])))
    print(f"  coseno fra i due trigger IDENTICI: {cos:.6f}")
if "d1" in vettori and "d3" in vettori:
    cos2 = float(vettori["d1"] @ vettori["d3"]
                 / (np.linalg.norm(vettori["d1"]) * np.linalg.norm(vettori["d3"])))
    print(f"  coseno fra due trigger DIVERSI:    {cos2:.6f}")
print("  find_duplicates(0.99):", [(a.id, b.id, round(float(s), 4))
                                   for a, b, s in lib3.find_duplicates(0.99)])
print("  find_duplicates(0.95):", [(a.id, b.id, round(float(s), 4))
                                   for a, b, s in lib3.find_duplicates(0.95)])
print("  find_duplicates(0.99) trova la coppia identica:",
      any({a.id, b.id} == {"d1", "d2"} for a, b, _ in lib3.find_duplicates(0.99)))
