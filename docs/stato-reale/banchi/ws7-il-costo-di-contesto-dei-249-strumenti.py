"""Quanto contesto si mangia il server MCP di verimem PRIMA che l'utente scriva una riga.

    python -u costo_di_contesto_dei_249.py

E' la misura che manca al ticket T2b (i 249 strumenti) e a T3 (le note interne
nelle descrizioni). Senza di essa non do una gravita': un'osservazione non e'
una misura, e l'ho gia' scritto per il difetto D-5 il 04/09.

COSA MISURA, e perche' proprio questo: un client MCP chiama `tools/list` una
volta per sessione e mette il risultato NEL PROMPT. Quel payload e' il prezzo
fisso che l'utente paga per avere verimem collegato, in ogni singola sessione,
che poi lo usi o no. Quindi la grandezza di prodotto e' **i byte del payload di
tools/list**, non il numero di strumenti: 249 strumenti con una riga di
descrizione costano poco, 249 con dieci righe costano una finestra.

⚠️ REGIME, dichiarato perche' senza non vale: questo NON e' il pacchetto 0.7.6
di PyPI (il venv dell'esercizio non esiste piu' sul disco). E' l'albero
di lavoro locale con il suo venv. Il numero va letto come ordine di
grandezza della superficie, non come «il numero che paga l'utente della 0.7.6»:
chi lo cita lo rifaccia sul wheel pubblicato.
⚠️ NON SCRIVE: store temporaneo in una cartella nuova, mai quello di Aurelio.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

VENV_PY = r"C:\Users\aurel\Code\HippoAgent\.venv\Scripts\python.exe"


def chiedi(py: str, store: Path) -> dict | None:
    env = dict(os.environ)
    env["ENGRAM_DATA_DIR"] = str(store)
    env["VERIMEM_DATA_DIR"] = str(store)
    env["PYTHONIOENCODING"] = "utf-8"
    righe = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "misura-iris", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    ingresso = "".join(json.dumps(r) + "\n" for r in righe)
    p = subprocess.run([py, "-m", "verimem.mcp_server"], input=ingresso,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=240, env=env)
    print(f"  returncode={p.returncode}  stdout={len(p.stdout)}B  stderr={len(p.stderr)}B")
    for riga in p.stdout.splitlines():
        riga = riga.strip()
        if not riga.startswith("{"):
            continue
        try:
            d = json.loads(riga)
        except json.JSONDecodeError:
            continue
        if d.get("id") == 2 and "result" in d:
            return d
    print("  --- ultime righe di stderr ---")
    for r in p.stderr.strip().splitlines()[-12:]:
        print("   ", r[:160])
    return None


def main() -> None:
    py = VENV_PY if Path(VENV_PY).exists() else sys.executable
    print(f"  python: {py}")
    store = Path(tempfile.mkdtemp(prefix="iris-misura-"))
    print(f"  store TEMPORANEO: {store}")

    d = chiedi(py, store)
    if d is None:
        raise SystemExit("  tools/list non e' tornato: nessuna misura, e lo dico "
                         "invece di stimare.")

    strumenti = d["result"]["tools"]
    intero = json.dumps(d["result"], ensure_ascii=False)
    descr = "".join(t.get("description") or "" for t in strumenti)
    nomi = [t["name"] for t in strumenti]
    schemi = json.dumps([t.get("inputSchema") for t in strumenti], ensure_ascii=False)

    print()
    print(f"  strumenti                      : {len(strumenti)}")
    print(f"  col prefisso hippo_            : {sum(1 for n in nomi if n.startswith('hippo_'))}")
    print(f"  col prefisso verimem_          : {sum(1 for n in nomi if n.startswith('verimem_'))}")
    print(f"  PAYLOAD INTERO di tools/list   : {len(intero):,} byte  ~{len(intero)//4:,} token")
    print(f"  di cui descrizioni             : {len(descr):,} byte")
    print(f"  di cui schemi di ingresso      : {len(schemi):,} byte")
    print()

    # T3: le note interne nelle descrizioni. Non le stimo: le CERCO e le conto.
    import re
    marche = {
        "FORGIA": re.compile(r"FORGIA\s*#?\d*", re.I),
        "Round N": re.compile(r"\bRound\s+\d+", re.I),
        "Cycle N": re.compile(r"\bCycle\s*#?\s*\d+", re.I),
        "LOOP N": re.compile(r"\bLOOP\s*#?\s*\d+", re.I),
        "W7-/LANT-": re.compile(r"\b(?:W\d-|LANT-)\d+"),
    }
    print("  --- T3: note interne nelle descrizioni (contate, non stimate) ---")
    colpiti = set()
    for etichetta, rx in marche.items():
        quali = [t["name"] for t in strumenti if rx.search(t.get("description") or "")]
        colpiti.update(quali)
        print(f"    {etichetta:12s} {len(quali):3d} strumenti"
              + (f"   es. {quali[0]}" if quali else ""))
    print(f"    ⇒ strumenti con ALMENO una nota interna: {len(colpiti)} su {len(strumenti)}")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps({
        "regime": "albero di lavoro locale, NON il wheel 0.7.6 di PyPI",
        "python": py,
        "strumenti": len(strumenti),
        "prefisso_hippo": sum(1 for n in nomi if n.startswith("hippo_")),
        "payload_byte": len(intero),
        "payload_token_stimati": len(intero) // 4,
        "descrizioni_byte": len(descr),
        "schemi_byte": len(schemi),
        "strumenti_con_note_interne": sorted(colpiti),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")


if __name__ == "__main__":
    main()
