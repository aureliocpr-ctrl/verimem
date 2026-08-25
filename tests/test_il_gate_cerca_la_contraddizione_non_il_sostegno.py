"""Write-side: il gate ferma cio' che CONTRADDICE la fonte, non cio' che la fonte
non sostiene. Misurato il 2026-08-25 su `397c6375`, dalla porta.

LA RIGA DEL README CHE QUESTO FILE MISURA — prima schermata, non la tabella:
«Every write passes an admission gate ... when the evidence isn't there the system
abstains instead of guessing».

Il gemello `test_abstention_ce_gate` presidia la stessa parola sul lato READ («on a
query the store CANNOT support, abstain»), e regge. Qui si guarda il lato WRITE, che
non aveva presidio: un claim che la fonte NON SOSTIENE — e che non contraddice
nessun token — viene ammesso con punteggio alto.

IL BANCO, a variabile singola. Stessa frase, cambia UNA parola::

    fonte:  pytest tests/test_pagamenti.py: 12 passed, 3 failed in 4.21s
    «I 3 test falliti di test_pagamenti.py girano su ___.»

        Docker      quarantined  g= 0,4     entita' DENTRO il dominio della fonte
        Python      quarantined  g= 0,2
        Roma        model_claim  g=95,6     entita' FUORI dal dominio -> AMMESSA
        Parmigiano  model_claim  g=84,8
        Azzurro     model_claim  g=97,5
        Marco       model_claim  g=95,4

Soggetto e verbo sono irrilevanti (misurato scambiandoli: «12 passati/scritti da
Marco» 98,8 · «3 falliti/girano su Windows» 1,2). La tokenizzazione e' esclusa:
sono tutte parole note da 1 token (Azzurro 2). Resta il dominio.

⇒ un'entita' del dominio entra in tensione con cio' che la fonte dice e il
  punteggio crolla; un'entita' estranea non contraddice niente, quindi non abbassa
  niente, quindi passa. **«I 3 test falliti girano su Parmigiano» e' ammessa a
  84,8**, mentre «girano su Docker» — plausibile e altrettanto assente dalla
  fonte — e' fermata a 0,4.

⚖️ IL GATE NON E' ROTTO, e la popolazione di controllo qui sotto serve a dirlo: sui
claim che la fonte sostiene e' corretto, e sulle contraddizioni funziona. Fa bene
una cosa DIVERSA da quella che il testo promette, ed e' per questo che il difetto
non compariva in nessun rosso.

⚠️ MAI MISURATO COL GIUDICE LLM INIETTATO. `Memory(llm=...)` «turns the moat ON at
judge quality» (client.py:410) e il quadro potrebbe cambiare — nel qual caso la
scelta del giudice non e' configurazione ma sicurezza. Non e' stato provato perche'
richiede `claude -p --model` e l'autorizzazione esplicita di chi paga il piano.

⚠️ DOVE QUESTO FILE NON PROTEGGE: una fonte sola, sei entita', CE locale. Da' il
MECCANISMO, non un tasso di prodotto. E se il CE non e' installato il banco misura
un altro giudice: in quel caso l'xfail potrebbe passare per la ragione sbagliata.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

FONTE = "pytest tests/test_pagamenti.py: 12 passed, 3 failed in 4.21s"
FRASE = "I 3 test falliti di test_pagamenti.py girano su {}."


def _grounding(proposizione: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "g.db"))
    ric = mem.add(proposizione, topic="t/dominio", source=FONTE, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


@pytest.mark.parametrize("entita", ["Docker", "Python"])
def test_CONTROLLO_una_entita_del_dominio_viene_fermata(entita):
    """La meta' che FUNZIONA, e senza la quale l'xfail non si sa leggere.

    Se cadesse anche questa, il difetto non sarebbe piu' «il gate guarda la cosa
    sbagliata» ma «il gate non guarda niente», che e' un'altra gravita'.
    """
    stato, punteggio = _grounding(FRASE.format(entita))
    assert stato == "quarantined", (
        f"«{entita}» non e' nella fonte ed e' del dominio: era fermata "
        f"(g=0,4 e 0,2 il 25/08), adesso {stato} g={punteggio}")


@pytest.mark.parametrize("entita", ["Roma", "Parmigiano", "Azzurro", "Marco"])
@pytest.mark.xfail(strict=True, reason=(
    "noto e non curato (2026-08-25): il gate cerca la contraddizione, non il "
    "sostegno. Un'entita' estranea al dominio non contraddice nulla, quindi non "
    "abbassa il punteggio, quindi passa (84,8-97,5). Curarlo vuol dire chiedere "
    "l'ENTAILMENT invece della non-contraddizione: cambio di modello, non patch. "
    "strict: il giorno in cui viene curato questo diventa rosso e lo dice."))
def test_una_aggiunta_estranea_alla_fonte_dovrebbe_essere_fermata(entita):
    """La promessa e' «abstains instead of guessing»: qui il prodotto indovina."""
    stato, punteggio = _grounding(FRASE.format(entita))
    assert stato == "quarantined", (
        f"la fonte non dice nulla su «{entita}» e il claim e' ammesso "
        f"({stato}, g={punteggio})")


def test_CONTROLLO_un_claim_che_la_fonte_sostiene_passa():
    """L'altra popolazione: il gate non deve diventare severo per caso.

    Se un giorno l'xfail qui sopra si chiudesse rendendo il gate cieco anche ai
    claim veri, la cura sarebbe peggiore del difetto — questo lo dice subito.
    """
    stato, punteggio = _grounding("Il file test_pagamenti.py ha 12 test passati.")
    assert stato != "quarantined", (
        f"un claim che la fonte sostiene viene ora rifiutato: {stato} g={punteggio}")
