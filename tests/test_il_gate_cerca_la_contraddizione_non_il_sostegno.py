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


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-26, 20:28 (`8713d66c`): la stessa proprieta' vista dove fa piu' danno.
# Sopra si cambia l'ENTITA' e la fonte tace su di lei. Qui si cambia la FORMA di
# una self-claim, e la fonte dice il contrario:
#
#   fonte: «Il modulo di pagamento e' stato scritto il 3 marzo.
#           Restano aperte due segnalazioni.»
#
#     caso                     status        grounding  moat
#     canonica  SENZA source   quarantined   None       not_run:no_source
#     riformul. SENZA source   model_claim   None       not_run:no_source   🔴
#     canonica  CON source     quarantined   85.2       passed              ⚠️
#     riformul. CON source     model_claim   95.3       passed              🔴🔴
#     controllo: fatto VERO    model_claim   99.8       passed
#
# Due cose che nessuna delle due meta' dice da sola:
#  · la canonica CON source e' quarantined MA il moat dice `passed` a 85.2 —
#    a fermarla e' L1, il moat l'avrebbe ammessa;
#  · fra il fatto VERO (99.8) e il vanto infondato (95.3) ci sono 4,5 punti:
#    nessuna soglia li separa.
# ⇒ le due difese non sono complementari. Il moat e' fortissimo contro la
#   CONTRADDIZIONE (misurato da ws3: 0/10 falsita' ammesse nei due versi) e non
#   e' una seconda linea contro il VANTO: e' una linea contro un'altra cosa.
#
# ⚠️ Ho ritirato, prima di scrivere questo, la conclusione opposta: avevo trovato
# che i 9 candidati a self-claim elusa nel corpus (su 9416 fatti di 60 giorni)
# erano 8 su 8 con grounding 98-99,98, e ne stavo deducendo «il moat copre cio'
# che L1 elude». Sono sostenuti perche' scriviamo fatti veri con fonti vere.
# Era inferenza da un'assenza.

FONTE_VANTO = (
    "Il modulo di pagamento e stato scritto il 3 marzo. "
    "Restano aperte due segnalazioni."
)
CANONICA = "Il modulo e stato testato."
RIFORMULATA = "Il modulo ha superato i test."


def _esito(proposizione: str, con_fonte: bool) -> tuple[str, float | None, str]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "v.db"))
    extra = {"source": FONTE_VANTO, "validate": "full"} if con_fonte else {}
    ric = mem.add(proposizione, topic="t/vanto", **extra)
    return str(ric.get("status")), ric.get("grounding_score"), str(ric.get("moat"))


def test_CONTROLLO_la_forma_canonica_del_vanto_e_fermata():
    """Il righello. Senza questo, gli xfail qui sotto non si sanno leggere."""
    stato, _, _ = _esito(CANONICA, con_fonte=False)
    assert stato == "quarantined", (
        f"il gate non ferma nemmeno {CANONICA!r}: questo banco non misura piu' nulla "
        f"({stato})"
    )


def test_CONTROLLO_un_fatto_che_la_fonte_sostiene_resta_ammesso():
    """L'altra popolazione: la cura non deve rendere il gate cieco ai fatti veri."""
    stato, punteggio, _ = _esito(
        "Il modulo di pagamento e stato scritto il 3 marzo.", con_fonte=True
    )
    assert stato != "quarantined", (
        f"un fatto che la fonte sostiene viene rifiutato: {stato} g={punteggio}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="riformulare elude L1: la self-claim entra come model_claim (26/08)",
)
def test_la_stessa_self_claim_riformulata_dovrebbe_essere_fermata():
    stato, _, _ = _esito(RIFORMULATA, con_fonte=False)
    assert stato == "quarantined"


@pytest.mark.xfail(
    strict=True,
    reason="il caso grave: CON una fonte che dice il contrario, la riformulata "
    "entra con grounding ~95 e moat passed — il moat non e' una seconda linea "
    "contro il vanto (26/08)",
)
def test_e_nemmeno_con_una_fonte_che_dice_il_contrario():
    stato, punteggio, moat = _esito(RIFORMULATA, con_fonte=True)
    assert stato == "quarantined", f"entrata con g={punteggio}, moat={moat}"


def test_a_fermare_il_vanto_canonico_e_L1_non_il_moat():
    """Lo stato attuale, e se un giorno diventa rosso e' una BUONA notizia.

    La canonica con fonte esce `quarantined`, ma il moat su quella stessa
    scrittura dice `passed`: il verdetto viene dal lexical screen. Se questo
    test fallisce perche' il moat ha smesso di dire `passed`, vuol dire che ha
    imparato a vedere il vanto — aggiornare il banco, non il prodotto.
    """
    stato, punteggio, moat = _esito(CANONICA, con_fonte=True)
    assert stato == "quarantined", f"atteso quarantined, ottenuto {stato}"
    assert moat == "passed", (
        "il moat non dice piu' `passed` sul vanto canonico: se ora lo giudica, "
        f"questa e' una buona notizia e il banco va aggiornato (moat={moat}, "
        f"g={punteggio})"
    )
