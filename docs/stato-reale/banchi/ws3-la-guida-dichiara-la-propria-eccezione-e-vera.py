"""La guida dichiara da sola la propria eccezione: e' vera?

`agent_guide.py:32-39` fa una cosa che i documenti di prodotto quasi mai fanno —
**dichiara un buco della propria garanzia, e dice perche' lo sta dicendo**:

    ONE EXCEPTION, measured 2026-08-28 and **stated here because you cannot see
    it**: a write made as a session NOTE — `meta_narrative=True`, which the
    `save` command uses — **skips that screen**. It is deliberate… But it means
    the screen is not literally universal… **The moat is UNAFFECTED**: with a
    source it runs in both modes, so a source is what protects you either way.

Sono **due affermazioni distinte**, e vanno verificate separatamente:

    ① con `meta_narrative=True` lo **screen lessicale L1** viene SALTATO
    ② con `meta_narrative=True` il **moat gira lo stesso** (quindi una fonte
      che NEGA quarantina comunque)

⚠️ La seconda e' la piu' importante: **e' la parte che rende innocua la prima**.
Se cadesse, l'eccezione non sarebbe «una nota di sessione salta lo screen» ma
«una nota di sessione **non e' controllata da niente**» — e la guida direbbe il
falso proprio dove sta cercando di essere onesta.

LA PREDIZIONE, scritta prima di eseguire: **entrambe reggono**. La guida e'
stata precisa altrove (l'ho verificata tutta stasera), e chi scrive «*stated
here because you cannot see it*» non sta vendendo.

CONDIZIONE DI FALSIFICAZIONE: se ② cade — cioe' se con `meta_narrative=True` una
fonte che nega **non** quarantina — la guida promette una protezione che non
c'e', **nel punto in cui dichiara un'eccezione**. Sarebbe il reperto piu' grave
della serata.

CONTROLLI CHE DEVONO POTER FALLIRE: gli stessi due casi **senza**
`meta_narrative` devono comportarsi da manuale — autoclaim **fermato da L1**,
fonte-che-nega **fermata dal moat**. Se i controlli non si comportassero cosi',
non misurerei l'eccezione: misurerei un gate che non funziona.

REGIME: store TEMPORANEO, cross-encoder locale (nessuna API esterna). Lo store
di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-la-guida-dichiara-la-propria-eccezione-e-vera.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: autoclaim: senza `meta_narrative` L1 li prende
AUTOCLAIM = [
    "Il fix funziona ed e' verificato.",
    "La migrazione e' completata e testata con successo.",
]

#: (claim, fonte che lo NEGA): il moat deve fermarli in entrambe le modalita'
NEGATI = [
    ("La penale e' di 500 euro al giorno.",
     "Il contratto fissa la penale in 120 euro al giorno."),
    ("Il magazzino resta aperto la domenica.",
     "Il magazzino osserva la chiusura domenicale."),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    mem = Memory(str(tmp / "meta.db"))
    n = 0

    def scrivi(claim: str, fonte: str | None, meta: bool) -> tuple[bool, str]:
        nonlocal n
        n += 1
        kw: dict = {"meta_narrative": True} if meta else {}
        if fonte:
            kw["source"] = fonte
        r = mem.add(claim, topic=f"mn/{n}", validate="full", **kw)
        return (str(r.get("status")) == "quarantined",
                str(r.get("quarantined_by") or "-"))

    # ── ① lo screen lessicale viene saltato? ─────────────────────────────
    print("\n  [1] AUTOCLAIM — lo screen L1 viene saltato con meta_narrative?")
    ctrl1 = 0
    saltato = 0
    for claim in AUTOCLAIM:
        q_no, qb_no = scrivi(claim, None, meta=False)
        q_si, qb_si = scrivi(claim, None, meta=True)
        if q_no:
            ctrl1 += 1
        if not q_si:
            saltato += 1
        print(f"      {claim[:40]:<42} senza={'FERMATO ' if q_no else 'passa   '}"
              f"({qb_no})  con meta={'fermato' if q_si else 'PASSA  '}({qb_si})")
    print(f"      controllo (senza meta L1 ferma): {ctrl1}/{len(AUTOCLAIM)}"
          f"   ·   eccezione osservata: {saltato}/{len(AUTOCLAIM)}")

    # ── ② il moat gira lo stesso? ────────────────────────────────────────
    print("\n  [2] FONTE CHE NEGA — il moat gira anche con meta_narrative?")
    ctrl2 = 0
    moat_regge = 0
    for claim, fonte in NEGATI:
        q_no, qb_no = scrivi(claim, fonte, meta=False)
        q_si, qb_si = scrivi(claim, fonte, meta=True)
        if q_no:
            ctrl2 += 1
        if q_si:
            moat_regge += 1
        print(f"      {claim[:40]:<42} senza={'FERMATO ' if q_no else 'passa   '}"
              f"({qb_no})  con meta={'FERMATO' if q_si else 'passa  '}({qb_si})")
    print(f"      controllo (senza meta il moat ferma): {ctrl2}/{len(NEGATI)}"
          f"   ·   moat regge con meta: {moat_regge}/{len(NEGATI)}")

    if ctrl1 < len(AUTOCLAIM) or ctrl2 < len(NEGATI):
        print("\n  CONTROLLO CADUTO: senza `meta_narrative` il gate non si")
        print("  comporta da manuale ⇒ non misuro l'eccezione, misuro un gate")
        print("  che non funziona. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     ① lo screen L1 viene saltato ....... "
          f"{saltato}/{len(AUTOCLAIM)}   (la guida dice: SI')")
    print(f"     ② il moat gira lo stesso ........... "
          f"{moat_regge}/{len(NEGATI)}   (la guida dice: SI')")
    if saltato == len(AUTOCLAIM) and moat_regge == len(NEGATI):
        print("     ENTRAMBE REGGONO: la guida descrive con precisione la")
        print("     propria eccezione — dice che c'e' un buco, dove sta, e")
        print("     cosa continua a proteggere. 🟢 Va detto, perche' e' raro:")
        print("     un documento di prodotto che dichiara il proprio limite")
        print("     «because you cannot see it» e poi RISULTA ESATTO.")
    elif moat_regge < len(NEGATI):
        print("     🔴 ② CADE: con `meta_narrative` una fonte che NEGA non")
        print("     quarantina ⇒ l'eccezione non e' «salta lo screen» ma «non")
        print("     e' controllata da niente», e la guida dice il falso proprio")
        print("     dove cerca di essere onesta. E' il reperto piu' grave della")
        print("     serata.")
    else:
        print("     ① non si osserva: `meta_narrative` NON salta lo screen su")
        print("     questi casi ⇒ la guida e' piu' pessimista del prodotto,")
        print("     oppure l'eccezione dipende da qualcosa che non ho variato.")

    print(f"\n  ⚠️ LIMITI: {n} celle, 2 autoclaim e 2 negati, italiano, porta")
    print("     SDK. La guida cita il comando `save` (CLI): io ho usato")
    print("     `Memory.add(meta_narrative=True)`, che e' la stessa bandiera")
    print("     ma non lo stesso percorso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
