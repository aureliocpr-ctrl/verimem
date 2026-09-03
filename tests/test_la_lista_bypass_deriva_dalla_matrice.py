"""La lista che salta il gate deve DERIVARE dalla matrice, non starle accanto.

IL DIFETTO, misurato il 03/09: ci sono DUE classificazioni dei tool e nessuno le
aveva contate insieme — `REGISTRY` (esplicita) e `GATING_BYPASS_LIST` (28 voci
che saltano il gate senza lasciare traccia). Solo 5 stavano in entrambe, e il
20,1% delle chiamate passava dalla seconda.

E UNA LISTA SCRITTA A MANO ACCUMULA VOCI MORTE: `hippo_chain_latest` e
`hippo_chain_show` sono nel bypass ma **non sono tool** — nessun handler, non
esposti. `hippo_chain_show` sta perfino nel REGISTRY: il conteggio «20 tool
classificati» ne includeva uno che non esiste.

⇒ una fonte sola: la capacita' di saltare il gate diventa un ATTRIBUTO della
matrice (`gating_bypass`), e la lista si deriva. Chi aggiunge un tool lo
classifica in un posto solo, e un nome che non corrisponde a niente si vede.
"""
from __future__ import annotations

import pytest

from verimem import mcp_server
from verimem.tool_registry import REGISTRY


class TestUnaSolaFonte:
    def test_il_registro_porta_l_attributo(self) -> None:
        """Il campo deve esistere sulla capability, o non c'e' niente da derivare."""
        una = next(iter(REGISTRY._caps.values()))
        assert hasattr(una, "gating_bypass"), (
            "ToolCapability non ha `gating_bypass`: la lista non puo' derivare "
            "dalla matrice e restano due fonti")

    def test_la_lista_e_derivata_dal_registro(self) -> None:
        """Ogni tool del bypass deve stare nel registro con il flag acceso."""
        dal_registro = {n for n, c in REGISTRY._caps.items()
                        if getattr(c, "gating_bypass", False)}
        assert set(mcp_server.GATING_BYPASS_LIST) == dal_registro, (
            f"la lista NON deriva dal registro. Solo nella lista: "
            f"{sorted(set(mcp_server.GATING_BYPASS_LIST) - dal_registro)} · "
            f"solo nel registro: {sorted(dal_registro - set(mcp_server.GATING_BYPASS_LIST))}")

    def test_chi_salta_il_gate_e_READ(self) -> None:
        """Il presidio che vale piu' della derivazione: saltare il gate senza
        lasciare traccia si concede solo a chi LEGGE. Se domani qualcuno mette
        il flag su un WRITE, questo test lo ferma."""
        non_read = [n for n, c in REGISTRY._caps.items()
                    if getattr(c, "gating_bypass", False) and c.capability != "READ"]
        assert not non_read, (
            f"tool NON-READ che saltano il gate senza audit: {non_read}. "
            f"Il bypass e' per efficienza sui READ, non una scorciatoia")


class TestNienteVociMorte:
    def test_ogni_tool_classificato_esiste(self) -> None:
        """Un nome nella matrice che non corrisponde a nessun tool e' peggio di
        un tool non classificato: gonfia il conteggio della copertura e nessuno
        se ne accorge, perche' non viene mai chiamato."""
        import re
        from pathlib import Path
        src = Path(mcp_server.__file__).read_text(encoding="utf-8")
        handler = set(re.findall(r'if name == "([a-z0-9_]+)"', src))
        fantasmi = sorted(n for n in REGISTRY._caps if n not in handler
                          and not n.startswith("sandbox"))
        assert not fantasmi, (
            f"nel registro ci sono nomi che non sono tool: {fantasmi}. "
            f"Il conteggio della copertura li conta come classificati")
