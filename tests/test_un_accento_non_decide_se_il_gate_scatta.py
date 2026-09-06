"""Un accento decideva se il gate scattava.

    «La latenza è 40 ms.»   ->  quarantined (L1.19)
    «La latenza e 40 ms.»   ->  model_claim
    «La latenza: 40 ms.»    ->  quarantined
    «La latenza di 40 ms.»  ->  quarantined

Il pattern accettava `(?:è|is|of|di|=|:)` fra il nome della metrica e il
numero: l'accento c'era, la forma nuda no.

PERCHÉ CONTA PIÙ DI QUANTO SEMBRI. In log, commit message, output di programmi
e scritture automatiche l'italiano si scrive spesso senza accenti — e chi
scrive questo file ci è cascato per primo: tutti i fatti verimem del 2-3
agosto sono stati salvati con «e» al posto di «è», per abitudine di encoding.
Quelle scritture aggiravano il gate senza che nessuno lo sapesse.

LA LISTA È DI DUE, non di tredici, e il modo di contarla è la parte che vale.
Leggere il SORGENTE dei pattern dava 13 candidati con ~10 falsi positivi — non
capiva `perch[ée]`, `gi[àa]`, né i range `[a-zà-ù]`. Interrogare i pattern
COMPILATI (`p.search(con_accento)` contro `p.search(senza)`) su 238 pattern del
package ne dà **2**:

    composer._COPULA_RE                                «Il modulo è già …»
    l1_quantitative_detector._QUANT_PATTERNS[latenza]  «La latenza è 40 ms.»

Sei volte più falsi allarmi. È la stessa lezione di `app.routes` contro il grep
sul nome: il sorgente non si legge, si esegue.

⛔ `composer._COPULA_RE` NON è curato qui, ed è una scelta misurata: accettare
«e» come copula recupera un caso vero e ne rompe tre — «Rex e Fido sono cani»
diventerebbe «Rex **è** Fido». In italiano «e» è anche la congiunzione, quindi
lì l'accento non è una dimenticanza ma una disambiguazione. Serve una cura
diversa (l'articolo dopo la copula?) con la sua misura.
"""
from __future__ import annotations

import pathlib
import re
import tempfile
import unicodedata

import pytest

from verimem import Memory

#: Le forme in cui un umano o un programma scrive la stessa metrica.
LATENZA = [
    "La latenza è 40 ms.",
    "La latenza e 40 ms.",
    "La latenza: 40 ms.",
    "La latenza di 40 ms.",
]

COPERTURA = [
    "La coverage è 95%.",
    "La coverage e 95%.",
    "La coverage al 95%.",
]


@pytest.fixture()
def store():
    return Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))


@pytest.mark.parametrize("claim", LATENZA)
def test_l_accento_non_cambia_il_verdetto_sulla_latenza(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}: scrivere «e» invece di "
        f"«è» non cambia che sia una metrica asserita senza evidenza")


@pytest.mark.parametrize("claim", COPERTURA)
def test_ne_sulla_copertura(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}")


def test_una_metrica_CON_evidenza_passa(store):
    """Il gate non diventa un muro: la stessa metrica con la sua prova entra."""
    r = store.add("La latenza e 40 ms.", topic="lav",
                  verified_by=["commit:abc123def", "bench:latency_PASS"])
    assert r.get("status") != "quarantined", r.get("warnings")


def test_nessun_ALTRO_pattern_del_package_dipende_dall_accento():
    """IL CRICCHETTO, e usa il metodo giusto: interroga i pattern COMPILATI.

    Se un domani nasce un pattern italiano che accetta solo la forma
    accentata, questo cade — senza i ~10 falsi positivi che la lettura del
    sorgente produceva.

    `composer._COPULA_RE` è l'eccezione dichiarata: là l'accento distingue la
    copula dalla congiunzione, e toglierlo romperebbe tre casi per salvarne
    uno."""
    import importlib
    import pkgutil

    import verimem

    def nuda(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", s)
                       if unicodedata.category(c) != "Mn")

    FRASI = ["La latenza è 40 ms.", "La coverage è 95%.",
             "Il rilascio sarà completato.", "La metà dei casi è passata."]
    # `subject_extract._VERB_MARK` (aggiunto il 2026-08-26 da ws4): stessa
    # ragione di `_COPULA_RE` qui sopra, misurata. L'elenco dei marcatori di
    # verbo contiene `è|sono|era` accentati; accettare anche la `e` nuda e'
    # gia' stato provato il 26/08 alle 19:20 e RIPORTA il difetto che la `e`
    # nuda causa — `subject_head` torna 'e' e i rossi passano da 4 a 17
    # (commit `dd904750`, revert). In italiano «e» e' anche la congiunzione:
    # li' l'accento e' disambiguazione, non dimenticanza. Il costo residuo e'
    # dichiarato: sulla forma nuda il soggetto non si trova, quindi il
    # carve-out non scatta e L1 resta veto — sbaglia in sicurezza.
    # `atomic_claims._RE_AUSILIARE` e `_RE_VERBO` (06/09, Galileo): stessa
    # ragione, e il modulo la dichiara come limite noto nel suo docstring — in
    # `decomponi()` la «e» nuda E' il separatore delle coordinate; letta come
    # verbo, un pezzo senza verbo non verrebbe piu' fuso al precedente. La
    # copula nuda vale l'1,22% del corpus (188/15.378, misurato il 06/09 alle
    # 03:40) e viene letta come congiunzione e spezzata; la forma con
    # l'apostrofo «e'» e' accettata (banco l-apostrofo-spegne-l-eredita-del-
    # soggetto), e il cricchetto qui toglie l'accento, non aggiunge l'apostrofo.
    ATTESE = {("composer", "_COPULA_RE"), ("subject_extract", "_VERB_MARK"),
              ("atomic_claims", "_RE_AUSILIARE"), ("atomic_claims", "_RE_VERBO")}

    fuori = []
    for mod in pkgutil.iter_modules(verimem.__path__):
        try:
            m = importlib.import_module("verimem." + mod.name)
        except Exception:  # noqa: BLE001
            continue
        for nome in dir(m):
            val = getattr(m, nome, None)
            pats = []
            if isinstance(val, re.Pattern):
                pats = [val]
            elif isinstance(val, list | tuple):
                for x in val:
                    if isinstance(x, re.Pattern):
                        pats.append(x)
                    elif isinstance(x, list | tuple):
                        pats += [y for y in x if isinstance(y, re.Pattern)]
            for p in pats:
                for f in FRASI:
                    if p.search(f) and not p.search(nuda(f)):
                        if (mod.name, nome) not in ATTESE:
                            fuori.append(f"{mod.name}.{nome} — «{f}»")
                        break
    assert not fuori, (
        "pattern che riconoscono la frase accentata e non quella nuda:\n  "
        + "\n  ".join(sorted(set(fuori))))
