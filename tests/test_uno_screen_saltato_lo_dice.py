"""T133 — uno screen SALTATO lo dice, con la ragione E il perimetro.

Banco preparato PRIMA del codice, come T109: la cura la scrivo dopo la fusione
di #80, ma il banco esiste gia' e oggi e' rosso. Chi scrive la cura non scrive
anche il suo giudice.

IL DIFETTO, misurato il 19/09 con DUE scritture e UNA variabile sola:

    ① normale                status=quarantined  layers=['L1.10','L1.15','L1.20']
    ② nota (meta_narrative)  status=model_claim  layers=[]
    la ricevuta della nota lo dice?  nessun campo

Non manca UN livello: ne spariscono TRE, e la ricevuta della nota e'
indistinguibile da quella di una frase pulita che ha passato tutti gli screen.

LE DUE STRADE, e sono due perimetri (condizione del lead, 19/09):
  · `narrative_l1_skip` (client.py:740) sopprime SOLO la famiglia L1 — injection,
    L3 e L4 girano. E' la strada dell'SDK: `verify_trusted_writer` rende False
    senza token, misurato in otto casi su otto.
  · `gate:2232`, con uno scrittore FIDATO e il token, ritorna subito
    (`GateResult(action="persist")`) e non gira NIENTE.
Dire «non ho guardato L1» quando non hai guardato niente e' una ricevuta che
rassicura: due perimetri, due celle.
"""
from __future__ import annotations

from verimem.anti_confab_gate import _is_advisory_layer
from verimem.client import Memory

TOPIC = "prova/t133"
#: Una frase che i lessicali DEVONO fermare, cosi' il salto si vede.
VANTO = "Il modulo e' stato testato e funziona perfettamente in produzione."


def _avvisi(r) -> list[dict]:
    return [w for w in (r.get("warnings") or []) if isinstance(w, dict)]


def _saltati(r) -> list[dict]:
    return [w for w in _avvisi(r)
            if str(w.get("stato", "")) == "saltato"
            or str(w.get("layer", "")).endswith("-skipped")]


def test_CONTROLLO_POSITIVO_senza_la_corsia_gli_screen_parlano(tmp_path):
    """Se questa cella cade, il banco misura il vuoto: la frase non fa scattare
    piu' i lessicali e il «salto» non avrebbe niente da saltare."""
    r = Memory(tmp_path / "m.db").add(VANTO, topic=TOPIC)
    strati = [w.get("layer") for w in _avvisi(r)]
    assert any(str(s).startswith("L1") for s in strati), (
        f"la frase non accende piu' nessun lessicale: strati={strati}")


def test_la_nota_DICE_che_L1_non_ha_guardato(tmp_path):
    """IL CUORE, strada `narrative_l1_skip`. Oggi questa lista e' vuota."""
    r = Memory(tmp_path / "m.db").add(VANTO, topic=TOPIC, meta_narrative=True)
    voci = _saltati(r)
    assert voci, (
        "la famiglia L1 non ha guardato e la ricevuta non lo dice: per chi "
        "legge, uno screen saltato e uno che non ha trovato niente sono la "
        f"stessa cosa.\n  avvisi resi = {[w.get('layer') for w in _avvisi(r)]}")
    for v in voci:
        assert v.get("ragione"), f"salto senza ragione: {v}"
        assert v.get("perimetro"), f"salto senza perimetro: {v}"
        assert _is_advisory_layer(str(v.get("layer", ""))), (
            f"il marcatore DECIDE: e' diventato un veto — {v}")


def test_i_due_perimetri_non_si_confondono(tmp_path):
    """La condizione del lead. «non guardato: L1» non e' «non guardato: tutto»,
    e la ricevuta della corsia SDK deve dire il primo: injection, L3 e L4 hanno
    guardato davvero."""
    r = Memory(tmp_path / "m.db").add(VANTO, topic=TOPIC, meta_narrative=True)
    for v in _saltati(r):
        p = str(v.get("perimetro", ""))
        assert "L1" in p, f"il perimetro non nomina la famiglia saltata: {p!r}"
        assert "tutt" not in p.lower(), (
            "questa corsia salta SOLO L1, e il perimetro dice che non ha "
            f"guardato nessuno: {p!r}")


def test_il_verdetto_NON_cambia(tmp_path):
    """La falsificazione. Su T93 e' scattata davvero: un marcatore advisory
    contato da una giuntura fuori convenzione ha trasformato una scrittura
    ammessa in una quarantenata."""
    a = Memory(tmp_path / "a.db").add(VANTO, topic=TOPIC, meta_narrative=True)
    assert a.get("status") != "quarantined", (
        "la nota viene trattenuta: il marcatore del salto e' diventato un veto")


def test_il_marcatore_del_salto_NON_TRAVOLGE_L4_skipped():
    """⚠️ LA CELLA CHE HA PRESO LA CI, e la scrivo qui perche' l'errore e' mio.

    La prima versione della cura allargava la convenzione con un SUFFISSO
    (`endswith("-skipped")`) e ha fatto cadere le tre gambe su
    `test_blocking_layers_keeps_l4_skipped_advisory`: `assert [] ==
    ['L4-skipped']`. Il suffisso era gia' in uso con la regola OPPOSTA.

        convenzione `_is_advisory_layer`   non puo' MAI essere la ragione
        `L4-skipped`                       se e' l'unica nota, la ragione e' lui

    Le due nozioni di «avviso» convivono, e un suffisso condiviso le fondeva in
    una. Questa cella tiene i due lati insieme, cosi' chi tocca la convenzione
    vede la coppia e non solo il proprio caso.
    """
    from verimem.client import _blocking_layers
    assert _is_advisory_layer("L1-skipped") is True
    assert _is_advisory_layer("L4-skipped") is False, (
        "il marcatore di T133 ha travolto `L4-skipped`: un avviso che il "
        "prodotto tiene fra gli attribuibili (ultima voce di "
        "`_BLOCK_LAYER_PRIORITY`) non deve sparire perche' un altro livello "
        "ha scelto lo stesso suffisso")
    assert _blocking_layers(
        [{"layer": "L4-skipped"}, {"layer": "L1-skipped"}]) == ["L4-skipped"]


def test_CONTROLLO_NEGATIVO_una_scrittura_normale_non_guadagna_il_marcatore(tmp_path):
    """Senza questa cella, marcare TUTTE le ricevute passerebbe — e un
    marcatore che c'e' sempre non significa piu' niente."""
    r = Memory(tmp_path / "m.db").add(VANTO, topic=TOPIC)
    assert not _saltati(r), (
        f"una scrittura normale dichiara uno screen saltato: {_saltati(r)}")
