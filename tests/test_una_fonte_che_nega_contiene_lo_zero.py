"""«NESSUN SUCCESS» e «success: 0» dicono la stessa cosa, e avevano due destini.

Un claim che afferma «il numero di success è 0» veniva ammesso se la fonte
scriveva la CIFRA e fermato se la fonte diceva la stessa identica cosa a
PAROLE::

    claim «il numero di success è 0»  ·  fonte «success: 0»      ammesso
    claim «il numero di success è 0»  ·  fonte «NESSUN SUCCESS»  fermato

⚠️ NON ERA IL GATE A ESSERE SEVERO. `extract_quantities("NESSUN SUCCESS")`
restituisce l'insieme **vuoto**: per il parser quella fonte non contiene alcun
numero, quindi il claim numerico risultava senza appiglio e L4.1 lo segnalava
come «valore che la fonte non contiene». Il layer faceva il suo mestiere su
un'informazione monca.

📌 Trovato da altre due istanze e misurato in tre momenti diversi — «per salvare
un'assenza serve un comando che la STAMPI», poi «non basta stamparla, va
CONTATA» con l'A/B `0,34 quarantinato` contro `99,97 ammesso`. Qui si chiude la
causa: il difetto sta a monte di entrambe le osservazioni.

═══ ⚖️ PERCHÉ LA CURA STA NEL CONFRONTO E NON NEL PARSER ═══

La strada ovvia — insegnare a `extract_quantities` che «nessun X» vale 0 — è
stata **misurata e scartata**. Sul corpus reale, 688 occorrenze di un'assenza a
parole su 4000 fatti, e fra queste ci sono::

    «zero costo»  ·  «zero MCP»  ·  «Zero API»  ·  «nessuno è …»

cioè lo **zero enfatico**, che non è una misura che una fonte possa confermare o
smentire. Creare una quantità lì significa immettere quantità fantasma nei sei
moduli del gate che leggono `extract_quantities`, dove alimenterebbero i
rilevatori di conflitto.

⇒ Qui l'equivalenza vive **solo nel confronto fra claim e fonte**: non entra nel
corpus, non crea niente, e vale per un unico valore — lo zero.

🔑 E resta dentro il criterio che il modulo dichiara di sé: *«o quel numero è
nella fonte, o non c'è»*. Una fonte che dice «zero costo» il numero zero ce l'ha.
Se poi quello zero parli d'altro è la domanda di **L4.2**, non di questo layer:
i due ruoli restano separati, ed è la ragione per cui questa cura è piccola.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte


@pytest.mark.parametrize("claim,fonte", [
    ("Il numero di success e' 0.", "NESSUN SUCCESS"),
    ("Le occorrenze sono 0.", "nessuna occorrenza trovata"),
    ("I run completati sono 0.", "nessun run completato"),
    ("Gli errori sono 0.", "no errors found"),
    ("I file mancanti sono 0.", "neanche un file mancante"),
])
def test_una_fonte_che_NEGA_sostiene_un_claim_che_dice_zero(claim, fonte):
    """Il cuore: la stessa verità in due grafie deve avere un destino solo."""
    assert not valori_non_nella_fonte(claim, fonte), (
        f"«{fonte}» dichiara un'assenza, quindi contiene lo zero che il claim "
        f"afferma — e invece il valore risulta non sostenuto")


@pytest.mark.parametrize("claim,fonte", [
    # il claim afferma un numero DIVERSO da zero: l'assenza non lo sostiene
    ("Il numero di success e' 5.", "NESSUN SUCCESS"),
    ("Ci sono 42 righe.", "nessuna riga trovata"),
    # la fonte non nega niente: lo zero del claim resta inventato
    ("Il costo e' 0 euro.", "il piano annuale costa 200 euro"),
    # la fonte porta uno zero, ma il claim afferma altro
    ("Le occorrenze sono 3.", "occorrenze: 0"),
    # nessuno zero da nessuna parte
    ("Il gate legge in 45 ms.", "il gate scrive in 300 ms"),
])
def test_LA_POPOLAZIONE_OPPOSTA_resta_segnalata(claim, fonte):
    """⚠️ IL PRESIDIO, e vale più della cura.

    L'aggiunta è un ALLENTAMENTO — il layer segnala meno — quindi il rischio non
    è un falso allarme ma un **silenzio nuovo**. Questi cinque casi misurano
    esattamente quello: se uno smettesse di essere segnalato, la cura avrebbe
    spento il layer invece di correggerlo.
    """
    assert valori_non_nella_fonte(claim, fonte), (
        f"«{claim}» non è sostenuto da «{fonte}» e non viene più segnalato: "
        f"l'aggiunta dello zero ha allargato troppo")


def test_LO_ZERO_SI_AGGIUNGE_SOLO_LUI():
    """⚠️ Il limite dell'aggiunta, scritto come test invece che come promessa.

    Una fonte che nega NON diventa una fonte che contiene qualunque numero: si
    aggiunge lo zero e nient'altro. Se un domani qualcuno estendesse l'idea —
    «nessuno dei 5» ⇒ aggiungi anche 5 — questo test cade e chiede di misurare
    prima.
    """
    assert valori_non_nella_fonte("Il totale e' 7.", "nessun elemento")
    assert not valori_non_nella_fonte("Il totale e' 0.", "nessun elemento")


def test_IL_LIMITE_di_lingua_e_dichiarato_e_misurato():
    """📌 QUESTO TEST DOCUMENTA UN LIMITE, NON UNA CAPACITÀ.

    La lista dei quantificatori copre italiano e inglese. Francese, spagnolo,
    tedesco e russo restano scoperti: il loro claim viene fermato come prima —
    nessun comportamento nuovo, semplicemente nessun guadagno.

    Se un giorno diventasse verde, vuol dire che qualcuno ha esteso la lista, e
    allora va estesa anche la popolazione opposta qui sopra: una voce nuova può
    solo far passare claim che dicono `0`, ma quali siano va misurato.
    """
    assert valori_non_nella_fonte("Le erreurs sont 0.", "aucune erreur")
    assert valori_non_nella_fonte("Los errores son 0.", "ningún error")
