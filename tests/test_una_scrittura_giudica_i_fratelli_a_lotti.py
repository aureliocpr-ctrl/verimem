"""Una scrittura giudica i fratelli in UN lotto, non uno alla volta.

DA DOVE VIENE (29/09, cura 7 del mandato: «scritture lente coi fratelli»). Con il
calcolo del modello finto e tutto il resto vero, sulle scritture della matrice
multilingue la stessa scrittura consulta i giudici una volta PER FRATELLO:

    L3 semantico   detect_semantic_conflicts   una judge.classify per fratello
                   (semantic_conflict.py)       sopra il coseno, fino a 200
    L3 lessicale   validate_claim ->            un CE score() per candidato con
                   _giudice_contraddice         lo stesso soggetto, fino a 30

Ogni chiamata e' un passaggio del modello, in fila. Il 28/09 una scrittura su un
topic con 224 fatti simili costava oltre 2,2 s. I verdetti non dipendono
dall'ordine ne' dal lotto: `LocalRelationJudge.classify_batch` decide ogni
coppia nei due versi come `classify`. Quindi il lotto e' la stessa risposta,
pagata una volta.

Questo file chiede due cose e le misura dove il prodotto chiama:
  1. la funzione di L3 usa il lotto quando il giudice lo sa fare, con gli STESSI
     avvisi; il giudice senza lotto continua a funzionare coppia per coppia;
  2. alla porta `Memory.add`, una scrittura con fratelli simili fa al piu' UNA
     chiamata al giudice NLI e al piu' DUE al giudice CE (il moat L4 e il lotto
     di L3). Il controllo positivo: il moat L4 deve essere stato chiamato,
     altrimenti il conteggio non vede niente.
Nessun modello: giudici finti che contano le chiamate.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem import local_grounding, local_relation
from verimem.semantic_conflict import Relation, detect_semantic_conflicts


def _regola(a: str, b: str) -> Relation:
    """Verdetto finto e deterministico: due frasi discordano se una dice 90."""
    return Relation.CONTRADICTION if ("90" in a) != ("90" in b) else Relation.NEUTRAL


class _GiudiceConLotto:
    def __init__(self) -> None:
        self.singole = 0
        self.lotti = 0

    def classify(self, a: str, b: str) -> Relation:
        self.singole += 1
        return _regola(a, b)

    def classify_batch(self, pairs):
        self.lotti += 1
        return [_regola(a, b) for a, b in pairs]


class _GiudiceSenzaLotto:
    def __init__(self) -> None:
        self.singole = 0

    def classify(self, a: str, b: str) -> Relation:
        self.singole += 1
        return _regola(a, b)


def _fratelli():
    testi = [f"Clause s{i} allows termination with 30 days notice." for i in range(5)]
    testi.append("Clause s5 allows termination with 90 days notice.")
    return [SimpleNamespace(id=f"f{i}", proposition=t, topic="t", created_at=float(i))
            for i, t in enumerate(testi)]


def _nuovo():
    return SimpleNamespace(id="__candidate__", proposition="Clause s9 allows termination with 30 days notice.",
                           topic="t", created_at=99.0)


def _avvisi(ws):
    return sorted((w.kind, w.other_fact_id) for w in ws)


def test_L3_giudica_i_fratelli_in_un_lotto_solo_con_gli_stessi_avvisi():
    atteso = _avvisi(detect_semantic_conflicts(_nuovo(), _fratelli(), _GiudiceSenzaLotto(),
                                               cosine_fn=lambda a, b: 1.0))
    assert atteso == [("semantic_conflict", "f5")], atteso  # la regola finta accende un solo fratello

    g = _GiudiceConLotto()
    avvisi = _avvisi(detect_semantic_conflicts(_nuovo(), _fratelli(), g, cosine_fn=lambda a, b: 1.0))

    assert avvisi == atteso, "il lotto deve dare gli STESSI avvisi della coppia per coppia"
    assert (g.lotti, g.singole) == (1, 0), (
        f"6 fratelli sopra il coseno: il giudice e' stato chiamato {g.singole} volte una coppia "
        f"alla volta e {g.lotti} volte a lotto. Ogni chiamata e' un passaggio del modello in fila: "
        "con un giudice che sa fare il lotto se ne chiede UNO.")


def test_L3_un_giudice_senza_lotto_continua_coppia_per_coppia():
    g = _GiudiceSenzaLotto()
    avvisi = _avvisi(detect_semantic_conflicts(_nuovo(), _fratelli(), g, cosine_fn=lambda a, b: 1.0))
    assert avvisi == [("semantic_conflict", "f5")]
    assert g.singole == 6


@pytest.fixture
def giudici_finti(monkeypatch):
    conta = {"nli": 0, "ce": 0, "verdetto": "ok"}

    def classificatore(pairs):
        conta["nli"] += 1
        return [{"contradiction": 0.01, "entailment": 0.01, "neutral": 0.98} for _ in pairs]

    def scorer(pairs):
        conta["ce"] += 1
        return [95.0 if conta["verdetto"] == "ok" else 3.0 for _ in pairs]

    monkeypatch.setattr(local_grounding.get_local_judge(), "_scorer", scorer)
    local_relation.set_local_relation_judge(local_relation.LocalRelationJudge(classifier=classificatore))
    try:
        yield conta
    finally:
        local_relation.set_local_relation_judge(None)


def test_alla_porta_una_scrittura_con_fratelli_simili_consulta_i_giudici_a_lotti(tmp_path, giudici_finti):
    from benchmark.moat_multilingual_matrix import CASES
    from verimem import Memory

    m = Memory(str(tmp_path / "m.db"))
    stats: dict = {}
    for r in range(3):
        for lang, src_t, ok_t, bad_t, (x, y), kind in CASES:
            s = f"{lang.lower()}{r}{len(stats)}"
            stats.setdefault((lang, kind), 1)
            src = src_t.format(s=s, x=x)
            giudici_finti["verdetto"] = "ok"
            m.add(ok_t.format(s=s, x=x), source=src)
            giudici_finti["verdetto"] = "bad"
            m.add(bad_t.format(s=s, y=y), source=src)

    lang, src_t, ok_t, _bad, (x, _y), _k = CASES[0]
    s = f"{lang.lower()}3x"
    giudici_finti.update(nli=0, ce=0, verdetto="ok")
    esito = m.add(ok_t.format(s=s, x=x), source=src_t.format(s=s, x=x))

    assert giudici_finti["ce"] >= 1, (
        "CONTROLLO POSITIVO: il moat L4 non ha chiamato il giudice CE, quindi questo conteggio "
        f"non vede niente (esito {esito.get('status')!r})")
    assert giudici_finti["nli"] <= 1 and giudici_finti["ce"] <= 2, (
        f"una scrittura con 3 fratelli simili ha chiamato il giudice NLI {giudici_finti['nli']} "
        f"volte e il giudice CE {giudici_finti['ce']} volte: al piu' 1 NLI (il lotto di L3) e 2 CE "
        "(il moat L4 e il lotto di validate_claim). Ogni chiamata in piu' e' un passaggio del "
        "modello in fila, e con 200 fratelli sono 200.")
