"""I tuoi fatti non si perdono: il passaggio automatico non ritira per numeri
ne' per scontri booleani, e due fatti senza topic non ne condividono uno.

Il 23 e il 24/09 ``run_maintenance`` (il consolidamento automatico all'avvio di
una sessione, ogni 4 ore) ha ritirato 41 fatti di uno store vero: un fatto di
prova ``model_claim`` vinceva gli scontri ``numeric_clash`` registrati contro
fatti di rango piu' basso, e ``heal_contradictions`` li eseguiva. Qui lo stesso
schema in uno store usa-e-getta: lo scontro e' registrato come l'avrebbe
registrato ``scan_corpus``, poi gira il passaggio automatico.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.auto_dream_worker import run_maintenance
from verimem.contradiction import Contradiction, ContradictionStore
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory

VINCITORE = "Il capannone 12 misura 400 mq."
PERDENTE = "Il servizio di ricerca ha risposto in 250 ms su 3 richieste."
COPPIE = {
    "numeric_clash": ("Il contatore segna 10 impulsi.", "Il contatore segna 20 impulsi."),
    "boolean_clash": ("Il backup notturno del server principale e' attivo.",
                      "Il backup notturno del server principale non e' attivo."),
}


def _scenario(tmp_path, tipo: str, topic: str = ""):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    vincitore = Fact(proposition=VINCITORE, topic=topic, status="model_claim")
    perdente = Fact(proposition=PERDENTE, topic=topic)
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
    assert aperti == {"numeric_clash": 1, "boolean_clash": 0}, out


def test_nessun_chiamante_di_heal_esegue_uno_scontro_numerico(tmp_path):
    """La regola sta in ``heal_contradictions``, non nel passaggio automatico:
    lo strumento MCP ``hippo_heal_contradictions`` lo chiama allo stesso modo,
    senza ``skip_kinds``, e deve lasciare aperto lo stesso scontro."""
    from verimem.contradiction import heal_contradictions
    sm, _mem, perdente = _scenario(tmp_path, "numeric_clash")
    esito = heal_contradictions(sm, principal="test:mcp", limit=200)
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, esito
    assert esito["left_open_kinds"] == {"numeric_clash": 1, "boolean_clash": 0}, esito


@pytest.mark.parametrize("topic", ["magazzino", ""], ids=["topic", "senza topic"])
def test_il_passaggio_automatico_non_ritira_un_fatto_per_uno_scontro_booleano(
        tmp_path, monkeypatch, topic):
    """Il 29/09, su una copia dello store dopo gli undo, il heal ritirava 172
    fatti per scontri booleani, e fra questi di nuovo tutti e 41 i ripristinati:
    finche' la catena col giudice non copre i booleani, restano aperti e contati."""
    monkeypatch.delenv("ENGRAM_AUTO_CONSOLIDATE", raising=False)
    sm, mem, perdente = _scenario(tmp_path, "boolean_clash", topic=topic)
    out = run_maintenance(tmp_path, now=1_000_000.0, sm=sm, mem=mem)
    assert out["ran"] is True, out
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, (
        "il passaggio automatico ha ritirato un fatto per uno scontro booleano: "
        f"{fatto.superseded_reason if fatto else 'il fatto non c e piu'} / {out}")
    assert (out.get("healed") or {}).get("left_open_kinds") == {"numeric_clash": 0, "boolean_clash": 1}, out


def test_nessun_chiamante_di_heal_esegue_uno_scontro_booleano(tmp_path):
    from verimem.contradiction import heal_contradictions
    sm, _mem, perdente = _scenario(tmp_path, "boolean_clash", topic="magazzino")
    esito = heal_contradictions(sm, principal="test:mcp", limit=200)
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, esito
    assert esito["left_open_kinds"] == {"numeric_clash": 0, "boolean_clash": 1}, esito


def test_controllo_positivo_chi_chiede_esplicitamente_i_booleani_li_esegue(tmp_path):
    """Il meccanismo c'e' ancora: e' il default a spegnerlo. Senza questa cella
    le due sopra passerebbero anche con un heal rotto."""
    from verimem.contradiction import heal_contradictions
    sm, _mem, perdente = _scenario(tmp_path, "boolean_clash", topic="magazzino")
    esito = heal_contradictions(sm, principal="test:mcp", limit=200,
                                skip_kinds=frozenset())
    fatto = sm.get(perdente)
    assert fatto is not None and fatto.superseded_by, (
        f"il controllo positivo non si accende: il heal non ritira piu' niente / {esito}")


# ------------------------------------------------------------ topic vuoto --
# Il 29/09 lo stesso heal, rifatto su una copia dello store vero dopo gli
# undo, ritirava di nuovo tutti e 41 i fatti ripristinati: per boolean_clash,
# contro quattro fatti che non c'entravano, perche' il topic vuoto era trattato
# come un topic condiviso. Un fatto senza topic non ne condivide uno con
# nessuno: lo scontro resta aperto e si conta.


def test_nessun_chiamante_di_heal_esegue_uno_scontro_fra_due_fatti_senza_topic(
        tmp_path):
    from verimem.contradiction import heal_contradictions
    sm, _mem, perdente = _scenario(tmp_path, "boolean_clash")
    # i booleani chiesti esplicitamente: la cella misura la guardia del topic,
    # che deve reggere anche quando il tipo tornera' acceso
    esito = heal_contradictions(sm, principal="test:mcp", limit=200,
                                skip_kinds=frozenset())
    fatto = sm.get(perdente)
    assert fatto is not None and not fatto.superseded_by, esito
    assert esito["left_open_no_topic"] == 1, esito


@pytest.mark.parametrize("tipo", ["numeric_clash", "boolean_clash"])
def test_lo_scan_non_mette_insieme_due_fatti_senza_topic(monkeypatch, tipo):
    """Lo scan non registra piu' scontri fra fatti senza topic; con un topic
    condiviso la stessa coppia si registra ancora (il controllo positivo)."""
    import verimem.contradiction as ct
    monkeypatch.setattr(ct, "_cosine", lambda a, b: 1.0)
    rileva = (ct.detect_numeric_clashes if tipo == "numeric_clash"
              else ct.detect_boolean_clashes)
    coppia = COPPIE[tipo]

    def trovati(topic):
        return rileva([Fact(id="a", proposition=coppia[0], topic=topic),
                       Fact(id="b", proposition=coppia[1], topic=topic)])

    assert trovati("magazzino"), "controllo positivo spento: la coppia non si registra"
    assert trovati("") == [], trovati("")
