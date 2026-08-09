"""Lo stesso verbo esiste su CLI, HTTP e MCP? — la dimensione SUPERFICIE.

`mappa_ignoranza_delle_misure.py` dice che il 12% delle guardie cita la
superficie, e che nessuna misura confronta le superfici FRA LORO. Questo script
lo fa: per ogni verbo centrale del prodotto guarda se e' raggiungibile dalla
riga di comando, dall'API HTTP e dal canale MCP.

NASCE DA UN FINDING IMPRECISO, e il modo in cui lo si e' scoperto conta. L'altra
istanza aveva riportato «/v1/ask 404 — la cura ha aperto la porta su CLI e non
su API». Interrogando le rotte (non il grep sul nome, che e' la loro stessa
lezione) `/v1/ask` non esiste e `/v1/answer` si': il nome era sbagliato. Ma
misurando l'INTERA superficie invece di quei quattro nomi e' venuto fuori
qualcosa di piu' grande.

⚠️ E LA PRIMA STESURA DI QUESTO SCRIPT SBAGLIAVA ALLO STESSO MODO: cercava
`"search" in comandi_cli` e concludeva che `search` mancasse dalla CLI, mentre
si chiama `facts search`. Un matching per nome dentro uno strumento che serve a
smascherare i matching per nome. I nomi qui sotto sono stati verificati uno per
uno contro `app.registered_commands`, `app.registered_groups` e i dispatcher
reali.

NON TUTTI I VERBI DEVONO STARE OVUNQUE: `doctor`, `backup-all` o `swarm` sono
manutenzione della macchina, non capacita' di prodotto. Questo e' un elenco da
guardare, non un verdetto — la stessa cautela della mappa dell'ignoranza.

    python scripts/matrice_delle_superfici.py
"""
from __future__ import annotations

import ast
import logging
import pathlib
import re
import sys

logging.disable(logging.INFO)

RADICE = pathlib.Path(__file__).resolve().parent.parent

#: verbo -> (nomi CLI accettati, rotta /v1, tool MCP senza prefisso).
#: Piu' nomi CLI perche' la stessa capacita' ha alias storici (`remember` e
#: `save`) o vive in un gruppo (`facts add`).
CENTRALI: dict[str, tuple[tuple[str, ...], str | None, str | None]] = {
    "remember":   (("remember", "save", "facts add"), "memories", "remember"),
    "search":     (("facts search", "search-docs"), "search", "facts_search"),
    "recall":     (("recall", "facts recall"), "search", "recall"),
    "answer":     (("ask",), "answer", "trust_report"),
    "explain":    ((), "explain", "recall_explain"),
    "count":      ((), None, "corpus_size"),
    "ignorance":  (("ignorance",), None, "ignorance_map"),
    "history":    ((), None, "recall_history"),
    "forget":     (("facts forget",), "memories", "fact_forget"),
    "correct":    (("correct",), "correct", "fact_supersede"),
    "quarantine": (("facts restore", "facts requalify-quarantined"),
                   "quarantine", "quarantine_log"),
    "documents":  (("index", "search-docs"), None, "document_search"),
    "episodes":   (("episodes list",), None, "episode_list"),
    "lineage":    (("chain show",), None, "lineage_trace"),
}


def comandi_cli() -> set[str]:
    from verimem.cli import app
    fuori = {(c.name or c.callback.__name__).replace("_", "-")
             for c in app.registered_commands}
    for g in getattr(app, "registered_groups", []):
        sub = getattr(g, "typer_instance", None)
        if sub is None:
            continue
        fuori |= {f"{g.name} " + (c.name or c.callback.__name__).replace("_", "-")
                  for c in sub.registered_commands}
    return fuori


def rotte_http() -> set[str]:
    """Dal SORGENTE dei decoratori: costruire l'app vera vuole data dir e chiavi."""
    albero = ast.parse((RADICE / "verimem" / "gateway.py").read_text(encoding="utf-8"))
    fuori: set[str] = set()
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for d in nodo.decorator_list:
            if (isinstance(d, ast.Call)
                    and getattr(d.func, "attr", "") in
                    {"get", "post", "put", "delete", "patch"}
                    and getattr(getattr(d.func, "value", None), "id", "") == "app"
                    and d.args and isinstance(d.args[0], ast.Constant)
                    and isinstance(d.args[0].value, str)
                    and d.args[0].value.startswith("/v1/")):
                fuori.add(d.args[0].value[4:].split("/")[0])
    return fuori


def tool_mcp() -> set[str]:
    s = (RADICE / "verimem" / "mcp_server.py").read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r'name == "hippo_([a-z0-9_]+)"', s)}


def misura() -> dict[str, list[str]]:
    cli, http, mcp = comandi_cli(), rotte_http(), tool_mcp()
    buchi: dict[str, list[str]] = {}
    for verbo, (nomi_cli, rotta, tool) in CENTRALI.items():
        mancano = []
        if not any(n in cli for n in nomi_cli):
            mancano.append("CLI")
        if rotta is None or rotta not in http:
            mancano.append("HTTP")
        if tool is None or tool not in mcp:
            mancano.append("MCP")
        if mancano:
            buchi[verbo] = mancano
    return buchi


def main() -> int:
    cli, http, mcp = comandi_cli(), rotte_http(), tool_mcp()
    print(f"CLI  {len(cli):>4} comandi (primo livello + gruppi)")
    print(f"HTTP {len(http):>4} rotte /v1 -> {', '.join(sorted(http))}")
    print(f"MCP  {len(mcp):>4} tool\n")

    buchi = misura()
    print(f"{'verbo':12s} {'CLI':>5} {'HTTP':>5} {'MCP':>5}   manca su")
    print("-" * 52)
    for verbo in CENTRALI:
        m = buchi.get(verbo, [])
        print(f"{verbo:12s} {'--' if 'CLI' in m else 'si':>5} "
              f"{'--' if 'HTTP' in m else 'si':>5} "
              f"{'--' if 'MCP' in m else 'si':>5}   {', '.join(m)}")

    per_superficie = {s: sum(1 for m in buchi.values() if s in m)
                      for s in ("CLI", "HTTP", "MCP")}
    print(f"\n{len(buchi)} verbi su {len(CENTRALI)} non sono su tutte e tre.")
    print("mancanze per superficie:", ", ".join(
        f"{s} {n}" for s, n in sorted(per_superficie.items(),
                                      key=lambda x: -x[1])))
    print("\nLETTURA: la superficie con piu' mancanze e' quella con cui un")
    print("cliente ESTERNO usa il prodotto. Un verbo che vive solo su MCP e'")
    print("raggiungibile da un agente e da nessun umano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
