"""LIVELLO: la porta di scrittura `Memory.add(..., ground=False)` — nessun modello.

MURO 1, parte gratuita: la decomposizione atomica del lead applicata alle QUINDICI
proposizioni di ws7. Non misura il guadagno: misura il DANNO COLLATERALE.

    python docs/stato-reale/banchi/ws3-muro1-le-quindici-sotto-decomposizione-atomica.py

⚡ COSTO ZERO: `ground=False`, nessun giudice, nessuno slot, store temporaneo
(⛔ lo store di Aurelio non viene mai aperto, ne' in lettura ne' in scrittura).

━━ PERCHE' QUESTO BANCO NON PUO' DIRE «L'ATOMICO E' MEGLIO» ━━━━━━━━━━━━━━━━━━━
Le 15 sono la popolazione che la cura di ws7 ha gia' sistemato: 5 sono TORNATE
FERMATE e 10 RESTANO AMMESSE. Su una popolazione gia' a posto il gate intero e'
vicino alla saturazione, e un banco saturo decide un'ALTRA domanda (⑫). Quella
che decide e' quindi:

    la decomposizione ROMPE cio' che e' gia' a posto?

E' la domanda che conviene fare per prima perche' e' l'unica che puo'
FALSIFICARE la tesi senza costare niente: se l'atomico ferma dei veri qui, il
guadagno che si misurera' sui 60+60 andra' pagato a quel prezzo.

━━ PREDIZIONE DEPOSITATA PRIMA (402605cc10e18db6, msg del 04/09) ━━━━━━━━━━━━━━
    P6-① sui 5 che DEVONO essere fermati: l'atomico ne ferma >= 4.
    P6-② sui 10 che DEVONO restare ammessi: l'atomico ne ferma ALMENO 2.
         E' la predizione CONTRO la tesi del lead. Muore se ne ferma 0 o 1.
    (P6-③, il costo, si misura nel banco dei 60+60 dentro un impianto solo.)

Il meccanismo che predico, per nome: le composte descrittive perdono l'evidenza
nello split e il pezzo separato assume la forma esatta di cio' che L1.13 ferma —
    «Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.»
      -> «Il comando warmup e' finito alle 14:53:19.»   (un completamento nudo)
Il MIN sui claim ferma se cade un pezzo solo, quindi basta UN frammento cosi'.

━━ LETTERATURA, letta PRIMA (URL completi in docs/ricerca/2026-09-04-...md) ━━━
· FActScore (2305.14251) decompone in fatti atomici auto-contenuti: e' da li'
  che viene l'eredita' del soggetto nello splitter del lead.
· Molecular Facts (2406.20079) dice che «fully atomic facts are not the right
  representation» e propone due desiderata in tensione: DECONTESTUALITA' (il
  pezzo sta in piedi da solo) e MINIMALITA' (quanto poco si aggiunge).
· DnDScore (2412.13175) misura quella tensione: il **19,11%** dei giudizi cambia
  fra la forma decomposta e quella decontestualizzata, e la loro Fig. 5 mostra
  un FALSO POSITIVO nato dal contesto AGGIUNTO sbagliato.
· VeriScore (2406.19276): sull'estrazione di SAFE trova over-decomposition e
  claim non verificabili; la cura e' estrarre solo i claim VERIFICABILI, non
  tutti gli atomici.
⇒ Concatenazione, ed e' la ragione per cui il banco esiste: quella letteratura
  misura la decomposizione su verifica CONTRO UNA FONTE. Qui la fonte non c'e'
  (`ground=False`): il gate e' un rilevatore lessicale di self-claim. Un pezzo
  che perde il contesto non diventa «non verificabile», diventa **una self-claim
  che nel testo originale non c'era**. E' un modo di sbagliare che i lavori
  citati non possono osservare, perche' nei loro impianti c'e' sempre una fonte.

━━ COME MUORE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se l'atomico ferma 0 o 1 dei 10 veri, la mia obiezione cade e la tesi del lead
e' piu' forte di quanto pensassi. Se il gate INTERO non ferma 5/5 sui tornati,
il controllo positivo e' spento e il banco non decide niente: si legge lo SHA.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

# ── l'albero da cui importare: quello CONDIVISO, su main, non il worktree ──────
ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402

QUINDICI = ALBERO / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"

# ── lo splitter del lead, COPIATO VERBATIM dal messaggio 7321c7b118e641a3 ──────
# Copiato e non riscritto: se lo riscrivessi misurerei il mio splitter, non il suo.
_COORD = re.compile(r"\s*(?:,\s*e\s+|\s+e\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBO_INIZIALE = re.compile(
    r"^(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)\b", re.I)


def claim_atomici(testo: str) -> list[str]:
    """Split sulle coordinate, con eredita' del soggetto (FActScore)."""
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


