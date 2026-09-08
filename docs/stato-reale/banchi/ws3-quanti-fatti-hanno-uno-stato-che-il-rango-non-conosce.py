"""Il difetto del rango con default «model_claim» e' ATTIVO OGGI, non solo sul
futuro stato «review»: quanti fatti vivi hanno uno stato che `_STATUS_RANK` non
conosce, e quindi valgono 2 (= model_claim) nei quattro punti di
anti_confab_gate (746, 791, 2257, 2406 su main). Store in SOLA LETTURA, nessun
modello. Il docstring di `_rango_di_fiducia` (semantic.py:599) misurava 2540 su
6982 il 07/08: qui si guarda oggi."""
import pathlib
import sqlite3
import sys
from collections import Counter

WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT))
from verimem.semantic import _STATUS_RANK, _VALID_STATUSES  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
righe = con.execute("SELECT status, COUNT(*) FROM facts WHERE superseded_by IS NULL GROUP BY status").fetchall()
con.close()

noti = set(_STATUS_RANK)
tot = sum(n for _s, n in righe)
ignoti = Counter({s or "(NULL)": n for s, n in righe if (s or "") not in noti})
print(f"stati che la tabella _STATUS_RANK conosce: {sorted(noti)}")
print(f"stati in _VALID_STATUSES: {len(_VALID_STATUSES)}")
print(f"\nfatti vivi: {tot}")
print(f"con uno stato che il RANGO non conosce: {sum(ignoti.values())} = {100 * sum(ignoti.values()) / tot:.1f}%")
for s, n in ignoti.most_common():
    print(f"   {s:22s} {n:6d}   -> oggi vale 2 (= model_claim) nei quattro punti del gate")
print("\ntutti gli stati nello store, per numero:")
for s, n in sorted(righe, key=lambda r: -r[1]):
    marca = "" if (s or "") in noti else "  ⚠️ IGNOTO AL RANGO"
    print(f"   {str(s):22s} {n:6d}{marca}")
