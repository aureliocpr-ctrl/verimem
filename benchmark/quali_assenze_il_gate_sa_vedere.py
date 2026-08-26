"""Il gate sa dirti che un VALORE manca dalla fonte. Ma quali forme conta come valore?

La promessa del write gate è che un fatto non sostenuto dalla sua fonte non ti
torni come verità. Su una classe questo funziona davvero, e in modo forte: se il
claim aggiunge un valore che la fonte non contiene, il gate lo trattiene ANCHE
quando il giudice semantico è contento (misurato: grounding 99.0 e quarantena
lo stesso). Questo banco misura il CONFINE di quella classe — quali forme di
valore il gate riconosce e quali gli passano davanti.

DUE POPOLAZIONI, e la seconda è ciò che rende leggibile la prima:

  ASSENTE   il claim aggiunge un valore che la fonte NON contiene -> deve CADERE
  PRESENTE  lo stesso valore, ma scritto anche nella fonte        -> deve PASSARE

Senza la seconda, una tabella di «cosa il gate prende» è indistinguibile da «il
gate odia le percentuali»: una mappa di ciò che un filtro blocca non si legge
senza la popolazione su cui NON deve scattare.

Misurato 2026-08-26 su 23 forme, con la doppia popolazione:

    RICONOSCE che manca (12):  intero in cifre · decimale col punto · decimale
        con virgola · percentuale · orario · identificativo esadecimale ·
        valuta senza separatore («1200 euro») · unita di misura («15 kg») ·
        frazione («1/3») · intervallo («fra 3 e 5»)
    NON riconosce (11):  intero in LETTERE · data testuale · data ISO · anno
        da solo · versione («2.4.1») · codice alfanumerico («AB-12») · valuta
        col separatore («1.200 EUR») · numero romano · ordinale in lettere
    FALSI POSITIVI: 0 su 23 — col valore presente nella fonte passano tutte.

La regolarita' che ne esce non e' «numeri si', parole no»: e' che il gate ferma
l'assenza di un valore quando la forma e' INEQUIVOCABILE, e la lascia passare
quando la forma e' ambigua o non e' una cifra.

⚠️ IL CASO PIU' INTERESSANTE E' LA VALUTA, perche' il prodotto DICHIARA di non
sapere e ammette lo stesso:

    «e il canone e 1200 euro»    -> CADE    layers: ['L4.1']
    «e il canone e 1.200 EUR»    -> passa   layers: ['L4.1-ambiguo']

Il separatore delle migliaia rende il numero indistinguibile da un decimale, il
layer lo riconosce, si marca AMBIGUO — e il fatto entra. E' un'astensione del
layer che diventa un'ammissione del prodotto: chi legge i layer vede che
qualcosa non ha saputo decidere, chi legge lo status vede solo un fatto servito.

⚠️ LE DATE SONO IL BUCO PIÙ COMUNE. Né «3 aprile» né «2019-04-03» vengono
fermate, e un layer le VEDE (compare fra quelli attivati) senza bloccare. In una
memoria verificata le date sono ovunque — «deciso il…», «scade il…» — e un claim
può attaccarne una che la fonte non contiene a un fatto per il resto vero.

⚠️ E UN'INCOERENZA CHE QUESTO BANCO NON SPIEGA: un identificativo esadecimale
(`3269bebb`) viene riconosciuto come valore mancante, una versione (`2.4.1`) no.
Misura, non diagnosi.

Run:  python -m benchmark.quali_assenze_il_gate_sa_vedere
Exit: 0 se il controllo PRESENTE è pulito (nessun falso positivo) — allora la
      colonna ASSENTE è leggibile; 2 se una forma cade anche col valore
      presente, perché in quel caso starebbe respingendo la forma e non
      l'assenza, e la mappa non significherebbe niente.
"""
from __future__ import annotations

import os
import sys
import tempfile

FONTE_BASE = "Verbale: il magazzino K-77 di Rovigo misura 4200 metri quadrati"
CLAIM_BASE = "Il magazzino K-77 misura 4200 metri quadrati"

