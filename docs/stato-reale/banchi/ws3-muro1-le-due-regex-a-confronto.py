"""LIVELLO: due — `run_validation_gate` (lessicale) per il campione grande, e la
porta vera `Memory.add(ground=False)` per le 15. Dichiarato cella per cella.

MURO 1: la regex vecchia contro quella corretta, UNA VARIABILE SOLA, nello stesso
processo e sulle stesse popolazioni.

    python docs/stato-reale/banchi/ws3-muro1-le-due-regex-a-confronto.py [N]

⚡ COSTO ZERO: nessun giudice, nessuno slot. Store di Aurelio in SOLA LETTURA.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alle 21:16 ho segnalato al lead che la sua regex spezzava « e » ma non « ed »,
la forma italiana davanti a vocale: «Il comando warmup e' iniziato alle 14:50:24
ed e' finito alle 14:53:19» dava **un pezzo solo**, e per questo non cadeva.
Alle 21:17 il lead ha corretto (`ed?`) e mi ha rimandato lo script
(msg ce8c16cef134e99a). Rimisurare non e' una formalita': cambiare lo splitter
cambia la POPOLAZIONE trattata, e quindi tutti e tre i miei numeri di stasera.
Le due regex girano qui **nello stesso processo, sugli stessi testi**: un A/B
nella stessa esecuzione e' immune ai confondenti d'ambiente, e lo dichiaro.

    vecchia:  r"\\s*(?:,\\s*e\\s+|\\s+e\\s+|,\\s*and\\s+|\\s+and\\s+|;\\s+)"
    nuova:    r"\\s*(?:,\\s*ed?\\s+|\\s+ed?\\s+|,\\s*and\\s+|\\s+and\\s+|;\\s+)"

━━ PREDIZIONI, scritte PRIMA di eseguire (file creato 04/09 21:30) ━━━━━━━━━━━━
    Q1 la superficie sale di poco: 48,9% -> fra 49,0% e 50,5%. I fatti che
       contengono « ed » sono 301 su 15.262 e solo 153 restavano interi: al
       massimo +1,0 punto. 🔴 muore sopra 50,5% o sotto 49,0%.
    Q2 il falso allarme sale, ma resta dentro l'intervallo di prima
       ([1,2% ; 3,2%]): piu' pezzi = piu' occasioni di cadere, ma cambia la
       decomposizione dell'1% dei fatti. 🔴 muore se esce dall'intervallo.
    Q3 sulle 15, il caso R4 «warmup … ed e' finito» ora si spezza E il pezzo
       «Il comando warmup e' finito alle 14:53:19» viene FERMATO da L1.13:
       il danno passa da 2/10 a 3/10. 🔴 muore se resta 2/10 (allora il pezzo
       passa, e la mia diagnosi di stamattina era sbagliata due volte).

━━ COME MUORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se la correzione della regex spostasse i numeri di molto, vorrebbe dire che i
risultati di stasera dipendevano da un dettaglio ortografico piu' che dalla tesi:
sarebbe un avviso su tutti e tre, non solo su questo banco.
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import sqlite3
import sys
import tempfile

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.client import Memory  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
QUINDICI = ALBERO / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"
SEED = 20260904

VECCHIA = re.compile(r"\s*(?:,\s*e\s+|\s+e\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
NUOVA = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBO_INIZIALE = re.compile(
    r"^(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)\b", re.I)


def claim_atomici(testo: str, coord: re.Pattern[str]) -> list[str]:
    """Lo splitter del lead, verbatim, con la regex passata come parametro:
    e' l'unica variabile che cambia fra i due bracci."""
    try:
        from verimem.subject_extract import subject_of
    except Exception:  # noqa: BLE001
        subject_of = None
    pezzi = [p.strip(" .") for p in coord.split(testo) if p and len(p.split()) >= 3]
    out: list[str] = []
    soggetto = ""
    for p in pezzi:
        if _VERBO_INIZIALE.match(p) and soggetto:
            p = f"{soggetto} {p[0].lower() + p[1:]}"
        else:
            s = subject_of(p) if subject_of else ""
            if not s:
                m_ = re.match(r"^(.*?)\s+(ha|è|e'|hanno|has|is|are|tested|signed)\b", p, re.I)
                s = m_.group(1) if m_ else ""
            soggetto = s.strip() or soggetto
        out.append(p[0].upper() + p[1:] + ".")
    return out or [testo]


def fermato_proxy(t: str) -> bool:
    g = run_validation_gate(proposition=t, verified_by=[], topic=None, agent=None)
    return getattr(g, "action", "persist") in ("downgrade", "reject")


def main() -> None:
    n_camp = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    print("IMPORT DA", verimem.__file__, "\n")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()

    # ── Q1: la superficie ──────────────────────────────────────────────────
    print(f"Q1 · SUPERFICIE sul corpus vivo ({len(righe)} fatti)")
    sup = {}
    for et, coord in (("vecchia", VECCHIA), ("nuova", NUOVA)):
        k = sum(1 for t in righe if len(claim_atomici(t, coord)) >= 2)
        sup[et] = 100.0 * k / len(righe)
        print(f"     regex {et:8s} composti {k:6d}  = {sup[et]:5.2f}%")
    print(f"     ⇒ differenza {sup['nuova'] - sup['vecchia']:+.2f} punti"
          f"   Q1 {'REGGE' if 49.0 <= sup['nuova'] <= 50.5 else '🔴 FALSIFICATA'}")

    # ── Q3: le 15, ALLA PORTA VERA (il livello che decide) ─────────────────
    print("\nQ3 · LE 15 di ws7, alla porta `Memory.add(ground=False)` (non il proxy)")
    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "due_regex.db")

    def fermato_porta(t: str) -> bool:
        return m.add(t, ground=False).get("status") == "quarantined"

    esiti = {}
    for nome, testi in (("tornate", d["elenco_tornate"]), ("restano", d["elenco_restano"])):
        esiti[(nome, "intero")] = sum(fermato_porta(t) for t in testi)
        for et, coord in (("vecchia", VECCHIA), ("nuova", NUOVA)):
            esiti[(nome, et)] = sum(
                any(fermato_porta(p) for p in claim_atomici(t, coord)) for t in testi)
    print(f"     TORNATE (fermare)   intero {esiti[('tornate', 'intero')]}/5"
          f"  · atomico vecchia {esiti[('tornate', 'vecchia')]}/5"
          f"  · atomico NUOVA {esiti[('tornate', 'nuova')]}/5")
    print(f"     RESTANO (ammettere) intero {esiti[('restano', 'intero')]}/10"
          f" · atomico vecchia {esiti[('restano', 'vecchia')]}/10"
          f" · atomico NUOVA {esiti[('restano', 'nuova')]}/10")
    print(f"     ⇒ Q3 (il danno passa da 2 a 3) "
          f"{'REGGE' if esiti[('restano', 'nuova')] == 3 else '🔴 FALSIFICATA'}")
    r4 = [t for t in d["elenco_restano"] if "warmup" in t.lower()]
    if r4:
        pezzi = claim_atomici(r4[0], NUOVA)
        print(f"     il caso R4 «warmup», con la regex nuova: {len(pezzi)} pezzi")
        for p in pezzi:
            print(f"       · «{p[:70]}» -> {'FERMATO' if fermato_porta(p) else 'passa'}")

    # ── Q2: il falso allarme, col proxy, sulle stesse due regex ────────────
    print(f"\nQ2 · FALSO ALLARME su campione casuale (seed {SEED}, proxy lessicale)")
    for et, coord in (("vecchia", VECCHIA), ("nuova", NUOVA)):
        composti = [t for t in righe if len(claim_atomici(t, coord)) >= 2]
        random.Random(SEED).shuffle(composti)
        ammessi = cade = 0
        for t in composti:
            if ammessi >= n_camp:
                break
            if fermato_proxy(t):
                continue
            ammessi += 1
            cade += any(fermato_proxy(p) for p in claim_atomici(t, coord))
        p_ = 100.0 * cade / max(1, ammessi)
        print(f"     regex {et:8s} ammessi {ammessi}  fermati dall'atomico {cade}"
              f"  = {p_:4.2f}%")
        if et == "nuova":
            print(f"     ⇒ Q2 (resta dentro [1,2% ; 3,2%]) "
                  f"{'REGGE' if 1.2 <= p_ <= 3.2 else '🔴 FALSIFICATA'}")


if __name__ == "__main__":
    main()
