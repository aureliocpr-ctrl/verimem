"""`verimem introspect` non deve morire su una skill con un `learned_embedding`
scritto da un modello di embedding diverso da quello attivo.

Terzo punto della stessa classe, trovato con lo sweep dopo la cura del sonno
(ws1, 07/08). `cli.py` legge il vettore persistito e lo passa a `cosine` senza
verificarne la forma:

    v = _np.asarray(s.learned_embedding, dtype=_np.float32)
    ...
    _emb.cosine(q, v / max(_np.linalg.norm(v), 1e-9))

Verificato: ``cosine(768, 384)`` -> ``ValueError: shapes (768,) and (384,) not
aligned``. Sul corpus reale 37 `learned_embedding` su 41 sono a 384 mentre il
modello attivo ne vuole 768, e 9 di quelli stanno su skill non-retired: basta
una di quelle perche' il comando muoia in faccia all'utente.

La guardia e' la stessa di `skill.py` (scartare il vettore inservibile e tornare
all'ancora canonica): qui manca perche' lo sweep di `skill.py` non usciva dal
file.
"""
from __future__ import annotations

import numpy as np
import pytest

from verimem import embedding


def _dim_attiva() -> int:
    return embedding.expected_embedding_bytes() // 4


def _vettore(dim: int) -> np.ndarray:
    v = np.zeros(dim, dtype=np.float32)
    v[0] = 1.0
    return v


def test_cosine_su_forme_diverse_e_il_caso_da_evitare():
    """Il fatto grezzo su cui poggia tutto il resto: sommare/moltiplicare due
    vettori di modelli diversi NON e' impreciso, e' impossibile."""
    altra = 384 if _dim_attiva() != 384 else 768
    with pytest.raises(ValueError):
        embedding.cosine(_vettore(_dim_attiva()), _vettore(altra))


def test_introspect_ignora_il_vettore_di_un_altro_modello(tmp_path, monkeypatch):
    """`introspect` deve produrre un punteggio (ricadendo sull'ancora canonica),
    non sollevare."""
    from verimem.cli import _punteggio_skill_per_introspect

    q = _vettore(_dim_attiva())
    altra = 384 if _dim_attiva() != 384 else 768

    class _SkillFinta:
        id = "vecchia"
        name = "Skill di prova"
        trigger = "quando serve"
        learned_embedding = [0.1] * altra

    punteggio = _punteggio_skill_per_introspect(_SkillFinta(), q)   # PRIMA: ValueError

    assert isinstance(punteggio, float)
    assert -1.0001 <= punteggio <= 1.0001


def test_il_vettore_della_dimensione_giusta_viene_ancora_usato(tmp_path):
    """CONTROLLO POSITIVO: se il vettore e' utilizzabile, `introspect` deve
    ancora usarlo — altrimenti una cura che ignora SEMPRE il learned_embedding
    passerebbe il test di sopra."""
    from verimem.cli import _punteggio_skill_per_introspect

    dim = _dim_attiva()
    q = _vettore(dim)

    class _Allineata:
        id = "buona"
        name = "Skill allineata"
        trigger = "quando serve"
        learned_embedding = list(_vettore(dim))       # identico alla query

    class _Ortogonale:
        id = "altra"
        name = "Skill ortogonale"
        trigger = "quando serve"
        v = _vettore(dim).copy()
        v[0] = 0.0
        v[1] = 1.0
        learned_embedding = list(v)

    assert _punteggio_skill_per_introspect(_Allineata(), q) > 0.9, (
        "il vettore appreso non viene piu' usato: la cura ha spento la funzione"
    )
    assert _punteggio_skill_per_introspect(_Ortogonale(), q) < 0.5
