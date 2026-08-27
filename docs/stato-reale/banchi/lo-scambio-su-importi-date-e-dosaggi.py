# -*- coding: utf-8 -*-
"""IL LIMITE CHE HO DICHIARATO ALLE 21:55, chiuso sul dominio che conta.

Il banco `lo-scambio-di-attribuzione-elude-la-regex.py` ha misurato cinque
scambi su cinque ammessi a 99.7-100.0, e ne ho dichiarato il limite nello stesso
post: le cifre erano TECNICHE — LOC, cosine, fitness, numeri di riga. «Non ho
provato date, importi, dosaggi, che e' esattamente dove servirebbe saperlo.»

Qui ci sono. Due fonti di dominio, ognuna con piu' grandezze dello STESSO tipo
attribuite a cose diverse — che e' la struttura di un contratto e di un referto:

  CONTRATTO  due penali (2% e 5%), due termini (12 marzo e 30 aprile),
             due importi (148000 e 22000 euro)
  REFERTO    tre dosaggi in mg (850, 5, 100) su tre farmaci diversi

Ogni scambio prende una cifra VERA della fonte e la attribuisce alla cosa
sbagliata. `L4.1` non ha nulla da segnalare per costruzione: la cifra c'e'.

⚠️ LE FONTI SONO COSTRUITE, e lo dichiaro invece di farlo scoprire: non ho un
contratto ne' un referto reale. Sono scritte nella forma del dominio (articoli
numerati, prescrizioni con posologia), e il difetto che misurano non dipende dal
contenuto ma dalla struttura — piu' grandezze omogenee su soggetti diversi.
Chi ha un documento vero rifa' il banco cambiando due stringhe.

IL CRITERIO, scritto prima: se gli scambi entrano anche qui, la classe non e'
un'anomalia di un documento tecnico ma vale dove il prodotto dovrebbe servire.

CONTROLLO CHE DEVE POTER FALLIRE: la cifra di ogni scambio deve stare nella
fonte (altrimenti misuro L4.1), e i claim VERI devono essere ammessi.

    python docs/stato-reale/banchi/lo-scambio-su-importi-date-e-dosaggi.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)

REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera. "
    "Controllo previsto a tre mesi."
)

CASI = [
    # (fonte, etichetta, claim, cifra, e' vero?)
    ("contratto", "VERO   ", "La penale per il ritardo e' pari al 2% dell'importo contrattuale.", "2%", True),
    ("contratto", "VERO   ", "Il termine di consegna e' fissato al 12 marzo 2027.", "12 marzo", True),
    ("contratto", "SCAMBIO", "La penale per il ritardo e' pari al 5% dell'importo contrattuale.", "5%", False),
    ("contratto", "SCAMBIO", "Il termine di consegna e' fissato al 30 aprile 2027.", "30 aprile", False),
    ("contratto", "SCAMBIO", "La cauzione definitiva e' pari a 148000 euro.", "148000", False),
    ("contratto", "SCAMBIO", "L'importo contrattuale e' di 22000 euro.", "22000", False),
    ("referto", "VERO   ", "Il paziente assume metformina 850 mg due volte al giorno.", "850", True),
    ("referto", "SCAMBIO", "Il ramipril e' prescritto a 850 mg al mattino.", "850", False),
    ("referto", "SCAMBIO", "La metformina e' prescritta a 100 mg due volte al giorno.", "100", False),
    ("referto", "SCAMBIO", "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.", "5 mg", False),
]

FONTI = {"contratto": CONTRATTO, "referto": REFERTO}


def main() -> int:
    for nome, _e, claim, cifra, _v in CASI:
        if cifra not in FONTI[nome]:
            print(f"CONTROLLO CADUTO: «{cifra}» non e' nella fonte {nome},")
            print(f"   quindi «{claim}» misurerebbe L4.1 e non lo scambio.")
            return 1
    print(f"  CONTROLLO retto: le cifre di tutti e {len(CASI)} i casi sono nelle rispettive fonti")
    print(f"  contratto: {len(CONTRATTO)} caratteri · referto: {len(REFERTO)} caratteri\n")

    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "dominio.db"))

    print("  fonte      tipo      esito         ground   claim")
    print("  " + "-" * 100)
    scambi, veri = [], []
    for nome, eti, claim, _c, e_vero in CASI:
        # topic separati: qui interessa se ENTRA, non se sostituisce
        ric = mem.add(claim, topic=f"dom/{nome}/{len(scambi) + len(veri)}",
                      source=FONTI[nome], validate="full")
        g = float(ric.get("grounding_score") or -1)
        st = str(ric.get("status"))
        (veri if e_vero else scambi).append((nome, st, g, claim))
        print(f"  {nome:<10} {eti}   {st:<12} {g:6.1f}   {claim[:56]}")

    print("\nCONTROLLO i claim VERI sono ammessi:")
    male = [c for _n, st, _g, c in veri if st == "quarantined"]
    if male:
        print(f"   CADUTO — {len(male)} veri quarantinati: {male}")
        return 1
    print(f"   retto — {len(veri)} su {len(veri)} ammessi")

    ammessi = [(n, g, c) for n, st, g, c in scambi if st != "quarantined"]
    print(f"\nGLI SCAMBI: {len(ammessi)} ammessi su {len(scambi)}")
    for n, g, c in ammessi:
        print(f"   {n:<10} {g:6.1f}   {c}")
    fermati = [(n, g, c) for n, st, g, c in scambi if st == "quarantined"]
    for n, g, c in fermati:
        print(f"   {n:<10} {g:6.1f}   FERMATO: {c}")

    if ammessi:
        print("\n  ⇒ la classe NON e' un'anomalia di un documento tecnico: entra anche")
        print("    su clausole, termini, importi e posologie, cioe' dove il prodotto")
        print("    dovrebbe servire.")
    else:
        print("\n  ⇒ su questo dominio il prodotto li ferma tutti, e va detto: la")
        print("    classe misurata sul documento tecnico non si estende qui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
