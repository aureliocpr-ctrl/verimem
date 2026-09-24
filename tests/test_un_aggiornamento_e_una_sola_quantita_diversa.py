"""T175 — un aggiornamento cambia UNA quantità, e nient'altro.

La cura mette UNA sola decisione numerica sotto due superfici che prima
decidevano ciascuna a modo suo, e la cella le prova tutte e due:

  SCRITTURA  `validate_claim`, strato L3 del gate: il suo «contradicted» manda
             il fatto vecchio della stessa fonte al ritiro same-source.
  BATCH      `contradiction.detect_numeric_clashes`, cioè `heal_contradictions`:
             fino al 24/09 decideva con `_values_clash` sui soli numeri, senza
             unità né parole.

Il criterio (nota di disegno approvata il 22/09, decisioni del 24/09):
  (a) una sola quantità diversa per lato, della stessa unità; un'unità presente
      in una sola frase è già una seconda differenza; i numeri nudi contano;
  (b) nessuna parola distintiva diversa (`da ^ db` vuota).

Fuori da qui, e perché:
  · il capannone 1 contro il capannone 2 (il verbo diventa l'unità): T211;
  · T149 in SCRITTURA lo ritira il giudice di entailment, non il ramo numerico:
    T210. Nel BATCH invece sta qui, perché lì decide il ramo numerico.

⚠️ COESISTENZA DICHIARATA, accettata il 24/09: nel batch, dopo la
cura, «il contatore … vale 7» e «… vale 12» non si ritirano più. La regola
posizionale degli indici (una parola seguita da un numero nudo) li legge come
due indici. In scrittura quel caso resta al giudice.

Le coppie sono vere: le prime quattro vengono dallo store, le altre dai casi
misurati il 23-24/09.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from verimem.validate_claim import validate_claim

SUITE_IN_DUE_MOMENTI = ("Sul seed 2069628213 la suite aveva 7 failed e 8585 passed.",
           "Dopo la cura la suite ha 8623 passed e EXIT=0.")
DUE_CORPORA = ("Il controllo del duplicato esatto costa 0.08 ms sul corpus REALE di 7950 righe.",
           "Il controllo del duplicato esatto costa 21.36 ms su un corpus SINTETICO di 200000 righe.")
TRE_FETTE_E_UNA = ("La suite di verimem a 3 fette del 1 agosto ha dato 2835 passed, 2804 passed e 3045 passed",
           "La fetta della suite che aveva 7 rossi dopo la cura ha dato 2929 passed con EXIT=0")
CON_E_SENZA_INDICE = ("Il controllo del duplicato esatto costa 21.36 ms su un corpus sintetico di 200000 righe.",
            "Con un indice su proposition il controllo del duplicato costa 0.127 ms su 200000 righe.")
CONTATORE_NUDO = ("Il contatore delle prove di segfault vale 7.",
                  "Il contatore delle prove di segfault vale 12.")
CONTATORE_CON_UNITA = ("Il contatore segna 10 impulsi.", "Il contatore segna 20 impulsi.")
T149 = ("Task veriagent completato — 'crea il file m1.txt con dentro il numero 1'",
        "Task veriagent completato — 'crea il file m2.txt con dentro il numero 2'")
DUE_CAMPIONI = ("Il campione S-001 contiene piombo a 11 mg/l",
                "Il campione S-002 contiene piombo a 15 mg/l")


# ---------------------------------------------------------------- scrittura --
@dataclass
class _Fatto:
    id: str
    proposition: str
    topic: str = "banco/t175"
    confidence: float = 0.9
    source_episodes: list[str] = field(default_factory=list)


class _Semantica:
    """Restituisce sempre il fatto vecchio: la cella non misura la ricerca, ma
    cosa decide il gate QUANDO il fatto vecchio è fra i risultati."""

    def __init__(self, fatti: list[_Fatto]) -> None:
        self._fatti = fatti

    def search_facts(self, query, *, limit=20, topic=None):
        return list(self._fatti)


class _Agente:
    def __init__(self, fatti: list[_Fatto]) -> None:
        self.semantic = _Semantica(fatti)


def _giudizio(vecchio: str, nuovo: str) -> tuple[str, str]:
    """(RITIRA o coesiste, advice di validate_claim).

    ⚠️ Il perché sta accanto al verdetto perché validate_claim decide con PIÙ
    rami: il 24/09 la sonda ha visto il contatore nudo ritirato dal GIUDICE di
    entailment e le coppie dello store dal ramo NUMERICO. Senza l'advice un rosso
    non dice quale ramo l'ha prodotto."""
    r = validate_claim(_Agente([_Fatto("vecchio", vecchio)]), nuovo)
    colpiti = r.get("evidence_facts") or []
    esito = ("RITIRA" if r.get("verdict") == "contradicted" and "vecchio" in colpiti
             else "coesiste")
    return esito, str(r.get("advice", ""))