def strati(r: dict) -> str:
    """I layer che si sono accesi, per poter guardare QUALI e non solo quanti."""
    w = r.get("warnings") or []
    return ",".join(sorted({str((x or {}).get("layer") or "?") for x in w})) or "-"


def main() -> None:
    print("IMPORT DA", verimem.__file__)
    for c in (["git", "log", "-1", "--format=%h %ad %an", "--date=short"],
              ["git", "status", "--short"], ["git", "rev-parse", "--abbrev-ref", "HEAD"]):
        out = subprocess.run(c, cwd=ALBERO, capture_output=True, text=True).stdout.strip()
        print(f"  {' '.join(c[1:3]):18s} {out[:110] or '(pulito)'}")

    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    popolazioni = [("TORNATE (devono essere FERMATE)", d["elenco_tornate"], "fermare"),
                   ("RESTANO  (devono restare AMMESSE)", d["elenco_restano"], "ammettere")]

    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "atomico.db")
    riepilogo: dict[str, tuple[int, int, int]] = {}
    for titolo, testi, atteso in popolazioni:
        print(f"\n{'=' * 78}\n{titolo}   —   n={len(testi)}\n{'=' * 78}")
        f_int = f_atm = 0
        for i, t in enumerate(testi):
            r = m.add(t, ground=False)
            v_int = r.get("status") == "quarantined"
            parti = claim_atomici(t)
            caduti = []
            for p in parti:
                rp = m.add(p, ground=False)
                if rp.get("status") == "quarantined":
                    caduti.append((p, strati(rp)))
            v_atm = bool(caduti)
            f_int += v_int
            f_atm += v_atm
            segno = "  " if v_int == v_atm else ("🔴" if atteso == "ammettere" else "🟢")
            print(f"{segno} [{i}] intero={'FERMATO' if v_int else 'passa':7s} ({strati(r)})"
                  f" | atomico={'FERMATO' if v_atm else 'passa':7s}  pezzi={len(parti)}")
            print(f"      «{t[:96].replace(chr(10), ' ')}…»")
            for p, s in caduti[:3]:
                print(f"      └─ CADE: «{p[:80]}…»  [{s}]")
        riepilogo[titolo] = (f_int, f_atm, len(testi))

    print(f"\n{'=' * 78}\nRIEPILOGO\n{'=' * 78}")
    for titolo, (fi, fa, n) in riepilogo.items():
        print(f"  {titolo:36s} fermati: intero {fi}/{n} · atomico {fa}/{n}")

    ft_i, ft_a, _ = riepilogo["TORNATE (devono essere FERMATE)"]
    fr_i, fr_a, _ = riepilogo["RESTANO  (devono restare AMMESSE)"]
    print("\nVERDETTO SULLE PREDIZIONI DEPOSITATE (402605cc10e18db6):")
    print(f"  P6-① atomico ferma >= 4 dei 5 tornati            : {ft_a}/5  ->"
          f" {'REGGE' if ft_a >= 4 else '🔴 FALSIFICATA'}")
    print(f"  P6-② atomico ferma >= 2 dei 10 che devono restare : {fr_a}/10 ->"
          f" {'REGGE (danno collaterale reale)' if fr_a >= 2 else '🔴 FALSIFICATA: la mia obiezione cade'}")
    print(f"\n  CONTROLLO POSITIVO (il gate intero ferma i 5 tornati): {ft_i}/5"
          f" {'ok' if ft_i == 5 else '⚠️  SPENTO: il banco non decide, guarda lo SHA'}")
    print(f"  CONTROLLO (il gate intero ammette i 10)             : {10 - fr_i}/10"
          f" {'ok' if fr_i == 0 else '⚠️  la popolazione non coincide con quella di ws7'}")


if __name__ == "__main__":
    main()
