"""Il TERZO STATO delle scritture composte (design 07/09,
docs/ricerca/2026-09-07-il-terzo-stato-per-le-scritture-composte.md): quando
l'INTERO passa la banda del giudice locale (>= tau_hi) e un claim decomposto
cade sotto la soglia, la scrittura va in REVIEW col claim nominato — non in
quarantena col MIN.

Perche': sui 102 claim caduti letti uno per uno, 68 sono pezzi veri provati
alla lettera che il giudice non legge e 19 hanno la prova fuori dalla finestra
conservata; quarantinare e' sbagliato sette volte su otto, ammettere lascia
passare le 13 code false su 25 che oggi si fermano. Review tiene insieme le
due cose e la ricevuta dice QUALE pezzo guardare.

Il giudice qui e' FINTO e riproduce il muro 1: 95 all'intero (la testa vera
lo trascina), 95 alla testa, 5 alla coda isolata «746 MB». Soglie del
prodotto: moat 40, tau_hi 80, banda ON. Il RED 3b del lead e la cella 3b-bis
restano com'erano: i loro finti danno 5 all'intero, e senza intero sopra la
banda il terzo stato non scatta (e' il controllo 4 qui sotto).
"""
from __future__ import annotations

import os

import pytest

import verimem.anti_confab_gate as g
import verimem.local_grounding as lg

FONTE = ("$ verimem warmup. [14:52:10] downloading gate model. "
         "[14:53:02] warmup finished OK. Log written to warmup.log. "
         "Il deposito di Prato ospita 300 bancali e il magazzino di Pordenone ne "
         "conta 180. Nel trimestre sono stati assunti 14 operai e formati 7 tecnici.")
VERA = "Il comando warmup e' finito alle 14:53 e ha scritto il log in warmup.log"
FALSA = "Il comando warmup e' finito alle 14:53 e ha scaricato 746 MB di modello"


class _GiudiceIngannatoDallaTesta(lg.LocalGroundingJudge):
    """95 a tutto, tranne alla coda falsa ISOLATA («746» senza «finito»): 5.
    `intero` permette di abbassare il punteggio dell'intero nel controllo 3."""

    def __init__(self, intero: float = 95.0) -> None:
        super().__init__()
        self.intero = intero
        self._scorer = self._finto

    @property
    def threshold(self) -> float:
        return 40.0

    def _finto(self, batch):  # noqa: ANN001
        out = []
        for _span, claim in batch:
            if "746" in claim and "finito" not in claim:
                out.append(5.0)
            elif "746" in claim:  # l'intero FALSA: la testa vera lo trascina
                out.append(self.intero)
            else:
                out.append(95.0)
        return out

    def _entro_la_finestra(self, span: str) -> str:
        return span


@pytest.fixture()
def ambiente(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("VERIMEM_CE_BAND_ENFORCE", raising=False)
    monkeypatch.delenv("VERIMEM_CE_TAU_HI", raising=False)
    yield
    lg.reset_local_judge()


def _gate(testo: str):
    return g.run_validation_gate(proposition=testo, source=FONTE, grounding_llm=None,
                                 ground_write=True, verified_by=None,
                                 topic="prova/terzo-stato", agent=None)


def test_CONTROLLO_quale_albero_sto_misurando():
    import verimem
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(verimem.__file__).startswith(os.path.abspath(qui))


def test_CONTROLLO_il_finto_riproduce_il_muro_1(ambiente):
    j = _GiudiceIngannatoDallaTesta()
    assert j._finto([(FONTE, FALSA)]) == [95.0]
    assert j._finto([(FONTE, "Il comando warmup ha scaricato 746 MB di modello.")]) == [5.0]


def test_IL_ROSSO_intero_sopra_la_banda_e_claim_caduto_va_in_review_col_claim_nominato(ambiente):
    lg.set_local_judge(_GiudiceIngannatoDallaTesta())
    r = _gate(FALSA)
    assert r.decomposed is True and len(r.claims) == 2, r.claims
    assert [v.get("score") for v in r.claims_verdict] == [95.0, 5.0], r.claims_verdict
    assert r.action == "downgrade", (r.action, r.warnings)
    layers = [w.get("layer") for w in r.warnings]
    assert "L4-grounding" not in layers, r.warnings
    rev = [w for w in r.warnings if w.get("layer") == "L4-review"]
    assert rev and rev[0].get("claim") == 1, r.warnings
    assert "746" in str(rev[0].get("reason", "")) or "746" in str(rev[0].get("claim_text", "")), rev[0]
    assert r.claims_verdict[1]["layer"] == "L4-review", r.claims_verdict
    assert r.claims_verdict[0]["layer"] is None, r.claims_verdict


def test_la_composta_tutta_provata_resta_ammessa(ambiente):
    lg.set_local_judge(_GiudiceIngannatoDallaTesta())
    r = _gate(VERA)
    assert r.action == "persist", (r.action, r.warnings)
    assert not [w for w in r.warnings if w.get("layer") in ("L4-review", "L4-grounding")], r.warnings


def test_CONTROLLO_intero_sotto_la_banda_e_claim_caduto_resta_quarantena(ambiente):
    lg.set_local_judge(_GiudiceIngannatoDallaTesta(intero=60.0))
    r = _gate(FALSA)
    assert r.action == "downgrade", (r.action, r.warnings)
    assert r.claims_verdict[1]["layer"] == "L4-grounding", r.claims_verdict


def test_CONTROLLO_con_la_banda_spenta_il_terzo_stato_non_esiste(ambiente, monkeypatch):
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "0")
    lg.set_local_judge(_GiudiceIngannatoDallaTesta())
    r = _gate(FALSA)
    assert r.action == "downgrade", (r.action, r.warnings)
    assert r.claims_verdict[1]["layer"] == "L4-grounding", r.claims_verdict
