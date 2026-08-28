"""W2-27 ter · La divergenza di VERDETTO fra le due porte, con la forma giusta.

Terzo giro, e la forma del claim l'ho **letta** invece di tentarla — è ciò che
mi è costato i due giri precedenti.

`l1_quantitative_detector.py:1-22` dichiara cosa prende **`L1.19`**: claim
**metrici assoluti** («*Latenza 50ms*», «*Coverage al 95%*», «*N records*»), e
quali prove lo **sopprimono**: `bench: measure: coverage: report: query: log:
profiler:`.

⇒ La forma che serve alla condizione di `anti_confab_gate.py:1960`
(`repo_root is not None AND not warnings AND verified_by is not None`) è:
**un claim metrico assoluto** — `L1.19` fira **senza** prove — **con una prova
`bench:` FABBRICATA**, che lo sopprime lasciando **zero warning**. A quel punto
`EVIDENCE-EXISTENCE` guarda se il riferimento **esiste**, e su MCP (che porta
`repo_root`) deve fermarlo.

⚠️ E il claim NON deve toccare i rilevatori di hype: «*Il fix funziona ed è
verificato*» faceva scattare `L1.10`/`L1.15` **anche con** la prova, quindi
`not warnings` era falsa e la cura restava inerte. **«La latenza è 40 ms» non
contiene nessuna parola di successo.**

I DUE REGIMI, misurati e non assunti (`02378996`):
    MCP   `_ag()` -> VerimemAgent -> semantic.repo_root = <radice del repo>
    SDK   `Memory()` di default   -> repo_root = None

LA PREDIZIONE, scritta prima di eseguire:
    ctrl (nessuna prova)      -> FERMATO su entrambe, con `L1.19`
    A    (bench: fabbricato)  -> **MCP ferma** (evidence_existence) · **SDK ENTRA**
    B    (bench: + file vero) -> ENTRA su entrambe
⇒ **A è la cella che deve divergere.**

CONDIZIONE DI FALSIFICAZIONE: se **A non diverge**, o la cura non ha effetto sul
verdetto, oppure il mio regime è ancora sbagliato — e il banco lo distingue
stampando `repo_root` **e il `type()`** di ciò che legge (nel giro precedente
leggevo `.semantic` su una **funzione** e il `None` non voleva dire niente).

CONTROLLO CHE DEVE POTER FALLIRE: `ctrl` deve essere fermato **con `L1.19`** su
entrambe. Se `L1.19` non compare, il claim non è quello che credo e il banco è
inerte come i due precedenti.

REGIME: un processo, store temporaneo per l'SDK, handler MCP in-process con il
suo agente **vero**. Lo store di Aurelio NON è toccato.

    python docs/stato-reale/banchi/ws3-W2-27-ter-la-divergenza-fra-le-due-porte.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

#: metrico ASSOLUTO: `L1.19` lo prende SENZA prove, e nessuna parola di hype
# ⚠️ FORMA ESATTA, trovata INTERROGANDO il rilevatore invece di indovinarla:
#   «La latenza e' 40 ms.»                    -> L1.19 absolute_latency
#   «La latenza MEDIA DI SCRITTURA e' 40 ms.» -> NIENTE
# Le parole in mezzo rompono il pattern. Era il mio claim ad avere tre
# parole di troppo, ed e' la quarta volta su questo fronte che la forma
# del claim mi costa un giro: la quarta l'ho chiesta al codice.
CLAIM = "La latenza e' 40 ms."
BENCH_FABBRICATO = "bench:non_esiste_2026"
FILE_VERO = "file:verimem/quantity_match.py:1050"

CASI = [
    ("ctrl nessuna prova  ", None),
    ("A bench FABBRICATO  ", [BENCH_FABBRICATO]),
    ("B fabbricato + reale", [BENCH_FABBRICATO, FILE_VERO]),
]


def _lay(d) -> list[str]:
    return [str(w.get("layer")) for w in (d.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


def _sdk(mem, vb, topic):
    kw = {"verified_by": vb} if vb else {}
    r = mem.add(CLAIM, topic=topic, validate="full", **kw)
    return str(r.get("status")) == "quarantined", _lay(r)


def _mcp(vb, topic):
    from verimem import mcp_server  # noqa: PLC0415

    args = {"proposition": CLAIM, "topic": topic}
    if vb:
        args["verified_by"] = vb
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    testo = "\n".join(getattr(c, "text", "") for c in out)
    try:
        d = json.loads(testo)
    except Exception:  # noqa: BLE001
        return ("quarantin" in testo.lower(), [])
    return str(d.get("status")) == "quarantined", _lay(d)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)}")
    print(f"    HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"    claim: «{CLAIM}»")

    mem = Memory(str(tmp / "ter.db"))
    rr_sdk = getattr(getattr(mem, "semantic", None), "repo_root", None)
    # ⚠️ SI CHIAMA L'ACCESSORE E SI STAMPA IL `type()`: nel giro precedente
    # leggevo `.semantic` su `mcp_server._ag`, che e' una FUNZIONE, e il `None`
    # che ne usciva non diceva niente su `repo_root`.
    from verimem import mcp_server  # noqa: PLC0415
    ag = mcp_server._ag()
    sem = getattr(ag, "semantic", None)
    rr_mcp = getattr(sem, "repo_root", None)
    print("\n  [0] I DUE REGIMI (con il type di cio' che leggo)")
    print(f"      SDK  Memory().semantic   {type(getattr(mem, 'semantic', None)).__name__:<18}"
          f" repo_root={rr_sdk!r}")
    print(f"      MCP  _ag().semantic      {type(sem).__name__:<18}"
          f" repo_root={rr_mcp!r}")
    if rr_mcp is None:
        print("      CONTROLLO CADUTO: MCP non porta repo_root ⇒ le due porte NON")
        print("      sono in regimi diversi e il banco non puo' concludere.")
        return 1
    if rr_sdk == rr_mcp:
        print("      CONTROLLO CADUTO: i due regimi COINCIDONO. NESSUN VERDETTO.")
        return 1

    print(f"\n  {'caso':<21} {'SDK':<28} {'MCP':<28} {'div?'}")
    print("  " + "-" * 84)
    esiti = {}
    div = []
    for i, (et, vb) in enumerate(CASI):
        s_q, s_l = _sdk(mem, vb, f"ter/sdk/{i}")
        m_q, m_l = _mcp(vb, f"ter/mcp/{i}")
        esiti[et.strip()] = (s_q, s_l, m_q, m_l)
        if s_q != m_q:
            div.append((et, s_q, m_q, s_l, m_l))
        def _f(q, ls):
            return f"{'ferma' if q else 'ENTRA'} {','.join(ls) if ls else '-'}"
        print(f"  {et:<21} {_f(s_q, s_l):<28} {_f(m_q, m_l):<28} "
              f"{'SI' if s_q != m_q else 'no'}")

    c_q, c_l, cm_q, cm_l = esiti["ctrl nessuna prova"]
    ha_l119 = any("L1.19" in x for x in c_l) or any("L1.19" in x for x in cm_l)
    print(f"\n  CONTROLLO: `ctrl` fermato con L1.19? "
          f"SDK={c_q} {c_l}  MCP={cm_q} {cm_l}  ->  L1.19 presente: {ha_l119}")
    if not ha_l119:
        print("     CONTROLLO CADUTO: L1.19 non compare ⇒ il claim non e' quello")
        print("     che credo e il banco e' inerte come i due precedenti.")
        print("     NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if div:
        print(f"     PREDIZIONE RETTA: {len(div)} cella/e DIVERGONO ⇒ W2-27 non e'")
        print("     una differenza di configurazione: CAMBIA IL VERDETTO. Lo stesso")
        print("     claim con la stessa prova FABBRICATA e' fermato da una porta e")
        print("     ammesso dall'altra.")
        for et, s_q, m_q, s_l, m_l in div:
            print(f"        {et}  SDK={'ferma' if s_q else 'ENTRA'} [{','.join(s_l)}]"
                  f"   MCP={'ferma' if m_q else 'ENTRA'} [{','.join(m_l)}]")
        print("     ⇒ un agente che scrive da MCP e' protetto da un riferimento")
        print("       fabbricato; lo stesso agente che scrive dall'SDK NO.")
    else:
        print("     PREDIZIONE FALSIFICATA: i due regimi sono diversi (controllo [0])")
        print("     e L1.19 e' ingaggiato (controllo ctrl), eppure nessuna cella")
        print("     diverge ⇒ `repo_root` e' ATTIVO ma NON DECISIVO sul verdetto.")
        print("     W2-27 va requalificato, e questa volta il nullo E' leggibile.")

    print("\n  ⚠️ LIMITI: tre combinazioni, un claim solo, italiano, nessuna fonte.")
    print("     L'handler MCP e' in-process: un client vero passa dallo stdio.")
    print("     Il file usato come prova vera deve esistere nel repo corrente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
