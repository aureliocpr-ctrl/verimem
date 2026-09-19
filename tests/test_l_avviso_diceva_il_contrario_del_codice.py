"""L'avviso dichiarava di isolare, e il prodotto scriveva in produzione.

Con le due variabili poste su percorsi diversi — che è la situazione NORMALE
sulla macchina di chi sviluppa, dove `ENGRAM_DATA_DIR` sta nell'ambiente in modo
permanente — il prodotto stampa:

    RuntimeWarning: DATA_DIR aliases disagree: HIPPO_DATA_DIR=C:\\tmp\\isolato,
    ENGRAM_DATA_DIR=C:\\Users\\aurel\\.engram — using C:\\tmp\\isolato
    (HIPPO_DATA_DIR wins, it is the explicit isolation handle)

e poi scrive in ``C:\\Users\\aurel\\.engram``. Misurato il 2026-08-04: il
conteggio dei fatti nel corpus di produzione è passato da 7178 a 7179 mentre
`HIPPO_DATA_DIR` puntava a una directory temporanea.

PEGGIO DEL SILENZIO. Un avviso che sceglie in silenzio lascia il dubbio; uno che
annuncia la scelta GIUSTA mentre il codice fa quella sbagliata rassicura. Chi lo
legge conclude di essere isolato, e non lo è.

LA CAUSA, e la regola era già scritta. `_compat._ALIAS_DATA_DIR` mette
`HIPPO_DATA_DIR` per primo, e `config.py` dice anche perché:

    ``HIPPO_DATA_DIR`` is checked FIRST (not ENGRAM_DATA_DIR) deliberately: it
    is the explicit isolation handle […] ``ENGRAM_DATA_DIR`` (the maintainer's
    → ~/.engram) must not override a test's explicit ``HIPPO_DATA_DIR``.

Quattro punti del prodotto leggono gli alias con un ordine PROPRIO, e invertito:

    cli._facts_data_dir              for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR")
    auto_dream_worker._resolve_…     ENGRAM_DATA_DIR or HIPPO_DATA_DIR
    hooks.pre_tool_use               for env_key in ("ENGRAM_DATA_DIR", …)
    mcp_server (hippo_briefing_stats) ENGRAM_DATA_DIR or HIPPO_DATA_DIR

cioè fanno esattamente ciò che la documentazione dice che NON deve succedere: la
variabile del manutentore sovrascrive l'isolamento esplicito di un test. Ed è il
meccanismo che produce il risultato già misurato il 2026-07-30 — **9,5 GB su
12,3 in 284 snapshot con 'pytest' nel nome dentro lo store di produzione**: la
suite crede di essere isolata e scrive dove vive la memoria.

È il finding F17 dell'altra istanza («due risolutori con precedenza opposta»),
dichiarato curato il 2026-07-30 unificando su `_compat._env_data_dir`. La cura
era giusta e INCOMPLETA: quattro chiamanti hanno mantenuto il loro loop, e
l'avviso aggiunto dalla stessa cura ha reso il residuo più difficile da vedere.
Non l'ho preso per buono da loro né come difetto né come cura: entrambi
misurati qui contro il prodotto.

L'ultimo test non elenca i chiamanti, li SCOPRE dall'AST — perché elencarli è il
motivo per cui questi quattro erano sopravvissuti a una cura che li nominava.
"""
from __future__ import annotations

import ast
import pathlib

import pytest


#: ⚠️ I PERCORSI SI COSTRUISCONO, NON SI SCRIVONO. La prima stesura usava
#: `C:\tmp\isolato`, e su Linux `Path(r"C:\tmp\isolato").resolve()` diventa
#: `/home/runner/work/verimem/verimem/C:\tmp\isolato` — relativo alla cwd. In
#: locale verde, in CI rosso su tutti e sei i job. È la terza volta in tre
#: giorni che un mio test misura l'AMBIENTE invece del prodotto, e stavolta
#: l'ambiente era il sistema operativo.
@pytest.fixture()
def dirs(tmp_path):
    isolato = tmp_path / "isolamento_esplicito"
    produzione = tmp_path / "finta_produzione_del_manutentore"
    isolato.mkdir()
    produzione.mkdir()
    return isolato, produzione


@pytest.fixture(autouse=True)
def _alias_discordi(monkeypatch: pytest.MonkeyPatch, dirs):
    """La situazione normale di chi sviluppa: la variabile del manutentore c'è
    già, e il test ne aggiunge una esplicita per isolarsi."""
    isolato, produzione = dirs
    monkeypatch.setenv("HIPPO_DATA_DIR", str(isolato))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(produzione))
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)


