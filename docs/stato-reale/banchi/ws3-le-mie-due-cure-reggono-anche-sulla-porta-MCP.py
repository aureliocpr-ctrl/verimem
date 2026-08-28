"""Le mie due cure all'estrattore reggono anche sulla porta MCP, o solo su SDK?

@ws2 ha trovato **quattro volte in una notte** la stessa classe::

    «IL PRESIDIO ESISTE, E' ACCESO, E GUARDA UNA PORTA SOLA ⇒ verde per
     costruzione. Su quale PORTA gira il tuo presidio, e su quale POPOLAZIONE?»

**Applicata a me la domanda brucia**: le mie due cure di stasera — i **numeri
d'articolo** (`29ab5544`) e l'**anno di una data inglese** (`ad0cad4f`) — le ho
misurate **alla porta SDK**, e i loro presidi (`tests/…`) chiamano
`extract_quantities` **direttamente**, senza passare da nessuna porta.
**Nessuna delle due è mai stata verificata su MCP**, che è **la porta che usano
gli agenti** — la nostra.

⚠️ E non è una preoccupazione teorica: @ws2 ha misurato che **`repo_root` è
passato al gate SOLO da MCP e mai dall'SDK** (`mcp_server.py:12887`), quindi
`EVIDENCE-EXISTENCE` (`anti_confab_gate.py:1945`) è **attivo su una porta e
spento sull'altra**. Due porte con difese diverse possono dare due verdetti
diversi sullo stesso claim.

LA DOMANDA: gli stessi casi che l'SDK ora ferma, li ferma anche MCP?

LA PREDIZIONE, scritta prima di eseguire: **stessi verdetti su entrambe le
porte** — le cure sono nell'estrattore, che sta **sotto** entrambe. Se
divergono, la cura è verde su una porta e la promessa vale a metà.

CONDIZIONE DI FALSIFICAZIONE: qualunque caso con esito diverso fra le due porte
**rompe la predizione**, e va detto anche se la differenza è «MCP è più
severo»: una cura che vale su una porta sola non è la cura che ho annunciato.

CONTROLLI CHE DEVONO POTER FALLIRE:
  (a) i claim VERI devono passare su ENTRAMBE le porte;
  (b) i casi «scoperti» (cifra estranea) devono essere fermati su ENTRAMBE —
      se MCP non fermasse nemmeno quelli, starei misurando una porta rotta e
      non una divergenza.

REGIME: un processo, store temporaneo vuoto, handler MCP chiamato IN-PROCESS
(niente stdio), SDK nello stesso processo. Le due porte vedono lo STESSO store.

    python docs/stato-reale/banchi/ws3-le-mie-due-cure-reggono-anche-sulla-porta-MCP.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale. Art. 6 - Il termine e' fissato. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
FONTE_EN = (
    "The delivery deadline is March 12, 2027. "
    "The late-delivery penalty is 2% of the contract value per week. "
    "The contract value is 148000 euro."
)

#: (etichetta, claim, fonte, deve essere FERMATO?)
CASI = [
    ("art.3 coperto  ", "Il numero di rate previste dal contratto e' 3.",
     CONTRATTO, True),
    ("art.6 coperto  ", "Il numero di rate previste dal contratto e' 6.",
     CONTRATTO, True),
    ("scoperto 91    ", "Il numero di rate previste dal contratto e' 91.",
     CONTRATTO, True),
    ("anno 2027      ", "The contract covers 2027 units of product.",
     FONTE_EN, True),
    ("scoperto 3129  ", "The contract covers 3129 units of product.",
     FONTE_EN, True),
    ("VERO euro      ", "L'importo contrattuale e' di 148000 euro.",
     CONTRATTO, False),
    ("VERO en        ", "The contract value is 148000 euro.",
     FONTE_EN, False),
]


def _quarantinato_sdk(mem, claim: str, fonte: str, topic: str) -> tuple[bool, float]:
    r = mem.add(claim, topic=topic, source=fonte, validate="full")
    return (str(r.get("status")) == "quarantined",
            float(r.get("grounding_score") or -1))


def _quarantinato_mcp(claim: str, fonte: str, topic: str) -> tuple[bool, float]:
    from verimem import mcp_server  # noqa: PLC0415

    out = asyncio.run(mcp_server._call_tool_impl(
        "hippo_remember",
        {"proposition": claim, "topic": topic, "source": fonte},
    ))
    testo = "\n".join(getattr(c, "text", "") for c in out)
    try:
        d = json.loads(testo)
    except Exception:                     # noqa: BLE001 — ricevuta non-JSON
        low = testo.lower()
        return ("quarantin" in low, -1.0)
    st = str(d.get("status", ""))
    g = d.get("grounding_score")
    return (st == "quarantined", float(g) if g is not None else -1.0)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)      # PRIMA di importare il server
    from verimem.client import Memory  # noqa: PLC0415

    print("  REGIME, dichiarato E misurato:")
    print(f"    PYTHONUTF8={os.environ.get('PYTHONUTF8', '<assente>')} "
          f"utf8mode={int(sys.flags.utf8_mode)} · python {sys.version.split()[0]}")
    print(f"    HIPPO_DATA_DIR={tmp}   (temporaneo: lo store di Aurelio NON e' toccato)")
    print("    handler MCP chiamato IN-PROCESS, niente stdio · SDK stesso processo")

    mem = Memory(str(tmp / "porte.db"))

    print(f"\n  {'caso':<17} {'atteso':<9} {'SDK':<18} {'MCP':<18} {'concordi?'}")
    print("  " + "-" * 74)
    divergenti = []
    veri_caduti = []
    for i, (et, claim, fonte, deve_fermare) in enumerate(CASI):
        s_q, s_g = _quarantinato_sdk(mem, claim, fonte, f"porte/sdk/{i}")
        m_q, m_g = _quarantinato_mcp(claim, fonte, f"porte/mcp/{i}")
        concordi = s_q == m_q
        if not concordi:
            divergenti.append((et, s_q, m_q))
        if not deve_fermare and (s_q or m_q):
            veri_caduti.append((et, s_q, m_q))
        def _f(q: bool, g: float) -> str:
            return f"{'ferma' if q else 'ENTRA'} {g:7.1f}"
        print(f"  {et:<17} {'ferma' if deve_fermare else 'ENTRA':<9} "
              f"{_f(s_q, s_g):<18} {_f(m_q, m_g):<18} "
              f"{'si' if concordi else 'NO'}")

    print(f"\n  CONTROLLO (a): claim VERI passati su entrambe: "
          f"{2 - len(veri_caduti)}/2")
    if veri_caduti:
        print(f"     CONTROLLO CADUTO: un VERO e' fermato ({veri_caduti}) ⇒ misuro")
        print("     un gate rotto, non una divergenza fra porte. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if divergenti:
        print(f"     PREDIZIONE FALSIFICATA: {len(divergenti)} casi con esito DIVERSO")
        print("     fra le due porte ⇒ le mie cure valgono su una porta sola, e la")
        print("     promessa che ho annunciato vale a meta'.")
        for et, s_q, m_q in divergenti:
            print(f"        {et}  SDK={'ferma' if s_q else 'ENTRA'}  "
                  f"MCP={'ferma' if m_q else 'ENTRA'}")
    else:
        print("     PREDIZIONE RETTA: stessi verdetti su entrambe le porte. Le cure")
        print("     stanno nell'ESTRATTORE, che e' sotto tutte e due, e la classe di")
        print("     @ws2 — «il presidio guarda una porta sola» — qui non scatta.")
        print("     ⚠️ Ma i miei PRESIDI restano sotto-porta: chiamano")
        print("       extract_quantities direttamente. Questo banco e' la verifica")
        print("       alla porta che ai test mancava.")

    print("\n  ⚠️ LIMITI: sette casi, due fonti, IT+EN. L'handler MCP e' chiamato")
    print("     in-process: un client vero passa dallo stdio e da un altro env.")
    print("     E la ricevuta MCP e' stata cambiata stanotte da @ws2 (c539ab18,")
    print("     8aa47068, 1cb62c35): questo banco la legge DOPO quelle modifiche.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
