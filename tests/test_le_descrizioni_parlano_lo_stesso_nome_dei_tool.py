"""Col namespace del prodotto acceso, le descrizioni rimandavano a nomi spenti.

`VERIMEM_TOOL_NAMESPACE=verimem` (fase 2 del rename) espone i 247 `hippo_*`
come `verimem_*`. Ma `_apply_tool_namespace` rinomina **solo `tool.name`**: le
descrizioni continuano a nominare i tool col prefisso vecchio. Misurato il
16/08 sulla porta `list_tools()`::

    tool la cui descrizione cita un altro tool hippo_*   50 su 248
    occorrenze                                           60

⇒ Con il namespace acceso un utente legge `verimem_stats` — «Cheaper than
`hippo_status` for dashboards» — e `hippo_status` **non compare in nessun punto
della lista che ha appena ricevuto**. Il prodotto rimanda a nomi che non espone.

È lo stesso difetto curato in `dfec9825` sul messaggio d'errore (che nominava un
tool mai digitato), sulla superficie delle descrizioni invece che su quella
degli errori.

═══ PERCHÉ LA SOSTITUZIONE È PER NOME NOTO E NON PER PREFISSO ═══

Una descrizione può contenere `hippo_` in punti che NON sono riferimenti a un
tool: `HIPPO_DISABLED` è una variabile d'ambiente (maiuscola, non matcha) e
`hippo_facts_*` con la stella è una famiglia, non un tool. ⇒ Si sostituisce
**solo ciò che corrisponde a un tool realmente rinominato**, e ciò che resta si
conta invece di essere nascosto (vedi
`test_cosa_resta_dopo_la_cura_e_dichiarato`).
"""
from __future__ import annotations

import asyncio
import re

import pytest

from verimem import mcp_server as ms

_RIF = re.compile(r"hippo_[a-z0-9_]+")


def _tools(ns: str | None):
    return asyncio.run(ms.list_tools())


@pytest.fixture
def acceso(monkeypatch):
    monkeypatch.setenv("VERIMEM_TOOL_NAMESPACE", "verimem")
    monkeypatch.delenv("ENGRAM_MCP_TOOLS_PREFIX", raising=False)
    return _tools("verimem")


@pytest.fixture
def spento(monkeypatch):
    monkeypatch.delenv("VERIMEM_TOOL_NAMESPACE", raising=False)
    monkeypatch.delenv("ENGRAM_TOOL_NAMESPACE", raising=False)
    monkeypatch.delenv("ENGRAM_MCP_TOOLS_PREFIX", raising=False)
    return _tools(None)


def _rimandi_morti(tools) -> list[tuple[str, str]]:
    """Riferimenti a tool che, in QUESTA lista, non esistono con quel nome ma
    esistono col nome nuovo."""
    esposti = {t.name for t in tools}
    morti = []
    for tool in tools:
        for rif in _RIF.findall(tool.description or ""):
            nuovo = "verimem_" + rif[len("hippo_"):]
            if rif not in esposti and nuovo in esposti:
                morti.append((tool.name, rif))
    return morti


def test_col_namespace_acceso_nessuna_descrizione_rimanda_a_un_nome_spento(
        acceso):
    morti = _rimandi_morti(acceso)
    assert not morti, (
        f"{len(morti)} riferimenti a tool che la lista NON espone più con quel "
        f"nome. L'utente legge un nome e non lo trova. Primi cinque: "
        f"{morti[:5]}")


def test_col_namespace_spento_le_descrizioni_restano_quelle_di_prima(spento):
    """⚠️ POPOLAZIONE OPPOSTA. Il docstring di `_apply_tool_namespace` promette
    che senza la variabile l'uscita è «byte-identical»: una cura che riscrivesse
    le descrizioni SEMPRE romperebbe quella promessa, e questo test cade."""
    con_hippo = [t.name for t in spento
                 if _RIF.search(t.description or "")]
    assert con_hippo, (
        "col namespace spento le descrizioni devono continuare a nominare i "
        "tool come hippo_*: se non lo fanno più, la cura ha riscritto anche "
        "il caso di default e la promessa «byte-identical» è rotta")


def test_i_nomi_e_le_descrizioni_dicono_lo_stesso_prefisso(acceso):
    """Il criterio in una riga: se un tool si chiama verimem_*, ciò che la sua
    descrizione addita deve chiamarsi verimem_* pure."""
    esposti = {t.name for t in acceso}
    assert any(n.startswith("verimem_") for n in esposti), \
        "il namespace non si è acceso: il resto del test non misura nulla"
    for tool in acceso:
        if not tool.name.startswith("verimem_"):
            continue
        for rif in _RIF.findall(tool.description or ""):
            assert "verimem_" + rif[len("hippo_"):] not in esposti, (
                f"{tool.name} è esposto col nome nuovo ma la sua descrizione "
                f"addita «{rif}», che in questa lista non esiste")


def test_cosa_resta_dopo_la_cura_e_dichiarato(acceso):
    """⚠️ NON un test di purezza: un CENSIMENTO che impedisce di dichiarare
    zero quando zero non è. Restano i `hippo_` che non corrispondono a nessun
    tool esposto — famiglie con la stella, troncature, prosa. Se questo numero
    cresce, qualcuno ha aggiunto un riferimento che la cura non copre."""
    esposti = {t.name for t in acceso}
    residui = sorted({
        rif for tool in acceso for rif in _RIF.findall(tool.description or "")
        if "verimem_" + rif[len("hippo_"):] not in esposti
    })
    assert len(residui) <= 6, (
        f"i riferimenti non risolvibili a un tool sono {len(residui)}, più di "
        f"quanti ne avevo censiti: {residui}")
