"""La porta SDK, letta sul CORPUS VIVO con e senza `ENGRAM_AVVISO_MIN_RELEVANCE`.

    python scripts/banco_sdk_soglia_sul_corpus_vivo.py

PERCHE'. Il 03/09 ho allineato la soglia dell'avviso su tre porte (SDK, MCP,
CLI) e ho scritto un presidio che le confronta — ma **i suoi banchi sono
DOPPI** (`_Mem`, `_Agente`, `CliRunner`). L'unica lettura REALE l'ho fatta sulla
CLI (19:34). ⇒ dichiaro da ieri «NON VERIFICATO» su SDK e MCP, e questo banco
chiude la meta' SDK.

⚠️ MCP RESTA NON VERIFICATO: la sua porta vera e' un server, e non l'ho ancora
letta. Questo banco NON lo copre.

UN SOLO PROCESSO, DUE REGIMI: `_pavimento_avviso` legge `os.environ` a ogni
chiamata, quindi la variabile si accende e si spegne dentro la stessa
esecuzione — l'embedder si carica UNA volta sola (Aurelio e' al PC).

PREDIZIONE SCRITTA PRIMA (2026-09-03 20:17):
  (1) SENZA variabile, domanda FUORI DOMINIO -> avvisa, pavimento ~0.88
      (il calibrato) e nota che dice «calibrata su questo corpus»
  (2) CON `ENGRAM_AVVISO_MIN_RELEVANCE=0.95`, stessa domanda -> avvisa,
      pavimento 0.95 e nota che dice «impostata con ENGRAM_AVVISO_MIN_RELEVANCE»
  (3) SENZA variabile, domanda CON RISPOSTA -> il fatto giusto esce; l'avviso
      puo' comparire lo stesso, perche' l'SDK confronta `_best_prima` col
      pavimento e sul corpus vivo le vere stanno a 0,858-0,90, cioe' a cavallo
      di 0,88. ⚠️ QUESTA E' UNA PREDIZIONE DEBOLE E LO DICHIARO: non so da che
      parte cade.
CONDIZIONE D'USCITA: (1) e (2) confermate ⇒ la porta SDK e' verificata sul
corpus vivo e il «NON VERIFICATO» si toglie per l'SDK, non per MCP.
"""
import os
import sys
from pathlib import Path

for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_GATEWAY_MIN_RELEVANCE", "ENGRAM_AVVISO_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
os.environ["ENGRAM_RECALL_RERANK"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.config import CONFIG  # noqa: E402

FUORI = "ricetta carbonara guanciale pecorino uova"
CON_RISPOSTA = "il pavimento calibrato dello store vale 0.8805"


def leggi(mem, query, etichetta):
    r = mem.search(query, k=10)
    sp = getattr(r, "sotto_il_pavimento", None)
    if not sp:
        print(f"  {etichetta:32} NESSUN AVVISO   (risultati: {len(r)})", flush=True)
        return None
    nota = (sp.get("nota") or "").lower()
    origine = ("dalla variabile" if "engram_avviso_min_relevance" in nota
               else ("calibrata sul corpus" if "calibrat" in nota else "?"))
    print(f"  {etichetta:32} pavimento={sp.get('pavimento')}  "
          f"best={sp.get('score_migliore')}  origine={origine}", flush=True)
    return sp


def main():
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO (righello di @ws2, 03/09): nel worktree si
    # importa il worktree, da uno script lanciato altrove l'albero condiviso.
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | store VIVO in sola lettura | rerank=OFF",
          flush=True)
    mem = Memory(CONFIG.semantic_db)

    print("SENZA la variabile", flush=True)
    a = leggi(mem, FUORI, "fuori dominio")
    c = leggi(mem, CON_RISPOSTA, "domanda CON risposta")

    os.environ["ENGRAM_AVVISO_MIN_RELEVANCE"] = "0.95"
    print("CON ENGRAM_AVVISO_MIN_RELEVANCE=0.95", flush=True)
    b = leggi(mem, FUORI, "fuori dominio")
    os.environ.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)

    # --- la porta MCP, con la FUNZIONE REALE e lo STORE VIVO ---------------
    # ⚠️ NON e' il server: e' `_avvisi_di_lettura` chiamata con un oggetto che
    # espone la `SemanticMemory` VERA. Il ripiego che il docstring di
    # `_pavimento_di` documenta («costruisce Memory dal db_path») e' proprio
    # questo percorso. ⇒ codice reale + dati reali, MA NON la porta di rete:
    # quello resta NON VERIFICATO e va detto accanto al numero.
    from verimem.mcp_server import _avvisi_di_lettura

    class _AgenteVivo:
        def __init__(self, sem):
            self.semantic = sem

    agente = _AgenteVivo(mem.semantic)
    print("porta MCP (funzione reale, store vivo, NON il server)", flush=True)
    for eti, var in (("senza la variabile", None), ("con 0.95", "0.95")):
        if var:
            os.environ["ENGRAM_AVVISO_MIN_RELEVANCE"] = var
        else:
            os.environ.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)
        out = _avvisi_di_lettura(agente, FUORI)
        sp = out.get("sotto_il_pavimento")
        if not sp:
            print(f"  {eti:32} NESSUN AVVISO", flush=True)
        else:
            nota = (sp.get("nota") or "").lower()
            org = ("dalla variabile" if "engram_avviso_min_relevance" in nota
                   else ("calibrata sul corpus" if "calibrat" in nota else "?"))
            print(f"  {eti:32} pavimento={sp.get('pavimento')}  "
                  f"best={sp.get('score_migliore')}  origine={org}", flush=True)
    os.environ.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)

    print(f"RIGA senza={a and a.get('pavimento')} con={b and b.get('pavimento')} "
          f"con_risposta={c and c.get('pavimento')}", flush=True)
    print("PREDIZIONE (scritta prima): senza -> ~0.88 e «calibrata su questo "
          "corpus»; con -> 0.95 e «impostata con ENGRAM_AVVISO_MIN_RELEVANCE». "
          "Il terzo caso e' una predizione DEBOLE, dichiarata.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
