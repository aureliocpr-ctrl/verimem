"""Ogni import di ``torch``/``transformers`` nel pacchetto passa da UN lock.

⚠️ PERCHE' QUESTO FILE ESISTE — la cura del 06/09 aveva lasciato dei buchi, e
un lock che qualcuno non prende non serializza niente.

Il 06/09 e' stato misurato che due import pesanti in parallelo o si bloccano
(T1b: 0 giri su 3) o FALLISCONO («cannot import name
'AutoModelForSequenceClassification' from 'transformers'»), e la cura e' stata
``verimem/_import_lock.py``. Ma il lock e' stato messo in ALCUNI punti:

    local_grounding.py  make_finetuned_scorer   sotto lock_import()   OK
    local_relation.py   make_nli_classifier     scoperto              <- gemella!
    local_grounding.py  _tokenizzatore()        scoperto

Le prime due sono la stessa funzione scritta due volte — un cross-encoder che
si carica — e solo una era protetta. E' la forma gia' vista su questo prodotto:
**una copia invece di una superficie unica**, dove la cura raggiunge la copia
che si stava guardando e non l'altra.

Il 08/09 e' stato misurato che senza il daemon condiviso il warm del giudice
fallisce con lo STESSO errore del 06/09 (3 giri su 3, `moat_judge_failed`),
mentre col preload sincrono riesce 3 su 3: **la corsa e' ancora aperta**.

⚠️ IL LIMITE DI QUESTO FILE, e va letto prima di fidarsi: presidia la
PROPRIETA' («nessun import pesante fuori dal lock»), NON la causa del giro
fallito. Che la corsa misurata passi proprio da uno di questi due punti resta
**un'ipotesi**: provarla richiede il banco end-to-end senza daemon, che non si
puo' fare mentre il daemon serve a un'altra misura. Se un giorno il banco senza
daemon fallisse ancora con tutti gli import sotto lock, l'ipotesi e' falsa e
questo file resta comunque vero — ma non basta piu'.

⚠️ ESCLUSIONE DICHIARATA: ``sentence_transformers`` NON e' in questa lista, e
non e' una svista. E' il modello dell'EMBEDDER, ha il suo ``_MODEL_LOCK``, un
perimetro diverso, e nel caso che stiamo curando (delegate-only senza daemon)
non viene caricato affatto — ``preload._run`` esce prima. Metterlo qui
renderebbe questo file rosso su codice che nessuno ha mandato di toccare oggi.
Il fatto che l'embedder usi un lock DIVERSO da questo resta un nodo aperto:
``sentence_transformers`` importa ``transformers``, quindi i due lock
proteggono in parte lo stesso import.

⚠️ NESSUN IMPORT VERO QUI: si legge il SORGENTE con l'AST. Importare davvero
torch in un test costerebbe i 13,8 s misurati oggi, e su un banco che gira in
CI sarebbe il difetto che stiamo curando.
"""
from __future__ import annotations

import ast
from pathlib import Path

import verimem

#: I moduli la cui importazione concorrente e' stata misurata fallire.
#: `sentence_transformers` e' escluso di proposito — vedi il docstring.
_PESANTI = {"torch", "transformers"}

#: Il file che DEFINISCE il lock non puo' usarlo su se' stesso.
_ESENTI = {"_import_lock.py"}


def _radice_del_modulo(nome: str | None) -> str:
    return (nome or "").split(".")[0]


def _import_pesanti(albero: ast.AST) -> set[int]:
    """Le righe dove si importa un modulo pesante, ovunque nell'albero dato."""
    righe: set[int] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Import):
            if any(_radice_del_modulo(a.name) in _PESANTI for a in nodo.names):
                righe.add(nodo.lineno)
        elif isinstance(nodo, ast.ImportFrom):
            if _radice_del_modulo(nodo.module) in _PESANTI:
                righe.add(nodo.lineno)
    return righe


def _e_il_nostro_lock(nodo: ast.With) -> bool:
    """True se questo `with` apre `lock_import()` — comunque sia importato."""
    for item in nodo.items:
        expr = item.context_expr
        if not isinstance(expr, ast.Call):
            continue
        f = expr.func
        nome = getattr(f, "id", None) or getattr(f, "attr", None)
        if nome == "lock_import":
            return True
    return False


def _scoperti(sorgente: str) -> set[int]:
    """Righe con un import pesante NON dentro un `with lock_import()`."""
    albero = ast.parse(sorgente)
    tutti = _import_pesanti(albero)
    protetti: set[int] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.With) and _e_il_nostro_lock(nodo):
            protetti |= _import_pesanti(nodo)
    return tutti - protetti


def _file_del_pacchetto() -> list[Path]:
    radice = Path(verimem.__file__).parent
    return [p for p in sorted(radice.glob("*.py")) if p.name not in _ESENTI]


def test_il_banco_riconosce_davvero_un_import_protetto():
    """CONTROLLO POSITIVO sullo strumento, e con la faccia che puo' smentirmi.

    Due sorgenti finti, identici tranne il `with`: se lo strumento non
    distinguesse il protetto dallo scoperto, la cella sotto sarebbe verde su
    qualunque codice e non misurerebbe niente. Deve dire scoperto sul primo e
    NIENTE sul secondo — se sbagliasse in un verso solo, se ne accorge.
    """
    scoperto = "def f():\n    import torch\n"
    protetto = ("def f():\n"
                "    from ._import_lock import lock_import\n"
                "    with lock_import():\n"
                "        import torch\n")
    assert _scoperti(scoperto) == {2}, _scoperti(scoperto)
    assert _scoperti(protetto) == set(), _scoperti(protetto)


def test_il_banco_guarda_davvero_dei_file():
    """CONTROLLO POSITIVO sul PERIMETRO: se la lista fosse vuota, la cella
    principale sarebbe verde per non aver guardato niente — l'assenza di
    misura letta come un verde, che su questo prodotto e' gia' costata."""
    file = _file_del_pacchetto()
    assert len(file) > 50, f"solo {len(file)} file del pacchetto: perimetro rotto"
    assert any("import torch" in p.read_text(encoding="utf-8", errors="ignore")
               or "from transformers" in p.read_text(encoding="utf-8",
                                                     errors="ignore")
               for p in file), (
        "nessun file del pacchetto importa torch/transformers: il banco sta "
        "guardando l'albero sbagliato, e direbbe «tutto a posto» comunque."
    )


def test_nessun_import_pesante_gira_fuori_dal_lock():
    """IL CUORE: chi non prende il lock non e' serializzato con chi lo prende."""
    fuori: list[str] = []
    for p in _file_del_pacchetto():
        righe = _scoperti(p.read_text(encoding="utf-8", errors="ignore"))
        fuori += [f"{p.name}:{n}" for n in sorted(righe)]

    assert fuori == [], (
        "import pesanti che NON passano da lock_import(): "
        + ", ".join(fuori)
        + ".\nUn lock serializza solo chi lo prende: finche' uno di questi "
        "gira su un thread mentre un altro import e' in corso, la corsa "
        "misurata il 06/09 (0 giri su 3) e l'08/09 (moat_judge_failed 3/3) "
        "resta aperta. Il lock va SOLO attorno all'import — mai attorno al "
        "caricamento dei pesi, che dura 19,1 s."
    )
