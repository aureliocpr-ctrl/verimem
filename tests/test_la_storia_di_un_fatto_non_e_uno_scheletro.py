"""`history()` rendeva 4 campi dove ogni altra lettura ne rende 14.

ws2, censimento «promesse vs realtà», 2026-08-07: le istruzioni del
prodotto dicono *«Every read carries grounding_score»* — vero su
`get`/`get_all`/`search`, **falso su `history()`**, che restituisce solo
`{id, text, status, superseded_by}`. E ws2 ha precisato la cosa giusta:
non è «manca il verdetto», è una **proiezione scheletrica** — cadono
insieme provenienza, verdetto, tempo, autore.

È esattamente la classe che `fact_contract` esiste per prevenire: 13
punti costruivano a mano il dizionario di un fatto e sette dimenticavano
il verdetto. `history()` è sfuggito al contratto e ha continuato a
costruirselo.

⚠️ Due chiavi restano garantite per una ragione, e non per compatibilità
pigra:
- **`text`** era il nome storico e chi legge una storia lo usa: resta come
  alias di `proposition`;
- **`superseded_by` c'è SEMPRE, anche quando è `None`**. In una catena la
  sua assenza è informazione — «questa è la punta» — e chi cammina la
  storia lo legge a ogni passo: ometterlo perché vuoto (la regola normale
  del contratto) romperebbe proprio il camminatore.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

_FONTE = "Company handbook: the head office is located in Milan, Italy."


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _catena(m: Memory) -> tuple[str, str]:
    a = m.add("the head office is in Milan", topic="hq", source=_FONTE)["id"]
    b = m.add("the head office is in Turin", topic="hq/nuovo")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    return a, b


def test_la_storia_porta_il_verdetto_come_ogni_altra_lettura(mem):
    """La promessa scritta nelle istruzioni del prodotto: «every read
    carries grounding_score»."""
    a, _ = _catena(mem)
    voci = mem.history(a)
    assert voci, "la catena deve avere almeno una voce"
    assert all("grounding_score" in v for v in voci), voci[0]


def test_non_e_solo_il_verdetto_ma_TUTTA_la_proiezione(mem):
    """ws2: «cadono tutte le promesse insieme». Il criterio giusto non è
    «c'è il campo che ho chiesto» ma «ci sono gli stessi campi di una
    lettura normale»."""
    a, _ = _catena(mem)
    dalla_storia = set(mem.history(a)[0])
    from verimem.fact_contract import fact_payload
    dal_contratto = set(fact_payload(mem.semantic.get(a)))

    mancanti = dal_contratto - dalla_storia
    assert not mancanti, f"la storia perde {sorted(mancanti)}"


def test_il_nome_storico_text_non_si_rompe(mem):
    """Chi legge una storia usa `text` da sempre: cambiarlo sotto i piedi
    sarebbe curare una promessa rompendone un'altra."""
    a, _ = _catena(mem)
    v = mem.history(a)[0]
    assert v["text"] == v["proposition"]
    assert v["text"]


def test_superseded_by_c_e_SEMPRE_anche_quando_e_None(mem):
    """La punta della catena ha `superseded_by` nullo, e quel nullo è
    informazione: il contratto omette i vuoti, ma qui l'omissione
    romperebbe chi cammina la storia."""
    a, b = _catena(mem)
    voci = mem.history(a)
    assert all("superseded_by" in v for v in voci), voci
    assert voci[-1]["superseded_by"] is None, voci[-1]
    assert voci[0]["superseded_by"] == b


def test_l_ordine_resta_dal_piu_vecchio_al_piu_nuovo(mem):
    """Guardia sul comportamento che c'era: una proiezione più ricca non
    deve cambiare l'ordine di lettura."""
    a, b = _catena(mem)
    ids = [v["id"] for v in mem.history(a)]
    assert ids == [a, b], ids
