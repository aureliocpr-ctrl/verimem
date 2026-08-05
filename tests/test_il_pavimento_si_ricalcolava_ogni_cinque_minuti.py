"""Il dossier costava 57 secondi, e li ripagava ogni cinque minuti.

MISURATO DA ws5 sul corpus vero, e riprodotto qui prima di toccare::

    explain chiamata 1:   56.845 ms      (ws5: 76.000 ms su 8058 fatti)
    explain chiamata 2:      773 ms      <- 73 volte più veloce
    recall:                  413 ms      <- costante, nessuna cache di mezzo

La causa è il PAVIMENTO DI RILEVANZA auto-calibrato: `estimate_relevance_floor`
fa ~32 recall di sonde e li giudica col cross-encoder. Su 8000 fatti costa
quasi un minuto. La cache c'era già — `_FLOOR_CACHE_TTL_S = 300.0` — e la
diagnosi di ws5 dice perché non bastava::

    «Il TTL è 300 secondi. Chi fa molte domande di fila paga 76 secondi UNA
     volta: tollerabile. Chi consulta il dossier OGNI TANTO paga 76 secondi
     OGNI VOLTA: inutilizzabile. E il secondo è il profilo d'uso vero —
     nessuno interroga la provenienza a raffica, la si chiede quando si ha un
     dubbio. Il caso ottimizzato dalla cache è quello che non capita mai.»

🔑 LA CURA VIENE DALLA SUA OSSERVAZIONE: **il pavimento è una proprietà del
CORPUS, non della query**. Cambia quando il corpus cambia, non quando passano
cinque minuti. Tenerlo a TTL significa ricalcolarlo per il passare del tempo
invece che per una ragione.

Quindi si persiste accanto al DB, e si invalida sul CONTEGGIO DEI FATTI.

⚠️ ACCANTO al DB e non DENTRO: una tabella nuova è una modifica di schema, e lo
schema è di un'altra istanza mentre scrivo. Un file JSON non ha migrazioni, non
ha lock, e se sparisce si ricalcola — il costo di perderlo è un ricalcolo, non
un errore.
"""
from __future__ import annotations

import json

import pytest

from verimem.client import Memory


@pytest.fixture()
def mem(tmp_path):
    m = Memory(str(tmp_path / "s.db"))
    for i in range(6):
        m.add(f"Il magazzino K-{70 + i} ha {4000 + i * 100} metri quadrati.",
              topic="az/mag")
    return m


def test_il_pavimento_sopravvive_a_un_CLIENT_NUOVO(mem, tmp_path):
    """IL CUORE: chi apre il prodotto, chiede, chiude e torna un'ora dopo non
    deve ripagare la calibrazione. Prima la cache era per-istanza e a 5
    minuti: un client nuovo la trovava sempre fredda."""
    primo = mem._auto_relevance_floor()
    secondo = Memory(str(tmp_path / "s.db"))._auto_relevance_floor()
    assert secondo == pytest.approx(primo), "un client nuovo ricalcola da zero"


def test_e_lo_fa_SENZA_ricalcolare(mem, tmp_path, monkeypatch):
    """Il presidio del presidio: non basta che il valore coincida — deve
    arrivare dal file, non da un secondo calcolo che dà lo stesso numero."""
    mem._auto_relevance_floor()
    import verimem.relevance_floor as rf

    def _vietato(*a, **k):
        raise AssertionError("ha ricalcolato invece di leggere il valore salvato")

    monkeypatch.setattr(rf, "estimate_relevance_floor", _vietato)
    m2 = Memory(str(tmp_path / "s.db"))
    assert isinstance(m2._auto_relevance_floor(), float)


def test_il_corpus_che_CRESCE_lo_invalida(mem, tmp_path):
    """⚠️ IL PRESIDIO CHE CONTA. Il pavimento è calibrato SU QUEL corpus: se il
    corpus cambia in modo sostanziale e il valore resta congelato, serviamo un
    pavimento sbagliato per sempre — che è peggio di uno lento."""
    mem._auto_relevance_floor()
    for i in range(60):
        mem.add(f"Il deposito Z-{i:03d} ha {200 + i} metri quadrati.",
                topic="az/dep")
    m2 = Memory(str(tmp_path / "s.db"))
    dati = json.loads((tmp_path / "s.db.floor.json").read_text(encoding="utf-8"))
    n_salvato = dati["n_facts"]
    m2._auto_relevance_floor()
    dopo = json.loads((tmp_path / "s.db.floor.json").read_text(encoding="utf-8"))
    assert dopo["n_facts"] > n_salvato, (
        "il corpus e' cresciuto e il pavimento non e' stato ricalcolato")


def test_un_file_illeggibile_non_rompe_nulla(mem, tmp_path):
    """Fail-open: il valore salvato è un'ottimizzazione, non un dato. Se il
    file è corrotto o scritto da una versione futura, si ricalcola — non si
    alza un'eccezione in faccia a chi ha solo chiesto un dossier."""
    mem._auto_relevance_floor()
    (tmp_path / "s.db.floor.json").write_text("{non json", encoding="utf-8")
    assert isinstance(
        Memory(str(tmp_path / "s.db"))._auto_relevance_floor(), float)


def test_CONTROLLO_POSITIVO_il_pavimento_e_un_numero_sensato(mem):
    """Se questo cade, è rotto il banco: un pavimento fuori da [0,1] non è un
    coseno e le altre misure non vogliono dire niente."""
    v = mem._auto_relevance_floor()
    assert 0.0 <= v <= 1.0, v
