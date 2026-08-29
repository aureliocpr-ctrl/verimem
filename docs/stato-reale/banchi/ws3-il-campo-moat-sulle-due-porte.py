"""Il campo `moat` differisce fra le porte in 6 casi su 6 — e NON e' un difetto.

`moat` e' l'ultimo campo del verdetto che non avevo letto: sta su **entrambe**
le porte, 6 casi su 6 (`57726ae1`). La domanda che valeva non era «e' pieno?»
ma: **dice la stessa cosa a chi legge dall'SDK e a chi legge da MCP?** Se lo
stesso campo raccontasse verdetti diversi sarebbe **peggio di un rename**.

── LA MISURA: 6/6 DIVERSI ──────────────────────────────────────────────────

    caso              SDK                  MCP
    nudo              not_run:no_source    "not run — no source, so the
                                            entailment moat had nothing to
                                            check; pass source=… to have this
                                            write judged"
    fonte SUPPORTA    passed               "judged 99.9 — the source SCORES as
                                            supporting this fact: that is the
                                            judge's score, NOT a check that the
                                            fact follows from it"
    fonte NEGA        failed               "judged 0.6 — the source does NOT
                                            entail this fact: that is why it is
                                            quarantined"

Sei celle su sei con stringhe diverse. **Sembrava il reperto della serata.**

── E POI HO CERCATO SE FOSSE PRESCRITTO, invece di gridare ─────────────────

🔑 **La lezione era nel file, come le altre due volte stasera.**
`mcp_server.py:13400-13407`, commento degli autori::

    # `esito_del_moat` non usa ne' il verdetto ne' la soglia. Usa i layer, la
    # source e il punteggio … Per questo ora si DERIVA dalla stessa funzione
    # dell'SDK invece di ricalcolare: **due calcoli della stessa cosa sono
    # cio' che ha permesso alle due porte di divergere.**

⇒ **Il problema che stavo per segnalare e' gia' stato trovato e curato**, e la
cura e' proprio quella giusta: **una sola funzione** (`client.esito_del_moat`),
non due calcoli. MCP la **chiama** e ne veste l'esito in prosa.

🟢 **VERDETTO: il verdetto e' IDENTICO, cambia solo la RESA.** SDK restituisce
un **codice** per il codice (`passed` / `failed` / `not_run:*`), MCP una
**frase** per un lettore umano o LLM. **Il mio «6/6 divergono» era vero sulla
stringa e falso sulla sostanza** — contavo caratteri dove serviva leggere da
dove venivano.

⚠️ **IL RESIDUO ONESTO, piccolo e reale.** L'avvertenza epistemica esiste
**solo** nella prosa MCP: «*that is the judge's **score**, **not a check that
the fact follows from it***». L'SDK dice `passed`, che e' **piu' forte di cio'
che il gate ha fatto** — ha misurato un punteggio, non verificato
un'implicazione. Chi legge `passed` da codice non riceve quella cautela, e il
docstring di `esito_del_moat` non la porta.
📌 **Non lo propongo come difetto**: `passed` e' un token per `if`, non una
promessa in prosa, e il posto giusto per l'avvertenza sarebbe il docstring —
**decisione di chi mantiene l'SDK**, non mia. **Lo lascio agli atti come
osservazione.**

🔑 **E il conto della serata**: e' il **quinto** allarme mio che si sgonfia
appena lo misuro, e il **terzo** sgonfiato dallo stesso presidio — *cercare se
la cosa e' PRESCRITTA prima di chiamarla difetto*. Tre volte su tre gli autori
ci erano gia' arrivati, e in due casi il commento spiegava anche **perche'**.

⚠️ LIMITI: 6 casi, nessuno raggiunge il ramo `reject`, handler MCP in-process,
italiano. Store TEMPORANEO: quello di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-campo-moat-sulle-due-porte.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path

F_SUP = "Il rapporto indica che la penale e-di 500 euro al giorno."
F_NEG = "Il rapporto indica che la penale e-di 120 euro al giorno."

CASI: list[tuple[str, str, str | None, list[str] | None]] = [
    ("1 nudo            ", "Il deposito si trova a Bologna.", None, None),
    ("2 autoclaim       ", "Il fix funziona ed e' verificato.", None, None),
    ("3 fonte SUPPORTA  ", "La penale e-di 500 euro al giorno.", F_SUP, None),
    ("4 fonte NEGA      ", "La penale e-di 500 euro al giorno.", F_NEG, None),
    ("5 bench FABBRICATO", "La latenza e' 40 ms.", None,
     ["bench:non_esiste_2026"]),
    ("6 file REALE      ", "La latenza e' 40 ms.", None,
     ["file:verimem/quantity_match.py:1050"]),
]


def _mcp(prop: str, topic: str, src: str | None, vb: list[str] | None) -> dict:
    from verimem import mcp_server  # noqa: PLC0415

    args: dict = {"proposition": prop, "topic": topic}
    if src:
        args["source"] = src
    if vb:
        args["verified_by"] = vb
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    return json.loads("\n".join(getattr(c, "text", "") for c in out))


def main() -> int:
    # ── ① LA PROVA CHE NON E' UN DIFETTO STA NEL SORGENTE, non nel banco ──
    print("  [1] MCP RICALCOLA il moat o lo DERIVA dalla funzione dell'SDK?")
    try:
        out = subprocess.run(
            ["git", "grep", "-n", "esito_del_moat", "--", "verimem/"],
            capture_output=True, text=True, check=False).stdout.strip()
    except Exception as e:  # noqa: BLE001
        out = f"<git grep non eseguibile: {type(e).__name__}>"
    for riga in out.splitlines():
        print(f"      {riga}")
    deriva = "mcp_server.py" in out and "client.py" in out
    print(f"      -> MCP importa la funzione dell'SDK: {deriva}")
    if not deriva:
        print("      ⚠️ ATTENZIONE: se MCP NON derivasse, due calcoli della")
        print("      stessa cosa potrebbero far divergere il VERDETTO e non")
        print("      solo la resa — e il verdetto qui sotto andrebbe rifatto.")

    # ── ② la misura testuale ──────────────────────────────────────────────
    tmp = Path(tempfile.mkdtemp())
    os.environ["HIPPO_DATA_DIR"] = str(tmp)
    from verimem.client import Memory  # noqa: PLC0415

    print(f"\n  [2] IL TESTO DI `moat`, PORTA PER PORTA (store temp: {tmp})")
    mem = Memory(str(tmp / "moat.db"))
    diversi = 0
    for i, (et, prop, src, vb) in enumerate(CASI):
        kw: dict = {}
        if src:
            kw["source"] = src
        if vb:
            kw["verified_by"] = vb
        rs = mem.add(prop, topic=f"mt/s{i}", validate="full", **kw)
        rm = _mcp(prop, f"mt/m{i}", src, vb)
        ms, mm = str(rs.get("moat")), str(rm.get("moat"))
        if ms != mm:
            diversi += 1
        print(f"      {et}  SDK: {ms[:52]}")
        print(f"      {'':<18}  MCP: {mm[:96]}")

    print(f"\n  [3] celle con TESTO diverso: {diversi}/{len(CASI)}")
    print("\n  ══ VERDETTO ══")
    if deriva:
        print("     Le stringhe differiscono in tutte le celle, ma il VERDETTO")
        print("     e' lo stesso: MCP DERIVA da `client.esito_del_moat` invece")
        print("     di ricalcolare, e il commento a mcp_server.py:13400 dice")
        print("     che e' stato fatto proprio perche' «due calcoli della stessa")
        print("     cosa sono cio' che ha permesso alle due porte di divergere».")
        print("     ⇒ NON e' un difetto: e' una traduzione deliberata.")
        print("     ⚠️ Residuo: l'avvertenza «e' il punteggio del giudice, NON")
        print("        una verifica che il fatto segua dalla fonte» sta SOLO")
        print("        nella prosa MCP. Osservazione, non difetto proposto.")
    else:
        print("     Il sorgente NON mostra la derivazione: il rischio che le due")
        print("     porte divergano sul VERDETTO torna aperto. RIMISURARE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
