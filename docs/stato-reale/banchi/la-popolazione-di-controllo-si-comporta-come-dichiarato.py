"""LA POPOLAZIONE DI CONTROLLO SI COMPORTA COME DICHIARATO? — la misuro prima di darla.

Una popolazione di controllo che nessuno ha misurato e' un'asserzione, non uno
strumento: se i casi non si comportano come il file dichiara, chiunque la usi
misura il mio errore invece del suo layer.

Qui la eseguo tutta e **dichiaro i casi che non fanno quello che ho scritto**,
invece di toglierli e far tornare i conti.

Atteso, dal file `popolazione_di_controllo_completamento.py`:
  A  self-claim senza fonte ............. FERMATI
  B  veri con fonte che li sostiene ..... PASSANO
  C  veri con fonte che non sostiene .... FERMATI
  D  reali dal corpus, fonte ricostruita  PASSANO (la fonte porta il participio)

CONTROLLI CHE POSSONO FALLIRE:
 (1) se A non e' fermata al 100%, il presidio non e' acceso su questa
     popolazione e il resto della misura non vale.
 (2) ogni scostamento da B, C e D va STAMPATO caso per caso: e' l'informazione
     che serve a chi la usera'.

    python -u docs/stato-reale/banchi/la-popolazione-di-controllo-si-comporta-come-dichiarato.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from popolazione_di_controllo_completamento import (  # noqa: E402
    REALI_DAL_CORPUS,
    SELFCLAIM_SENZA_FONTE,
    TAGLIE,
    VERI_CON_FONTE,
    VERI_CON_FONTE_CHE_NON_SOSTIENE,
)


def main() -> int:
    try:
        from verimem import l1_completion_detector as det
        from verimem.l1_completion_detector import (
            detect_unsupported_completion_claim,
        )
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1
    print(f"  codice sotto misura: {det.__file__}")
    for k, v in TAGLIE.items():
        print(f"  {k}: {v}")

    def ferma(claim, source=None):
        r = detect_unsupported_completion_claim(
            proposition=claim, verified_by=[], source=source)
        return r is not None

    scostamenti = []

    print(f"\n  == A. SELF-CLAIM SENZA FONTE — attesi TUTTI fermati")
    a_ok = 0
    for c in SELFCLAIM_SENZA_FONTE:
        if ferma(c):
            a_ok += 1
        else:
            scostamenti.append(("A", c, "PASSA ma doveva essere fermato"))
            print(f"     ⚠️ PASSA  {c[:66]}")
    print(f"     ⇒ fermati {a_ok} su {len(SELFCLAIM_SENZA_FONTE)}")

    print(f"\n  == B. VERI CON FONTE CHE LI SOSTIENE — attesi TUTTI passanti")
    b_ok = 0
    for c, s in VERI_CON_FONTE:
        if not ferma(c, s):
            b_ok += 1
        else:
            scostamenti.append(("B", c, "FERMATO ma doveva passare"))
            print(f"     ⚠️ FERMATO  {c[:64]}")
    print(f"     ⇒ passano {b_ok} su {len(VERI_CON_FONTE)}")

    print(f"\n  == C. VERI CON FONTE CHE NON SOSTIENE — attesi TUTTI fermati")
    c_ok = 0
    for c, s in VERI_CON_FONTE_CHE_NON_SOSTIENE:
        if ferma(c, s):
            c_ok += 1
        else:
            scostamenti.append(("C", c, "PASSA ma doveva essere fermato"))
            print(f"     ⚠️ PASSA  {c[:66]}")
    print(f"     ⇒ fermati {c_ok} su {len(VERI_CON_FONTE_CHE_NON_SOSTIENE)}")

    print(f"\n  == D. REALI DAL CORPUS (fonte ricostruita) — attesi passanti")
    d_ok = 0
    for c, s in REALI_DAL_CORPUS:
        if not ferma(c, s):
            d_ok += 1
        else:
            scostamenti.append(("D", c, "FERMATO ma la fonte porta il participio"))
            print(f"     ⚠️ FERMATO  {c[:64]}")
    print(f"     ⇒ passano {d_ok} su {len(REALI_DAL_CORPUS)}")

    print("\n  -- CONTROLLO (1): il presidio e' ACCESO su A?")
    if a_ok < len(SELFCLAIM_SENZA_FONTE):
        print(f"     PARZIALE - {a_ok} su {len(SELFCLAIM_SENZA_FONTE)}: i casi")
        print("     che passano sono stampati sopra e restano nel file, perche'")
        print("     una popolazione da cui tolgo cio' che non torna misura me.")
    else:
        print(f"     retto - {a_ok} su {len(SELFCLAIM_SENZA_FONTE)} fermati")

    print("\n  -- CONTROLLO (2): gli scostamenti, tutti")
    if not scostamenti:
        print("     nessuno: la popolazione si comporta come dichiarata.")
    else:
        print(f"     {len(scostamenti)} casi non fanno quello che il file dice:")
        for gruppo, c, perche in scostamenti:
            print(f"       [{gruppo}] {perche}")
            print(f"            {c[:70]}")
        print("\n     ⇒ RESTANO NEL FILE, con questa riga a documentarli. Chi la")
        print("     usa deve saperlo; toglierli farebbe tornare i conti e")
        print("     nasconderebbe proprio i casi difficili.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