SCRITTURA = [
    ("la suite in due momenti", "coesiste", *SUITE_IN_DUE_MOMENTI),
    ("due corpora", "coesiste", *DUE_CORPORA),
    ("tre fette e una", "coesiste", *TRE_FETTE_E_UNA),
    ("con e senza indice", "coesiste", *CON_E_SENZA_INDICE),
    ("contatore nudo, al giudice", "RITIRA", *CONTATORE_NUDO),
    ("controllo positivo", "RITIRA", *CONTATORE_CON_UNITA),
]


@pytest.mark.parametrize("nome, atteso, vecchio, nuovo", SCRITTURA,
                         ids=[c[0] for c in SCRITTURA])
def test_in_scrittura_un_aggiornamento_e_una_sola_quantita_diversa(
        nome, atteso, vecchio, nuovo):
    osservato, perche = _giudizio(vecchio, nuovo)
    assert osservato == atteso, (
        f"{nome}: il gate in scrittura dice {osservato}, il criterio doppio "
        f"dice {atteso}.\n  vecchio: {vecchio}\n  nuovo:   {nuovo}\n"
        f"  perché (advice di validate_claim): {perche}")


# -------------------------------------------------------------------- batch --
@pytest.fixture
def batch(monkeypatch):
    """Il batch filtra anche per coseno >= 0.75, e sotto pytest l'embedder è
    uno stub: qui il coseno è fissato a 1.0, così la cella misura SOLO la
    decisione numerica, che è quella che la cura cambia."""
    import verimem.contradiction as ct
    monkeypatch.setattr(ct, "_cosine", lambda a, b: 1.0)
    return ct


def _scontro_batch(ct, vecchio: str, nuovo: str) -> str:
    from verimem.semantic import Fact
    fatti = [Fact(id="vecchio", proposition=vecchio, topic="banco/t175"),
             Fact(id="nuovo", proposition=nuovo, topic="banco/t175")]
    return "RITIRA" if ct.detect_numeric_clashes(fatti) else "coesiste"


BATCH = [
    ("la suite in due momenti", "coesiste", *SUITE_IN_DUE_MOMENTI),
    ("due corpora", "coesiste", *DUE_CORPORA),
    ("tre fette e una", "coesiste", *TRE_FETTE_E_UNA),
    ("con e senza indice", "coesiste", *CON_E_SENZA_INDICE),
    ("T149, due task diversi", "coesiste", *T149),
    ("S-001 e S-002, due campioni", "coesiste", *DUE_CAMPIONI),
    ("contatore nudo, coesistenza dichiarata", "coesiste", *CONTATORE_NUDO),
    ("controllo positivo", "RITIRA", *CONTATORE_CON_UNITA),
]


@pytest.mark.parametrize("nome, atteso, vecchio, nuovo", BATCH,
                         ids=[c[0] for c in BATCH])
def test_il_batch_decide_come_la_scrittura(batch, nome, atteso, vecchio, nuovo):
    osservato = _scontro_batch(batch, vecchio, nuovo)
    assert osservato == atteso, (
        f"{nome}: il batch dice {osservato}, la decisione condivisa dice "
        f"{atteso}.\n  vecchio: {vecchio}\n  nuovo:   {nuovo}")
