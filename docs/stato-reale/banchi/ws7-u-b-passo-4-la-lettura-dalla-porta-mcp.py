"""U-B passo 4 — «un terzo legge e riceve SOLO IL CORRENTE», dalla PORTA MCP.

    python ws7-u-b-passo-4-la-lettura-dalla-porta-mcp.py

⏱️ **FINESTRA DICHIARATA: 600 s** (atteso ~90 s col daemon acceso). Si dichiara
PRIMA perche' su questa porta esiste T1: a giudice freddo la risposta puo'
arrivare dopo 313-903 s, e un timeout mio verrebbe scambiato per un'assenza.

━━ PERCHE' ADESSO, E PERCHE' NON DOPO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
La cura di T14 (@ws6 Aldo, `6074ef02`) entra in main al verde della finestra ④.
**Dopo, questo RED non e' piu' dimostrabile su questa porta.** Ordine del lead
(`f0da894d4b03d2ac`): «Iris chiude il passo 4 alla porta MCP entro allora».

━━ IL CRITERIO, SCRITTO PRIMA DI ESEGUIRE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il passo 4 di U-B chiede: *«un terzo che non era presente legge e riceve SOLO il
corrente, e puo' chiedere la storia»*. Sulla porta MCP **passa** se:

    (a) la lettura torna UN fatto solo, ed e' quello nuovo (Adyen);   oppure
    (b) ne torna piu' d'uno, MA il superato porta un segno leggibile
        (`superseded_by`, uno `status`, una nota) che un terzo puo' vedere
        SENZA sapere che esiste.

🔴 **Fallisce** se ne tornano due indistinguibili: allora un terzo che legge
riceve **due fornitori di pagamento diversi** per lo stesso servizio, e nulla
gli dice quale vale — che e' il danno completo di T14 sul percorso di un team.

⚠️ **Cosa questo banco NON misura**: se il gate abbia deciso bene (e' la causa,
gia' trovata da Aldo: `L3-coexistence` scambia il valore che cambia per un
soggetto diverso) e se l'avviso arrivi alla SCRITTURA (misurato a parte,
`ws7-t14-l-avviso-del-conflitto-sulla-porta-mcp.py`). Qui si misura **la
LETTURA**, che e' la cosa che il passo 4 chiede.

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

SEGNI_DI_SUPERAMENTO = ("superseded_by", "superseded", "is_current", "retired",
                        "replaced_by", "valid_until", "status")


def chiama(store: Path, richieste: list[dict]) -> list[dict]:
    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = str(store)
    env["ENGRAM_DATA_DIR"] = str(store)
    env["ENGRAM_ENCODE_SERVICE"] = "1"        # daemon acceso: evita T1
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
    if not fuori:
        print(f"  returncode={p.returncode} · stdout={len(p.stdout)}B")
        for r in p.stderr.strip().splitlines()[-8:]:
            print("   stderr:", r[:150])
    return fuori


def corpo(risposta: dict) -> dict | None:
    """Il payload JSON dentro la risposta MCP, o None."""
    for c in risposta.get("result", {}).get("content", []):
        if c.get("type") == "text":
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return None
    return None


def main() -> None:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    ora = subprocess.run(["date", "+%H:%M:%S"],
                         capture_output=True, text=True).stdout.strip() or "?"
    store = Path(tempfile.mkdtemp(prefix="iris-ub4-"))
    print(f"  REGIME: albero {sha} · ora {ora} · store TEMPORANEO {store}")
    print("  finestra dichiarata: 600 s (atteso ~90 s col daemon)")

    def scrivi(i: int, prop: str, fonte: str, principal: str) -> dict:
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": "hippo_remember",
                           "arguments": {"proposition": prop, "source": fonte,
                                         "topic": "ub4", "principal": principal}}}

    risposte = chiama(store, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "iris-ub4", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        scrivi(2, "Il fornitore di pagamenti del servizio checkout e' Stripe.",
               FONTE_A, "anna"),
        scrivi(3, "Il fornitore di pagamenti del servizio checkout e' Adyen.",
               FONTE_C, "bruno"),
        # IL PASSO 4: un TERZO legge. Non sa niente di quello che e' successo.
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "hippo_facts_search",
                    "arguments": {"query": "fornitore di pagamenti del checkout"}}},
    ])

    per_id = {r.get("id"): r for r in risposte if "id" in r}
    if 3 not in per_id:
        raise SystemExit("  ⛔ la CORREZIONE non ha risposto entro 600 s: NON MISURATO")
    if 4 not in per_id:
        raise SystemExit("  ⛔ la LETTURA non ha risposto entro 600 s: NON MISURATO "
                         "(e non e' un'assenza di risultati)")

    lettura = corpo(per_id[4])
    print()
    print("  === IL PASSO 4: cosa riceve un terzo che legge dalla porta MCP ===")
    if lettura is None:
        raise SystemExit("  ⛔ la lettura non ha restituito JSON: NON MISURATO")

    print("    chiavi della risposta:", sorted(lettura))
    fatti = lettura.get("facts") or lettura.get("results") or lettura.get("items") or []
    if isinstance(fatti, dict):
        fatti = [fatti]
    print(f"    ➜ FATTI RESTITUITI: {len(fatti)}")

    stripe = adyen = 0
    for i, f in enumerate(fatti, 1):
        testo = json.dumps(f, ensure_ascii=False)
        prop = f.get("proposition") or f.get("text") or testo[:90]
        print(f"      [{i}] {str(prop)[:100]}")
        segni = {k: f.get(k) for k in SEGNI_DI_SUPERAMENTO if k in f}
        print(f"          segni di superamento presenti: {segni or 'NESSUNO'}")
        if "stripe" in testo.lower():
            stripe += 1
        if "adyen" in testo.lower():
            adyen += 1

    print()
    print(f"    Stripe (il SUPERATO) compare in {stripe} fatti serviti")
    print(f"    Adyen  (il CORRENTE) compare in {adyen} fatti serviti")

    # il verdetto, contro il criterio scritto PRIMA
    print()
    if len(fatti) == 1 and adyen == 1 and stripe == 0:
        print("    ✅ PASSO 4 PASSA (a): un fatto solo, ed e' il corrente")
    elif stripe and any(any(k in f for k in ("superseded_by", "superseded", "replaced_by"))
                        and f.get("superseded_by") for f in fatti
                        if "stripe" in json.dumps(f, ensure_ascii=False).lower()):
        print("    ✅ PASSO 4 PASSA (b): il superato torna, ma PORTA IL SEGNO")
    elif stripe and adyen:
        print("    🔴 PASSO 4 FALLISCE: il terzo riceve DUE fornitori diversi per lo")
        print("       stesso servizio, e nessuno dei due porta un segno di superamento.")
    else:
        print("    ⚠️ ESITO FUORI DAL CRITERIO — leggere l'uscita, non dedurla")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps({"regime": {"albero": sha, "ora": ora},
                                 "lettura": lettura,
                                 "risposta_correzione": per_id[3]},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  scritto {fuori}")
    shutil.rmtree(store, ignore_errors=True)


if __name__ == "__main__":
    main()
