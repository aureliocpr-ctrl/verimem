"""T224 — i controlli sulla fonte girano anche quando chi scrive spegne il giudice.

Il difetto, misurato il 24/09 alle 23:30 su `0d0e6aac` (due processi freschi,
la porta `run_validation_gate(source=..., ground_write=False)`): lo stesso
claim, con un «7» che la fonte non ha, prende `L4.1` quando il prodotto non
vede un giudice e NIENTE quando lo vede. I controlli L4.1-L4.3 leggono solo
claim e fonte (il commento accanto alla loro chiamata lo dice), ma girano in
due rami su tre: col giudice acceso, e senza giudice. Il terzo, «il giudice
c'e' ma chi scrive l'ha spento», non entra in nessun ramo.

Le due porte da cui ci si arriva:

* SDK — `Memory.add(..., source=..., ground=False)`;
* MCP — `hippo_remember` con `ENGRAM_GROUNDING_WRITE=0`, che la porta traduce
  in `ground_write=False`.

Tre bracci per porta, che differiscono SOLO nel giudice visibile:

* `nessuno` — la cartella del modello e' vuota e nessun llm e' iniettato: e'
  il braccio di CONTROLLO, verde gia' prima della cura;
* `modello_su_disco` — un `config.json` finto sotto `ENGRAM_LOCAL_GATE_MODEL`:
  `local_ce_available()` fa una stat e dice True, niente si carica;
* `llm_iniettato` — un giudice passato a chi scrive, che non deve mai essere
  chiamato.

In ogni braccio un SENSORE deve scattare: `L1.10` su una frase che apre con
«Working». Prova che la porta ha girato, cosi' «nessun avviso» non si confonde
con «nessuna chiamata».

La promessa servita e' quella di README:46: il controllo sulle cifre e'
lessicale, cerca la cifra nella fonte, e un dettaglio aggiunto con un numero
viene fermato. Chi scrive la vede nella ricevuta: `L4.1` e il fatto in
quarantena, invece di un fatto scritto senza avvisi.

Predizione, scritta PRIMA di eseguire: i due bracci `nessuno` verdi, i quattro
con un giudice visibile ROSSI (nessun `L4.1`, fatto non in quarantena).
"""
from __future__ import annotations

import asyncio
import json
import types
from pathlib import Path

import pytest

CLAIM = "Tim suggested Edinburgh for 7 days of the team trip."
FONTE = "Tim: Edinburgh, Scotland would be great for a magical vibe."
# p098 del pilota delle memorie estratte: alla porta senza giudice da' L1.10 su «Working»
SENSORE = ("Working on cars is like therapy for Dave and a way to get away from everyday "
           "stress. He sees it as more than a hobby, but a passion.")
FONTE_SENSORE = ("Dave: It's not just a hobby, it's a passion. It's like therapy, a way to "
                 "get away from everyday stress.")


class _GiudiceCheNonSiChiama:
    """Un giudice iniettato. Il giudizio e' spento: se qualcuno lo chiama, e' un altro difetto."""

    def complete(self, *args, **kwargs):
        raise AssertionError("il giudice e' stato chiamato con il giudizio spento")


