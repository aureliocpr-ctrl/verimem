"""Sonda: `_route_evolutions` arriva davvero al confronto dei ranghi, o si ferma
prima? Senza questa risposta l'xfail della cella e' un rosso che non prova niente."""
import pathlib
import sys
from types import SimpleNamespace

WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT))
from verimem.anti_confab_gate import _route_evolutions  # noqa: E402


class _Store:
    def __init__(self, v):
        self._v = v

    def get(self, _id):
        return self._v


def vecchio(status):
    return SimpleNamespace(id="vecchio", proposition="Il canone del capannone 12 e' 5100 euro.",
                           status=status, agent="ws3", verified_by=[], asserted_at=1.0,
                           source_signature="firma", topic="prova/rango", valid_from=1.0)


def prova(status_vecchio, nuovo="model_claim"):
    ag = SimpleNamespace(semantic=_Store(vecchio(status_vecchio)), store=_Store(vecchio(status_vecchio)))
    sup: list[str] = []
    conf = _route_evolutions(ag, [], 2.0, ["vecchio"], sup, new_status=nuovo, claimant="ws3",
                             proposition="Il canone del capannone 12 e' 5900 euro.", cand_ha_source=True)
    return sup, conf


for st in ("user_manual", "model_claim", "quarantined", "verified"):
    sup, conf = prova(st)
    print(f"vecchio status={st:16s} -> supersede_ids={sup} conflicts={conf}")
