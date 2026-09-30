"""Un fatto NUOVO nasce da una porta sola: `Memory.add()`.

Il 19 settembre 2026 la porta MCP costruiva il `Fact` a mano e chiamava
`semantic.store()`: non passava da `add()`, quindi la ricevuta del nucleo non
c'era, il libro mastro non contava le sue scritture, e il 07/08 lo stesso buco
era stato pareggiato con un secondo emettitore di eventi invece che chiuso. La
riga di comando fa lo stesso in `facts add`, e lo dice da sola: il commento sul
suo `Fact(` racconta che «è la terza volta che questo `Fact(` costruito a mano
perde un campo che `client.py` scrive». Classe ①: una copia invece della
superficie unica. Ogni campo che nasce in `add()` va poi ricopiato in ogni
copia, e la copia che se ne dimentica scrive un fatto diverso con lo stesso
testo.

Il censimento del 25/09 su `0d0e6aac`, fatto con due strumenti (`git grep` e
questo stesso rilevatore) che hanno dato lo stesso elenco: dieci costruzioni,
una sola nella porta, due nelle letture di `semantic.py`, sette fuori.

🔑 IL CRITERIO E' L'OGGETTO, NON IL NOME. Il rilevatore risolve gli import
(`from .semantic import Fact as F`, `from . import semantic`,
`import verimem.semantic as s`) e cerca le chiamate che costruiscono QUELLA
classe. Contare la stringa `Fact(` avrebbe mancato un alias, e contare
`semantic.store(` avrebbe preso anche gli episodi (`mem.store(ep)` in
`consolidation.py`) e mancato `sm.store(f)`.

📌 PERCHE' LA COSTRUZIONE E NON LA PERSISTENZA. Un fatto nuovo non esiste senza
essere costruito: chi lo costruisce decide che cosa entra. Chi persiste un fatto
che esiste gia' non e' una porta — il replay del journal in `semantic.py`
completa una scrittura che il cancello ha gia' ammesso.

⚠️ E' UN PRESIDIO STATICO, e il suo limite va detto. Legge il sorgente, non il
comportamento: non vede una copia fatta con `dataclasses.replace` o
`copy.copy` (zero nel pacchetto al 25/09), ne' una costruzione via `getattr` o
`eval`. E non dice se la porta scrive BENE: quello lo misurano le celle alla
porta, una per via di scrittura. Qui si sorveglia una cosa sola: che la
decisione di che cosa diventa un fatto resti in un posto solo.

📉 IL DEBITO SCENDE E BASTA. I siti non ancora curati stanno in `DEBITO`,
ciascuno col pezzo della strada che lo cura. Un sito nuovo e' rosso; un sito
curato che resta nell'elenco e' rosso anche lui, perche' un'esenzione che non
esenta piu' niente coprirebbe il prossimo che nasce nella stessa funzione.
"""

from __future__ import annotations

import ast
import pathlib

RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"

#: Dove un `Fact` si puo' costruire, e perche'. Chiave: (file, funzione).
AMMESSI = {
    ("client.py", "Memory.add"):
        "LA porta: costruisce il fatto dopo il giudizio, una volta per tutte",
    ("semantic.py", "_fact_from_dict"):
        "lettura: il replay del journal ricostruisce una scrittura gia' ammessa",
    ("semantic.py", "SemanticMemory._row"):
        "lettura: una riga del database diventa un oggetto",
}

#: I siti che costruiscono ancora un `Fact` fuori dalla porta, col pezzo della
#: strada che li porta dentro `Memory.add()`. Puo' solo scendere.
DEBITO = {
    # ("document_promote.py", "promote_chunk_to_fact"): P2, arrivato con #150.
    # ("transcript_promote.py", "promote_turn_to_fact"): P3, arrivato il 30/09.
    ("conversation_ingest.py", "ingest_conversation"): "P4, dopo #23",
    ("sleep.py", "SleepEngine._synthesize_from_cluster"): "P5",
    # ("consolidation.py", "_persist_master"): P5, arrivato il 30/09.
}


def _e_il_modulo_semantic(modulo: str | None, livello: int) -> bool:
    if not modulo:
        return False
    return modulo.split(".")[-1] == "semantic" and (
        livello > 0 or modulo.split(".")[0] in {"verimem", "engram", "hippoagent"})


