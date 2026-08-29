"""Che cosa, nella forma tabellare, fa parlare L4.2: l'ORDINE etichetta/numero.

Il banco gemello (ws6-la-forma-della-fonte-decide-il-rumore.py) mostra CHE la
forma conta. Questo mostra COSA della forma conta, ed e' il pezzo che serve
alla cura.

ATTESA DICHIARATA PRIMA di misurare, e FALSIFICATA: «L4.2 confronta i numeri
posizionalmente (commit b410d594), quindi il colpevole sara' la COMPRESENZA di
piu' numeri». Non era quella.

ESITO misurato il 2026-08-29 alle 19:29, porta SDK, modello vero, fuori pytest,
store NUOVO per ogni cella, stesso claim vero «Il magazzino di Verona contiene
480 pallet.»:

    (a) tabellare completa (baseline)                 -> 99.8  ['L4.2']
    (b) stessa tabella SENZA la riga della data       -> 99.8  ['L4.2']
    (c) stessa tabella con «480  pallet» invece di
        «pallet  480» (grandezza DOPO il numero)      -> 99.6  (nessuno)
    (d) prosa con DUE numeri                          -> 99.1  (nessuno)

 (b) uccide «e' la compresenza di numeri»: un solo numero, e L4.2 parla lo stesso.
 (c) uccide «e' la tabella»: stessa tabella, cambia SOLO l'ordine, e tace.
 (d) conferma dall'altro lato: due numeri in prosa, nessun allarme.
⇒ Resta una sola variabile: l'ORDINE. «pallet 480» fa parlare L4.2, «480 pallet» no.

CONFERMA il reperto di ws4 («L4.2 legge la grandezza a DESTRA del numero») a
VARIABILE SINGOLA: nelle tabelle l'etichetta sta a sinistra, il layer guarda a
destra, non trova la grandezza e avvisa. E chiude la catena con ws3 (il corpus
e' al 51,9% a colonne): il rumore lo paghiamo noi per una convenzione
tipografica, non per una proprieta' vaga della «forma».

PER LA CURA (perimetro di ws4, non mio): leggere la grandezza anche a sinistra,
OPPURE astenersi quando a destra non c'e' nulla che sia una grandezza. La
variante (c) e' la popolazione di controllo: deve restare silenziosa.

LIMITI: un claim, quattro varianti, una lingua (il banco gemello mostra che la
lingua non conta, ma queste quattro celle sono solo IT), una porta. E il codice
di L4.2 NON l'ho letto: ho misurato ingresso e uscita.

    B=docs/stato-reale/banchi/ws6-cosa-della-tabella-attiva-L4-2.py
    for v in a b c d; do HIPPO_DATA_DIR=$(mktemp -d) python $B $v; done
"""
import sys

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir "
    "NUOVA per ogni variante.")

from verimem import Memory  # noqa: E402

CLAIM = "Il magazzino di Verona contiene 480 pallet."

VARIANTI = {
    "a": ("(a) tabellare COMPLETA - baseline",
          "inventario --sede verona\n"
          "  sede        Verona\n"
          "  pallet      480\n"
          "  aggiornato  2026-08-29"),
    "b": ("(b) tabellare SENZA la riga della data - un solo numero",
          "inventario --sede verona\n"
          "  sede        Verona\n"
          "  pallet      480"),
    "c": ("(c) tabellare con la grandezza DOPO il numero",
          "inventario --sede verona\n"
          "  sede        Verona\n"
          "  480         pallet\n"
          "  2026-08-29  aggiornato"),
    "d": ("(d) PROSA con DUE numeri - separa piu-numeri da tabella",
          "Il presente verbale attesta che il magazzino di Verona contiene 480 "
          "pallet, con aggiornamento al 2026-08-29 da parte dell'ufficio logistico."),
}


def main() -> None:
    v = sys.argv[1] if len(sys.argv) > 1 else "a"
    if v not in VARIANTI:
        raise SystemExit(f"variante sconosciuta: {v!r} - usa: {sorted(VARIANTI)}")
    etichetta, fonte = VARIANTI[v]
    m = Memory()
    r = m.add(CLAIM, topic=f"banco/v{v}", source=fonte)
    avvisi = r.get("warnings") or []
    layer = [(x.get("layer") if isinstance(x, dict) else str(x)) for x in avvisi]
    print(etichetta)
    print(f"    status={r.get('status'):<12} "
          f"grounding={r.get('grounding_score'):>5.1f}  layer={layer or '(nessuno)'}")


if __name__ == "__main__":
    main()
