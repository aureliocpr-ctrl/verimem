"""Il contratto che ogni agente riceve promette una separazione e non dice
con quale campo si legge — e il campo NON e' quello che il lettore immagina.

`agent_guide.py` e' il testo che il server MCP consegna a ogni client che si
connette: e' la prima cosa che un agente legge, quindi e' il gradino piu' alto
della gerarchia («protocollo > docstring di modulo > docstring di funzione >
commenti», di ws5 Tara).

=== IL FATTO MISURATO (11/08, store reale, 9563 fatti) ===
    `grounding_score >= 90`  (il moat ha girato e approvato) -> `model_claim` **2693**
    `grounding_score IS NULL` (il moat non ha mai guardato)  -> `model_claim` **1570**
⇒ **`status` NON separa**: un fatto verificato a 99 e uno mai giudicato portano
la stessa identica parola. Chi cerca la separazione in `status` non la trova.

=== IL DIFETTO, ed e' di LOCALITA' non di omissione ===
La guida **spiega correttamente** come si legge la separazione, ma lo fa
nell'*Orientation* (~13 righe piu' sotto): *«A number means a source was checked
against it; `null` means NEVER JUDGED … treat it as a claim, not a fact»*.
La **promessa** invece sta nella sezione *Store*: *«Pass a source whenever you
have one — it is what separates a claim from a verified fact»* — e non rimanda
al campo. Chi legge la promessa e si ferma li' cerca in `status`.
⇒ La cura e' UNA PROPOSIZIONE che collega i due punti. Non c'e' niente da
spiegare che non sia gia' spiegato: c'e' da **indicare dove**.

=== PERCHE' UN GUARDIANO SUL TESTO E NON SUL COMPORTAMENTO ===
Un test che scrive un fatto e verifica lo `status` avrebbe bisogno del giudice,
che in CI non c'e' (`verimem warmup --no-gate`): sarebbe saltato, cioe'
esattamente il difetto che ws8 Vedetta ha misurato — 16 test del moat che non
girano. Questo invece e' deterministico e gira ovunque.
⚠️ **Limite dichiarato**: presidia il TESTO, non il comportamento. Se un giorno
`status` cominciasse davvero a separare, questo test resterebbe verde e la
frase sarebbe da riscrivere al contrario. Il presidio per quel caso non c'e'.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

GUIDA = Path(__file__).resolve().parents[1] / "verimem" / "agent_guide.py"
PROMESSA = "separates a claim from a verified fact"


@pytest.fixture
def testo() -> str:
    return GUIDA.read_text(encoding="utf-8")


def _paragrafo_con(testo: str, ago: str) -> str:
    """Il blocco di righe attorno alla promessa: dal punto elenco che la
    contiene fino alla riga vuota successiva."""
    righe = testo.split("\n")
    i = next(n for n, riga in enumerate(righe) if ago in riga)
    inizio = i
    while inizio > 0 and not righe[inizio].lstrip().startswith("- "):
        inizio -= 1
    fine = i
    while fine < len(righe) - 1 and righe[fine + 1].strip():
        fine += 1
    return "\n".join(righe[inizio:fine + 1])


class TestLaPromessaIndicaIlCampo:

    def test_la_promessa_esiste_ancora(self, testo):
        """CONTROLLO POSITIVO: se qualcuno riscrive la frase, questo banco
        smette di avere senso e deve dirlo — invece di passare a vuoto."""
        assert testo.count(PROMESSA) == 1, (
            "la promessa non c'e' piu' o e' duplicata: il guardiano sotto "
            "sta presidiando una frase che non esiste"
        )

    def test_la_promessa_rimanda_al_campo_che_porta_il_verdetto(self, testo):
        """IL ROSSO: la promessa dice che passare una fonte separa un claim da
        un fatto verificato, e non dice dove quella separazione si legge."""
        par = _paragrafo_con(testo, PROMESSA)
        assert "grounding_score" in par, (
            "la promessa non nomina `grounding_score`: chi la legge cerca la "
            "separazione in `status`, dove 2693 fatti giudicati e 1570 mai "
            "giudicati portano la stessa parola"
        )

    def test_la_promessa_non_promette_uno_status_diverso(self, testo):
        """L'altra meta': la frase non deve lasciar credere che lo `status`
        cambi. Se un giorno qualcuno scrivesse «status becomes verified», il
        contratto direbbe una cosa falsa e questo diventerebbe rosso."""
        par = _paragrafo_con(testo, PROMESSA)
        bugie = re.findall(
            r"status\s+(?:becomes|is set to|turns)\s+[`']?verified", par, re.I)
        assert not bugie, f"il contratto promette uno status che non arriva: {bugie}"


class TestIlCampoResta:

    def test_l_orientation_spiega_ancora_come_si_legge(self, testo):
        """PRESIDIO sulla parte che gia' funziona: la spiegazione buona sta
        nell'Orientation e non deve sparire mentre si cura la promessa."""
        assert "means NEVER JUDGED" in testo
        assert "grounding_score" in testo
