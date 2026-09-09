"""La rubrica dei 15 documenti del LOTTO 1, nel formato che l'indice chiede.

Il lotto 1 l'ho scritto in prosa prima che il formato tabellare esistesse: il
contenuto c'e' (wake.md:86 nomina `_avoid_path_block`), ma il contatore cerca
`verimem/x.py:NNN` seguito da `nome` NELLA STESSA CELLA. Questo script non
inventa contenuto: prende dall'AST dove ogni funzione sta, da chiamanti-ws5.json
chi la chiama e quale test la esercita, e ne fa l'indice navigabile.

⚠️ Il formato NON si deduce dalla regex, si copia da una riga che gia' conta
(chunking.md). Dedurlo mi e' costato un giro: avevo messo il separatore di
colonna FRA il file e il nome, e il contatore leggeva i verdetti ma non le
funzioni — 550 verdetti e 221 mappate, che e' il modo in cui un formato
sbagliato si traveste da lavoro mancante.

I VERDETTI, e cosa vale ciascuno:
  MAI CHIAMATA  nessun chiamante nel prodotto E nessuno nei test. Il caso forte:
                non la chiama nemmeno chi la dovrebbe provare.
  NON MISURATO  tutto il resto. E' lo stato vero finche' non l'ho esercitata:
                sapere CHI la chiama non e' sapere che FUNZIONA.
Un verdetto piu' alto lo scrivo a mano, con la prova accanto: FUNZIONA COME
PROMESSO generato da uno script non sarebbe un verdetto, sarebbe un colore.

Uso:  python scripts/mappa_tabella_ws5.py [--scrivi]
"""
from __future__ import annotations

import argparse
import ast
import json
import os

MAPPA = os.path.join("docs", "stato-reale", "mappa")
CHIAMANTI = os.path.join(MAPPA, ".chiamanti-ws5.json")

# .md -> i .py che documenta. Scritta a mano e verificata: il nome coincide
# tranne config_e_resonator, che ne tiene due.
# facts_conflict.md NON c'e': l'indice riga 413 lo assegna a ws6. Il documento
# l'ho scritto io di sponda; la rubrica la fa il suo owner.
DOCUMENTI = {
    "_hang_watchdog.md": ["verimem/_hang_watchdog.py"],
    "_import_lock.md": ["verimem/_import_lock.py"],
    "admission_gate.md": ["verimem/admission_gate.py"],
    "anti_confab_gate.md": ["verimem/anti_confab_gate.py"],
    "config_e_resonator.md": ["verimem/config.py",
                              "verimem/resonator_text_bridge.py"],
    "embedding.md": ["verimem/embedding.py"],
    "encode_service.md": ["verimem/encode_service.py"],
    "flow_events.md": ["verimem/flow_events.py"],
    "grounding_gate.md": ["verimem/grounding_gate.py"],
    "local_grounding.md": ["verimem/local_grounding.py"],
    "observability.md": ["verimem/observability.py"],
    "preload.md": ["verimem/preload.py"],
    "wake.md": ["verimem/wake.py"],
    "wake_strategy.md": ["verimem/wake_strategy.py"],
}

# I verdetti che ho scritto A MANO, con la prova accanto. Uno script puo'
# dire chi NON e' nominato; non puo' dire se cio' che una funzione promette
# sia vero. Questi tre li ho letti e verificati oggi.
VERDETTI_A_MANO = {
    ("verimem/wake.py", "WakeAgent._run_loop_tools"): (
        "NON COME PROMESSO",
        "il docstring la dichiara «Native tool-use ENTRY», ma l'ingresso vero e' "
        "`_run_loop` (def 1353, chiamata a 1296 e 1313) e nessuno la nomina"),
    ("verimem/wake.py", "WakeAgent._run_loop_react"): (
        "NON COME PROMESSO",
        "il docstring la dichiara «ReAct text-mode ENTRY»; stessa prova di "
        "`_run_loop_tools`: nessun riferimento nel prodotto ne' nei test"),
    ("verimem/wake.py", "WakeAgent._system_prompt"): (
        "MAI CHIAMATA",
        "soppiantata da `strategy.system_prompt`, usata a wake.py:1411 e "
        "definita in wake_strategy.py:109, 183, 352; questa non e' nominata"),
    ("verimem/observability.py", "route_logs_to_stderr"): (
        "NON COME PROMESSO",
        "il nome e le righe 22-25 promettono stderr perche' «its protocol owns "
        "stdout»; ma `PrintLoggerFactory(file=sys.stderr)` legge sys.stderr alla "
        "CHIAMATA, e con `sys.stderr is None` (pythonw, servizio senza console) "
        "`file=None` significa stdout: **86 byte misurati il 09/09**. Era la "
        "causa del rosso intermittente di test_ws5_il_download (T41). Il "
        "verdetto vale su questo commit: la cura e' sul ramo "
        "`tara/t41-logger-tace` (`be118f90`), non ancora su main"),
    ("verimem/grounding_gate.py", "_is_abstention"): (
        "MAI CHIAMATA",
        "un commento del 2026-07-21 (grounding_gate.py:129) ne descrive il "
        "comportamento come attivo, ma il nome non compare nel codice"),
}

INIZIO = "<!-- TABELLA-FUNZIONI ws5 -->"
FINE = "<!-- /TABELLA-FUNZIONI ws5 -->"

