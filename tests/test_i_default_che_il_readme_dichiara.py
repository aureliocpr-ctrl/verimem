"""I default che il README dichiara devono essere quelli veri nel codice.

Un default documentato è una promessa fatta a chi **non** configura niente —
cioè quasi tutti. Se il README dice «balanced» e il codice parte «permissive»,
nessuno se ne accorge: non c'è errore, c'è solo un prodotto che si comporta
diversamente da come è descritto.

Misurato oggi sugli oggetti, non sul sorgente::

    README:249  preset del gate          "balanced"              ✅
    README:84   validate del preset      "full"                  ✅
    README:52   band a due soglie        accesa senza variabili  ✅
    README:56   giudice ollama           "qwen2.5:7b-instruct"   ✅
    README:368/393  bind delle porte     127.0.0.1               ✅

═══ 🔑 IL BIND SI MISURA CON UNO SWEEP, NON CON UN ELENCO ═══

L'ultima riga è di sicurezza, e ha una trappola di perimetro: il README ne parla
in **due** punti — «Personal mode binds 127.0.0.1» (riga 368) e «The gateway
binds loopback» (riga 393) — che sono due superfici distinte. Misurarne una e
concludere per entrambe è il modo in cui un controllo diventa più stretto di
quanto sia davvero.

E il rischio non sono le superfici di oggi, sono quelle di domani. Un test che
nomina `gateway_serve`, `console_cmd` e `dashboard` resta verde il giorno in cui
qualcuno aggiunge un quarto server con `host="0.0.0.0"`. Perciò qui le superfici
**si scoprono dall'AST** — ogni funzione che chiama `uvicorn.run` — e il default
di ciascuna viene risolto risalendo alla firma. Trovate oggi: tre.

⚠️ Un bind non-loopback non è vietato all'utente: `--host` esiste apposta, e il
README dice come esporsi (dietro un reverse proxy TLS). Ciò che si pretende qui
è che **il default** non lo faccia — la differenza fra scegliere di esporsi e
scoprire di esserlo.
"""
from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]

#: Gli indirizzi che NON raggiungono la rete. `0.0.0.0` e `::` sono l'opposto:
#: bindano ogni interfaccia, cioè espongono il servizio a chiunque veda la
#: macchina. È la distinzione che il presidio esiste per tenere.
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def test_IL_CRITERIO_DI_SICUREZZA_boccia_gli_indirizzi_esposti():
    """⚠️ Il banco del misuratore, PRIMO perché tutto il resto ci si appoggia.

    Se `LOOPBACK` contenesse per errore `0.0.0.0` — o se qualcuno lo allargasse
    «per far passare i test» — ogni asserzione qui sotto continuerebbe a essere
    verde mentre il prodotto si espone. Un criterio di sicurezza va falsificato
    prima di essere usato.
    """
    for esposto in ("0.0.0.0", "::", ""):
        assert esposto not in LOOPBACK, (
            f"{esposto!r} è finito fra gli indirizzi considerati sicuri: il "
            f"presidio sul bind ha smesso di distinguere loopback da esposto")


def _superfici_che_aprono_una_porta():
    """Ogni funzione della CLI che chiama ``uvicorn.run``, scoperta dall'AST.

    Restituisce `(nome, riga, host_effettivo)`. L'host è la costante passata, o
    — se è un parametro — il default di quel parametro nella firma, che è ciò
    che ottiene chi non passa `--host`.
    """
    import verimem.cli as CLI

    sorgente = (_RADICE / "verimem" / "cli.py").read_text(encoding="utf-8")
    for nodo in ast.walk(ast.parse(sorgente)):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        for n in ast.walk(nodo):
            chiamata_uvicorn = (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "run"
                and getattr(n.func.value, "id", "") == "uvicorn"
            )
            if not chiamata_uvicorn:
                continue
            for kw in n.keywords:
                if kw.arg != "host":
                    continue
                if isinstance(kw.value, ast.Constant):
                    yield nodo.name, nodo.lineno, kw.value.value
                else:
                    fn = getattr(CLI, nodo.name, None)
                    if fn is None:
                        pytest.skip(f"{nodo.name} non è esportata: sweep incompleto")
                    d = inspect.signature(fn).parameters[kw.value.id].default
                    yield nodo.name, nodo.lineno, getattr(d, "default", d)


