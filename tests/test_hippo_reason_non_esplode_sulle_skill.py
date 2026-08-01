"""`hippo_reason` era rotto: 6 chiamate registrate, 5 finite in exception.

Reperto dell'altra istanza (in sola lettura), 2026-08-01. L'audit di produzione::

    hippo_reason: 6 chiamate, 5 esiti `exception`, 1 `rejected_empty`

e la chiamata col solo `task` risponde::

    error: TypeError: cannot unpack non-iterable Skill object

LA CAUSA, in due righe che si contraddicono a vicenda. `_safe_recall`
(reasoning.py:30) dichiara nella firma `-> list[tuple]` e nel docstring
«Returns `[(skill, score), ...]`», ma restituisce::

    return list(skills_store.retrieve(task, k=k)) or []

e `SkillLibrary.retrieve` (skill.py:415) e' dichiarata `-> list[Skill]`: oggetti
nudi, non coppie. Il chiamante si fida del contratto scritto e spacchetta::

    for s, score in recall_pairs

Non e' un caso di bordo, e' il percorso NORMALE del tool: `retrieve` e' la prima
superficie che `_safe_recall` prova, quindi il tool esplode praticamente sempre.
Le 5 exception su 6 lo dicono.

LA CURA NORMALIZZA LA FORMA, NON INVENTA IL NUMERO. Una superficie che
restituisce `Skill` nudi non ha uno score da dare, e metterci `0.0` sarebbe un
punteggio inventato che il chiamante espone come se fosse misurato — la classe
di difetto curata tutta la notte (un campo che dice piu' di quello che sa). Lo
score assente vale `None`, e il payload lo riporta `None`.

I due contratti che questo file inchioda:

* qualunque superficie di richiamo restituisca `Skill` nudi o coppie, il tool
  RISPONDE invece di sollevare;
* uno score che nessuno ha misurato esce come `None`, non come zero.
"""
from __future__ import annotations

from verimem.reasoning import _safe_recall


class _Skill:
    def __init__(self, sid, nome):
        self.id, self.name = sid, nome
        self.trigger, self.status = "t", "promoted"


class _StoreNudo:
    """Il caso reale: `SkillLibrary.retrieve -> list[Skill]`."""
    def retrieve(self, query, k=3, status=None):
        return [_Skill("a", "alfa"), _Skill("b", "beta")]


class _StoreCoppie:
    """La forma che il contratto dichiarava: gia' appaiata."""
    def retrieve(self, query, k=3, status=None):
        return [(_Skill("a", "alfa"), 0.91)]


class _Ag:
    def __init__(self, store): self.skills = store


def test_una_superficie_che_torna_skill_nude_non_fa_esplodere_il_tool():
    """Il difetto: `cannot unpack non-iterable Skill object`."""
    out = _safe_recall(_Ag(_StoreNudo()), "un compito qualunque", k=3)
    assert len(out) == 2, out
    for coppia in out:
        assert isinstance(coppia, tuple) and len(coppia) == 2, (
            f"`_safe_recall` promette [(skill, score)] e ha restituito "
            f"{type(coppia).__name__}: e' il contratto che il chiamante "
            f"spacchetta, e da cui il tool esplodeva")
    s, score = out[0]
    assert s.id == "a"
    assert score is None, (
        f"nessuno ha misurato questo score: riportarlo come {score} lo fa "
        f"sembrare un punteggio vero")


def test_una_superficie_che_torna_gia_le_coppie_non_viene_toccata():
    """Controprova: la normalizzazione non deve rompere chi era gia' a posto."""
    out = _safe_recall(_Ag(_StoreCoppie()), "un compito qualunque", k=3)
    assert out and out[0][1] == 0.91, out


def test_una_superficie_assente_o_rotta_da_lista_vuota_non_un_errore():
    """Il contratto storico della funzione — «Returns [...] or []» — resta."""
    class _Rotto:
        def retrieve(self, *a, **k): raise RuntimeError("giu'")

    assert _safe_recall(_Ag(_Rotto()), "x", k=3) == []
    assert _safe_recall(_Ag(None), "x", k=3) == []
