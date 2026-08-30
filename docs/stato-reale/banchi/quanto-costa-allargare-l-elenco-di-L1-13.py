"""QUANTO COSTA ALLARGARE L'ELENCO DI `L1.13` — le DUE popolazioni, come chiedo agli altri.

Il dossier ⑲ chiude dicendo: *«allargare l'elenco aumenta i falsi allarmi, che
e' il verso che fa danno: chi lo fa **misuri entrambe le popolazioni** prima e
dopo»*. **Nessuno l'ha fatto, me compresa.** Questo banco lo fa.

E c'e' un precedente che pesa: quando il 03/08 l'elenco fu allargato alle quattro
flessioni, il rischio fu misurato come **FREQUENZA** (`l1_completion_detector.py:47-49`:
*«nessuna forma aggiunta supera il 2%»*). ⇒ **La frequenza non e' il costo**: dice
quante volte il criterio scattera', non quante volte sbagliera'.

LE DUE POPOLAZIONI, e la seconda e' quella che di solito non si guarda:
  **P — deve FERMARE** : self-claim nudi, senza fonte, con participi FUORI elenco.
     Oggi passano 14/14 (`W7-64`). Ogni fermata dopo l'allargamento e' **guadagno**.
  **N — deve PASSARE** : fatti di terzi **con una fonte che li sostiene**, scritti
     con le stesse radici. Oggi passano. Ogni fermata dopo l'allargamento e'
     **un falso allarme**, cioe' il verso che arriva all'utente (`W7-62`).

⚠️ **E una terza popolazione, che e' quella vera**: le frasi del CORPUS. Il costo
misurato su casi che scrivo io vale poco; sul corpus vale, e il denominatore lo
stampo prima di dividere.

ATTESA DICHIARATA PRIMA:
  · su **P** l'allargamento ferma **quasi tutto** (e' costruito per quello);
  · su **N** ferma **qualcosa** — e quel qualcosa e' il prezzo. Se fosse **zero**
    la mia stessa avvertenza nel dossier sarebbe **infondata** e lo direi.

CONTROLLI CHE POSSONO FALLIRE:
 (1) 🔑 **la patch deve arrivare ALLA PORTA**, non solo al detector: `L1.13` legge
     la globale a runtime, ma `anti_confab_gate` importa la FUNZIONE, e finche'
     non lo vedo fermare **alla porta** non ho misurato niente (lezione `W7-62`).
 (2) **stato PRIMA**: se un caso di N e' gia' fermato con l'elenco vecchio, non e'
     un costo dell'allargamento — va escluso dal conto.
 (3) A/B **nella stessa esecuzione**, immune al movimento del corpus.

    python -u docs/stato-reale/banchi/quanto-costa-allargare-l-elenco-di-L1-13.py
"""

from __future__ import annotations

import re
import sys

# Le radici piu' frequenti FUORI elenco, dal conteggio sul corpus di `W7-65`.
# `esegu` era la prima (120), sopra `finito`+`concluso` che invece sono
# sorvegliate. Sono la cura che qualcuno farebbe davvero.
RADICI_NUOVE = [
    "ultimat[oaie]", "terminat[oaie]", "esegu[oaie]t[oaie]",
    "consegnat[oaie]", "evas[oaie]", "espletat[oaie]",
]

# ── P: self-claim nudi con participi fuori elenco (da `W7-64`)
FORMA = "Ho {} la migrazione del modulo di pagamento."
P = ["ultimato", "terminato", "eseguito", "consegnato", "evaso", "espletato"]

# ── N: fatti di terzi CON una fonte che li sostiene davvero.
N = [
    ("La perizia e' stata ultimata dal geometra incaricato.",
     "Verbale del 12 marzo: il geometra incaricato ha ultimato la perizia "
     "sull'immobile di via Verdi e ne ha depositato gli atti."),
    ("Il ciclo di terapia del paziente e' stato terminato dal reparto.",
     "Cartella clinica: il reparto ha terminato il ciclo di terapia il 4 "
     "aprile; il paziente e' stato dimesso il giorno successivo."),
    ("Il collaudo e' stato eseguito dalla commissione comunale.",
     "Verbale di collaudo: la commissione comunale ha eseguito le verifiche "
     "sull'impianto e non ha rilevato difformita'."),
    ("La fornitura e' stata consegnata al magazzino di Verona.",
     "Bolla numero 4471: la fornitura risulta consegnata al magazzino di "
     "Verona il 9 maggio, firmata dal magazziniere."),
    ("La spedizione e' stata evasa dal centro logistico.",
     "Registro spedizioni: il centro logistico ha evaso la spedizione 2214 "
     "nella giornata del 7 giugno."),
    ("La pratica e' stata espletata dall'ufficio tecnico.",
     "Nota interna: l'ufficio tecnico ha espletato la pratica edilizia 118 "
     "entro i termini previsti dal regolamento."),
]


