"""Il registro dei ritiri diceva cosa, quando e perché — non CHI.

ws4, 2026-08-07: «il prodotto non sa chi scrive, il 67% dei fatti di
agosto non porta sigla». La metà che riguarda questa superficie è più
stretta e più curabile: **il dato c'era**. Ogni supersessione registra il
principal in `audit_mutations`, nella STESSA transazione della mutazione
— e il registro dei ritiri non lo leggeva.

Misurato sul corpus reale:

    audit_mutations  404 righe
       217 delete     sdk:local
       137 supersede  cli:local
        37 supersede  system:heal
        10 delete     cli:local
         3 forget     mcp:unbound

⚠️ E i DUE limiti vanno detti insieme al dato, o il campo promette più di
quanto mantiene:

1. **174 supersessioni attribuite su 1805 ritiri.** Il resto non ha una
   riga d'audit: la maggior parte dei ritiri del corpus (il collasso del 2
   luglio) è precedente o è passata da percorsi che non la scrivono. Un
   `retired_by` nullo significa «non registrato», non «nessuno».
2. **Il principal nomina la PORTA, non chi.** `cli:local` è il valore per
   tutte e sei le istanze che lavorano su questo corpus: dice da quale
   uscio è passata l'azione, non chi l'ha compiuta. È esattamente il
   difetto di ws4, e non lo curo io — ma non lo nascondo dietro un campo
   che sembra rispondere.

`system:heal` invece distingue davvero: è l'unico che identifica un
attore non umano, ed è quello che ritira da solo ogni 4 ore.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown, retirement_log


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _coppia(m: Memory, i: int = 0) -> tuple[str, str]:
    a = m.add(f"the depot {i} holds 10 crates", topic=f"log/a{i}")["id"]
    b = m.add(f"the depot {i} holds 20 crates", topic=f"log/b{i}")["id"]
    return a, b


def test_la_riga_dice_chi_ha_ritirato(mem):
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="cli:ws6", reason="banco")

    r = next(x for x in retirement_log(mem.semantic) if x["loser_id"] == a)
    assert r["retired_by"] == "cli:ws6", r


def test_un_ritiro_senza_riga_d_audit_dice_NON_REGISTRATO(mem):
    """1631 ritiri su 1805 stanno cosi'. Nullo vuol dire «non
    registrato», e va distinto da «nessuno»: e' la stessa regola per cui
    un `grounding_score` nullo non e' uno zero."""
    import sqlite3
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="cli:ws6", reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("DELETE FROM audit_mutations WHERE resource_id = ?", (a,))

    r = next(x for x in retirement_log(mem.semantic) if x["loser_id"] == a)
    assert r["retired_by"] is None, r


def test_il_riassunto_raggruppa_per_attore(mem):
    """Chi ritira di piu' e' la domanda di governo: sul corpus reale la
    risposta include `system:heal`, cioe' un processo che nessuno guarda."""
    a, b = _coppia(mem, 0)
    c, d = _coppia(mem, 1)
    e, f = _coppia(mem, 2)
    mem.semantic.supersede(a, b, principal="cli:ws6", reason="x")
    mem.semantic.supersede(c, d, principal="cli:ws6", reason="x")
    mem.semantic.supersede(e, f, principal="system:heal", reason="x")

    voci = {v["principal"]: v["n"]
            for v in retirement_breakdown(mem.semantic)["by_principal"]}
    assert voci["cli:ws6"] == 2 and voci["system:heal"] == 1


def test_il_riassunto_conta_i_NON_attribuiti_invece_di_ometterli(mem):
    """Se le righe attribuite fossero le uniche elencate, un lettore
    sommerebbe i conteggi e otterrebbe un totale che non torna: sul corpus
    reale mancherebbero 1631 ritiri su 1805."""
    import sqlite3
    a, b = _coppia(mem, 0)
    c, d = _coppia(mem, 1)
    mem.semantic.supersede(a, b, principal="cli:ws6", reason="x")
    mem.semantic.supersede(c, d, principal="cli:ws6", reason="x")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("DELETE FROM audit_mutations WHERE resource_id = ?", (a,))

    bd = retirement_breakdown(mem.semantic)
    voci = {v["principal"]: v["n"] for v in bd["by_principal"]}
    assert voci.get("(not recorded)") == 1, bd["by_principal"]
    assert sum(v["n"] for v in bd["by_principal"]) == bd["total_retired"]


def test_il_campo_DICHIARA_che_nomina_la_porta_e_non_la_persona(mem):
    """Il limite di ws4 va accanto al dato: `cli:local` e' lo stesso valore
    per tutte e sei le istanze. Un campo che sembra rispondere «chi» senza
    dire cosa misura e' peggio di un campo assente."""
    a, b = _coppia(mem)
    mem.semantic.supersede(a, b, principal="cli:ws6", reason="banco")

    nota = retirement_breakdown(mem.semantic)["principal_means"]
    assert "port" in nota.lower() or "door" in nota.lower(), nota
    assert "not recorded" in nota.lower()
