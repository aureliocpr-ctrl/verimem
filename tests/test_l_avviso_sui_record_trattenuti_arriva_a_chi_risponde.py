"""Il campo esisteva nel dizionario e non arrivava a chi formula la risposta.

`Memory.answer` costruiva il contesto con ``facts = [h["text"] for h in hits]``:
solo il testo. Il campo `hidden_records`, che `search` calcola dal 2026-08-04,
non usciva da li' — e una garanzia che vive nel dizionario e non nella risposta
e' una garanzia che nessuno legge. E' la classe di errore che questa casa paga
di piu': *il meccanismo c'e', il chiamante non lo alimenta*.

⚠️ L'AVVISO NON PORTA IL TESTO DEL FATTO NASCOSTO, ed e' una scelta di merito.
Un quarantinato e' stato filtrato in scrittura apposta: darlo a chi formula la
risposta lo servirebbe come evidenza e tradirebbe la garanzia che il prodotto
vende. Passano il CODICE, il NUMERO e il PERCHE'.

QUELLO CHE QUESTI TEST DIMOSTRANO: che l'avviso arriva nel contesto.
QUELLO CHE NON DIMOSTRANO: che il modello poi si astenga davvero — misurarlo
richiede un modello vero, e sta a chi fa dogfooding.
"""
from __future__ import annotations

from verimem.hidden_records import withheld_notice


class _Resp:
    text = "NO ANSWER"
    finish_reason = "stop"


class _LlmSpia:
    """Non risponde: registra il contesto che gli e' stato passato."""

    def __init__(self):
        self.visti: list[str] = []

    def complete(self, system, messages, max_tokens=None):
        self.visti.append(messages[0]["content"])
        return _Resp()


HIT_CON_NASCOSTI = [{
    "text": "Il ticket T-451 e' aperto e assegnato al primo livello.",
    "hidden_records": [
        {"code": "T-451", "id": "b2", "why": "quarantined",
         "text": "Il ticket T-451 e' stato chiuso il 3 marzo."},
    ],
}]


def test_l_avviso_nomina_il_record_e_il_motivo():
    avviso = withheld_notice(HIT_CON_NASCOSTI)
    assert "T-451" in avviso
    assert "quarantined" in avviso
    assert "WITHHELD" in avviso


def test_l_avviso_NON_porta_il_testo_del_fatto_trattenuto():
    """IL PRESIDIO CHE VALE PIU' DI TUTTI. Se il testo passasse, un fatto
    che il gate ha bloccato tornerebbe a chi risponde come evidenza."""
    avviso = withheld_notice(HIT_CON_NASCOSTI)
    assert "chiuso il 3 marzo" not in avviso
    assert "e' stato chiuso" not in avviso


def test_senza_nascosti_l_avviso_e_la_stringa_vuota():
    """L'ALTRO PRESIDIO: sul caso ordinario il prompt resta byte-identico.
    Sul corpus reale sono 4356 fatti su 5333 a non contenere nemmeno un
    codice, quindi e' la stragrande maggioranza delle letture."""
    assert withheld_notice([{"text": "Il progetto procede bene."}]) == ""
    assert withheld_notice([]) == ""


def test_piu_record_si_raggruppano_per_codice():
    hits = [{
        "text": "risposta",
        "hidden_records": [
            {"code": "S-007", "id": "1", "why": "retired", "text": "x"},
            {"code": "S-007", "id": "2", "why": "retired", "text": "y"},
            {"code": "T-451", "id": "3", "why": "quarantined", "text": "z"},
        ],
    }]
    avviso = withheld_notice(hits)
    assert "S-007: 2 retired" in avviso
    assert "T-451: 1 quarantined" in avviso


def test_answer_mette_l_avviso_nel_contesto(monkeypatch, tmp_path):
    """END-TO-END sulla superficie vera: e' il test che sarebbe mancato se
    avessi verificato solo la funzione — un difetto di funzione e' un'ipotesi
    finche' non e' girato end-to-end."""
    from verimem.client import Memory

    m = Memory(str(tmp_path / "s.db"))
    monkeypatch.setattr(m, "search", lambda *a, **k: HIT_CON_NASCOSTI)
    spia = _LlmSpia()
    m.answer("Il ticket T-451 e' ancora aperto?", llm=spia)
    assert spia.visti, "l'llm non e' stato chiamato"
    contesto = spia.visti[0]
    assert "WITHHELD" in contesto, contesto
    assert "T-451" in contesto
    assert "chiuso il 3 marzo" not in contesto


def test_answer_senza_nascosti_non_cambia_il_contesto(monkeypatch, tmp_path):
    from verimem.client import Memory

    m = Memory(str(tmp_path / "s.db"))
    monkeypatch.setattr(m, "search", lambda *a, **k: [{"text": "Va tutto bene."}])
    spia = _LlmSpia()
    m.answer("Come va?", llm=spia)
    contesto = spia.visti[0]
    # il formato della riga e' quello di `trust_conditioning`, attivo di
    # default: `[quando | fonte | status] testo`. Cio' che conta qui e' che
    # NULLA si aggiunga quando non c'e' niente da dichiarare.
    assert "WITHHELD" not in contesto, contesto
    assert contesto.endswith("Question: Come va?")
    assert contesto.count("\n\n") == 1, "nessuna riga in piu' fra fatti e domanda"
