"""Una variabile d'ambiente poteva rompere il server MCP.

Il transport stdio possiede **stdout**: ogni byte che non è JSON-RPC rompe il
framing. Il modulo lo sapeva e faceva::

    os.environ.setdefault("HIPPO_LOG_STDERR", "1")

`setdefault` **non sovrascrive**: un ambiente che porta già la variabile a `"0"`
vince, e il server parla su un canale rotto. Misurato il 22/08 su **tre** nomi,
perché il mirror di compatibilità li propaga tutti::

    HIPPO_LOG_STDERR=0     ->  2 righe di log su STDOUT
    ENGRAM_LOG_STDERR=0    ->  2 righe   (mirror ENGRAM_  -> HIPPO_)
    VERIMEM_LOG_STDERR=0   ->  2 righe   (mirror VERIMEM_ -> ENGRAM_ -> HIPPO_)

⛔ E non è una preferenza calpestata: su stdio «log su stdout» non è una
configurazione valida, è un server che non parla. Chi vuole i log altrove ha
`ENGRAM_LOG_LEVEL` e il transport HTTP.

📌 COME CI SONO ARRIVATA: guardavo la ricevuta di `add()` — un altro fronte — e
nell'output di un banco sono passate barre di progresso di HuggingFace. Quelle
vanno su stderr ed erano innocue, **ma accanto c'era una riga `flow.write` su
stdout**. Il difetto non era dove stavo guardando.

⚠️ IL TEST GIRA IN SUBPROCESS, e non è un vezzo: la variabile viene letta
**una volta sola, all'import** di `observability`. In-process il modulo è già
importato e un `monkeypatch.setenv` non cambierebbe nulla — il test passerebbe
sempre, in entrambi gli alberi.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

_PROGRAMMA = textwrap.dedent(
    """
    import asyncio, sys
    import verimem.mcp_server as m

    async def p():
        await m.call_tool("hippo_status", {})

    asyncio.run(p())
    sys.stdout.write("@@FINE@@\\n")
    """
)


def _righe_estranee(variabile: str | None) -> list[str]:
    """Le righe su STDOUT che non sono il marcatore: su stdio sarebbero
    byte non-JSON-RPC in mezzo al protocollo."""
    import os
    env = dict(os.environ)
    env.pop("HIPPO_LOG_STDERR", None)
    env.pop("ENGRAM_LOG_STDERR", None)
    env.pop("VERIMEM_LOG_STDERR", None)
    if variabile:
        env[variabile] = "0"
    r = subprocess.run([sys.executable, "-c", _PROGRAMMA],
                       capture_output=True, text=True, timeout=300, env=env)
    if r.returncode != 0:
        pytest.skip(f"il server non si avvia in questo ambiente: "
                    f"{r.stderr.strip()[-200:]}")
    return [x for x in r.stdout.splitlines() if x.strip() and x.strip() != "@@FINE@@"]


@pytest.mark.parametrize("variabile", [
    "HIPPO_LOG_STDERR",
    "ENGRAM_LOG_STDERR",    # arriva via mirror ENGRAM_ -> HIPPO_
    "VERIMEM_LOG_STDERR",   # arriva via mirror VERIMEM_ -> ENGRAM_ -> HIPPO_
])
def test_nessun_nome_della_variabile_manda_i_log_su_stdout(variabile):
    """IL CUORE: tre nomi per la stessa variabile, e il mirror li propaga —
    quindi non basta difendersi da quello che il modulo scrive."""
    estranee = _righe_estranee(variabile)
    assert not estranee, (
        f"con {variabile}=0 il server scrive {len(estranee)} righe non-JSON-RPC "
        f"su stdout, e su stdio questo rompe il framing: {estranee[:2]}")


def test_presidio_senza_nessuna_variabile_lo_stdout_resta_pulito():
    """L'altra popolazione: il caso normale non deve essere rotto dalla cura."""
    assert not _righe_estranee(None), (
        "senza nessuna variabile impostata lo stdout non è pulito: la cura "
        "non c'entra, è il canale che perde")
