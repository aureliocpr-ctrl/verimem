"""LIVELLO: due, dichiarati cella per cella — la porta vera `Memory.add(ground=False)`
per le 15 di ws7, il proxy `run_validation_gate` (validato ieri 4/4 contro la
porta) per il campione grande.

MURO 1, fase 2: i veri che cadono sotto decomposizione cadono perche' il pezzo
non ha la FORMA di un claim — e un filtro di forma li salva senza riaprire i falsi.

    python docs/stato-reale/banchi/ws3-muro1-fase2-il-filtro-di-forma-salva-i-veri.py [N]

⚡ COSTO ZERO: nessun giudice, nessuno slot. Store di Aurelio in SOLA LETTURA.
Finestra di attesa dichiarata: ~5 s a scrittura alla porta, 45 scritture -> 225 s
attese, dichiaro 500 s; il proxy sul campione e' lessicale, sotto i 60 s.

━━ LA CONCATENAZIONE (letteratura in docs/ricerca/2026-09-05-…md) ━━━━━━━━━━━━━━
Ieri: la decomposizione del lead ferma 2/10 veri sulle 15 e 16/800 sul campione
non scelto, e guardando QUALI cadono sono frammenti degeneri («Indietro 16 con
tracciato 0.»), citazioni spezzate, completamenti nudi («Finito alle 22:32.»).
RefChecker (2405.14486) dice che l'unita' giusta e' una TRIPLETTA soggetto-
predicato-oggetto, e che quella granularita' batte frase e sub-frase di 6,8-26,1
punti. Un frammento senza soggetto o senza verbo finito NON e' una tripletta:
non e' un claim, e' un pezzo di claim. Giudicarlo e' l'errore.

TESI: filtrare i pezzi per FORMA — «giudica solo i pezzi con soggetto e verbo
finito» — toglie il danno collaterale senza togliere il guadagno.
Il filtro NON lo invento: e' `verimem.subject_extract.subject_of`, che torna ''
quando il testo non ha un soggetto davanti a un verbo finito. Uso una funzione
del prodotto, cosi' la cura e' gia' nel suo vocabolario.

━━ PREDIZIONI, depositate sul canale PRIMA (fc8b697a4d90ce14, 20:55) ━━━━━━━━━━
    T1 fra i pezzi che fanno cambiare verdetto ai 16 del campione, ALMENO 8 sono
       senza forma (subject_of == ''). 🔴 muore sotto 8: il problema e' semantico,
       non di forma, e il filtro non e' la cura.
    T2 col filtro, il danno sulle 10 di ws7 scende da 2/10 a <= 1/10, e i 5 che
       devono essere fermati restano 5/5. 🔴 muore se i 5 scendono: il filtro
       salva anche i falsi, e allora costa piu' di quanto rende.
    T3 col filtro, il falso allarme sul campione n=800 scende sotto l'1,0%
       (ieri 2,12% [1,2 ; 3,2]). 🔴 muore se resta >= 1,2%.
⚠️ T1 e T2/T3 usano lo STESSO criterio (subject_of): non sono tre misure
   indipendenti, sono una diagnosi e due effetti. T1 pero' puo' morire da sola.

━━ COSA NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il filtro puo' anche NASCONDERE una self-claim vera scritta senza soggetto («e'
tutto verificato.» -> subject_of == '' -> non giudicata). Lo misuro nel banco
delle subordinate e nel controllo dei 5: se un falso passa PERCHE' il filtro lo
ha esentato, e' un costo del filtro e va scritto accanto al guadagno.
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
from verimem.subject_extract import subject_of  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
QUINDICI = ALBERO / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"
SEED = 20260904

# lo splitter del lead con le DUE cure di ieri: « ed » e la guardia senza \b
_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBI = r"(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)"
_VERBO_INIZIALE = re.compile(rf"^{_VERBI}(?=\s|$)", re.I)


def claim_atomici(testo: str) -> list[str]:
    pezzi = [p.strip(" .") for p in _COORD.split(testo) if p and len(p.split()) >= 3]
    out: list[str] = []
    soggetto = ""
    for p in pezzi:
        if _VERBO_INIZIALE.match(p) and soggetto:
            p = f"{soggetto} {p[0].lower() + p[1:]}"
        else:
            s = subject_of(p)
            if not s:
                m_ = re.match(rf"^(.*?)\s+{_VERBI}\b", p, re.I)
                s = m_.group(1) if m_ else ""
            soggetto = s.strip() or soggetto
        out.append(p[0].upper() + p[1:] + ".")
    return out or [testo]


def ha_forma(p: str) -> bool:
    """Il filtro: soggetto davanti a un verbo finito, secondo il prodotto."""
    return bool(subject_of(p))


def fermato_proxy(t: str) -> bool:
    g = run_validation_gate(proposition=t, verified_by=[], topic=None, agent=None)
    return getattr(g, "action", "persist") in ("downgrade", "reject")


def atomico(t: str, fermato, filtro: bool) -> tuple[bool, list[str]]:
    """FERMATO se cade almeno un pezzo (MIN); col filtro si giudicano solo i pezzi con forma."""
    pezzi = claim_atomici(t)
    giudicati = [p for p in pezzi if (ha_forma(p) if filtro else True)] or pezzi
    caduti = [p for p in giudicati if fermato(p)]
    return bool(caduti), caduti


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> None:
    n_camp = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    print("IMPORT DA", verimem.__file__, "\n")

    # ── T2: le 15, ALLA PORTA ─────────────────────────────────────────────
    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "forma.db")

    def fermato_porta(t: str) -> bool:
        return m.add(t, ground=False).get("status") == "quarantined"

    print("T2 · LE 15 di ws7, alla porta `Memory.add(ground=False)`")
    esiti = {}
    for nome, testi in (("tornate", d["elenco_tornate"]), ("restano", d["elenco_restano"])):
        for filtro in (False, True):
            k = 0
            for t in testi:
                cade, _ = atomico(t, fermato_porta, filtro)
                k += cade
            esiti[(nome, filtro)] = k
    print(f"   TORNATE (fermare)   senza filtro {esiti[('tornate', False)]}/5"
          f"  · col filtro {esiti[('tornate', True)]}/5")
    print(f"   RESTANO (ammettere) senza filtro {esiti[('restano', False)]}/10"
          f" · col filtro {esiti[('restano', True)]}/10")
    t2 = esiti[("restano", True)] <= 1 and esiti[("tornate", True)] == 5
    print(f"   ⇒ T2 {'REGGE' if t2 else '🔴 FALSIFICATA'}")
    for t in d["elenco_restano"]:
        cade, caduti = atomico(t, fermato_porta, True)
        if cade:
            print(f"      resta fermato col filtro: «{caduti[0][:70]}»")

    # ── T1 + T3: il campione, col proxy ───────────────────────────────────
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()
    composti = [t for t in righe if len(claim_atomici(t)) >= 2]
    random.Random(SEED).shuffle(composti)

    ammessi = cade_senza = cade_con = 0
    senza_forma = con_forma = 0
    quali: list[tuple[str, str, bool]] = []
    for t in composti:
        if ammessi >= n_camp:
            break
        if fermato_proxy(t):
            continue
        ammessi += 1
        c1, caduti = atomico(t, fermato_proxy, False)
        c2, _ = atomico(t, fermato_proxy, True)
        cade_senza += c1
        cade_con += c2
        if c1:
            for p in caduti:
                f = ha_forma(p)
                con_forma += f
                senza_forma += not f
                quali.append((t, p, f))

    print(f"\nT1 · I PEZZI CHE FANNO CAMBIARE VERDETTO (campione di {ammessi}, corpus {len(righe)})")
    print(f"   fatti che cambiano verdetto      : {cade_senza}")
    print(f"   pezzi caduti SENZA forma (subject_of == '') : {senza_forma}")
    print(f"   pezzi caduti CON forma                      : {con_forma}")
    print(f"   ⇒ T1 (almeno 8 senza forma) {'REGGE' if senza_forma >= 8 else '🔴 FALSIFICATA'}")
    print("   QUALI, i primi 10:")
    for t, p, f in quali[:10]:
        print(f"     {'FORMA ' if f else 'nudo  '} «{p[:70]}»   ← «{t[:50].replace(chr(10), ' ')}…»")

    lo1, hi1 = wilson(cade_senza, ammessi)
    lo2, hi2 = wilson(cade_con, ammessi)
    print(f"\nT3 · FALSO ALLARME sul campione (seed {SEED})")
    print(f"   senza filtro : {cade_senza}/{ammessi} = {100 * cade_senza / max(1, ammessi):.2f}%"
          f"  [{100 * lo1:.1f} ; {100 * hi1:.1f}]")
    print(f"   col filtro   : {cade_con}/{ammessi} = {100 * cade_con / max(1, ammessi):.2f}%"
          f"  [{100 * lo2:.1f} ; {100 * hi2:.1f}]")
    p3 = 100 * cade_con / max(1, ammessi)
    print(f"   ⇒ T3 (sotto l'1,0%) {'REGGE' if p3 < 1.0 else ('🔴 FALSIFICATA' if p3 >= 1.2 else 'indeciso (fra 1,0 e 1,2)')}")


if __name__ == "__main__":
    main()
