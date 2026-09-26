"""T-MAP-11, il presidio — perché la prossima porta non nasca col moat spento.

`ingest_conversation` ha `ground: bool = False` nella firma: un chiamante che
non lo passa ottiene un ingest **senza moat**, e non lo scopre — non c'è errore,
non c'è avviso, i fatti entrano tutti come `model_claim`. È esattamente com'è
nata la porta MCP (`mcp_server.py`), rimasta così finché non l'ho misurata il
2026-09-09.

Una regola riletta non vale niente: il presidio è un CONTROLLO. Questo test
legge l'albero sintattico del pacchetto e pretende che **ogni** chiamata a
`ingest_conversation` dica esplicitamente cosa vuole — `ground=` passato, in un
senso o nell'altro. Fallisce sulla porta nuova che se ne dimentica.

Oggi i chiamanti sono tre: `client.py` (preset), `import_conversations.py`
(True) e `mcp_server.py` (l'argomento del tool, default True).

    python -m pytest tests/test_ogni_porta_dell_ingest_dice_se_vuole_il_moat.py -q
"""
from __future__ import annotations

import ast
import pathlib

PACCHETTO = pathlib.Path(__file__).resolve().parents[1] / "verimem"
#: il file che DEFINISCE la funzione: qui la firma è il default, non un chiamante.
DEFINIZIONE = "conversation_ingest.py"


def _chiamate_senza_ground() -> list[str]:
    fuori: list[str] = []
    for f in sorted(PACCHETTO.glob("*.py")):
        if f.name == DEFINIZIONE:
            continue
        try:
            albero = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except SyntaxError:  # pragma: no cover — un file rotto è un altro problema
            continue
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.Call):
                continue
            nome = nodo.func
            atteso = (isinstance(nome, ast.Name) and nome.id == "ingest_conversation") or \
                     (isinstance(nome, ast.Attribute) and nome.attr == "ingest_conversation")
            if not atteso:
                continue
            if not any(k.arg == "ground" for k in nodo.keywords):
                fuori.append(f"{f.name}:{nodo.lineno}")
    return fuori


def test_ogni_chiamante_dell_ingest_dichiara_se_vuole_il_moat() -> None:
    senza = _chiamate_senza_ground()
    assert not senza, (
        "queste porte chiamano ingest_conversation senza dire se vogliono il "
        f"moat, e la firma lo ha a False: {senza}. Passa ground= (True, il "
        "default del preset, o l'argomento della porta): un ingest senza moat "
        "non emette nessun segnale, i fatti entrano tutti come model_claim.")


def test_il_presidio_sa_riconoscere_una_porta_smemorata(tmp_path) -> None:
    """Il controllo positivo del controllo: se il presidio non sapesse vedere
    una chiamata senza `ground`, il test sopra sarebbe verde per sempre."""
    finto = tmp_path / "porta_finta.py"
    finto.write_text(
        "def f(sm, msgs, llm):\n"
        "    return ingest_conversation(sm, msgs, llm=llm, conversation_id='x')\n",
        encoding="utf-8")
    albero = ast.parse(finto.read_text(encoding="utf-8"))
    trovate = [n for n in ast.walk(albero)
               if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name)
               and n.func.id == "ingest_conversation"
               and not any(k.arg == "ground" for k in n.keywords)]
    assert len(trovate) == 1, "il presidio non vede una chiamata senza ground"
