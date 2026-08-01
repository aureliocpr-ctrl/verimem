"""«Non ho un giudice» e «il giudice sta scaldando» non sono la stessa cosa.

MISURATO il 2026-07-30, riproducendo l'env del server MCP piu'
``HIPPO_ENCODE_DELEGATE_ONLY=1`` (che il server si mette da se',
``mcp_server.py:13822``), e chiamando il giudice ogni 15 secondi:

    tentativo 1: NoGroundingJudge: ... (model missing or unloadable)
    tentativo 2: NoGroundingJudge: ... (model missing or unloadable)
    tentativo 3: NoGroundingJudge: ... (model missing or unloadable)
    tentativo 4: score=99.9319076538086 judge=local
    tentativo 5: score=99.9319076538086 judge=local

Per i primi ~45 secondi di vita del processo il moat NON giudica, e dice che il
modello manca o non si carica. Il modello c'e' (verificato: la stessa chiamata
senza delegate-only da 99.93 subito) e sta caricando su un thread di sfondo. Il
messaggio manda l'operatore a cercare un file che non manca — e' esattamente il
genere di diagnosi confidente-e-sbagliata che questo prodotto esiste per
impedire, emessa dal prodotto stesso.

Il difetto NON e' il caricamento differito: quello e' una cura vera (il
cold-load da ~30s sotto il lock bloccava il primo write di ogni server, la
lezione dell'hang del 2026-06-05). Il difetto e' che tre superfici — l'advisory
L4, la ricevuta MCP e ``doctor`` — DEDUCONO ognuna per conto suo perche' non
c'e' un punteggio, e nessuna delle tre sa distinguere «assente» da «sta
scaldando». Percio' la cura e' un posto solo che lo sa: ``judge_state()``.

Stessa forma della cura del contratto di uscita dei fatti: quando 13 punti
ricostruiscono a mano lo stesso dato, la cura non e' correggerne 13, e' averne
uno.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _giudice_pulito(monkeypatch):
    """Il giudice e' un singleton di processo: senza azzerarlo un test che gira
    dopo un altro leggerebbe lo stato del precedente."""
    from verimem import local_grounding as lg
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    monkeypatch.setattr(lg, "_bg_warm_started", False, raising=False)
    yield
    monkeypatch.setattr(lg, "_judge", None, raising=False)


def test_lo_stato_del_giudice_ha_un_nome(monkeypatch, tmp_path):
    """Quattro stati distinti, perche' mandano l'operatore a fare cose diverse:
    pronto · sta scaldando · assente (scaricalo) · il caricamento e' fallito."""
    from verimem import local_grounding as lg

    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "non_esiste"))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    assert lg.judge_state() == "absent"

    (tmp_path / "modello").mkdir()
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "modello"))
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    assert lg.judge_state() == "warming", (
        "in delegate-only, con il modello su disco e lo scorer non ancora "
        "caricato, lo stato e' 'sta scaldando' — non 'assente'")

    lg.get_local_judge()._scorer = lambda pairs: [99.0] * len(pairs)
    assert lg.judge_state() == "ready"

    lg.get_local_judge()._scorer = None
    lg.get_local_judge()._load_failed = True
    assert lg.judge_state() == "failed", (
        "un caricamento fallito non e' un modello assente: il primo si "
        "diagnostica, il secondo si scarica")


def test_l_advisory_non_dice_piu_che_il_modello_manca(monkeypatch, tmp_path):
    """L'advisory L4 e' cio' che finisce nella provenance del fatto: se dice
    'non installato' quando sta scaldando, resta scritto sul fatto per sempre."""
    from verimem import local_grounding as lg
    (tmp_path / "modello").mkdir()
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "modello"))
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(lg, "_judge", None, raising=False)

    from verimem.anti_confab_gate import _advisory_l4_skipped
    avviso = _advisory_l4_skipped()
    assert lg.judge_state() == "warming"
    testo = (avviso["reason"] + " " + avviso["advice"]).lower()
    assert "warm" in testo or "loading" in testo, avviso
    assert "not installed" not in testo, (
        f"dice che il modello non e' installato mentre sta caricando: {avviso}")


def test_quando_e_davvero_assente_lo_dice_ancora(monkeypatch, tmp_path):
    """La cura non deve ammorbidire il caso vero: un modello che NON c'e'
    dev'essere ancora detto assente, con il rimedio (scaricalo)."""
    from verimem import local_grounding as lg
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "manca"))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setattr(lg, "_judge", None, raising=False)

    from verimem.anti_confab_gate import _advisory_l4_skipped
    avviso = _advisory_l4_skipped()
    assert lg.judge_state() == "absent"
    assert "warmup" in avviso["advice"].lower(), avviso


def test_doctor_nomina_ANCHE_la_seconda_causa_dei_non_giudicati():
    """`doctor` attribuiva la scarsa copertura a UNA causa — «il moat gira solo
    sui write che portano una fonte» — ed e' vera e incompleta.

    Prova che la seconda causa esiste: un write CON fonte, sul canale MCP, non
    e' stato giudicato lo stesso, perche' il giudice stava ancora caricando. Un
    operatore che legge solo la prima causa aggiunge una `source` che gia'
    passava e non capisce perche' il numero non si muove.
    """
    from verimem import doctor as d
    testo = d.__file__ and open(d.__file__, encoding="utf-8").read()
    checks = [c for c in d.run_doctor() if c["name"] == "moat-judge"]
    assert checks, "il check moat-judge e' sparito"
    consiglio = (checks[0].get("fix") or "") + " " + (checks[0].get("detail") or "")
    if "carry a source" in consiglio or "carry no source" in consiglio:
        assert "warm" in consiglio.lower() or "loading" in consiglio.lower(), (
            "doctor nomina una sola causa dei non-giudicati; la seconda — il "
            "giudice che carica in sfondo sul canale MCP — resta invisibile:\n"
            f"{consiglio}")
    assert "judge_state" in testo, (
        "doctor deve leggere lo stato dalla funzione unica, non ridedurlo")


def test_il_preload_scalda_il_giudice_se_il_moat_scrive(monkeypatch):
    """Se l'operatore ha acceso il moat sul write, quel server GIUDICHERA': il
    modello va scaldato all'avvio, non alla prima scrittura (che oggi non viene
    giudicata e non viene rimessa in coda quando il giudice si sveglia).

    Resta condizionato al flag, e non e' un dettaglio: il preload incondizionato
    del cross-encoder e' costato ~450 MB per OGNI server MCP nell'incidente RAM
    del 2026-07-10. Chi non accende il moat sul write non paga niente.
    """
    from verimem import preload
    scaldati: list[str] = []
    monkeypatch.setattr(preload, "_warm_moat_judge",
                        lambda **kw: scaldati.append("moat"))

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    assert preload._deve_scaldare_il_giudice() is True

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "0")
    assert preload._deve_scaldare_il_giudice() is False

    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    assert preload._deve_scaldare_il_giudice() is False, (
        "senza il flag esplicito non si paga il modello: e' la lezione "
        "dell'incidente RAM del 2026-07-10")
