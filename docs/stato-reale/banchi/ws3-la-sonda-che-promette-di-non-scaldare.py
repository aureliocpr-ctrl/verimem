"""«the NEXT semantic call pays a ~20s cold-load»: sulla porta MCP quel costo
non si paga mai, e non perche' sia veloce.

LA PROMESSA, dalla descrizione di `hippo_warmup_status`: *«Readiness probe for
semantic recall — PURE, never triggers a model load. … If warm=false, **the
NEXT semantic call (hippo_recall / hippo_facts_recall) pays a ~20s cold-load**;
prefer keyword tools (hippo_facts_search) or retry after warmup.»*

SWEEP DELLA COPERTURA, fatto PRIMA: `git grep -l warmup_status -- tests/` da due
file — `test_l120_si_disarma_quando_il_daemon_c_e.py` (presidia L1.20, non
questa porta) e `test_mcp_server.py` (elenco degli strumenti). ⇒ **Nessuna delle
affermazioni di questa descrizione e' presidiata.**

🔑 LA LETTURA CHE CAMBIA LA DOMANDA. `embedding._delegate_only`, docstring:
*«True in an MCP-server process (`HIPPO_ENCODE_DELEGATE_ONLY=1`): **NEVER
cold-load the model here** — only the shared daemon loads it (once). The daemon
+ CLI leave it unset, so they still load in-process normally.»*
⇒ Sulla superficie MCP — **quella dove vive questa descrizione** — il
caricamento locale e' VIETATO. Le possibilita' per la «prossima chiamata
semantica» sono allora TRE, e la descrizione ne nomina una sola:

    paga ~20s   ·   FALLISCE (nessun daemon)   ·   DEGRADA al ramo lessicale

═══════════════════════════════════════════════════════════════════════════════
🔑 DUE COSE CHE QUESTO BANCO NON PUO' FARE, ed e' meta' del suo risultato:
 ① **la purezza della sonda NON e' misurabile qui.** Il controllo positivo
   sarebbe «una chiamata che DEVE caricare», e in questo regime non esiste:
   sarebbe pura anche una sonda che ci prova, perche' il caricamento e' vietato
   a monte. Un verde qui non proverebbe la promessa.
 ② i «~20s» non si misurano senza pagarli, e dipendono da macchina e cache.
⚠️ E il rilevatore giusto e' `embedding.is_loaded()`, la stessa funzione che usa
la porta (`mcp_server.py:8402`): la prima stesura leggeva `_model is not None`,
che e' True GIA' ALL'AVVIO — il rilevatore non vedeva niente e il «controllo
positivo» rispondeva SI per la ragione sbagliata. Undicesima volta in una notte
che il difetto sta nel misuratore, e la prima in cui a mentire era il CONTROLLO.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, daemon condiviso spento
(`ENGRAM_ENCODE_SERVICE=0`), `HIPPO_ENCODE_DELEGATE_ONLY` come la trova
sull'ambiente — ed e' il valore che conta, quindi il banco lo STAMPA. Lo store
di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-la-sonda-che-promette-di-non-scaldare.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import asyncio, json, os, tempfile, time

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import embedding, mcp_server

def caricato():
    return bool(embedding.is_loaded())

prima = caricato()
t0 = time.perf_counter()
sonda = json.loads(asyncio.run(
    mcp_server._call_tool_impl("hippo_warmup_status", {}))[0].text)
ms_sonda = (time.perf_counter() - t0) * 1000.0
dopo_sonda = caricato()

t1 = time.perf_counter()
errore, esito = None, {}
try:
    r = json.loads(asyncio.run(mcp_server._call_tool_impl(
        "hippo_facts_recall",
        {"query": "quanto costa il piano annuale", "k": 5}))[0].text)
    esito = {"items": len(r.get("items") or []),
             "ranking": str(r.get("ranking"))[:70],
             "error": str(r.get("error"))[:80] if r.get("error") else None}
except Exception as e:
    errore = f"{type(e).__name__}: {str(e)[:110]}"
ms_chiamata = (time.perf_counter() - t1) * 1000.0

print(json.dumps({
    "sonda": {k: sonda.get(k) for k in (
        "warm", "source", "in_process_model_loaded", "daemon_reachable",
        "daemon_usable", "cold_load_estimate_s")},
    "chiavi": sorted(sonda.keys()),
    "prima": prima, "dopo_sonda": dopo_sonda, "dopo_chiamata": caricato(),
    "ms_sonda": round(ms_sonda, 1), "ms_chiamata": round(ms_chiamata, 1),
    "esito": esito, "errore": errore,
    "delegate_only": os.environ.get("HIPPO_ENCODE_DELEGATE_ONLY", ""),
}, ensure_ascii=False, default=str))
'''


def _acceso(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  ricevuta della sonda : {d['sonda']}")
    print(f"  chiavi (LETTE)       : {d['chiavi']}")
    print(f"  HIPPO_ENCODE_DELEGATE_ONLY = "
          f"{d['delegate_only'] or 'non impostata'}")
    print(f"\n  modello in memoria — prima: {d['prima']} · dopo la sonda: "
          f"{d['dopo_sonda']} ({d['ms_sonda']} ms) · dopo la chiamata "
          f"semantica: {d['dopo_chiamata']} ({d['ms_chiamata']} ms)")
    print(f"  esito della chiamata semantica: {d['esito']}"
          + (f"  ECCEZIONE={d['errore']}" if d["errore"] else ""))

    print("\n  ══ ① PUREZZA DELLA SONDA ══")
    if _acceso(d["delegate_only"]):
        print("     ⚪ NON MISURABILE QUI, ed e' il primo reperto: con")
        print("     `HIPPO_ENCODE_DELEGATE_ONLY=1` il caricamento locale e'")
        print("     VIETATO, quindi non esiste una chiamata che «deve caricare»")
        print("     da usare come controllo positivo — sarebbe pura anche una")
        print("     sonda che ci prova. NESSUN VERDETTO su «PURE».")
    elif d["prima"]:
        print("     ⚪ PREMESSA CADUTA: il modello era gia' in memoria all'avvio.")
    elif not d["dopo_chiamata"]:
        print("     ⚪ CONTROLLO CADUTO: nemmeno la chiamata semantica ha")
        print("     caricato ⇒ il rilevatore non vede, e lo zero non significa.")
    else:
        print("     🟢 LA SONDA E' PURA" if not d["dopo_sonda"]
              else "     🔴 LA SONDA SCALDA: chiedere «costa?» costa.")

    print("\n  ══ ② «the NEXT semantic call pays a ~20s cold-load» ══")
    # ⚠️ LA PREMESSA DELLA PROMESSA È «SE warm=false». Col daemon condiviso VIVO
    # la sonda risponde warm=true e il caso NON SI PRESENTA. La prima stesura di
    # questo verdetto lo ha ignorato e ha concluso «HA DEGRADATO» — su uno store
    # VUOTO, dove `ranking: skipped_no_input` dice solo che non c'era niente da
    # fondere. Dodicesima volta in una notte che il difetto sta nel misuratore,
    # e la seconda in cui avrebbe accusato il prodotto.
    if d["sonda"].get("warm"):
        print(f"     ⚪ NON MISURABILE: la sonda risponde warm="
              f"{d['sonda'].get('warm')} (source={d['sonda'].get('source')}) e la")
        print("     promessa vale «SE warm=false»: il caso non si presenta.")
        print("     ⛔ Per crearlo servirebbe spegnere il daemon CONDIVISO, che")
        print("     non è mio: non lo tocco. ⇒ NESSUN VERDETTO.")
        print("     📌 Resta scritto COSA servirebbe: un processo senza daemon")
        print("     raggiungibile e con `HIPPO_ENCODE_DELEGATE_ONLY` spenta —")
        print("     cioè il regime della CLI, non quello del server MCP.")
    elif not (d["esito"] or {}).get("items") and not d["errore"]:
        print("     ⚪ NON MISURABILE: la chiamata non ha restituito nulla su uno")
        print("     store vuoto — «degradato» e «niente da cercare» non si")
        print("     distinguono. Serve un corpus prima di cronometrare.")
    elif d["errore"]:
        print(f"     🔴 NON PAGA: FALLISCE — {d['errore'][:80]}")
        print("     La descrizione promette un'attesa; arriva un errore, e sono")
        print("     due cose diverse per chi deve decidere cosa fare dopo.")
    elif not d["dopo_chiamata"] and d["ms_chiamata"] < 5000:
        print(f"     🔴 NON PAGA: {d['ms_chiamata']:.0f} ms e il modello NON e'")
        print("     caricato ⇒ ha DEGRADATO, il terzo esito che la descrizione")
        print("     non nomina. Chi legge «pagherai ~20s» si aspetta un COSTO e")
        print("     riceve una risposta veloce di QUALITA' diversa — che e'")
        print("     esattamente cio' che la sonda esiste per anticipare.")
    else:
        print(f"     🟢 coerente: {d['ms_chiamata']:.0f} ms, "
              f"modello caricato={d['dopo_chiamata']}.")

    print("\n  📌 REPERTO DI REGIME, e correggo una riga che avevo scritto io:")
    print(f"     ho messo `ENGRAM_ENCODE_SERVICE=0` credendo di spegnere il")
    print(f"     daemon, e la sonda risponde daemon_usable="
          f"{d['sonda'].get('daemon_usable')}, daemon_reachable="
          f"{d['sonda'].get('daemon_reachable')}.")
    print("     ⇒ Quella variabile NON spegne cio' che la sonda guarda: la")
    print("     sonda legge il file di discovery e prova la porta, non")
    print("     l'ambiente del chiamante. Chi la usa per isolare un banco crede")
    print("     di aver spento un daemon che risponde ancora.")

    print("\n  ⚠️ LIMITI: una macchina, un processo, e il daemon condiviso VIVO")
    print("     (non e' mio: non lo spengo). NON misura i «~20s» — dipendono da")
    print("     macchina e cache — e non puo' misurare NESSUNA delle due")
    print("     affermazioni: questo banco documenta PERCHE' non sono")
    print("     verificabili da dentro il processo del server, cosi' chi verra'")
    print("     dopo non ci riprova credendo di poterle misurare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
