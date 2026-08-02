"""Il ritiro arrivava al file e non all'indice.

`SkillLibrary.store` scriveva in quest'ordine:

    1. il JSON su disco
    2. `embedding.encode(...)`      <-- la riga fallibile
    3. la riga nell'indice SQLite

`encode` è la sola parte di questo metodo che può non rispondere — budget
scaduto, daemon dell'embedding giù, cold load da decine di secondi — e quando
solleva, il file è già quello NUOVO e l'indice è rimasto VECCHIO. Il chiamante
vede un'eccezione e conclude «lo store è fallito»; metà scrittura invece è
passata.

Misurato dall'altra istanza sul corpus vivo: **159 skill su 324** hanno due
status, tutte `file=retired` / `indice=candidate` — è il RITIRO a non arrivare
in fondo. E `retrieve()` interroga l'INDICE, quindi
`retrieve(status="candidate")` restituiva **10 skill su 10** già ritirate nei
file: la libreria pescava skill morte.

La cura è l'ordine: l'encode PRIMA di qualunque scrittura. Se non risponde,
non è stato scritto niente — né il file né l'indice — e «lo store è fallito»
torna a essere vero.
"""
from __future__ import annotations

import json

import pytest

from verimem import embedding as emb_mod
from verimem.skill import Skill, SkillLibrary


@pytest.fixture()
def libreria(tmp_path):
    return SkillLibrary(dir_path=tmp_path / "sk", db_path=tmp_path / "sk.db")


def _stato_su_file(lib: SkillLibrary, sid: str) -> str | None:
    p = lib._path(sid)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("status")


def _stato_su_indice(lib: SkillLibrary, sid: str) -> str | None:
    import sqlite3
    con = sqlite3.connect(str(lib.db_path))
    try:
        r = con.execute("SELECT status FROM skills WHERE id = ?",
                        (sid,)).fetchone()
    finally:
        con.close()
    return r[0] if r else None


def test_un_encode_che_non_risponde_non_lascia_meta_scrittura(
        libreria, monkeypatch):
    """Il caso misurato: il ritiro sul file e lo stato vecchio nell'indice."""
    libreria.store(Skill(id="s1", name="una skill", trigger="t",
                         status="candidate"))
    assert _stato_su_file(libreria, "s1") == "candidate"
    assert _stato_su_indice(libreria, "s1") == "candidate"

    def _giu(*a, **k):
        raise RuntimeError("encode budget exceeded")
    monkeypatch.setattr(emb_mod, "encode", _giu)

    with pytest.raises(Exception):
        libreria.store(Skill(id="s1", name="una skill", trigger="t",
                             status="retired"))

    assert _stato_su_file(libreria, "s1") == _stato_su_indice(libreria, "s1"), (
        f"due verità: file={_stato_su_file(libreria, 's1')} "
        f"indice={_stato_su_indice(libreria, 's1')} — un encode fallito ha "
        f"lasciato passare metà scrittura")


def test_lo_store_normale_aggiorna_entrambi(libreria):
    """Controprova: la cura non deve rompere il caso che funzionava."""
    libreria.store(Skill(id="s2", name="due", trigger="t", status="candidate"))
    libreria.store(Skill(id="s2", name="due", trigger="t", status="retired"))
    assert _stato_su_file(libreria, "s2") == "retired"
    assert _stato_su_indice(libreria, "s2") == "retired"


def test_una_skill_nuova_con_encode_giu_non_nasce_a_meta(
        libreria, monkeypatch):
    """Il caso estremo: senza cura restava un file orfano senza riga
    nell'indice — sul corpus vivo ce n'è esattamente una."""
    def _giu(*a, **k):
        raise RuntimeError("encode budget exceeded")
    monkeypatch.setattr(emb_mod, "encode", _giu)

    with pytest.raises(Exception):
        libreria.store(Skill(id="s3", name="tre", trigger="t",
                             status="candidate"))
    assert _stato_su_file(libreria, "s3") is None, (
        "il file è nato senza la sua riga nell'indice")
