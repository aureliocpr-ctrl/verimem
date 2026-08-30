"""La seconda cura del doc 48: basta costruire l'oggetto giusto?

Il blocco di `mcp_server.py` cerca `_auto_relevance_floor` su `agent` e
`agent.memory`; nessuno dei due lo espone, quindi `mem` resta None e
`sotto_il_pavimento` non viene mai emesso. La via corretta e' gia' in uso alle
righe 8139 e 13778 dello stesso file: COSTRUIRE un `Memory`.

Qui chiamo `_avvisi_di_lettura` due volte — con l'oggetto di oggi e con uno che
espone il metodo — e confronto i payload.

SU UNA COPIA in tempdir: lo store di Aurelio non viene toccato.
"""
import os
import shutil
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="ws6-cura2-"))
os.environ["HIPPO_DATA_DIR"] = str(TMP)
os.environ.pop("ENGRAM_DATA_DIR", None)
os.environ.pop("VERIMEM_DATA_DIR", None)

SRC = Path(os.path.expanduser("~/.engram/semantic/semantic.db"))
DST_DIR = TMP / "semantic"
DST_DIR.mkdir(parents=True, exist_ok=True)
DST = DST_DIR / "semantic.db"
shutil.copy2(SRC, DST)
print("copia dello store: %s (%.1f MB)" % (DST, DST.stat().st_size / 1e6))
print("il floor.json NON viene copiato: nella copia il pavimento si ricalcola")

from verimem.client import Memory                      # noqa: E402
from verimem.mcp_server import _avvisi_di_lettura      # noqa: E402

QUERY = "come si compra un biglietto ferroviario per Saturno"
mem = Memory(str(DST))
pav = mem._auto_relevance_floor()
print("\npavimento nella copia: %r" % pav)


class AgenteDiOggi:
    """Quello che la porta passa adesso: espone `semantic` e `memory`, ma
    nessuno dei due ha `_auto_relevance_floor`."""

    def __init__(self, m):
        self.semantic = m.semantic
        self.memory = object()          # sta per EpisodicMemory: niente metodo


class AgenteCurato(AgenteDiOggi):
    """La cura: l'agente espone anche il metodo, come le righe 8139 e 13778
    ottengono costruendo un Memory."""

    def __init__(self, m):
        super().__init__(m)
        self._mem = m

    def _auto_relevance_floor(self):
        return self._mem._auto_relevance_floor()


for eti, ag in (("OGGI   ", AgenteDiOggi(mem)), ("CURATO ", AgenteCurato(mem))):
    try:
        out = _avvisi_di_lettura(ag, QUERY)
    except Exception as e:                              # noqa: BLE001
        print("\n%s -> eccezione %s: %s" % (eti, type(e).__name__, e))
        continue
    print("\n%s chiavi del payload: %s" % (eti, sorted(out)))
    if "sotto_il_pavimento" in out:
        print("        sotto_il_pavimento = %s" % out["sotto_il_pavimento"])
    else:
        print("        sotto_il_pavimento ASSENTE")

print("\nlo store di Aurelio non e' stato toccato; copia in %s" % TMP)