def test_ogni_superficie_che_apre_una_porta_binda_loopback_per_default():
    """Il cuore, ed è la promessa che il README fa in due punti diversi."""
    esposte = [(nome, riga, host)
               for nome, riga, host in _superfici_che_aprono_una_porta()
               if host not in LOOPBACK]
    assert not esposte, (
        f"queste superfici bindano un indirizzo raggiungibile dalla rete senza "
        f"che nessuno l'abbia chiesto: {esposte}. Il README promette loopback "
        f"per default in due punti (Personal mode e gateway); esporsi deve "
        f"restare una scelta esplicita via --host")


def test_LO_SWEEP_TROVA_ANCORA_LE_SUPERFICI():
    """⚠️ IL VERSO OPPOSTO: se `uvicorn.run` cambiasse forma, lo sweep
    troverebbe ZERO superfici e il test sopra passerebbe a vuoto — dichiarando
    sicuro un file che non ha più guardato.
    """
    trovate = list(_superfici_che_aprono_una_porta())
    assert len(trovate) >= 3, (
        f"lo sweep trova solo {len(trovate)} superfici (erano 3): o i server "
        f"sono stati spostati fuori da cli.py, o non usano più uvicorn.run — in "
        f"entrambi i casi questo presidio ha smesso di coprirli")


def test_il_preset_di_default_e_quello_dichiarato():
    """README:249 — «Gate presets: "balanced" (default)»."""
    import verimem.client as C
    assert inspect.signature(C.Memory.__init__).parameters["preset"].default == "balanced"


def test_il_preset_di_default_valida_come_dichiarato():
    """README:84 — «the default `validate="full"`»."""
    import verimem.client as C
    mappa = next(v for v in vars(C).values()
                 if isinstance(v, dict) and isinstance(v.get("balanced"), dict))
    assert mappa["balanced"]["validate"] == "full"


def test_la_band_e_accesa_senza_variabili():
    """README:52 — «A two-threshold band (on by default…)».

    Si misura in un ambiente ripulito dalle tre grafie della variabile: il
    mirror dei prefissi le rende equivalenti, quindi toglierne una sola
    lascerebbe il test in balia dell'ambiente di chi lancia la suite.
    """
    import verimem.grounding_gate as G
    fn = next(f for f in vars(G).values()
              if inspect.isfunction(f) and "CE_BAND_ENFORCE" in inspect.getsource(f))
    salvate = {}
    for p in ("VERIMEM", "ENGRAM", "HIPPO"):
        salvate[p] = os.environ.pop(p + "_CE_BAND_ENFORCE", None)
    try:
        assert fn() is True or bool(fn()), (
            "la band non risulta accesa senza variabili: il README la dichiara "
            "on by default e reversibile con VERIMEM_CE_BAND_ENFORCE=0")
    finally:
        for p, v in salvate.items():
            if v is not None:
                os.environ[p + "_CE_BAND_ENFORCE"] = v


def test_il_giudice_ollama_e_quello_misurato():
    """README:56 — «default `qwen2.5:7b-instruct`».

    Il modello non è un dettaglio di configurazione: il README gli attribuisce
    numeri misurati (AUROC 0.858 contro 0.829 del CE). Cambiarlo senza toccare
    il documento lascerebbe quei numeri attribuiti a un modello diverso.
    """
    import verimem.band_escalation as B
    fn = next(f for f in vars(B).values()
              if inspect.isfunction(f) and "qwen2.5:7b-instruct" in inspect.getsource(f))
    assert fn() == "qwen2.5:7b-instruct"
