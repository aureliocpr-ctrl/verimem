"""I 28 candidati a «falsa assenza» di L4.1: il contesto del numero nel claim e
nella fonte, per classificarli a mano (store in sola lettura)."""
import pathlib
import re
import sqlite3
import sys

QUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(QUI.parents[2]))
from verimem.valore_non_nella_fonte import valori_non_nella_fonte  # noqa: E402

IDS = """21b5710c46f5 cf5b0157ffb4 9eade078637f 6c3bc544d4b2 687edd69f53e dffc45dca687 c995920e7a47
ec2993298189 2bf35b09d120 aa9545463b3a 662c59ab1803 ec910e601c7b ff492db4f726 5e281783181f d104ce022403
cf0517c6ef72 2ccc34b6547c ea717048769d 283d353b5ed9 d5fa20bc2ff6 db75b5bf67e8 f72209bc802c 8ab2419f2aab
453bdb71f8d9 621bc05b3b77 76a17e5935f5 7ff731e9bce9 281db2b21ad4""".split()

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def intorno(testo: str, t: str, largo: int = 28) -> list[str]:
    out = []
    for m in re.finditer(re.escape(t), testo):
        a, b = max(0, m.start() - largo), min(len(testo), m.end() + largo)
        out.append(testo[a:b].replace("\n", " "))
        if len(out) == 2:
            break
    return out or ["(non compare come stringa)"]


for fid in IDS:
    row = con.execute("SELECT proposition, grounding_span FROM facts WHERE id LIKE ?", (fid + "%",)).fetchone()
    if not row:
        print(fid, "NON TROVATO")
        continue
    prop, span = row
    assenti = valori_non_nella_fonte(prop, span)
    print(f"\n— {fid} assenti={[a.testo for a in assenti]}")
    for a in assenti:
        t = a.testo or ""
        print(f"   claim : {intorno(prop, t)[0]!r}")
        print(f"   fonte : {intorno(span, t)[0]!r}")
con.close()
