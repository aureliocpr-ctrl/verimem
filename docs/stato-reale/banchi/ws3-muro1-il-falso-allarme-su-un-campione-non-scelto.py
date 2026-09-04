"""LIVELLO: `run_validation_gate` (i layer lessicali L1.x) — dichiarato, e VALIDATO
contro la porta `Memory.add(ground=False)` prima di essere usato.

MURO 1, il banco che decide: quanti fatti VERI la decomposizione atomica
fermerebbe, su un campione NON scelto dal difetto.

    python docs/stato-reale/banchi/ws3-muro1-il-falso-allarme-su-un-campione-non-scelto.py [N]

⚡ COSTO ZERO: nessun modello, nessuno slot, nessuna scrittura. Lo store di
Aurelio e' aperto in SOLA LETTURA (`mode=ro`) per LEGGERE le proposizioni.

━━ PERCHE' NON BASTAVANO LE 15 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sulle 15 di ws7 l'atomico ferma 2 dei 10 che devono restare ammessi. Quel 2/10
NON e' un tasso: quelle dieci sono i fatti che una cura aveva appena liberato —
un campione scelto DAL difetto. Un effetto misurato sui casi di chi conosce il
difetto non e' una frequenza. Qui il campione e' casuale, con seed fisso, fra i
fatti composti che il gate di oggi AMMETTE: quelli che la cura puo' solo rovinare.

━━ IL LIVELLO, dichiarato ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`run_validation_gate` e' il gate senza lo store: esercita i layer lessicali L1.x
ma **non** L3 (che ha bisogno del corpus per trovare la contraddizione). Per il
falso allarme da decomposizione e' il livello giusto — i pezzi cadono su L1.13 /
L1.17 / L1.10 — ma il numero e' un MINIMO: con lo store attaccato puo' solo
salire. Prima di usarlo il banco lo VALIDA sui quattro numeri gia' misurati alla
porta vera (banco ws3-muro1-le-quindici-...): se non coincidono, si ferma.

━━ MISURATO il 04/09 alle 21:20 — n=800, seed fisso ━━━━━━━━━━━━━━━━━━━━━━━━━━
    fatti vivi 15.262 · composti 7.458 · esaminati 1.133 per arrivare a 800
    AMMESSI dal gate intero (i «veri»)      800
    di questi FERMATI dall'atomico           16   **2,0%**   Wilson 95% [1,2% ; 3,2%]
    layer che ferma il pezzo: L1.13 x5 · L1.15 x3 · L1.16 x2 · L1.10 x2 · altri
⇒ Sulle 15 il danno era 2/10 = 20%. Su un campione non scelto e' il **2,0%**: un
  ordine di grandezza meno. Le 15 non potevano dare un tasso — l'intervallo di
  Wilson per 2 su 10 e' [5,7% ; 51%], cioe' non dice niente.
⇒ E il meccanismo che avevo predetto e che sulle 15 NON si era visto, qui c'e':
  «L'ultimo run di ci concluso su main e' un success sullo SHA 397c6375, crea…»
      -> CADE il frammento «Finito alle 22:32.» [L1.13]
  cioe' un completamento nudo fabbricato dallo split. Sulle 15 la mia
  spiegazione era sbagliata; sulla popolazione vera e' quella giusta.

━━ ⚠️ IL CRITERIO E' CIRCOLARE, e il 2,0% e' un LIMITE SUPERIORE ━━━━━━━━━━━━━━
Qui «vero» vuol dire «il gate intero lo ammette»: non e' un'etichetta di verita',
e' il verdetto del sistema che stiamo giudicando. Fra i 16 che cambiano verdetto
ce ne sono di **giustamente** fermati — per esempio «A.0.1 AUDIT 20 SUBCOMMAND
CLP COMPLETO…» e' una self-claim di completamento che oggi passa intera: quello
e' GUADAGNO, non danno. Quindi 2,0% e' quanto cambia, non quanto sbaglia.
Separarli e' una lettura caso per caso, e non deve farla chi ha scritto la tesi
ne' chi ha scritto l'obiezione: i 16 vanno passati a QA o al Product Owner.

━━ COME MUORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se la lettura dei 16 dicesse che sono quasi tutti guadagno, la cura si porta a
casa quasi gratis. Se sono quasi tutti danno, va accompagnata da una guardia (per
esempio: non giudicare un frammento che ha perso il soggetto, non spezzare dentro
le virgolette) prima di entrare nel percorso di scrittura.
"""
from __future__ import annotations

import pathlib
import random
import re
import sqlite3
import sys

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
QUINDICI = ALBERO / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"
SEED = 20260904