@pytest.fixture()
def isolato(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Nessuna scrittura fuori da tmp_path, e lo si CONTROLLA invece di crederlo."""
    dati = tmp_path / "dati"
    casa = tmp_path / "casa"
    dati.mkdir()
    casa.mkdir()
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(alias, str(dati))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(dati / "eventi.jsonl"))
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(dati / "mcp_audit.log"))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.delenv("ENGRAM_GROUNDING_BACKEND", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)

    from verimem._compat import provenienza_data_dir
    usata = Path(provenienza_data_dir().percorso)
    assert usata == dati, f"il prodotto userebbe {usata}, non la cartella del banco {dati}"
    return tmp_path


def _giudice_visibile(monkeypatch: pytest.MonkeyPatch, tmp: Path, giudice: str):
    """Monta il braccio e CONTROLLA che il prodotto veda quello che il braccio dice.

    La cartella del modello si fissa in TUTTI i bracci: il default sta sotto la
    casa letta all'import, e sulla macchina di chi sviluppa il modello vero c'e'.
    Il giudice locale e' un singleton che legge la cartella quando nasce: si azzera.
    """
    from verimem import local_grounding as lg

    cartella = tmp / f"modello_{giudice}"
    cartella.mkdir()
    if giudice == "modello_su_disco":
        (cartella / "config.json").write_text("{}", encoding="utf-8")
        (cartella / "model.safetensors").write_bytes(b"")
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(cartella))
    monkeypatch.setattr(lg, "_judge", None)
    atteso = giudice == "modello_su_disco"
    assert lg.local_ce_available() is atteso, (
        f"braccio {giudice}: il prodotto vede il modello su disco = "
        f"{lg.local_ce_available()}, il braccio vuole {atteso}")
    assert lg.daemon_del_giudice_annunciato() is False, "un daemon del giudice e' annunciato"
    return _GiudiceCheNonSiChiama() if giudice == "llm_iniettato" else None


def _layer_sdk(tmp: Path, llm) -> tuple[set[str], set[str], str]:
    from verimem.client import Memory

    m = Memory(str(tmp / "sdk.db"), grounding_llm=llm)
    fuori = m.add(CLAIM, source=FONTE, topic="t224/prova", ground=False)
    sensore = m.add(SENSORE, source=FONTE_SENSORE, topic="t224/sensore", ground=False)
    return ({str(w.get("layer")) for w in fuori.get("warnings") or []},
            {str(w.get("layer")) for w in sensore.get("warnings") or []},
            str(fuori.get("status")))


def _layer_mcp(tmp: Path, llm, monkeypatch: pytest.MonkeyPatch) -> tuple[set[str], set[str], str]:
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "0")
    agente = types.SimpleNamespace(semantic=SemanticMemory(db_path=tmp / "mcp.db"),
                                   wake=types.SimpleNamespace(llm=llm))
    monkeypatch.setattr(mcp_server, "_ag", lambda: agente)
    monkeypatch.setattr(mcp_server, "_agent", agente, raising=False)

    def ricevuta(prop: str, fonte: str, topic: str) -> dict:
        uscita = asyncio.run(mcp_server._call_tool_impl("hippo_remember", {  # noqa: SLF001
            "proposition": prop, "source": fonte, "topic": topic}))
        return json.loads(uscita[0].text)

    fuori = ricevuta(CLAIM, FONTE, "t224/prova")
    sensore = ricevuta(SENSORE, FONTE_SENSORE, "t224/sensore")
    return ({str(w.get("layer")) for w in fuori.get("anti_confab_warnings") or []},
            {str(w.get("layer")) for w in sensore.get("anti_confab_warnings") or []},
            str(fuori.get("status")))


@pytest.mark.parametrize("giudice", ["nessuno", "modello_su_disco", "llm_iniettato"])
@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_i_controlli_sulla_fonte_girano_col_giudice_spento(
        monkeypatch: pytest.MonkeyPatch, isolato: Path, porta: str, giudice: str) -> None:
    llm = _giudice_visibile(monkeypatch, isolato, giudice)
    if porta == "sdk":
        layer, sensore, stato = _layer_sdk(isolato, llm)
    else:
        layer, sensore, stato = _layer_mcp(isolato, llm, monkeypatch)

    # SENSORE NEL BRACCIO: la porta ha girato. Se cade, il resto non misura niente.
    assert "L1.10" in sensore, f"porta {porta}, braccio {giudice}: il sensore L1 tace: {sensore}"
    assert "L4.1" in layer, (
        f"porta {porta}, braccio {giudice}: un «7» che la fonte non ha passa senza L4.1 "
        f"quando chi scrive spegne il giudice. I controlli sulla fonte non hanno bisogno "
        f"del giudice, e senza giudice visibile girano. Avvisi della scrittura: {sorted(layer)}")
    # LA PROMESSA dal lato di chi scrive: il fatto non torna come verita'.
    assert stato == "quarantined", (
        f"porta {porta}, braccio {giudice}: il fatto col «7» inventato e' stato scritto "
        f"come {stato!r}, non in quarantena")
