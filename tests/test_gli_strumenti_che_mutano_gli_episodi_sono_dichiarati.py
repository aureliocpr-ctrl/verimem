"""T71a — l'insieme degli strumenti che mutano gli EPISODI e' dichiarato,
e cio' che il dispatch fa davvero continua a coincidere con la dichiarazione.

PERCHE' ESISTE. Fino al 2026-09-12 quell'insieme viveva solo nella prosa del
README — «the five episode-mutating tools», con l'elenco. Misurato, quel
numerale sbagliava in TRE direzioni contemporaneamente:

  · DUE dei cinque elencati non scrivono niente (`hippo_rollup_old_episodes` e
    `hippo_episode_classify` restituiscono un rapporto);
  · TRE che mutano mancavano, e uno cancella un episodio per intero
    (`hippo_forget`, «Delete one episode by id»);
  · e nessun criterio chiudeva l'insieme: per NOME da' 18 strumenti, col
    ricevitore fissato 5, leggendo a mano 6. Tre criteri, tre risposte, e
    nessun modo di dire quale fosse giusta — perche' la proprieta' non era un
    oggetto del prodotto, era una frase.

La lista era stata fatta sui NOMI: `hippo_forget` non contiene «episode» ed e'
sfuggito, mentre `rollup` e `classify` ce l'hanno e sono entrati senza la
sostanza.

🔑 IL PRESIDIO NON E' L'ELENCO, E' L'UGUAGLIANZA. Un test che ripetesse i sei
nomi non presidierebbe niente: sarebbe una seconda copia della stessa frase.
Qui l'insieme dichiarato viene confrontato con quello che il DISPATCH fa, e il
rosso arriva in DUE direzioni:

    derivato ⊃ dichiarato   qualcuno ha aggiunto uno strumento che muta gli
                            episodi e non l'ha dichiarato — il buco originale;
    derivato ⊂ dichiarato   il criterio ha smesso di vedere una forma del
                            dispatch ⇒ il presidio si accorge di essersi
                            SCOLLEGATO invece di passare verde.

Il secondo verso conta quanto il primo: uno sweep che smette di spazzare si
legge esattamente come uno pulito.

IL CRITERIO, due gambe, e in tutt'e due il RICEVITORE E' FISSATO:
  (a) il blocco `if name == "…":` chiama `a.memory.<scrittore>()`;
  (b) il blocco passa `a.memory` a una funzione di modulo, e quella chiama un
      `<scrittore>` sul parametro che l'ha ricevuto.
La gamba (b) esiste perche' `hippo_episodes_dedup` fa cosi', e la (a) da sola
non lo vedeva. Gli `<scrittore>` non sono scritti a mano: sono i metodi di
`EpisodicMemory` il cui corpo contiene un INSERT/UPDATE/DELETE.

⚠️ IL LIMITE, DICHIARATO. La gamba (b) segue UN salto. Se domani una mutazione
passasse per tre funzioni, questo test cadrebbe dal lato `⊂` — cioe' si
lamenterebbe invece di mentire, che e' il verso giusto in cui sbagliare. Prima
di pubblicare i sei sono state provate altre quattro strade e sono tutte vuote
sul codice di oggi: un alias locale (`x = a.memory`), l'AGENTE passato a un
aiutante che scrive, uno store costruito dentro il dispatch, e l'aiutante che
inoltra lo store a un secondo aiutante.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import verimem
from verimem.mcp_server import _EPISODE_MUTATING, _THIN_UNSUPPORTED_WRITES

#: La radice del pacchetto INSTALLATO, non `sys.path[0]`: in un worktree
#: quest'ultimo punta all'albero di chi ha lanciato lo script, e la confusione
#: e' gia' costata due rossi il 2026-09-10.
_PACCHETTO = Path(verimem.__file__).resolve().parent
_SQL_SCRITTURA = re.compile(
    r"\b(INSERT\s+(OR\s+\w+\s+)?INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.I)


def _albero(percorso: Path) -> ast.AST | None:
    try:
        return ast.parse(percorso.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return None


def _scrittori_di_episodi() -> set[str]:
    """I metodi di `EpisodicMemory` che scrivono, presi dal loro SQL."""
    fuori: set[str] = set()
    for f in sorted(_PACCHETTO.rglob("*.py")):
        albero = _albero(f)
        if albero is None:
            continue
        for c in ast.walk(albero):
            if not (isinstance(c, ast.ClassDef) and c.name == "EpisodicMemory"):
                continue
            for m in c.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                        isinstance(x, ast.Constant) and isinstance(x.value, str)
                        and _SQL_SCRITTURA.search(x.value) for x in ast.walk(m)):
                    fuori.add(m.name)
    return fuori


def _funzioni_del_pacchetto() -> dict[str, ast.AST]:
    fuori: dict[str, ast.AST] = {}
    for f in sorted(_PACCHETTO.rglob("*.py")):
        albero = _albero(f)
        if albero is None:
            continue
        for n in ast.walk(albero):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fuori.setdefault(n.name, n)
    return fuori


def _e_a_memory(nodo: ast.AST) -> bool:
    """E' l'espressione `a.memory`? Il ricevitore, non un nome qualsiasi."""
    return (isinstance(nodo, ast.Attribute) and nodo.attr == "memory"
            and isinstance(nodo.value, ast.Name) and nodo.value.id == "a")


def _blocchi_di_dispatch() -> dict[str, list]:
    albero = _albero(_PACCHETTO / "mcp_server.py")
    assert albero is not None, "mcp_server.py non si legge"
    fuori: dict[str, list] = {}
    for n in ast.walk(albero):
        if not isinstance(n, ast.If):
            continue
        c = n.test
        if (isinstance(c, ast.Compare) and getattr(c.left, "id", None) == "name"
                and len(c.ops) == 1 and isinstance(c.ops[0], ast.Eq)
                and isinstance(c.comparators[0], ast.Constant)
                and isinstance(c.comparators[0].value, str)):
            fuori.setdefault(c.comparators[0].value, []).extend(n.body)
    return fuori


def _prova_che_muta(corpo, scrittori, funzioni) -> str | None:
    """Il PERCORSO che prova la mutazione, o None.

    Torna la prova e non un booleano: un criterio che dice solo si'/no non si
    puo' controllare leggendolo, e il messaggio di un rosso deve dire DOVE.
    """
    passati: list[tuple[str, int]] = []
    for stmt in corpo:
        for n in ast.walk(stmt):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            if (isinstance(f, ast.Attribute) and f.attr in scrittori
                    and _e_a_memory(f.value)):
                return f"a.memory.{f.attr}()"
            nome = getattr(f, "id", None) or getattr(f, "attr", None)
            if not nome:
                continue
            for i, arg in enumerate(n.args):
                if _e_a_memory(arg):
                    passati.append((nome, i))
            for kw in n.keywords:
                if _e_a_memory(kw.value):
                    passati.append((nome, -1))
    for nome, pos in passati:
        fn = funzioni.get(nome)
        if fn is None:
            continue
        param = (fn.args.args[pos].arg
                 if 0 <= pos < len(fn.args.args) else None)
        for x in ast.walk(fn):
            if (isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
                    and x.func.attr in scrittori):
                base = getattr(x.func.value, "id", None)
                if param is None or base == param:
                    return f"{nome}(a.memory) -> {base or '?'}.{x.func.attr}()"
    return None


def _derivato() -> dict[str, str]:
    scrittori = _scrittori_di_episodi()
    assert scrittori, (
        "nessun metodo di scrittura trovato su `EpisodicMemory`: il criterio "
        "non sta misurando niente. La classe e' stata rinominata, oppure le "
        "scritture non passano piu' da SQL nel corpo del metodo. Aggiusta il "
        "criterio, non l'assert.")
    funzioni = _funzioni_del_pacchetto()
    blocchi = _blocchi_di_dispatch()
    assert len(blocchi) > 100, (
        f"solo {len(blocchi)} blocchi `if name == ...` trovati nel dispatch: "
        f"la forma del dispatch e' cambiata e questo criterio non la vede "
        f"piu'. Senza questo controllo l'insieme derivato sarebbe vuoto e il "
        f"test direbbe «nessuno muta gli episodi», che e' il modo in cui un "
        f"presidio si scollega restando verde.")
    return {t: p for t in sorted(blocchi)
            if (p := _prova_che_muta(blocchi[t], scrittori, funzioni))}


def test_l_insieme_derivato_dal_dispatch_e_quello_DICHIARATO():
    """Il presidio vero: la dichiarazione e il codice dicono la stessa cosa."""
    derivato = _derivato()
    non_dichiarati = sorted(set(derivato) - _EPISODE_MUTATING)
    spariti = sorted(_EPISODE_MUTATING - set(derivato))
    assert not non_dichiarati, (
        "STRUMENTI CHE MUTANO GLI EPISODI E NON SONO DICHIARATI: "
        + ", ".join(f"{t} ({derivato[t]})" for t in non_dichiarati)
        + ". Aggiungili a `_EPISODE_MUTATING` in mcp_server.py. E' lo stesso "
        "buco che nel 2026-09-12 aveva lasciato fuori `hippo_forget`, che "
        "cancella un episodio: un elenco tenuto a mano non cresce da solo.")
    assert not spariti, (
        "DICHIARATI E NON PIU' VISTI DAL CRITERIO: " + ", ".join(spariti)
        + ". Due letture possibili e vanno distinte PRIMA di toccare la "
        "costante: (1) lo strumento non muta piu' gli episodi, e allora va "
        "tolto dalla costante; (2) il dispatch e' stato rifattorizzato e il "
        "criterio non lo vede piu' — e allora togliere il nome dalla costante "
        "SPEGNE il presidio senza che nessuno se ne accorga. Leggi il blocco "
        "`if name == ...` di quello strumento prima di scegliere.")


def _strumenti_dichiarati() -> set[str]:
    """I nomi dei `Tool(name=…)`, dall'AST.

    Non si esegue `_list_tools_unfiltered` per averli: e' una coroutine, e
    farla girare qui aggiungerebbe un event loop a un test che deve solo
    leggere. L'AST da' la stessa cosa senza costruire niente.
    """
    albero = _albero(_PACCHETTO / "mcp_server.py")
    assert albero is not None
    fuori: set[str] = set()
    for n in ast.walk(albero):
        if not isinstance(n, ast.Call):
            continue
        if (getattr(n.func, "attr", None)
                or getattr(n.func, "id", None)) != "Tool":
            continue
        for kw in n.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                fuori.add(str(kw.value.value))
    return fuori


def test_ogni_nome_dichiarato_e_uno_strumento_CHE_ESISTE():
    """Una voce morta protegge uno strumento che non c'e' piu'."""
    nomi = _strumenti_dichiarati()
    assert len(nomi) > 200, (
        f"solo {len(nomi)} strumenti trovati: il criterio non legge piu' le "
        f"dichiarazioni, e senza questo controllo il test sotto passerebbe "
        f"dicendo che nessun nome e' un fantasma.")
    fantasmi = sorted(_EPISODE_MUTATING - nomi)
    assert not fantasmi, (
        f"`_EPISODE_MUTATING` dichiara nomi che non sono strumenti: "
        f"{fantasmi}. Una voce morta non protegge niente e fa sembrare "
        f"l'elenco piu' completo di quanto sia.")


def test_nessuno_di_loro_sta_nella_deny_list_DELLE_MUTAZIONI_SUI_FATTI():
    """Le due liste non sono intercambiabili, e confonderle rompe l'utente.

    `_THIN_UNSUPPORTED_WRITES` RIFIUTA dietro un server condiviso, perche' per
    i fatti agire sul locale sarebbe una bugia. Per gli episodi il locale e'
    la risposta GIUSTA: il server serve fatti. Mettere uno strumento episodico
    nella deny-list gli toglierebbe una funzione che deve avere.
    """
    confusi = sorted(_EPISODE_MUTATING & _THIN_UNSUPPORTED_WRITES)
    assert not confusi, (
        f"{confusi} sono dichiarati come mutatori di EPISODI e insieme "
        f"rifiutati dietro un server condiviso. Gli episodi restano locali "
        f"per disegno: o lo strumento muta i fatti (e allora esce da "
        f"`_EPISODE_MUTATING`), o e' episodico (e allora esce dalla "
        f"deny-list). Non tutt'e due.")
