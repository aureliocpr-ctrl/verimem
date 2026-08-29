"""Quanto e' grande la classe che il moat non vede: l'irrilevante non contraddittorio.

Un'ora fa (`f675ea4f`) ho misurato su **quattro** casi che il **moat** da'
`passed` a claim che la fonte **non dice affatto**, e che quando nessun altro
strato interviene **entrano**. Quattro casi sono un indizio, non una misura —
e' la mia stessa regola: **«su quanti casi DIVERSI?»**. Qui sono **dodici**, su
dodici fonti diverse.

⚠️ **DUE NUMERI, e vanno tenuti DISTINTI perche' misurano cose diverse:**

    ① `moat: passed` su un irrilevante  -> misura **il MOAT**, cioe' se la
       promessa di `agent_guide.py:40` («*admitted only if the source TEXT
       actually supports it*») descriva quello che il moat fa;
    ② il claim **ENTRA** (nessuno strato lo ferma) -> misura **cio' che il
       cliente subisce**.

**② e' il numero del prodotto, ① e' il numero della promessa.** Confonderli
sarebbe gonfiare o minimizzare a seconda di quale conviene.

📌 **E c'e' un confondente che DEVO separare**: nel banco precedente «*il corso
costa 950 euro*» era fermato da **`L4.1`**, non dal moat — perche' `950` non e'
nella fonte. Un claim irrilevante **che contiene un numero** ha addosso un
guardiano in piu'. Quindi qui: **otto claim SENZA numeri** (dove il moat e' quasi
solo) e **quattro CON numeri** (dove `L4.1` puo' intervenire). La differenza fra
i due gruppi e' informativa quanto il totale.

LA PREDIZIONE, scritta prima di eseguire:
    · ① `moat: passed` su **almeno 8 dei 12** irrilevanti;
    · ② fra i **senza numeri** entrano **piu'** claim che fra i **con numeri**.

CONDIZIONE DI FALSIFICAZIONE: se il moat dice `failed` sulla **maggioranza**
degli irrilevanti, il reperto dei quattro casi era **un caso** — e lo dico:
sarebbe il settimo allarme sgonfiato in due serate.

CONTROLLO CHE DEVE POTER FALLIRE: **tre claim VERI di controllo** devono essere
ammessi con `moat: passed`. Se cadessero, starei misurando un gate rotto e ogni
numero sugli irrilevanti sarebbe illeggibile.

REGIME: store TEMPORANEO, cross-encoder locale (nessuna API esterna). Lo store
di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-quanto-e-grande-la-classe-dell-irrilevante.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: (fonte, claim IRRILEVANTE non contraddittorio, contiene_numeri)
IRRILEVANTI: list[tuple[str, str, bool]] = [
    ("Il contratto prevede una penale per il ritardo e un termine di consegna "
     "di trenta giorni dalla firma.",
     "Il contratto e' stato firmato a Milano.", False),
    ("Genova si affaccia sul mar Ligure ed e' capoluogo di regione.",
     "Genova ha un aeroporto internazionale.", False),
    ("Il server alfa e' monitorato dal sistema interno e ha un contratto di "
     "assistenza attivo.",
     "Il server alfa e' ospitato in un data center tedesco.", False),
    ("Il corso avanzato si tiene in aula e prevede una prova finale scritta.",
     "Il corso avanzato e' tenuto da un docente universitario.", False),
    ("Il fornitore Bianchi consegna con corriere espresso e accetta resi entro "
     "il termine di legge.",
     "Il fornitore Bianchi ha sede in Veneto.", False),
    ("Il magazzino centrale e' aperto dal lunedi' al venerdi' e dispone di una "
     "cella refrigerata.",
     "Il magazzino centrale e' dotato di impianto antincendio.", False),
    ("Il volume e' stampato su carta riciclata e rilegato in brossura.",
     "Il volume e' stato tradotto dal francese.", False),
    ("La riunione si tiene in videoconferenza e viene registrata per il "
     "verbale.",
     "La riunione e' presieduta dal direttore generale.", False),
    # con numeri: L4.1 puo' intervenire, e la differenza e' informativa
    ("Il contratto prevede una penale per il ritardo e un termine di consegna "
     "di trenta giorni dalla firma.",
     "Il contratto prevede un anticipo di 2500 euro.", True),
    ("Il corso avanzato si tiene in aula e prevede una prova finale scritta.",
     "Il corso avanzato costa 950 euro.", True),
    ("Il magazzino centrale e' aperto dal lunedi' al venerdi' e dispone di una "
     "cella refrigerata.",
     "Il magazzino centrale ha 14 banchine di carico.", True),
    ("Il fornitore Bianchi consegna con corriere espresso e accetta resi entro "
     "il termine di legge.",
     "Il fornitore Bianchi impiega 37 dipendenti.", True),
]

#: controllo positivo: veri, devono passare col moat
CONTROLLI: list[tuple[str, str]] = [
    ("Genova si affaccia sul mar Ligure ed e' capoluogo di regione.",
     "Genova si affaccia sul mar Ligure."),
    ("Il corso avanzato si tiene in aula e prevede una prova finale scritta.",
     "Il corso avanzato prevede una prova finale scritta."),
    ("Il magazzino centrale e' aperto dal lunedi' al venerdi' e dispone di una "
     "cella refrigerata.",
     "Il magazzino centrale dispone di una cella refrigerata."),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    mem = Memory(str(tmp / "irr.db"))
    n = 0

    def prova(claim: str, fonte: str) -> tuple[str, float, bool, str]:
        nonlocal n
        n += 1
        r = mem.add(claim, topic=f"cl/{n}", source=fonte, validate="full")
        gs = r.get("grounding_score")
        return (str(r.get("moat"))[:24],
                -1.0 if gs is None else float(gs),
                str(r.get("status")) != "quarantined",
                str(r.get("quarantined_by") or "-"))

    # ── CONTROLLO PRIMA, cosi' un banco rotto si vede subito ─────────────
    print("\n  [1] CONTROLLO — tre claim VERI devono entrare con moat passed:")
    ok_ctrl = 0
    for fonte, claim in CONTROLLI:
        moat, gs, entra, _qb = prova(claim, fonte)
        buono = entra and moat.startswith("passed")
        ok_ctrl += buono
        print(f"      {claim[:46]:<48} moat={moat:<10} gs={gs:>5.1f} "
              f"{'AMMESSO' if entra else 'fermato'}  {'ok' if buono else 'NO'}")
    if ok_ctrl < len(CONTROLLI):
        print("      CONTROLLO CADUTO: i claim VERI non passano ⇒ misuro un")
        print("      gate rotto, e ogni numero sugli irrilevanti e'")
        print("      illeggibile. NESSUN VERDETTO.")
        return 1

    # ── LA CLASSE ────────────────────────────────────────────────────────
    print("\n  [2] DODICI IRRILEVANTI NON CONTRADDITTORI")
    print(f"      {'claim':<46} {'moat':<10} {'gs':>5}  esito  fermato-da")
    moat_passed = {"senza": 0, "con": 0}
    entrati = {"senza": 0, "con": 0}
    totali = {"senza": 0, "con": 0}
    for fonte, claim, ha_num in IRRILEVANTI:
        g = "con" if ha_num else "senza"
        totali[g] += 1
        moat, gs, entra, qb = prova(claim, fonte)
        if moat.startswith("passed"):
            moat_passed[g] += 1
        if entra:
            entrati[g] += 1
        print(f"      {claim[:46]:<48} {moat:<10} {gs:>5.1f}  "
              f"{'ENTRA  ' if entra else 'fermato'}  {qb}")

    tot = sum(totali.values())
    mp = sum(moat_passed.values())
    en = sum(entrati.values())

    print("\n  ══ VERDETTO — DUE NUMERI, TENUTI DISTINTI ══")
    print(f"     ① `moat: passed` su un IRRILEVANTE ..... {mp}/{tot}"
          f"   (misura LA PROMESSA)")
    print(f"     ② il claim ENTRA davvero ............... {en}/{tot}"
          f"   (misura CIO' CHE IL CLIENTE SUBISCE)")
    print(f"\n     senza numeri: moat passed {moat_passed['senza']}/"
          f"{totali['senza']} · entrati {entrati['senza']}/{totali['senza']}")
    print(f"     con numeri:   moat passed {moat_passed['con']}/"
          f"{totali['con']} · entrati {entrati['con']}/{totali['con']}")

    if mp <= tot // 2:
        print("\n     PREDIZIONE FALSIFICATA: il moat FERMA la maggioranza degli")
        print("     irrilevanti ⇒ il reperto dei quattro casi era un caso, e lo")
        print("     dico: settimo allarme sgonfiato in due serate.")
    else:
        print(f"\n     PREDIZIONE RETTA su ①: il moat marca `passed` {mp} volte")
        print(f"     su {tot} ⇒ NON distingue l'irrilevante dal supportato, e la")
        print("     promessa «admitted only if the source supports it» descrive")
        print("     qualcosa che il moat non fa.")
        if en < mp:
            print(f"     🟢 MA il gate ne ferma {mp - en} che il moat lasciava")
            print(f"        passare: entrano {en}/{tot}, non {mp}/{tot}. La difesa")
            print("        in profondita' FUNZIONA — va detto con la stessa forza.")

    print(f"\n  ⚠️ LIMITI: {n} celle, italiano, un giudice (cross-encoder")
    print("     locale), fonti corte e costruite. NON e' un numero sul")
    print("     prodotto: e' la dimensione di UNA classe su un campione mio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
