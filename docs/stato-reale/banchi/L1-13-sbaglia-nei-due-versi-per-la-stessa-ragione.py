"""`L1.13` SBAGLIA NEI DUE VERSI, E PER LA STESSA RAGIONE — la specifica, chiusa.

`W7-61` ha misurato **un verso**: la cura che ho scritto io perdona quando la
fonte contiene **la stessa parola in un ALTRO senso** (*«il campo va completato
in stampatello»* fa entrare *«il collaudo e' stato completato»*).

Un'altra istanza riporta **l'altro verso**, che io **non avevo riprodotto**:
`L1.13` **ferma** una parafrasi **fedele** mentre il giudice le da' **97,6**.

⇒ Questo banco mette i due versi **sulla stessa tabella**, con la stessa cura
attiva, e chiede se siano **due difetti o uno solo**.

  · **PERMESSO**: stessa PAROLA, senso diverso  → la cura perdona (misurato)
  · **ALLARME** : stesso SENSO, parola diversa  → la cura non perdona, e `L1.13`
    ferma **anche se il moat approva**

🔑 **L'IPOTESI, dichiarata prima**: sono **lo stesso difetto visto da due lati** —
il criterio guarda la **PAROLA**, non il **SENSO**. Se e' cosi', nel verso
ALLARME il **grounding deve essere ALTO** (il giudice capisce la parafrasi) e
`L1.13` deve fermare lo stesso: **il layer contraddice il giudice**.

⚠️ **Cosa la falsificherebbe**: se nel verso ALLARME anche il **moat** desse un
punteggio basso, allora `L1.13` non contraddice nessuno — starebbe solo
concordando con un giudice che a sua volta non capisce la parafrasi, e la mia
lettura («il layer contro il giudice») cadrebbe.

CONTROLLI CHE POSSONO FALLIRE:
 (1) le parafrasi devono essere **fedeli**: se cambiano il fatto, `L1.13` ferma
     a ragione e non c'e' nessun falso allarme da misurare. Le scrivo come
     coppie sinonimo/sinonimo sullo stesso soggetto.
 (2) **controllo positivo**: la stessa coppia con il participio IDENTICO deve
     PASSARE — altrimenti non sto misurando la parola, sto misurando altro.

    python -u docs/stato-reale/banchi/L1-13-sbaglia-nei-due-versi-per-la-stessa-ragione.py
"""

from __future__ import annotations

import sys

# ── verso ALLARME: stesso SENSO, parola diversa (parafrasi fedele)
ALLARME = [
    ("L'istruttoria e' stata conclusa dal responsabile del procedimento.",
     "Verbale del 12 marzo: l'istruttoria relativa alla pratica 2214 e' stata "
     "chiusa dal responsabile del procedimento, che ne ha firmato gli atti."),
    ("Il collaudo dell'impianto e' stato ultimato dalla commissione.",
     "Verbale di collaudo: la commissione ha completato le verifiche "
     "sull'impianto e non ha rilevato difformita'."),
]
# ── controllo positivo: la STESSA coppia con il participio identico
IDENTICO = [
    ("L'istruttoria e' stata chiusa dal responsabile del procedimento.",
     ALLARME[0][1]),
    ("Il collaudo dell'impianto e' stato completato dalla commissione.",
     ALLARME[1][1]),
]
# ── verso PERMESSO: stessa PAROLA, senso diverso (gia' misurato in W7-61)
PERMESSO = [
    ("Il collaudo dell'impianto e' stato completato dalla commissione.",
     "Modulo di iscrizione: il campo va completato in stampatello. "
     "La domanda si presenta allo sportello entro il 30 aprile."),
]


