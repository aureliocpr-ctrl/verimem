"""«gated writes»: le porte che scrivono un fatto sono CINQUE, e due non sono
ne' verdi ne' rosse.

DA DOVE VIENE. Nella matrice promessa x porta di @ws7, la riga ① «gated
writes» e' data per **«regge su 3 porte»** (`LANT-33`). Il censimento degli
strumenti MCP che mettono un FATTO nel corpus ne trova di piu'.

🔑 IL CRITERIO, SCRITTO PRIMA: una porta e' *gated* se **lo stesso testo
auto-affermativo** che `hippo_remember` quarantina viene fermato anche li'.
E servono TRE esiti, non due, perche' una porta puo' ammettere **per disegno
dichiarato** — che non e' un difetto e non e' un verde:

    ✅ FERMA      il gate lo quarantina
    ⚖️ AMMETTE, DICHIARATO   passa, e la porta DICE perche'
    ⚪ NON ESERCITATO        il gate non e' stato raggiunto: la cella e' VUOTA,
                            e una cella vuota NON e' un verde

⚠️ La terza categoria e' il punto di questo banco: **una matrice a due colori
nasconde le celle che nessuno ha provato**, ed e' la classe «una misura che non
c'e' si legge come perfetta».

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: `hippo_remember` DEVE quarantinare il
testo di prova. Se lo ammettesse, il testo non e' discriminante e nessuna delle
altre celle direbbe niente.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO (entrambi gli alias di `DATA_DIR`),
giudice locale assente per costruzione — e quest'ultimo dettaglio E' la ragione
per cui una cella resta vuota, quindi va letto insieme al risultato. Lo store di
Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-le-porte-di-scrittura-non-sono-tre.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import asyncio, json, os, tempfile
d = tempfile.mkdtemp()
os.environ["HIPPO_DATA_DIR"] = d
os.environ["ENGRAM_DATA_DIR"] = d
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server
from verimem.transcript_index import TranscriptIndex, Turn

AUTO = "Ho verificato che il collaudo del capannone Alfa e' concluso con successo."

def c(n, a):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(n, a))[0].text)

def prova(nome, args):
    try:
        r = c(nome, args)
        return {"status": r.get("status"), "stored": r.get("stored"),
                "quarantined_by": r.get("quarantined_by"),
                "extracted": r.get("extracted"),
                "error": (str(r.get("error"))[:70] if r.get("error") else None),
                "chiavi": sorted(r.keys())[:8]}
    except Exception as e:
        return {"eccezione": f"{type(e).__name__}: {str(e)[:70]}"}

celle = {}
celle["hippo_remember"] = prova("hippo_remember", {"proposition": AUTO, "topic": "g/1"})

idx = TranscriptIndex()
tid = idx.store(Turn(text=AUTO, session_id="s1"))
celle["hippo_transcript_promote"] = prova("hippo_transcript_promote",
                                          {"turn_id": tid, "topic": "g/2"})

celle["hippo_ingest_conversation"] = prova("hippo_ingest_conversation", {
    "messages": [{"role": "assistant", "content": AUTO}],
    "conversation_id": "c1", "topic": "g/3"})

percorso = os.path.join(tempfile.mkdtemp(), "conv.json")
with open(percorso, "w", encoding="utf-8") as fh:
    json.dump([{"id": "c1", "messages": [{"role": "assistant", "content": AUTO}]}], fh)
celle["hippo_import_conversations"] = prova("hippo_import_conversations",
                                            {"path": percorso})

print("CELLE=" + json.dumps(celle, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-400:]}")
        return 1
    celle = json.loads([r for r in p.stdout.strip().splitlines()
                        if r.startswith("CELLE=")][-1][6:])

    rem = celle.get("hippo_remember", {})
    print(f"  [1] CONTROLLO — `hippo_remember` quarantina il testo di prova: "
          f"{rem.get('status')} (da {rem.get('quarantined_by')})")
    if rem.get("status") != "quarantined":
        print("      CONTROLLO CADUTO: il testo non e' discriminante ⇒ nessuna")
        print("      delle altre celle dice niente. NESSUN VERDETTO.")
        return 1

    print(f"\n  {'porta':<30} esito")
    print("  " + "-" * 74)
    verdetti = {}
    for porta, r in celle.items():
        if r.get("eccezione"):
            v, nota = "⚪ NON ESERCITATO", r["eccezione"]
        elif r.get("error"):
            v, nota = "⚪ NON ESERCITATO", f"la porta rifiuta la chiamata: {r['error']}"
        elif r.get("status") == "quarantined":
            v, nota = "✅ FERMA", f"quarantined_by={r.get('quarantined_by')}"
        elif r.get("extracted") == 0 or (r.get("stored") == 0
                                         and r.get("status") is None):
            v, nota = "⚪ NON ESERCITATO", ("nessun fatto estratto ⇒ il gate non "
                                           "e' stato raggiunto")
        elif r.get("status"):
            v, nota = "⚖️ AMMETTE", f"status={r.get('status')}"
        else:
            v, nota = "🟡 non classificato", json.dumps(r, ensure_ascii=False)[:70]
        verdetti[porta] = v
        print(f"  {porta:<30} {v}   — {nota}")

    print("\n  ══ VERDETTO ══")
    ferma = sum(1 for v in verdetti.values() if v.startswith("✅"))
    ammette = sum(1 for v in verdetti.values() if v.startswith("⚖️"))
    vuote = sum(1 for v in verdetti.values() if v.startswith("⚪"))
    print(f"     ferma {ferma} · ammette {ammette} · NON esercitate {vuote}"
          f"   (su {len(verdetti)} porte provate)")
    if vuote:
        print("     🔑 LE CELLE VUOTE SONO IL PUNTO: non sono verdi e non sono")
        print("     rosse — nessuno ha esercitato quel gate. In una matrice a due")
        print("     colori sparirebbero, e «non misurato» si leggerebbe «a posto».")
    if ammette:
        print("     ⚖️ E l'AMMISSIONE puo' essere per disegno: `transcript_promote`")
        print("     registra che una cosa e' stata DETTA, non la afferma, e la")
        print("     sua nota lo dichiara. E' una terza categoria, non un rosso.")

    print("\n  ⚠️ LIMITI: un testo, un giro, giudice locale assente — ed e' quella")
    print("     assenza a lasciare vuota la cella dell'ingestione (senza un")
    print("     estrattore non esce nessun fatto da giudicare). `import` chiede")
    print("     un formato di export che NON ho indovinato: la cella resta vuota")
    print("     e dichiarata tale. `document_promote_chunk` non e' qui perche' e'")
    print("     gia' presidiata in tests/test_il_vanto_entrava_dalla_porta_dei_documenti.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
