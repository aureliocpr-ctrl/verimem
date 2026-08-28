"""NON E' UNA SOGLIA DI CARATTERI: E' LA BANDA A 80 — predizione dichiarata PRIMA.

Il fronte «quale variabile decide quali scambi entrano» ha **14 ipotesi cadute**
(dossier ⑬). W7-39 ha stabilito che il verdetto e' ripetibile al bit; W7-41 che
bastano **+6 caratteri** e che la curva **non e' monotona** (a +18 torna
indietro).

⇒ Letto il gate: `band_enforced=True`, `cut=40.0`, **`tau_hi=80.0`**. La banda
e' `[40, 80]`: sotto 40 il fatto e' rifiutato, sopra 80 ammesso, **in mezzo
trattenuto**.

E i sette punti gia' misurati si spiegano TUTTI cosi':

    nuda  72.1 dentro -> trattenuto · +6  90.0 sopra -> ammesso
    +12   95.9 sopra  -> ammesso    · +18 77.4 dentro -> trattenuto
    +24   93.9 sopra  -> ammesso    · assente 0.4 sotto -> rifiutato
    vero 100.0 sopra  -> ammesso

⚠️ **MA SETTE PUNTI SPIEGATI A POSTERIORI NON SONO UNA PREDIZIONE.** Qualunque
regola inventata dopo aver visto i dati li spiega. Quindi qui la regola viene
**dichiarata prima** e verificata su **delta NUOVI**, mai misurati.

LA REGOLA, scritta prima di eseguire:
    esito = 'persist' se grounding_score >= 80.0, altrimenti 'downgrade'
e non serve sapere NIENTE del testo — ne' la lunghezza, ne' il contenuto.

CONTROLLI CHE POSSONO FALLIRE:
 (1) i delta di prova sono NUOVI (2, 4, 8, 10, 14, 16, 20, 22, 26, 34, 44, 50):
     nessuno compare in W7-41. Se la regola sbaglia anche una sola volta, non e'
     la banda, o non e' solo la banda.
 (2) il claim con CIFRA ASSENTE dev'essere predetto anche lui: se la regola vale
     solo sullo scambio, e' una regola sullo scambio, non sul gate.

    python -u docs/stato-reale/banchi/non-e-una-soglia-di-caratteri-e-la-banda-a-80.py
"""

from __future__ import annotations

import sys

NUDA = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 7% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
CODA = (" Le parti dichiarano di aver letto e compreso ogni clausola del "
        "presente accordo e di accettarne integralmente il contenuto, "
        "riservandosi ogni facolta' di legge in ordine alle obbligazioni.")

# delta MAI misurati in W7-41 (che usava 0,6,12,18,24,30,36,42,48,54,60,80,120,180)
DELTA_NUOVI = [2, 4, 8, 10, 14, 16, 20, 22, 26, 34, 44, 50]

CLAIM = [
    ("SCAMBIO", "La cauzione definitiva e' pari a 148000 euro."),
    ("ASSENTE", "La cauzione definitiva e' pari a 99999 euro."),
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.grounding_gate import _ce_band_tau_hi
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    TAU = _ce_band_tau_hi()
    print(f"  tau_hi letto dal gate: {TAU}")
    print("  REGOLA DICHIARATA PRIMA: persist  <=>  grounding_score >= tau_hi")
    print("  (nessuna informazione sul testo entra in questa regola)")

    giusti = sbagliati = 0
    errori = []
    for nome, claim in CLAIM:
        print(f"\n  == {nome}  su {len(DELTA_NUOVI)} delta MAI misurati")
        print(f"     {'delta':>6} {'score':>8}  {'predetto':<10}{'osservato':<10} esito")
        for d in DELTA_NUOVI:
            fonte = NUDA + CODA[:d]
            g = run_validation_gate(proposition=claim, verified_by=[],
                                    topic=None, agent=None, source=fonte,
                                    ground_write=True)
            score = getattr(g, "grounding_score", None) or 0.0
            osservato = getattr(g, "action", None)
            predetto = "persist" if score >= TAU else "downgrade"
            ok = (predetto == osservato)
            giusti += 1 if ok else 0
            sbagliati += 0 if ok else 1
            if not ok:
                errori.append((nome, d, score, predetto, osservato))
            print(f"     {d:>6} {score:>8.1f}  {predetto:<10}{str(osservato):<10}"
                  f" {'ok' if ok else 'SBAGLIATA'}")

    tot = giusti + sbagliati
    print(f"\n  == LA PREDIZIONE, su {tot} casi nuovi")
    print(f"     giuste {giusti}   sbagliate {sbagliati}")

    print("\n  -- CONTROLLO (1) e (2): la regola regge su casi mai visti?")
    if sbagliati:
        print(f"     CADUTA su {sbagliati} casi:")
        for nome, d, s, p, o in errori[:6]:
            print(f"       {nome} delta={d} score={s:.1f} predetto={p} osservato={o}")
        print("     ⇒ NON e' (solo) la banda: c'e' dell'altro, e non lo so.")
        return 1
    print(f"     RETTA - {giusti} su {tot}, su ENTRAMBE le popolazioni.")
    print("\n  ⇒ IL FRONTE SI CHIUDE COSI': non c'e' nessuna soglia di")
    print("    CARATTERI. C'e' un punteggio che il testo sposta di 10-20 punti")
    print("    per pochi caratteri, e una BANDA a 80 che trasforma quello")
    print("    spostamento in un verdetto binario. Le 14 ipotesi cadute")
    print("    cercavano una regola sul TESTO per un fenomeno che e' una")
    print("    soglia sul PUNTEGGIO.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
