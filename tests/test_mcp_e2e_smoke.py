"""FORGIA pezzo #28 — End-to-end MCP smoke test (real subprocess).

Existing `tests/test_mcp_server.py` exercises the handlers in-process
with mocked memory/skills. This file fills the remaining E2E gap: it
spawns `python -m verimem.mcp_server` as a real subprocess, feeds
hand-crafted JSON-RPC frames through stdin via `subprocess.communicate`,
and parses every frame the server returns.

Why this approach (vs the official mcp.client.stdio SDK or interactive
pipes): on Windows + pytest-asyncio, the SDK's anyio task groups
deadlock waiting for stdout reads, and interactive Popen.stdin.write /
flush isn't reliably forwarded to the child. `communicate()` with a
pre-built batch of frames works on every platform we care about and is
sufficient for a smoke verification.

What it verifies (all of it in one round-trip, fast):

  1. SUBPROCESS BOOTS — `python -m verimem.mcp_server` starts and
     exits cleanly when stdin closes. No crash on import.

  2. STDOUT IS PROTOCOL-CLEAN — every line on stdout parses as JSON.
     This is the regression guard for the `HIPPO_LOG_STDERR` env-var
     redirection: if structlog ever lands a log line on stdout the
     test fails immediately.

  3. tools/list returns the expected catalog (the 5 user-facing tools
     the README and CLI advertise).

  4. tools/call hippo_status returns a dict with `n_episodes` /
     `n_skills` keys (zero on a fresh tmp data dir).

  5. tools/call hippo_recall on empty memory returns [] without crash.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _frames_in() -> bytes:
    """Build the full JSON-RPC batch we send to the server in one shot."""
    frames = [
        # 1. initialize
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {
             "protocolVersion": "2024-11-05",
             "capabilities": {},
             "clientInfo": {"name": "smoke", "version": "0.0.1"},
         }},
        # 2. initialized notification (required by spec)
        {"jsonrpc": "2.0", "method": "notifications/initialized",
         "params": {}},
        # 3. tools/list
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        # 4. tools/call hippo_status
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "hippo_status", "arguments": {}}},
        # 5. tools/call hippo_recall on empty memory
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "hippo_recall",
                    "arguments": {"query": "anything", "k": 3}}},
    ]
    return ("\n".join(json.dumps(f, separators=(",", ":")) for f in frames)
            + "\n").encode("utf-8")


def _parse_lines(raw: bytes) -> list[dict]:
    """Parse newline-delimited JSON. Skip blank lines but raise on garbage."""
    out: list[dict] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        out.append(json.loads(s))  # raises on log-line contamination
    return out


def _referto(frames: list[dict], proc, secondi: float | None = None) -> str:
    """Il referto di un frame mancante: PICCOLO, e con la causa dentro.

    ⚠️ PERCHÉ ESISTE — il 2026-08-21, run 32475919020 su ``93d5e379``, questo
    test è andato rosso su ``assert 4 in by_id`` e il referto era ``{frames!r}``.
    Misurato in locale: **155.047 caratteri**, perché ``frames`` contiene la
    risposta a ``tools/list``, cioè l'``inputSchema`` di ogni tool esposto.

    Nel log del run quella riga NON c'è (la più lunga arrivata è di 2484
    caratteri) e con lei manca tutta la coda: niente riga di sintesi, niente
    «short test summary», nessun ``##[error]``. Il referto che doveva spiegare
    il rosso è la ragione per cui non si sa perché è rosso.

    E dei 155 KB nemmeno uno serviva: la domanda è «quali id sono arrivati, e
    che errore ha dato il server», non «com'è fatto lo schema di ogni tool».
    Quello che serve sta nello **stderr del server**, che il referto vecchio non
    stampava affatto.
    """
    righe = [f"id ricevuti: {sorted(f['id'] for f in frames if 'id' in f)}"]
    # ⚠️ rc E DURATA — aggiunti dopo il run 32478842864, dove il referto (gia'
    # ridotto) diceva «id ricevuti: [1, 2, 3]» con lo stderr VUOTO. Uno stderr
    # vuoto esclude l'eccezione e lascia in piedi due spiegazioni opposte: il
    # server e' USCITO prima di rispondere, oppure stava ancora lavorando. A
    # separarle bastano due numeri che il referto non aveva:
    #   · rc — se il server e' uscito, con quale codice;
    #   · secondi — se e' andato a sbattere contro il `timeout=60` o se ha
    #     chiuso in un lampo.
    # Un referto che non distingue due cause opposte costa un run intero a chi
    # lo legge; questi due numeri costano due righe.
    righe.append(f"rc del server: {proc.returncode}"
                 + (f" · durata: {secondi:.1f}s" if secondi is not None else ""))
    righe.append(f"byte di stdout: {len(proc.stdout or b'')}")
    for f in frames:
        if "error" in f:
            righe.append(f"  frame id={f.get('id')} ERROR: {f['error']!r}"[:500])
    err = (proc.stderr or b"").decode(errors="replace")
    righe.append(f"stderr del server (coda): {err[-2500:] or '(VUOTO)'}")
    return "\n".join(righe)


@pytest.mark.e2e
def test_mcp_server_e2e_smoke(tmp_path: Path):
    env = os.environ.copy()
    # ⚠️ TUTTI E TRE GLI ALIAS. Con il solo `HIPPO_DATA_DIR` il figlio avvisa
    # «DATA_DIR aliases disagree» e i due alias rimasti puntano alla memoria
    # VERA — misurato il 2026-08-21: ENGRAM_DATA_DIR=C:\Users\aurel\.engram.
    # Qui `HIPPO_DATA_DIR` vince e la produzione non viene toccata, ma un test
    # non deve nemmeno NOMINARE il corpus di produzione: la precedenza e' una
    # convenzione, e le convenzioni cambiano.
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                  "ENGRAM_DIR"):
        env[alias] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"
    env["HIPPO_MCP_DISABLE_RATELIMIT"] = "1"
    env["HIPPO_LOG_LEVEL"] = "ERROR"
    env["PYTHONUNBUFFERED"] = "1"
    # Transport test — isolate it from the startup single-instance guard so it
    # never scans/terminates real system processes during a test run.
    env["HIPPO_REAP_ORPHANS"] = "0"
    # I pin del modello NON passano al figlio, e per SUFFISSO. `conftest.py:11`
    # pinna il modello della SUITE (L12/384); il PRODOTTO usa e5/768
    # (config.py:74) ed è quello che i workflow scaldano. Un server MCP che
    # eredita il pin cerca in CI un modello che nessuno ha scaricato — e
    # `_compat.py:136` propaga ogni `HIPPO_*` su `ENGRAM_*` e `VERIMEM_*`, quindi
    # togliere il solo nome intero non basta (misurato il 2026-08-21 sul presidio
    # multilingue: il figlio ricostruiva il pin dagli alias).
    #
    # ⚠️⚠️ E NON ERA LA CAUSA DEL ROSSO — misurato, non supposto. Con la cura
    # applicata, il run 32478842864 su `82e4b34b` è ancora rosso e stavolta il
    # referto lo dice::
    #
    #     FAILED test_mcp_server_e2e_smoke - AssertionError: id ricevuti: [1, 2, 3]
    #       stderr del server (coda):        <- VUOTO
    #
    # Lo stesso run porta gli altri 21 a verde (16 ERROR + 2 FAILED prima, «1
    # failed, 21 passed, 8 skipped in 112.46s» dopo), quindi la cura serviva
    # altrove: qui no. **Il difetto è un altro e resta aperto**: su Linux il
    # server risponde a 1, 2, 3 e non al 4, senza scrivere una riga di errore.
    #
    # ⚠️ E NON È PERCHÉ `hippo_recall` SIA LENTO — l'avevo scritto come ipotesi
    # («il primo che tocca l'embedder»), poi l'ho cronometrata, ed è falsa. I
    # tempi di arrivo di ogni risposta, misurati con `Popen` in locale::
    #
    #     t=2.86s  id=1    4225 byte
    #     t=2.88s  id=2  144529 byte   (+0.02s)
    #     t=11.29s id=3     430 byte   (+8.41s)   <- hippo_status: il lento è LUI
    #     t=11.29s id=4      91 byte   (+0.00s)   <- hippo_recall: istantaneo
    #
    # Su una memoria vuota `hippo_recall` costa zero, e su Linux il frame 3
    # ARRIVA, cioè gli 8.41 s sono già stati pagati quando il 4 sparisce. Le
    # ipotesi in piedi restano due, opposte, e `_referto` porta `rc` e `durata`
    # apposta per separarle: il server è uscito prima, o stava ancora lavorando.
    #
    # La cura sui pin resta perché è dovuta di suo: un subprocess che deve
    # comportarsi come il prodotto non eredita la configurazione del banco.
    for chiave in [k for k in env
                   if k.endswith(("EMBEDDING_MODEL", "EMBEDDING_DIM"))]:
        env.pop(chiave, None)

    _t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-u", "-m", "verimem.mcp_server"],
        input=_frames_in(),
        capture_output=True,
        env=env,
        timeout=60,
    )
    _secondi = time.monotonic() - _t0
    # Server may exit with non-zero when stdin closes mid-loop on Windows;
    # we don't gate on that. We gate on stdout content.
    stdout = proc.stdout
    assert stdout, (
        f"server produced no stdout. stderr:\n{proc.stderr.decode(errors='replace')[:1500]}"
    )
    frames = _parse_lines(stdout)
    by_id = {f["id"]: f for f in frames if "id" in f}

    # --- 1. Initialize succeeded ---
    assert 1 in by_id, _referto(frames, proc, _secondi)
    init = by_id[1]
    assert init.get("result", {}).get("serverInfo", {}).get("name"), init

    # --- 2. tools/list ---
    assert 2 in by_id, _referto(frames, proc, _secondi)
    tools = by_id[2]["result"]["tools"]
    names = {t["name"] for t in tools}
    for expected_name in ("hippo_run_task", "hippo_consolidate",
                          "hippo_recall", "hippo_status",
                          "hippo_skills_for"):
        assert expected_name in names, (
            f"missing MCP tool: {expected_name}; got {names}"
        )
    for tool in tools:
        assert "inputSchema" in tool, f"{tool['name']} has no inputSchema"

    # --- 3. tools/call hippo_status ---
    # Note: we don't gate on counts here because CONFIG.data_dir is set at
    # config-import time and our HIPPO_DATA_DIR env var is currently a
    # no-op (the production DB at the project root may have leftover
    # episodes from previous CLI runs). We verify the SHAPE of the reply
    # — the smoke test is a transport check, not a state assertion.
    assert 3 in by_id, _referto(frames, proc, _secondi)
    status_text = by_id[3]["result"]["content"][0]["text"]
    payload = json.loads(status_text)
    assert isinstance(payload, dict)
    assert "episodes" in payload, payload
    assert isinstance(payload["episodes"], int)
    assert "skills" in payload and isinstance(payload["skills"], dict)
    assert "active_llm" in payload, payload

    # --- 4. tools/call hippo_recall ---
    assert 4 in by_id, _referto(frames, proc, _secondi)
    recall_text = by_id[4]["result"]["content"][0]["text"]
    hits = json.loads(recall_text)
    assert isinstance(hits, list), f"recall must return a list: {hits!r}"
    # Every hit (if any) must be a dict with the documented keys.
    for hit in hits:
        assert {"id", "task", "outcome", "answer_preview",
                "steps", "similarity"} <= hit.keys(), hit


def test_mcp_server_stdout_is_protocol_clean(tmp_path: Path):
    """Regression: every byte on stdout must be a JSON-RPC frame."""
    env = os.environ.copy()
    # ⚠️ TUTTI E TRE GLI ALIAS. Con il solo `HIPPO_DATA_DIR` il figlio avvisa
    # «DATA_DIR aliases disagree» e i due alias rimasti puntano alla memoria
    # VERA — misurato il 2026-08-21: ENGRAM_DATA_DIR=C:\Users\aurel\.engram.
    # Qui `HIPPO_DATA_DIR` vince e la produzione non viene toccata, ma un test
    # non deve nemmeno NOMINARE il corpus di produzione: la precedenza e' una
    # convenzione, e le convenzioni cambiano.
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                  "ENGRAM_DIR"):
        env[alias] = str(tmp_path)
    env["HIPPO_OFFLINE"] = "1"
    env["HIPPO_MCP_DISABLE_RATELIMIT"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["HIPPO_REAP_ORPHANS"] = "0"  # don't scan/kill system processes in a transport test

    init_only = (
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "clean", "version": "0.0.1"},
            },
        }, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    proc = subprocess.run(
        [sys.executable, "-u", "-m", "verimem.mcp_server"],
        input=init_only, capture_output=True, env=env, timeout=30,
    )
    stdout = proc.stdout.strip()
    # ⚠️ 2026-08-15: senza questa riga il test passava A VUOTO. Il ciclo qui
    # sotto itera su `stdout.splitlines()`: se il server MUORE senza scrivere
    # niente, la lista è vuota, il ciclo non gira e «ogni riga è JSON valido»
    # risulta vero **perché non c'è nessuna riga**. Un verde che non ha
    # guardato niente — e su questo banco varrebbe come prova che lo stdout
    # dell'MCP è pulito, cioè la superficie che il cliente legge.
    # 🔑 Il gemello a riga 105 questo controllo ce l'ha già, e il suo commento
    # dichiara anche perché non si guarda il `returncode` (su Windows il server
    # esce non-zero quando stdin si chiude a metà). Qui mancava: **la stessa
    # cura entrata in una chiamata e non nell'altra, nello stesso file.**
    assert stdout, (
        "il server non ha scritto NIENTE su stdout: senza righe il controllo "
        "qui sotto passerebbe a vuoto invece di provare la purezza del "
        f"protocollo. returncode={proc.returncode} "
        f"stderr:\n{proc.stderr.decode(errors='replace')[:1200]}"
    )
    # Every non-blank line must be valid JSON. No log lines allowed.
    for line in stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            json.loads(s)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"stdout line is not valid JSON-RPC: {s!r} (err: {exc})"
            ) from exc
