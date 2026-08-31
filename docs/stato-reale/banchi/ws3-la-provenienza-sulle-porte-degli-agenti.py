"""«provenance on every read»: sull'SDK si LEGGE la fonte, su MCP no.

DA DOVE VIENE. La matrice promessa x porta di @ws7 (`LANT-130`): la riga ②
*«provenance on every read»* e' misurata **4/4 sulle porte SDK**, e le porte
MCP non le ha nessuno. Questo banco riempie quelle celle.

🔑 IL CRITERIO, DECISO E SCRITTO PRIMA DI MISURARE — e sono TRE cose diverse,
che una casella verde sola confonderebbe:

  A. **LEGGIBILE**  il testo della fonte torna ⇒ chi legge puo' vedere SU COSA
                    si regge il fatto, senza avere altro
  B. **VERIFICABILE** torna un'impronta o un riferimento ⇒ chi ha GIA' la fonte
                    puo' confermarla, ma chi non ce l'ha non la recupera
  C. **GIUDICATO**   torna il VERDETTO (`grounding_score`) ⇒ si sa che una fonte
                    e' stata pesata, non QUALE

⇒ Solo A e' «provenance» nel senso che un lettore intende. C da solo e'
«verdict on every read», che e' una promessa diversa e piu' debole.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: il fatto viene scritto CON una fonte e
CON un `verified_by`, e la scrittura deve risultare giudicata
(`grounding_score` alto). Se il moat non avesse girato, l'assenza della fonte a
valle non direbbe niente sulle porte: direbbe che non c'era una fonte.
⚠️ LE CHIAVI SI LEGGONO dalla ricevuta e la fonte si cerca in TUTTI i campi,
non in quello che ci si aspetta: sull'SDK il campo `source` esiste ed e' None,
mentre il testo sta altrove — cercarlo per nome avrebbe dato «assente» su una
porta che invece la porta.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo per superficie, store TEMPORANEO (entrambi gli alias di
`DATA_DIR`), giudice locale assente per costruzione. Lo store di Aurelio non e'
toccato.

    python docs/stato-reale/banchi/ws3-la-provenienza-sulle-porte-degli-agenti.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FONTE = "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."
ANCORA = "articolo 7"          # il pezzo di fonte che si cerca nelle risposte
RIFERIMENTO = "doc:contratto-rossi:7"

FIGLIO = r'''
import asyncio, json, os, tempfile
d = tempfile.mkdtemp()
os.environ["HIPPO_DATA_DIR"] = d
os.environ["ENGRAM_DATA_DIR"] = d
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

import sys
fonte, ancora, riferimento = sys.argv[1], sys.argv[2], sys.argv[3]
PROP = "La penale del contratto Rossi e' 120 euro al giorno."
Q = "quanto e' la penale del contratto Rossi"

def dove(riga, ago):
    """In QUALE campo compare l'ago. Il nome non si indovina: si trova."""
    if isinstance(riga, dict):
        return [k for k, v in riga.items() if ago in str(v)]
    return ["<riga di testo>"] if ago in str(riga) else []

out = {}

# ── superficie MCP ────────────────────────────────────────────────────────
from verimem import mcp_server
def c(n, a):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(n, a))[0].text)

scritto = c("hippo_remember", {"proposition": PROP, "source": fonte,
                               "topic": "prov/x", "verified_by": [riferimento]})
out["scrittura"] = {k: scritto.get(k) for k in ("status", "grounding_score", "moat")}

for porta, args, chiave in (
        ("hippo_facts_recall", {"query": Q, "k": 5}, "items"),
        ("hippo_facts_search", {"query": Q, "k": 5}, "items"),
        ("hippo_recall_history", {"query": Q, "k": 5}, "context"),
        ("hippo_trust_report", {"query": Q, "k": 5}, "facts")):
    r = c(porta, args)
    righe = r.get(chiave) or []
    prima = righe[0] if righe else None
    out[porta] = {
        "n": len(righe),
        "campi_con_la_fonte": dove(prima, ancora),
        "fonte_nell_intera_risposta": ancora in json.dumps(r, ensure_ascii=False, default=str),
        "verified_by": (prima.get("verified_by") if isinstance(prima, dict) else None),
        "grounding_score": (prima.get("grounding_score") if isinstance(prima, dict) else None),
        "chiavi": sorted(prima.keys()) if isinstance(prima, dict) else type(prima).__name__,
    }

print("MCP=" + json.dumps(out, ensure_ascii=False, default=str))
'''

FIGLIO_SDK = r'''
import json, os, sys, tempfile
d = tempfile.mkdtemp()
os.environ["HIPPO_DATA_DIR"] = d
os.environ["ENGRAM_DATA_DIR"] = d
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()

fonte, ancora, riferimento = sys.argv[1], sys.argv[2], sys.argv[3]
from verimem.client import Memory
m = Memory(os.path.join(tempfile.mkdtemp(), "s.db"))
m.add("La penale del contratto Rossi e' 120 euro al giorno.", source=fonte,
      topic="p/x", verified_by=[riferimento])
