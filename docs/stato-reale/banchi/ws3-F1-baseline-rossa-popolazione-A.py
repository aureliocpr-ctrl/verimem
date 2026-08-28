# -*- coding: utf-8 -*-
"""F1 · BASELINE ROSSA — popolazione A: i FALSI che lo strato soggetto-valore
deve prendere. **Pre-registrato: nessuna cura qui dentro.**

Ordine del giorno 28/08 (@lead-audit): F1 = strato soggetto-valore, @ws3+@ws5,
**design falsificabile PRIMA, banco pre-registrato, review, POI implementazione**.
Questo file e' il primo pezzo: il ROSSO DI PARTENZA, misurato — non assunto.

────────────────────────────────────────────────────────────────────────────
LA RESTRIZIONE CHE HO DOVUTO FARE ALLA MIA STESSA TESI (28/08)

Avevo scritto «chi cura il legame soggetto-valore chiude TRE falle». E' MIA ed
e' TROPPO LARGA. Le tre condividono la CAUSA, non la CURA:

  numero a parole   nessun glifo 0-9 => il valore non e' nemmeno ESTRAIBILE
                    cura: NORMALIZZARE i numerali prima di L4.1
  attribuz. scamb.  il valore c'e' ed e' TROVATO, ma su un'ALTRA entita'
                    cura: LEGARE il valore al suo SOGGETTO (insiemi -> coppie)
  omissione         il claim non porta il valore => niente da cercare
                    cura: la direzione INVERSA, che oggi NON ESISTE —
                    `valori_non_nella_fonte(claim, source)`
                    (anti_confab_gate.py:2455) prende i valori DAL CLAIM

⇒ un SOLO componente che estragga coppie (soggetto, valore) da claim E fonte,
  normalizzando i numerali, e confronti nelle DUE direzioni. «Ne chiude tre» e'
  vero SOLO con tutte e tre le proprieta'. Col solo legame ne chiude UNA.

────────────────────────────────────────────────────────────────────────────
IL RISCHIO, PRE-REGISTRATO PRIMA DI SCRIVERE UNA RIGA DI CURA

Regola di casa: «un criterio SINTATTICO su un fenomeno SEMANTICO sbaglia in
ENTRAMBE le direzioni e penalizza il codice piu' CURATO». Lo strato e'
sintattico; «chi dice cosa di chi» e' semantico.
🔴 La direzione INVERSA e' la piu' pericolosa: **ogni claim vero omette
qualcosa della sua fonte** — e' cio' che significa riassumere. Un controllo di
omissione ingenuo quarantina quasi ogni claim vero. **La cura puo' fare piu'
danno della falla.**
⇒ per questo la POPOLAZIONE B (i veri che NON devono rompersi) la scrive
**@ws5**, non io: «il banco lo scriva chi non ha in mente la cura». Questo file
copre SOLO la popolazione A e non ha voce sulla B.

────────────────────────────────────────────────────────────────────────────
CRITERIO DI SUCCESSO, DICHIARATO ORA (e non riscrivibile dopo i numeri)

Dopo la cura, ri-eseguendo QUESTO file senza modificarlo:
  · SCAMBIO    almeno 6 dei 7 oggi ammessi devono essere fermati
  · NUMERALE   3 su 3 dei falsi a parole devono essere fermati
  · OMISSIONE  almeno 2 su 3 devono ricevere ALMENO UN AVVISO
               (non pretendo la quarantena: un'omissione puo' essere
                legittima, e trasformarla in veto e' il danno da evitare)
  · CONTROLLI  i falsi in CIFRA devono restare fermati (0 regressioni)
E la popolazione B di @ws5 decide il resto: **una cura che passa questo file e
rompe i veri e' respinta.** Nessuno dei due banchi da solo e' un verdetto.

CONTROLLO CHE DEVE POTER FALLIRE: i falsi in CIFRA (famiglia NUMERALE, ramo
`cifra`) devono essere fermati GIA' OGGI. Se non lo sono, il regime e' rotto —
il giudice non sta girando — e il banco non stampa una baseline.

REGIME: un processo, store temporaneo vuoto (`Memory(path=…)`), porta SDK,
`validate="full"`, italiano. Gli strati si leggono da `warnings` (la ricevuta
NON ha una chiave `layers`: cella 50).

    python docs/stato-reale/banchi/ws3-F1-baseline-rossa-popolazione-A.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# ── fonti ────────────────────────────────────────────────────────────────
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
# le tre frasi decisive del banco omissione (documento lungo), qui in fonte CORTA
OMI_FONTI = {
    "affidamento": "L'affidamento al fornitore Bertani e' subordinato "
                   "all'approvazione preventiva del collegio dei revisori.",
    "rimborso": "Il rimborso delle spese di trasferta e' ammesso solo entro il "
                "limite mensile fissato dal regolamento interno.",
    "proroga": "La proroga del contratto di servizio decorre dalla scadenza "
               "originaria ed e' condizionata alla verifica dei requisiti da "
               "parte dell'ufficio.",
}

# ── popolazione A ────────────────────────────────────────────────────────
# (famiglia, etichetta, fonte, claim, ramo)
CASI: list[tuple[str, str, str, str, str]] = []

# ① SCAMBIO DI ATTRIBUZIONE — i 12 di @ws4, entrambi i versi, alla lettera
for _et, _f, _a, _b in [
    ("penali 2%/5%", CONTRATTO,
     "La penale per il ritardo e' pari al 5% dell'importo contrattuale.",
     "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale."),
    ("termini mar/apr", CONTRATTO,
     "Il termine di consegna e' fissato al 30 aprile 2027.",
     "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027."),
    ("importi 148k/22k", CONTRATTO,
     "La cauzione definitiva e' pari a 148000 euro.",
     "L'importo contrattuale e' di 22000 euro."),
    ("metform./ramipr.", REFERTO,
     "Il ramipril e' prescritto a 850 mg al mattino.",
     "Il paziente assume metformina 5 mg due volte al giorno."),
    ("metform./acido", REFERTO,
     "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.",
     "Il paziente assume metformina 100 mg due volte al giorno."),
    ("ramipr./acido", REFERTO,
     "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.",
     "Il ramipril e' prescritto a 100 mg al mattino."),
]:
    CASI.append(("SCAMBIO", f"{_et} A", _f, _a, "scambio"))
    CASI.append(("SCAMBIO", f"{_et} B", _f, _b, "scambio"))

# ② NUMERALE — la variabile isolata da @ws5: unica differenza il GLIFO 0-9.
#    il ramo `cifra` e' il CONTROLLO (deve essere fermato gia' oggi).
for _et, _f, _cif, _par in [
    ("importo", CONTRATTO,
     "L'importo contrattuale e' di 391000 euro.",
     "L'importo contrattuale e' di trecentonovantunomila euro."),
    ("cauzione", CONTRATTO,
     "La cauzione definitiva e' pari a 70000 euro.",
     "La cauzione definitiva e' pari a settantamila euro."),
    ("dosaggio", REFERTO,
     "Il ramipril e' prescritto a 73 mg al mattino.",
     "Il ramipril e' prescritto a settantatre mg al mattino."),
]:
    CASI.append(("NUMERALE", f"{_et} cifra", _f, _cif, "cifra"))
    CASI.append(("NUMERALE", f"{_et} parole", _f, _par, "parole"))

# ③ OMISSIONE — il claim tace la condizione che la fonte pone
for _et, _claim in [
    ("affidamento", "Il consiglio ha disposto l'affidamento al fornitore Bertani."),
    ("rimborso", "Le spese di trasferta sono rimborsate al personale."),
    ("proroga", "Il contratto di servizio e' stato prorogato."),
]:
    CASI.append(("OMISSIONE", _et, OMI_FONTI[_et], _claim, "omissione"))


def _strati(ric) -> list[str]:
    """Da `warnings`: la ricevuta NON ha una chiave `layers` (cella 50)."""
    return [str(w.get("layer")) for w in (ric.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def main() -> int:
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print("    store TEMPORANEO vuoto · un processo · porta SDK · validate='full' · IT")
    print("    NESSUNA CURA in questo file: e' la baseline pre-registrata.\n")

    mem = Memory(str(Path(tempfile.mkdtemp()) / "f1base.db"))
    righe = []
    print(f"  {'famiglia':<10} {'caso':<18} {'esito':<7} {'ground':>7}  strati")
    print("  " + "-" * 76)
    for fam, et, fonte, claim, ramo in CASI:
        r = mem.add(claim, topic=f"f1/{fam}/{et}".replace(" ", "_"),
                    source=fonte, validate="full")
        st = str(r.get("status"))
        g = r.get("grounding_score")
        gf = float(g) if g is not None else -1.0
        ls = _strati(r)
        entra = st != "quarantined"
        righe.append((fam, et, ramo, entra, gf, ls))
        print(f"  {fam:<10} {et:<18} {'ENTRA' if entra else 'ferma':<7} "
              f"{gf:7.1f}  {','.join(ls) if ls else '-'}")

    # ── controllo che deve poter fallire ────────────────────────────────
    cifre = [r for r in righe if r[2] == "cifra"]
    passate = [r for r in cifre if r[3]]
    print(f"\n  CONTROLLO: falsi in CIFRA fermati oggi: "
          f"{len(cifre) - len(passate)} su {len(cifre)}")
    if passate:
        print("     CONTROLLO CADUTO: un falso in cifra e' ENTRATO ⇒ il giudice non")
        print("     sta girando o il regime e' rotto. NESSUNA BASELINE.")
        for r in passate:
            print(f"        {r[1]}  ground={r[4]:.1f}")
        return 1

    # ── la baseline ─────────────────────────────────────────────────────
    print("\n  ══ BASELINE ROSSA — popolazione A, prodotto di oggi ══")
    for fam in ("SCAMBIO", "NUMERALE", "OMISSIONE"):
        f = [r for r in righe if r[0] == fam and r[2] != "cifra"]
        entrati = [r for r in f if r[3]]
        con_strato = [r for r in f if r[5]]
        print(f"     {fam:<10} ENTRANO {len(entrati)}/{len(f)}"
              f"   con almeno uno strato: {len(con_strato)}/{len(f)}")
    tot = [r for r in righe if r[2] != "cifra"]
    tot_e = [r for r in tot if r[3]]
    print(f"     {'TOTALE':<10} ENTRANO {len(tot_e)}/{len(tot)}")

    print("\n  ══ CRITERIO DI SUCCESSO, dichiarato PRIMA della cura ══")
    print("     SCAMBIO    almeno 6 dei 7 oggi ammessi devono essere FERMATI")
    print("     NUMERALE   3 su 3 dei falsi a parole devono essere FERMATI")
    print("     OMISSIONE  almeno 2 su 3 devono ricevere ALMENO UN AVVISO")
    print("                (non la quarantena: un'omissione puo' essere legittima)")
    print("     CONTROLLI  i falsi in CIFRA restano fermati: 0 regressioni")
    print("     ⇒ e la POPOLAZIONE B di @ws5 decide il resto: una cura che passa")
    print("       questo file e ROMPE I VERI e' respinta. Nessuno dei due banchi")
    print("       da solo e' un verdetto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