# ── lo splitter del lead, copiato VERBATIM dal messaggio 7321c7b118e641a3 ─────
_COORD = re.compile(r"\s*(?:,\s*e\s+|\s+e\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBO_INIZIALE = re.compile(
    r"^(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)\b", re.I)


def claim_atomici(testo: str) -> list[str]:
    try:
        from verimem.subject_extract import subject_of
    except Exception:  # noqa: BLE001
        subject_of = None
    pezzi = [p.strip(" .") for p in _COORD.split(testo) if p and len(p.split()) >= 3]
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


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervallo di Wilson al 95%: una proporzione senza intervallo inganna,
    e su k piccolo il Wald darebbe un estremo negativo."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    mezzo = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, centro - mezzo), min(1.0, centro + mezzo))


def fermato(testo: str) -> tuple[bool, str]:
    g = run_validation_gate(proposition=testo, verified_by=[], topic=None, agent=None)
    strati = ",".join(sorted({str((w or {}).get("layer") or "?")
                              for w in (getattr(g, "warnings", None) or [])})) or "-"
    return getattr(g, "action", "persist") in ("downgrade", "reject"), strati


def valida_il_proxy() -> bool:
    """I quattro numeri gia' misurati ALLA PORTA vera, che il proxy deve riprodurre."""
    import json
    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    atteso = {"tornate_intero": 5, "tornate_atomico": 5,
              "restano_intero": 0, "restano_atomico": 2}
    ott = {}
    for chiave, testi in (("tornate", d["elenco_tornate"]), ("restano", d["elenco_restano"])):
        ott[f"{chiave}_intero"] = sum(fermato(t)[0] for t in testi)
        ott[f"{chiave}_atomico"] = sum(
            any(fermato(p)[0] for p in claim_atomici(t)) for t in testi)
    ok = ott == atteso
    print("VALIDAZIONE DEL PROXY contro la porta `Memory.add(ground=False)`:")
    for k in atteso:
        segno = "ok" if ott[k] == atteso[k] else "🔴 DIVERGE"
        print(f"    {k:18s} porta={atteso[k]}  proxy={ott[k]}   {segno}")
    print(f"  ⇒ {'coincide su 4/4: uso il proxy e lo dichiaro' if ok else 'NON coincide: il banco si ferma'}\n")
    return ok


def main() -> None:
    n_camp = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    print("IMPORT DA", verimem.__file__, "\n")
    if not valida_il_proxy():
        return

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()

    composti = [t for t in righe if len(claim_atomici(t)) >= 2]
    random.Random(SEED).shuffle(composti)

    esaminati = ammessi_interi = fermati_atomico = 0
    quali: list[tuple[str, str, str]] = []
    for t in composti:
        if ammessi_interi >= n_camp:
            break
        esaminati += 1
        if fermato(t)[0]:
            continue  # il gate lo ferma gia' da intero: non e' un vero da proteggere
        ammessi_interi += 1
        caduti = [(p, s) for p in claim_atomici(t) for ok, s in [fermato(p)] if ok]
        if caduti:
            fermati_atomico += 1
            quali.append((t, caduti[0][0], caduti[0][1]))

    print(f"CAMPIONE CASUALE (seed {SEED}) fra i fatti COMPOSTI del corpus vivo")
    print(f"  fatti vivi                          : {len(righe)}")
    print(f"  di cui composti (>= 2 unita')       : {len(composti)}")
    print(f"  esaminati per arrivare al campione  : {esaminati}")
    print(f"  AMMESSI dal gate intero (i «veri»)  : {ammessi_interi}")
    lo, hi = wilson(fermati_atomico, ammessi_interi)
    print(f"  di questi, FERMATI dall'atomico     : {fermati_atomico}"
          f"  ({100 * fermati_atomico / max(1, ammessi_interi):.1f}%)  <- FALSO ALLARME")
    print(f"  intervallo di Wilson al 95%         : [{100 * lo:.1f}% , {100 * hi:.1f}%]")

    print("\n  QUALI cadono (i primi 12, col pezzo che cade e il layer):")
    for t, p, s in quali[:12]:
        print(f"   · «{t[:74].replace(chr(10), ' ')}…»")
        print(f"     └─ CADE: «{p[:74]}…»  [{s}]")

    strati: dict[str, int] = {}
    for _, _, s in quali:
        strati[s] = strati.get(s, 0) + 1
    print("\n  per LAYER che ferma il pezzo:")
    for s, k in sorted(strati.items(), key=lambda x: -x[1]):
        print(f"    {k:4d}  {s}")
    print("\n  ⚠️ MINIMO: il proxy non esercita L3 (serve il corpus). Con lo store"
          " attaccato il numero puo' solo salire.")


if __name__ == "__main__":
    main()