def main() -> int:
    try:
        from verimem.anti_confab_gate import run_validation_gate
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim as det,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    def misura(claim, fonte):
        d = det(proposition=claim, verified_by=None, source=fonte)
        # 🪞 `ground_write=True` AGGIUNTO dopo la prima esecuzione, ed e' la
        # lezione del banco: senza, il moat NON GIRA e `grounding_score` torna
        # None. La prima stesura mappava None -> -1.0 e concludeva «il moat non
        # approva» — cioe' leggeva **un'assenza di misura come un verdetto**,
        # che e' la classe di errore piu' vecchia del registro.
        g = run_validation_gate(proposition=claim, verified_by=[], topic=None,
                                agent=None, source=fonte, ground_write=True)
        sc = getattr(g, "grounding_score", None)
        if sc is None:
            print("     ⚠️ grounding_score ASSENTE: il moat non ha girato, e non")
            print("        lo leggo come punteggio basso.")
        az = str(getattr(g, "action", None))
        ws = getattr(g, "warnings", None) or []
        lay = ",".join(sorted({str((w or {}).get("layer") or "?") for w in ws})) or "-"
        return ("ferma" if d is not None else "passa",
                (-1.0 if sc is None else float(sc)), az, lay)

    print("  -- CONTROLLO (2): con il participio IDENTICO la cura perdona?")
    ok_id = True
    for claim, fonte in IDENTICO:
        d, sc, az, lay = misura(claim, fonte)
        print(f"     detector {d:<6} moat {sc:6.1f}  {az:<10} [{lay}]  {claim[:44]}")
        ok_id = ok_id and d == "passa"
    if not ok_id:
        print("     CADUTO - non perdona nemmeno la parola identica: non sto")
        print("     misurando la PAROLA, e l'ipotesi non e' verificabile qui.")
        return 1
    print("     retto - con la parola identica passa")

    print("\n  == VERSO **ALLARME**: stesso senso, parola diversa")
    print(f"     {'detector':<10}{'moat':>7}  {'porta':<11}layer")
    all_alto, all_ferma = True, 0
    for claim, fonte in ALLARME:
        d, sc, az, lay = misura(claim, fonte)
        print(f"     {d:<10}{sc:7.1f}  {az:<11}{lay}")
        print(f"        claim: {claim[:70]}")
        if d == "ferma":
            all_ferma += 1
        all_alto = all_alto and sc >= 80.0

    print("\n  == VERSO **PERMESSO**: stessa parola, senso diverso")
    perm_passa = 0
    for claim, fonte in PERMESSO:
        d, sc, az, lay = misura(claim, fonte)
        print(f"     {d:<10}{sc:7.1f}  {az:<11}{lay}")
        print(f"        claim: {claim[:70]}")
        if d == "passa":
            perm_passa += 1

    print("\n  -- L'IPOTESI: e' UN difetto solo, visto da due lati?")
    if all_ferma and perm_passa and all_alto:
        print(f"     🔑 REGGE. Nel verso ALLARME `L1.13` ferma {all_ferma} su"
              f" {len(ALLARME)} parafrasi FEDELI **mentre il moat le approva**")
        print("     (punteggi sopra 80); nel verso PERMESSO lascia passare un")
        print("     claim che la fonte non sostiene. ⇒ **Il criterio guarda la")
        print("     PAROLA, non il SENSO**, e per questo sbaglia in entrambe le")
        print("     direzioni: e' UN difetto, non due.")
    elif all_ferma and not all_alto:
        print("     🪞 FALSIFICATA nella parte che conta: `L1.13` ferma, ma il")
        print("     moat NON approva ⇒ il layer non contraddice il giudice, e la")
        print("     mia lettura «il layer contro il giudice» cade. Il numero")
        print("     resta, la spiegazione no.")
    else:
        print(f"     ⇒ Quadro misto: ALLARME ferma {all_ferma} su {len(ALLARME)},")
        print(f"     PERMESSO passa {perm_passa} su {len(PERMESSO)}, moat alto:"
              f" {all_alto}. Non forzo una tesi su questi numeri.")

    print("\n  ⚠️ COSA NON DICE: due parafrasi per verso, fonti costruite da me,")
    print("  due soli verbi. E il caso originale dell'altra istanza (giudice")
    print("  97,6) NON e' questo: e' la stessa FORMA, non lo stesso caso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