h = m.search("quanto e' la penale del contratto Rossi", k=5)
r = h[0] if h else {}
print("SDK=" + json.dumps({
    "n": len(h),
    "campi_con_la_fonte": [k for k, v in r.items() if ancora in str(v)] if isinstance(r, dict) else [],
    "source": r.get("source") if isinstance(r, dict) else None,
    "source_signature": (str(r.get("source_signature"))[:40]
                         if isinstance(r, dict) else None),
    "chiavi": sorted(r.keys()) if isinstance(r, dict) else type(r).__name__,
}, ensure_ascii=False, default=str))
'''


def _run(codice: str) -> dict:
    p = subprocess.run([sys.executable, "-c", codice, FONTE, ANCORA, RIFERIMENTO],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-400:]}")
        return {}
    for riga in reversed(p.stdout.strip().splitlines()):
        if riga.startswith(("MCP=", "SDK=")):
            return json.loads(riga.split("=", 1)[1])
    return {}


def main() -> int:
    mcp = _run(FIGLIO)
    sdk = _run(FIGLIO_SDK)
    if not mcp or not sdk:
        print("\n  NESSUN VERDETTO: una delle due superfici non ha risposto.")
        return 1

    scritto = mcp.get("scrittura", {})
    print(f"  scrittura (con fonte E riferimento): {scritto}")
    gs = scritto.get("grounding_score")
    print(f"\n  [1] CONTROLLO — il moat ha GIUDICATO la fonte: "
          f"grounding_score={gs}")
    if not isinstance(gs, (int, float)) or gs <= 0:
        print("      CONTROLLO CADUTO: nessun giudizio ⇒ l'assenza della fonte a")
        print("      valle non direbbe niente sulle porte. NESSUN VERDETTO.")
        return 1

    print(f"\n  {'superficie':<26} {'n':>2}  campi che contengono la FONTE")
    print("  " + "-" * 76)
    print(f"  {'SDK Memory.search':<26} {sdk.get('n', 0):>2}  "
          f"{sdk.get('campi_con_la_fonte') or 'NESSUNO'}")
    for porta in ("hippo_facts_recall", "hippo_facts_search",
                  "hippo_recall_history", "hippo_trust_report"):
        c = mcp.get(porta, {})
        print(f"  {porta:<26} {c.get('n', 0):>2}  "
              f"{c.get('campi_con_la_fonte') or 'NESSUNO'}"
              + ("" if c.get("campi_con_la_fonte")
                 else f"   (in tutta la risposta: "
                      f"{c.get('fonte_nell_intera_risposta')})"))

    print(f"\n  SDK: source={sdk.get('source')!r} · "
          f"source_signature={sdk.get('source_signature')!r}")
    print(f"  MCP: verified_by={mcp.get('hippo_facts_recall', {}).get('verified_by')} · "
          f"grounding_score={mcp.get('hippo_facts_recall', {}).get('grounding_score')}")

    sdk_legge = bool(sdk.get("campi_con_la_fonte"))
    mcp_legge = any(mcp.get(p, {}).get("campi_con_la_fonte")
                    for p in ("hippo_facts_recall", "hippo_facts_search",
                              "hippo_recall_history", "hippo_trust_report"))

    print("\n  ══ VERDETTO ══")
    print(f"     A. LEGGIBILE (il testo della fonte torna) — SDK: "
          f"{'SI' if sdk_legge else 'NO'} · MCP: {'SI' if mcp_legge else 'NO'}")
    if sdk_legge and not mcp_legge:
        print(f"     🔴 LE DUE SUPERFICI NON MANTENGONO LA STESSA PROMESSA.")
        print(f"     Sull'SDK il testo torna in {sdk.get('campi_con_la_fonte')};")
        print("     su NESSUNA porta MCP torna, in nessun campo.")
        print("     ⇒ Su MCP «provenance on every read» vale nel senso C")
        print("     (il VERDETTO) e in parte nel B (il `verified_by` che il")
        print("     CHIAMANTE ha passato), non nel senso A.")
        print("     ⚠️ E il campo che sull'SDK porta la fonte NON si chiama")
        print("     `source`: quello vale None. Cercarlo per nome avrebbe dato")
        print("     «assente» anche dove la fonte c'e'.")
    elif mcp_legge:
        print("     🟢 anche su MCP il testo della fonte torna: la riga ② regge")
        print("     su entrambe le superfici.")
    else:
        print("     🔴 su NESSUNA delle due superfici il testo della fonte torna:")
        print("     la promessa va riletta ovunque, non solo su MCP.")

    print("\n  ⚠️ LIMITI: un fatto, una fonte, una domanda; `verified_by` passato")
    print("     dal chiamante (senza, quel campo e' vuoto — misurato). NON copre")
    print("     `hippo_document_semantic_search`, che ha una provenienza sua")
    print("     (`file:<id>:<start>-<end>`) gia' misurata dal team all'84,9%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
