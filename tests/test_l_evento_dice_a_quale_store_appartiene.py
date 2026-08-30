"""Un evento non diceva su QUALE memoria era successo.

Tre misure indipendenti sono cadute nella stessa ora sullo stesso file:

- **ws3**: il 94% delle quarantene in `events.jsonl` poggia su fatti che
  non esistono più — «la fonte è MULTI-STORE e non lo dice»;
- **ws1**: confermato al decimale (1279 morti su 1363), ma la causa è
  un'altra: i topic sono i NOSTRI banchi. `events.jsonl` non viene isolato
  con `HIPPO_DATA_DIR`, quindi il journal è inquinato all'88% dal nostro
  dogfooding;
- **ws4**: 2426 quarantene su 2579 poggiano su fatti assenti dal corpus.

⚠️ E la parte che mi riguarda, detta da ws1: **è un fatto mio, in memoria
da due giorni, che nessuno aveva collegato.** Avevo curato il percorso del
log — deriva dalla data dir invece di essere `~/.engram` fisso — e avevo
aggiunto l'avviso quando diverge. Ma `EVENT_LOG_PATH` si fissa
all'IMPORT: chi imposta `HIPPO_DATA_DIR` dopo aver importato verimem (cioè
ogni banco) continua a scrivere nel journal di casa. La mia cura
DICHIARAVA la divergenza e non la rendeva LEGGIBILE a valle.

La cura giusta non è impedire la scrittura — un evento perso è peggio di
un evento da filtrare — ma **far dire a ogni evento a quale memoria si
riferisce**. Con quel campo, il join sui fatti vivi (che ws1 e ws4 hanno
dovuto inventarsi, e che introduce un secondo taglio non scelto) diventa
un filtro esatto.

Impronta e non percorso: il percorso di uno store è lungo, cambia di
macchina e finisce su una pagina web; l'impronta è stabile, corta, e basta
a dire «questi due eventi vengono da memorie diverse».
"""
from __future__ import annotations

import json

import pytest

from verimem import event_jsonl_log, flow_events


@pytest.fixture()
def canale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    flow_events.reset_flow_context()
    flow_events.reset_store_fingerprint()
    return tmp_path


def _ultimo(tmp_path) -> dict:
    righe = [json.loads(ln) for ln in
             (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    return righe[-1]["payload"]


def test_ogni_evento_porta_l_impronta_dello_store(canale):
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", grounding_score=None)
    p = _ultimo(canale)
    assert p.get("store"), p


def test_due_store_DIVERSI_danno_impronte_diverse(canale, monkeypatch,
                                                  tmp_path):
    """È tutto il punto: distinguere il traffico di un banco da quello di
    produzione dentro lo STESSO file."""
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", grounding_score=None)
    uno = _ultimo(canale)["store"]

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "altro"))
    flow_events.reset_store_fingerprint()
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f2",
                           topic="t", grounding_score=None)

    assert _ultimo(canale)["store"] != uno


def test_lo_STESSO_store_da_la_STESSA_impronta(canale):
    """Altrimenti non si può raggruppare: un'impronta che cambia a ogni
    evento è rumore con un nome."""
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", grounding_score=None)
    a = _ultimo(canale)["store"]
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f2",
                           topic="t", grounding_score=None)
    assert _ultimo(canale)["store"] == a


def test_l_impronta_NON_e_il_percorso(canale):
    """Il percorso è lungo, cambia di macchina, e questo campo finisce su
    una pagina web e in un file che ci scambiamo."""
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", grounding_score=None)
    impronta = _ultimo(canale)["store"]
    assert len(impronta) <= 20, impronta
    for pezzo in ("/", "\\", ":"):
        assert pezzo not in impronta, impronta


def test_vale_per_TUTTI_gli_eventi_non_solo_per_la_scrittura(canale):
    """Il campo sta negli ambient tag: se lo mettessi solo su `flow.write`,
    le quarantene — cioè proprio la popolazione che ws3 e ws4 stavano
    misurando — resterebbero senza."""
    flow_events.emit_flow("flow.quarantine", fact_id="f1", reason="banco")
    assert _ultimo(canale).get("store"), _ultimo(canale)


def test_un_banco_che_cambia_data_dir_DOPO_l_import_non_deve_MENTIRE(
        canale, monkeypatch, tmp_path):
    """Il caso REALE, che i test sopra non toccano.

    `test_due_store_DIVERSI_danno_impronte_diverse` chiama
    `reset_store_fingerprint()` a mano prima di riemettere: verifica il caso
    CURATO, non quello che succede. Nessun banco chiama quel reset — importa
    verimem e POI imposta `HIPPO_DATA_DIR`, esattamente come qui sotto. Con
    l'impronta memorizzata all'import, i suoi eventi finiscono nel journal di
    casa marcati come se fossero di casa: 592 scritture su 980 il 29/08.

    E' lo stesso difetto che questo file racconta di aver curato:
    `EVENT_LOG_PATH` si fissava all'import, e `_IMPRONTA` si fissa all'import
    allo stesso modo. La cura ha ereditato il difetto che curava.
    """
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f1",
                           topic="t", grounding_score=None)
    casa = _ultimo(canale)["store"]

    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "banco"))
    # NESSUN reset: e' precisamente cio' che fa ogni banco reale.
    flow_events.emit_write(stored=True, status="model_claim", fact_id="f2",
                           topic="t", grounding_score=None)

    assert _ultimo(canale)["store"] != casa, (
        "l'evento del banco porta l'impronta della memoria di casa: "
        "chi analizza il journal non puo' separare le due popolazioni")
