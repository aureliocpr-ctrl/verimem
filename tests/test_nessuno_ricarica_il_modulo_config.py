"""Nessun test deve ricaricare ``verimem.config``.

``importlib.reload(verimem.config)`` costruisce un NUOVO oggetto ``CONFIG``
dentro il modulo, ma i moduli del prodotto lo hanno gia' catturato con
``from .config import CONFIG`` all'import e restano legati al precedente.
Da quel punto in poi i due non sono lo stesso oggetto: ogni override di
CONFIG in un test SUCCESSIVO finisce sull'istanza che il prodotto non
legge. Il test non fallisce — passa senza verificare nulla.

Misurato il 2026-08-12 (cura 464ddb8a): dopo il reload
``wake.CONFIG is config.CONFIG`` diventa False, e
``test_wake_extra::test_adaptive_macro_threshold_disabled`` legge 0.585
invece di 0.72 perche' prende il ramo adattato. Sulla coppia, nell'ordine
alfabetico in cui la CI la incontra: con il reload 1 failed / 59 passed,
senza 60 passed. In locale — un file alla volta — non si vede mai.

PERCHE' QUESTO FILE ESISTE, ed e' il punto:
la diagnosi era gia' scritta, per esteso e con questo stesso test nominato
come vittima, in ``tests/test_embedding_dim_guard.py``. Piu' altri tre file
che avvertono dello stesso pericolo. Quattro avvisi non hanno impedito la
recidiva, perche' un commento protegge il file in cui sta e nessun altro.
Una regola che vale per tutti va messa dove tutti passano.

L'alternativa senza effetti collaterali e' costruire un'istanza nuova:
``Config`` legge ``os.environ`` alla costruzione, quindi
``monkeypatch.setenv(...)`` + ``Config()`` ottiene lo stesso risultato
senza toccare il modulo condiviso.
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).parent


def _alias_del_modulo_config(albero: ast.AST) -> set[str]:
    """I nomi con cui QUESTO file chiama il modulo ``verimem.config``.

    Copre entrambe le forme d'importazione, perche' cercare la stringa
    "config" prenderebbe anche variabili omonime che non c'entrano.
    """
    alias: set[str] = set()
    for nodo in ast.walk(albero):
        # from verimem import config as _cfg   /   from verimem import config
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith(
            ("verimem", "engram", "hippoagent"),
        ):
            for n in nodo.names:
                if n.name == "config":
                    alias.add(n.asname or n.name)
        # import verimem.config as cfg
        elif isinstance(nodo, ast.Import):
            for n in nodo.names:
                if n.name.endswith(".config") and n.asname:
                    alias.add(n.asname)
    return alias


def _ricariche_del_config(sorgente: str) -> list[int]:
    """Righe in cui si chiama ``reload`` su un alias del modulo config."""
    albero = ast.parse(sorgente)
    alias = _alias_del_modulo_config(albero)
    if not alias:
        return []
    righe: list[int] = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        # importlib.reload(x)  oppure  reload(x)
        nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if nome != "reload" or not nodo.args:
            continue
        arg = nodo.args[0]
        bersaglio = getattr(arg, "id", None) or getattr(arg, "attr", None)
        if bersaglio in alias:
            righe.append(nodo.lineno)
    return righe


def test_il_rilevatore_riconosce_un_caso_COSTRUITO() -> None:
    """Controllo positivo: un guardiano che non trova mai niente puo' essere
    rotto senza che nessuno se ne accorga. Qui gli si da' in pasto il difetto
    esatto che deve fermare, e una variante che NON deve fermare."""
    colpevole = (
        "import importlib\n"
        "from verimem import config as _cfg\n"
        "importlib.reload(_cfg)\n"
    )
    assert _ricariche_del_config(colpevole) == [3], (
        "il rilevatore non vede il caso che esiste per fermare"
    )

    innocente = (
        "import importlib\n"
        "from verimem import mcp_server\n"
        "importlib.reload(mcp_server)\n"
    )
    assert _ricariche_del_config(innocente) == [], (
        "il rilevatore accusa un reload che non tocca il config"
    )


def test_nessun_file_di_test_ricarica_il_modulo_config() -> None:
    colpevoli: list[str] = []
    for f in sorted(TESTS.rglob("test_*.py")):
        if f.name == Path(__file__).name:
            continue
        try:
            righe = _ricariche_del_config(f.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - un file rotto lo dice pytest
            continue
        colpevoli += [f"{f.relative_to(TESTS)}:{r}" for r in righe]

    assert not colpevoli, (
        "questi test ricaricano verimem.config e da quel punto in poi ogni "
        "override di CONFIG non raggiunge piu' il prodotto:\n  "
        + "\n  ".join(colpevoli)
        + "\nUsa `Config()` (legge os.environ alla costruzione) invece di "
          "`importlib.reload`."
    )
