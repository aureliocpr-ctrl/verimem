"""I tuoi fatti non si perdono: il passaggio automatico non ritira per numeri.

Il 23 e il 24/09 ``run_maintenance`` (il consolidamento automatico all'avvio di
una sessione, ogni 4 ore) ha ritirato 41 fatti di uno store vero: un fatto di
prova ``model_claim`` vinceva gli scontri ``numeric_clash`` registrati contro
fatti di rango piu' basso, e ``heal_contradictions`` li eseguiva. Qui lo stesso
schema in uno store usa-e-getta: lo scontro e' registrato come l'avrebbe
registrato ``scan_corpus``, poi gira il passaggio automatico.
"""
from __future__ import annotations

import sqlite3

from verimem.auto_dream_worker import run_maintenance
from verimem.contradiction import Contradiction, ContradictionStore
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory

VINCITORE = "Il capannone 12 misura 400 mq."
PERDENTE = "Il servizio di ricerca ha risposto in 250 ms su 3 richieste."


def _scenario(tmp_path, tipo: str):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    vincitore = Fact(proposition=VINCITORE, topic="", status="model_claim")
    perdente = Fact(proposition=PERDENTE, topic="")
    sm.store(vincitore)
    sm.store(perdente)
    # Il rango piu' basso si impone nel DB: i gate di scrittura riportano
    # `provisional` a `model_claim` quando mancano i riferimenti, e a rango
    # pari heal non ritira niente — il banco passerebbe senza misurare la
    # regola (e' successo alla prima stesura: lo ha detto il controllo
    # positivo).
    with sqlite3.connect(str(sm.db_path)) as con:
        con.execute("UPDATE facts SET status = 'legacy_unverified' "
                    "WHERE id = ?", (perdente.id,))
    assert sm.get(perdente.id).status == "legacy_unverified"
    ContradictionStore(sm.db_path).add(Contradiction(
        fact_a_id=vincitore.id, fact_b_id=perdente.id, kind=tipo,
        similarity=0.9))
    return sm, EpisodicMemory(db_path=tmp_path / "ep.db"), perdente.id


def test_il_passaggio_automatico_non_ritira_un_fatto_per_uno_scontro_numerico(
        tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_AUTO_CONSOLIDATE", raising=False)
    sm, mem, perdente = _scenario(tmp_path, "numeric_clash")
    out = run_maintenance(tmp_path, now=1_000_000.0, sm=sm, mem=mem)
    assert out["ran"] is True, out
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, (
        "il passaggio automatico ha ritirato un fatto per uno scontro numerico: "
        f"{fatto.superseded_reason if fatto else 'il fatto non c e piu'} / {out}")
    # il passo spento lo DICE: lo scontro resta aperto ed e' contato
    aperti = (out.get("healed") or {}).get("left_open_kinds")
    assert aperti == {"numeric_clash": 1}, out


def test_nessun_chiamante_di_heal_esegue_uno_scontro_numerico(tmp_path):
    """La regola sta in ``heal_contradictions``, non nel passaggio automatico:
    lo strumento MCP ``hippo_heal_contradictions`` lo chiama allo stesso modo,
    senza ``skip_kinds``, e deve lasciare aperto lo stesso scontro."""
    from verimem.contradiction import heal_contradictions
    sm, _mem, perdente = _scenario(tmp_path, "numeric_clash")
    esito = heal_contradictions(sm, principal="test:mcp", limit=200)
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, esito
    assert esito["left_open_kinds"] == {"numeric_clash": 1}, esito


def test_controllo_positivo_uno_scontro_booleano_si_esegue_ancora(
        tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_AUTO_CONSOLIDATE", raising=False)
    sm, mem, perdente = _scenario(tmp_path, "boolean_clash")
    out = run_maintenance(tmp_path, now=1_000_000.0, sm=sm, mem=mem)
    fatto = sm.get(perdente)
    assert fatto is not None and fatto.superseded_by, (
        "il controllo positivo non si accende: il passaggio automatico non "
        f"esegue piu' nemmeno gli scontri booleani / {out}")
