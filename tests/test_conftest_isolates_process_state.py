"""Lo stato di processo dei breaker non si eredita fra test.

Il conftest azzera gia' il breaker del rerank, con la motivazione che vale
identica per il gemello: "Va azzerato come ogni altro stato di processo, non
lasciato alla cortesia dei test". Il breaker della FUSIONE e' nato il 25/07,
dopo quella fixture, e non ci e' mai entrato — cosi'
test_cold_path_gains_ppr_signal_when_fusion_on, che fissa il budget a 30 s
proprio per non misurare la velocita' del runner, restava comunque in balia
di un trip lasciato da un test qualunque girato prima: a breaker scattato la
fusione e' SALTATA e nessun budget la riporta. Riprodotto il 27/07 trippando
il breaker prima del test: stesso identico fallimento del rosso in suite.

Verifica di CONTRATTO sull'AST del conftest, non funzionale: provare la
fixture dall'esterno vorrebbe dire lanciare un pytest figlio con due test in
ordine fissato, e il valore aggiunto non paga il costo. La mutazione che
conta (togliere una delle due chiamate) fa fallire questo test.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_the_autouse_fixture_resets_every_process_breaker() -> None:
    src = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    attesi = {"_rerank_breaker_reset", "_fusion_breaker_reset"}
    trovati: set[str] = set()
    for nodo in ast.walk(tree):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        autouse = any(
            isinstance(d, ast.Call)
            and any(kw.arg == "autouse" and getattr(kw.value, "value", False)
                    for kw in d.keywords)
            for d in nodo.decorator_list
        )
        if not autouse:
            continue
        for c in ast.walk(nodo):
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
                if c.func.attr in attesi:
                    trovati.add(c.func.attr)
    assert attesi <= trovati, (
        f"una fixture autouse deve azzerare OGNI breaker di processo; "
        f"mancano: {sorted(attesi - trovati)}")
