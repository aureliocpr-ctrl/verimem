"""TDD — ClaudeCLILLM.complete(model=...) deve finire nella riga di comando.

Trovato 2026-07-25 mentre curavo la terza occorrenza dell'incidente Fable: la
firma di ``complete`` espone ``model: str | None = None``, il chiamante crede di
poter scegliere il modello, e il comando costruito e'
``[claude, -p, --output-format, json] + extra_args`` — il parametro non viene mai
letto. Ironia del codice: subito dopo estrae da ``modelUsage`` quale modello ha
risposto, quindi sa che conta, ma non lo controlla.

Non e' una scelta di default imposta all'utente (quella e' una decisione di
prodotto, separata e non presa qui): e' un parametro pubblico ignorato in
silenzio. Chi non passa ``model`` mantiene esattamente il comportamento di prima.
"""
from __future__ import annotations

import json

import pytest

from verimem.llm import ClaudeCLILLM


class _FakeRun:
    """Cattura argv invece di spawnare la CLI. Il fake E' un call-site a tutti
    gli effetti (lezione 2026-07-22: i fake entrano nello sweep come il codice
    vero), quindi restituisce la stessa shape JSON della CLI reale."""

    def __init__(self):
        self.cmd = None

    def __call__(self, cmd, **kw):
        self.cmd = list(cmd)
        return type("P", (), {
            "returncode": 0,
            "stdout": json.dumps({"result": "ok", "usage": {},
                                  "modelUsage": {"claude-opus-4-8": {}}}),
            "stderr": "",
        })()


@pytest.fixture()
def fake(monkeypatch):
    import subprocess
    f = _FakeRun()
    monkeypatch.setattr(subprocess, "run", f)
    return f


def test_model_argument_reaches_the_command_line(fake):
    ClaudeCLILLM().complete("sys", [{"role": "user", "content": "hi"}],
                            model="claude-opus-4-8")
    assert "--model" in fake.cmd, f"model ignorato: {fake.cmd}"
    assert fake.cmd[fake.cmd.index("--model") + 1] == "claude-opus-4-8"


def test_without_model_the_command_is_unchanged(fake):
    """Nessun default imposto: chi non chiede un modello ottiene quello che
    otteneva prima (il default della CLI locale)."""
    ClaudeCLILLM().complete("sys", [{"role": "user", "content": "hi"}])
    assert "--model" not in fake.cmd


def test_explicit_extra_args_still_win(fake):
    """extra_args e' la via che i benchmark usano da sempre: non deve rompersi,
    e non deve finire con due --model in conflitto."""
    ClaudeCLILLM(extra_args=["--model", "claude-sonnet-5"]).complete(
        "sys", [{"role": "user", "content": "hi"}])
    assert fake.cmd.count("--model") == 1
    assert fake.cmd[fake.cmd.index("--model") + 1] == "claude-sonnet-5"