NOTA = [
    "*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*",
    "",
    "- **dove e chi** — `file:riga` dall'AST: misurato.",
    "- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione",
    "  PROMETTE, non cio' che fa.",
    "- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche",
    "  riferimenti nudi, property e annotazioni. Gli alias di import sono",
    "  risolti (senza, `emit_write` risultava a zero). Contando solo le",
    "  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,",
    "  property e callback non passano da una `ast.Call`. Include il file",
    "  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma",
    "  usi non suoi: e' un TETTO, non una misura.",
    "- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,",
    "  non che sia coperta.",
    "- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei",
    "  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =",
    "  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'",
    "  sapere che funziona.",
    "",
]


def nomi_qualificati(path):
    """(nome, riga, tipo, prima riga di docstring) di funzioni e classi."""
    with open(path, encoding="utf-8") as fh:
        albero = ast.parse(fh.read())
    fuori = []

    def visita(nodo, prefisso):
        for figlio in getattr(nodo, "body", []):
            if isinstance(figlio, (ast.ClassDef, ast.FunctionDef,
                                   ast.AsyncFunctionDef)):
                nome = prefisso + figlio.name
                tipo = "classe" if isinstance(figlio, ast.ClassDef) else "funzione"
                prime = (ast.get_docstring(figlio) or "").strip().splitlines()
                doc = (prime[0] if prime else "").replace("|", "-")[:120]
                fuori.append((nome, figlio.lineno, tipo, doc))
                visita(figlio, nome + ".")
            else:
                visita(figlio, prefisso)

    visita(albero, "")
    return sorted(fuori, key=lambda x: x[1])


def carica_chiamanti():
    with open(CHIAMANTI, encoding="utf-8") as fh:
        return json.load(fh)


def riassunto(files, quanti=2):
    """«a.py; b.py (+3)» — i primi, poi quanti restano."""
    if not files:
        return "**nessuno**"
    testa = "; ".join(f"`{f}`" for f in files[:quanti])
    resto = len(files) - quanti
    return testa + (f" (+{resto})" if resto > 0 else "")


def verdetto_di(corto, prod, test):
    if corto.startswith("__") and corto.endswith("__"):
        return "NON MISURATO"
    if not prod and not test:
        return "MAI CHIAMATA"
    return "NON MISURATO"


def tabella(md, pyfiles, dati):
    percorso_md = os.path.join(MAPPA, md)
    with open(percorso_md, encoding="utf-8") as fh:
        testo = fh.read()

    righe = [INIZIO, "", "## Dove sta ogni funzione, e con che verdetto", ""]
    righe += NOTA
    conta = {"MAI CHIAMATA": 0, "NON MISURATO": 0,
             "NON COME PROMESSO": 0, "solo test": 0}
    for py in pyfiles:
        funz = nomi_qualificati(py)
        righe += ["", f"### `{py}` — {len(funz)} fra funzioni e classi", "",
                  "| # | dove e chi | cos'e' | nominata da | test | verdetto |",
                  "|---|---|---|---|---|---|"]
        for i, (nome, ln, tipo, doc) in enumerate(funz, 1):
            corto = nome.split(".")[-1]
            prod = [f for f in dati["prodotto"].get(corto, [])]
            tst = dati["test"].get(corto, [])
            manuale = VERDETTI_A_MANO.get((py, nome))
            v = manuale[0] if manuale else verdetto_di(corto, prod, tst)
            conta[v] = conta.get(v, 0) + 1
            if not prod and tst:
                conta["solo test"] += 1
            desc = f"{tipo}: {doc}" if doc else tipo
            if manuale:
                desc += f" — **{manuale[1]}**"
            righe.append(
                f"| {i} | `{py}:{ln}` `{nome}` | {desc} | {riassunto(prod)} "
                f"| {riassunto(tst)} | {v} |")
    righe += ["", FINE, ""]
    return percorso_md, testo, "\n".join(righe), conta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrivi", action="store_true")
    a = ap.parse_args()
    dati = carica_chiamanti()

    tot = {"MAI CHIAMATA": 0, "NON MISURATO": 0,
           "NON COME PROMESSO": 0, "solo test": 0}
    righe_tot = 0
    for md, pyfiles in sorted(DOCUMENTI.items()):
        percorso, testo, blocco, conta = tabella(md, pyfiles, dati)
        n = sum(v for k, v in conta.items() if k != "solo test")
        righe_tot += n
        for k, v in conta.items():
            tot[k] += v
        mai = conta["MAI CHIAMATA"]
        print(f"{md:26} {n:4} righe   MAI CHIAMATA {mai:3}   "
              f"solo test {conta['solo test']:3}")
        if a.scrivi:
            if INIZIO in testo:
                pre = testo.split(INIZIO)[0].rstrip()
                post = testo.split(FINE, 1)[1] if FINE in testo else ""
                nuovo = pre + "\n\n" + blocco + post
            else:
                nuovo = testo.rstrip() + "\n\n---\n\n" + blocco
            with open(percorso, "w", encoding="utf-8") as fh:
                fh.write(nuovo)
    print(f"\nTOTALE {righe_tot} righe")
    print(f"  MAI CHIAMATA          {tot['MAI CHIAMATA']}")
    print(f"  NON MISURATO          {tot['NON MISURATO']}")
    print(f"  di cui SOLO NEI TEST  {tot['solo test']}   "
          "(zero chiamanti nel prodotto, ma un test le chiama)")


if __name__ == "__main__":
    main()
