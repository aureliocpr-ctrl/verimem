"""`"auto"` e' un valore legittimo del pavimento su due porte, e un tipo
sbagliato sulla terza. Cosa arriva al chiamante?

DA DOVE VIENE. Ieri notte ho misurato che `ENGRAM_MIN_RELEVANCE` non raggiunge
`hippo_trust_report` (`b0481a07`). Leggendo gli schemi per curare la
descrizione ho visto una seconda asimmetria, questa nei TIPI::

    hippo_facts_recall     min_relevance  type ASSENTE   (la descrizione
    hippo_recall_history   min_relevance  type ASSENTE    ammette "auto")
    hippo_trust_report     min_relevance  {"type": "number", "default": 0.0}

⇒ Le due porte che GESTISCONO `"auto"` non dichiarano un tipo; quella che lo
dichiara `number` non lo gestisce, e nel suo handler fa
`float(arguments.get("min_relevance", 0.0))` — su `"auto"` sarebbe un
`ValueError`.

🔑 LA DOMANDA NON E' «c'e' un'incoerenza» — e' **cosa arriva a chi chiama**.
Tre esiti diversi, e solo uno e' accettabile:
  ① la validazione ferma la chiamata NOMINANDO il tipo        → la porta parla
  ② la chiamata passa e `float("auto")` esplode grezzo        → la porta rompe
  ③ la chiamata passa e il valore viene ignorato in silenzio  → la porta mente

⚖️ NOTA DI CONTESTO, letta prima: dal §305 il server auto-deriva uno schema
LENIENT (tipo ed enum, senza `required`) per ogni tool. Se e' collegato,
l'esito atteso e' ①. **Questo banco esiste per verificarlo, non per assumerlo**:
un validatore che c'e' e non e' agganciato e' la forma di difetto che questa
notte ha incontrato piu' volte.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: un pavimento NUMERICO valido (0.5) deve
essere accettato da tutte e tre le porte. Se una rifiutasse anche quello, la
porta sarebbe rotta per un'altra ragione e il banco misurerebbe altro.
⚠️ LA POPOLAZIONE OPPOSTA — che il VALIDATORE VEDA: un valore fuori tipo su un
campo diverso e dichiarato (`k: "molti"`, `type: integer`) deve essere fermato.
Se passasse, un rifiuto su `min_relevance` non proverebbe nulla sul validatore
e uno zero non sarebbe leggibile.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO con un fatto, porte MCP in-process,
giudice locale ASSENTE per costruzione (nessuno scaricamento). Lo store di
Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-tipo-dichiarato-e-la-parola-auto.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FATTO = "La penale del contratto Rossi e' 120 euro al giorno."
FONTE = "Contratto Rossi, articolo 7: penale di 120 euro al giorno di ritardo."
DOMANDA = "quanto e' la penale del contratto Rossi"

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server

fatto, fonte, domanda = sys.argv[1:4]

def chiama(nome, args):
    """Esito grezzo: cosa vede DAVVERO chi chiama la porta."""
    try:
        out = asyncio.run(mcp_server._call_tool_impl(nome, args))
        testo = out[0].text
        try:
            d = json.loads(testo)
        except Exception:
            return {"esito": "testo", "dettaglio": testo[:180]}
        if isinstance(d, dict) and d.get("error"):
            return {"esito": "rifiutata", "dettaglio": str(d.get("error"))[:180]}
        n = len(d.get("results") or d.get("facts") or d.get("items") or [])
        return {"esito": "accettata", "dettaglio": f"min_relevance={d.get('min_relevance')} n={n}"}
    except Exception as e:
        return {"esito": f"ECCEZIONE {type(e).__name__}", "dettaglio": str(e)[:180]}

chiama("hippo_remember", {"proposition": fatto, "source": fonte, "topic": "tip/x"})

PORTE = ("hippo_facts_recall", "hippo_recall_history", "hippo_trust_report")
righe = []
for porta in PORTE:
    for etichetta, extra in (("pavimento 0.5 (CONTROLLO)", {"min_relevance": 0.5}),
                             ('pavimento "auto"', {"min_relevance": "auto"})):
        r = chiama(porta, {"query": domanda, "k": 5, **extra})
        righe.append({"porta": porta, "caso": etichetta, **r})

# POPOLAZIONE OPPOSTA: il validatore vede un tipo sbagliato su un ALTRO campo?
r = chiama("hippo_trust_report", {"query": domanda, "k": "molti"})
righe.append({"porta": "hippo_trust_report", "caso": 'k="molti" (VALIDATORE)', **r})

print(json.dumps(righe, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, FATTO, FONTE, DOMANDA],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-400:]}")
        return 1
    righe = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  {'porta':<22} {'caso':<26} {'esito':<12} dettaglio")
    print("  " + "-" * 100)
    for r in righe:
        print(f"  {r['porta']:<22} {r['caso']:<26} {r['esito']:<12} "
              f"{r['dettaglio'][:44]}")

    def _get(porta: str, caso_prefisso: str) -> dict:
        for r in righe:
            if r["porta"] == porta and r["caso"].startswith(caso_prefisso):
                return r
        return {"esito": "?", "dettaglio": ""}

    print("\n  [1] CONTROLLO — pavimento numerico 0.5 accettato da tutte e tre:")
    ok_controllo = True
    for porta in ("hippo_facts_recall", "hippo_recall_history",
                  "hippo_trust_report"):
        r = _get(porta, "pavimento 0.5")
        segno = "SI" if r["esito"] == "accettata" else "NO"
        print(f"      {porta:<22} {segno}  ({r['esito']})")
        ok_controllo &= (r["esito"] == "accettata")
    if not ok_controllo:
        print("      CONTROLLO CADUTO: una porta rifiuta anche un pavimento")
        print("      valido ⇒ il banco misurerebbe un guasto diverso da quello")
        print("      che dichiara. NESSUN VERDETTO.")
        return 1

    val = _get("hippo_trust_report", 'k="molti"')
    print(f"\n  [2] POPOLAZIONE OPPOSTA — il validatore VEDE un tipo sbagliato "
          f"({'k=\"molti\"'}): {val['esito']}")
    if val["esito"] == "accettata":
        print("      Il validatore non e' agganciato su questa porta ⇒ un")
        print("      eventuale rifiuto su `min_relevance` non proverebbe nulla.")
        print("      NESSUN VERDETTO sul validatore.")
        return 1

    print("\n  ══ VERDETTO ══")
    tr = _get("hippo_trust_report", 'pavimento "auto"')
    fr = _get("hippo_facts_recall", 'pavimento "auto"')
    print(f"     `\"auto\"` su facts_recall : {fr['esito']} — {fr['dettaglio'][:60]}")
    print(f"     `\"auto\"` su trust_report : {tr['esito']} — {tr['dettaglio'][:60]}")
    if tr["esito"] == "rifiutata":
        print("     🟢 ① LA PORTA PARLA: il tipo dichiarato viene fatto")
        print("     rispettare e il rifiuto e' esplicito. L'asimmetria fra le")
        print("     tre porte resta, ma NON produce un crash ne' un silenzio.")
    elif tr["esito"].startswith("ECCEZIONE"):
        print("     🔴 ② LA PORTA ROMPE: il tipo e' dichiarato ma non fatto")
        print("     rispettare, e il chiamante riceve un'eccezione grezza.")
    elif tr["esito"] == "accettata" and "min_relevance=0" in tr["dettaglio"]:
        print("     🔴 ③ LA PORTA MENTE: `\"auto\"` passa e viene ignorato in")
        print("     silenzio — chi lo chiede crede di avere il pavimento")
        print("     auto-calibrato e non ha nessun pavimento.")
    else:
        print(f"     🟡 esito non previsto dalle tre forme: {tr}")

    print("\n  ⚠️ LIMITI: un fatto, una domanda, un solo valore fuori tipo, un")
    print("     solo campo di controllo. NON misura le altre ~210 porte, ne'")
    print("     se `\"auto\"` calcoli un pavimento SENSATO dove e' accettato:")
    print("     misura solo che cosa riceve chi lo passa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
