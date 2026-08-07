"""«il fatto», «i due fatti» — il SOSTANTIVO letto come participio di chiusura.

TROVATO seguendo un numero. Se `verimem save` chiamasse il gate L1, **3520 fatti
vivi su 5781 (60%)** riceverebbero un warning, e L1.13 da solo ne fa **2082**:
è il detector che decide se quel cablaggio è possibile. Contati i suoi hit per
parola scatenante, i primi due posti sono `fatto` **437** e `fatti` **390** —
855 su 2082, il 41%.

    …ce che scrive updated_at uguale 1785623544 il fatto ha grounding 3.9…
    …Con i due fatti sul piano annuale entrambi vivi…
    …e cita i fatti 88e7462f44f9 5145cbd67e9c…

**IL PUNTO NON È UNA REGEX, È UN'OMONIMIA CHE NASCE DALLA TRADUZIONE.** In
inglese `fact` e `done` sono parole diverse e il detector non può confonderle.
In italiano «fatto» è tutt'e due: il participio di *fare* **e** il sostantivo
che questo prodotto usa per la propria unità di dominio. Il pattern è stato
esteso all'italiano parola per parola (`fatt[oaie]`, `chius[oaie]`, …) senza
accorgersi che una di quelle parole è **il nome della cosa di cui il corpus
parla tutto il tempo**. Un gate su una memoria di *fatti* non può leggere «il
fatto» come «il lavoro è finito».

MISURATO SU ENTRAMBE LE POPOLAZIONI, perché un criterio guardato solo dai
negativi sembra sempre ottimo — è la trappola già pagata cinque volte in questo
progetto. Su 855 hit di `fatt*`: **419 con un determinante davanti, 428 senza**.
Letti nove per parte:
  * con determinante → **9 su 9 sostantivi** (falsi positivi);
  * senza → **almeno 4 su 9 sono comunque sostantivi** («fatti nascono
    model_claim», «dieci fatti aziendali»).
⇒ La separazione ha **precisione alta e richiamo parziale**: questa cura toglie
i 419 senza perdere claim veri, e non pretende di prenderli tutti.

⚠️ IL CONFINE È «IMMEDIATAMENTE PRIMA». «Il task è fatto» e «il lavoro fatto in
fretta» devono continuare a scattare: lì fra il determinante e la parola c'è
qualcos'altro, e la parola resta un participio. Per lo stesso motivo restano
fuori dalla lista `tutti`/`altri`, che precedono volentieri un participio
(«sono tutti fatti»), e un numero preceduto da `#` («P1 #6 FATTO») che è un
identificatore di task, non un conteggio.
"""
from __future__ import annotations

import pytest

from verimem.l1_completion_detector import detect_unsupported_completion_claim

#: «fatto» come SOSTANTIVO: il corpus parla dei propri record.
SOSTANTIVO = [
    "Il fatto quarantinato 26dea947aee9 contiene la misura giusta.",
    "Con i due fatti sul piano annuale entrambi vivi il recall sbaglia.",
    "Il documento cita i fatti 88e7462f44f9 e 5145cbd67e9c.",
    "Fra i 21 numeric_clash residui il fatto sulla tabella e' sbagliato.",
    "La query mostra le entita' e non i fatti.",
    "Scrivendo dodici fatti aziendali su uno store vergine il recall cade.",
]

#: «fatto» come PARTICIPIO: qualcuno dichiara di aver chiuso un lavoro.
PARTICIPIO = [
    "Il task e' fatto e non serve altro.",
    "Ho fatto la migrazione del database.",
    "Il lavoro fatto in fretta va rivisto.",
    "P1 #6 FATTO 2026-05-11 senza altre note.",
    "Abbiamo completato la migrazione.",
    "La modifica e' chiusa.",
]


@pytest.mark.parametrize("prop", SOSTANTIVO)
def test_il_fatto_col_determinante_e_un_sostantivo(prop):
    """Il cuore: un determinante immediatamente prima rende «fatto» il nome di
    un record, non la dichiarazione che un lavoro è finito."""
    assert detect_unsupported_completion_claim(
        proposition=prop, verified_by=[]) is None, (
        f"«{prop}» parla di un record del corpus e viene letta come «ho finito»")


@pytest.mark.parametrize("prop", PARTICIPIO)
def test_i_claim_di_chiusura_VERI_continuano_a_chiedere_la_prova(prop):
    """Il verso che rende la cura una correzione. «Il lavoro fatto» ha un
    determinante nella frase ma non ATTACCATO alla parola, e resta un
    participio: se bastasse un articolo qualunque, la cura sarebbe un
    interruttore."""
    assert detect_unsupported_completion_claim(
        proposition=prop, verified_by=[]) is not None, (
        f"«{prop}» dichiara un lavoro chiuso senza prova e non viene piu' vista")


def test_la_prova_continua_a_zittire_il_detector():
    """La porta d'uscita legittima non si tocca."""
    assert detect_unsupported_completion_claim(
        proposition="Il task e' fatto.",
        verified_by=["pytest:test_task_PASS"]) is None


def test_una_seconda_occorrenza_VERA_non_si_nasconde_dietro_la_prima():
    """Se il fatto nomina un record e POI dichiara un lavoro chiuso, il claim
    va visto: fermarsi alla prima occorrenza renderebbe la cura una scappatoia
    — basterebbe scrivere «il fatto» all'inizio."""
    prop = "Il fatto 26dea947aee9 lo dimostra, e la migrazione e' completata."
    assert detect_unsupported_completion_claim(
        proposition=prop, verified_by=[]) is not None