def _costruzioni(testo: str, definisce_fact: bool = False) -> list[tuple[str, int]]:
    """(funzione che la contiene, riga) per ogni chiamata che costruisce un Fact.

    I legami d'import si raccolgono su tutto il modulo, anche quelli dentro una
    funzione: `cli.py` importa `Fact` dentro `facts_add`. Un nome legato alla
    classe in un punto qualsiasi del modulo vale per tutto il modulo — e'
    un'approssimazione per eccesso, e per un presidio e' il verso giusto.
    """
    albero = ast.parse(testo)
    nomi_fact: set[str] = {"Fact"} if definisce_fact else set()
    alias_modulo: set[str] = set()
    for n in ast.walk(albero):
        if isinstance(n, ast.ImportFrom):
            if _e_il_modulo_semantic(n.module, n.level):
                nomi_fact.update(a.asname or "Fact" for a in n.names if a.name == "Fact")
            elif n.module in (None, "verimem", "engram", "hippoagent"):
                alias_modulo.update(
                    a.asname or "semantic" for a in n.names if a.name == "semantic")
        elif isinstance(n, ast.Import):
            alias_modulo.update(
                a.asname or a.name for a in n.names if _e_il_modulo_semantic(a.name, 0))

    def _punteggiato(e: ast.AST) -> str | None:
        parti = []
        while isinstance(e, ast.Attribute):
            parti.append(e.attr)
            e = e.value
        if not isinstance(e, ast.Name):
            return None
        parti.append(e.id)
        return ".".join(reversed(parti))

    trovate: list[tuple[str, int]] = []

    class _Visita(ast.NodeVisitor):
        def __init__(self) -> None:
            self.pila: list[str] = []

        def _dentro(self, nodo) -> None:
            self.pila.append(nodo.name)
            self.generic_visit(nodo)
            self.pila.pop()

        visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _dentro

        def visit_Call(self, nodo: ast.Call) -> None:
            f = nodo.func
            if isinstance(f, ast.Name):
                costruisce = f.id in nomi_fact
            elif isinstance(f, ast.Attribute) and f.attr == "Fact":
                base = _punteggiato(f.value)
                costruisce = base is not None and (
                    base in alias_modulo or base.split(".")[-1] == "semantic")
            else:
                costruisce = False
            if costruisce:
                trovate.append((".".join(self.pila) or "<modulo>", nodo.lineno))
            self.generic_visit(nodo)

    _Visita().visit(albero)
    return trovate


def _censimento() -> dict[tuple[str, str], list[int]]:
    """(file, funzione) -> righe, per tutto il pacchetto."""
    siti: dict[tuple[str, str], list[int]] = {}
    for p in sorted(RADICE.rglob("*.py")):
        testo = p.read_text(encoding="utf-8", errors="replace")
        definisce = "\nclass Fact" in testo or testo.startswith("class Fact")
        for funzione, riga in _costruzioni(testo, definisce):
            siti.setdefault((p.relative_to(RADICE).as_posix(), funzione), []).append(riga)
    return siti


def test_nessun_fatto_nasce_fuori_dalla_porta():
    fuori = {k: v for k, v in _censimento().items()
             if k not in AMMESSI and k not in DEBITO}
    assert not fuori, (
        "questi punti costruiscono un `Fact` fuori da `Memory.add()`, e non "
        "sono nell'elenco del debito:\n" + "\n".join(
            f"  {f}:{','.join(map(str, righe))}  in {fn}"
            for (f, fn), righe in sorted(fuori.items()))
        + "\nUn fatto costruito qui non passa dal cancello della porta, non "
        "rende la ricevuta del nucleo e perde ogni campo che nascera' in "
        "`add()`: fallo passare da `Memory.add()`.")


def test_il_debito_puo_solo_scendere():
    siti = _censimento()
    curati = sorted(k for k in DEBITO if k not in siti)
    assert not curati, (
        "questi siti del debito non costruiscono piu' un `Fact`: toglili "
        f"dall'elenco, e' la prova che il pezzo e' arrivato — {curati}")


def test_CONTROLLO_ogni_esenzione_esenta_ancora_qualcosa():
    """Un'esenzione rimasta senza oggetto copre il prossimo `Fact(` che nasce
    nella stessa funzione, senza che nessuno l'abbia deciso."""
    siti = _censimento()
    vuote = sorted(k for k in AMMESSI if k not in siti)
    assert not vuote, f"esenzioni che non esentano piu' niente: {vuote}"


def test_CONTROLLO_il_rilevatore_vede_la_porta():
    """Se `add()` smettesse di costruire il fatto — o il rilevatore smettesse
    di vederlo — i test sopra resterebbero verdi sorvegliando il nulla."""
    assert ("client.py", "Memory.add") in _censimento(), (
        "il rilevatore non vede piu' la costruzione del fatto nella porta: "
        "questo file sta sorvegliando il nulla")


def test_CONTROLLO_il_rilevatore_segue_l_oggetto_e_non_il_nome():
    """Il positivo e il negativo, su sorgenti scritti apposta."""
    visti = {
        "alias": "from .semantic import Fact as F\ndef a():\n    return F(proposition='x')\n",
        "modulo": "from . import semantic\ndef b():\n    return semantic.Fact(proposition='x')\n",
        "assoluto": "import verimem.semantic as s\ndef c():\n    return s.Fact(proposition='x')\n",
        "catena": "import verimem.semantic\ndef d():\n    return verimem.semantic.Fact(proposition='x')\n",
    }
    for nome, sorgente in visti.items():
        assert _costruzioni(sorgente), f"costruzione non vista: {nome}"
    non_costruzioni = (
        "from .semantic import Fact\n"
        "def e(x) -> Fact:\n"
        "    if isinstance(x, Fact):\n"
        "        return x\n"
        "    return Fact.__name__\n"
        "class Fatto:\n"
        "    pass\n"
        "def f():\n"
        "    return Fatto()\n"
    )
    assert _costruzioni(non_costruzioni) == [], (
        "un'annotazione, un isinstance o una classe di nome simile sono stati "
        "presi per costruzioni: il presidio accuserebbe chi non costruisce")
