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

📌 **Il limite, misurato e non stimato.** Il criterio è «i file ci sono»: con un
`config.json` e un `model.safetensors` dal contenuto non valido, `doctor` dice
ancora `✓ the grounding moat is ON` con EXIT=0 (misurato il 17/08). Il confine è
scelto, non subìto: **cartella vuota** e **soli metadati** sono stati che il
prodotto produce DA SÉ — la destinazione nasce prima del download, e
l'estrazione mette `config.json` prima dei pesi — mentre un file di pesi
corrotto richiede una corruzione esterna del filesystem. Coprire anche quello
vuole un caricamento vero, che sfonda il budget di ~2 s che `doctor` dichiara e
difende. ⚠️ Chi misurasse che i pesi corrotti sono un caso reale ha il diritto
di riaprirlo: il confine è documentato QUI e non è presidiato da nessun test
verde, perché un verde su un comportamento indesiderato lo autorizzerebbe.
"""
from __future__ import annotations

import pytest

from verimem.doctor import FAIL, OK, WARN, run_doctor


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


def _con_cartella(monkeypatch, tmp_path, *, stato: str):
    """Un `doctor` su una cartella nuova, col giudice azzerato PRIMA.

    `stato` è uno dei TRE che il prodotto sa produrre da sé:
      «vuota»          il download crea la destinazione prima di scaricare, e
                       una rete che cade la lascia così;
      «solo_metadati»  l'estrazione mette `config.json` (1 KB) prima dei pesi
                       (737 MB), e interrotta a metà lascia questo;
      «completa»       metadati e pesi.

    L'azzeramento del giudice non è cerimonia: senza, il secondo confronto
    dentro lo stesso test eredita il giudice che la prima cartella ha già fatto
    fallire, e i casi tornano indistinguibili — cioè il banco riprodurrebbe da
    sé il difetto che deve misurare, e lo attribuirebbe al prodotto (visto
    succedere mentre scrivevo questo file: `fail` in entrambi i rami, col
    prodotto già curato).
    """
    from verimem import local_grounding as lg

    d = tmp_path / "local_gate_ce_v2"
    d.mkdir(parents=True)
    if stato in ("solo_metadati", "completa"):
        (d / "config.json").write_text("{}", encoding="utf-8")
    if stato == "completa":
        (d / "model.safetensors").write_bytes(b"\x00")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(d))
    monkeypatch.setattr(lg, "_judge", None, raising=False)
    return _moat(run_doctor())


def test_una_cartella_vuota_non_viene_certificata(store_isolato, tmp_path,
                                                  monkeypatch):
    """Il caso: la cartella c'è (un'estrazione interrotta la lascia così) e
    dentro non c'è niente."""
    mj = _con_cartella(monkeypatch, tmp_path, stato="vuota")
    assert mj["status"] == FAIL, (
        f"su una cartella vuota `doctor` non segnala nulla: {mj}. È il comando "
        f"che il README prescrive per verificare l'installazione")
    assert "missing" in mj["detail"], (
        f"il referto non dice che il modello manca: {mj['detail']}")


def test_i_soli_metadati_non_sono_un_giudice_che_funziona(store_isolato,
                                                          tmp_path, monkeypatch):
    """Lo stato intermedio, e la ragione per cui esiste questo test: la prima
    versione di questo file lo asseriva come CASO BUONO.

    Misurato il 17/08 su una cartella con il solo `config.json`::

        verimem doctor   «local CE gate model installed - the moat is ON»  EXIT=0
        verimem save     judged=False, grounding_score=None, L4-skipped,
                         e «900 pallet» contro una fonte che dice 480 AMMESSO

    ⇒ `doctor` certificava di proteggere in uno stato in cui il moat non gira.
    Un test verde su un comportamento sbagliato non è neutro: autorizza.
    """
    mj = _con_cartella(monkeypatch, tmp_path, stato="solo_metadati")
    assert mj["status"] == FAIL, (
        f"con i metadati e senza i pesi `doctor` dice che va bene: {mj}")
    assert "weights" in mj["detail"], mj["detail"]
    assert "delete" in (mj.get("fix") or ""), (
        f"il rimedio non dice di togliere di mezzo la cartella a metà: "
        f"{mj.get('fix')!r}. Eseguire `warmup` su di essa riporta «already "
        f"installed» con EXIT=0 senza scaricare nulla (misurato il 17/08)")


def test_con_un_llm_disponibile_il_referto_indica_la_strada(store_isolato,
                                                            tmp_path,
                                                            monkeypatch):
    """⚠️ L'ALTRA POPOLAZIONE DELLO STESSO CASO, ed è un difetto che la prima
    stesura di questa cura aveva introdotto: con un llm disponibile il referto
    diceva «moat OFF» e basta, mandando a riscaricare 737 MB di modello chi
    poteva già far giudicare passando `llm=` a Memory.

    È la distinzione che il ramo del CE ASSENTE fa da sempre — WARN con la
    strada, non FAIL — e il ramo nuovo doveva ereditarla invece di ignorarla.
    """
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: "openai")
    mj = _con_cartella(monkeypatch, tmp_path, stato="solo_metadati")
    assert mj["status"] == WARN, (
        f"con un llm disponibile il CE incompleto è un avviso, non un "
        f"fallimento: {mj}")
    assert "openai" in mj["detail"], mj["detail"]
    assert "llm=" in mj["detail"], (
        f"il referto non dice come far girare il moat con l'llm che c'è: "
        f"{mj['detail']}")


def test_un_modello_presente_resta_certificato(store_isolato, tmp_path,
                                               monkeypatch):
    """⚠️ POPOLAZIONE OPPOSTA, e senza di essa i test sopra si soddisfano con un
    `doctor` che dice sempre di no — che sarebbe un difetto uguale e contrario."""
    mj = _con_cartella(monkeypatch, tmp_path, stato="completa")
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
    vuota = _con_cartella(monkeypatch, tmp_path / "a", stato="vuota")
    piena = _con_cartella(monkeypatch, tmp_path / "b", stato="completa")
    assert vuota["detail"] != piena["detail"], (
        f"`doctor` dà lo stesso identico referto con e senza il modello: "
        f"{vuota['detail']!r}")
    assert vuota["status"] != piena["status"], (
        f"stesso status nei due casi: {vuota['status']}")
