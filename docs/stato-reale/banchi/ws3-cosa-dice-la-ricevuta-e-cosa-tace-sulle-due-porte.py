"""Censimento: quali campi la ricevuta espone, su quale porta, con quale nome.

Ieri notte ho letto `warnings` su una ricevuta **MCP**, che quella chiave **non
ce l'ha** — espone `anti_confab_warnings`. Il mio lettore tornava `[]`, io ci ho
letto sopra «zero strati», e ci ho costruito un reperto che ho poi **pubblicato
e ritirato** (`621d9ab3` → `5b70f035`). **Io me ne sono accorto in quindici
minuti perche' avevo un controllo positivo. Un integratore lo paga in silenzio.**

Quel giorno ho guardato **un caso solo**. Un campo puo' comparire **solo in
certi esiti** — `quarantined_by` esiste solo se qualcosa quarantina, `advice`
solo se il gate ha qualcosa da consigliare — quindi una matrice costruita su un
caso e' una matrice **incompleta per costruzione**, ed e' esattamente l'errore
che mi ha fatto ritirare cinque verdetti in cinque ore.

**SEI CASI**, scelti per attraversare esiti diversi del gate:

    1 nudo                claim neutro, nessuna fonte, nessuna prova
    2 autoclaim           «il fix funziona ed e' verificato» -> L1 senza prove
    3 fonte che SUPPORTA  il moat gira e dovrebbe ammettere
    4 fonte che NEGA      il moat gira e dovrebbe fermare
    5 bench FABBRICATO    prova ben formata che non esiste
    6 file REALE          prova che esiste davvero nel repo

⚠️ Questo banco **NON ha una predizione da falsificare**: e' **descrittivo**.
Non dice se il gate sbagli — dice **cosa racconta di se stesso** e **a chi**. Il
controllo che deve poter fallire e' un altro: **le due porte devono produrre
almeno un esito diverso fra loro**; se dessero sempre lo stesso identico
risultato, la matrice non distinguerebbe «campo assente su quella porta» da
«caso mai raggiunto».

🔴 **ESITO — 19 campi distinti su 6 casi, e il censimento CORREGGE una cosa
che avevo detto io ieri.**

    SOLO SDK (3)     advice · stored · warnings                    6/6 casi
    SOLO MCP (10)    anti_confab_warnings · confidence · deferred ·
                     gate_knobs_denied · ok · proposition · replaced ·
                     source_signature · topic · verified_by        6/6 casi
    ENTRAMBE (6)     adjudication · grounding_score · id · moat ·
                     status  (6/6)  ·  quarantined_by (SDK 3/6, MCP 4/6)

**LE DUE DIFFERENZE CHE PESANO:**
① **`warnings` (SDK) e `anti_confab_warnings` (MCP) sono lo STESSO contenuto
   sotto DUE NOMI, su 6 casi su 6.** Non e' un caso limite: e' la regola. Chi
   scrive **un** lettore per **due** porte prende `[]` e non se ne accorge.
② **`advice` esiste solo sull'SDK, in 6 casi su 6.** Il consiglio che il gate
   formula — «*verified_by ben formato ma NESSUN ref esiste nel repo: fornisci
   un `commit:`/`file:` reale*» — **non raggiunge mai un chiamante MCP**, che
   quindi sa di essere stato fermato ma non cosa fare.

✅ **CORREZIONE DI UNA MIA AFFERMAZIONE DI IERI.** Sul canale avevo scritto:
«*`quarantined_by` c'e' SOLO su MCP*». **E' falso.** Sta su **entrambe**, e
compare esattamente quando c'e' una quarantena: SDK 3/6 (casi 2, 4, 6), MCP 4/6
(gli stessi piu' il 5, dove solo MCP ferma). Ieri lo vedevo «solo MCP» perche'
il mio unico caso era **proprio** quello in cui l'SDK non quarantinava.
🔑 **Un campo che compare solo in certi esiti, misurato su un caso solo,
produce una matrice sbagliata senza che si veda** — la stessa forma dell'errore
che ieri mi e' costato cinque ritiri.

⚠️ **E NON GONFIO IL «10 CONTRO 3»**: dei dieci campi solo-MCP, **quattro sono
echi dell'input** (`proposition`, `topic`, `verified_by`, `source_signature`) e
tre sono di servizio (`ok`, `replaced`, `deferred`). **Non sono informazione in
piu' sul verdetto.** Il conteggio grezzo direbbe «MCP informa tre volte
meglio»: e' un titolo gonfiato, e il dato vero e' che **ogni porta tace qualcosa
che l'altra dice**.

REGIME: store TEMPORANEO, handler MCP in-process con il suo agente vero. Lo
store di Aurelio NON e' toccato.

    python docs/stato-reale/banchi/ws3-cosa-dice-la-ricevuta-e-cosa-tace-sulle-due-porte.py
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

FONTE_SUPPORTA = (
    "Il rapporto trimestrale indica che la penale per il ritardo e' fissata "
    "in 500 euro al giorno e che il termine di consegna e' di 30 giorni."
)
FONTE_NEGA = (
    "Il rapporto trimestrale indica che la penale per il ritardo e' fissata "
    "in 120 euro al giorno e che il termine di consegna e' di 90 giorni."
)

#: (etichetta, proposition, source, verified_by)
CASI: list[tuple[str, str, str | None, list[str] | None]] = [
    ("1 nudo              ", "Il deposito si trova a Bologna.", None, None),
    ("2 autoclaim         ", "Il fix funziona ed e' verificato.", None, None),
    ("3 fonte SUPPORTA    ", "La penale e' di 500 euro al giorno.",
     FONTE_SUPPORTA, None),
    ("4 fonte NEGA        ", "La penale e' di 500 euro al giorno.",
     FONTE_NEGA, None),
    ("5 bench FABBRICATO  ", "La latenza e' 40 ms.", None,
     ["bench:non_esiste_2026"]),
    ("6 file REALE        ", "La latenza e' 40 ms.", None,
     ["file:verimem/quantity_match.py:1050"]),
]


def _mcp(prop: str, topic: str, source: str | None,
         vb: list[str] | None) -> dict:
    from verimem import mcp_server  # noqa: PLC0415

    args: dict = {"proposition": prop, "topic": topic}
    if source:
        args["source"] = source
    if vb:
        args["verified_by"] = vb
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    return json.loads("\n".join(getattr(c, "text", "") for c in out))


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  REGIME: HIPPO_DATA_DIR={tmp}  (store di Aurelio NON toccato)")
    mem = Memory(str(tmp / "cens.db"))

    visto: dict[str, dict[str, int]] = {}   # campo -> {SDK: n, MCP: n}
    esiti: list[tuple[str, str, str]] = []
    print(f"\n  {'caso':<21} {'SDK status':<14} {'MCP status':<14} "
          f"{'chiavi SDK/MCP'}")
    print("  " + "-" * 72)
    for i, (et, prop, src, vb) in enumerate(CASI):
        kw: dict = {}
        if src:
            kw["source"] = src
        if vb:
            kw["verified_by"] = vb
        r_sdk = mem.add(prop, topic=f"cens/sdk/{i}", validate="full", **kw)
        r_mcp = _mcp(prop, f"cens/mcp/{i}", src, vb)
        for porta, ric in (("SDK", r_sdk), ("MCP", r_mcp)):
            for k in ric:
                visto.setdefault(k, {"SDK": 0, "MCP": 0})[porta] += 1
        s_st, m_st = str(r_sdk.get("status")), str(r_mcp.get("status"))
        esiti.append((et.strip(), s_st, m_st))
        print(f"  {et:<21} {s_st:<14} {m_st:<14} "
              f"{len(r_sdk)}/{len(r_mcp)}")

    # ── CONTROLLO CHE DEVE POTER FALLIRE ─────────────────────────────────
    diversi = sum(1 for _e, a, b in esiti if a != b)
    quarantine = sum(1 for _e, a, b in esiti
                     if "quarant" in a or "quarant" in b)
    print("\n  [1] CONTROLLO: i casi attraversano esiti DIVERSI?")
    print(f"      celle con esito diverso fra le porte: {diversi}/{len(CASI)}")
    print(f"      casi che producono una quarantena: {quarantine}/{len(CASI)}")
    if quarantine == 0:
        print("      CONTROLLO CADUTO: nessun caso quarantina ⇒ i campi che")
        print("      esistono SOLO in quell'esito non compaiono, e la matrice")
        print("      sarebbe incompleta senza che si veda. NESSUN VERDETTO.")
        return 1

    # ── LA MATRICE ───────────────────────────────────────────────────────
    n = len(CASI)
    solo_sdk = sorted(k for k, v in visto.items() if v["SDK"] and not v["MCP"])
    solo_mcp = sorted(k for k, v in visto.items() if v["MCP"] and not v["SDK"])
    entrambe = sorted(k for k, v in visto.items() if v["SDK"] and v["MCP"])

    print(f"\n  ══ MATRICE — {len(visto)} campi distinti su {n} casi ══")
    print(f"\n  SOLO SDK ({len(solo_sdk)}) — il chiamante MCP non li vede:")
    for k in solo_sdk:
        print(f"     {k:<24} presente in {visto[k]['SDK']}/{n} casi")
    print(f"\n  SOLO MCP ({len(solo_mcp)}) — il chiamante SDK non li vede:")
    for k in solo_mcp:
        print(f"     {k:<24} presente in {visto[k]['MCP']}/{n} casi")
    print(f"\n  SU ENTRAMBE ({len(entrambe)}):")
    for k in entrambe:
        v = visto[k]
        nota = "" if v["SDK"] == v["MCP"] else "   <<< frequenza DIVERSA"
        print(f"     {k:<24} SDK {v['SDK']}/{n} · MCP {v['MCP']}/{n}{nota}")

    print("\n  ⚠️ CHE COSA QUESTO NON DICE: non dice che il gate sbagli, ne'")
    print("     che una porta sia migliore. Dice cosa ciascuna RACCONTA di se'.")
    print(f"     LIMITI: {n} casi, italiano, handler MCP in-process (un client")
    print("     vero passa dallo stdio). I campi che compaiono solo in esiti")
    print("     non coperti da questi sei casi NON sono in questa matrice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
