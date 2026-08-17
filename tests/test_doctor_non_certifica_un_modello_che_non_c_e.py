"""`doctor` certificava un modello che non c'era, e il presidio non poteva vederlo.

Misurato il 17/08 alla PORTA (il comando, non la funzione) su `0805f36d`, con
lo stesso comando e come unica differenza la cartella del modello::

    ENGRAM_LOCAL_GATE_MODEL=<cartella VUOTA>      store mai usato
      ✓ moat-judge  local CE gate model installed — the grounding moat is ON
      EXIT=0
    ENGRAM_LOCAL_GATE_MODEL=<modello vero, 737.716.196 byte>   store mai usato
      ✓ moat-judge  local CE gate model installed — the grounding moat is ON
      EXIT=0

Le due schermate erano **identiche carattere per carattere**, e `doctor` è il
comando che il README prescrive proprio per verificare l'installazione: chi lo
eseguiva non aveva modo di distinguere «il moat mi protegge» da «non c'è nessun
giudice».

⚠️ **Perché nessuno se n'era accorto, ed è la ragione per cui questo file esiste
separato.** Un presidio c'era già — `test_gate_model_fetch_and_doctor.py:102` e
`:119` — e prova entrambi i casi. Ma li prova così::

    monkeypatch.setattr("verimem.local_grounding.local_ce_available",
                        lambda: False)   # e lambda: True nell'altro

cioè **sostituisce la funzione che conteneva il difetto**. Verifica che `doctor`
reagisca correttamente al booleano — e ci riesce — ma non può accorgersi che il
booleano è sbagliato. Due componenti giusti che, congiunti, ingannano: il difetto
sta nella giuntura, e un banco che sostituisce uno dei due lati non la vede mai.

⇒ **La regola di questo file: qui NON si monkeypatcha `local_ce_available` né
`judge_state`.** La cartella del modello è una cartella vera su disco, e si
chiede a `doctor` che cosa dice. Se un giorno servisse sostituirle per far
passare qualcosa, la cosa da cambiare è il prodotto.

📌 Limite dichiarato: «modello presente» qui significa `config.json` presente —
lo stesso criterio che usa `_holds_a_model`. Non certifica che i pesi si
carichino (un `model.safetensors` corrotto resta invisibile a questo banco). La
separazione misurata è **vuota / non vuota**, ed è quella che mancava.
"""
from __future__ import annotations

import pytest

from verimem.doctor import FAIL, OK, run_doctor


def _moat(checks):
    return next(c for c in checks if c["name"] == "moat-judge")


@pytest.fixture
def store_isolato(tmp_path, monkeypatch):
    """Store mai usato + nessun provider llm, così il verdetto dipende solo
    dalla cartella del modello.

    Tutti e tre gli alias: `_compat.data_dir()` ne preferisce altri prima di
    `HIPPO_DATA_DIR`, e su questa macchina `ENGRAM_DATA_DIR` punta al corpus
    reale — un test che ne pone uno solo legge lo store dell'operatore.
    """
    from verimem import local_grounding as lg

    for _env in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_env, str(tmp_path / "store"))
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: "mock")
    # Il giudice è un singleton di processo: senza azzerarlo questo test
    # leggerebbe la cartella che ha guardato il test precedente.
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    delegato = lg._GATE_DELEGATO["ok"]
    lg._GATE_DELEGATO["ok"] = False
    yield
    lg._GATE_DELEGATO["ok"] = delegato
    monkeypatch.setattr(lg, "_judge", None, raising=False)


def _con_cartella(monkeypatch, tmp_path, *, tiene_un_modello: bool):
    """Un `doctor` su una cartella nuova, col giudice azzerato PRIMA.

    L'azzeramento non è cerimonia: senza, il secondo confronto dentro lo stesso
    test eredita il giudice che la prima cartella ha già fatto fallire, e i due
    casi tornano indistinguibili — cioè il banco riprodurrebbe da sé il difetto
    che deve misurare, e lo attribuirebbe al prodotto (visto succedere mentre
    scrivevo questo file: `fail` in entrambi i rami, col prodotto già curato).
    """
    from verimem import local_grounding as lg

    d = tmp_path / "local_gate_ce_v2"
    d.mkdir(parents=True)
    if tiene_un_modello:
        (d / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(d))
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    return _moat(run_doctor())


def test_una_cartella_vuota_non_viene_certificata(store_isolato, tmp_path,
                                                  monkeypatch):
    """Il caso: la cartella c'è (un'estrazione interrotta la lascia così) e
    dentro non c'è niente."""
    mj = _con_cartella(monkeypatch, tmp_path, tiene_un_modello=False)
    assert mj["status"] == FAIL, (
        f"su una cartella vuota `doctor` non segnala nulla: {mj}. È il comando "
        f"che il README prescrive per verificare l'installazione")
    assert "missing" in mj["detail"], (
        f"il referto non dice che il modello manca: {mj['detail']}")


def test_un_modello_presente_resta_certificato(store_isolato, tmp_path,
                                               monkeypatch):
    """⚠️ POPOLAZIONE OPPOSTA, e senza di essa il test sopra si soddisfa con un
    `doctor` che dice sempre di no — che sarebbe un difetto uguale e contrario."""
    mj = _con_cartella(monkeypatch, tmp_path, tiene_un_modello=True)
    assert mj["status"] == OK, (
        f"col modello sul disco `doctor` non lo riconosce più: {mj}")
    assert "installed" in mj["detail"], mj["detail"]


def test_i_due_casi_non_danno_lo_stesso_referto(store_isolato, tmp_path,
                                                monkeypatch):
    """⚠️⚠️ L'ASSERZIONE CHE DECIDE, e va tenuta anche se sembra ridondante: il
    difetto del 17/08 non era che una delle due righe fosse sbagliata — era che
    **le due erano la stessa riga**. Un banco che controlla i due casi in due
    test separati passerebbe anche il giorno in cui tornassero a coincidere,
    purché coincidano sul valore giusto per entrambi."""
    vuota = _con_cartella(monkeypatch, tmp_path / "a", tiene_un_modello=False)
    piena = _con_cartella(monkeypatch, tmp_path / "b", tiene_un_modello=True)
    assert vuota["detail"] != piena["detail"], (
        f"`doctor` dà lo stesso identico referto con e senza il modello: "
        f"{vuota['detail']!r}")
    assert vuota["status"] != piena["status"], (
        f"stesso status nei due casi: {vuota['status']}")
