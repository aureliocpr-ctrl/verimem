"""Il briefing dice «non disponibile», non «-1».

Misurato da ws5 il 2026-08-05: `get_briefing` vuole un agent con `.skills`,
`.memory` e `.semantic`, ma un utente SDK ha una `Memory` — che ha solo
`.semantic`. Riempiendo ciò che si può (l'unico gesto possibile), la prima
riga che quell'utente legge aprendo la sessione è:

    "verimem memory: -1 episode (0 success, 0 failure), 6113 fact, -1 skill"

Meno uno. E «0 success, 0 failure» mentre nel corpus ci sono 405 success e
8 failure. La causa è `_safe_count`, che ritorna -1 su errore: una sentinella
ragionevole DENTRO una funzione, che però finisce testuale in un riepilogo
per un umano.

È la classe che questo ramo cura da stanotte — un input incompleto che
produce un numero plausibile invece di dichiarare che non lo sa: il campo
`surface` che defaultava a "sdk", il pannello che diceva «nothing lost» su
un gateway senza le rotte, il contatore dei vivi senza la sua formula.
Un numero falso è peggio di un buco: il buco lo vedi.
"""
from __future__ import annotations

import pytest

from verimem.briefing import get_briefing
from verimem.client import Memory


class _AgentParziale:
    """Ciò che un utente SDK può davvero costruire: solo il tier semantico."""

    def __init__(self, mem: Memory) -> None:
        self.semantic = mem.semantic
        self.memory = None
        self.skills = None


@pytest.fixture()
def agent_parziale(tmp_path):
    m = Memory(tmp_path / "memory.db")
    m.add("the office headquarters are in Milan", topic="hq",
          verified_by=["doc"])
    return _AgentParziale(m)


def test_niente_meno_uno_nel_testo_del_briefing(agent_parziale):
    b = get_briefing(agent=agent_parziale)
    testo = b["summary_text"]
    assert "-1" not in testo, (
        f"un numero inventato e' peggio di un buco: {testo!r}")


def test_dice_che_il_tier_non_e_disponibile(agent_parziale):
    b = get_briefing(agent=agent_parziale)
    testo = b["summary_text"].lower()
    assert "unavailable" in testo or "not available" in testo, (
        f"deve DICHIARARE l'indisponibilita', non tacerla: {testo!r}")
    # e il tier che c'e' resta un numero vero
    assert "1 fact" in b["summary_text"], b["summary_text"]


def test_gli_esiti_non_si_dichiarano_a_zero_se_non_si_sanno(agent_parziale):
    """«0 success, 0 failure» su un corpus con 405 success è una bugia
    tanto quanto -1: se il tier episodi non risponde, non si contano."""
    testo = get_briefing(agent=agent_parziale)["summary_text"]
    assert "0 success" not in testo, testo


def test_le_stats_restano_machine_readable(agent_parziale):
    """La cura è nel TESTO per l'umano; il dict `stats` deve restare
    leggibile da un programma — None dichiara l'assenza meglio di -1."""
    b = get_briefing(agent=agent_parziale)
    st = b["stats"]
    assert st.get("episodes") is None, st
    assert st.get("skills") is None, st
    assert st.get("facts") == 1, st
