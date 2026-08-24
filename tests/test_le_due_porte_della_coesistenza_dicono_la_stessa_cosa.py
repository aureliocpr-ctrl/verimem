"""Due porte, lo stesso verdetto, DUE spiegazioni — nella stessa ricevuta.

Il gate può decidere che due fatti in conflitto parlano di entità diverse e
vanno tenuti entrambi. Quel verdetto lo emettono **due** punti di
`anti_confab_gate.py` (le due chiamate a `_entita_diverse`), e avevano due
testi diversi. Misurato alla porta il 24/08, due `Memory.add` in regime
predefinito — e non era una porta *o* l'altra::

    L3-coexistence  ...a distinct code, date, numbered record,
                    ATTRIBUTE OR PROPER NAME — so neither is an update...
    L3-coexistence  ...a distinct code, date, OR NAMED RECORD - so
                    neither supersedes the other...

⚠️ **La seconda omette il nome proprio**, che è il ramo che scatta di più
(`if ea or eb` in `_entita_diverse`). Chi legge quella cerca un codice o una
data, non li trova, e conclude che il gate ha sbagliato. È il caso portato
sul canale da ws7 — «soggetto identico, nessuna delle tre cose presente» —
e aveva ragione: il difetto era più grande di come l'aveva descritto.

🔑 LA CURA NON È ALLINEARE DUE COPIE. Quelle ri-divergono, ed è esattamente
ciò che era successo qui senza che nessun test le confrontasse. Una costante
di modulo non può divergere per COSTRUZIONE, non per disciplina.

⛔ COSA QUESTA CURA NON FA, e va detto:
* non cambia il comportamento — solo il testo. Le misure del 24/08 sulla
  taglia del ramo reggono invariate.
* non rende verde `test_l3_subject_prefilter :: head_mismatch_never_skipped`
  (di ws7): quello riguarda lo skip, non il messaggio.
* non toglie il DUPLICATO. Il verdetto esce ancora due volte; allineati, i
  due warning sono ridondanti anziché contraddittori. Deduplicare cambia il
  numero di warning ed è una decisione separata, dichiarata e non presa.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from verimem import Memory

_GATE = Path(__file__).resolve().parent.parent / "verimem" / "anti_confab_gate.py"

VECCHIO = "The payments team still runs on the legacy processor."
NUOVO = "The payments team migrated to Stripe in 2025."


@pytest.fixture()
def avvisi(tmp_path):
    """I warning di coesistenza che un utente riceve davvero."""
    m = Memory(str(tmp_path / "s.db"))
    m.add(VECCHIO, topic="t", source=f"Minutes: {VECCHIO.lower()}")
    r = m.add(NUOVO, topic="t", source=f"Minutes: {NUOVO.lower()}")
    return [w for w in (r.get("warnings") or [])
            if "L3-coexistence" in str(w.get("layer"))]


def test_le_due_porte_non_danno_due_spiegazioni_diverse(avvisi):
    """IL CUORE, e si misura alla PORTA: qualunque sia il numero di warning,
    il verdetto deve avere UNA spiegazione sola."""
    if not avvisi:
        pytest.skip("il banco non riproduce la coesistenza in questo ambiente")
    testi = {str(w.get("advice") or "") for w in avvisi}
    assert len(testi) == 1, (
        f"lo stesso verdetto arriva con {len(testi)} spiegazioni DIVERSE nella "
        f"stessa ricevuta: {[t[:90] for t in sorted(testi)]}")


def test_la_spiegazione_nomina_il_ramo_che_scatta_di_piu(avvisi):
    """Un consiglio che elenca le cause deve elencare QUELLA che ha deciso.

    Qui il gate ha trattenuto per un NOME PROPRIO («Stripe», su un lato solo):
    un testo che parla solo di «codice, data, record nominato» manda a cercare
    tre cose che nel caso non ci sono."""
    if not avvisi:
        pytest.skip("il banco non riproduce la coesistenza in questo ambiente")
    for w in avvisi:
        assert "proper name" in str(w.get("advice") or ""), (
            f"il consiglio non nomina il nome proprio, che è la causa di "
            f"questo caso: {w.get('advice')!r}")


def test_nessuna_porta_ricabla_un_testo_suo():
    """⚠️ IL PRESIDIO STRUTTURALE, e senza di esso la cura dura un giorno.

    I due testi erano già allineati in passato e sono ri-divergiti: allineare
    due copie chiede disciplina a chi passa di lì, e prima o poi qualcuno
    modifica una sola delle due. Qui si vieta la COPIA, non la divergenza.

    ⛔ AST, non regex: l'advice sta dentro un dict annidato in una `append`,
    e una regex su una struttura annidata legge quello che capita.
    """
    albero = ast.parse(_GATE.read_text(encoding="utf-8", errors="replace"))
    colpevoli = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Dict):
            continue
        chiavi = {getattr(k, "value", None) for k in nodo.keys}
        if "layer" not in chiavi or "advice" not in chiavi:
            continue
        strato = next((v for k, v in zip(nodo.keys, nodo.values, strict=False)
                       if getattr(k, "value", None) == "layer"), None)
        if getattr(strato, "value", None) != "L3-coexistence":
            continue
        consiglio = next((v for k, v in zip(nodo.keys, nodo.values, strict=False)
                          if getattr(k, "value", None) == "advice"), None)
        # un letterale (anche implicitamente concatenato) invece della costante
        if isinstance(consiglio, ast.Constant) and isinstance(consiglio.value, str):
            colpevoli.append(nodo.lineno)
    assert not colpevoli, (
        f"queste righe ricablano un testo LETTERALE per L3-coexistence invece "
        f"di usare `_ADVICE_COESISTENZA`: {colpevoli}. Due copie ri-divergono — "
        f"è già successo.")


def test_la_costante_e_una_sola_e_viene_usata_da_entrambe():
    """Il controllo dell'altro verso: la costante esiste e non è orfana.

    Senza questo, cancellare i due usi renderebbe verde il test qui sopra —
    il modo più facile di far passare un presidio è togliere ciò che presidia.
    """
    src = _GATE.read_text(encoding="utf-8", errors="replace")
    usi = src.count("_ADVICE_COESISTENZA")
    assert usi >= 3, (
        f"`_ADVICE_COESISTENZA` compare {usi} volte: attese almeno 3 — la "
        f"definizione e le DUE porte che emettono il verdetto")
