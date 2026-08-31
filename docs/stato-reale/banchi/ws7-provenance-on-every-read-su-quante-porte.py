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

#: 🔴🪞 31/08 02:52 — LA PRIMA VERSIONE GIUDICAVA SULLE CHIAVI, NON SUI VALORI,
#: e il verde e' finito in una cella pubblicata. @ws3 (02:36) ha misurato che
#: su `search` il campo `source` **esiste ed e' None**, e che il testo della
#: fonte sta in `grounding_span` — verificato qui: `source=None`,
#: `source_signature='sha256:…'` (un'IMPRONTA), `verified_by=[]`,
#: `grounding_span='Il contratto Rossi, articolo 7…'`.
#: ⇒ Avevo scritto «`search` porta `source` + `source_signature`»: **il primo
#: e' vuoto e il secondo non e' la fonte**. Un criterio SINTATTICO (il nome
#: della chiave) su un fenomeno SEMANTICO (la fonte c'e' o no) — la lezione
#: che avevo in testa e non ho applicato al mio stesso banco.
#: 📌 Lo strumento pero' ha fatto la sua parte: **stampava tutte le chiavi**,
#: ed e' per quello che un'altra istanza ha potuto contestarlo.
#:
#: TRE COSE CHE UN VERDE SOLO CONFONDE (classificazione di @ws3):
#:   A LEGGIBILE     torna il TESTO della fonte      -> si vede SU COSA si regge
#:   B VERIFICABILE  torna un'impronta/riferimento   -> conferma chi ce l'ha gia'
#:   C GIUDICATO     torna il VERDETTO               -> si sa CHE e' stata pesata
#: Solo **A** e' «provenance» nel senso che un lettore intende.
#: ⚠️ `_id` ESCLUSO dal TESTO: al primo giro `source_id` finiva in A perche'
#: contiene «source» ed e' una stringa lunga — ma un identificatore non e' la
#: fonte. **Il righello nuovo era peggiore del vecchio in 2 punti su 4** (qui e
#: su `explain`, dove guardavo il livello sbagliato): e' la ragione per cui si
#: fa girare accanto al vecchio prima di pubblicare.
TESTO = ("grounding_span", "passage", "text_source", "quote", "text")
NON_TESTO = ("_id", "_signature", "_ids")
IMPRONTA = ("source_signature", "verified_by", "doc_id", "source_id", "uri",
            "start", "end", "offset", "episode", "ref")
VERDETTO = ("grounding_score", "confidence", "confidence_tier", "provenance",
            "evidence_types", "judge")


def _pieno(v) -> bool:
    """Un campo che c'e' ed e' vuoto NON e' un campo pieno."""
    return not (v is None or v == "" or v == [] or v == {} or v == ())


def classifica(d: dict) -> dict[str, list[str]]:
    """A/B/C con i campi che hanno davvero un VALORE.

    ⚠️⚠️ IL VERDETTO DI QUESTA FUNZIONE E' INDICATIVO, NON PROBANTE — e la
    prova sta nella sua storia: **in dieci minuti ha dato tre esiti diversi**
    sullo stesso store (4/4 -> 3/4 -> 4/4), ogni volta per un difetto diverso
    del criterio, non dei dati:

        ① `source` vuota contata come provenienza  (chiave, non valore)
        ② `source_id` contato come TESTO           (un id non e' la fonte)
        ③ `text` contato come TESTO                (e' il CLAIM, non la fonte)

    ⇒ 🔑 **Un criterio sintattico su un fenomeno semantico sbaglia in
    entrambe le direzioni, e qui l'ha fatto tre volte di fila su me stessa.**
    La classificazione che vale e' quella scritta nella cella `LANT-130`,
    fatta LEGGENDO i campi uno per uno; questa serve a mettere i valori sotto
    gli occhi, che e' cio' che il banco sa fare davvero.

    Il controllo che decide, e non passa da qui: **cercare una frase della
    fonte nella risposta serializzata**. Su `explain` «articolo 7» non compare
    da nessuna parte; su `search` compare.
    """
    out = {"A": [], "B": [], "C": []}
    for k, v in d.items():
        if not _pieno(v):
            continue
        kl = k.lower()
        if any(t in kl for t in NON_TESTO):
            out["B"].append(k)
        elif any(t in kl for t in TESTO) and isinstance(v, str) and len(v) > 30:
            out["A"].append(k)
        elif any(t in kl for t in IMPRONTA):
            out["B"].append(k)
        elif any(t in kl for t in VERDETTO):
            out["C"].append(k)
    return out


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
        #: il primo record, appiattito: e' li' che si guardano i VALORI.
        rec = out
        while isinstance(rec, (list, tuple)) and rec:
            rec = rec[0]
        #: ⚠️ le porte annidano il record dove capita: `ask` sotto `results`,
        #: `explain` sotto `facts`. Al primo giro guardavo solo il primo
        #: livello e `explain` risultava «solo verdetto» — falso: la sua
        #: provenienza sta un piano sotto. **Chi cerca in un solo livello
        #: misura la forma della risposta, non il suo contenuto.**
        for dentro in ("results", "facts", "items"):
            if isinstance(rec, dict) and rec.get(dentro):
                rec = rec[dentro][0]
                break
        d = rec if isinstance(rec, dict) else (vars(rec) if hasattr(rec, "__dict__") else {})
        abc = classifica(d)
        ch = _chiavi(out)
        vuota = not out
        esiti[nome] = ("VUOTA" if vuota
                       else "A" if abc["A"] else "B" if abc["B"]
                       else "C" if abc["C"] else "NO")
        print(f"  {nome:<18} {esiti[nome]:<6} tipo={type(out).__name__} vuota={vuota}")
        print(f"  {'':<18} chiavi: {', '.join(ch[:12]) or '(nessuna)'}")
        for lettera, etichetta in (("A", "TESTO della fonte"),
                                   ("B", "impronta/riferimento"),
                                   ("C", "verdetto")):
            print(f"  {'':<18} {lettera} {etichetta:<22} "
                  f"{', '.join(abc[lettera]) or '—'}")
        vuoti = sorted(k for k, v in d.items()
                       if any(s in k.lower() for s in SEGNALI) and not _pieno(v))
        if vuoti:
            print(f"  {'':<18} ⚠️ chiavi di provenienza PRESENTI e VUOTE: "
                  f"{', '.join(vuoti)}")
        print()

    a = sum(1 for v in esiti.values() if v == "A")
    print(f"  «provenance on every read» LEGGIBILE (A): {a}/{len(PORTE)} porte")
    print(f"  dettaglio: {esiti}")
    print("  ⚠️ A = il testo torna · B = solo un'impronta · C = solo il verdetto")
    print(f"\n  store temporaneo: {os.environ['HIPPO_DATA_DIR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
