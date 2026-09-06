"""LIVELLO: solo la regex dello splitter — nessun gate, nessun modello, nessuna scrittura.

MURO 1: prima di misurare se la decomposizione atomica giudica MEGLIO, misuro se
ha qualcosa da decomporre. E' il denominatore della cura.

    python docs/stato-reale/banchi/ws3-muro1-quanta-superficie-ha-la-decomposizione.py

⚡ COSTO ZERO. Lo store di Aurelio e' aperto in SOLA LETTURA (`mode=ro`).

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il lead (msg a05dd7a6d6fa2458) mi ha chiesto di estendere la tesi «ai 60+60 e ai
15 di ieri», con la predizione: «sui 60 falsi diretti l'atomico ferma >= 27/30
contro 21 dell'intero». Prima di prendere lo slot del giudice ho controllato la
PREMESSA — quante unita' produce lo splitter su quelle popolazioni — perche' se
ne produce una sola l'atomico E' l'intero e l'esperimento non puo' dire niente.

━━ MISURATO, e decide l'esperimento ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    popolazione                     unita' per claim   claim NON decomposti
    30 coppie DIRETTE  (60 claim)        1,00              60/60 = 100%
    30 coppie IMPLICITE (60 claim)       1,00              60/60 = 100%
    fonti delle 30 dirette               1,00 frasi        30/30 = 100%
    fonti delle 30 implicite             1,00 frasi        30/30 = 100%
⇒ Sui 60+60 la decomposizione atomica e' **l'identita'**: MIN su un claim solo e
  MAX su una frase sola danno lo stesso numero del giudizio intero, su tutte e
  120 le celle. Non serve il giudice per saperlo: serve la regex.
  Non e' un difetto della tesi: e' che quei 120 claim li ho costruiti IO per
  misurare il GIUDICE (frase estranea, contraddizione implicita), e sono frasi
  singole brevi per costruzione. Sono la popolazione sbagliata per questa
  domanda — la mia, non la sua.

━━ E ALLORA QUAL E' LA POPOLAZIONE GIUSTA: il corpus vero ━━━━━━━━━━━━━━━━━━━━━
Questo banco la misura: quanti dei fatti realmente scritti sono composti, cioe'
quanti la cura toccherebbe davvero se entrasse nel percorso di scrittura.
Riporta anche il buco italiano dello splitter: la regex spezza su « e » ma non
su « ed », che in italiano e' la forma davanti a vocale — «iniziato ... ed e'
finito» resta intero.

━━ COME MUORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se sul corpus i composti fossero una frazione trascurabile, la cura non avrebbe
superficie e la discussione sul MIN/MAX sarebbe accademica. Se invece sono molti,
il banco successivo (intero vs atomico su QUELLI) e' il banco che decide.
"""
from __future__ import annotations

import pathlib
import re
import sqlite3

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
_COORD = re.compile(r"\s*(?:,\s*e\s+|\s+e\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_ED = re.compile(r"\s+ed\s+", re.I)
_FRASI = re.compile(r"(?<=[.!?])\s+")


def n_pezzi(t: str) -> int:
    return len([p for p in _COORD.split(t) if p and len(p.split()) >= 3]) or 1


def main() -> None:
    if not pathlib.Path(DB).exists():
        print(f"⚠️  store non trovato: {DB}")
        return
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()

    n = [n_pezzi(t) for t in righe]
    tot = len(n)
    uno = sum(1 for x in n if x == 1)
    due_piu = tot - uno
    tre_piu = sum(1 for x in n if x >= 3)
    con_ed = sum(1 for t in righe if _ED.search(t))
    ed_non_spezzati = sum(1 for t, k in zip(righe, n, strict=True) if k == 1 and _ED.search(t))
    frasi = [len([f for f in _FRASI.split(t) if f.strip()]) or 1 for t in righe]
    fonte_multi = sum(1 for x in frasi if x >= 2)

    print("QUANTA SUPERFICIE HA LA DECOMPOSIZIONE ATOMICA, sul corpus vero\n")
    print(f"  fatti vivi esaminati                : {tot}")
    print(f"  decomposti in >= 2 unita'           : {due_piu}  ({100 * due_piu / tot:.1f}%)")
    print(f"     di cui in >= 3                   : {tre_piu}  ({100 * tre_piu / tot:.1f}%)")
    print(f"  NON decomposti (una unita' sola)    : {uno}  ({100 * uno / tot:.1f}%)")
    print(f"  unita' medie per fatto              : {sum(n) / tot:.2f}   max={max(n)}")
    print(f"  testi con piu' di una frase (MAX)   : {fonte_multi}  ({100 * fonte_multi / tot:.1f}%)")
    print("\n  IL BUCO ITALIANO DELLO SPLITTER — la regex spezza « e » ma non « ed »:")
    print(f"    fatti che contengono « ed »       : {con_ed}  ({100 * con_ed / tot:.1f}%)")
    print(f"    di questi, restano INTERI          : {ed_non_spezzati}"
          f"  ({100 * ed_non_spezzati / max(1, con_ed):.1f}% di quelli con « ed »)")
    print("\n  ⇒ il denominatore della cura e' il primo numero: e' li' che l'atomico")
    print("    puo' fare bene o male. Fuori di li' e' l'identita'.")


if __name__ == "__main__":
    main()
