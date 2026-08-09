"""`hippo_recall_chain` esplode, e il suo test e' verde.

Il difetto e' lo stesso gia' curato in `reasoning.py` — `SkillLibrary.retrieve`
e' dichiarata `-> list[Skill]` (skill.py:415) e restituisce oggetti NUDI,
mentre il chiamante spacchetta coppie::

    recall_chain.py:39   recall_pairs = list(skills_store.retrieve(task, k=k_recall))
    recall_chain.py:56   for sk, score in recall_pairs:
                         -> TypeError: cannot unpack non-iterable Skill object

Il `for` sta FUORI dal `try` che avvolge la chiamata, quindi l'errore esce dal
tool. La cura esisteva gia' nel repo: `_appaia` (reasoning.py:30), scritta il
giorno prima per l'identico difetto su `hippo_reason`, che l'audit di
produzione misurava a 6 chiamate e 5 exception. E' stata applicata a UN call
site e non all'altro — l'unico altro che spacchetta quella superficie in tutto
il repo (`mcp_server`, `sleep`, `wake` la usano come lista di Skill e stanno
bene).

PERCHE' IL PRESIDIO NON HA PRESIDIATO. `tests/test_recall_chain.py` esiste ed
e' verde, ma prova un `_FakeSkillsStore` la cui `retrieve` restituisce
``scored[:k]``, cioe' COPPIE ``(Skill, float)``. Il doppio e' stato scritto
sull'aspettativa del CHIAMANTE invece che sul comportamento del FORNITORE, e
non c'e' modo di accorgersene finche' qualcuno non prova quello vero: un test
verde su un mondo che non esiste.

E c'e' una seconda ragione per cui poteva restare invisibile: il `for` non
gira sulla lista vuota. Uno store senza skill fa passare il tool; il corpus di
Aurelio ne ha 325.

Questo file usa la `SkillLibrary` VERA, senza doppi. E' l'unico modo di
inchiodare un difetto che nasce proprio dalla distanza fra il doppio e il
vero.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.recall_chain import recall_chain
from verimem.skill import Skill, SkillLibrary


class _Episodio:
    def __init__(self, usate): self.skills_used = list(usate)


class _MemoriaVera:
    """Non c'e' un doppio da sbagliare qui: `all(limit=...)` e' tutto cio' che
    `recall_chain` chiede alla memoria, e restituisce oggetti con
    `skills_used`, come gli episodi veri."""
    def __init__(self, eps): self._eps = eps
    def all(self, limit=None): return list(self._eps)


class _Agente:
    def __init__(self, skills, memoria):
        self.skills, self.memory = skills, memoria


@pytest.fixture()
def libreria(tmp_path: Path) -> SkillLibrary:
    lib = SkillLibrary(dir_path=tmp_path / "skills_dir",
                       db_path=tmp_path / "skills_index.db")
    for sid, nome in (("s-deploy", "deploy the release"),
                      ("s-rollback", "rollback the release")):
        lib.store(Skill(id=sid, name=nome, trigger="release",
                        status="promoted"))
    return lib


def test_il_tool_risponde_con_la_libreria_VERA(libreria):
    """Il difetto: `cannot unpack non-iterable Skill object`, sul percorso
    normale del tool."""
    agente = _Agente(libreria, _MemoriaVera(
        [_Episodio(["s-deploy", "s-rollback"])] * 3))
    out = recall_chain(task="deploy the release", agent=agente)
    assert isinstance(out, dict), out
    assert "recalls" in out, sorted(out)


def test_lo_score_che_nessuno_ha_misurato_esce_None(libreria):
    """La superficie vera non ha uno score da dare. Metterci 0.0 lo farebbe
    uscire dal tool indistinguibile da un punteggio misurato — la stessa
    classe di difetto per cui `_appaia` fu scritta, e la ragione per cui
    normalizza a None."""
    agente = _Agente(libreria, _MemoriaVera([_Episodio(["s-deploy"])]))
    out = recall_chain(task="deploy the release", agent=agente)
    for r in out.get("recalls", []):
        assert r.get("score") is None, (
            f"score inventato: {r.get('score')!r} — nessuno l'ha misurato")


def test_una_superficie_che_torna_gia_le_coppie_continua_a_funzionare():
    """Controprova: normalizzare non deve rompere chi era gia' a posto —
    ed e' la forma che il vecchio doppio prometteva."""
    class _Sk:
        def __init__(self, sid): self.id, self.name = sid, sid
    class _StoreCoppie:
        def retrieve(self, task, k=3, **kw): return [(_Sk("a"), 0.91)]

    out = recall_chain(task="x", agent=_Agente(_StoreCoppie(),
                                               _MemoriaVera([])))
    assert out["recalls"][0]["score"] == 0.91, out


def test_uno_store_vuoto_non_e_una_prova(libreria, tmp_path):
    """Inchioda il motivo per cui il difetto poteva restare invisibile: sulla
    lista vuota il ciclo non gira e QUALUNQUE versione del codice passa.
    Se un giorno questo file venisse ridotto al solo caso vuoto, tornerebbe
    verde su un prodotto rotto."""
    vuota = SkillLibrary(dir_path=tmp_path / "vuota_dir",
                         db_path=tmp_path / "vuota.db")
    out = recall_chain(task="qualsiasi", agent=_Agente(vuota,
                                                       _MemoriaVera([])))
    assert out["recalls"] == [], out
    assert libreria.retrieve("deploy the release", k=2), (
        "presupposto: la libreria piena deve restituire qualcosa, altrimenti "
        "anche i test qui sopra girerebbero a vuoto")
