"""Il nome del tool c'era in due posti e non nella risposta.

L'ultima rete di sicurezza di tutti i tool MCP faceva così::

    log.exception("mcp_tool_failed", tool=name)          # il nome c'è
    _audit(name, arguments, outcome="exception", ...)    # il nome c'è
    return _err(f"{type(exc).__name__}: {exc}")          # il nome NON c'è

⇒ Il nome finiva dove lo legge un **operatore** (log, audit) e mai dove lo legge
**chi ha chiamato**. Un agente che lancia più tool in parallelo riceveva
`KeyError: 'x'` e non sapeva quale dei suoi fosse fallito.

🔑 È l'ultima rete di TUTTI i tool di quel file: qui si finisce solo quando
nessun ramo ha previsto il caso, cioè proprio quando chi legge ha meno contesto
di chiunque.

Il rimando è onesto e non promette una diagnosi che non abbiamo: dice che
l'errore NON è un rifiuto del gate — quelli hanno un messaggio loro — così
l'agente non va a cercare una regola che non ha violato.

📌 MISURATO PRIMA DI CURARE, sull'AST (non con un regex: un regex su strutture
annidate legge la prima chiave e tace sul resto). Delle 129 chiamate a `_err`
con testo leggibile::

    sull'INPUT dell'agente (sa cosa correggere)   80  (62%)
    su STATO INTERNO (non può fare niente)        14  (11%)
    né l'uno né l'altro                           35  (27%)

La superficie è messa bene — «set `perm_shell=true`», «Pick another
shadow_name», «rate limit exceeded — set HIPPO_MCP_RATELIMIT» —, e questo era
il messaggio **più importante del file**, perché è quello che si vede quando
tutto il resto ha fallito.
"""
from __future__ import annotations

import asyncio
import json

import pytest


def _chiama(nome: str, argomenti: dict) -> dict:
    import verimem.mcp_server as m
    r = asyncio.run(m.call_tool(nome, argomenti))
    assert r, "il tool non ha risposto"
    return json.loads(r[0].text)


def test_un_crash_dentro_un_tool_dice_QUALE_tool(monkeypatch):
    """IL CUORE: senza il nome, un agente con più chiamate in volo non sa
    quale delle sue è esplosa."""
    import verimem.retirement_log as rl

    def boom(*a, **k):
        raise KeyError("colonna_che_non_ce")

    monkeypatch.setattr(rl, "quarantine_breakdown", boom, raising=False)
    esito = _chiama("hippo_quarantine_log", {"limit": 2, "breakdown": True})
    assert "error" in esito, f"il crash non è diventato un errore: {esito}"
    assert "hippo_quarantine_log" in esito["error"], (
        f"la risposta non nomina il tool che è esploso: {esito['error']!r}")


def test_il_messaggio_porta_ancora_il_tipo_e_il_testo_dell_eccezione(monkeypatch):
    """Il presidio: nominare il tool non deve far PERDERE ciò che c'era già.
    Un messaggio più leggibile e meno informativo sarebbe un peggioramento."""
    import verimem.retirement_log as rl

    def boom(*a, **k):
        raise KeyError("colonna_che_non_ce")

    monkeypatch.setattr(rl, "quarantine_breakdown", boom, raising=False)
    msg = _chiama("hippo_quarantine_log", {"limit": 2, "breakdown": True})["error"]
    assert "KeyError" in msg, f"perso il tipo dell'eccezione: {msg!r}"
    assert "colonna_che_non_ce" in msg, f"perso il testo dell'eccezione: {msg!r}"


def test_dice_che_NON_e_un_rifiuto_del_gate(monkeypatch):
    """⚖️ La riga che evita la caccia sbagliata: senza, un agente che riceve un
    errore da una memoria-con-gate cerca la regola che ha violato — e non ne ha
    violata nessuna."""
    import verimem.retirement_log as rl

    def boom(*a, **k):
        raise RuntimeError("qualcosa di rotto dentro")

    monkeypatch.setattr(rl, "quarantine_breakdown", boom, raising=False)
    msg = _chiama("hippo_quarantine_log", {"limit": 2, "breakdown": True})["error"]
    assert "NOT a gate refusal" in msg, (
        f"il messaggio non distingue un crash da un rifiuto del gate: {msg!r}")


def test_un_tool_sano_non_e_toccato():
    """L'altra popolazione: la cura sta in un `except`, e un tool che NON
    esplode non deve cambiare comportamento."""
    esito = _chiama("hippo_facts_topics", {"limit": 2})
    assert "error" not in esito, f"un tool sano ora risponde con un errore: {esito}"


@pytest.mark.parametrize("nome", ["hippo_non_esiste_affatto"])
def test_un_tool_sconosciuto_resta_un_messaggio_suo(nome):
    """Il ramo `unknown tool` è un ALTRO messaggio e deve restare distinto: chi
    sbaglia il nome di un tool e chi ne rompe uno hanno due problemi diversi."""
    esito = _chiama(nome, {})
    assert "error" in esito
    assert "unknown tool" in esito["error"], (
        f"un nome sconosciuto non è più distinto da un crash: {esito['error']!r}")
