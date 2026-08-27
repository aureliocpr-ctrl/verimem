# -*- coding: utf-8 -*-
"""L'APERTO DELLE 22:00: cosa distingue gli scambi che entrano da quelli fermati.

Il banco di dominio ha dato 3 ammessi su 7 e io ho dichiarato di non aver
isolato la differenza. Guardando i sette casi a occhio ho provato due
regolarita' e cadono entrambe sui dati che ho gia':

  «scambio fra grandezze della stessa specie» — cade: anche i quattro fermati
     scambiano penale con penale, importo con importo, dosaggio con dosaggio;
  «il valore aumenta» — cade su «cauzione = 148000» (aumenta ed e' fermato).

Guardare i dati e cercarci una forma e' esattamente il modo in cui stasera mi
sono gia' sbagliata tre volte. Qui invece c'e' un DISEGNO: ogni coppia di
grandezze omogenee viene scambiata in ENTRAMBI i versi, sulla stessa fonte.

  se una coppia entra in un verso e viene fermata nell'altro, la differenza sta
     nel VERSO — e allora e' il danno a decidere, non la struttura;
  se le coppie sono coerenti (entrambi i versi uguali), la differenza sta nella
     COPPIA, e la variabile e' un'altra: quale, non lo so ancora.

CONTROLLO CHE DEVE POTER FALLIRE: ogni cifra usata deve stare nella fonte, e i
claim VERI di riferimento devono essere ammessi.

⚠️ Fonti costruite, come nel banco precedente, e dichiarate.

    python docs/stato-reale/banchi/lo-scambio-e-simmetrico-o-no.py
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

# (fonte, nome della coppia, claim verso A, claim verso B)
COPPIE = [
    ("contratto", "penali 2%/5%",
     "La penale per il ritardo e' pari al 5% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale."),
    ("contratto", "termini marzo/aprile",
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027."),
    ("contratto", "importi 148000/22000",
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro."),
    ("referto", "metformina/ramipril",
     "Il ramipril e' prescritto a 850 mg al mattino.",
     "Il paziente assume metformina 5 mg due volte al giorno."),
    ("referto", "metformina/acido",
     "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.",
     "Il paziente assume metformina 100 mg due volte al giorno."),
    ("referto", "ramipril/acido",
     "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.",
     "Il ramipril e' prescritto a 100 mg al mattino."),
]
FONTI = {"contratto": CONTRATTO, "referto": REFERTO}


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    mem = Memory(str(Path(tempfile.mkdtemp()) / "simm.db"))

    # controllo: due veri devono entrare
    veri = [("contratto", "La penale per il ritardo e' pari al 2% dell'importo contrattuale."),
            ("referto", "Il ramipril e' prescritto a 5 mg al mattino.")]
    for nome, prop in veri:
        r = mem.add(prop, topic=f"simm/vero/{nome}", source=FONTI[nome], validate="full")
        if str(r.get("status")) == "quarantined":
            print(f"CONTROLLO CADUTO: il vero «{prop}» e' quarantinato")
            return 1
    print(f"  CONTROLLO retto: i due claim VERI di riferimento sono ammessi\n")

    print(f"  {'coppia':<24} {'verso A':>22}   {'verso B':>22}")
    print("  " + "-" * 76)
    righe = []
    for i, (nome, coppia, a, b) in enumerate(COPPIE):
        out = []
        for j, prop in enumerate((a, b)):
            ric = mem.add(prop, topic=f"simm/{i}/{j}", source=FONTI[nome], validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            out.append((st, g))
        (sa, ga), (sb, gb) = out
        ea = "ENTRA" if sa != "quarantined" else "ferma"
        eb = "ENTRA" if sb != "quarantined" else "ferma"
        righe.append((coppia, ea, ga, eb, gb))
        print(f"  {coppia:<24} {ea:>7} {ga:6.1f}      {eb:>13} {gb:6.1f}")

    discordi = [(c, ea, ga, eb, gb) for c, ea, ga, eb, gb in righe if ea != eb]
    concordi = [(c, ea) for c, ea, _ga, eb, _gb in righe if ea == eb]
    print(f"\n  coppie DISCORDI (un verso entra, l'altro no): {len(discordi)} su {len(righe)}")
    for c, ea, ga, eb, gb in discordi:
        print(f"     {c:<24} A {ea} {ga:.1f}   B {eb} {gb:.1f}")
    print(f"  coppie CONCORDI: {len(concordi)} su {len(righe)}")
    for c, e in concordi:
        print(f"     {c:<24} entrambi {e}")

    if discordi:
        print("\n  ⇒ lo scambio NON e' simmetrico: sulla stessa coppia di grandezze un")
        print("    verso entra e l'altro viene fermato. La differenza non e' nella")
        print("    coppia, e va cercata in cosa cambia FRA i due versi.")
    else:
        print("\n  ⇒ lo scambio e' SIMMETRICO su tutte le coppie: la differenza sta")
        print("    nella coppia, non nel verso, e il verso e' escluso come variabile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
