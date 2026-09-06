"""LIVELLO: la porta SDK `Memory` su store ISOLATO in tempdir, con i metodi di
`DocumentIndex` avvolti da un contatore. Nessun giudice (niente `source`), nessuno slot.

Il tier Documents e' INDICIZZATO (59 documenti, 683 chunk, banco 98fa7c82).
Qualcuno lo LEGGE dal flusso normale della porta SDK?

    python docs/stato-reale/banchi/ws3-chi-attraversa-il-tier-documents.py

⚡ COSTO ZERO. ⛔ Lo store di Aurelio non viene aperto: HIPPO_DATA_DIR e' un tempdir.
Finestra dichiarata: 4 letture + 1 indicizzazione, < 120 s (l'embedder puo' scaldare).

━━ IL DEBITO CHE PAGO, e a chi ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ws6 (msg ce41086374e70018, 04/09): «59 documenti nello store dicono che qualcuno
ha INDICIZZATO, non che qualcuno abbia LETTO. Per l'uso in lettura serve contare
gli attraversamenti». Aveva ragione: il mio banco misurava la scrittura e la
chiamava «usato». Il METODO e' il suo, copiato da
`ws6-chi-attraversa-il-tier-episodi.py`: avvolgere i metodi del tier con un
contatore, eseguire un flusso vero, guardare chi ha letto — e tenere la colonna
delle SCRITTURE come controllo che il contatore conti.

Una cosa in piu' rispetto al suo: il documento indicizzato contiene una parola
INVENTATA («zafferanoide») che nessun fatto contiene. Cosi' l'attraversamento si
legge anche nel RISULTATO: se `recall` la restituisce, ha attraversato il tier;
se il contatore dice «chiamato» ma la parola non torna, ha bussato e basta.

━━ PERCHE' LA DOMANDA E' DIVERSA DA QUELLA DEGLI EPISODI ━━━━━━━━━━━━━━━━━━━━━━
Per gli episodi ws6 ha trovato che `Memory` non ha il tier PER COSTRUZIONE
(`client.py` non nomina EpisodicMemory). Per i documenti `Memory` ce l'ha:
`documents` (client.py:1751), `index_document` (:1786), `search_documents`
(:1798). Quindi «raggiungibile» e' vero. La domanda e' se il FLUSSO NORMALE —
`recall`, `search`, `ask`, quello che un utente chiama senza sapere che esiste
un tier documenti — lo attraversa, o se lo legge solo chi chiama
`search_documents` per nome.

━━ PREDIZIONE, scritta prima di eseguire (05/09 21:20) ━━━━━━━━━━━━━━━━━━━━━━━
    D1 `recall`, `search`, `ask`: ZERO chiamate a DocumentIndex.search, e la
       parola inventata NON torna. Il tier e' raggiungibile solo per nome.
       🔴 muore se una delle tre lo attraversa E restituisce la parola: allora
       il tier e' vivo nel flusso e «indicizzato ma non letto» e' falso.
    D2 `search_documents` esplicito: 1 chiamata e la parola torna
       (CONTROLLO POSITIVO: se non torna, l'indice o il contatore non
       funzionano e il banco non decide niente).
    D3 CONTROLLO: le SCRITTURE (`index_file`/`index_document`) sono > 0,
       altrimenti il contatore non conta e lo zero delle letture non e' uno zero.

━━ ESITO, 05/09 21:24, main 5d7152d8, entrambi i controlli accesi ━━━━━━━━━━━━━
    fase                                 chiamate a DocumentIndex        la parola torna?
    scrittura di 1 fatto (senza fonte)   — NESSUNA —                     no
    indicizzazione del documento         index_document x1, index_file x1
    recall                               — NESSUNA —                     no
    search                               — NESSUNA —                     no
    ask                                  — NESSUNA —                     no
    search_documents (per nome)          search x1                       SI
    LETTURE 1 ['search'] · SCRITTURE 2 ['index_document', 'index_file']
    D3 ok · D2 ok · D1 REGGE — il tier si legge solo per nome.

⇒ La formulazione giusta, come per gli episodi di ws6 ma con una causa diversa:
  non «il tier non e' raggiungibile» (lo e': `search_documents`), ma **«il
  flusso normale della porta SDK non lo attraversa»**. Un utente che indicizza
  un documento e poi chiama `recall` non lo ritrova; lo ritrova solo se sa che
  esiste `search_documents`. Il mio banco 98fa7c82 diceva «usato»: era
  «indicizzato». ws6 aveva ragione, e la correzione sta anche li'.

━━ COSA NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Una porta sola (SDK). La CLI e MCP hanno i loro comandi/tool per i documenti
(`verimem index`, `hippo_document_search`): se lo attraversino dal loro flusso
normale e' un'altra cella, per porta. E «non attraversato dal flusso» non e'
«inutile»: e' «l'utente deve sapere che esiste» — cioe' un fatto di superficie,
che tocca a ws7 pesare.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
from collections import Counter

_tmp = tempfile.mkdtemp(prefix="ws3_tier_documents_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
import verimem  # noqa: E402
from verimem import Memory  # noqa: E402
from verimem.document_index import DocumentIndex  # noqa: E402

LETTURE = ("search", "stats")
SCRITTURE = ("index_document", "index_file")
PAROLA = "zafferanoide"

conta: Counter = Counter()


def _spia(nome: str) -> None:
    originale = getattr(DocumentIndex, nome)

    def avvolto(self, *a, **k):
        conta[nome] += 1
        return originale(self, *a, **k)

    avvolto.__name__ = getattr(originale, "__name__", nome)
    setattr(DocumentIndex, nome, avvolto)


for _n in LETTURE + SCRITTURE:
    if hasattr(DocumentIndex, _n):
        _spia(_n)


def contiene(risultato) -> bool:
    try:
        return PAROLA in json.dumps(risultato, default=str, ensure_ascii=False).lower()
    except Exception:  # noqa: BLE001
        return PAROLA in repr(risultato).lower()


def main() -> None:
    print("IMPORT DA", verimem.__file__)
    print("CHI ATTRAVERSA IL TIER DOCUMENTS, contando le chiamate su un flusso vero\n")

    m = Memory()
    doc = pathlib.Path(_tmp) / "inventario.txt"
    doc.write_text(
        "Inventario del deposito di Mantova.\n"
        f"Il pallet {PAROLA} del deposito di Mantova pesa 713 chili ed e' in banchina 4.\n"
        "Il deposito ha quattro banchine e un montacarichi.\n", encoding="utf-8")
    QUERY = f"quanto pesa il pallet {PAROLA} del deposito di Mantova"

    fasi: list[tuple[str, Counter, bool]] = []

    def _fase(nome: str, azione) -> None:
        prima = Counter(conta)
        trovata = False
        try:
            trovata = contiene(azione())
        except Exception as e:  # noqa: BLE001 — il banco misura, non giudica
            print(f"  ({nome} ha sollevato: {str(e)[:70]})")
        fasi.append((nome, Counter(conta) - prima, trovata))

    _fase("scrittura di 1 fatto (senza fonte)",
          lambda: m.add("Il deposito di Mantova ha quattro banchine.", topic="tier/doc"))
    _fase("indicizzazione del documento", lambda: m.index_document(doc, source_id="inventario"))
    _fase("recall", lambda: m.recall(QUERY, k=5))
    _fase("search", lambda: m.search(QUERY, k=5))
    _fase("ask", lambda: m.ask(QUERY, k=5))
    _fase("search_documents (per nome)", lambda: m.search_documents(QUERY, k=5))

    print(f"  {'fase':36s} {'chiamate a DocumentIndex':28s} la parola torna?")
    for nome, delta, trovata in fasi:
        voci = ", ".join(f"{k} x{v}" for k, v in sorted(delta.items())) or "— NESSUNA —"
        print(f"  {nome:36s} {voci:28s} {'SI' if trovata else 'no'}")

    let = sum(v for k, v in conta.items() if k in LETTURE)
    scr = sum(v for k, v in conta.items() if k in SCRITTURE)
    print(f"\n  LETTURE del tier   {let:3d}   {sorted(k for k in conta if k in LETTURE)}")
    print(f"  SCRITTURE nel tier {scr:3d}   {sorted(k for k in conta if k in SCRITTURE)}")

    per_nome = {n: (d, t) for n, d, t in fasi}
    flusso = [per_nome[n] for n in ("recall", "search", "ask")]
    d1 = all(d.get("search", 0) == 0 and not t for d, t in flusso)
    d2 = per_nome["search_documents (per nome)"][0].get("search", 0) >= 1 \
        and per_nome["search_documents (per nome)"][1]
    d3 = scr > 0
    print("\n  D3 CONTROLLO scritture > 0            :", "ok" if d3 else "⚠️ SPENTO: il contatore non conta")
    print("  D2 CONTROLLO search_documents trova   :", "ok" if d2 else "⚠️ SPENTO: indice o contatore rotti")
    if d2 and d3:
        print("  D1 recall/search/ask NON attraversano :",
              "REGGE — il tier si legge solo per nome" if d1
              else "🔴 FALSIFICATA — il flusso normale attraversa il tier")
    else:
        print("  D1: NESSUN VERDETTO, un controllo e' spento.")


if __name__ == "__main__":
    main()
