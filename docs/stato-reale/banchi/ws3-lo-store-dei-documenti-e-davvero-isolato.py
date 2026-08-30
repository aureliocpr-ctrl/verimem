"""«Isolated store — NOT the accepted recall corpus»: il confine fra i documenti
indicizzati e i fatti.

LA PROMESSA, dalla descrizione di `hippo_document_index_file`: *«Index a whole
FILE … extract text -> provenance-anchored chunks -> embeddings … **Isolated
store — NOT the accepted recall corpus.**»*

🔑 PERCHE' QUESTA E NON UN'ALTRA delle cinque affermazioni di quel tool. Le
altre quattro sono presidiate — l'idempotenza da TRE file
(`test_cli_docs.py`, `test_document_index.py`, `test_documents_tier.py`), il
versionamento al cambio e la provenienza dai loro. Questa no.
E se cadesse, cadrebbe nel modo peggiore: **un documento indicizzato NON e'
stato giudicato da nessun moat.** Se i suoi pezzi entrassero nel corpus dei
fatti, il prodotto servirebbe come fatto un testo che nessuno ha verificato —
cioe' la confabulazione che esiste per fermare.

═══════════════════════════════════════════════════════════════════════════════
🔑 DUE CONTROLLI, e servono ENTRAMBI perche' la tesi e' un'ASSENZA:
 ① il documento dev'essere DAVVERO indicizzato — la ricerca sui documenti deve
   trovarlo. Senza, l'assenza dai fatti non prova isolamento: prova che non e'
   stato indicizzato niente.
 ② il richiamo dei FATTI deve funzionare — deve trovare un fatto scritto
   normalmente. Senza, l'assenza del documento non prova isolamento: prova che
   quella porta non risponde a nulla.
⚠️ Uno zero e' leggibile solo quando lo strumento che lo misura ha appena
mostrato di vedere qualcos'altro.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO, porte MCP in-process, giudice locale
assente per costruzione. Il file indicizzato e' temporaneo e il suo contenuto e'
una frase che NON compare da nessun'altra parte. Lo store di Aurelio non e'
toccato.

    python docs/stato-reale/banchi/ws3-lo-store-dei-documenti-e-davvero-isolato.py
"""

from __future__ import annotations

import json
import subprocess
import sys

