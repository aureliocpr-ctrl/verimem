"""W2-27 quater · La stessa matrice, riletta con la chiave GIUSTA.

I miei tre banchi W2-27 leggevano ``ricevuta["warnings"]`` **anche sulla porta
MCP**, che quella chiave **non ce l'ha**: espone ``anti_confab_warnings``. La
colonna MCP degli strati era dunque **vuota per costruzione**, e ci ho
costruito sopra un racconto pubblicato (`621d9ab3`, poi ritirato in `5b70f035`).

Questo banco fa due cose, e la prima serve alla seconda:

**① CONTROLLI SUL LETTORE** — prima di rifidarmi di una misura devo provare che
lo strumento **vede** e che **si rompe** quando non vede:

    a) una ricevuta senza chiavi note  -> DEVE alzare (se torna [] e' inutile)
    b) una ricevuta SDK reale          -> deve trovare la chiave `warnings`
    c) una ricevuta MCP reale          -> deve trovare `anti_confab_warnings`

Se (a) non alza, il lettore ha lo stesso difetto di quello che sostituisce e il
banco **non puo' concludere**.

**② LA MATRICE RILETTA** — la predizione, scritta prima di eseguire: la
divergenza di **verdetto** regge (l'ho gia' vista da due letture indipendenti),
ma la colonna **strati** di MCP **non sara' piu' vuota** — e in particolare il
caso A mostrera' `L1.19`, cioe' la prova fabbricata **non sopprime niente** su
MCP. Se invece la colonna MCP restasse vuota **anche con la chiave giusta**,
allora il mio racconto di `5b70f035` sarebbe sbagliato a sua volta.

REGIME: un processo, store temporaneo, handler MCP in-process con il suo agente
vero. Lo store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-W2-27-quater-la-matrice-riletta-con-la-chiave-giusta.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ricevuta import (  # noqa: E402
    RicevutaIlleggibile,
    quarantinata,
    spiega,
    strati,
)

CLAIM = "La latenza e' 40 ms."
BENCH_FABBRICATO = "bench:non_esiste_2026"
FILE_VERO = "file:verimem/quantity_match.py:1050"

CASI = [
    ("ctrl nessuna prova  ", None),
    ("A bench FABBRICATO  ", [BENCH_FABBRICATO]),
    ("B fabbricato + reale", [BENCH_FABBRICATO, FILE_VERO]),
]


def _mcp(vb, topic: str) -> dict:
    from verimem import mcp_server  # noqa: PLC0415

    args = {"proposition": CLAIM, "topic": topic}
    if vb:
        args["verified_by"] = vb
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    return json.loads("\n".join(getattr(c, "text", "") for c in out))


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    print(f"  claim: «{CLAIM}»")
    mem = Memory(str(tmp / "quater.db"))

    # ── ① I CONTROLLI SUL LETTORE ────────────────────────────────────────
    print("\n  [1] CONTROLLI SUL LETTORE (deve VEDERE e deve ROMPERSI)")
    try:
        strati({"status": "model_claim", "id": "x"}, dove="finta")
        print("      (a) ricevuta senza chiavi note -> NON HA ALZATO")
        print("      CONTROLLO CADUTO: il lettore ha lo stesso difetto di")
        print("      quello che sostituisce. NESSUN VERDETTO.")
        return 1
    except RicevutaIlleggibile as e:
        print(f"      (a) senza chiavi note -> ALZA, e dice quali ha visto: "
              f"{str(e)[:78]}…")

    r_sdk = mem.add(CLAIM, topic="quater/ctrl-sdk", validate="full")
    r_mcp = _mcp(None, "quater/ctrl-mcp")
    print(f"      (b) {spiega(r_sdk, dove='SDK')}")
    print(f"      (c) {spiega(r_mcp, dove='MCP')}")
    if not [k for k in ("warnings",) if k in r_sdk]:
        print("      CONTROLLO CADUTO: la ricevuta SDK non ha `warnings`.")
        return 1
    if "anti_confab_warnings" not in r_mcp:
        print("      CONTROLLO CADUTO: la ricevuta MCP non ha")
        print("      `anti_confab_warnings` ⇒ la mia diagnosi era sbagliata.")
        return 1

    # ── ② LA MATRICE ─────────────────────────────────────────────────────
    print(f"\n  {'caso':<21} {'SDK':<26} {'MCP':<26} {'div?'}")
    print("  " + "-" * 80)
    div = 0
    mcp_strati_visti = 0
    for i, (et, vb) in enumerate(CASI):
        kw = {"verified_by": vb} if vb else {}
        s = mem.add(CLAIM, topic=f"quater/sdk/{i}", validate="full", **kw)
        m = _mcp(vb, f"quater/mcp/{i}")
        s_q, s_l = quarantinata(s, dove="SDK"), strati(s, dove="SDK")
        m_q, m_l = quarantinata(m, dove="MCP"), strati(m, dove="MCP")
        mcp_strati_visti += len(m_l)
        if s_q != m_q:
            div += 1

        def _f(q, ls):
            return f"{'ferma' if q else 'ENTRA'} {','.join(ls) if ls else '-'}"
        print(f"  {et:<21} {_f(s_q, s_l):<26} {_f(m_q, m_l):<26} "
              f"{'SI' if s_q != m_q else 'no'}")

    print("\n  ══ VERDETTO ══")
    print(f"     celle divergenti .......... {div}")
    print(f"     strati letti su MCP ....... {mcp_strati_visti}"
          f"   (con la chiave sbagliata erano SEMPRE 0)")
    if mcp_strati_visti == 0:
        print("     PREDIZIONE FALSIFICATA: la colonna MCP e' vuota ANCHE con la")
        print("     chiave giusta ⇒ il racconto di 5b70f035 e' sbagliato a sua")
        print("     volta, e la chiave non era la causa.")
    else:
        print("     PREDIZIONE RETTA: gli strati su MCP c'erano, e il mio banco")
        print("     non poteva vederli. La divergenza di VERDETTO regge; la")
        print("     colonna 'strati' dei tre banchi W2-27 era vuota PER")
        print("     COSTRUZIONE, non per misura.")

    print("\n  ⚠️ LIMITI: tre combinazioni, un claim, italiano, nessuna fonte;")
    print("     handler MCP in-process (un client vero passa dallo stdio).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
