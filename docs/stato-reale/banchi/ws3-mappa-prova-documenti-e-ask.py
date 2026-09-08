"""Prova ESEGUITA per le righe 5-7 della mappa di client.py: index_document /
search_documents (claim README:273-275) e ask (il router di intento). Store
temporaneo con path esplicito, quello di Aurelio non si tocca."""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-mappa2-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
import verimem  # noqa: E402
from verimem import Memory  # noqa: E402

print("IMPORT DA", verimem.__file__)
m = Memory(str(tmp / "mappa2.db"))

doc = tmp / "contratto.txt"
doc.write_text(
    "Contratto di locazione. Il canone mensile e' 5.900 euro.\n"
    "La clausola di risoluzione prevede un preavviso di sei mesi.\n"
    "Il deposito cauzionale e' pari a tre mensilita'.\n", encoding="utf-8")

print("\n--- index_document(path)  [README:274]")
try:
    r = m.index_document(str(doc))
    print("   ritorna:", {k: r[k] for k in list(r)[:6]} if isinstance(r, dict) else type(r).__name__)
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:160])

print("\n--- search_documents('risoluzione')  [README:275, 504: «passages with file + offset citations»]")
try:
    hits = m.search_documents("clausola di risoluzione", k=3)
    print(f"   {len(hits)} passaggi")
    for h in hits[:3]:
        d = h if isinstance(h, dict) else getattr(h, "__dict__", {})
        print("   campi:", sorted(d)[:10])
        print("   uri/file:", d.get("uri") or d.get("path") or d.get("doc_id"),
              "· start:", d.get("start"), "· end:", d.get("end"))
        break
except Exception as e:  # noqa: BLE001
    print("   ECCEZIONE:", type(e).__name__, str(e)[:160])

m.add("Il canone del capannone 12 e' 5900 euro.", source="Contratto: il canone del capannone 12 e' 5900 euro.", topic="mappa/ask")
m.add("Il capannone 12 e' a Prato.", source="Anagrafica: il capannone 12 si trova a Prato.", topic="mappa/ask")

for q, atteso in (("quante volte ho parlato del capannone?", "COUNT"),
                  ("elenca tutti i capannoni", "LIST_ALL"),
                  ("dove si trova il capannone 12?", "FIND")):
    print(f"\n--- ask({q!r})  [atteso intent {atteso}]")
    try:
        r = m.ask(q, k=5)
        print("   intent:", r.get("intent"), "· chiavi:", sorted(r)[:8])
        if "count" in r:
            print("   count:", r["count"])
        if "results" in r:
            print("   results:", len(r["results"]))
    except Exception as e:  # noqa: BLE001
        print("   ECCEZIONE:", type(e).__name__, str(e)[:160])

print("\n--- answer() senza llm  [README:705: «raises TypeError without one»]")
try:
    m.answer("quanto costa il capannone 12?")
    print("   NESSUNA ECCEZIONE (il README dice che dovrebbe sollevare TypeError)")
except TypeError as e:
    print("   TypeError come promesso:", str(e)[:120])
except Exception as e:  # noqa: BLE001
    print("   ALTRA ECCEZIONE:", type(e).__name__, str(e)[:120])
