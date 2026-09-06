"""U-B passo 5 — l'audit dalla porta MCP: dice CHI ha fatto COSA? E i RIFIUTI ci entrano?

    python ws7-u-b-passo-5-l-audit-dalla-porta-mcp.py

⏱️ **FINESTRA DICHIARATA: 600 s** (atteso ~90 s col daemon acceso).
⚡ Store TEMPORANEO, mai quello di Aurelio. Daemon ACCESO per non incappare in T1.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il passo 5 di U-B («qualcuno chiede cosa e' successo») era marcato **NON
MISURABILE** dal banco SDK, e per una ragione mia: `mcp_audit.log` lo scrive
**solo il server MCP** (`mcp_server.py:887`). Cercavo il registro di una porta
usandone un'altra. Qui il passo si esegue **sulla porta giusta**, e con esso
diventa decidibile il criterio di arrivo di U-B, che chiede 2 + 4 + 5.

━━ E MISURA ANCHE T6, CHE AVEVO CLASSIFICATO SENZA VERIFICARLO ━━━━━━━━━━━━━━
**T6 = P1**: «le chiamate rifiutate per validazione non entrano in
`mcp_audit.log`». L'ho classificato il 04/09 **su un reperto di Corrado, senza
rieseguirlo**, e l'ho scritto nel documento («non verificato da me»). Qui c'e' il
braccio che lo prova: **una chiamata volutamente invalida** (un parametro fuori
schema) e poi si conta se il registro la nomina.
⚠️ Se T6 cade, il livello cade con lui, e lo dico con la stessa energia con cui
l'ho dato: **un ticket dato su un reperto altrui vale finche' qualcuno non lo
riesegue, e chi lo riesegue puo' essere chi l'ha classificato.**
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FONTE = ("Verbale riunione infrastruttura del 3 settembre: il servizio checkout "
         "usa Stripe come fornitore di pagamenti dal 2024.")


def parla(store: Path, richieste: list[dict]) -> tuple[list[dict], str]:
    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = str(store)
    env["ENGRAM_DATA_DIR"] = str(store)
    env["ENGRAM_ENCODE_SERVICE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    ingresso = "".join(json.dumps(r) + "\n" for r in richieste)
    p = subprocess.run([sys.executable, "-m", "verimem.mcp_server"], input=ingresso,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=env)
    fuori = []
    for riga in p.stdout.splitlines():
        riga = riga.strip()
        if riga.startswith("{"):
            try:
                fuori.append(json.loads(riga))
            except json.JSONDecodeError:
                pass
    return fuori, p.stderr


def main() -> None:
    store = Path(tempfile.mkdtemp(prefix="iris-ub5-"))
    print(f"  store TEMPORANEO: {store}")
    print("  finestra dichiarata: 600 s (atteso ~90 s col daemon)")

    richieste = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "iris-ub5", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        # due scritture VALIDE, da due "scrittori" diversi
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "hippo_remember",
                    "arguments": {"proposition": "Il fornitore di pagamenti del "
                                  "servizio checkout e' Stripe.",
                                  "source": FONTE, "topic": "ub5"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "hippo_facts_search",
                    "arguments": {"query": "fornitore di pagamenti", "limit": 5}}},
        # ⚠️ IL BRACCIO DI T6: una chiamata VOLUTAMENTE INVALIDA.
        # `hippo_facts_recall` ha `maximum: 50` nello schema (reperto di Giano):
        # k=100 viene RIFIUTATO dalla validazione, prima di arrivare al tool.
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "hippo_facts_recall",
                    "arguments": {"query": "fornitore", "k": 100}}},
    ]
    risposte, err = parla(store, richieste)
    esiti = {r.get("id"): r for r in risposte if "id" in r}
    print(f"  risposte ricevute: {sorted(k for k in esiti if k is not None)}")

    rifiutata = esiti.get(4, {})
    testo_rif = json.dumps(rifiutata, ensure_ascii=False)
    print(f"  la chiamata id=4 e' stata RIFIUTATA dalla validazione? "
          f"{'maximum' in testo_rif or 'validation' in testo_rif.lower()}")
    print(f"    -> {testo_rif[:180]}")

    log = store / "mcp_audit.log"
    print()
    print(f"  === il registro esiste? {log.exists()} ===")
    if not log.exists():
        altri = sorted(p.name for p in store.rglob("*") if p.is_file())
        print(f"    file nello store: {altri[:12]}")
        raise SystemExit("  ⛔ nessun mcp_audit.log: il passo 5 NON PASSA "
                         "(e stavolta la porta e' quella giusta)")

    righe = [json.loads(r) for r in log.read_text(encoding="utf-8").splitlines()
             if r.strip().startswith("{")]
    print(f"  righe nel registro: {len(righe)}")
    campi = sorted({k for r in righe for k in r})
    print(f"  campi: {campi}")
    chi = [c for c in campi if any(s in c.lower() for s in
                                   ("princip", "client", "agent", "user", "who"))]
    cosa = [c for c in campi if any(s in c.lower() for s in ("tool", "method", "op"))]
    print(f"  dice CHI: {chi or 'NESSUN CAMPO'} · dice COSA: {cosa or 'NESSUN CAMPO'}")
    for r in righe:
        print("   ·", json.dumps({k: r.get(k) for k in (cosa + ["outcome", "latency_ms"])
                                  if k in r}, ensure_ascii=False)[:150])

    # ── T6: il RIFIUTO e' nel registro? ─────────────────────────────────────
    print()
    corpo = json.dumps(righe, ensure_ascii=False)
    tracce = [r for r in righe if "recall" in json.dumps(r, ensure_ascii=False)]
    print("  === T6: la chiamata RIFIUTATA compare nel registro? ===")
    print(f"    righe che nominano 'recall': {len(tracce)}")
    print(f"    il registro nomina un rifiuto/errore? "
          f"{any(s in corpo.lower() for s in ('reject', 'invalid', 'error', 'denied', 'validation'))}")
    for t in tracce[:3]:
        print("     ", json.dumps(t, ensure_ascii=False)[:200])

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps({"righe_registro": righe, "campi": campi,
                                 "risposta_rifiutata": rifiutata},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")
    shutil.rmtree(store, ignore_errors=True)


if __name__ == "__main__":
    main()
