"""La porta MCP dice che la scadenza ha tolto qualcosa? — eseguendo, non leggendo.

    python docs/stato-reale/banchi/ws6-la-porta-mcp-dice-cosa-ha-tolto.py

Un pari ha misurato staticamente che `esclusi_perche_scaduti` compare in
`client.py` 4 volte, in `cli.py` 2 e in `mcp_server.py` **0** — e ha dichiarato
onestamente «NON VERIFICATO A RUNTIME», cercando anche i sinonimi (`scadut`,
`expired`, `valid_until`, `esclus`, `stale`, `fresh_mask`) per non ripetere
l'errore di contare un identificatore solo. Questo banco chiude quel dubbio
dall'unico lato che lo chiude: eseguendo la porta.

⚠️ E LA PRIMA COSA DA CORREGGERE È QUALE PORTA. `hippo_recall` nell'MCP NON è
la controparte di `Memory.recall`: chiama `a.memory.recall(...)` dove
`a.memory` è `EpisodicMemory()` (`agent.py:62`), e rende EPISODI — `ep.task_text`,
`ep.outcome`, `ep.final_answer`. La porta dei fatti è **`hippo_facts_recall`**.
Confrontare `esclusi_perche_scaduti` con `hippo_recall` sarebbe confrontare due
cose diverse: la stessa classe di errore per cui questo banco, due giorni fa,
interrogava un comando `search` che non esiste.

METODO: si scrive uno store con un fatto vivo e uno scaduto, si chiama
l'handler MCP vero (`_call_tool_impl`, che è `async`) e si guarda il payload
che l'agente riceverebbe. Poi si confronta con ciò che riceve chi usa l'SDK
sulla STESSA domanda e sullo STESSO store.

⚠️ CONTROLLO POSITIVO: la porta deve rispondere e deve servire il fatto VIVO.
Una porta che non risponde non è una porta che tace — e senza questo controllo
un payload vuoto si leggerebbe come «non dichiara».

⚠️ E SI CERCANO I SINONIMI, non un nome: la CLI, misurata due giorni fa,
avvisava con parole proprie senza mai nominare il campo.

⛔ Store isolato in tempdir: non tocca lo store di casa.

═══ ESITO (04/09 19:23) — il pari aveva ragione, e adesso e' ESEGUITO ═══

    SDK (Memory.recall)      risponde=si  dichiara=SI   {"esclusi": 1, ...}
    MCP hippo_facts_recall   risponde=si  dichiara=no   scaduto: no · vivo: SI
    MCP hippo_facts_search   risponde=si  dichiara=SI   scaduto: SI · vivo: SI

🔑 `hippo_facts_recall` TOGLIE il fatto scaduto e NON LO DICE, mentre l'SDK —
stessa domanda, stesso store, stesso istante — lo dichiara. Un agente che passa
di li' riceve una risposta ridotta senza modo di accorgersene: e' la stessa
forma curata su `recall` e su `ask`, un giro dopo e su un'altra porta.

✅ `hippo_facts_search` NON ha il problema, e per una ragione che va detta: non
toglie affatto — SERVE il fatto scaduto e ne parla. Una porta che non toglie
non ha nulla da dichiarare, e metterla nella stessa colonna dell'altra sarebbe
confondere due comportamenti opposti.

⚠️ IL BANCO E' STATO RIFATTO UNA VOLTA, e la prima versione non misurava: usava
«varco nord/sud», e su quella domanda l'SDK stesso taceva (criterio
anticorrelato, `client.py`). Con il metro muto, un «no» sulla porta MCP non
distingue «non espone il campo» da «il campo e' vuoto per tutti».
"""
import asyncio
import json
import os
import sys
import tempfile
import time

_RADICE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, _RADICE)

_tmp = tempfile.mkdtemp(prefix="ws6_mcp_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

#: ⚠️ QUESTI FATTI E QUESTA DOMANDA SONO SCELTI PERCHE' L'SDK QUI DICHIARA.
#: La prima stesura del banco usava «varco nord/sud», e su quella domanda
#: l'SDK stesso NON dichiarava — per il criterio anticorrelato gia' scritto in
#: `client.py`. Con l'SDK muto, un «no» sulla porta MCP non distingue fra «non
#: espone il campo» e «il campo e' vuoto per tutti»: il banco non misurava
#: quello che dice. Serve un caso in cui il metro parla.
VIVO = "Il deposito di Verona custodisce pallet di imballaggi in un'area coperta."
SCADUTO = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
QUERY = "quanti pallet ospita il deposito di Verona"

#: I sinonimi con cui una porta potrebbe dire la stessa cosa senza nominare il
#: campo. Cercarne uno solo e' l'errore che questo banco esiste per non fare.
PAROLE = ("scadut", "esclus", "expired", "valid_until", "esclusi_perche_scaduti",
          "stale", "non serviti", "tolti")

m = Memory()
m.add(VIVO, topic="mcp/vivo")
m.add(SCADUTO, topic="mcp/scaduto", valid_until=time.time() - 86_400)

print("LA PORTA MCP DICE CHE LA SCADENZA HA TOLTO QUALCOSA?\n")

# ── il metro: cosa riceve chi usa l'SDK ───────────────────────────────────
r = m.recall(QUERY, k=10)
sdk_av = getattr(r, "esclusi_perche_scaduti", None)
sdk_testi = [x.get("text", "") if isinstance(x, dict) else str(x) for x in r]
print("  %-26s risponde=%-4s dichiara=%s" % (
    "SDK (Memory.recall)", "si" if sdk_testi else "NO", "SI" if sdk_av else "no"))
if sdk_av:
    print("       %s" % json.dumps(sdk_av, ensure_ascii=False)[:96])

# ── la porta MCP, eseguita ────────────────────────────────────────────────
try:
    from verimem.mcp_server import _call_tool_impl
except Exception as e:                        # noqa: BLE001 — il banco misura
    print("  MCP non importabile: %s" % str(e)[:90])
    raise SystemExit(0) from None

for tool, args in (
    ("hippo_facts_recall", {"query": QUERY, "k": 10}),
    ("hippo_facts_search", {"query": "pallet", "limit": 10}),
):
    try:
        out = asyncio.run(_call_tool_impl(tool, args))
        testo = "".join(getattr(c, "text", "") or "" for c in (out or []))
    except Exception as e:                    # noqa: BLE001 — il banco misura
        testo = "ERRORE: %s" % str(e)[:120]
    risponde = ("pallet" in testo.lower()) or ("Verona" in testo)
    trovate = [p for p in PAROLE if p.lower() in testo.lower()]
    print("  %-26s risponde=%-4s dichiara=%s %s" % (
        "MCP %s" % tool, "si" if risponde else "NO",
        "SI" if trovate else "no", ("(%s)" % ", ".join(trovate)) if trovate else ""))
    #: Si guarda anche se il fatto SCADUTO e' stato servito: se la porta MCP lo
    #: servisse, non avrebbe nulla da dichiarare e la cella andrebbe letta al
    #: contrario — «non toglie» invece di «toglie e tace».
    print("       serve lo scaduto: %s  ·  serve il vivo: %s" % (
        "SI" if "ricambi" in testo else "no", "SI" if "imballaggi" in testo else "no"))

print("\n  ── LETTURA ──")
print("  Il confronto vale solo fra porte che rispondono alla STESSA domanda.")
print("  `hippo_recall` NON e' in tabella apposta: chiama a.memory.recall")
print("  (EpisodicMemory) e rende episodi, non fatti — confrontarlo col campo")
print("  degli scaduti sarebbe confrontare due cose diverse.")