FIGLIO = r'''
import asyncio, json, os, tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server

def chiama(nome, args):
    return json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)

# Una frase che non esiste altrove: se riemerge, viene DA QUI.
FRASE = "Il capannone di Portogruaro misura 7431 metri quadrati coperti."
DOMANDA_DOC = "quanti metri quadrati misura il capannone di Portogruaro"

# 🔒 LA RADICE CONSENTITA. La prima esecuzione e' stata RIFIUTATA:
# «path is outside the allowed document roots … set ENGRAM_DOC_ROOTS to widen
# it deliberately». Esiste una guardia sui percorsi — giusta, presidiata da
# `tests/security/test_document_index_path_guard.py` — che la DESCRIZIONE del
# tool non nomina. Qui si usa la via che l'errore stesso indica, ed e' un
# reperto a parte: il banco ha scoperto un vincolo leggendo un rifiuto, non la
# documentazione.
_radice = tempfile.mkdtemp()
os.environ["ENGRAM_DOC_ROOTS"] = _radice
percorso = os.path.join(_radice, "scheda.txt")
with open(percorso, "w", encoding="utf-8") as fh:
    fh.write("Scheda immobile.\n" + FRASE + "\nFine scheda.\n")

ind = chiama("hippo_document_index_file", {"path": percorso, "title": "scheda"})

# Il CONTROLLO ②: un fatto ordinario, per provare che la porta dei fatti risponda.
chiama("hippo_remember", {
    "proposition": "La penale del contratto Bianchi e' 90 euro al giorno.",
    "source": "Contratto Bianchi, articolo 4: penale di 90 euro al giorno.",
    "topic": "iso/x"})

FORME = {}

def righe(nome, args, chiavi):
    """⚠️ NON TUTTE LE PORTE RESTITUISCONO UN DICT: la ricerca sui documenti
    restituisce direttamente una LISTA, e la prima stesura chiamava `.get()`
    su di essa (`AttributeError`, il banco morto invece che concluso — che e'
    il comportamento giusto, ma e' la nona volta in una notte che il
    misuratore sbaglia la forma). La forma viene REGISTRATA e stampata."""
    d = chiama(nome, args)
    FORME[nome] = type(d).__name__ + (
        f" chiavi={sorted(d.keys())[:8]}" if isinstance(d, dict)
        else f" len={len(d)}")
    if isinstance(d, list):
        return d, FORME[nome]
    for c in chiavi:
        if isinstance(d.get(c), list):
            return d[c], FORME[nome]
    return [], FORME[nome]

doc_hits, doc_chiavi = righe("hippo_document_semantic_search",
                             {"query": DOMANDA_DOC, "k": 5},
                             ("results", "items", "chunks", "hits"))
fat_hits, fat_chiavi = righe("hippo_facts_recall", {"query": DOMANDA_DOC, "k": 10},
                             ("items", "results", "facts"))
ctl_hits, _ = righe("hippo_facts_recall", {"query": "penale contratto Bianchi", "k": 10},
                    ("items", "results", "facts"))
src_hits, _ = righe("hippo_facts_search", {"query": "Portogruaro", "k": 10},
                    ("items", "results", "facts"))

def testi(hits):
    fuori = []
    for h in hits:
        if isinstance(h, dict):
            fuori.append(str(h.get("text") or h.get("proposition")
                             or h.get("chunk") or "")[:90])
    return fuori

print(json.dumps({
    "indice": {k: ind.get(k) for k in ("ok", "chunks", "n_chunks", "version", "error")},
    "doc_chiavi": doc_chiavi, "fat_chiavi": fat_chiavi,
    "doc_n": len(doc_hits), "doc_testi": testi(doc_hits)[:2],
    "fatti_sulla_domanda_del_doc": len(fat_hits), "fatti_testi": testi(fat_hits)[:3],
    # 🔑 IL CRITERIO VERO: non QUANTI fatti tornano, ma se fra loro ci sia
    # il TESTO DEL DOCUMENTO. Vedi la nota nel banco: contare le righe dava
    # «il confine perde» perche' la porta dei fatti non si astiene mai e
    # restituiva il fatto di CONTROLLO.
    "doc_dentro_i_fatti": [t for t in testi(fat_hits) + testi(src_hits)
                           if "Portogruaro" in t or "7431" in t],
    "controllo_fatti": len(ctl_hits),
    "ricerca_lessicale_portogruaro": len(src_hits), "lessicale_testi": testi(src_hits)[:2],
}, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    d = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  ricevuta dell'indicizzazione : {d['indice']}")
    print(f"  forma ricerca documenti (LETTA): {d['doc_chiavi']}")
    print(f"  forma richiamo fatti    (LETTA): {d['fat_chiavi']}")
    print(f"\n  documenti sulla domanda del doc : {d['doc_n']}")
    for t in d["doc_testi"]:
        print(f"      · {t}")
    print(f"  FATTI sulla domanda del doc     : {d['fatti_sulla_domanda_del_doc']}")
    for t in d["fatti_testi"]:
        print(f"      · {t}")
    print(f"  ricerca lessicale «Portogruaro» : "
          f"{d['ricerca_lessicale_portogruaro']}")
    for t in d["lessicale_testi"]:
        print(f"      · {t}")

    print(f"\n  [1] CONTROLLO — il documento e' DAVVERO indicizzato "
          f"(la ricerca documenti lo trova): {d['doc_n']}")
    if d["doc_n"] <= 0:
        print("      CONTROLLO CADUTO: nessun chunk trovato ⇒ l'assenza dai")
        print("      fatti non prova isolamento, prova che non e' stato")
        print("      indicizzato niente. NESSUN VERDETTO.")
        return 1

    print(f"  [2] CONTROLLO — la porta dei FATTI risponde su un fatto "
          f"ordinario: {d['controllo_fatti']}")
    if d["controllo_fatti"] <= 0:
        print("      CONTROLLO CADUTO: quella porta non risponde a nulla ⇒ uno")
        print("      zero li' non significa «isolato». NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    # ⚠️ PRIMA STESURA: `sporcato = len(fatti) > 0`. SBAGLIATA, e avrebbe
    # pubblicato «il confine perde» — cioe' accusato il prodotto di servire
    # come fatto un testo mai giudicato. Il fatto che tornava era quello di
    # CONTROLLO, restituito perche' la porta dei fatti NON SI ASTIENE (misurato
    # da me stesso alle 23:51 e scritto nella guida: e' il vicino piu' prossimo,
    # non una risposta). Contare le righe non misura la contaminazione: la
    # misura e' se il TESTO del documento compaia fra i fatti.
    # 🔑 A salvarmi e' stato stampare i TESTI, non un controllo automatico.
    sporcato = bool(d["doc_dentro_i_fatti"])
    if not sporcato:
        print("     🟢 LO STORE E' ISOLATO: il testo del documento e'")
        print("     recuperabile dalla ricerca sui documenti e NON compare fra i")
        print("     fatti, ne' dalla porta semantica ne' da quella lessicale.")
        print("     ⚠️ Entrambi i controlli reggono, quindi lo zero e'")
        print("     leggibile. E lo zero e' sul TESTO del documento: la porta")
        print(f"     dei fatti ha comunque risposto ({d['fatti_sulla_domanda_del_doc']} "
              "riga/e), ma con il fatto di CONTROLLO — perche' non si astiene")
        print("     mai. Contare le righe avrebbe detto il contrario.")
    else:
        print("     🔴 IL CONFINE PERDE: un testo indicizzato come DOCUMENTO —")
        print("     che nessun moat ha giudicato — risponde dalla porta dei")
        print("     FATTI. La descrizione promette «NOT the accepted recall")
        print("     corpus».")
        print(f"     testi del documento trovati fra i fatti: "
              f"{d['doc_dentro_i_fatti']}")

    print("\n  ⚠️ LIMITI: un file, una frase, uno store nuovo. NON misura il")
    print("     percorso inverso (un fatto che appaia fra i documenti), ne' cosa")
    print("     accada dopo `hippo_document_promote_chunk`, che e' il modo")
    print("     DICHIARATO per far passare un pezzo di documento nel corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
