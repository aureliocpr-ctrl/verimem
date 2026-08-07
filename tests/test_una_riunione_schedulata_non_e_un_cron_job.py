"""«La riunione è schedulata per venerdì» finiva in quarantena.

TROVATO COL CONTROLLO POSITIVO di ws5, alla sua prima applicazione: stavo per
dichiarare un difetto di retrieval multilingue, ho verificato che il fatto
fosse entrato, ed era ``status=quarantined``::

    «Il deploy del frontend è schedulato per venerdì.»  -> QUARANTINED (L1.18)
    «La riunione è schedulata per venerdì.»             -> QUARANTINED (L1.18)
    «Il rilascio è previsto per venerdì.»               -> ok

L1.18 esiste per un buon motivo: intercetta chi dichiara «l'ho automatizzato»
senza uno scheduler a sostegno. Ma confonde DUE SENSI della stessa parola —
«schedulato» come *«ho configurato un cron»* e «schedulato» come *«è in
programma»*, che in italiano è l'uso corrente.

MISURATO, due popolazioni + il controllo positivo::

    controllo positivo (frasi ordinarie)  3/3 ok — il banco è sano
    EVENTI   (calendario umano)  bloccati  8/9   <- il difetto
    PROCESSI (automazione vera)  presi     5/6   <- il presidio da non rompere

⚠️ IL PRECEDENTE STA NEL CODICE, ed è lo stesso difetto sulla parola accanto::

    # 2026-06-14 FP fix: "recurring/periodic <problem-noun>" describes a
    # problem that keeps happening ... Only 'recurring'/'periodic' get this
    # descriptive pass — 'scheduled'/'automated' are claims of active
    # automation and still flag.

Quella cura escluse DELIBERATAMENTE `scheduled` come «claim di automazione
attiva». La misura dice che non è vero: una riunione schedulata è un
calendario. È «la cura c'era e mancava lo SWEEP», sulla riga accanto.

🔑 LA DISCRIMINANTE NON È IL SOSTANTIVO ma QUANDO ACCADE. Un «deploy» può
essere entrambe le cose; un momento SINGOLO no::

    «schedulato PER VENERDI'»      un'occorrenza   -> calendario
    «schedulato OGNI NOTTE alle 3» una ricorrenza  -> automazione

SEPARAZIONE MISURATA: eventi 8/8 · processi 6/6 sul banco; e sul CORPUS VERO
il criterio morde 1 volta su 45 fatti che contengono il verbo — quell'una è
«the quarterly board meeting is scheduled for Friday», cioè giusta. Non
trasforma nessuna automazione in calendario.

⚠️ Il beneficio non si vede sul nostro corpus (cronache tecniche, senza
riunioni): si vede su un corpus aziendale, che è dove il prodotto deve andare.
"""
from __future__ import annotations

import pytest

from verimem.l1_automated_detector import detect_unsupported_automated_claim


def _scatta(testo: str) -> bool:
    return detect_unsupported_automated_claim(
        proposition=testo, verified_by=[]) is not None


@pytest.mark.parametrize("testo", [
    "La riunione settimanale e' schedulata per venerdi alle 10.",
    "Il deploy del frontend e' schedulato per venerdi.",
    "L'intervento del tecnico e' schedulato per giovedi mattina.",
    "La consegna e' schedulata per il 12 marzo.",
    "Il colloquio con il candidato e' schedulato per lunedi.",
    "La manutenzione dell'impianto e' programmata per sabato.",
    "The board meeting is scheduled for Friday.",
    "The customer visit is scheduled for next week.",
])
def test_un_evento_di_calendario_non_e_un_claim_di_automazione(testo):
    """IL CUORE: otto frasi aziendali ordinarie, tutte quarantinate."""
    assert not _scatta(testo), f"bloccata: {testo}"


@pytest.mark.parametrize("testo", [
    "Il backup del database e' schedulato ogni notte alle 3.",
    "Il job di pulizia e' automatizzato e gira ogni ora.",
    "La sincronizzazione e' periodica e non richiede intervento.",
    "The nightly build is scheduled on the CI runner.",
    "The cleanup task is automated via cron.",
])
def test_IL_PRESIDIO_un_automazione_vera_resta_bloccata(testo):
    """IL PRESIDIO, e vale più della cura: L1.18 esiste per intercettare chi
    dichiara «l'ho automatizzato» senza uno scheduler a sostegno. Se questo
    cade, ho spento un layer del gate invece di renderlo preciso."""
    assert _scatta(testo), f"NON piu' intercettata: {testo}"


@pytest.mark.parametrize("testo", [
    "Il magazzino centrale di Rovigo ha 4200 metri quadrati.",
    "La prova gratuita dura quattordici giorni.",
    "Il paziente Rossi pesa 70 chilogrammi.",
])
def test_CONTROLLO_POSITIVO_una_frase_ordinaria_non_scatta_mai(testo):
    """IL CONTROLLO POSITIVO, adottato da ws5 dopo il suo ritiro:

        «Il difetto non è aver sbagliato: è che il mio banco NON AVEVA UN
         CONTROLLO POSITIVO. Se avessi messo accanto un caso che DEVE riuscire
         e avessi visto che non riusciva nemmeno quello…»

    Se una di queste scatta, è rotto il banco (o il detector), e non serve
    guardare il resto."""
    assert not _scatta(testo)


def test_una_ricorrenza_esplicita_vince_sul_giorno_nominato():
    """Il caso che decide fra i due criteri: c'è un giorno («ogni lunedì») MA
    è una ricorrenza. Deve restare un'automazione — altrimenti basterebbe
    nominare un giorno per aggirare il layer."""
    assert _scatta("The report is scheduled every Monday.")
    assert _scatta("Il backup e' schedulato ogni lunedi.")


def test_IL_BUCO_PREESISTENTE_automaticamente_non_e_nel_pattern():
    """📌 DIFETTO SEPARATO, dichiarato e non curato: `_AUTOMATED_PATTERN`
    contiene l'inglese `automatically` e NON l'italiano `automaticamente`.

        «Il report viene inviato ogni lunedi automaticamente.»  -> NON scatta

    È preesistente alla cura di questo file — misurato prima di toccarla (5
    processi su 6 intercettati, e il sesto era questo). Non lo curo insieme:
    allungare una lista di parole è la classe che stanotte è caduta sei volte
    su sei, e questa merita la sua misura.

    Il test lo FOTOGRAFA: quando qualcuno aggiungerà la parola, cadrà da solo
    e troverà qui il perché."""
    assert not _scatta("Il report viene inviato ogni lunedi automaticamente."), (
        "curato? allora aggiorna questo test e la nota che lo accompagna")
