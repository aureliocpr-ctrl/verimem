"""Una fixture a scope largo gira PRIMA delle `autouse`, e quindi fuori da esse.

═══ IL DIFETTO, misurato il 2026-08-16 ═══

Nove test andavano in ERROR al setup in CI mentre la stessa chiamata, sullo
stesso runner e pochi minuti prima, riusciva. I nove stanno in **due file**, e
i due file hanno l'unica cosa in comune che conta::

    test_il_write_path_gate_mantiene_cio_che_la_riga_promette.py:67
    test_ogni_porta_di_lettura_porta_la_provenienza.py:71
        @pytest.fixture(scope="module")

Gli altri file rossi non ce l'hanno. ⇒ **La correlazione è perfetta.**

═══ IL MECCANISMO, provato su un banco a due file ═══

pytest istanzia le fixture **dal più largo al più stretto**. Misurato::

    1. fixture di MODULO
    2. stub (function, autouse)

⇒ Una fixture di modulo gira **prima** di OGNI `autouse` a scope funzione — cioè
prima di tutte le garanzie che il conftest dà a ogni test::

    _stub_embedding_model   il modello finto: senza, si carica quello VERO
    _isolate_test_env       HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE,
                            ENGRAM_ADMISSION_GATE neutralizzato, rerank pinnato

🔑 **Il caso peggiore non è la lentezza: è che un test SUL GATE girava con
l'impostazione persistente del gate dell'operatore** — `ENGRAM_ADMISSION_GATE`
viene tolto da `_isolate_test_env`, che per quelle fixture non era ancora
partita. Lo stesso test può passare o fallire secondo una variabile di ambiente
della macchina, e nessuno lo vedrebbe.

═══ LA CLASSE, che è il motivo per cui questo banco esiste ═══

**Una fixture promossa a scope largo per VELOCITÀ rinuncia in silenzio a ogni
garanzia `autouse`.** Non c'è errore, non c'è avviso: la promozione è una riga,
e il prezzo è invisibile finché un ambiente diverso non lo rende visibile.

⚠️ LIMITE: qui si guarda il TESTO dei file di test, non l'ordine a runtime.
L'ordine l'ho misurato a parte (sopra); questo banco impedisce che la forma
torni, non ricontrolla la semantica di pytest a ogni giro.
"""
from __future__ import annotations

import ast
import pathlib

TESTS = pathlib.Path(__file__).resolve().parent

#: Chi costruisce uno di questi dentro una fixture a scope largo sta uscendo
#: dalle garanzie: sono le superfici che il conftest neutralizza per ogni test.
_COSTRUTTORI = ("Memory", "SemanticMemory", "EpisodicMemory")

#: Fixture a scope largo che NON toccano il prodotto: legittime, e dichiarate
#: qui con il motivo, perche' un elenco vuoto renderebbe il banco un divieto
#: assoluto invece di un criterio.
TOLLERATE: frozenset[str] = frozenset()


def _fixture_larghe_che_costruiscono(percorso: pathlib.Path) -> list[str]:
    """Nomi delle fixture module/session che istanziano il prodotto."""
    try:
        albero = ast.parse(percorso.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    trovate = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        largo = False
        for dec in nodo.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            nome = ast.unparse(dec.func) if hasattr(ast, "unparse") else ""
            if "fixture" not in nome:
                continue
            for kw in dec.keywords:
                if kw.arg == "scope" and isinstance(kw.value, ast.Constant) \
                        and kw.value.value in ("module", "session", "package"):
                    largo = True
        if not largo:
            continue
        costruisce = any(
            isinstance(c, ast.Call)
            and (getattr(c.func, "id", "") in _COSTRUTTORI
                 or getattr(c.func, "attr", "") in _COSTRUTTORI)
            for c in ast.walk(nodo))
        if costruisce:
            trovate.append(f"{percorso.name}::{nodo.name}")
    return trovate


def test_nessuna_fixture_larga_costruisce_il_prodotto():
    """IL CUORE: chi costruisce il prodotto in una fixture a scope largo lo fa
    fuori dallo stub e fuori dall'isolamento dell'ambiente."""
    colpevoli = [
        v
        for f in sorted(TESTS.glob("test_*.py"))
        for v in _fixture_larghe_che_costruiscono(f)
        if v not in TOLLERATE
    ]
    assert not colpevoli, (
        "queste fixture hanno scope module/session e istanziano il prodotto, "
        "quindi girano PRIMA di ogni `autouse` del conftest — senza il modello "
        "finto e senza `_isolate_test_env` (HF offline, gate dell'operatore "
        "neutralizzato, rerank pinnato):\n  " + "\n  ".join(colpevoli)
        + "\n\nToglile lo scope: con quello di default la fixture entra nelle "
          "garanzie e il modello finto la rende anche piu' veloce. Se una "
          "davvero deve restare larga, aggiungila a TOLLERATE col motivo.")


def test_il_RILEVATORE_vede_il_caso_che_deve_vedere():
    """CONTROLLO POSITIVO: senza, il banco sopra passerebbe anche se il
    rilevatore non trovasse mai niente — la forma di verde che curiamo da
    giorni."""
    sorgente = (
        "import pytest\n"
        "from verimem import Memory\n"
        '@pytest.fixture(scope="module")\n'
        "def finta(tmp_path_factory):\n"
        "    return Memory(str(tmp_path_factory.mktemp('x') / 'd.db'))\n"
    )
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "test_finto.py"
        p.write_text(sorgente, encoding="utf-8")
        trovate = _fixture_larghe_che_costruiscono(p)
    assert trovate == ["test_finto.py::finta"], (
        f"il rilevatore non vede il caso da manuale: {trovate}")