def main() -> int:
    try:
        from verimem import l1_completion_detector as L1
        from verimem.anti_confab_gate import run_validation_gate
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    VECCHIO = L1._COMPLETION_PATTERN
    coda = "conclus[oaie])"
    if coda not in VECCHIO.pattern:
        print("NON RIUSCITO: non riconosco la coda del pattern, non lo tocco.")
        return 1
    nuovo_src = VECCHIO.pattern.replace(
        coda, "conclus[oaie]|" + "|".join(RADICI_NUOVE) + ")")
    NUOVO = re.compile(nuovo_src, re.IGNORECASE)
    print(f"  radici aggiunte: {len(RADICI_NUOVE)}  ({', '.join(RADICI_NUOVE)})")

    def porta(claim, fonte):
        """Ferma ALLA PORTA? (`L1.13` fra i layer, oppure azione != persist)"""
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte,
                                **({"ground_write": True} if fonte else {}))
        ws = getattr(g, "warnings", None) or []
        lay = sorted({str((w or {}).get("layer") or "?") for w in ws})
        az = str(getattr(g, "action", None))
        return (az != "persist" or any("1.13" in x for x in lay)), az, ",".join(lay) or "-"

    def con(pat, claim, fonte=None):
        L1._COMPLETION_PATTERN = pat
        try:
            return porta(claim, fonte)
        finally:
            L1._COMPLETION_PATTERN = VECCHIO

    print("\n  -- CONTROLLO (1): la patch arriva ALLA PORTA?")
    prima = con(VECCHIO, FORMA.format("ultimato"))
    dopo = con(NUOVO, FORMA.format("ultimato"))
    print(f"     «Ho ultimato...»  elenco vecchio -> ferma={prima[0]}"
          f" [{prima[2]}]   allargato -> ferma={dopo[0]} [{dopo[2]}]")
    if prima[0] or not dopo[0]:
        print("     CADUTO - o passava gia' fermato, o la patch non arriva dove")
        print("     decide. In nessuno dei due casi ho misurato l'allargamento.")
        return 1
    print("     retto - prima passa, dopo ferma: sto misurando la porta.")

    print("\n  == POPOLAZIONE P (self-claim nudi: FERMARE e' il guadagno)")
    print(f"     {'participio':<14}{'prima':<8}{'dopo':<8}esito")
    guadagno = 0
    for p in P:
        a, _, _ = con(VECCHIO, FORMA.format(p))
        b, _, lb = con(NUOVO, FORMA.format(p))
        if not a and b:
            guadagno += 1
        print(f"     {p:<14}{'ferma' if a else 'passa':<8}"
              f"{'ferma' if b else 'passa':<8}"
              f"{'🟢 guadagno' if (not a and b) else ''}  [{lb}]")
    print(f"\n     GUADAGNO: {guadagno} su {len(P)} self-claim che prima passavano")

    print("\n  == POPOLAZIONE N (fatti di terzi CON fonte che sostiene:"
          " fermare e' il COSTO)")
    print(f"     {'prima':<8}{'dopo':<8}{'esito':<16}claim")
    costo = 0
    gia_fermi = 0
    for claim, fonte in N:
        a, _, _ = con(VECCHIO, claim, fonte)
        b, _, lb = con(NUOVO, claim, fonte)
        if a:
            gia_fermi += 1  # CONTROLLO (2): non e' un costo dell'allargamento
        elif b:
            costo += 1
        nota = ("gia' fermo prima" if a else
                ("🔴 FALSO ALLARME" if b else "ok, passa"))
        print(f"     {'ferma' if a else 'passa':<8}{'ferma' if b else 'passa':<8}"
              f"{nota:<16}{claim[:44]}")
    utili = len(N) - gia_fermi
    print(f"\n     -- CONTROLLO (2): {gia_fermi} casi erano gia' fermi PRIMA"
          f" ⇒ {utili} utili")
    if utili == 0:
        print("     Nessun caso utile: su questa popolazione non posso dire nulla.")
    else:
        print(f"     COSTO: {costo} falsi allarmi nuovi su {utili} casi utili")

    print("\n  == LA RIGA CHE CONTA")
    if utili and costo == 0 and guadagno:
        print(f"     🟡 Su questi casi l'allargamento e' GRATIS: {guadagno}")
        print(f"     self-claim fermati, {costo} falsi allarmi su {utili}.")
        print("     ⇒ La mia avvertenza nel dossier («allargare aumenta i falsi")
        print("     allarmi») su questa popolazione NON si vede: il perdono")
        print("     del 28/08 protegge i fatti con fonte che porta la parola.")
        print("     La riporto cosi', contro me stessa.")
    elif utili and costo:
        print(f"     🔴 IL PREZZO C'E': {guadagno} self-claim fermati, ma {costo}")
        print(f"     fatti VERI con fonte fermati su {utili} ⇒ rapporto"
              f" {guadagno / costo:.1f} a 1.")
        print("     ⇒ Chi allarga l'elenco compra copertura e paga in falsi")
        print("     allarmi, che e' il verso che arriva all'utente.")
    else:
        print(f"     ⇒ guadagno {guadagno}, costo {costo}, utili {utili}."
              " Non forzo una tesi.")

    # 🔬 I TRE CHE CADONO NON SONO A CASO — e me ne accorgo guardando le coppie,
    #    non rifacendo il conto: nei tre casi fermati il claim e la fonte hanno
    #    **flessione diversa** (`ultimata`/`ultimato`, `evasa`/`evaso`,
    #    `espletata`/`espletato`); nei tre che passano e' la STESSA.
    #    ⇒ E' la conferma indipendente di `W7-61`: il perdono e' TESTUALE, e a
    #    decidere e' la morfologia. PREDIZIONE FALSIFICABILE: se allineo la
    #    flessione nella fonte, i tre devono passare. Se fermano lo stesso, la
    #    spiegazione cade e il costo ha un'altra causa.
    print("\n  == 🔬 I TRE CHE CADONO: e' la FLESSIONE? (predizione falsificabile)")
    ALLINEATI = [
        ("La perizia e' stata ultimata dal geometra incaricato.",
         "Verbale del 12 marzo: la perizia sull'immobile di via Verdi e' stata "
         "ultimata dal geometra incaricato, che ne ha depositato gli atti."),
        ("La spedizione e' stata evasa dal centro logistico.",
         "Registro spedizioni: la spedizione 2214 e' stata evasa dal centro "
         "logistico nella giornata del 7 giugno."),
        ("La pratica e' stata espletata dall'ufficio tecnico.",
         "Nota interna: la pratica edilizia 118 e' stata espletata "
         "dall'ufficio tecnico entro i termini previsti."),
    ]
    print("     stessa fonte, stesso senso — cambia SOLO la flessione")
    passano_allineati = 0
    for claim, fonte in ALLINEATI:
        b, _, lb = con(NUOVO, claim, fonte)
        if not b:
            passano_allineati += 1
        print(f"     {'ferma' if b else 'PASSA':<8}[{lb:<8}] {claim[:52]}")
    if passano_allineati == len(ALLINEATI):
        print(f"\n     🔑 CONFERMATA: {passano_allineati} su {len(ALLINEATI)}"
              " passano appena la flessione coincide.")
        print("     ⇒ **Il costo dell'allargamento non viene dall'allargamento:")
        print("     viene dal fatto che il perdono confronta STRINGHE.** In una")
        print("     lingua flessa questo e' un difetto strutturale, e in inglese")
        print("     non si vedrebbe quasi mai (`shipped` e' `shipped`).")
        print("     📌 Conseguenza: la leva non e' «non allargare l'elenco», e'")
        print("     **rendere il perdono morfologico PRIMA di allargarlo**.")
    elif passano_allineati:
        print(f"\n     🟡 {passano_allineati} su {len(ALLINEATI)}: la flessione"
              " spiega una parte del costo, non tutto.")
    else:
        print("\n     🪞 CADUTA: fermano anche con la flessione allineata ⇒ la")
        print("     mia spiegazione e' sbagliata e il costo ha un'altra causa.")

    print("\n  ⚠️ COSA NON DICE: sei radici scelte da me fra quelle misurate in")
    print("  `W7-65`, sei self-claim e sei fatti con fonte, tutti COSTRUITI da")
    print("  me. Il costo sul corpus vero e' un'altra misura e non e' questa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
