"""T-MAP-11 — il limite che avevo DICHIARATO, adesso misurato: quanto costa la
fascia [40, 80) sul LATO BUONO?

Su HaluEval i positivi erano frasi prese ALLA LETTERA dal contesto: il caso piu'
facile, e infatti «veri persi 0%». Lo avevo scritto come limite. Qui uso i
positivi VERI del repository — coppie (dialogo, fatto fedele) che stanno nei
test scritti da altri, non da me oggi — e guardo dove cadono rispetto a 80.

Se anche uno solo cade nella fascia, la mia cura quarantina un fatto che il
dialogo dice davvero, e va detto prima che lo scopra un utente.

    python ws3_quanto_costa_la_fascia_sul_lato_buono.py <wt>
"""
from __future__ import annotations

import pathlib
import sys

FASCIA_LO, FASCIA_HI = 40.0, 80.0

#: (da dove viene, dialogo, fatto che il dialogo DICE)
CASI = [
    ("tests/test_ingest_keeps_the_moat_score.py:25 — CROSS-LINGUA: dialogo "
     "italiano, fatto in inglese",
     "human: Su quale porta gira il servizio di fatturazione in produzione?\n"
     "assistant: Il servizio di fatturazione ascolta sulla porta 8443 in "
     "produzione, dietro il reverse proxy nginx.",
     "The billing service listens on port 8443."),
    ("tests/test_moat_on_ingest.py:51 — parafrasi inglese",
     "I moved the analytics database to Postgres last quarter, hosted in "
     "eu-west. The team is happy with it.",
     "The analytics database runs on Postgres."),
    ("tests/test_moat_on_ingest.py:51 — seconda lettura dello stesso dialogo",
     "I moved the analytics database to Postgres last quarter, hosted in "
     "eu-west. The team is happy with it.",
     "The analytics database is hosted in eu-west."),
    ("banco del capannone — parafrasi italiana (canone)",
     "user: Quanto costa il capannone 12?\n"
     "assistant: Il canone del capannone 12 e' 5900 euro al mese, e la "
     "consegna e' prevista per il 3 marzo.",
     "Il canone del capannone 12 e' 5900 euro."),
    ("banco del capannone — parafrasi italiana (consegna)",
     "user: Quanto costa il capannone 12?\n"
     "assistant: Il canone del capannone 12 e' 5900 euro al mese, e la "
     "consegna e' prevista per il 3 marzo.",
     "La consegna del capannone 12 e' prevista per il 3 marzo."),
    ("banco del capannone — ASTRATTIVO: il fatto riformula, non copia",
     "user: Quanto costa il capannone 12?\n"
     "assistant: Il canone del capannone 12 e' 5900 euro al mese, e la "
     "consegna e' prevista per il 3 marzo.",
     "Il capannone 12 costa 5900 euro ogni mese."),
]


def main() -> None:
    wt = pathlib.Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(wt))
    from verimem.local_grounding import try_local_score

    print(f"== la fascia trattiene [{FASCIA_LO}, {FASCIA_HI}) · sotto {FASCIA_LO} "
          f"si respinge · da {FASCIA_HI} in su si ammette")
    nella_fascia = 0
    sotto = 0
    for dove, dialogo, fatto in CASI:
        r = try_local_score(dialogo, fatto)
        if r is None:
            print("!! il giudice locale non risponde: misura impossibile")
            return
        s = float(r[0])
        if s < FASCIA_LO:
            esito, sotto = "RESPINTO", sotto + 1
        elif s < FASCIA_HI:
            esito, nella_fascia = "NELLA FASCIA (trattenuto)", nella_fascia + 1
        else:
            esito = "ammesso"
        print(f"  {s:6.2f}  {esito:26s}  {fatto[:52]}")
        print(f"          ({dove})")
    print(f">> fatti VERI che la fascia trattiene: {nella_fascia}/{len(CASI)} · "
          f"respinti gia' prima: {sotto}/{len(CASI)}")


if __name__ == "__main__":
    main()
