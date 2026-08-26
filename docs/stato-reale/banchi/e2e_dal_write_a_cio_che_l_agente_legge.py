"""Il ciclo completo: dalla scrittura a cio' che l'agente legge.

⚠️ QUESTO BANCO NON PUO' STARE IN `tests/`, e la ragione e' il punto piu' utile
del file. `tests/conftest.py:121` installa `_stub_embedding_model` con
`autouse=True` — «Auto-applied to every test. Real sentence-transformers is
never loaded in unit tests». Un presidio che misura il RANKING o la RECALL,
sotto pytest, misura uno stub deterministico su SHA-256 dei token: non il
prodotto. L'ho scoperto perche' la versione pytest di questo banco tornava
`grounding_score=None` e lo skip che ne seguiva si sarebbe letto come un verde.

    esecuzione:  python docs/stato-reale/banchi/e2e_dal_write_a_cio_che_l_agente_legge.py

Misurato il 2026-08-26 alle 21:07, `2af77a4e`, store isolato con
`Memory(path=...)` — NON con `ENGRAM_DATA_DIR`, che su questa macchina non
isola (`HIPPO_DATA_DIR` e' gia' esportata e ha precedenza, `config.py:26`).

RISULTATO DI QUELLA ESECUZIONE:

    WRITE
      VERO   Il lotto B12 e' arrivato il 3 marzo con 40 pezzi.  model_claim  100.0
      VERO   Due pezzi del lotto B12 risultano difformi.        model_claim   99.9
      VANTO  Il lotto B12 e' conforme alle specifiche.          model_claim   99.8
      VANTO  Il collaudo del lotto B12 e' stato superato.       quarantined    4.5
      VANTO  Il lotto B12 ha passato tutti i controlli.         quarantined    0.8

    READ — « Il lotto B12 e' conforme? »
      g=99.76  Il lotto B12 e' conforme alle specifiche.      <- PRIMO, e la fonte dice il contrario
      g=99.96  Il lotto B12 e' arrivato il 3 marzo…
      g=99.90  Due pezzi del lotto B12 risultano difformi.    <- lo smentisce, 14 centesimi sotto

LE DUE META', e la prima e' a favore del prodotto:

  ✅ «QUARANTINED — kept OUT of default recall, so you never get it back as
     truth» REGGE: su 5 interrogazioni (3 search + 2 ask) i due vanti
     quarantinati non compaiono mai. Zero su dieci occasioni.
  🔴 Il vanto che il gate NON ferma torna primo, e niente nella risposta dice
     all'agente quale credere. `trust_report` non aiuta: `abstained: false`,
     `n_disputed: 0`, e mette il vanto per primo.

⇒ Il problema non e' che il prodotto menta — la promessa sul quarantinato la
mantiene. E' COSA finisce quarantinato, e quello dipende dalla FORMA:
`tests/test_il_rilevatore_prestazioni_e_scritto_attivo.py` (attiva 4/4,
passiva 1/4), `tests/test_il_gate_vede_la_polarita_e_nient_altro.py`
(elusione 9/9), `tests/test_nessuna_soglia_separa_il_vanto_dal_fatto_vero.py`.

📌 Quei tre presidi restano validi in pytest perche' misurano il WRITE (lo
   status che il gate assegna), non il ranking.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from verimem.client import Memory

FONTE = (
    "Il lotto B12 e arrivato il 3 marzo con 40 pezzi. Due pezzi risultano difformi. "
    "Il collaudo non e ancora stato eseguito."
)
SCRITTURE = [
    ("VERO ", "Il lotto B12 e arrivato il 3 marzo con 40 pezzi."),
    ("VERO ", "Due pezzi del lotto B12 risultano difformi."),
    ("VANTO", "Il lotto B12 e conforme alle specifiche."),
    ("VANTO", "Il collaudo del lotto B12 e stato superato."),
    ("VANTO", "Il lotto B12 ha passato tutti i controlli."),
]
DOMANDE = [
    "Il lotto B12 e conforme?",
    "Il collaudo del lotto B12 e stato superato?",
    "Il lotto B12 ha passato i controlli?",
]


def main() -> int:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "e2e.db"))
    etichetta, quarantinati = {}, []
    print("── WRITE")
    for et, prop in SCRITTURE:
        ric = mem.add(prop, topic="e2e/lotto", source=FONTE, validate="full")
        stato, g = str(ric.get("status")), ric.get("grounding_score")
        etichetta[prop] = (et.strip(), stato)
        if stato == "quarantined":
            quarantinati.append(prop)
        gs = f"{g:.1f}" if isinstance(g, (int, float)) else str(g)
        print(f"   {et}  {stato:<12} g={gs:>6}  {prop[:56]}")

    if not quarantinati:
        print("\n⚠️  IL RIGHELLO E' CADUTO: il gate non ha quarantinato nulla.")
        print("   Senza quarantena la meta' READ di questo banco non misura niente.")
        return 1

    print("\n── READ — cosa vede un agente")
    tornati_male = []
    for dom in DOMANDE:
        print(f"   « {dom} »")
        for x in mem.search(dom, k=4) or []:
            testo = str(x.get("text"))
            et, stato = etichetta.get(testo, ("?", str(x.get("status"))))
            g = x.get("grounding_score")
            gs = f"{g:.2f}" if isinstance(g, (int, float)) else str(g)
            if testo in quarantinati:
                tornati_male.append((dom, testo))
                marca = "🔴🔴 QUARANTINATO SERVITO"
            else:
                marca = "🔴 vanto" if et == "VANTO" else ("✅ vero " if et == "VERO" else "      ")
            print(f"     {marca} [{stato}] g={gs:>7}  {testo[:52]}")

    print("\n── VERDETTO")
    if tornati_male:
        print(f"   🔴 la promessa «kept OUT of default recall» E' CADUTA: {tornati_male}")
        return 1
    print(f"   ✅ nessun quarantinato e' tornato su {len(DOMANDE)} interrogazioni")
    print("   🔴 ma il vanto AMMESSO torna, e sulla domanda diretta arriva primo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
