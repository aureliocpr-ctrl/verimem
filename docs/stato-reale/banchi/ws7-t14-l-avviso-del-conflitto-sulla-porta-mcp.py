"""T14 — l'avviso del conflitto arriva anche sulla PORTA MCP, o solo dall'SDK?

    python t14_porta_mcp.py

⏱️ **FINESTRA DICHIARATA: 600 s** (atteso ~60 s con il daemon acceso). Il regime
si dichiara PRIMA perche' su questa porta esiste T1: a giudice freddo la risposta
puo' arrivare dopo 313-903 s, e un timeout mio verrebbe scambiato per un'assenza.

━━ PERCHE' QUESTA MISURA DECIDE UN LIVELLO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dall'SDK, la correzione che contraddice un fatto in memoria torna con:

    advice = "il giudice non trova sostegno per questo claim nel fatto in memoria,
              che parla dello STESSO SOGGETTO (fact <id>) — controlla prima di affermare."

T14 e' **P1 e non P0** proprio per quell'avviso: *il prodotto non tace*. La mia
riga per il P0 e' «serve come vero, o TACE, qualcosa che chi legge non ha modo di
controllare». ⇒ Se quell'`advice` **non compare sulla porta MCP**, per l'utente
MCP il prodotto TACE, e **T14 diventa P0 su quella porta**.

⚡ Store TEMPORANEO, mai quello di Aurelio. Daemon ACCESO per non incappare in T1.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FONTE_A = ("Verbale riunione infrastruttura del 3 settembre: il servizio checkout "
           "usa Stripe come fornitore di pagamenti dal 2024.")
FONTE_C = ("Comunicazione al team del 5 settembre: la migrazione del checkout ad "
           "Adyen e' completata, Stripe non e' piu' il fornitore di pagamenti.")


def chiama(store: Path, richieste: list[dict]) -> list[dict]:
    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = str(store)
    env["ENGRAM_DATA_DIR"] = str(store)
    env["ENGRAM_ENCODE_SERVICE"] = "1"        # daemon acceso: evita T1
    env["PYTHONIOENCODING"] = "utf-8"
    ingresso = "".join(json.dumps(r) + "\n" for r in richieste)
    p = subprocess.run([sys.executable, "-m", "verimem.mcp_server"], input=ingresso,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=env)   # <- la finestra
    fuori = []
    for riga in p.stdout.splitlines():
        riga = riga.strip()
        if riga.startswith("{"):
            try:
                fuori.append(json.loads(riga))
            except json.JSONDecodeError:
                pass
    if not fuori:
        print(f"  returncode={p.returncode} · stdout={len(p.stdout)}B")
        for r in p.stderr.strip().splitlines()[-8:]:
            print("   stderr:", r[:150])
    return fuori


def main() -> None:
    store = Path(tempfile.mkdtemp(prefix="iris-t14mcp-"))
    print(f"  store TEMPORANEO: {store}")
    print("  finestra dichiarata: 600 s (atteso ~60 s col daemon)")

    def scrivi(i: int, prop: str, fonte: str) -> dict:
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": "hippo_remember",
                           "arguments": {"proposition": prop, "source": fonte,
                                         "topic": "t14"}}}

    risposte = chiama(store, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "iris-t14", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        scrivi(2, "Il fornitore di pagamenti del servizio checkout e' Stripe.", FONTE_A),
        scrivi(3, "Il fornitore di pagamenti del servizio checkout e' Adyen.", FONTE_C),
    ])

    corr = next((r for r in risposte if r.get("id") == 3), None)
    if corr is None:
        raise SystemExit("  ⛔ la CORREZIONE non ha risposto entro la finestra di 600 s: "
                         "NON MISURATO (e non e' un'assenza di advice)")

    testo = json.dumps(corr, ensure_ascii=False)
    print()
    print("  === la risposta MCP alla CORREZIONE ===")
    for chiave in ("advice", "stesso soggetto", "STESSO SOGGETTO", "controlla prima"):
        print(f"    contiene {chiave!r}: {chiave.lower() in testo.lower()}")
    print()
    # il corpo vero, per leggere invece di dedurre
    for c in corr.get("result", {}).get("content", []):
        if c.get("type") == "text":
            try:
                d = json.loads(c["text"])
            except json.JSONDecodeError:
                print("   (testo non JSON)", c["text"][:300]); continue
            print("    chiavi della ricevuta MCP:", sorted(d))
            for k in ("advice", "adjudication", "moat", "anti_confab_warnings",
                      "warnings", "status", "quarantined_by"):
                if k in d:
                    print(f"      {k} = {json.dumps(d[k], ensure_ascii=False)[:260]}")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps({"risposta_correzione": corr}, ensure_ascii=False,
                                indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")
    shutil.rmtree(store, ignore_errors=True)


if __name__ == "__main__":
    main()
