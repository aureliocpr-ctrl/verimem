"""La porta MCP espone `superseded_by`, o non lo espone MAI?

    python ws7-la-porta-mcp-espone-superseded-by.py

━━ PERCHE' QUESTO BANCO ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@ws2 Giano (`e03900687ae29250`) ha ragione su una cosa e me l'ha dimostrata col
codice: `include_superseded` e' spento di default e presidiato, quindi se una
lettura MCP restituisce due fatti, la spiegazione piu' semplice e' che **non
siano collegati** — e il difetto sta nel WRITE (T14, di @ws6 Aldo), non nella
porta. **Il controllo che propone: guardare `superseded_by` sui due.**

⇒ Nella mia lettura del passo 4 le chiavi restituite erano:

    confidence · confidence_tier · created_at · grounding_score · id ·
    meta_narrative · proposition · status · topic · verified_by · writer_principal

**`superseded_by` NON c'e'.** Ma questo da solo non prova niente: in quel caso il
campo sarebbe stato nullo comunque, e un campo nullo puo' essere semplicemente
omesso. ⚠️ **Un'assenza si prova ESEGUENDO il caso in cui la cosa DEVE esserci.**

━━ IL CRITERIO, SCRITTO PRIMA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creo una supersessione **esplicita** (`hippo_fact_supersede`), cosi' la relazione
esiste per certo, poi leggo dalla porta MCP.

    ✅ il campo compare sul fatto superato   -> la porta lo espone, e il
                                                controllo di Giano si puo' fare
                                                anche da MCP. Nessun reperto.
    🔴 il campo NON compare                  -> chi lavora dalla porta MCP non
                                                puo' distinguere «due fatti
                                                distinti» da «un corrente e un
                                                superato»: il controllo che
                                                decide non e' disponibile li'.

📏 **Nessun giudice**: si scrive SENZA fonte, perche' qui non serve un giudizio,
serve una relazione. Niente inferenza pesante ⇒ nessuno slot occupato.
⚡ Store TEMPORANEO, mai quello di Aurelio.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def chiama(store: Path, richieste: list[dict]) -> list[dict]:
    env = dict(os.environ)
    env["HIPPO_DATA_DIR"] = str(store)
    env["ENGRAM_DATA_DIR"] = str(store)
    env["PYTHONIOENCODING"] = "utf-8"
    ingresso = "".join(json.dumps(r) + "\n" for r in richieste)
    p = subprocess.run([sys.executable, "-m", "verimem.mcp_server"], input=ingresso,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300, env=env)
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


def corpo(risposta: dict):
    for c in risposta.get("result", {}).get("content", []):
        if c.get("type") == "text":
            try:
                return json.loads(c["text"])
            except json.JSONDecodeError:
                return c["text"]
    return None


def main() -> None:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    ora = subprocess.run(["date", "+%H:%M:%S"],
                         capture_output=True, text=True).stdout.strip() or "?"
    store = Path(tempfile.mkdtemp(prefix="iris-supby-"))
    print(f"  REGIME: albero {sha} · ora {ora} · store TEMPORANEO · nessun giudice")

    def scrivi(i: int, prop: str) -> dict:
        return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                "params": {"name": "hippo_remember",
                           "arguments": {"proposition": prop, "topic": "supby"}}}

    base = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "iris-supby", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        scrivi(2, "Il fornitore di pagamenti del servizio checkout e' Stripe."),
        scrivi(3, "Il fornitore di pagamenti del servizio checkout e' Adyen."),
    ]
    risposte = chiama(store, base)
    per_id = {r.get("id"): r for r in risposte if "id" in r}

    def id_di(n: int) -> str | None:
        d = corpo(per_id.get(n, {}))
        if isinstance(d, dict):
            return d.get("fact_id") or d.get("id")
        return None

    vecchio, nuovo = id_di(2), id_di(3)
    print(f"  scritti: vecchio={vecchio} · nuovo={nuovo}")
    if not (vecchio and nuovo):
        raise SystemExit("  ⛔ non ho gli id delle due scritture: NON MISURATO")

    # ── la supersessione ESPLICITA: la relazione esiste per certo ──
    risposte = chiama(store, base + [
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "hippo_fact_supersede",
                    "arguments": {"old_id": vecchio, "new_id": nuovo}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "hippo_facts_search",
                    "arguments": {"query": "fornitore di pagamenti del checkout",
                                  "include_superseded": True}}},
    ])
    per_id = {r.get("id"): r for r in risposte if "id" in r}

    print()
    print("  === la supersessione esplicita ===")
    esito_sup = corpo(per_id.get(4))
    print("   ", json.dumps(esito_sup, ensure_ascii=False)[:300])
    # 🔑 IL PRESIDIO CHE MANCAVA AL PRIMO GIRO: senza la relazione, l'assenza del
    # campo non dimostra niente — sarebbe nullo comunque. Il banco DEVE fermarsi.
    testo_sup = json.dumps(esito_sup, ensure_ascii=False).lower()
    if (not isinstance(esito_sup, dict)) or "error" in testo_sup or "validation" in testo_sup:
        raise SystemExit("  ⛔ LA SUPERSESSIONE NON E' STATA CREATA ⇒ NON MISURATO. "
                         "Senza la relazione, l'assenza del campo non prova nulla: "
                         "sarebbe nullo in ogni caso. (Al primo giro questo presidio "
                         "non c'era e il banco ha stampato un rosso che non valeva.)")

    lettura = corpo(per_id.get(5))
    print()
    print("  === CONTROLLO POSITIVO: la lettura CHIEDENDO i superati ===")
    if not isinstance(lettura, dict):
        raise SystemExit("  ⛔ lettura non JSON: NON MISURATO")
    items = lettura.get("items") or lettura.get("facts") or []
    print(f"    fatti restituiti: {len(items)}")
    trovato = False
    for f in items:
        chiavi = sorted(f)
        print(f"      {str(f.get('proposition'))[:52]!r}")
        print(f"        chiavi: {chiavi}")
        if any("supersed" in k for k in chiavi):
            trovato = True
            for k in chiavi:
                if "supersed" in k:
                    print(f"        ➜ {k} = {f[k]!r}")

    print()
    if trovato:
        print("    ✅ LA PORTA ESPONE il campo: il controllo di Giano si fa anche da MCP")
    else:
        print("    🔴 NESSUN campo di supersessione nella risposta MCP, nemmeno")
        print("       chiedendo esplicitamente i superati e con la relazione CREATA.")
        print("       ⇒ da questa porta non si distingue «due fatti distinti» da")
        print("         «un corrente e un superato».")

    fuori = Path(__file__).with_suffix(".json")
    fuori.write_text(json.dumps({"regime": {"albero": sha, "ora": ora},
                                 "supersede": corpo(per_id.get(4)),
                                 "lettura": lettura}, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"\n  scritto {fuori}")
    shutil.rmtree(store, ignore_errors=True)


if __name__ == "__main__":
    main()
