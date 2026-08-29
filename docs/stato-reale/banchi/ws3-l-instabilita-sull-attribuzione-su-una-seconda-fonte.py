"""L'instabilita' sull'attribuzione regge su una SECONDA fonte?

Alle 01:55 (`1a9bfc9a`) ho misurato, a variabile singola, che il giudice e'
**stabile sulla presenza** (`vero` 99,4-99,6 e `assente` 0,7 in tutte e sei le
righe) e **instabile sull'attribuzione** (lo scambio va da **8,2 a 73,0**
cambiando **un solo token**). E' l'unico reperto della nottata con una variabile
sola e i controlli fermi — **ed e' su UNA fonte.**

Stanotte ho gia' ritirato due reperti costruiti su una fonte sola. **La prima
domanda su qualunque numero e': su quante fonti DIVERSE?** Qui la risposta era
«una», quindi la seconda e' d'obbligo prima di consegnarlo.

IL DISEGNO: la **stessa matrice** — sei soggetti, stessa struttura di claim — su
un **dominio completamente diverso** (citta' e abitanti invece di workflow e
run), con verbi e unita' diverse.

LA PREDIZIONE, scritta prima di eseguire:
    · i **controlli restano fermi** anche sulla seconda fonte (`vero` alto e
      `assente` basso in ogni riga);
    · lo **scambio resta SPARSO**, cioe' l'intervallo fra il minimo e il
      massimo resta ampio (>30 punti).
    · ⚠️ **NON** predico che siano gli STESSI soggetti a passare: se lo fossero
      sarebbe un'informazione in piu', ma non e' cio' che sostiene il reperto.

CONDIZIONE DI FALSIFICAZIONE: se sulla seconda fonte lo scambio e' **compatto**
(intervallo <15 punti), l'instabilita' non e' una proprieta' del giudice ma
della **prima fonte**, e il reperto va **ristretto a quella**.

CONTROLLO CHE DEVE POTER FALLIRE: se `vero` o `assente` si muovono al cambiare
del soggetto, allora il token disturba **tutto** e non solo l'attribuzione —
e la lettura «stabile sulla presenza, instabile sull'attribuzione» cade.

🔴 **ESITO: PREDIZIONE FALSIFICATA. IL REPERTO DELLE 01:55 SI RESTRINGE.**

    dominio                        scambio            ampiezza
    ① workflow/run (gia' misurata)   8.2 → 73.0          64.8
    ② citta'/abitanti (NUOVA)        0.6 →  2.4           1.8

I **controlli restano fermi in entrambi** (`vero` 99,4-99,9 · `assente`
0,6-0,9), quindi il nullo del dominio ② e' **leggibile**: non e' uno strumento
spento, e' il giudice che **prende tutti e sei gli scambi**.

⇒ **L'instabilita' e' una proprieta' di QUELLA fonte, non del giudice.** Il
reperto delle 01:55 va **ristretto**: su una fonte il giudice sbanda di 65
punti al cambiare di un token, su un'altra e' compatto entro 1,8. **Non posso
dire «il giudice e' instabile sull'attribuzione»: posso dire che esiste almeno
una fonte su cui lo e'.**

📌 E i soggetti che passavano nel dominio ① (`ci`, `si`, `deploy`, `build`) nel
dominio ② non passano: **zero in comune** — coerente con «e' la fonte», non «e'
il token».

💡 **OSSERVAZIONE NON MISURATA, e la lascio tale.** Le due fonti differiscono
per piu' di una cosa, e la piu' vistosa e' che nel dominio ① ogni soggetto porta
**DUE numeri** («50 run, di cui 0 cancellati») mentre nel ② ne porta **UNO**.
Sarebbe una spiegazione plausibile — **e plausibile e' esattamente cio' che
stanotte mi ha fregato quattro volte.** Non la misuro e non la consegno: la
scrivo come **prossima domanda**.

🔑 **BILANCIO DEL FILONE**: quattro tentativi di dire qualcosa di generale sul
giudice (forma, lingua, soggetto-clitico, instabilita'), **quattro
restringimenti**. Quel che resta di solido e' molto piccolo e molto onesto:
**su UNA fonte costruita, il verdetto sull'attribuzione oscilla di 65 punti per
un token irrilevante, mentre presenza e assenza restano fermi.** Il resto e'
**non misurato**.

REGIME: store TEMPORANEO, cross-encoder locale su disco (nessuna API esterna).
Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-l-instabilita-sull-attribuzione-su-una-seconda-fonte.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

SOGGETTI = ["ci", "si", "ne", "alfa", "deploy", "build"]
SOGLIA = 50.0


def dominio_workflow(sog: str) -> tuple[str, str, str, str]:
    f = (f"Il workflow {sog} ha avuto 50 run, di cui 0 cancellati. "
         f"Il workflow security ha avuto 60 run, di cui 59 cancellati.")
    return (f,
            "Il workflow security ha 59 run cancellati.",
            f"Il workflow {sog} ha 59 run cancellati.",
            f"Il workflow {sog} ha 777 run cancellati.")


def dominio_citta(sog: str) -> tuple[str, str, str, str]:
    f = (f"La citta' di {sog} conta 390 mila abitanti. "
         f"La citta' di Genova conta 560 mila abitanti.")
    return (f,
            "La citta' di Genova conta 560 mila abitanti.",
            f"La citta' di {sog} conta 560 mila abitanti.",
            f"La citta' di {sog} conta 902 mila abitanti.")


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print("  giudice: cross-encoder locale su disco (nessuna API esterna)")
    mem = Memory(str(tmp / "due.db"))
    n = 0

    def s(claim: str, f: str) -> float:
        nonlocal n
        n += 1
        v = mem.add(claim, topic=f"d2/{n}", source=f,
                    validate="full").get("grounding_score")
        return -1.0 if v is None else float(v)

    esiti: dict[str, dict[str, tuple[float, float, float]]] = {}
    for nome, costruttore in (("① workflow/run (gia' misurata)", dominio_workflow),
                              ("② citta'/abitanti (NUOVA)", dominio_citta)):
        print(f"\n  ── {nome}")
        print(f"     {'soggetto':<10} {'vero':>7} {'SCAMBIO':>8} {'assente':>8}"
              f"  controllo")
        esiti[nome] = {}
        for sog in SOGGETTI:
            f, vero, scambio, assente = costruttore(sog)
            v, sc, a = s(vero, f), s(scambio, f), s(assente, f)
            esiti[nome][sog] = (v, sc, a)
            ok = v > SOGLIA and a < SOGLIA
            print(f"     {sog:<10} {v:>7.1f} {sc:>8.1f} {a:>8.1f}"
                  f"  {'ok' if ok else 'CONTROLLO ROTTO'}")

    print("\n  [1] I CONTROLLI RESTANO FERMI IN ENTRAMBI I DOMINI?")
    controlli_ok = True
    for nome, righe in esiti.items():
        veri = [v for v, _sc, _a in righe.values()]
        ass = [a for _v, _sc, a in righe.values()]
        fermo = (min(veri) > SOGLIA and max(ass) < SOGLIA)
        controlli_ok = controlli_ok and fermo
        print(f"      {nome:<32} vero {min(veri):.1f}-{max(veri):.1f} · "
              f"assente {min(ass):.1f}-{max(ass):.1f}  "
              f"{'fermi' if fermo else 'MOSSI'}")
    if not controlli_ok:
        print("      CONTROLLO CADUTO: i controlli si muovono col soggetto ⇒ il")
        print("      token disturba TUTTO e la lettura «stabile sulla presenza,")
        print("      instabile sull'attribuzione» CADE. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    compatti = []
    for nome, righe in esiti.items():
        sc = [x for _v, x, _a in righe.values()]
        amp = max(sc) - min(sc)
        print(f"     {nome:<32} scambio {min(sc):5.1f} → {max(sc):5.1f}"
              f"   ampiezza {amp:5.1f}")
        if amp < 15:
            compatti.append(nome)
    if compatti:
        print(f"     PREDIZIONE FALSIFICATA in: {', '.join(compatti)}")
        print("     ⇒ lo scambio e' COMPATTO li' ⇒ l'instabilita' non e' una")
        print("       proprieta' del giudice ma della PRIMA fonte, e il reperto")
        print("       delle 01:55 va RISTRETTO a quella.")
    else:
        print("     PREDIZIONE RETTA: su ENTRAMBE le fonti i controlli restano")
        print("     fermi e lo scambio resta SPARSO ⇒ l'instabilita'")
        print("     sull'attribuzione NON e' un fatto di quella fonte.")

    # informazione in piu', NON parte del reperto: passano gli stessi soggetti?
    passa = {nome: {s_ for s_, (_v, sc, _a) in righe.items() if sc > SOGLIA}
             for nome, righe in esiti.items()}
    a, b = list(passa.values())
    print("\n     (di contorno, NON sostiene il reperto) soggetti che passano:")
    print(f"       ① {sorted(a) or 'nessuno'}")
    print(f"       ② {sorted(b) or 'nessuno'}")
    print(f"       in comune: {sorted(a & b) or 'nessuno'}")

    print(f"\n  ⚠️ LIMITI: {n} celle, due fonti, un giudice (cross-encoder")
    print("     locale), italiano. NON e' un numero sul prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
