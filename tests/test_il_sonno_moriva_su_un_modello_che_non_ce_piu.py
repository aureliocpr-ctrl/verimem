"""Il ciclo di sonno moriva su un vettore di un modello che non c'è più.

IL CRASH, isolato da ws1 eseguendo il sonno su una copia (referto 7)::

    File "verimem/skill.py", line 726, in decay_idle_embeddings
        new = (1.0 - rate) * current + rate * anchor
    ValueError: operands could not be broadcast together with shapes (384,) (768,)

Misurato sul corpus vivo, e i due conti tornano da strade diverse::

    FILE   ~/.engram/skills/*.json   41 con learned_embedding: 37 a 384 · 4 a 768
    INDICE skills_index.db           324 su 324 a 3072 byte = 768 float
    non-retired con dimensione sbagliata: 9   ← bastano queste

🔑 LA GUARDIA ESISTE GIÀ, TRENTA RIGHE PIÙ SU NELLO STESSO FILE (`skill.py:305`)::

    # Reuse the persisted learned_embedding ONLY if its dimension matches the
    # ACTIVE model … On a dim mismatch (or no vector) re-encode
    if skill.learned_embedding is not None and (
        len(skill.learned_embedding) * 4 == embedding.expected_embedding_bytes()
    ):

`decay_idle_embeddings` non ce l'ha, e non è sola: `cli.py:2051`,
`selection.py:97`, `code.py:523`, `dashboard_routes/skills.py:65` leggono lo
stesso campo senza controllarne la lunghezza. **Uno su sei ce l'ha.** È la
classe ② — «la cura c'era e mancava lo sweep» — per la sesta volta in due
giorni, e per questo il criterio diventa UNA funzione invece di una sesta copia.

⚠️ E LA CAUSA PER CUI I FILE NON CONVERGONO MAI, che il referto constatava senza
spiegarla: `store()` calcola `emb` col modello attivo e lo mette nell'INDICE, ma
scrive il file con `skill.to_dict()` — cioè col `learned_embedding` ORIGINALE.
Non è una migrazione incompleta: **ogni scrittura sana l'indice e ri-scrive il
file rotto.**

⚠️ COSA COSTA, ed è il motivo per cui non è un crash qualsiasi: il sonno fa
tutto il lavoro e muore all'ULTIMO stadio. Nel giro misurato da ws1 aveva già
prodotto 1 skill NREM, 2 REM, 3 merge, 1 schema e 2 prompt — e chi lo lanciava
vedeva solo il traceback. Un tier fermo che sembra non partire, mentre in realtà
non riesce a finire.
"""
from __future__ import annotations

import numpy as np
import pytest

from verimem import embedding
from verimem.config import CONFIG


@pytest.fixture()
def store(tmp_path):
    from verimem.skill import SkillLibrary
    return SkillLibrary(dir_path=tmp_path / "skills_dir",
                        db_path=tmp_path / "skills_index.db")


def _skill_con_vettore(store, dims: int, *, idle: bool = True):
    """Una skill non-retired, inattiva da tanto, con un vettore di `dims`.

    ⚠️ Il vettore si riscrive sul FILE dopo `store()`, ed è il punto: `store()`
    ri-encoda ciò che va nell'INDICE ma serializza il file con `to_dict()`,
    cioè col vettore originale. È esattamente lo stato in cui `all()` rilegge
    le 37 skill del corpus vivo — riprodurlo altrimenti significherebbe
    misurare un caso che non esiste.
    """
    import json
    import time

    from verimem.skill import Skill
    s = Skill(id=f"s{dims}", name="Skill di prova",
              trigger="quando serve una prova", status="candidate")
    s.learned_embedding = [0.1] * dims
    s.last_used_at = (time.time() - CONFIG.hebbian_decay_after_s * 3
                      if idle else time.time())
    store.store(s)
    p = store.dir / f"{s.id}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["learned_embedding"] = [0.1] * dims
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    store._skills_cache = None          # rileggi dal file, non dalla cache
    return s


def test_il_sonno_non_muore_su_un_vettore_di_un_modello_morto(store):
    """IL CUORE: una sola skill con un vettore della dimensione sbagliata
    faceva saltare l'INTERO ciclo, dopo che il lavoro era già stato fatto."""
    attesi = embedding.expected_embedding_bytes() // 4
    sbagliata = 384 if attesi != 384 else 768
    _skill_con_vettore(store, sbagliata)
    store.decay_idle_embeddings()          # non deve alzare ValueError


def test_e_il_vettore_incompatibile_viene_SCARTATO(store):
    """La semantica giusta è già quella che il codice prevede tre righe dopo:
    «drop learned_embedding entirely so retrieval falls back to canonical». Un
    vettore di un modello che non esiste più **è** un vettore che non serve."""
    attesi = embedding.expected_embedding_bytes() // 4
    sbagliata = 384 if attesi != 384 else 768
    s = _skill_con_vettore(store, sbagliata)
    store.decay_idle_embeddings()
    dopo = store.get(s.id)
    assert dopo is not None
    assert (dopo.learned_embedding is None
            or len(dopo.learned_embedding) == attesi), (
        f"vettore incompatibile ancora sul file: "
        f"{len(dopo.learned_embedding or [])} dimensioni")


def test_CONTROLLO_POSITIVO_un_vettore_BUONO_decade_ancora(store):
    """⚠️ IL PRESIDIO: il decadimento hebbiano è la funzione, non l'ostacolo.
    Se scartassi anche i vettori buoni avrei spento il meccanismo invece di
    curare il crash — e il test passerebbe lo stesso, perché «non alza» è
    soddisfatto anche da un ciclo che non fa niente."""
    attesi = embedding.expected_embedding_bytes() // 4
    s = _skill_con_vettore(store, attesi)
    prima = list(s.learned_embedding or [])
    n = store.decay_idle_embeddings()
    dopo = store.get(s.id)
    assert n >= 1, "nessuna skill è decaduta: il meccanismo è spento"
    cambiato = (dopo.learned_embedding is None
                or list(dopo.learned_embedding) != prima)
    assert cambiato, "il vettore buono non è stato toccato: decay inerte"


def test_il_criterio_di_compatibilita_e_UNA_superficie_sola():
    """La sesta copia non nasce qui. Il criterio `len(v)*4 == expected_bytes()`
    era scritto a mano in `skill.py:305` e mancava in altri cinque consumatori
    (`decay_idle_embeddings`, `cli.py`, `selection.py`, `code.py`,
    `dashboard_routes/skills.py`): ora è una funzione, e chi la importa non può
    scriverla diversa."""
    attesi = embedding.expected_embedding_bytes() // 4
    assert embedding.vettore_compatibile([0.0] * attesi) is True
    assert embedding.vettore_compatibile([0.0] * (attesi // 2)) is False
    assert embedding.vettore_compatibile(None) is False
    assert embedding.vettore_compatibile([]) is False
