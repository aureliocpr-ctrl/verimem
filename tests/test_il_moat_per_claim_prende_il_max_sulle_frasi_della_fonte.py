"""Muro 1, pezzo 3b-bis: per claim il MAX sulle FRASI della fonte, in un lotto — e il fallback al focus DICHIARATO.

RED sopra la cura 3b (7c123e89): la coda VERA con la fonte lunga a zavorra deve
reggere e la coda FALSA deve cadere. Giudice locale FINTO che vede le frasi:
95 alla frase giusta per QUEL claim, presa da sola; 5 a tutto il resto — quindi
5 anche allo span del focus, che con budget 400 concatena piu' frasi. E' il
fenomeno misurato nella cella P-E (3d1b5c90): «la fonte D+Z entra intera nel
budget e il CE ribalta». Costo zero: nessun modello, nessun daemon.

Rosso oggi: con 3b ogni claim passa dal focus (`coppia()` →
`select_relevant_span`), lo span non e' mai una frase sola, il finto da' 5 alla
coda vera e il verdetto (il minimo) la affonda. Verde con 3b-bis: il lotto
(frase, claim) trova la frase giusta e la coda vera prende 95.
La cella col giudice VERO (i 5 casi zavorra del lead + i 30 di Galileo) resta
il banco P-E, da eseguire a «RAM ok».
"""
from __future__ import annotations

import os

import pytest

import verimem
import verimem.anti_confab_gate as g
from verimem import local_grounding as lg

FONTE = ("$ verimem warmup. [14:52:10] downloading gate model. "
         "[14:53:02] warmup finished OK. Log written to warmup.log. "
         "Il deposito di Prato ospita 300 bancali e il magazzino di Pordenone ne "
         "conta 180. Nel trimestre sono stati assunti 14 operai e formati 7 tecnici. "
         "La linea 3 ha lavorato per 22 giorni senza fermi. Il collaudo si e' "
         "concluso con tre rilievi minori.")
VERA = "Il comando warmup e' finito alle 14:53 e ha scritto il log in warmup.log"
FALSA = "Il comando warmup e' finito alle 14:53 e ha scaricato 746 MB di modello"
FRASE_GIUSTA = {
    "finito": "[14:53:02] warmup finished OK.",
    "log": "Log written to warmup.log.",
}


def _giusta(frase: str, claim: str) -> bool:
    """95 solo alla coppia (frase giusta, claim che quella frase prova). Il
    claim dei «746 MB» non ha una frase: 5 ovunque."""
    f = frase.strip()
    if "warmup.log" in claim:
        return f == FRASE_GIUSTA["log"]
    if "finito" in claim or "finished" in claim:
        return f == FRASE_GIUSTA["finito"]
    return False


class _GiudiceCheVedeLeFrasi(lg.LocalGroundingJudge):
    """Lo scorer del prodotto, finto: riceve coppie (span, claim) e da' 95 solo
    quando lo span e' ESATTAMENTE la frase giusta di quel claim. Soglia 40 come
    il giudice di casa nel RED del lead: la soglia vera del CE (gate_config)
    e' un'altra variabile e qui non si misura."""

    def __init__(self) -> None:
        super().__init__()
        self.lotti: list[int] = []
        self._scorer = self._finto
        self.threshold = 40.0

    def _finto(self, batch):  # noqa: ANN001
        self.lotti.append(len(batch))
        return [95.0 if _giusta(span, claim) else 5.0 for span, claim in batch]

    def _entro_la_finestra(self, span: str) -> str:  # niente tokenizer: costo zero
        return span


@pytest.fixture()
def giudice(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "local")
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    # La banda CE («held for review» fra tau_lo e tau_hi con backend local) e'
    # un'altra variabile: qui si misura il MAX per frase, non la banda.
    import verimem.grounding_gate as gg
    monkeypatch.setattr(gg, "_ce_band_enforced", lambda: False)
    j = _GiudiceCheVedeLeFrasi()
    lg.set_local_judge(j)
    yield j
    lg.reset_local_judge()


def _gate(testo: str, **kw):
    kw.setdefault("verified_by", None)
    kw.setdefault("topic", "prova/muro-1-3b-bis")
    kw.setdefault("agent", None)
    return g.run_validation_gate(proposition=testo, source=FONTE,
                                 grounding_llm=None, ground_write=True, **kw)


def test_CONTROLLO_quale_albero_sto_misurando():
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(verimem.__file__).startswith(os.path.abspath(qui)), verimem.__file__


def test_CONTROLLO_il_finto_distingue_la_frase_giusta_dallo_span_del_focus(giudice):
    """Il righello prima del verdetto: la frase giusta da sola vale 95, lo span
    del focus (piu' frasi) vale 5. Se questo cade, i test sotto non misurano niente."""
    frasi = lg.frasi_della_fonte(FONTE)
    assert FRASE_GIUSTA["log"] in frasi and FRASE_GIUSTA["finito"] in frasi, frasi
    coda = "Il comando warmup ha scritto il log in warmup.log."
    assert giudice._finto([(FRASE_GIUSTA["log"], coda)]) == [95.0]
    span, _ = giudice.coppia(FONTE, coda)
    assert span.strip() != FRASE_GIUSTA["log"], span
    assert giudice._finto([(span, coda)]) == [5.0]


def test_IL_ROSSO_la_coda_vera_con_la_fonte_a_zavorra_regge_col_max_per_frase(giudice):
    r = _gate(VERA)
    assert r.decomposed is True and len(r.claims) == 2, r.claims
    punteggi = [v.get("score") for v in r.claims_verdict]
    assert punteggi == [95.0, 95.0], r.claims_verdict
    assert r.grounding_score == 95.0, r.grounding_score
    assert r.action == "persist", (r.action, r.warnings)
    assert all(v.get("via") == "max-per-frase" for v in r.claims_verdict), r.claims_verdict
    # un lotto SOLO: 2 claim x 7 frasi = 14 coppie in una chiamata
    assert giudice.lotti and max(giudice.lotti) == 2 * len(lg.frasi_della_fonte(FONTE)), giudice.lotti


def test_CONTROLLO_la_coda_falsa_cade_ancora_e_il_layer_sta_sul_claim_giusto(giudice):
    r = _gate(FALSA)
    assert r.decomposed is True and len(r.claims) == 2, r.claims
    punteggi = [v.get("score") for v in r.claims_verdict]
    assert punteggi == [95.0, 5.0], r.claims_verdict
    assert r.grounding_score == 5.0 and r.action == "downgrade", (r.grounding_score, r.action)
    assert r.claims_verdict[1]["layer"] == "L4-grounding", r.claims_verdict


def test_senza_lotto_la_funzione_torna_None_e_il_chiamante_resta_sul_focus(monkeypatch):
    """Il fallback e' dichiarato, non silenzioso: in delega con il daemon muto la
    funzione torna None (il gate scrive via=focus), nessuna eccezione esce."""
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setattr(lg, "_gate_via_daemon", lambda pairs, **kw: None)
    j = lg.LocalGroundingJudge()
    j._scorer = None
    assert lg.punteggi_max_per_frase(FONTE, ["a.", "b."], judge=j) is None
    assert lg.punteggi_max_per_frase("", ["a."], judge=j) is None
    assert lg.punteggi_max_per_frase(FONTE, [], judge=j) is None
