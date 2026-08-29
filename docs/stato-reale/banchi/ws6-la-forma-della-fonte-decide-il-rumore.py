"""Lo stesso claim, due forme di fonte: L4.2 avvisa solo sulla NOSTRA.

Nasce dal fronte di ws3 («il corpus su cui validiamo non somiglia al cliente»:
51,9% dei nostri span con righe a colonne) e lo lega al reperto di ws4 su L4.2
(«8 falsi allarmi su 8 su source tabellare»). La domanda, una sola: il falso
allarme dipende dal CLAIM o dalla FORMA DELLA FONTE?

ESITO misurato il 2026-08-29 alle 19:20, porta SDK, modello vero, fuori pytest,
UNO STORE NUOVO PER OGNI CELLA:

    claim VERO  «Il magazzino di Verona contiene 480 pallet.»
      fonte TABELLARE (nostra)      -> model_claim 99.8  layer ['L4.2']   <- falso allarme
      fonte PROSA (tipo-cliente)    -> model_claim 98.3  layer (nessuno)
    claim FALSO «…contiene 999 pallet.»
      fonte TABELLARE               -> quarantined 0.4   ['L4.1','L4-grounding']
      fonte PROSA                   -> quarantined 0.6   ['L4.1','L4-grounding']

DUE CONCLUSIONI, e la prima e' quella che rende leggibile la seconda:
 ① LA PROSA NON E' CIECA. Il claim falso e' quarantinato in ENTRAMBE le forme,
    con gli STESSI due layer e grounding quasi identico. La protezione non
    dipende dalla forma della fonte. Se fosse stato il contrario, il reperto
    sarebbe stato l'opposto e molto peggiore.
 ② IL FALSO ALLARME DI L4.2 ESISTE SOLO SULLA TABELLARE. Stesso claim, stessa
    cifra, stessa verita': cambia solo la forma, e su prosa L4.2 tace.

⇒ LA DIREZIONE: ogni tasso di rumore misurato sul nostro corpus SOVRASTIMA
quello di un cliente che indicizza verbali e contratti. Dipingiamo il prodotto
PEGGIORE di com'e' — e il nostro corpus e' tabellare per COSTRUZIONE, perche'
O3 impone di salvare output di strumenti come source.
⚖️ Non e' un'assoluzione: L4.2 sbaglia davvero. Cambia CHI lo paga.

⚠️ LIMITI: un claim, una coppia vero/falso, una lingua, una porta. E' una
DIREZIONE, non una frequenza: non estrapolare un tasso da qui. Il grounding
scende da 99.8 a 98.3 sulla prosa e NON so perche'.
⚠️ PRIMO GIRO SCARTATO: con lo stesso store per le due forme la seconda
scrittura tornava `duplicate` e il layer mascherava il confronto. Uno store
nuovo per cella non e' pignoleria: senza, il numero non e' leggibile.

    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-la-forma-della-fonte-decide-il-rumore.py tabellare
    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-la-forma-della-fonte-decide-il-rumore.py prosa
"""
import sys

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir, "
    "e una tempdir NUOVA per ogni forma.")

from verimem import Memory  # noqa: E402

FONTI = {
    "tabellare": ("inventario --sede verona\n"
                  "  sede        Verona\n"
                  "  pallet      480\n"
                  "  aggiornato  2026-08-29"),
    "prosa": ("Il presente verbale attesta che, alla data odierna, il magazzino "
              "di Verona contiene 480 pallet, regolarmente censiti dall'ufficio "
              "logistico."),
}

POPOLAZIONI = (
    ("VERO  (480)", "Il magazzino di Verona contiene 480 pallet."),
    ("FALSO (999)", "Il magazzino di Verona contiene 999 pallet."),
)


def main() -> None:
    forma = sys.argv[1] if len(sys.argv) > 1 else "tabellare"
    if forma not in FONTI:
        raise SystemExit(f"forma sconosciuta: {forma!r} — usa: {sorted(FONTI)}")
    print(f"=== {forma.upper()} — le due popolazioni")
    for etichetta, claim in POPOLAZIONI:
        m = Memory()
        r = m.add(claim, topic=f"banco/{etichetta[:5].strip()}", source=FONTI[forma])
        avvisi = r.get("warnings") or []
        layer = [(x.get("layer") if isinstance(x, dict) else str(x)) for x in avvisi]
        print(f"  {etichetta}: status={r.get('status'):<12} "
              f"grounding={r.get('grounding_score'):>5.1f}  layer={layer or '(nessuno)'}")


if __name__ == "__main__":
    main()
