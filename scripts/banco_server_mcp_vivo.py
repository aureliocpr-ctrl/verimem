"""L'ULTIMA PORTA: il SERVER MCP vivo, parlato dal protocollo.

    python scripts/banco_server_mcp_vivo.py

PERCHE'. Dal 02/09 dichiaro «NON VERIFICATO» sul server MCP, e alle 20:22 ho
tolto quel marchio a SDK e alla FUNZIONE `_avvisi_di_lettura` — ma non al
server. La differenza non e' formale: fra la funzione e il protocollo c'e' la
serializzazione, il router dei tool e il contratto della risposta, e un campo
puo' sparire in ognuno dei tre. **Questo banco parla al server sul suo stdio,
in JSON-RPC, come farebbe un agente vero.**

PREDIZIONE SCRITTA PRIMA (2026-09-03 20:33):
  (1) il server risponde a `tools/list` e fra i tool c'e' una porta di lettura
      della memoria semantica;
  (2) SENZA la variabile, una domanda fuori dominio torna con
      `sotto_il_pavimento.pavimento` ~= 0.8805;
  (3) CON `ENGRAM_AVVISO_MIN_RELEVANCE=0.95`, la stessa domanda torna 0.95.
CONDIZIONE D'USCITA:
  (2) e (3) confermate ⇒ il «NON VERIFICATO» si toglie anche per il server e
      le TRE porte sono provate sul corpus vivo dal loro protocollo.
  il campo NON esce dal protocollo ⇒ **il difetto sta fra funzione e rete**, ed
      e' esattamente quello che ho dichiarato di temere: si apre un reperto.

⚠️ COSTO E CAUTELA: il server carica il prodotto intero. Un solo processo, lo si
chiude sempre (`finally`), timeout su ogni lettura. Aurelio e' al PC.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

import verimem  # noqa: E402


def _manda(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def _leggi(proc, atteso_id=None, secondi=180):
    """Legge righe JSON-RPC finche' trova la risposta con quell'id."""
    scadenza = time.time() + secondi
    while time.time() < scadenza:
        riga = proc.stdout.readline()
        if not riga:
            return None
        riga = riga.strip()
        if not riga or not riga.startswith("{"):
            continue
        try:
            d = json.loads(riga)
        except json.JSONDecodeError:
            continue
        if atteso_id is None or d.get("id") == atteso_id:
            return d
    return None


def _avvia(var=None):
    env = dict(os.environ)
    env.pop("ENGRAM_AVVISO_MIN_RELEVANCE", None)
    if var:
        env["ENGRAM_AVVISO_MIN_RELEVANCE"] = var
    return subprocess.Popen(
        [sys.executable, "-m", "verimem.cli", "mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", cwd=str(RADICE), env=env)


def _handshake(proc):
    _manda(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "ws1-riscontro", "version": "1"}}})
    r = _leggi(proc, 1)
    _manda(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    return r


def _nomi_tool(proc):
    _manda(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    r = _leggi(proc, 2) or {}
    return [t.get("name") for t in (r.get("result") or {}).get("tools", [])]


def _chiama(proc, nome, args, idx):
    _manda(proc, {"jsonrpc": "2.0", "id": idx, "method": "tools/call",
                  "params": {"name": nome, "arguments": args}})
    return _leggi(proc, idx)


def _cerca_pavimento(oggetto):
    """`sotto_il_pavimento` ovunque sia annidato nella risposta."""
    if isinstance(oggetto, dict):
        if "sotto_il_pavimento" in oggetto:
            return oggetto["sotto_il_pavimento"]
        for v in oggetto.values():
            t = _cerca_pavimento(v)
            if t:
                return t
    elif isinstance(oggetto, list):
        for v in oggetto:
            t = _cerca_pavimento(v)
            if t:
                return t
    elif isinstance(oggetto, str) and "sotto_il_pavimento" in oggetto:
        try:
            return _cerca_pavimento(json.loads(oggetto))
        except json.JSONDecodeError:
            return {"grezzo": oggetto[:300]}
    return None


def giro(var, nome_tool, query):
    proc = _avvia(var)
    try:
        _handshake(proc)
        r = _chiama(proc, nome_tool, {"query": query, "k": 5}, 3)
        return _cerca_pavimento(r), r
    finally:
        try:
            proc.stdin.close()
        except Exception:  # noqa: BLE001
            pass
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            proc.kill()


def main():
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | SERVER MCP vivo, parlato in JSON-RPC su stdio",
          flush=True)
    proc = _avvia()
    try:
        h = _handshake(proc)
        print(f"  initialize -> {'OK' if h else 'NESSUNA RISPOSTA'}", flush=True)
        if not h:
            print("STOP: il server non risponde all'handshake.", flush=True)
            return 2
        nomi = _nomi_tool(proc)
        print(f"  tools/list -> {len(nomi)} tool", flush=True)
        # ⚠️ NON SI SCEGLIE PER NOME: `hippo_recall` e' la porta degli EPISODI e
        # non produce l'avviso — interrogandola avevo quasi gridato a un difetto
        # inesistente. I due tool che chiamano davvero `_avvisi_di_lettura` sono
        # `hippo_facts_search` e `hippo_facts_recall`, letti nel dispatcher
        # (`mcp_server.py` righe 12667 e 14016).
        cand = [n for n in nomi
                if n in ("hippo_facts_search", "hippo_facts_recall")]
        print(f"  porte che emettono l'avviso: {cand}", flush=True)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            proc.kill()
    if not cand:
        print("STOP: nessun tool di recall trovato: il banco non sa quale porta "
              "interrogare.", flush=True)
        return 2

    tool = cand[0]
    q = "ricetta carbonara guanciale pecorino uova"
    for eti, var in (("senza la variabile", None), ("con 0.95", "0.95")):
        sp, grezza = giro(var, tool, q)
        if not sp:
            print(f"  {eti:22} NESSUN `sotto_il_pavimento` NELLA RISPOSTA", flush=True)
            # ⚠️ PRIMA DI GRIDARE AL DIFETTO SI GUARDA LA RISPOSTA: il campo puo'
            # mancare perche' il server non lo manda, oppure perche' il tool che
            # ho scelto non e' la porta che lo produce. Sono due reperti diversi.
            print(f"  {'':22} RISPOSTA GREZZA: {json.dumps(grezza)[:700]}", flush=True)
        else:
            print(f"  {eti:22} {json.dumps(sp)[:200]}", flush=True)
    print(f"RIGA tool={tool}", flush=True)
    print("PREDIZIONE (scritta prima): senza -> ~0.8805; con -> 0.95. Se il campo "
          "non esce dal protocollo, il difetto sta fra funzione e rete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
