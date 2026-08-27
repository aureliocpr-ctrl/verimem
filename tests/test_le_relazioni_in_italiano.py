"""Presidio bilingue di `unverified_relation`: le celle gemelle IT/EN del routing.

`anti_confab_gate.py:2669` spiega perche' questa funzione esiste: la banda «cattura
cio' di cui il CE DUBITA, mai cio' che il CE sbaglia con sicurezza», e quella classe -
relazioni che la fonte non enuncia - viene instradata a un giudice A QUALUNQUE
PUNTEGGIO da `unverified_relation()`. E' l'unica rete sotto gli errori ad alto
punteggio: se tace, non c'e' un secondo presidio dietro.

Misurato il 27/08 (ws6): la rete regge sull'inglese e sull'italiano NO, e non perche'
manchino le parole italiane - la lista LE HA. E' che i pattern chiudono con `\b` dopo
la preposizione (`dovuto a\b`), e in italiano la preposizione si FONDE con l'articolo:
«a causa DEL ritardo» e' la forma normale, «a causa DI ritardo» e' agrammaticale. Cosi'
la lista copre la forma che nessuno scrive. Stessa riga di codice, un difetto che
l'inglese non puo' avere: li' l'articolo resta staccato («due to THE overload» passa).
Secondo difetto della stessa famiglia: i participi sono in lista solo al maschile
singolare, e in italiano ogni participio ha quattro forme.

Le celle rosse sono `xfail(strict=True)`: quando la cura arriva diventano rosse davvero
e il marcatore va tolto - il presidio si accorge da solo di essere stato superato.
Falsificazione obbligatoria prima di fidarsene:
    pytest tests/test_le_relazioni_in_italiano.py --runxfail
i tre xfail DEVONO fallire; se passano, questo file non misura niente.
"""
from __future__ import annotations

import pytest

from verimem.relation_claim import unverified_relation

# fonte fissa in tutte le celle causali: nomina i fatti, MAI il legame fra loro
FONTE_IT = "La macchina si e' fermata. Ieri c'e' stato un sovraccarico."
FONTE_EN = "The machine stopped. There was an overload yesterday."
# fonte fissa per il completamento: azione INIZIATA, mai conclusa
FONTE_FATTA_IT = "La migrazione e' iniziata lunedi' e procede. Il contratto e' in firma."


# --------------------------------------------------------------- il verso che regge
@pytest.mark.parametrize("fatto", [
    "The failure is due to the overload.",
    "The failure happened because of the overload.",
    "The failure was caused by the overload.",
    "The failure happened thanks to the late fixes.",
])
def test_una_causa_inventata_e_instradata_in_inglese(fatto):
    assert unverified_relation(FONTE_EN, fatto) == "causal"


@pytest.mark.parametrize("fatto", [
    "Il guasto e' dovuto a sovraccarico.",
    "Il guasto e' avvenuto a causa di sovraccarico.",
    "Il sovraccarico ha causato il guasto.",
])
def test_una_causa_inventata_e_instradata_in_italiano_senza_articolo(fatto):
    assert unverified_relation(FONTE_IT, fatto) == "causal"


@pytest.mark.parametrize("ling,fatto,fonte", [
    ("IT", "Il farmaco previene la ricaduta.", "Il farmaco e' stato dato a dodici pazienti."),
    ("EN", "The drug prevents relapse.", "The drug was given to twelve patients."),
    ("IT", "Il collaudo garantisce la consegna.", "Il collaudo e' previsto per giovedi'."),
    ("EN", "The review guarantees delivery.", "The review is scheduled for Thursday."),
])
def test_la_modalita_e_instradata_in_entrambe_le_lingue(ling, fatto, fonte):
    """Cella VERDE tenuta apposta: il 27/08 avevo concluso che `modality` fosse spento
    perche' i miei esempi erano fuori lista. Questa cella impedisce di rifarlo."""
    assert unverified_relation(fonte, fatto) == "modality"


@pytest.mark.parametrize("fonte,fatto", [
    ("Il guasto e' stato causato dal sovraccarico di ieri.",
     "Il guasto e' stato causato dal sovraccarico."),
    ("The failure was caused by yesterday's overload.",
     "The failure was caused by the overload."),
    ("La migrazione e' stata completata lunedi'.", "La migrazione e' stata completata."),
])
def test_se_la_relazione_e_gia_nella_fonte_la_rete_tace(fonte, fatto):
    """Controllo negativo: senza questo, un `return 'causal'` costante passerebbe tutto
    il resto del file."""
    assert unverified_relation(fonte, fatto) is None


# ------------------------------------------------------------------- le celle rosse
@pytest.mark.xfail(strict=True, reason=(
    "27/08: i pattern chiudono con \b dopo la preposizione (`dovuto a\b`, "
    "`a causa di\b`, `grazie a\b`) e in italiano la preposizione si fonde con "
    "l'articolo. La forma che il pattern copre e' quella che nessuno scrive: 4 su 4 "
    "delle forme normali passano senza essere instradate. La gemella inglese e' verde "
    "qui sopra perche' li' l'articolo resta staccato."))
@pytest.mark.parametrize("fatto", [
    "Il guasto e' dovuto al sovraccarico.",
    "Il guasto e' avvenuto a causa del sovraccarico.",
    "Il guasto e' stato causato dal sovraccarico.",
    "Il guasto e' avvenuto grazie agli interventi tardivi.",
])
def test_la_preposizione_articolata_non_deve_spegnere_il_routing(fatto):
    assert unverified_relation(FONTE_IT, fatto) == "causal"


@pytest.mark.xfail(strict=True, reason=(
    "27/08: `completion` elenca i participi solo al maschile singolare "
    "(`completato`, `firmato`). In italiano ogni participio ha quattro forme e tre "
    "non sono coperte: 4 casi su 6 non vengono instradati. In inglese la forma e' "
    "una sola, quindi la stessa lista li' e' completa."))
@pytest.mark.parametrize("fatto", [
    "La migrazione e' completata.",
    "I lavori sono completati.",
    "Le migrazioni sono completate.",
    "La lettera e' firmata.",
])
def test_i_participi_femminili_e_plurali_devono_essere_instradati(fatto):
    assert unverified_relation(FONTE_FATTA_IT, fatto) == "completion"


@pytest.mark.xfail(strict=True, reason=(
    "27/08, e questo tocca l'INGLESE: la lista ha `caused by` ma non il `caused` "
    "attivo, mentre l'italiano ha `ha causato`. Le due liste non sono l'una la "
    "traduzione dell'altra: ognuna copre forme che l'altra manca."))
def test_la_causa_attiva_deve_essere_instradata_anche_in_inglese():
    assert unverified_relation(FONTE_EN, "The overload caused the failure.") == "causal"
