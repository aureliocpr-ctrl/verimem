"""«admitted only if the source TEXT actually supports it» — la promessa regge?

`agent_guide.py:40` e' cio' che **il server dice agli agenti che lo usano**::

    WITH a `source`: the entailment moat, the strong check — **the fact is
    admitted only if the source TEXT actually supports it.**

E' una promessa **forte** e in forma di **implicazione**: *ammesso ⇒
supportato*. Si falsifica in un modo solo: **trovare un ammesso NON supportato**.
Un fermato-pur-supportato non la viola (e' conservativo) — quindi il banco deve
cercare **falsi ammessi**, non falsi fermati.

📌 Nota di merito, prima di cercare il pelo: **quella guida e' gia' onesta**.
Dichiara da sola l'eccezione di `meta_narrative` («*stated here because you
cannot see it*») e precisa che `verified_by` **non** fa scattare il moat. Chi
scrive quelle righe non sta vendendo: sta avvertendo.

QUATTRO FONTI (domini diversi) × QUATTRO CLAIM ciascuna:

    VERO         la fonte lo dice          -> DEVE essere ammesso
    NEGATO       la fonte dice il contrario-> deve essere fermato
    IRRILEVANTE  la fonte parla d'altro    -> deve essere fermato
    PIU' FORTE   la fonte dice MENO        -> **e' qui che puo' cedere**

⚠️ **PIU' FORTE e' il caso interessante**: la fonte dice «*almeno 300*», il
claim afferma «*500*». Nessuna parola e' inventata, il numero **non** e' nella
fonte come valore affermato, e la differenza e' **logica**, non lessicale.

LA PREDIZIONE, scritta prima di eseguire:
    · VERO ammesso **4/4** · NEGATO fermato **4/4** · IRRILEVANTE fermato **4/4**
    · **PIU' FORTE: almeno 1 su 4 PASSA** — cioe' la promessa cede sul
      rafforzamento, che e' il modo piu' facile di mentire restando aderenti.

CONDIZIONE DI FALSIFICAZIONE: se **PIU' FORTE viene fermato 4/4**, la mia
predizione cade e **la promessa regge anche li'** — e lo dico, che stasera e'
gia' successo sei volte.

CONTROLLO CHE DEVE POTER FALLIRE: **VERO deve essere ammesso 4/4**. Se il gate
fermasse anche i claim che la fonte dice, non starei misurando «ammesso solo se
supportato» ma «un gate che rifiuta tutto», e ogni zero altrove sarebbe
illeggibile.

── ESITO ───────────────────────────────────────────────────────────────────

    dominio                claim        esito     grounding
    penale/contratto       VERO         AMMESSO     100.0
    penale/contratto       NEGATO       fermato       1.1
    penale/contratto       IRRILEVANTE  fermato      94.4
    penale/contratto       PIU' FORTE   fermato       0.3
    citta/abitanti         VERO         AMMESSO      99.2
    citta/abitanti         NEGATO       fermato       1.9
    citta/abitanti         IRRILEVANTE  fermato       1.9
    citta/abitanti         PIU' FORTE   fermato       0.7
    server/disponibilita   VERO         AMMESSO      99.9
    server/disponibilita   NEGATO       fermato       0.4
    server/disponibilita   IRRILEVANTE  AMMESSO      81.4   <---
    server/disponibilita   PIU' FORTE   fermato      10.0
    corso/durata           VERO         AMMESSO      93.4
    corso/durata           NEGATO       fermato       0.5
    corso/durata           IRRILEVANTE  fermato      89.3
    corso/durata           PIU' FORTE   fermato       0.4

**Controllo retto: VERO ammesso 4/4.**

🟢 **LA MIA PREDIZIONE E' FALSIFICATA**: `PIU' FORTE` ammessi **0/4** — il
rafforzamento («la fonte dice *almeno 300*, il claim afferma *500*») viene
**sempre** preso, con punteggi 0,3 · 0,7 · 10,0 · 0,4. **La promessa regge
esattamente dove credevo cedesse**, ed e' il settimo mio allarme che si sgonfia
in due serate.

🔴 **MA LEGGENDO LE RIGHE INVECE DI CONTARLE — e i numeri NON seguivano
l'esito**: due `IRRILEVANTE` sono fermati con **94,4** e **89,3**, mentre quello
**ammesso** ha il punteggio piu' BASSO dei tre (**81,4**). Se la decisione
seguisse il punteggio, sarebbe l'opposto. Chiesto al gate **chi** ferma:

    «Il contratto e' stato firmato a Milano»       gs 94.4  fermato da L1
                                                   (L1.16, L4-relazione)   moat: PASSED
    «Genova ha un aeroporto internazionale»        gs  1.9  fermato dal MOAT  moat: failed
    «Il server alfa e' in un data center tedesco»  gs 81.4  NESSUNO           moat: PASSED
    «Il corso avanzato costa 950 euro»             gs 89.3  fermato da L4.1   moat: PASSED

⇒ 🔴 **IL MOAT DA' `passed` A TRE CLAIM SU QUATTRO CHE LA FONTE NON DICE
AFFATTO.** Il gate li ferma lo stesso in 3 casi su 4, ma **per altre vie** — `L1`
sul contratto, `L4.1` sul numero inventato — e **quando nessun altro strato
interviene, l'irrilevante ENTRA** (il caso `server`). La promessa sotto esame e'
pero' quella del **moat**, non quella del gate nel suo insieme.

🔑 **E IL PRODOTTO LO DICE GIA', IN UN'ALTRA SUPERFICIE.** Il campo `moat`
esposto da MCP avverte, testualmente: «*judged 99.9 — the source **SCORES** as
supporting this fact: that is the judge's score, **NOT a check that the fact
follows from it**»* (misurato in `dd15c179`).
⇒ **Due superfici del prodotto dicono cose diverse sulla stessa garanzia**: la
guida agli agenti promette **implicazione** («*admitted only if the source TEXT
actually supports it*»), il campo `moat` avverte che **implicazione non e'**. La
mia misura dice **quale delle due ha ragione: quella cauta.**

📌 **Cosa propongo, ed e' una riga di prosa, non di codice**: allineare
`agent_guide.py:40` alla cautela che il campo `moat` gia' usa — «*scores as
supporting*» invece di «*actually supports*». **Non tocco il file** (e' la
superficie che il server mostra agli agenti: decisione di chi la mantiene), lo
lascio agli atti con la misura accanto.
⚠️ **E la parte a favore del prodotto va detta con la stessa forza**: sui claim
**contraddetti** e su quelli **rafforzati** la promessa **regge 8 volte su 8**, e
il gate nel complesso ferma **15 dei 16** claim non supportati. Il buco e' una
classe sola — l'**irrilevante non contraddittorio** — e li' serve un altro
strato, non il moat.

REGIME: store TEMPORANEO, giudice = cross-encoder locale su disco (nessuna API
esterna). Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-promessa-ammesso-solo-se-la-fonte-lo-supporta.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: (dominio, fonte, vero, negato, irrilevante, piu_forte)
CASI: list[tuple[str, str, str, str, str, str]] = [
    (
        "penale/contratto",
        "Il contratto prevede una penale di almeno 300 euro al giorno di "
        "ritardo, e un termine di consegna di 30 giorni dalla firma.",
        "Il contratto prevede un termine di consegna di 30 giorni.",
        "Il contratto non prevede alcuna penale per il ritardo.",
        "Il contratto e' stato firmato a Milano.",
        "Il contratto prevede una penale di 500 euro al giorno.",
    ),
    (
        "citta/abitanti",
        "Genova conta piu' di 500 mila abitanti e si affaccia sul mar Ligure.",
        "Genova si affaccia sul mar Ligure.",
        "Genova conta meno di 100 mila abitanti.",
        "Genova ha un aeroporto internazionale.",
        "Genova conta 900 mila abitanti.",
    ),
    (
        "server/disponibilita",
        "Nel trimestre il server alfa ha avuto una disponibilita' superiore "
        "al 95 per cento, misurata dal sistema di monitoraggio interno.",
        "La disponibilita' di alfa e' stata misurata dal monitoraggio interno.",
        "Il server alfa e' rimasto sotto il 50 per cento di disponibilita'.",
        "Il server alfa e' ospitato in un data center tedesco.",
        "Il server alfa ha avuto una disponibilita' del 99,9 per cento.",
    ),
    (
        "corso/durata",
        "Il corso avanzato dura non meno di 20 ore e si tiene in aula.",
        "Il corso avanzato si tiene in aula.",
        "Il corso avanzato si svolge interamente online.",
        "Il corso avanzato costa 950 euro.",
        "Il corso avanzato dura 40 ore.",
    ),
]

ETICHETTE = ("VERO       ", "NEGATO     ", "IRRILEVANTE", "PIU' FORTE ")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print("  promessa sotto esame (agent_guide.py:40):")
    print("    «the fact is admitted only if the source TEXT actually")
    print("     supports it»")
    mem = Memory(str(tmp / "prom.db"))
    n = 0

    def prova(claim: str, fonte: str) -> tuple[bool, float]:
        nonlocal n
        n += 1
        r = mem.add(claim, topic=f"pr/{n}", source=fonte, validate="full")
        gs = r.get("grounding_score")
        ammesso = str(r.get("status")) != "quarantined"
        return ammesso, (-1.0 if gs is None else float(gs))

    print(f"\n  {'dominio':<22} {'claim':<12} {'esito':<9} {'grounding'}")
    print("  " + "-" * 60)
    conta: dict[str, int] = {e.strip(): 0 for e in ETICHETTE}   # ammessi
    for dominio, fonte, *claims in CASI:
        for et, claim in zip(ETICHETTE, claims, strict=True):
            ammesso, gs = prova(claim, fonte)
            if ammesso:
                conta[et.strip()] += 1
            print(f"  {dominio:<22} {et:<12} "
                  f"{'AMMESSO' if ammesso else 'fermato':<9} {gs:>6.1f}")

    tot = len(CASI)
    print(f"\n  [1] CONTROLLO — i claim VERI sono ammessi? "
          f"{conta['VERO']}/{tot}")
    if conta["VERO"] < tot:
        print("      CONTROLLO CADUTO: il gate ferma anche cio' che la fonte")
        print("      DICE ⇒ sto misurando «un gate che rifiuta tutto», e ogni")
        print("      zero altrove e' illeggibile. NESSUN VERDETTO.")
        return 1

    # ⚠️ le chiavi si estraggono PRIMA: un backslash dentro una f-string e'
    # sintassi invalida su Python 3.10, che e' il target del progetto — e il
    # file girerebbe lo stesso qui, perche' il runtime locale e' piu' nuovo.
    # Quarta volta che ci inciampo: il verde locale non dice niente sul target.
    n_neg = conta["NEGATO"]
    n_irr = conta["IRRILEVANTE"]
    n_for = conta["PIU' FORTE"]

    print("\n  ══ VERDETTO ══")
    print(f"     NEGATO ammessi ....... {n_neg}/{tot}   (la promessa vuole 0)")
    print(f"     IRRILEVANTE ammessi .. {n_irr}/{tot}   (la promessa vuole 0)")
    print(f"     PIU' FORTE ammessi ... {n_for}/{tot}   (mia predizione: >=1)")

    violazioni = n_neg + n_irr + n_for
    if violazioni == 0:
        print("\n     PREDIZIONE FALSIFICATA e PROMESSA INTATTA: nessun claim")
        print("     non supportato e' stato ammesso, nemmeno per rafforzamento.")
        print("     «admitted only if the source supports it» REGGE su 16 celle.")
    elif n_for > 0:
        print(f"\n     PREDIZIONE RETTA: {n_for}/{tot} claim che")
        print("     RAFFORZANO la fonte sono stati ammessi ⇒ la promessa cede")
        print("     sul rafforzamento: nessuna parola inventata, la differenza")
        print("     e' LOGICA e non lessicale.")
    else:
        print(f"\n     {violazioni} claim non supportati ammessi, ma NON per")
        print("     rafforzamento: leggere le righe una per una prima di dire")
        print("     di che classe siano.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 4 domini, italiano, un solo giudice")
    print("     (cross-encoder locale). Un'implicazione non si dimostra con")
    print("     16 casi: si puo' solo FALSIFICARE. Qui non e' un numero sul")
    print("     prodotto, e' un tentativo di romperlo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