def test_la_CLI_onora_l_isolamento_esplicito(dirs):
    """`facts add` e ogni comando che passa da qui: è il canale con cui si
    carica un corpus, quindi è quello che può sporcare di più."""
    isolato, _ = dirs
    from verimem.cli import _facts_data_dir
    scelto = pathlib.Path(_facts_data_dir()).resolve()
    assert scelto == isolato.resolve(), (
        f"la CLI ha scelto {scelto} invece di {isolato}: la variabile del "
        f"manutentore ha sovrascritto l'isolamento esplicito, che è "
        f"esattamente ciò che config.py dice di non fare")


def test_il_worker_dei_sogni_onora_l_isolamento_esplicito(dirs):
    """Gira in background e scrive: se non è isolato, sporca durante la suite."""
    isolato, _ = dirs
    from verimem.auto_dream_worker import _resolve_engram_dir
    assert pathlib.Path(_resolve_engram_dir()).resolve() == isolato.resolve(), (
        f"il worker ha scelto {_resolve_engram_dir()}")


def test_quello_che_l_avviso_ANNUNCIA_e_quello_che_il_codice_USA():
    """Il cuore del difetto: la coerenza fra ciò che il prodotto dichiara di
    fare e ciò che fa. Un avviso che annuncia la scelta giusta mentre il codice
    fa quella sbagliata è peggio del silenzio."""
    from verimem import _compat
    from verimem.cli import _facts_data_dir
    annunciato = pathlib.Path(_compat._env_data_dir()).expanduser().resolve()
    usato = pathlib.Path(_facts_data_dir()).expanduser().resolve()
    assert annunciato == usato, (
        f"l'avviso dichiara di usare {annunciato} e il codice usa {usato}: chi "
        f"legge l'avviso conclude di essere isolato e non lo è")


def test_NESSUN_modulo_risolve_gli_alias_per_conto_proprio():
    """IL CRICCHETTO, e scopre invece di elencare.

    Un modulo che legge `ENGRAM_DATA_DIR`/`HIPPO_DATA_DIR` da sé ha una propria
    idea della precedenza, e prima o poi è quella sbagliata. L'unico posto che
    può leggerli è `_compat`, che è il risolutore, più `config` che lo delega.

    Si legge l'AST e non il testo: guardare il testo accenderebbe su ogni
    commento e ogni docstring che le nomina — e qui i commenti che le nominano
    sono parecchi, proprio perché il difetto è già stato pagato una volta.

    ⚠️ LA PRIMA STESURA DI QUESTO CRICCHETTO AVEVA IL BUCO CHE CERCAVA. Guardava
    solo `os.environ.get("X")` con la chiave costante, e `hooks/pre_tool_use`
    scorreva ``for env_key in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR")`` — chiave
    in una variabile, invisibile. Un presidio che vede quattro colpevoli su
    cinque è esattamente la forma che questo file documenta. Ora si guarda ogni
    occorrenza LETTERALE degli alias, ovunque compaia: dentro una tupla, un
    dizionario, una lista o una chiamata. Le docstring restano fuori perché
    sono l'unico `Constant` che non è codice."""
    RADICE = pathlib.Path("verimem")
    ALIAS = {"ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"}
    ESENTI = {"_compat.py", "config.py"}

    colpevoli: list[str] = []
    for f in RADICE.rglob("*.py"):
        if f.name in ESENTI:
            continue
        try:
            albero = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        # Le stringhe che stanno da sole come istruzione sono docstring (o
        # commenti scritti come stringa): non sono un accesso all'ambiente.
        prosa = {id(n.value) for n in ast.walk(albero)
                 if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
        for nodo in ast.walk(albero):
            if (isinstance(nodo, ast.Constant)
                    and isinstance(nodo.value, str)
                    and nodo.value in ALIAS
                    and id(nodo) not in prosa):
                colpevoli.append(
                    f"{f.as_posix()}:{nodo.lineno} nomina {nodo.value} nel codice")

    assert not colpevoli, (
        "questi punti hanno una propria idea di quale alias vince, e il "
        "prodotto ne ha già una dichiarata (HIPPO_DATA_DIR per primo, perché è "
        "l'appiglio esplicito di isolamento):\n  "
        + "\n  ".join(sorted(set(colpevoli)))
        + "\ndelega a `_compat._env_data_dir()` invece di rileggere l'ambiente")