#: (etichetta, coda che aggiunge il valore, come lo stesso valore appare in fonte)
#: due celle per forma: due valori diversi, per non consegnare un n=1.
FORME: list[tuple[str, str, str]] = [
    ("intero in cifre", "e ha 3 banchine", "e ha 3 banchine"),
    ("intero in cifre (2)", "e ha 17 dipendenti", "e ha 17 dipendenti"),
    ("intero in lettere", "e ha tre banchine", "e ha tre banchine"),
    ("intero in lettere (2)", "e ha diciassette dipendenti", "e ha diciassette dipendenti"),
    ("decimale col punto", "e il soffitto e alto 4.5 metri", "e il soffitto e alto 4.5 metri"),
    ("decimale con virgola", "e il soffitto e alto 4,5 metri", "e il soffitto e alto 4,5 metri"),
    ("percentuale", "ed e occupato al 80%", "ed e occupato al 80%"),
    ("percentuale (2)", "ed e libero al 12,5%", "ed e libero al 12,5%"),
    ("data testuale", "ed e stato aperto il 3 aprile", "ed e stato aperto il 3 aprile"),
    ("data ISO", "ed e stato aperto il 2019-04-03", "ed e stato aperto il 2019-04-03"),
    ("anno da solo", "ed e stato aperto nel 2019", "ed e stato aperto nel 2019"),
    ("orario", "e chiude alle 18:30", "e chiude alle 18:30"),
    ("versione", "e usa il gestionale 2.4.1", "e usa il gestionale 2.4.1"),
    ("identificativo esa", "e il suo lotto e 3269bebb", "e il suo lotto e 3269bebb"),
    ("codice alfanumerico", "e il suo settore e AB-12", "e il suo settore e AB-12"),
    ("valuta", "e il canone e 1200 euro", "e il canone e 1200 euro"),
    ("valuta col simbolo", "e il canone e 1.200 EUR", "e il canone e 1.200 EUR"),
    ("unita di misura", "e la portata e 15 kg per metro", "e la portata e 15 kg per metro"),
    ("numero romano", "ed e nel lotto XII", "ed e nel lotto XII"),
    ("frazione", "ed e pieno per 1/3", "ed e pieno per 1/3"),
    ("intervallo", "e ha fra 3 e 5 uscite", "e ha fra 3 e 5 uscite"),
    ("ordinale in lettere", "ed e il terzo della zona", "ed e il terzo della zona"),
    ("nessun valore", "ed e dotato di impianto antincendio", "ed e dotato di impianto antincendio"),
]


def main() -> int:
    os.environ.setdefault("HIPPO_DATA_DIR", tempfile.mkdtemp(prefix="assenze_"))
    from verimem import Memory

    def scrivi(claim: str, fonte: str) -> tuple[bool, float | None, list]:
        #: percorso esplicito: il costruttore vince su qualunque variabile
        m = Memory(os.path.join(tempfile.mkdtemp(prefix="assenze_db_"), "m.db"))
        r = m.add(claim, source=fonte)
        return (r["status"] == "quarantined",
                r.get("grounding_score"),
                [w.get("layer") for w in (r.get("warnings") or [])][:2])

    print(f"  {'forma':<24} {'ASSENTE':<12} {'PRESENTE':<12} {'ground':>7}  layers")
    riconosciute, falsi_positivi = [], []
    for etichetta, coda, dentro in FORME:
        claim = f"{CLAIM_BASE} {coda}."
        cade_se_assente, g, layers = scrivi(claim, FONTE_BASE + ".")
        cade_se_presente, _, _ = scrivi(claim, f"{FONTE_BASE} {dentro}.")
        if cade_se_assente:
            riconosciute.append(etichetta)
        if cade_se_presente:
            falsi_positivi.append(etichetta)
        print(f"  {etichetta:<24} {'CADE' if cade_se_assente else 'passa':<12} "
              f"{'CADE' if cade_se_presente else 'passa':<12} "
              f"{(f'{g:.1f}' if g is not None else '-'):>7}  {layers}")

    print()
    print(f"  riconosce che manca : {len(riconosciute)}/{len(FORME)}")
    print(f"     {', '.join(riconosciute) or '(nessuna)'}")
    non = [e for e, _, _ in FORME if e not in riconosciute]
    print(f"  NON riconosce       : {len(non)}/{len(FORME)}")
    print(f"     {', '.join(non) or '(nessuna)'}")
    print()
    if falsi_positivi:
        print(f"  FALSI POSITIVI: {falsi_positivi}")
        print("  ⇒ il gate respinge la FORMA, non l'assenza: la mappa sopra NON e' leggibile.")
        return 2
    print("  falsi positivi: 0 — il gate respinge l'ASSENZA, non la forma.")
    print("  ⇒ la mappa sopra e' leggibile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
