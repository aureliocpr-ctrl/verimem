"""Uno stato che dice «sto scaldando» mentre il daemon giudica e' uno stato che mente.

Rilievo del critic avversariale sul commit 962aa616, che l'aveva pero'
classificato come «stringa diagnostica cosmetica, fuori dallo scope della
claim»::

    L'unica imperfezione trovata — judge_state() (local_grounding.py:222)
    riporta ancora "warming" in delegate-only mentre il daemon giudica, perche'
    non consulta _GATE_DELEGATO — e' una stringa diagnostica cosmetica, non un
    difetto di correttezza. Rifiutata come nitpick fuori-scope.

Fuori scope rispetto alla claim: giusto, le scritture VENGONO giudicate. Ma non
cosmetica: `judge_state()` e' cio' che il `doctor` legge per dire in che stato
e' il giudice, ed e' la superficie su cui si decide se aspettare, se allarmarsi
o se andare avanti. Un campo che dichiara «sto scaldando» mentre il lavoro sta
gia' avvenendo altrove e' precisamente la classe curata tre volte questa
settimana — la recall che taceva quali segnali l'avessero ordinata, l'esito che
era un'etichetta e non un dato, il tool che rispondeva `found: true` senza aver
trovato niente.

`"warming"` era vero quando l'unica strada era il thread di sfondo. Da 962aa616
ce ne sono due, e lo stato deve dire QUALE regge il giudizio adesso — non
restare vero per la strada che non si sta usando.
"""
from __future__ import annotations

import pytest

from verimem import local_grounding as lg


@pytest.fixture(autouse=True)
def _pulisci():
    lg.reset_local_judge()
    lg._GATE_DELEGATO["ok"] = False
    yield
    lg._GATE_DELEGATO["ok"] = False


def test_finche_nessuno_giudica_lo_stato_resta_warming(monkeypatch, tmp_path):
    """Il caso che «warming» descriveva bene, e che deve restare intatto."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    assert lg.judge_state() == "warming"


def test_quando_il_daemon_ha_giudicato_lo_stato_lo_dice(monkeypatch, tmp_path):
    """Il difetto. Dopo una risposta del daemon il giudizio E' disponibile in
    questo processo, anche se il modello qui non c'e' e non ci sara' mai."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path))
    lg._GATE_DELEGATO["ok"] = True
    stato = lg.judge_state()
    assert stato != "warming", (
        "lo stato dice «sto scaldando» mentre il daemon sta gia' giudicando: "
        "chi legge il doctor conclude che il moat non stia girando")
    assert stato in ("ready", "delegated"), stato


def test_senza_il_modello_in_casa_lo_stato_resta_absent(monkeypatch, tmp_path):
    """Controprova che vale il test: se `delegated` scavalcasse anche il caso
    «modello assente», si direbbe «pronto» su un'installazione rotta, che e' il
    modo peggiore di sbagliare per una diagnostica."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(tmp_path / "che-non-esiste"))
    lg._GATE_DELEGATO["ok"] = False
    assert lg.judge_state() == "absent"
