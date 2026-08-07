"""Il decay hebbiano non deve MORIRE su una skill che porta un `learned_embedding`
scritto da un modello di embedding diverso da quello attivo.

Trovato eseguendo il ciclo di sonno su una copia del corpus reale (ws1, 05/08):

    File "verimem/skill.py", line 726, in decay_idle_embeddings
        new = (1.0 - rate) * current + rate * anchor
    ValueError: operands could not be broadcast together with shapes (384,) (768,)

Le due viste del tier dicevano cose diverse: l'INDICE aveva tutte le 324 skill a
768 float col modello attivo, mentre nei FILE JSON 37 `learned_embedding` su 41
erano rimasti a 384 (il modello precedente). La migrazione ha ri-encodato
l'indice e ha lasciato i file.

Il vettore vecchio non e' recuperabile — vive in un altro spazio — quindi la cura
e' SCARTARLO e ripartire dall'ancora canonica, che e' esattamente cio' che
``store()`` fa gia' per il ``trigger_embedding`` (skill.py, ramo
``len(...) * 4 == expected_embedding_bytes()``): qui il controllo mancava.

Conseguenza del difetto: il crash e' nell'ULTIMO stadio del ciclo, quindi il
sonno faceva tutto il lavoro (sintesi, merge, schema) e poi moriva — chi lo
lanciava vedeva solo il traceback.
"""
from __future__ import annotations

import numpy as np
import pytest

from verimem import embedding
from verimem.config import CONFIG
from verimem.skill import Skill, SkillLibrary


@pytest.fixture()
def lib(tmp_path):
    return SkillLibrary(dir_path=tmp_path / "skills",
                        db_path=tmp_path / "skills_index.db")


def _dim_attiva() -> int:
    return embedding.expected_embedding_bytes() // 4


def _skill_ferma_da_tempo(dim: int, sid: str = "vecchia") -> Skill:
    """Una skill idonea al decay: non ritirata, con learned_embedding, ferma."""
    s = Skill(id=sid, version=1, name="Skill di prova",
              trigger="quando serve la prova", body="corpo")
    s.learned_embedding = [0.1] * dim
    s.last_used_at = 1.0                      # usata una volta, tantissimo tempo fa
    return s


def test_decay_non_esplode_su_vettore_di_dimensione_diversa(lib):
    dim_altra = 384 if _dim_attiva() != 384 else 768
    lib.store(_skill_ferma_da_tempo(dim_altra))

    n = lib.decay_idle_embeddings()            # PRIMA: ValueError (384,) vs (768,)

    assert n >= 0
    dopo = lib.get("vecchia")
    assert dopo is not None
    # il vettore inservibile e' stato scartato, non sommato
    assert (dopo.learned_embedding is None
            or len(dopo.learned_embedding) == _dim_attiva())


def test_una_skill_incompatibile_non_ferma_le_altre(lib):
    """Il caso che uccideva il ciclo: basta UNA riga vecchia per far saltare
    l'intero stadio, e con esso il sonno."""
    dim_altra = 384 if _dim_attiva() != 384 else 768
    lib.store(_skill_ferma_da_tempo(dim_altra, sid="rotta"))
    lib.store(_skill_ferma_da_tempo(_dim_attiva(), sid="sana"))

    lib.decay_idle_embeddings()                # non deve sollevare

    sana = lib.get("sana")
    assert sana.learned_embedding is None or len(sana.learned_embedding) == _dim_attiva()


def test_il_vettore_della_dimensione_giusta_viene_ancora_decaduto(lib):
    """CONTROLLO POSITIVO (la regola di ws5): accanto al caso che deve NON
    esplodere, uno che deve ancora FUNZIONARE — altrimenti una cura che
    disattiva il decay passerebbe il test di sopra."""
    dim = _dim_attiva()
    s = _skill_ferma_da_tempo(dim, sid="normale")
    prima = list(s.learned_embedding)
    lib.store(s)

    n = lib.decay_idle_embeddings()

    assert n == 1, "una skill idonea DEVE essere decaduta"
    dopo = lib.get("normale")
    cambiato = (dopo.learned_embedding is None
                or not np.allclose(dopo.learned_embedding, prima))
    assert cambiato, "il decay non ha toccato il vettore: la cura ha spento la funzione"
