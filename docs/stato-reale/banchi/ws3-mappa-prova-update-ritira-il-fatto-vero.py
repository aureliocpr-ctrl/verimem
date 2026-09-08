"""IL REPERTO DEL TURNO, isolato con UNA VARIABILE PER VOLTA.

Nel banco di gestione `update()` ha restituito `status='quarantined'` e la
catena `history` mostrava [model_claim 5900] -> [quarantined 6100]: il fatto
VERO era stato ritirato da uno che il gate aveva bocciato. Se è così, chi
aggiorna un fatto con una frase che la fonte non sostiene **perde dalla vista
anche quella vecchia**, e nessuna delle due viene più servita.

Qui lo misuro pulito, e col braccio che può falsificarmi:
  A) update con un testo NON sostenuto dalla fonte  -> cosa serve la search?
  B) update con un testo SOSTENUTO dalla fonte      -> deve passare e servire.
Se cade solo A, il difetto è dell'interazione gate+supersessione, non di
`update` in sé. Se cadono entrambi, è `update`. Se non cade nessuno, il reperto
del banco precedente era un artefatto e lo scrivo.
"""
import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-upd-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from verimem import Memory  # noqa: E402

FONTE = ("Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro "
         "e la consegna e' prevista per il 3 marzo.")


def servite(m, q="canone capannone 12"):
    return [str(h.get("text"))[:52] for h in m.search(q, k=10)]


for etichetta, nuovo_testo in (
        ("A) update NON sostenuto dalla fonte", "Il canone del capannone 12 e' 6100 euro."),
        ("B) update SOSTENUTO dalla fonte", "La consegna del capannone 12 e' prevista per il 3 marzo.")):
    d = pathlib.Path(tempfile.mkdtemp(prefix="ws3-upd-"))
    m = Memory(str(d / "u.db"))
    r = m.add("Il canone del capannone 12 e' 5900 euro.", source=FONTE, topic="u/x")
    print("\n" + "=" * 72)
    print(etichetta)
    print("  1. scritto:", r.get("status"), "| id", r.get("id"))
    print("  2. search PRIMA :", servite(m))
    u = m.update(r["id"], nuovo_testo, topic="u/x")
    print("  3. update ->", "stored:", u.get("stored"), "| status:", u.get("status"),
          "| supersedes:", str(u.get("supersedes"))[:14],
          "| warnings:", [w.get("layer") for w in (u.get("warnings") or [])])
    print("  4. search DOPO  :", servite(m))
    print("  5. history      :",
          [(x.get("status"), str(x.get("text"))[:38]) for x in m.history(r["id"])])
    sv = m.survivability()
    print("  6. survivability: written", sv.get("written"), "servable", sv.get("servable"),
          "retired", sv.get("retired"), "quarantined", sv.get("quarantined"))
    vecchio = m.get(r["id"]) or {}
    print("  7. il fatto vecchio: status", vecchio.get("status"),
          "| superseded_by", str(vecchio.get("superseded_by"))[:14])
    print("  >>> fatti serviti su quel contenuto DOPO l'update:", len(servite(m)))
