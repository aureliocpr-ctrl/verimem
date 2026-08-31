"""«provenance on every read» — su quante delle porte pubbliche vale davvero?

PERCHE'. Il Summary del pacchetto **pubblicato** (`v0.7.0:pyproject.toml`) — cioe'
la riga che `pip show verimem` stampa e che apre la pagina PyPI — promette
quattro cose:

    Verified memory for AI agents: gated writes, PROVENANCE ON EVERY READ,
    bi-temporal history, abstention instead of hallucination.

@ws1 (31/08 01:45) ne ha smontata una: **l'astensione vale su `explain` e non su
`search`** (18 sonde su 18 servite), ed e' una differenza di contratto
DOCUMENTATA — non un difetto del prodotto, ma il Summary non la distingue.
`LANT-33` aveva gia' verificato la prima su tre porte.

⇒ Restano **due promesse non verificate per porta**. Questo banco prende la
seconda: **«provenance on EVERY read»** — «every» e' un quantificatore, e un
quantificatore si falsifica con un solo controesempio.

PORTE PUBBLICHE (elenco di @ws1, verificato nei docstring): `search` · `ask` ·
`explain` · `search_documents`. ⚠️ `recall` NON e' una porta pubblica: e'
`mem.semantic.recall`, il livello sotto.

CRITERIO, dichiarato prima di contare: la risposta porta la provenienza se
contiene un riferimento identificabile alla FONTE del fatto. Il banco **stampa
le chiavi di ogni risposta** prima di giudicare, cosi' il criterio e'
contestabile da chi legge invece che nascosto nel codice.

Fuori da pytest, store temporaneo, zero rete.

    python docs/stato-reale/banchi/ws7-provenance-on-every-read-su-quante-porte.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_prov_")

from verimem import Memory  # noqa: E402

FONTE = ("Il bilancio 2025 del comune di Ozzano riporta una spesa corrente di "
         "4,2 milioni di euro e investimenti per 1,8 milioni.")
CLAIM = "La spesa corrente del comune di Ozzano nel 2025 e' di 4,2 milioni di euro."
DOMANDA = "Quanto e' la spesa corrente del comune di Ozzano?"

#: le parole che, in una chiave o in un attributo, indicano provenienza.
#: Dichiarate qui e non dentro un `if`: chi contesta il criterio le vede.
SEGNALI = ("source", "provenance", "citation", "cite", "evidence", "origin",
           "ref", "episode", "document", "offset", "fact_id", "id")


def _chiavi(x, prof: int = 0) -> list[str]:
    """Le chiavi di primo e secondo livello, per stamparle prima di contare."""
    if isinstance(x, dict):
        out = list(x.keys())
        if prof == 0:
            for v in x.values():
                out += [f"·{k}" for k in _chiavi(v, prof + 1)]
        return out
    if isinstance(x, (list, tuple)) and x:
        return _chiavi(x[0], prof)
    if hasattr(x, "__dict__"):
        return [k for k in vars(x) if not k.startswith("_")]
    return []


def main() -> int:
    m = Memory()
    r = m.add(CLAIM, source=FONTE, topic="banco/provenance")
    print(f"  scrittura: status={r.get('status')} "
          f"grounding={r.get('grounding_score')}")

    #: ⚠️ SENZA QUESTO IL BANCO MENTE. La prima esecuzione dava
    #: `search_documents` -> VUOTA, e l'avrei potuta contare come «porta che
    #: non porta la provenienza»: ma era vuota perche' **non le avevo dato
    #: nessun documento da trovare**. Un mio buco di disegno letto come un
    #: difetto del prodotto — il rovescio esatto di «una misura che non c'e'
    #: si legge come perfetta». La porta dei documenti si prova con un
    #: documento indicizzato, o non si prova affatto.
    doc = Path(tempfile.gettempdir()) / "ws7_bilancio_ozzano.txt"
    doc.write_text(FONTE + "\n\nLa delibera e' del 12 marzo 2025.\n",
                   encoding="utf-8")
    try:
        d = m.index_document(str(doc))
        print(f"  documento indicizzato: {str(d)[:90]}\n")
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️ indicizzazione FALLITA ({type(e).__name__}): "
              f"search_documents resta non provata\n")

    PORTE = [
        ("search", lambda: m.search(DOMANDA, k=3)),
        ("ask", lambda: m.ask(DOMANDA)),
        ("explain", lambda: m.explain(DOMANDA)),
        ("search_documents", lambda: m.search_documents(DOMANDA, k=3)),
    ]
    esiti: dict[str, str] = {}
    for nome, chiama in PORTE:
        try:
            out = chiama()
        except Exception as e:  # noqa: BLE001 — una porta assente e' un dato
            esiti[nome] = f"ERRORE {type(e).__name__}"
            print(f"  {nome:<18} ERRORE  {type(e).__name__}: {str(e)[:90]}")
            continue
        ch = _chiavi(out)
        ha = sorted({k for k in ch if any(s in k.lower() for s in SEGNALI)})
        vuota = not out
        esiti[nome] = "VUOTA" if vuota else ("SI" if ha else "NO")
        print(f"  {nome:<18} {esiti[nome]:<6} tipo={type(out).__name__} "
              f"vuota={vuota}")
        print(f"  {'':<18} chiavi: {', '.join(ch[:14]) or '(nessuna)'}")
        print(f"  {'':<18} → di provenienza: {', '.join(ha) or 'NESSUNA'}\n")

    si = sum(1 for v in esiti.values() if v == "SI")
    print(f"  «provenance on every read»: {si}/{len(PORTE)} porte pubbliche")
    print(f"  dettaglio: {esiti}")
    print(f"\n  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
