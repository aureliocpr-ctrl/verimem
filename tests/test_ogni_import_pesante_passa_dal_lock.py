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

📌 08/09, IL SEGUITO — E L'ESCLUSIONE CHE AVEVO DICHIARATO ERA LA CAUSA.

Qui c'era scritto che ``sentence_transformers`` restava fuori dalla lista
perche' «e' l'embedder, ha il suo ``_MODEL_LOCK``, un perimetro diverso». La
cella (e) rifatta sulla cura dei tre buchi ha dato **ancora
``moat_judge_failed`` 3 su 3**: quei tre import erano una proprieta' vera e NON
la causa. La causa e' proprio l'esclusione:

    sentence_transformers  ->  transformers        (misurato: PRIMA False, DOPO True)
    embedding.py           ->  _MODEL_LOCK         (usa lock_import ZERO volte)
    local_grounding.py     ->  _import_lock._LOCK

⇒ **due lock diversi sullo stesso import**, e un lock protegge solo chi lo
prende. Il perimetro che mi ero data conteneva il difetto, e tenerlo fuori
dalla lista lo rendeva invisibile a questo file.

⚠️ NEL PRODOTTO CI SONO TRE LOCK che avvolgono import pesanti — ``_MODEL_LOCK``
(embedding), ``_RERANKER_LOCK`` (semantic) e questo. Gli altri due restano
dove sono: proteggono la COSTRUZIONE dei rispettivi modelli, che e' il loro
scopo. Cio' che cambia e' che l'import passi anche da ``lock_import``, preso e
rilasciato DENTRO di loro. L'ordine e' sempre lo stesso —
``_MODEL_LOCK``/``_RERANKER_LOCK`` fuori, ``lock_import`` dentro, mai
l'inverso — e per questo non si crea il ciclo che li farebbe aspettare a
vicenda: verificato che nessun punto tenga ``lock_import`` mentre chiede uno
degli altri due, ed e' presidiato dalla cella
``test_sotto_il_lock_ci_vanno_SOLO_import``.

⚠️ Un import scritto in un DOCSTRING non conta, e infatti
``cross_encoder_rerank.py`` ne ha uno d'esempio che questo file NON segnala:
l'AST vede il codice, il grep vedrebbe anche la prosa.

⚠️ NESSUN IMPORT VERO QUI: si legge il SORGENTE con l'AST. Importare davvero
torch in un test costerebbe i 13,8 s misurati oggi, e su un banco che gira in
CI sarebbe il difetto che stiamo curando.
"""
from __future__ import annotations

import ast
from pathlib import Path

import verimem

#: I moduli la cui importazione concorrente e' stata misurata fallire.
#: `sentence_transformers` c'e' perche' TRASCINA `transformers` (misurato
#: l'08/09): tenerlo fuori nascondeva la causa vera di T26a.
_PESANTI = {"torch", "transformers", "sentence_transformers"}

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
    """Tutti i .py del pacchetto, SOTTOCARTELLE COMPRESE.

    ⚠️ Prima era ``glob("*.py")`` — solo il primo livello — e sarebbe stato un
    perimetro che sembra completo e non lo e': un import pesante messo domani
    in ``verimem/swarm/`` o ``verimem/dashboard_routes/`` non avrebbe acceso
    niente, e questo file avrebbe continuato a dire verde. Verificato l'08/09
    che oggi nelle 31 sottocartelle non ce n'e' nessuno — cioe' la cecita' non
    stava nascondendo nulla, ma sarebbe rimasta li' ad aspettare.
    """
    radice = Path(verimem.__file__).parent
    return [p for p in sorted(radice.rglob("*.py"))
            if p.name not in _ESENTI and "__pycache__" not in p.parts]


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


def _sotto_il_lock_non_solo_import(sorgente: str) -> list[str]:
    """Righe dentro un `with lock_import()` che NON sono import."""
    albero = ast.parse(sorgente)
    fuori: list[str] = []
    for nodo in ast.walk(albero):
        if not (isinstance(nodo, ast.With) and _e_il_nostro_lock(nodo)):
            continue
        for stmt in nodo.body:
            if not isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Pass)):
                fuori.append(f"riga {stmt.lineno}: {type(stmt).__name__}")
    return fuori


def test_sotto_il_lock_ci_vanno_SOLO_import():
    """⚠️ LA REGOLA CHE VALE PIU' DI TUTTE, e adesso e' presidiata.

    ``_import_lock`` dice: «IL LOCK SI TIENE SOLO ATTORNO ALL'IMPORT, MAI
    ATTORNO AL LAVORO». Due ragioni, e la seconda e' nata oggi:

    1. i pesi del giudice sono 746 MB e 19,1 s: sotto il lock, una richiesta
       che arriva nel frattempo aspetterebbe 19 secondi;
    2. **e' cio' che rende impossibile il deadlock fra i tre lock del
       prodotto.** ``_MODEL_LOCK`` e ``_RERANKER_LOCK`` stanno FUORI e
       ``lock_import`` DENTRO; se dentro questo blocco ci finisse una CHIAMATA,
       quella chiamata potrebbe chiedere uno degli altri due mentre tiene
       questo — l'ordine inverso — e i due si aspetterebbero a vicenda. Finche'
       qui dentro ci sono solo ``import``, l'ordine inverso non e'
       esprimibile.

    Cioe' la sicurezza non e' affidata a «ho controllato i chiamanti di oggi»:
    e' affidata a una proprieta' che questa cella misura a ogni giro.
    """
    colpevoli: list[str] = []
    for p in _file_del_pacchetto():
        for r in _sotto_il_lock_non_solo_import(
                p.read_text(encoding="utf-8", errors="ignore")):
            colpevoli.append(f"{p.name} {r}")

    assert colpevoli == [], (
        "dentro un `with lock_import()` c'e' qualcosa che non e' un import: "
        + ", ".join(colpevoli)
        + ".\nUna chiamata li' dentro puo' chiedere _MODEL_LOCK o "
        "_RERANKER_LOCK mentre tiene questo lock: e' l'ordine inverso, ed e' "
        "il deadlock che oggi non esiste solo perche' qui dentro ci sono solo "
        "import. Sposta il lavoro FUORI dal blocco."
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
